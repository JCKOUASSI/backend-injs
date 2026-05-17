from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from math import radians, sin, cos, sqrt, atan2
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from authentication.permissions import IsDFRC, IsDFRCOrEncadrant, IsSecretariatOrEncadrantOrDFRC, IsSecretariatOrDFRC
from authentication.throttles import ScanRateThrottle
from formations.models import (
    Formation, Participant, Module, ModuleParticipant, ModuleFormateur,
    Formateur, QRToken, SessionModule, RefSite,
)
FormationParticipant = ModuleParticipant
FormationFormateur = ModuleFormateur
from formations.serializers import ParticipantSerializer, FormateurSerializer, FormationListSerializer
from formations.session_views import _auto_manage_sessions
from .models import Pointage, DeviceBinding, AuditLog, _log_audit
from .serializers import (
    PointageSerializer,
    ScanSerializer,
    SecureScanSerializer,
    SecureHeartbeatSerializer,
    ForcePointageSerializer,
)

User = get_user_model()


def _password_change_required_response():
    return Response(
        {
            'code': 'PASSWORD_CHANGE_REQUIRED',
            'detail': 'Vous devez changer votre mot de passe avant de continuer.',
        },
        status=status.HTTP_403_FORBIDDEN,
    )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _normalize_scan_identifier(value):
    """Normalise un identifiant saisi pour comparer les variantes de format."""
    return ''.join(ch for ch in (value or '').strip().upper() if ch.isalnum())


def _resolve_personne(numero, formation, module=None):
    """
    Résout un numéro (auditeur, formateur, encadrant) vers la personne et vérifie l'inscription.
    Retourne (personne, type_str, personne_data, error_response).
    Note: `personne_data` est volontairement "minimal" pour limiter la fuite de PII sur l'endpoint public.
    """
    numero_upper = (numero or '').strip().upper()
    numero_compact = _normalize_scan_identifier(numero)

    # Variantes acceptées pour un badge formateur:
    # - casse indifférente (f0042 == F0042)
    # - espaces/ponctuation ignorés (F 00-42)
    # - saisie numérique seule (42 -> F0042)
    formateur_candidates = {numero_upper}
    if numero_compact:
        formateur_candidates.add(numero_compact)
    if numero_compact.isdigit():
        formateur_candidates.add(f"F{int(numero_compact):04d}")
    elif numero_compact.startswith('F') and numero_compact[1:].isdigit():
        formateur_candidates.add(f"F{int(numero_compact[1:]):04d}")

    # Portée du contrôle: module (si fourni) sinon formation.
    # Cela permet d'imposer strictement la liste autorisée de la séance scannée.
    module_scope = module

    # Chercher d'abord comme formateur (numéros courts: F0001, F0002…)
    # puis comme participant (numéros FNCE24-xxx, matricule, etc.)
    formateur_filters = Q()
    for candidate in formateur_candidates:
        formateur_filters |= Q(numerobadge__iexact=candidate)
    formateur = Formateur.objects.filter(formateur_filters).first()
    if formateur is not None:
        formateur_in_scope = (
            ModuleFormateur.objects.filter(module=module_scope, formateur=formateur).exists()
            if module_scope is not None
            else ModuleFormateur.objects.filter(module__formation=formation, formateur=formateur).exists()
        )
        if not formateur_in_scope:
            return None, None, None, Response(
                {'code': 'FORMATEUR_NOT_IN_LIST',
                 'detail': 'Formateur non autorisé pour ce module.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return formateur, 'formateur', {
            'numero': formateur.numerobadge,
            'nom': formateur.nom,
            'prenom': formateur.prenom,
        }, None

    # Chercher comme encadrant via son matricule utilisateur
    encadrant = User.objects.filter(
        role='ENCADRANT',
        matricule=numero_upper,
    ).first()
    if encadrant is not None:
        encadrant_in_scope = (
            bool(module_scope and module_scope.superviseur_id == encadrant.id)
            if module_scope is not None
            else Formation.objects.filter(pk=formation.pk, modules__superviseur=encadrant).exists()
        )
        if not encadrant_in_scope:
            return None, None, None, Response(
                {'code': 'ENCADRANT_NOT_IN_LIST',
                 'detail': 'Encadrant non autorisé pour ce module.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return encadrant, 'encadrant', {
            'numero': encadrant.matricule,
            'nom': encadrant.last_name or '',
            'prenom': encadrant.first_name or '',
            'username': encadrant.username,
        }, None

    # Chercher comme participant par matricule
    participant = Participant.objects.filter(matricule__iexact=numero_upper).first()
    if participant is None and numero_compact and numero_compact != numero_upper:
        participant = Participant.objects.filter(matricule__iexact=numero_compact).first()
    if participant is None and numero_compact:
        # Fallback tolérant: comparer la version normalisée des matricules
        # uniquement sur les participants attendus de la formation.
        for insc in (
            ModuleParticipant.objects
            .filter(module__formation=formation)
            .select_related('participant')
            .only(
                'participant__id',
                'participant__matricule',
                'participant__nom',
                'participant__prenom',
            )
        ):
            p = insc.participant
            if p and _normalize_scan_identifier(p.matricule) == numero_compact:
                participant = p
                break
    if participant is None:
        return None, None, None, Response(
            {'code': 'PARTICIPANT_NOT_FOUND',
             'detail': 'Auditeur introuvable.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    participant_in_scope = (
        ModuleParticipant.objects.filter(module=module_scope, participant=participant).exists()
        if module_scope is not None
        else ModuleParticipant.objects.filter(module__formation=formation, participant=participant).exists()
    )
    if not participant_in_scope:
        return None, None, None, Response(
            {'code': 'PARTICIPANT_NOT_IN_LIST',
             'detail': 'Auditeur non autorisé pour ce module.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return participant, 'participant', {
        'numero': participant.matricule,
        'nom': participant.nom,
        'prenom': participant.prenom,
    }, None


def _pointage_filter(personne, type_personne, formation, **extra):
    """Construit le filtre de pointage pour participant ou formateur."""
    base = {'session__module__formation': formation}
    if type_personne == 'formateur':
        base['formateur'] = personne
    elif type_personne == 'encadrant':
        base['encadrant'] = personne
    else:
        base['participant'] = personne
    base.update(extra)
    return base


def _create_pointage_kwargs(personne, type_personne, session, **extra):
    """Construit les kwargs de création de pointage."""
    base = {'session': session}
    if type_personne == 'formateur':
        base['formateur'] = personne
    elif type_personne == 'encadrant':
        base['encadrant'] = personne
    else:
        base['participant'] = personne
    base.update(extra)
    return base


def _find_open_pointage_same_module_day(
    personne, type_personne, module, date_journee, exclude_session_id=None
):
    """
    Retourne le pointage ouvert d'une personne sur le même module et jour.
    Utilisé pour empêcher une nouvelle entrée sur une autre séance
    tant que la précédente n'est pas terminée.
    """
    filt = (
        {'formateur': personne}
        if type_personne == 'formateur'
        else {'encadrant': personne}
        if type_personne == 'encadrant'
        else {'participant': personne}
    )
    qs = Pointage.objects.select_for_update().filter(
        **filt,
        session__module=module,
        date_journee=date_journee,
        timestamp_sortie__isnull=True,
    )
    if exclude_session_id is not None:
        qs = qs.exclude(session_id=exclude_session_id)
    return qs.order_by('-timestamp_entree').first()


def _has_unfinished_previous_session(seance):
    """
    Retourne True si une séance précédente du même module et du même jour
    n'est pas encore terminée.
    """
    return SessionModule.objects.filter(
        module=seance.module,
        date_journee=seance.date_journee,
        numero__lt=seance.numero,
        terminee_le__isnull=True,
    ).exists()


def _get_accessible_formation(user, pk):
    """
    Récupère une formation accessible par l'utilisateur.
    Délègue à formations.access.formation_accessible pour une logique centralisée.
    """
    from formations.access import formation_accessible
    return formation_accessible(user, pk)


def _check_fenetre_entree(seance):
    """
    Vérifie que le scan d'entrée se fait dans la fenêtre autorisée :
      - Le jour du scan doit correspondre à seance.date_journee
      - L'heure courante ne doit pas dépasser heure_fin_prevue (si renseignée)
    Retourne None si OK, sinon une Response d'erreur.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo('Africa/Abidjan')
    now_local = timezone.localtime(timezone.now())
    today = now_local.date()

    # Mauvais jour
    if seance.date_journee and seance.date_journee != today:
        return Response(
            {'code': 'WRONG_DAY',
             'detail': f'Ce QR code est prévu pour le {seance.date_journee.strftime("%d/%m/%Y")}. Le badgeage n\'est pas autorisé aujourd\'hui.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Heure après la fin prévue de la séance
    if seance.heure_fin_prevue and now_local.time() > seance.heure_fin_prevue:
        return Response(
            {'code': 'SESSION_TIME_OVER',
             'detail': f'La fenêtre de badgeage est dépassée. La séance était prévue jusqu\'à {seance.heure_fin_prevue.strftime("%H:%M")}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return None


def _clamp_to_seance(ts, seance):
    """
    Borne un timestamp aux heures prévues de la séance.
    - Si ts est avant heure_debut_prevue → retourne heure_debut_prevue
    - Si ts est après heure_fin_prevue   → retourne heure_fin_prevue
    - Sinon retourne ts tel quel.
    """
    if seance is None:
        return ts
    from datetime import datetime
    local_ts = timezone.localtime(ts)
    date = local_ts.date()
    tz = local_ts.tzinfo
    if seance.heure_debut_prevue and local_ts.time() < seance.heure_debut_prevue:
        return timezone.make_aware(datetime.combine(date, seance.heure_debut_prevue), tz)
    if seance.heure_fin_prevue and local_ts.time() > seance.heure_fin_prevue:
        return timezone.make_aware(datetime.combine(date, seance.heure_fin_prevue), tz)
    return ts


def _resolve_authenticated_personne(user):
    """Retourne (personne, type_str, error_response)."""
    try:
        return user.participant_profile, 'participant', None
    except (Participant.DoesNotExist, AttributeError):
        pass

    try:
        return user.formateur_profile, 'formateur', None
    except (Formateur.DoesNotExist, AttributeError):
        pass

    if user.role == 'ENCADRANT':
        if not user.matricule:
            return None, None, Response(
                {
                    'code': 'NO_MATRICULE',
                    'detail': 'Aucun matricule renseigné sur votre compte encadrant.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return user, 'encadrant', None

    return None, None, Response(
        {
            'code': 'NO_PROFILE',
            'detail': 'Aucun profil auditeur, formateur ou encadrant lié à ce compte.',
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def _distance_meters(lat1, lon1, lat2, lon2):
    """Distance approximative en mètres (haversine)."""
    earth_radius_m = 6371000
    phi1 = radians(float(lat1))
    phi2 = radians(float(lat2))
    d_phi = radians(float(lat2) - float(lat1))
    d_lambda = radians(float(lon2) - float(lon1))
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * earth_radius_m * atan2(sqrt(a), sqrt(1 - a))


def _resolve_site_geofence(module):
    """
    Retourne (lat, lon, rayon_m) pour le site du module, ou (None, None, None)
    si aucun RefSite correspondant ne possède de geofence configurée.
    Le lien se fait préférentiellement par FK (Module.site → RefSite),
    avec fallback legacy par nom si nécessaire.
    """
    # Nouveau modèle: module.site est une FK.
    site_obj = getattr(module, 'site', None)
    if site_obj is not None:
        # Peut être un objet RefSite déjà chargé, ou juste un id.
        try:
            site_id = getattr(module, 'site_id', None)
        except Exception:
            site_id = None
        if site_id:
            site = RefSite.objects.filter(pk=site_id).first()
        elif getattr(site_obj, 'pk', None):
            site = site_obj
        else:
            site = None
    else:
        site = None

    # Fallback legacy: match par texte
    if site is None:
        site_name = (getattr(module, 'site_legacy', '') or '').strip()
        if not site_name:
            return None, None, None
        site = RefSite.objects.filter(nom__iexact=site_name).first()

    if site is None or site.geofence_latitude is None or site.geofence_longitude is None:
        return None, None, None
    rayon = site.geofence_rayon_m or getattr(settings, 'MOBILE_GEOFENCE_DEFAULT_RADIUS_M', 200)
    return site.geofence_latitude, site.geofence_longitude, rayon


def _check_geofence(module, latitude, longitude, accuracy_m=None):
    """
    Vérifie si la position est dans la zone autorisée du site du module.
    Retourne (ok, code, detail, distance_m, rayon_m).
    """
    site_lat, site_lon, rayon_m = _resolve_site_geofence(module)
    if site_lat is None or site_lon is None:
        return True, None, None, None, None

    max_accuracy = getattr(settings, 'MOBILE_GEOFENCE_MAX_ACCURACY_M', 80)
    if accuracy_m is not None and float(accuracy_m) > float(max_accuracy):
        return (
            False,
            'LOCATION_INACCURATE',
            f"Précision GPS insuffisante ({round(float(accuracy_m), 1)}m). "
            f"Seuil maximum autorisé: {max_accuracy}m.",
            None,
            None,
        )

    rayon_m = float(rayon_m)
    distance_m = _distance_meters(latitude, longitude, site_lat, site_lon)
    if distance_m > rayon_m:
        return (
            False,
            'OUT_OF_GEOFENCE',
            (
                f"Hors périmètre autorisé ({round(distance_m, 1)}m du site, "
                f"rayon max {round(rayon_m, 1)}m)."
            ),
            distance_m,
            rayon_m,
        )

    return True, None, None, distance_m, rayon_m


# ──────────────────────────────────────────────
# ENDPOINT /api/scan/ — Participants & Formateurs
# ──────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([ScanRateThrottle])
def scan_view(request):
    """
    Endpoint de scan QR — gère ENTREE et SORTIE pour participants (P0001) et formateurs (F0001).

    body: { token_qr, numero_participant, device_id }
    """
    serializer = ScanSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # 1. Vérifier token QR valide
    try:
        qr_token = QRToken.objects.select_related('session__module__formation').get(
            token=data['token_qr']
        )
    except QRToken.DoesNotExist:
        return Response(
            {'code': 'INVALID_TOKEN', 'detail': 'QR code invalide.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if qr_token.is_expired:
        return Response(
            {'code': 'TOKEN_EXPIRED', 'detail': 'QR code expiré.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Si le token a été remplacé (regeneration QR), utiliser le token actif courant
    if not qr_token.actif:
        replacement = QRToken.objects.filter(
            session=qr_token.session,
            actif=True,
        ).order_by('-created_at').first()
        if replacement and replacement.is_valid:
            qr_token = replacement
        else:
            return Response(
                {'code': 'TOKEN_EXPIRED', 'detail': 'QR code désactivé. Aucun QR actif pour cette séance.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    seance = qr_token.session
    if not seance:
        return Response({'code': 'NO_SESSION', 'detail': 'Ce QR code n\'est pas lié à une séance.'}, status=status.HTTP_400_BAD_REQUEST)
    if seance.est_terminee:
        return Response(
            {'code': 'TOKEN_EXPIRED', 'detail': 'QR code désactivé. Cette séance est terminée.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    formation = seance.module.formation

    # 2. Résoudre la personne (participant ou formateur)
    personne, type_str, personne_data, err = _resolve_personne(
        data['numero_participant'], formation, seance.module
    )
    if err:
        return err

    role_map = {
        'participant': 'Participant',
        'formateur': 'Formateur',
        'encadrant': 'Encadrant',
    }
    role_label = role_map.get(type_str, 'Participant')

    # 3. Chercher une session ouverte aujourd'hui (transaction + verrou)
    today = timezone.localdate()
    device_id = data.get('device_id', '')

    with transaction.atomic():
        if type_str == 'formateur':
            Formateur.objects.select_for_update().get(pk=personne.pk)
        elif type_str == 'encadrant':
            User.objects.select_for_update().get(pk=personne.pk)
        else:
            Participant.objects.select_for_update().get(pk=personne.pk)

        # Filtres de base pour cette séance
        session_filter = _pointage_filter(personne, type_str, formation, date_journee=today)
        session_filter['session'] = seance

        # Vérifier si un pointage TERMINÉ existe déjà pour cette séance → bloquer
        pointage_termine = Pointage.objects.filter(
            **session_filter, timestamp_sortie__isnull=False,
        ).exists()
        if pointage_termine:
            seance_label = seance.intitule or f"Séance {seance.numero}"
            return Response({
                'code': 'ALREADY_SCANNED',
                'detail': f'Vous avez déjà pointé (entrée + sortie) pour « {seance_label} ».',
            }, status=status.HTTP_400_BAD_REQUEST)

        # "Ouverte" = timestamp_sortie NULL
        pointage_ouvert = Pointage.objects.select_for_update().filter(
            **session_filter, timestamp_sortie__isnull=True,
        ).order_by('-timestamp_entree').first()

        if pointage_ouvert:
            pointage_ouvert.timestamp_sortie = _clamp_to_seance(timezone.now(), seance)
            pointage_ouvert.statut = Pointage.Statut.TERMINE
            pointage_ouvert.calculer_duree()
            pointage_ouvert.save()

            _log_audit(
                action=AuditLog.Action.SCAN_SORTIE,
                request=request,
                cible_type=type_str,
                cible_numero=personne_data['numero'],
                cible_nom=f"{personne_data['nom']} {personne_data['prenom']}",
                pointage=pointage_ouvert,
                device_id=device_id,
                extra={'duree_minutes': float(pointage_ouvert.duree_presence_minutes or 0)},
            )

            sessions_jour = Pointage.objects.filter(
                **_pointage_filter(
                    personne, type_str, formation,
                    date_journee=today,
                    timestamp_sortie__isnull=False,
                )
            )
            total_jour = sum(
                float(s.duree_presence_minutes or 0) for s in sessions_jour
            )
            nb_sessions = sessions_jour.count()

            return Response({
                'action': 'SORTIE',
                'type_personne': type_str,
                'participant': personne_data if type_str == 'participant' else None,
                'formateur': personne_data if type_str == 'formateur' else None,
                'encadrant': personne_data if type_str == 'encadrant' else None,
                'date': str(today),
                'timestamp': pointage_ouvert.timestamp_sortie,
                'duree_session_minutes': pointage_ouvert.duree_presence_minutes,
                'duree_total_jour_minutes': round(total_jour, 2),
                'nb_sessions': nb_sessions,
                'message': (
                    f'Sortie enregistrée ({role_label}). '
                    f'Session : {pointage_ouvert.duree_presence_minutes} min | '
                    f'Total jour : {round(total_jour)} min ({nb_sessions} session(s)).'
                ),
            })

        pointage_ouvert_autre_seance = _find_open_pointage_same_module_day(
            personne=personne,
            type_personne=type_str,
            module=seance.module,
            date_journee=today,
            exclude_session_id=seance.id,
        )
        if pointage_ouvert_autre_seance:
            seance_label = (
                pointage_ouvert_autre_seance.session.intitule
                or f"Séance {pointage_ouvert_autre_seance.session.numero}"
            )
            return Response(
                {
                    'code': 'SESSION_ALREADY_OPEN',
                    'detail': (
                        f'Une autre session est déjà en cours sur ce module '
                        f'({seance_label}). Terminez-la d’abord.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if _has_unfinished_previous_session(seance):
            return Response(
                {
                    'code': 'PREVIOUS_SESSION_NOT_TERMINATED',
                    'detail': (
                        'Impossible de badger cette séance tant que la '
                        'séance précédente du même jour n’est pas terminée.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        nb_sessions_existantes = Pointage.objects.filter(
            **_pointage_filter(
                personne, type_str, formation,
                date_journee=today,
                timestamp_sortie__isnull=False,
            )
        ).count()

        # Block new ENTREE if the session is already terminated
        if seance.est_terminee:
            return Response(
                {'code': 'SESSION_TERMINATED', 'detail': 'La séance est terminée. Aucune nouvelle entrée possible.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier la fenêtre horaire et le jour
        fenetre_err = _check_fenetre_entree(seance)
        if fenetre_err:
            return fenetre_err

        timestamp_entree = _clamp_to_seance(timezone.now(), seance)
        create_kwargs = _create_pointage_kwargs(
            personne, type_str, seance,
            date_journee=today,
            device_id=device_id,
            timestamp_entree=timestamp_entree,
            statut=Pointage.Statut.EN_COURS,
        )

        pointage = Pointage.objects.create(**create_kwargs)

        _log_audit(
            action=AuditLog.Action.SCAN_ENTREE,
            request=request,
            cible_type=type_str,
            cible_numero=personne_data['numero'],
            cible_nom=f"{personne_data['nom']} {personne_data['prenom']}",
            formation=formation,
            pointage=pointage,
            device_id=device_id,
        )

        return Response({
            'action': 'ENTREE',
            'type_personne': type_str,
            'participant': personne_data if type_str == 'participant' else None,
            'formateur': personne_data if type_str == 'formateur' else None,
            'encadrant': personne_data if type_str == 'encadrant' else None,
            'date': str(today),
            'timestamp': pointage.timestamp_entree,
            'duree_presence_minutes': None,
            'nb_sessions': nb_sessions_existantes + 1,
            'message': f'Entrée enregistrée ({role_label}).',
        }, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────
# ENDPOINT /api/scan/secure/ — App mobile (anti-fraude)
# Le numéro est déduit du user connecté : impossible de badger pour autrui.
# ──────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScanRateThrottle])
def secure_scan_view(request):
    """
    Scan sécurisé pour l'app mobile.
    Le participant/formateur doit être authentifié.
    Son numéro est automatiquement déduit de son profil — anti-fraude.

    body: { token_qr, device_id }
    """
    serializer = SecureScanSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    user = request.user
    if getattr(user, 'must_change_password', False):
        return _password_change_required_response()

    # 1. Résoudre le profil participant/formateur/encadrant lié au user
    personne, type_str, err = _resolve_authenticated_personne(user)
    if err:
        return err

    # 1b. Vérifier que l'appareil est bien lié à ce user
    device_id = data.get('device_id', '')
    if device_id and type_str == 'participant':
        binding = DeviceBinding.objects.filter(
            device_id=device_id, is_active=True
        ).first()
        if binding and binding.user_id != user.id:
            return Response(
                {'code': 'DEVICE_MISMATCH',
                 'detail': 'Cet appareil est lié à un autre compte. '
                           'Contactez votre superviseur.'},
                status=status.HTTP_403_FORBIDDEN,
            )

    # 2. Vérifier token QR valide
    try:
        qr_token = QRToken.objects.select_related('session__module__formation').get(
            token=data['token_qr']
        )
    except QRToken.DoesNotExist:
        return Response(
            {'code': 'INVALID_TOKEN', 'detail': 'QR code invalide.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if qr_token.is_expired:
        return Response(
            {'code': 'TOKEN_EXPIRED', 'detail': 'QR code expiré.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Si le token a été remplacé (regeneration QR), utiliser le token actif courant
    if not qr_token.actif:
        replacement = QRToken.objects.filter(
            session=qr_token.session,
            actif=True,
        ).order_by('-created_at').first()
        if replacement and replacement.is_valid:
            qr_token = replacement
        else:
            return Response(
                {'code': 'TOKEN_EXPIRED', 'detail': 'QR code désactivé. Aucun QR actif pour cette séance.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    seance = qr_token.session
    if not seance:
        return Response({'code': 'NO_SESSION', 'detail': 'Ce QR code n\'est pas lié à une séance.'}, status=status.HTTP_400_BAD_REQUEST)
    if seance.est_terminee:
        return Response(
            {'code': 'TOKEN_EXPIRED', 'detail': 'QR code désactivé. Cette séance est terminée.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    formation = seance.module.formation

    # 3. Vérifier inscription à la formation
    if type_str == 'formateur':
        if not ModuleFormateur.objects.filter(
            module=seance.module, formateur=personne
        ).exists():
            return Response(
                {'code': 'NOT_IN_LIST',
                 'detail': 'Vous n\'êtes pas assigné(e) à ce module.'},
                status=status.HTTP_403_FORBIDDEN,
            )
    elif type_str == 'encadrant':
        if seance.module.superviseur_id != personne.id:
            return Response(
                {'code': 'NOT_IN_LIST',
                 'detail': 'Vous n\'êtes pas encadrant de ce module.'},
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        if not ModuleParticipant.objects.filter(
            module=seance.module, participant=personne
        ).exists():
            return Response(
                {'code': 'NOT_IN_LIST',
                 'detail': 'Vous n\'êtes pas inscrit(e) à ce module.'},
                status=status.HTTP_403_FORBIDDEN,
            )

    personne_data = {
        'numero': (
            getattr(personne, 'matricule', None)
            or getattr(personne, 'numerobadge', None)
            or getattr(personne, 'numero', '')
        ),
        'nom': getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '',
        'prenom': getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or '',
    }
    role_map = {
        'participant': 'Participant',
        'formateur': 'Formateur',
        'encadrant': 'Encadrant',
    }
    role_label = role_map.get(type_str, 'Participant')

    # 4. Logique entrée/sortie — 1 entrée + 1 sortie par séance
    today = timezone.localdate()

    with transaction.atomic():
        if type_str == 'formateur':
            Formateur.objects.select_for_update().get(pk=personne.pk)
        elif type_str == 'encadrant':
            User.objects.select_for_update().get(pk=personne.pk)
        else:
            Participant.objects.select_for_update().get(pk=personne.pk)

        # Filtres de base pour cette séance
        session_filter = _pointage_filter(personne, type_str, formation, date_journee=today)
        session_filter['session'] = seance

        # Vérifier si un pointage TERMINÉ existe déjà pour cette séance → bloquer
        pointage_termine = Pointage.objects.filter(
            **session_filter, timestamp_sortie__isnull=False,
        ).exists()
        if pointage_termine:
            seance_label = seance.intitule or f"Séance {seance.numero}"
            return Response({
                'code': 'ALREADY_SCANNED',
                'detail': f'Vous avez déjà pointé (entrée + sortie) pour « {seance_label} ».',
            }, status=status.HTTP_400_BAD_REQUEST)

        # "Ouverte" = timestamp_sortie NULL
        pointage_ouvert = Pointage.objects.select_for_update().filter(
            **session_filter, timestamp_sortie__isnull=True,
        ).order_by('-timestamp_entree').first()

        if pointage_ouvert:
            pointage_ouvert.timestamp_sortie = _clamp_to_seance(timezone.now(), seance)
            pointage_ouvert.statut = Pointage.Statut.TERMINE
            pointage_ouvert.calculer_duree()
            pointage_ouvert.save()

            _log_audit(
                action=AuditLog.Action.SCAN_SECURE_SORTIE,
                request=request,
                cible_type=type_str,
                cible_numero=personne_data['numero'],
                cible_nom=f"{personne_data['nom']} {personne_data['prenom']}",
                formation=formation,
                pointage=pointage_ouvert,
                device_id=device_id,
                extra={'duree_minutes': float(pointage_ouvert.duree_presence_minutes or 0)},
            )

            sessions_jour = Pointage.objects.filter(
                **_pointage_filter(
                    personne, type_str, formation,
                    date_journee=today,
                    timestamp_sortie__isnull=False,
                )
            )
            total_jour = sum(
                float(s.duree_presence_minutes or 0) for s in sessions_jour
            )
            nb_sessions = sessions_jour.count()

            return Response({
                'action': 'SORTIE',
                'type_personne': type_str,
                'participant': personne_data if type_str == 'participant' else None,
                'formateur': personne_data if type_str == 'formateur' else None,
                'encadrant': personne_data if type_str == 'encadrant' else None,
                'formation': {'id': formation.id, 'titre': formation.formation},
                'date': str(today),
                'timestamp': pointage_ouvert.timestamp_sortie,
                'duree_session_minutes': pointage_ouvert.duree_presence_minutes,
                'duree_total_jour_minutes': round(total_jour, 2),
                'nb_sessions': nb_sessions,
                'message': (
                    f'Sortie enregistrée ({role_label}). '
                    f'Session : {pointage_ouvert.duree_presence_minutes} min | '
                    f'Total jour : {round(total_jour)} min ({nb_sessions} session(s)).'
                ),
            })

        pointage_ouvert_autre_seance = _find_open_pointage_same_module_day(
            personne=personne,
            type_personne=type_str,
            module=seance.module,
            date_journee=today,
            exclude_session_id=seance.id,
        )
        if pointage_ouvert_autre_seance:
            seance_label = (
                pointage_ouvert_autre_seance.session.intitule
                or f"Séance {pointage_ouvert_autre_seance.session.numero}"
            )
            return Response(
                {
                    'code': 'SESSION_ALREADY_OPEN',
                    'detail': (
                        f'Une autre session est déjà en cours sur ce module '
                        f'({seance_label}). Terminez-la d’abord.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if _has_unfinished_previous_session(seance):
            return Response(
                {
                    'code': 'PREVIOUS_SESSION_NOT_TERMINATED',
                    'detail': (
                        'Impossible de badger cette séance tant que la '
                        'séance précédente du même jour n’est pas terminée.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        nb_sessions_existantes = Pointage.objects.filter(
            **_pointage_filter(
                personne, type_str, formation,
                date_journee=today,
                timestamp_sortie__isnull=False,
            )
        ).count()

        # Block new ENTREE if the session is already terminated
        if seance.est_terminee:
            return Response(
                {'code': 'SESSION_TERMINATED', 'detail': 'La séance est terminée. Aucune nouvelle entrée possible.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier la fenêtre horaire et le jour
        fenetre_err = _check_fenetre_entree(seance)
        if fenetre_err:
            return fenetre_err

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy_m = data.get('accuracy_m')
        battery_level = data.get('battery_level')
        is_charging = data.get('is_charging')

        if (latitude is None) ^ (longitude is None):
            return Response(
                {
                    'code': 'LOCATION_INVALID',
                    'detail': 'latitude et longitude doivent être fournis ensemble.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        site_lat_cfg, site_lon_cfg, _site_rayon = _resolve_site_geofence(seance.module)
        if site_lat_cfg is not None and latitude is None:
            return Response(
                {
                    'code': 'LOCATION_REQUIRED',
                    'detail': 'La géolocalisation est obligatoire pour badger cette séance.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        distance_m = None
        rayon_m = None
        if latitude is not None and longitude is not None:
            geo_ok, geo_code, geo_detail, distance_m, rayon_m = _check_geofence(
                seance.module, latitude, longitude, accuracy_m
            )
            if not geo_ok:
                return Response({'code': geo_code, 'detail': geo_detail}, status=status.HTTP_400_BAD_REQUEST)

        timestamp_entree = _clamp_to_seance(timezone.now(), seance)
        create_kwargs = _create_pointage_kwargs(
            personne, type_str, seance,
            date_journee=today,
            device_id=device_id,
            last_heartbeat_at=timezone.now(),
            last_latitude=latitude,
            last_longitude=longitude,
            last_accuracy_m=accuracy_m,
            last_battery_level=battery_level,
            last_is_charging=is_charging,
            timestamp_entree=timestamp_entree,
            statut=Pointage.Statut.EN_COURS,
        )

        pointage = Pointage.objects.create(**create_kwargs)

        _log_audit(
            action=AuditLog.Action.SCAN_SECURE_ENTREE,
            request=request,
            cible_type=type_str,
            cible_numero=personne_data['numero'],
            cible_nom=f"{personne_data['nom']} {personne_data['prenom']}",
            formation=formation,
            pointage=pointage,
            device_id=device_id,
            extra={
                'distance_m': round(distance_m, 1) if distance_m is not None else None,
                'rayon_m': round(rayon_m, 1) if rayon_m is not None else None,
                'accuracy_m': accuracy_m,
                'battery_level': battery_level,
                'is_charging': is_charging,
            },
        )

        return Response({
            'action': 'ENTREE',
            'type_personne': type_str,
            'participant': personne_data if type_str == 'participant' else None,
            'formateur': personne_data if type_str == 'formateur' else None,
            'encadrant': personne_data if type_str == 'encadrant' else None,
            'formation': {'id': formation.id, 'titre': formation.formation},
            'date': str(today),
            'timestamp': pointage.timestamp_entree,
            'duree_presence_minutes': None,
            'nb_sessions': nb_sessions_existantes + 1,
            'message': f'Entrée enregistrée ({role_label}).',
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScanRateThrottle])
def secure_scan_heartbeat(request):
    """
    Heartbeat mobile sécurisé pendant une session ouverte.
    body: { token_qr, device_id, latitude, longitude, accuracy_m?, battery_level?, is_charging? }
    """
    serializer = SecureHeartbeatSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    user = request.user
    if getattr(user, 'must_change_password', False):
        return _password_change_required_response()
    personne, type_str, err = _resolve_authenticated_personne(user)
    if err:
        return err

    device_id = data.get('device_id', '')
    if device_id and type_str == 'participant':
        binding = DeviceBinding.objects.filter(
            device_id=device_id, is_active=True
        ).first()
        if binding and binding.user_id != user.id:
            return Response(
                {
                    'code': 'DEVICE_MISMATCH',
                    'detail': 'Cet appareil est lié à un autre compte. Contactez votre superviseur.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    try:
        qr_token = QRToken.objects.select_related('session__module__formation').get(
            token=data['token_qr']
        )
    except QRToken.DoesNotExist:
        return Response(
            {'code': 'INVALID_TOKEN', 'detail': 'QR code invalide.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if qr_token.is_expired:
        return Response(
            {'code': 'TOKEN_EXPIRED', 'detail': 'QR code expiré.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not qr_token.actif:
        replacement = QRToken.objects.filter(
            session=qr_token.session,
            actif=True,
        ).order_by('-created_at').first()
        if replacement and replacement.is_valid:
            qr_token = replacement
        else:
            return Response(
                {'code': 'TOKEN_EXPIRED', 'detail': 'QR code désactivé. Aucun QR actif pour cette séance.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    seance = qr_token.session
    if not seance:
        return Response({'code': 'NO_SESSION', 'detail': "Ce QR code n'est pas lié à une séance."}, status=status.HTTP_400_BAD_REQUEST)
    if seance.est_terminee:
        return Response(
            {'code': 'SESSION_TERMINATED', 'detail': 'La séance est terminée.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    formation = seance.module.formation

    if type_str == 'formateur':
        if not ModuleFormateur.objects.filter(module=seance.module, formateur=personne).exists():
            return Response({'code': 'NOT_IN_LIST', 'detail': "Vous n'êtes pas assigné(e) à ce module."}, status=status.HTTP_403_FORBIDDEN)
    elif type_str == 'encadrant':
        if seance.module.superviseur_id != personne.id:
            return Response({'code': 'NOT_IN_LIST', 'detail': "Vous n'êtes pas encadrant de ce module."}, status=status.HTTP_403_FORBIDDEN)
    else:
        if not ModuleParticipant.objects.filter(module=seance.module, participant=personne).exists():
            return Response({'code': 'NOT_IN_LIST', 'detail': "Vous n'êtes pas inscrit(e) à ce module."}, status=status.HTTP_403_FORBIDDEN)

    today = timezone.localdate()
    session_filter = _pointage_filter(personne, type_str, formation, date_journee=today)
    session_filter['session'] = seance
    pointage = Pointage.objects.filter(
        **session_filter, timestamp_sortie__isnull=True
    ).order_by('-timestamp_entree').first()
    if not pointage:
        return Response(
            {
                'code': 'NO_OPEN_SESSION',
                'detail': 'Aucune session ouverte à mettre à jour pour ce QR.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    latitude = data['latitude']
    longitude = data['longitude']
    accuracy_m = data.get('accuracy_m')
    battery_level = data.get('battery_level')
    is_charging = data.get('is_charging')

    geo_ok, geo_code, geo_detail, distance_m, rayon_m = _check_geofence(
        seance.module, latitude, longitude, accuracy_m
    )
    outside_limit = max(1, int(getattr(settings, 'MOBILE_GEOFENCE_OUTSIDE_CONFIRMATIONS', 2)))

    pointage.last_heartbeat_at = timezone.now()
    pointage.last_latitude = latitude
    pointage.last_longitude = longitude
    pointage.last_accuracy_m = accuracy_m
    pointage.last_battery_level = battery_level
    pointage.last_is_charging = is_charging
    if geo_ok:
        pointage.outside_geofence_count = 0
        if pointage.statut == Pointage.Statut.HORS_LIGNE_SUSPECT:
            pointage.statut = Pointage.Statut.EN_COURS
        pointage.save(
            update_fields=[
                'last_heartbeat_at',
                'last_latitude',
                'last_longitude',
                'last_accuracy_m',
                'last_battery_level',
                'last_is_charging',
                'outside_geofence_count',
                'statut',
                'updated_at',
            ]
        )
        _log_audit(
            action=AuditLog.Action.SCAN_HEARTBEAT,
            request=request,
            cible_type=type_str,
            cible_numero=getattr(personne, 'matricule', None) or getattr(personne, 'numerobadge', None) or '',
            cible_nom=(getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '') + ' ' + (getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or ''),
            formation=formation,
            pointage=pointage,
            device_id=device_id,
            extra={
                'distance_m': round(distance_m, 1) if distance_m is not None else None,
                'rayon_m': round(rayon_m, 1) if rayon_m is not None else None,
                'accuracy_m': accuracy_m,
                'battery_level': battery_level,
                'is_charging': is_charging,
            },
        )
        return Response(
            {
                'detail': 'Heartbeat enregistré.',
                'statut': pointage.statut,
                'outside_geofence_count': pointage.outside_geofence_count,
                'distance_m': round(distance_m, 1) if distance_m is not None else None,
                'rayon_m': round(rayon_m, 1) if rayon_m is not None else None,
            }
        )

    pointage.outside_geofence_count = (pointage.outside_geofence_count or 0) + 1
    if pointage.outside_geofence_count >= outside_limit:
        pointage.timestamp_sortie = _clamp_to_seance(timezone.now(), seance)
        pointage.statut = Pointage.Statut.SORTIE_AUTO
        pointage.calculer_duree()
        pointage.save(
            update_fields=[
                'timestamp_sortie',
                'statut',
                'duree_presence_minutes',
                'last_heartbeat_at',
                'last_latitude',
                'last_longitude',
                'last_accuracy_m',
                'last_battery_level',
                'last_is_charging',
                'outside_geofence_count',
                'updated_at',
            ]
        )
        extra = {
            'motif': 'OUT_OF_GEOFENCE',
            'distance_m': round(distance_m, 1) if distance_m is not None else None,
            'rayon_m': round(rayon_m, 1) if rayon_m is not None else None,
            'accuracy_m': accuracy_m,
            'battery_level': battery_level,
            'is_charging': is_charging,
            'outside_geofence_count': pointage.outside_geofence_count,
            'outside_geofence_limit': outside_limit,
        }
        _log_audit(
            action=AuditLog.Action.OUT_OF_GEOFENCE,
            request=request,
            cible_type=type_str,
            cible_numero=getattr(personne, 'matricule', None) or getattr(personne, 'numerobadge', None) or '',
            cible_nom=(getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '') + ' ' + (getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or ''),
            formation=formation,
            pointage=pointage,
            device_id=device_id,
            extra=extra,
        )
        _log_audit(
            action=AuditLog.Action.AUTO_EXIT,
            request=request,
            cible_type=type_str,
            cible_numero=getattr(personne, 'matricule', None) or getattr(personne, 'numerobadge', None) or '',
            cible_nom=(getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '') + ' ' + (getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or ''),
            formation=formation,
            pointage=pointage,
            device_id=device_id,
            extra=extra,
        )
        return Response(
            {
                'detail': 'Sortie automatique déclenchée (hors périmètre).',
                'action': 'SORTIE_AUTO',
                'statut': pointage.statut,
                'timestamp_sortie': pointage.timestamp_sortie,
                'duree_session_minutes': pointage.duree_presence_minutes,
                'motif': 'OUT_OF_GEOFENCE',
            }
        )

    pointage.statut = Pointage.Statut.HORS_LIGNE_SUSPECT
    pointage.save(
        update_fields=[
            'last_heartbeat_at',
            'last_latitude',
            'last_longitude',
            'last_accuracy_m',
            'last_battery_level',
            'last_is_charging',
            'outside_geofence_count',
            'statut',
            'updated_at',
        ]
    )

    _log_audit(
        action=AuditLog.Action.SCAN_HEARTBEAT,
        request=request,
        cible_type=type_str,
        cible_numero=getattr(personne, 'matricule', None) or getattr(personne, 'numerobadge', None) or '',
        cible_nom=(getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '') + ' ' + (getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or ''),
        formation=formation,
        pointage=pointage,
        device_id=device_id,
        extra={
            'geofence_code': geo_code,
            'geofence_detail': geo_detail,
            'distance_m': round(distance_m, 1) if distance_m is not None else None,
            'rayon_m': round(rayon_m, 1) if rayon_m is not None else None,
            'accuracy_m': accuracy_m,
            'battery_level': battery_level,
            'is_charging': is_charging,
            'outside_geofence_count': pointage.outside_geofence_count,
            'outside_geofence_limit': outside_limit,
        },
    )

    return Response(
        {
            'detail': geo_detail,
            'statut': pointage.statut,
            'outside_geofence_count': pointage.outside_geofence_count,
            'outside_geofence_limit': outside_limit,
            'distance_m': round(distance_m, 1) if distance_m is not None else None,
            'rayon_m': round(rayon_m, 1) if rayon_m is not None else None,
        },
        status=status.HTTP_202_ACCEPTED,
    )


# ──────────────────────────────────────────────
# Historique personnel (app mobile)
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_historique(request):
    """Historique des pointages du user connecté (participant, formateur ou encadrant)."""
    user = request.user
    if getattr(user, 'must_change_password', False):
        return _password_change_required_response()
    personne = None
    type_str = None

    try:
        personne = user.participant_profile
        type_str = 'participant'
    except (Participant.DoesNotExist, AttributeError):
        pass

    if personne is None:
        try:
            personne = user.formateur_profile
            type_str = 'formateur'
        except (Formateur.DoesNotExist, AttributeError):
            pass

    if personne is None and user.role == 'ENCADRANT':
        personne = user
        type_str = 'encadrant'

    if personne is None:
        return Response(
            {'detail': 'Aucun profil lié à ce compte.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if type_str == 'formateur':
        filt = {'formateur': personne}
    elif type_str == 'encadrant':
        filt = {'encadrant': personne}
    else:
        filt = {'participant': personne}
    pointages = Pointage.objects.filter(**filt).select_related('session__module__formation')

    data = []
    for pt in pointages:
        data.append({
            'id': pt.id,
            'formation_id': pt.session.module.formation_id,
            'formation_titre': pt.session.module.formation.formation,
            'date_journee': str(pt.date_journee),
            'timestamp_entree': pt.timestamp_entree.isoformat() if pt.timestamp_entree else None,
            'timestamp_sortie': pt.timestamp_sortie.isoformat() if pt.timestamp_sortie else None,
            'duree_presence_minutes': float(pt.duree_presence_minutes) if pt.duree_presence_minutes else None,
            'statut': pt.statut,
        })

    modules_data = _modules_for_personne(personne, type_str)
    pointages_qs = _pointages_queryset_for_personne(personne, type_str)
    stats = _compute_fiche_stats(pointages_qs)
    stats.update(_compute_volume_horaire_stats(modules_data, pointages_qs))

    return Response({
        'type_personne': type_str,
        'personne_id': personne.pk,
        'numero': (
            getattr(personne, 'matricule', None)
            or getattr(personne, 'numerobadge', None)
            or getattr(personne, 'numero', '')
        ),
        'nom': getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '',
        'prenom': getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or '',
        'pointages': data,
        'modules': modules_data,
        'stats': stats,
    })


def _module_fiche_payload(module, inscrit_le=None):
    site_label = module.site.nom if module.site_id else (module.site_legacy or '')
    return {
        'id': module.id,
        'formation_id': module.formation_id,
        'formation': module.formation.formation if module.formation_id else '',
        'module': module.intitule,
        'grade': module.grade or '',
        'groupe': module.groupe or '',
        'vague': module.vague or '',
        'site': site_label,
        'date_debut': str(module.date_debut) if module.date_debut else None,
        'date_fin': str(module.date_fin) if module.date_fin else None,
        'statut': module.statut,
        'secretariat_nom': module.secretariat.nom if module.secretariat_id else None,
        'inscrit_le': inscrit_le.isoformat() if inscrit_le else None,
        'duree_prevue_heures': float(module.duree_prevue_heures or 0),
    }


def _modules_for_personne(personne, type_str):
    modules_data = []
    if type_str == 'participant':
        inscriptions = (
            ModuleParticipant.objects.filter(participant=personne)
            .select_related('module__formation', 'module__secretariat', 'module__site')
            .order_by('-inscrit_le')
        )
        for ins in inscriptions:
            modules_data.append(_module_fiche_payload(ins.module, ins.inscrit_le))
    elif type_str == 'formateur':
        inscriptions = (
            ModuleFormateur.objects.filter(formateur=personne)
            .select_related('module__formation', 'module__secretariat', 'module__site')
            .order_by('-inscrit_le')
        )
        for ins in inscriptions:
            modules_data.append(_module_fiche_payload(ins.module, ins.inscrit_le))
    return modules_data


def _pointages_queryset_for_personne(personne, type_str):
    if type_str == 'formateur':
        return Pointage.objects.filter(formateur=personne)
    if type_str == 'encadrant':
        return Pointage.objects.filter(encadrant=personne)
    return Pointage.objects.filter(participant=personne)


def _compute_fiche_stats(pointages_qs):
    pointages = list(
        pointages_qs.select_related('session__module__formation').order_by('-timestamp_entree')
    )
    total_minutes = 0.0
    terminees = 0
    en_cours = 0
    a_verifier = 0
    dernier = None
    formations_ids = set()
    modules_ids = set()

    alert_statuts = {
        Pointage.Statut.HORS_LIGNE_SUSPECT,
        Pointage.Statut.ABSENT_NON_BADGE,
        Pointage.Statut.SORTIE_AUTO,
    }

    for pt in pointages:
        if pt.duree_presence_minutes is not None:
            total_minutes += float(pt.duree_presence_minutes)
        if pt.timestamp_sortie:
            terminees += 1
        elif pt.statut == Pointage.Statut.EN_COURS:
            en_cours += 1
        if pt.statut in alert_statuts or (
            pt.statut == Pointage.Statut.EN_COURS and not pt.timestamp_sortie
        ):
            a_verifier += 1
        if dernier is None or pt.timestamp_entree > dernier:
            dernier = pt.timestamp_entree
        if pt.session_id and pt.session.module_id:
            modules_ids.add(pt.session.module_id)
            if pt.session.module.formation_id:
                formations_ids.add(pt.session.module.formation_id)

    return {
        'nb_badgeages': len(pointages),
        'nb_seances_terminees': terminees,
        'nb_seances_en_cours': en_cours,
        'nb_a_verifier': a_verifier,
        'nb_sans_probleme': max(0, len(pointages) - a_verifier),
        'total_minutes_presence': round(total_minutes, 1),
        'nb_formations': len(formations_ids),
        'nb_modules_badges': len(modules_ids),
        'dernier_badgeage': dernier.isoformat() if dernier else None,
    }


def _compute_volume_horaire_stats(modules_data, pointages_qs):
    """Volume horaire effectué (présence badgeée) / total prévu (modules inscrits)."""
    module_cap_minutes = {}
    total_heures = 0.0
    for m in modules_data:
        mid = m.get('id')
        heures = float(m.get('duree_prevue_heures') or 0)
        total_heures += heures
        if mid is not None:
            module_cap_minutes[mid] = heures * 60

    module_accum = {mid: 0.0 for mid in module_cap_minutes}
    effectue_minutes = 0.0

    for pt in pointages_qs.select_related('session__module'):
        mins = float(pt.duree_presence_minutes or 0)
        if mins <= 0:
            continue
        mid = pt.session.module_id if pt.session_id else None
        if mid in module_cap_minutes:
            remaining = module_cap_minutes[mid] - module_accum[mid]
            if remaining <= 0:
                continue
            counted = min(mins, remaining)
            module_accum[mid] += counted
            effectue_minutes += counted
        else:
            effectue_minutes += mins

    effectue_heures = round(effectue_minutes / 60, 1)
    total_heures_r = round(total_heures, 1)
    taux = (
        round((effectue_heures / total_heures_r) * 100, 1)
        if total_heures_r > 0
        else 0.0
    )

    return {
        'volume_horaire_total_heures': total_heures_r,
        'volume_horaire_effectue_heures': effectue_heures,
        'volume_horaire_effectue_taux': taux,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_fiche(request):
    """Fiche personnelle mobile : profil, modules inscrits et statistiques de badgeage."""
    from authentication.serializers import UserSerializer

    user = request.user
    if getattr(user, 'must_change_password', False):
        return _password_change_required_response()

    personne, type_str, err = _resolve_authenticated_personne(user)
    if err:
        return err

    modules_data = _modules_for_personne(personne, type_str)
    pointages_qs = _pointages_queryset_for_personne(personne, type_str)
    stats = _compute_fiche_stats(pointages_qs)
    stats.update(_compute_volume_horaire_stats(modules_data, pointages_qs))
    stats['nb_modules_inscrits'] = len(modules_data)

    profil = {
        'type_personne': type_str,
        'numero': (
            getattr(personne, 'matricule', None)
            or getattr(personne, 'numerobadge', None)
            or getattr(user, 'matricule', None)
            or ''
        ),
        'nom': getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '',
        'prenom': getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or '',
    }
    if type_str == 'formateur':
        profil['specialite'] = getattr(personne, 'specialite', '') or ''

    return Response({
        'utilisateur': UserSerializer(user).data,
        'profil': profil,
        'modules': modules_data,
        'stats': stats,
    })


# ──────────────────────────────────────────────
# Gestion des liaisons appareils (superviseur / DFRC)
# ──────────────────────────────────────────────

@api_view(['DELETE'])
@permission_classes([IsDFRCOrEncadrant])
def unbind_device(request, device_id):
    """Superviseur / DFRC : délier un appareil pour permettre un changement de compte."""
    try:
        binding = DeviceBinding.objects.get(device_id=device_id, is_active=True)
        binding.is_active = False
        binding.save(update_fields=['is_active'])
        _log_audit(
            action=AuditLog.Action.DEVICE_UNBIND,
            request=request,
            cible_nom=binding.user.get_full_name() or binding.user.username,
            device_id=device_id,
            extra={'unbound_user_id': binding.user_id, 'device_info': binding.device_info},
        )
        return Response({'detail': f'Appareil délié de {binding.user.get_full_name()}.'})
    except DeviceBinding.DoesNotExist:
        return Response(
            {'detail': 'Aucune liaison active trouvée pour cet appareil.'},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(['GET'])
@permission_classes([IsDFRCOrEncadrant])
def list_device_bindings(request):
    """Liste toutes les liaisons appareils actives."""
    bindings = DeviceBinding.objects.filter(is_active=True).select_related('user')
    data = [{
        'device_id': b.device_id,
        'user_id': b.user_id,
        'username': b.user.username,
        'full_name': b.user.get_full_name(),
        'bound_at': b.bound_at.isoformat(),
        'device_info': b.device_info,
    } for b in bindings]
    return Response(data)


# ──────────────────────────────────────────────
# DFRC — Dashboard temps réel (polling)
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSecretariatOrEncadrantOrDFRC])
def formation_dashboard(request, pk):
    """Dashboard de suivi d'une formation (présents / absents / en salle) — participants + formateurs + encadrants."""
    formation = _get_accessible_formation(request.user, pk)
    if not formation:
        return Response(
            {'detail': 'Formation introuvable.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    _auto_manage_sessions(formation)

    date_str = request.GET.get('date')
    if date_str:
        try:
            from datetime import datetime as dt
            jour = dt.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            jour = timezone.localdate()
    else:
        jour = timezone.localdate()

    from collections import defaultdict
    from formations.models import SessionModule as SF
    now = timezone.now()

    # Filtre optionnel par séance
    session_id = request.GET.get('session_id')
    seance_selectionnee = None
    if session_id:
        try:
            seance_selectionnee = SF.objects.get(pk=session_id, module__formation=formation)
            jour = seance_selectionnee.date_journee
        except SF.DoesNotExist:
            seance_selectionnee = None

    pointages_qs = Pointage.objects.filter(
        session__module__formation=formation, date_journee=jour
    ).select_related('participant', 'formateur', 'encadrant', 'session')

    # Séances du jour (sert aussi à déterminer le périmètre module du dashboard)
    seances_jour = SF.objects.filter(
        module__formation=formation,
        date_journee=jour,
    ).order_by('heure_debut_prevue', 'numero')

    if seance_selectionnee:
        module_ids_scope = {seance_selectionnee.module_id}
    else:
        module_ids_scope = set(seances_jour.values_list('module_id', flat=True))

    if seance_selectionnee:
        from django.db.models import Q
        q = Q(session=seance_selectionnee)
        # Inclure aussi les pointages sans session liée dont l'heure d'entrée
        # tombe dans la plage horaire de la séance (forçage après fin de séance, QR sans session…)
        if seance_selectionnee.heure_debut_prevue and seance_selectionnee.heure_fin_prevue:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            tz = ZoneInfo('Africa/Abidjan')
            dt_debut = datetime.combine(seance_selectionnee.date_journee, seance_selectionnee.heure_debut_prevue, tzinfo=tz)
            dt_fin = datetime.combine(seance_selectionnee.date_journee, seance_selectionnee.heure_fin_prevue, tzinfo=tz)
            q |= Q(session__isnull=True, timestamp_entree__gte=dt_debut, timestamp_entree__lte=dt_fin)
        elif seance_selectionnee.demarree_le:
            # Pas d'horaire prévu : utiliser les horodatages réels de démarrage/fin
            q_null = Q(session__isnull=True, timestamp_entree__gte=seance_selectionnee.demarree_le)
            if seance_selectionnee.terminee_le:
                q_null &= Q(timestamp_entree__lte=seance_selectionnee.terminee_le)
            q |= q_null
        pointages_qs = pointages_qs.filter(q)

    pointages = list(pointages_qs)

    # Index sessions par (type, id)
    sessions_map = defaultdict(list)
    for pt in pointages:
        if pt.formateur_id:
            sessions_map[('formateur', pt.formateur_id)].append(pt)
        elif pt.encadrant_id:
            sessions_map[('encadrant', pt.encadrant_id)].append(pt)
        else:
            sessions_map[('participant', pt.participant_id)].append(pt)

    def _classify(personne, type_str, serializer_cls):
        key = (type_str, personne.id)
        sessions = sessions_map.get(key, [])
        p_data = serializer_cls(personne).data
        p_data['type_personne'] = type_str

        if not sessions:
            return 'absent', p_data

        # "Ouverte" = timestamp_sortie NULL
        session_ouverte = next(
            (s for s in sessions if s.timestamp_sortie is None), None
        )
        sessions_terminees = [s for s in sessions if s.timestamp_sortie is not None]
        # Exclure les pointages sans présence réelle (absent forcé, non badgé)
        sessions_presentes = [
            s for s in sessions_terminees
            if s.statut not in (Pointage.Statut.ABSENT_NON_BADGE,)
            and float(s.duree_presence_minutes or 0) > 0
        ]
        total_termine = sum(float(s.duree_presence_minutes or 0) for s in sessions_presentes)
        p_data['nb_sessions'] = len(sessions)

        if session_ouverte:
            duree_session = round(
                (now - session_ouverte.timestamp_entree).total_seconds() / 60, 2
            )
            p_data['timestamp_entree'] = session_ouverte.timestamp_entree
            p_data['duree_actuelle_minutes'] = round(total_termine + duree_session, 2)
            return 'en_salle', p_data
        elif sessions_presentes:
            derniere = max(sessions_presentes, key=lambda s: s.timestamp_sortie or s.timestamp_entree)
            p_data['timestamp_entree'] = sessions_presentes[0].timestamp_entree
            p_data['timestamp_sortie'] = derniere.timestamp_sortie
            p_data['duree_presence_minutes'] = round(total_termine, 2)
            return 'present', p_data
        else:
            return 'absent', p_data

    presents, en_salle, absents = [], [], []

    def _encadrant_data(enc):
        nom = (enc.last_name or '').strip()
        prenom = (enc.first_name or '').strip()
        if not nom and not prenom:
            nom = enc.username or ''
        return {
            'id': enc.id,
            'nom': nom,
            'prenom': prenom,
            'matricule': enc.matricule or '',
            'email': enc.email or '',
            'telephone': enc.telephone or '',
            'site': '',
            'grade': enc.grade or '',
        }

    class _InlineEncadrantSerializer:
        def __init__(self, obj):
            self.data = _encadrant_data(obj)

    # Participants (périmètre: modules du dashboard, pas toute la formation)
    seen_p = set()
    for insc in ModuleParticipant.objects.filter(module_id__in=module_ids_scope).select_related('participant'):
        if insc.participant_id in seen_p:
            continue
        seen_p.add(insc.participant_id)
        cat, data = _classify(insc.participant, 'participant', ParticipantSerializer)
        {'present': presents, 'en_salle': en_salle, 'absent': absents}[cat].append(data)

    # Formateurs (périmètre: modules du dashboard)
    seen_fmt = set()
    for insc in ModuleFormateur.objects.filter(module_id__in=module_ids_scope).select_related('formateur'):
        if insc.formateur_id in seen_fmt:
            continue
        seen_fmt.add(insc.formateur_id)
        cat, data = _classify(insc.formateur, 'formateur', FormateurSerializer)
        {'present': presents, 'en_salle': en_salle, 'absent': absents}[cat].append(data)

    # Encadrants (superviseurs de modules de la formation)
    seen_enc = set()
    # Inclure:
    # 1) les encadrants actuellement assignés à au moins un module de la formation
    # 2) les encadrants ayant déjà pointé sur la formation à la date demandée
    encadrants_qs = User.objects.filter(
        role='ENCADRANT',
    ).filter(
        Q(modules_supervises__id__in=module_ids_scope)
        | Q(
            pointages_encadrant__session__module_id__in=module_ids_scope,
            pointages_encadrant__date_journee=jour,
        )
    ).distinct()

    for enc in encadrants_qs:
        if enc.id in seen_enc:
            continue
        seen_enc.add(enc.id)
        cat, data = _classify(enc, 'encadrant', _InlineEncadrantSerializer)
        {'present': presents, 'en_salle': en_salle, 'absent': absents}[cat].append(data)

    # Séances du jour (pour le sélecteur frontend)
    seances_jour_data = [
        {
            'id': s.id,
            'numero': s.numero,
            'intitule': s.intitule or f'Séance {s.numero}',
            'heure_debut': s.heure_debut_prevue.strftime('%H:%M') if s.heure_debut_prevue else None,
            'heure_fin': s.heure_fin_prevue.strftime('%H:%M') if s.heure_fin_prevue else None,
            'en_cours': s.est_en_cours,
            'terminee': s.est_terminee,
        }
        for s in seances_jour
    ]

    nb_seances_jour = len(seances_jour_data) if seances_jour_data else 1

    nb_inscrits_participants = ModuleParticipant.objects.filter(module_id__in=module_ids_scope).values('participant').distinct().count()
    nb_inscrits_formateurs = ModuleFormateur.objects.filter(module_id__in=module_ids_scope).values('formateur').distinct().count()
    nb_inscrits_encadrants = encadrants_qs.count()
    nb_inscrits = nb_inscrits_participants + nb_inscrits_formateurs + nb_inscrits_encadrants

    # Si filtre séance : total attendus = inscrits, sinon inscrits × nb séances
    total = nb_inscrits if seance_selectionnee else nb_inscrits * nb_seances_jour

    total_pointes = sum(
        1 for pts in sessions_map.values()
        for pt in pts
        if pt.statut not in (Pointage.Statut.ABSENT_NON_BADGE,)
        and float(pt.duree_presence_minutes or 0) > 0
    )
    taux = round((total_pointes / total * 100), 1) if total > 0 else 0

    # Historique chronologique
    historique = []
    for pt in sorted(pointages, key=lambda p: p.timestamp_entree):
        personne = pt.formateur or pt.participant or pt.encadrant
        if personne:
            nom = (
                f"{getattr(personne, 'nom', '')} {getattr(personne, 'prenom', '')}".strip()
                or f"{getattr(personne, 'last_name', '')} {getattr(personne, 'first_name', '')}".strip()
                or getattr(personne, 'username', '—')
            )
        else:
            nom = '—'
        numero = (
            getattr(personne, 'numerobadge', None)
            or getattr(personne, 'matricule', None)
            or getattr(personne, 'numero', '—')
        ) if personne else '—'
        type_p = 'formateur' if pt.formateur_id else 'encadrant' if pt.encadrant_id else 'participant'
        historique.append({
            'nom': nom,
            'numero': numero,
            'type_personne': type_p,
            'action': 'ENTREE',
            'timestamp': pt.timestamp_entree,
            'statut': pt.statut,
        })
        if pt.timestamp_sortie:
            historique.append({
                'nom': nom,
                'numero': numero,
                'type_personne': type_p,
                'action': 'SORTIE',
                'timestamp': pt.timestamp_sortie,
                'duree_minutes': float(pt.duree_presence_minutes or 0),
                'statut': pt.statut,
            })
    historique.sort(key=lambda x: x['timestamp'])

    return Response({
        'formation': FormationListSerializer(formation).data,
        'presents': presents,
        'en_salle': en_salle,
        'absents': absents,
        'taux_presence': taux,
        'total_attendus': total,
        'total_pointes': total_pointes,
        'nb_inscrits': nb_inscrits,
        'nb_seances_jour': nb_seances_jour,
        'seances_jour': seances_jour_data,
        'seance_selectionnee_id': seance_selectionnee.id if seance_selectionnee else None,
        'historique': historique,
    })


# ──────────────────────────────────────────────
# DFRC — Liste des présences d'une formation
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSecretariatOrEncadrantOrDFRC])
def formation_presences(request, pk):
    """Liste des pointages d'une formation."""
    user = request.user
    formation = _get_accessible_formation(user, pk)
    if not formation:
        return Response(
            {'detail': 'Formation introuvable ou non autorisée.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    base_qs = Pointage.objects.filter(
        session__module__formation=formation,
    ).select_related('participant', 'formateur', 'encadrant', 'session__module__formation')

    if user.role == 'ENCADRANT':
        pointages = base_qs.filter(session__module__superviseur=user)
    elif user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT') and user.secretariat:
        pointages = base_qs.filter(session__module__secretariat=user.secretariat)
    else:
        pointages = base_qs

    serializer = PointageSerializer(pointages, many=True)
    return Response(serializer.data)


# ──────────────────────────────────────────────
# SUPERVISEUR / DFRC — Fermer session ouverte d'un participant
# ──────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSecretariatOrEncadrantOrDFRC])
def close_session(request, pk):
    """
    Secrétariat / Superviseur / DFRC : fermer la session ouverte d'un participant/formateur/encadrant
    qui a oublié de scanner sa sortie.
    body: { personne_id, type_personne }  (type_personne default: 'participant')
    """
    personne_id = request.data.get('personne_id')
    type_personne = request.data.get('type_personne', 'participant')

    if not personne_id:
        return Response({'detail': 'personne_id est requis.'}, status=status.HTTP_400_BAD_REQUEST)

    # Superviseur ne peut agir que sur sa formation
    formation = _get_accessible_formation(request.user, pk)
    if not formation:
        return Response({'detail': 'Formation introuvable ou non autorisée.'}, status=status.HTTP_404_NOT_FOUND)

    if type_personne == 'formateur':
        try:
            personne = Formateur.objects.get(pk=personne_id)
        except Formateur.DoesNotExist:
            return Response({'detail': 'Formateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        filt = {'session__module__formation': formation, 'formateur': personne, 'timestamp_sortie__isnull': True}
    elif type_personne == 'encadrant':
        try:
            personne = User.objects.get(pk=personne_id, role='ENCADRANT')
        except User.DoesNotExist:
            return Response({'detail': 'Encadrant introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        filt = {'session__module__formation': formation, 'encadrant': personne, 'timestamp_sortie__isnull': True}
    else:
        try:
            personne = Participant.objects.get(pk=personne_id)
        except Participant.DoesNotExist:
            return Response({'detail': 'Auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        filt = {'session__module__formation': formation, 'participant': personne, 'timestamp_sortie__isnull': True}

    try:
        pointage = Pointage.objects.filter(**filt).latest('timestamp_entree')
    except Pointage.DoesNotExist:
        return Response({'detail': 'Aucune session ouverte pour cette personne.'}, status=status.HTTP_400_BAD_REQUEST)

    pointage.timestamp_sortie = timezone.now()
    pointage.statut = Pointage.Statut.FORCE_DFRC
    pointage.calculer_duree()
    pointage.save()
    personne_label = (
        f"{getattr(personne, 'nom', '')} {getattr(personne, 'prenom', '')}".strip()
        or f"{getattr(personne, 'last_name', '')} {getattr(personne, 'first_name', '')}".strip()
        or getattr(personne, 'username', '—')
    )

    _log_audit(
        action=AuditLog.Action.CLOSE_SESSION,
        request=request,
        cible_type=type_personne,
        cible_numero=getattr(personne, 'numero', None) or getattr(personne, 'numerobadge', None) or getattr(personne, 'matricule', ''),
        cible_nom=personne_label,
        formation=formation,
        pointage=pointage,
        extra={'duree_minutes': float(pointage.duree_presence_minutes or 0)},
    )

    return Response({
        'detail': f'Session fermée pour {personne_label} ({round(float(pointage.duree_presence_minutes or 0))} min).',
        'pointage_id': pointage.id,
        'duree_minutes': float(pointage.duree_presence_minutes or 0),
    })


# ──────────────────────────────────────────────
# DFRC / SUPERVISEUR — Pointage forcé (R6)
# ──────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSecretariatOrEncadrantOrDFRC])
def force_pointage(request, pk):
    """Secrétariat / Superviseur / DFRC : forcer un pointage entrée ou sortie pour participant, formateur ou encadrant (R6)."""
    serializer = ForcePointageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    formation = _get_accessible_formation(request.user, pk)
    if not formation:
        return Response(
            {'detail': 'Formation introuvable ou non autorisée.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Jour cible : utiliser date_journee du body si fourni (forçage rétroactif), sinon aujourd'hui
    date_journee = data.get('date_journee') or timezone.localdate()

    type_str = data.get('type_personne', 'participant')
    if type_str == 'formateur':
        try:
            personne = Formateur.objects.get(pk=data['personne_id'])
        except Formateur.DoesNotExist:
            return Response({'detail': 'Formateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
    elif type_str == 'encadrant':
        try:
            personne = User.objects.get(pk=data['personne_id'], role='ENCADRANT')
        except User.DoesNotExist:
            return Response({'detail': 'Encadrant introuvable.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        try:
            personne = Participant.objects.get(pk=data['personne_id'])
        except Participant.DoesNotExist:
            return Response({'detail': 'Auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    if data['action'] == 'ENTREE':
        seance_qs = SessionModule.objects.filter(
            module__formation=formation,
            date_journee=date_journee,
            demarree_le__isnull=False,
            terminee_le__isnull=True,
        )
        module_id = data.get('module_id')
        if module_id:
            seance_qs = seance_qs.filter(module_id=module_id)
        if type_str == 'encadrant':
            seance_qs = seance_qs.filter(module__superviseur=personne)
        seance_active = seance_qs.first()
        if not seance_active:
            return Response({'detail': 'Aucune séance active pour ce module ce jour.'}, status=status.HTTP_400_BAD_REQUEST)
        if _has_unfinished_previous_session(seance_active):
            return Response(
                {
                    'detail': (
                        'Impossible de forcer un badgeage sur cette séance tant que '
                        'la séance précédente du même jour n’est pas terminée.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        pointage_ouvert = _find_open_pointage_same_module_day(
            personne=personne,
            type_personne=type_str,
            module=seance_active.module,
            date_journee=date_journee,
        )
        if pointage_ouvert:
            return Response(
                {'detail': 'Une session est déjà en cours sur ce module pour ce jour.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Timestamp fourni explicitement (rétroactif) ou calculé maintenant
        ts_entree_raw = data.get('timestamp_entree') or timezone.now()
        timestamp_entree = _clamp_to_seance(ts_entree_raw, seance_active)
        pointage = Pointage.objects.create(
            **_create_pointage_kwargs(
                personne, type_str, seance_active,
                date_journee=date_journee,
                timestamp_entree=timestamp_entree,
                statut=Pointage.Statut.FORCE_DFRC,
                device_id='FORCE_DFRC',
            )
        )
        _log_audit(
            action=AuditLog.Action.FORCE_ENTREE,
            request=request,
            cible_type=type_str,
            cible_numero=getattr(personne, 'numero', None) or getattr(personne, 'numerobadge', None) or getattr(personne, 'matricule', ''),
            cible_nom=(
                f"{getattr(personne, 'nom', '')} {getattr(personne, 'prenom', '')}".strip()
                or f"{getattr(personne, 'last_name', '')} {getattr(personne, 'first_name', '')}".strip()
                or getattr(personne, 'username', '—')
            ),
            formation=formation,
            pointage=pointage,
            extra={'acteur_role': request.user.role, 'motif': data.get('motif', '')},
        )
        return Response({
            'action': 'ENTREE',
            'detail': 'Entrée forcée enregistrée.',
            'pointage': PointageSerializer(pointage).data,
        }, status=status.HTTP_201_CREATED)

    elif data['action'] == 'SORTIE':
        filt_ouvert = _pointage_filter(personne, type_str, formation, date_journee=date_journee, timestamp_sortie__isnull=True)
        try:
            pointage = Pointage.objects.filter(**filt_ouvert).latest('timestamp_entree')
        except Pointage.DoesNotExist:
            return Response(
                {'detail': 'Aucune session ouverte pour cette personne ce jour.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ts_sortie_raw = data.get('timestamp_sortie') or timezone.now()
        pointage.timestamp_sortie = _clamp_to_seance(ts_sortie_raw, pointage.session)
        pointage.statut = Pointage.Statut.FORCE_DFRC
        pointage.calculer_duree()
        pointage.save()
        _log_audit(
            action=AuditLog.Action.FORCE_SORTIE,
            request=request,
            cible_type=type_str,
            cible_numero=getattr(personne, 'numero', None) or getattr(personne, 'numerobadge', None) or getattr(personne, 'matricule', ''),
            cible_nom=(
                f"{getattr(personne, 'nom', '')} {getattr(personne, 'prenom', '')}".strip()
                or f"{getattr(personne, 'last_name', '')} {getattr(personne, 'first_name', '')}".strip()
                or getattr(personne, 'username', '—')
            ),
            formation=formation,
            pointage=pointage,
            extra={'duree_minutes': float(pointage.duree_presence_minutes or 0), 'acteur_role': request.user.role, 'motif': data.get('motif', '')},
        )
        return Response({
            'action': 'SORTIE',
            'detail': 'Sortie forcée enregistrée.',
            'pointage': PointageSerializer(pointage).data,
        })


# ──────────────────────────────────────────────
# PARTICIPANT — Historique personnel
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def participant_historique(request, pk):
    """Historique des présences d'un participant."""
    if request.user.role != User.Role.AUDITEUR:
        return Response({'detail': 'Acces interdit.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        participant = request.user.participant_profile
    except Participant.DoesNotExist:
        return Response({'detail': 'Auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    if participant.id != pk:
        return Response({'detail': 'Acces interdit.'}, status=status.HTTP_403_FORBIDDEN)

    pointages = Pointage.objects.filter(
        participant=participant
    ).select_related('session__module__formation')
    serializer = PointageSerializer(pointages, many=True)
    return Response({
        'participant': ParticipantSerializer(participant).data,
        'pointages': serializer.data,
    })


# ──────────────────────────────────────────────
# PARTICIPANT — Lookup par numéro (pour app mobile R7)
# ──────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def formation_offline_data(request, token):
    """
    Retourne les données d'une formation nécessaires au badgeage hors ligne.
    Authentification par token QR (pas besoin de login).
    """
    try:
        qr_token = QRToken.objects.select_related('session__module__formation').get(token=token)
    except QRToken.DoesNotExist:
        return Response({'detail': 'Token invalide.'}, status=status.HTTP_404_NOT_FOUND)

    if qr_token.is_expired:
        return Response({'detail': 'Token expiré.'}, status=status.HTTP_400_BAD_REQUEST)

    # Si le token a été remplacé (regeneration QR), utiliser le token actif courant
    if not qr_token.actif:
        replacement = QRToken.objects.filter(
            session=qr_token.session,
            actif=True,
        ).order_by('-created_at').first()
        if replacement and replacement.is_valid:
            qr_token = replacement
        else:
            return Response({'detail': 'Token désactivé. Aucun QR actif pour cette séance.'}, status=status.HTTP_400_BAD_REQUEST)

    if not qr_token.session:
        return Response({'detail': 'Ce token n\'est pas lié à une séance.'}, status=status.HTTP_400_BAD_REQUEST)
    if qr_token.session.est_terminee:
        return Response({'detail': 'Token désactivé. Cette séance est terminée.'}, status=status.HTTP_400_BAD_REQUEST)
    formation = qr_token.session.module.formation

    participants = []
    seen_ids = set()
    for fp in ModuleParticipant.objects.filter(module__formation=formation).select_related('participant'):
        if fp.participant_id in seen_ids:
            continue
        seen_ids.add(fp.participant_id)
        p = fp.participant
        participants.append({'numero': p.matricule, 'nom': p.nom, 'prenom': p.prenom})

    formateurs = []
    seen_ff = set()
    for ff in ModuleFormateur.objects.filter(module__formation=formation).select_related('formateur'):
        if ff.formateur_id in seen_ff:
            continue
        seen_ff.add(ff.formateur_id)
        f = ff.formateur
        formateurs.append({'numero': f.numerobadge, 'nom': f.nom, 'prenom': f.prenom})

    encadrants = []
    seen_enc = set()
    for enc in User.objects.filter(
        role='ENCADRANT',
        modules_supervises__formation=formation,
    ).distinct():
        if enc.id in seen_enc:
            continue
        seen_enc.add(enc.id)
        encadrants.append({
            'numero': enc.matricule or '',
            'nom': enc.last_name or '',
            'prenom': enc.first_name or '',
            'username': enc.username,
        })

    module = getattr(qr_token.session, 'module', None) if qr_token.session else None
    site     = ((module.site.nom if getattr(module, 'site', None) else getattr(module, 'site_legacy', '')) if module else '')
    batiment = (module.batiment if module else '')
    salle    = (module.salle    if module else '')

    return Response({
        'formation': {
            'id': formation.id,
            'titre': formation.formation,
            'site': site,
            'batiment': batiment,
            'salle': salle,
        },
        'token': str(qr_token.token),
        'participants': participants,
        'formateurs': formateurs,
        'encadrants': encadrants,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def participant_lookup(request):
    """Recherche participant par numéro (R7 — pas besoin de compte)."""
    numero = request.query_params.get('numero', '')
    if not numero:
        return Response(
            {'detail': 'Paramètre "numero" requis.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.user.role != User.Role.AUDITEUR:
        return Response({'detail': 'Acces interdit.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        participant = request.user.participant_profile
    except Participant.DoesNotExist:
        return Response({'detail': 'Auditeur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    if participant.matricule != numero:
        return Response(
            {'detail': 'Auditeur introuvable.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(ParticipantSerializer(participant).data)


# ──────────────────────────────────────────────
# DFRC / ENCADRANT — Journal d'audit
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsDFRCOrEncadrant])
def audit_log_list(request):
    """
    Journal d'audit de toutes les actions critiques.
    Filtres disponibles (query params) :
      - formation_id : int
      - action       : code action (ex: FORCE_ENTREE)
      - acteur_id    : int (user qui a agi)
      - cible_numero : numéro participant/formateur
      - date_debut   : YYYY-MM-DD
      - date_fin     : YYYY-MM-DD
    """
    qs = AuditLog.objects.select_related('acteur', 'formation', 'pointage').order_by('-timestamp')

    formation_id = request.query_params.get('formation_id')
    if formation_id:
        qs = qs.filter(formation_id=formation_id)

    action = request.query_params.get('action')
    if action:
        qs = qs.filter(action=action)

    acteur_id = request.query_params.get('acteur_id')
    if acteur_id:
        qs = qs.filter(acteur_id=acteur_id)

    cible_numero = request.query_params.get('cible_numero')
    if cible_numero:
        qs = qs.filter(cible_numero__icontains=cible_numero)

    date_debut = request.query_params.get('date_debut')
    if date_debut:
        qs = qs.filter(timestamp__date__gte=date_debut)

    date_fin = request.query_params.get('date_fin')
    if date_fin:
        qs = qs.filter(timestamp__date__lte=date_fin)

    # Encadrant : restreindre aux formations dont il est superviseur
    if request.user.role == 'ENCADRANT':
        qs = qs.filter(formation__modules__superviseur=request.user)

    data = []
    for log in qs[:500]:
        data.append({
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'action': log.action,
            'action_label': log.get_action_display(),
            'acteur_id': log.acteur_id,
            'acteur_label': log.acteur_label or 'Anonyme',
            'acteur_role': log.acteur.role if log.acteur else None,
            'cible_type': log.cible_type,
            'cible_numero': log.cible_numero,
            'cible_nom': log.cible_nom,
            'formation_id': log.formation_id,
            'formation_titre': log.formation_titre,
            'pointage_id': log.pointage_id,
            'ip_address': log.ip_address,
            'device_id': log.device_id,
            'extra': log.extra,
        })

    return Response({'count': len(data), 'results': data})


# ──────────────────────────────────────────────
# Vérification statut badgeage sécurisé (app mobile, authentifié)
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secure_check_badge_status(request):
    """
    Indique si le prochain scan de l'utilisateur authentifié sera une ENTREE ou
    une SORTIE pour le QR donné (ou s'il a déjà terminé cette séance).

    GET ?token_qr=<uuid>
    Retour : { statut: 'ABSENT'|'EN_SALLE'|'TERMINE'|'INCONNU',
               action_suivante: 'ENTREE'|'SORTIE'|null,
               heure_entree: 'HH:MM'|null,
               seance_intitule: str|null }
    """
    token_qr = request.GET.get('token_qr', '').strip()
    if not token_qr:
        return Response(
            {'code': 'MISSING_TOKEN', 'detail': 'token_qr requis.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user
    if getattr(user, 'must_change_password', False):
        return _password_change_required_response()

    personne, type_str, err = _resolve_authenticated_personne(user)
    if err:
        return err

    try:
        qr_token = QRToken.objects.select_related('session__module__formation').get(
            token=token_qr,
        )
    except (QRToken.DoesNotExist, ValueError):
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    if not qr_token.is_valid and qr_token.actif:
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    # QR remplacé mais valide : suivre le remplaçant
    if not qr_token.actif:
        replacement = QRToken.objects.filter(
            session=qr_token.session, actif=True,
        ).order_by('-created_at').first()
        if replacement and replacement.is_valid:
            qr_token = replacement
        else:
            return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    seance = qr_token.session
    if not seance:
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    formation = seance.module.formation
    today = timezone.localdate()
    session_filter = _pointage_filter(personne, type_str, formation, date_journee=today)
    session_filter['session'] = seance

    seance_label = seance.intitule or f'Séance {seance.numero}'

    # Informations de géofence pour permettre au client d'afficher la position.
    module = seance.module
    site_lat, site_lon, site_rayon = _resolve_site_geofence(module)
    geofence_info = {
        'geofence_configured': site_lat is not None and site_lon is not None,
        'geofence_latitude': float(site_lat) if site_lat is not None else None,
        'geofence_longitude': float(site_lon) if site_lon is not None else None,
        'geofence_rayon_m': float(site_rayon) if site_rayon is not None else None,
        'distance_m': None,
        'in_geofence': None,
        'accuracy_ok': None,
        'accuracy_max_m': float(getattr(settings, 'MOBILE_GEOFENCE_MAX_ACCURACY_M', 80)),
    }

    # Si le client envoie sa position, calculer la distance et l'état geofence.
    lat_raw = request.GET.get('latitude')
    lon_raw = request.GET.get('longitude')
    acc_raw = request.GET.get('accuracy_m')
    try:
        lat = float(lat_raw) if lat_raw not in (None, '') else None
        lon = float(lon_raw) if lon_raw not in (None, '') else None
        acc = float(acc_raw) if acc_raw not in (None, '') else None
    except (TypeError, ValueError):
        lat = lon = acc = None

    if lat is not None and lon is not None and geofence_info['geofence_configured']:
        distance = _distance_meters(lat, lon, site_lat, site_lon)
        geofence_info['distance_m'] = round(distance, 1)
        geofence_info['in_geofence'] = distance <= geofence_info['geofence_rayon_m']

    if acc is not None:
        geofence_info['accuracy_ok'] = acc <= geofence_info['accuracy_max_m']

    pointage_ouvert = Pointage.objects.filter(
        **session_filter, timestamp_sortie__isnull=True,
    ).order_by('-timestamp_entree').first()
    if pointage_ouvert:
        heure = timezone.localtime(pointage_ouvert.timestamp_entree).strftime('%H:%M')
        return Response({
            'statut': 'EN_SALLE',
            'action_suivante': 'SORTIE',
            'heure_entree': heure,
            'seance_intitule': seance_label,
            **geofence_info,
        })

    pointage_termine = Pointage.objects.filter(
        **session_filter, timestamp_sortie__isnull=False,
    ).exists()
    if pointage_termine:
        return Response({
            'statut': 'TERMINE',
            'action_suivante': None,
            'heure_entree': None,
            'seance_intitule': seance_label,
            **geofence_info,
        })

    return Response({
        'statut': 'ABSENT',
        'action_suivante': 'ENTREE',
        'heure_entree': None,
        'seance_intitule': seance_label,
        **geofence_info,
    })


# ──────────────────────────────────────────────
# Vérification statut badgeage avant confirmation (endpoint public)
# ──────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def check_badge_status(request):
    """
    Vérifie l'état actuel du badgeage pour un participant/formateur/encadrant sur un token QR.
    GET ?token_qr=<uuid>&numero=<matricule>
    Retourne : { statut: 'ABSENT'|'EN_SALLE'|'TERMINE', action_suivante: 'ENTREE'|'SORTIE'|null,
                 nom, prenom, timestamp_entree, heure_entree }
    Endpoint public (lecture seule, pas de mutation).
    """
    token_qr = request.GET.get('token_qr', '').strip()
    numero = request.GET.get('numero', '').strip()

    if not token_qr or not numero:
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    try:
        qr_token = QRToken.objects.select_related('session__module__formation').get(token=token_qr)
    except QRToken.DoesNotExist:
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    if not qr_token.is_valid:
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    if not qr_token.session:
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})
    formation = qr_token.session.module.formation
    today = timezone.localdate()

    personne, type_str, _, err = _resolve_personne(numero, formation, qr_token.session.module)
    if err:
        return Response({'statut': 'INCONNU', 'action_suivante': 'ENTREE'})

    seance = qr_token.session
    session_filter = _pointage_filter(personne, type_str, formation, date_journee=today)
    session_filter['session'] = seance

    pointage_ouvert = Pointage.objects.filter(
        **session_filter, timestamp_sortie__isnull=True,
    ).order_by('-timestamp_entree').first()

    if pointage_ouvert:
        heure = timezone.localtime(pointage_ouvert.timestamp_entree).strftime('%H:%M')
        return Response({
            'statut': 'EN_SALLE',
            'action_suivante': 'SORTIE',
            'type_personne': type_str,
            'nom': getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '',
            'prenom': getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or '',
            'heure_entree': heure,
        })

    pointage_termine = Pointage.objects.filter(
        **session_filter, timestamp_sortie__isnull=False,
    ).exists()

    if pointage_termine:
        return Response({
            'statut': 'TERMINE',
            'action_suivante': None,
            'type_personne': type_str,
            'nom': getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '',
            'prenom': getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or '',
        })

    return Response({
        'statut': 'ABSENT',
        'action_suivante': 'ENTREE',
        'type_personne': type_str,
        'nom': getattr(personne, 'nom', None) or getattr(personne, 'last_name', '') or '',
        'prenom': getattr(personne, 'prenom', None) or getattr(personne, 'first_name', '') or '',
    })
