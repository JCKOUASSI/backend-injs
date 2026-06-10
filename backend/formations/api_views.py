"""
API views for the React frontend.
These views complement the existing DRF views with additional endpoints
needed for the frontend dashboard.
"""
from io import BytesIO
from datetime import timedelta, datetime, time, date
import calendar
import re
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, F
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from authentication.permissions import IsSecretariat, IsSecretariatOrDFRC, CanManageModuleParticipant
from formations.models import Secretariat
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from presences.models import Pointage, SessionModule as PresenceSessionModule, AuditLog, _log_audit

from .models import (
    Formation, Participant, Formateur, QRToken, SessionModule, ModuleParticipant,
    ModuleFormateur, RefFormation, RefModule, RefSite, RefBatiment, RefSalle,
    RefCategorie, RefGrade, RefTypeSecretariat, RefVague, Module, FinanceSettings,
    FinanceAjustement,
)
FormationParticipant = ModuleParticipant
FormationFormateur = ModuleFormateur
from .formateur_privacy import (
    can_view_formateur_sensitive_data,
    can_edit_formateur_sensitive_data,
    formateur_sensitive_payload,
)
from .serializers import (
    FormationListSerializer,
    FormationDetailSerializer,
    ParticipantSerializer,
    FormateurSerializer,
    ModuleSerializer,
)
from .period_filter import parse_period_from_request, periode_api_payload


def _normalize_groupe_value(value):
    """Normalise les variantes de groupe (1, 01, GROUPE 1) vers GROUPE N."""
    raw = str(value or '').strip()
    if not raw:
        return ''
    compact = re.sub(r'\s+', ' ', raw).strip()
    match = re.fullmatch(r'(?:GROUPE\s*)?0*(\d+)', compact, flags=re.IGNORECASE)
    if match:
        return f"GROUPE {int(match.group(1))}"
    return compact.upper()


def _groupe_sort_key(value):
    match = re.fullmatch(r'GROUPE (\d+)', value)
    if match:
        return (0, int(match.group(1)))
    return (1, value)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Return dashboard statistics, scoped by secretariat for SECRETARIAT role."""
    modules_qs = Module.objects.all()
    participants_qs = Participant.objects.all()
    secretariat_filter = request.query_params.get('secretariat')
    reference_date_raw = request.query_params.get('reference_date')

    if request.user.is_authenticated and request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        sec = request.user.secretariat
        modules_qs = modules_qs.filter(secretariat=sec)
        participants_qs = participants_qs.filter(secretariat=sec)
    elif request.user.is_authenticated and request.user.role == 'ENCADRANT':
        modules_qs = modules_qs.filter(superviseur=request.user)
        fp_ids = ModuleParticipant.objects.filter(module__superviseur=request.user).values_list('participant_id', flat=True)
        participants_qs = participants_qs.filter(id__in=fp_ids).distinct()
    elif request.user.is_authenticated and request.user.role in ('CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'DIRECTION') and secretariat_filter:
        modules_qs = modules_qs.filter(secretariat_id=secretariat_filter)
        participants_qs = participants_qs.filter(secretariat_id=secretariat_filter)

    today = timezone.localdate()
    if reference_date_raw:
        try:
            today = datetime.strptime(reference_date_raw, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': 'Format de date invalide. Utilisez YYYY-MM-DD pour reference_date.'},
                status=400,
            )

    total_formations = modules_qs.count()
    formations_actives = modules_qs.filter(statut='EN_COURS').count()
    formations_terminees = modules_qs.filter(statut='TERMINEE').count()
    formations_planifiees = modules_qs.filter(statut='PLANIFIEE').count()
    groupes_en_cours = modules_qs.filter(statut='EN_COURS', groupe__isnull=False).exclude(groupe='').values('groupe').distinct().count()
    total_participants = participants_qs.count()

    from .volume_horaire import compute_dashboard_volume_horaire

    period = parse_period_from_request(request)
    if period['error']:
        return Response({'detail': period['detail']}, status=400)

    volume_horaire_effectue_heures, volume_horaire_total_heures, volume_horaire_effectue_taux = (
        compute_dashboard_volume_horaire(
            modules_qs,
            date_debut=period['date_debut'],
            date_fin=period['date_fin'],
        )
    )

    formateurs_qs = Formateur.objects.all()
    if request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        sec = request.user.secretariat
        formateurs_qs = formateurs_qs.filter(secretariats=sec)
    elif request.user.role == 'ENCADRANT':
        formateurs_qs = formateurs_qs.filter(modules_assignes__module__in=modules_qs).distinct()
    total_formateurs = formateurs_qs.count()

    seances_actives = PresenceSessionModule.objects.filter(
        module__in=modules_qs, demarree_le__isnull=False, terminee_le__isnull=True
    ).count()
    seances_planifiees_aujourd_hui = PresenceSessionModule.objects.filter(
        module__in=modules_qs,
        module__statut__in=['PLANIFIEE', 'EN_COURS'],
        date_journee=today,
        demarree_le__isnull=True,
    ).count()
    pointages_aujourd_hui = Pointage.objects.filter(
        session__module__in=modules_qs, date_journee=today
    ).count()
    pointages_ouverts = Pointage.objects.filter(
        session__module__in=modules_qs,
        date_journee=today,
        timestamp_sortie__isnull=True,
        timestamp_entree__isnull=False,
    )
    en_salle_now = (
        pointages_ouverts.filter(participant__isnull=False).values('participant').distinct().count()
        + pointages_ouverts.filter(formateur__isnull=False).values('formateur').distinct().count()
    )

    # Les indicateurs présence/absence du jour sont calculés sur les modules ayant
    # une séance aujourd'hui, qu'ils soient EN_COURS ou PLANIFIEE (première séance du jour).
    modules_avec_seance_aujourd_hui = modules_qs.filter(
        statut__in=['EN_COURS', 'PLANIFIEE'],
        sessions__date_journee=today,
    ).distinct()
    participants_attendus_jour = ModuleParticipant.objects.filter(
        module__in=modules_avec_seance_aujourd_hui
    ).values('participant').distinct().count()
    formateurs_attendus_jour = ModuleFormateur.objects.filter(
        module__in=modules_avec_seance_aujourd_hui
    ).values('formateur').distinct().count()
    total_attendus_jour = participants_attendus_jour + formateurs_attendus_jour

    participants_pointes = Pointage.objects.filter(
        session__module__in=modules_avec_seance_aujourd_hui,
        date_journee=today,
        participant__isnull=False,
    ).values('participant').distinct().count()
    formateurs_pointes = Pointage.objects.filter(
        session__module__in=modules_avec_seance_aujourd_hui,
        date_journee=today,
        formateur__isnull=False,
    ).values('formateur').distinct().count()
    presents_aujourd_hui = participants_pointes + formateurs_pointes

    absents_aujourd_hui = max(total_attendus_jour - presents_aujourd_hui, 0)
    taux_presence = round((presents_aujourd_hui / total_attendus_jour * 100), 1) if total_attendus_jour > 0 else 0
    taux_absence = round(100 - taux_presence, 1) if total_attendus_jour > 0 else 0

    # Indicateurs agrégés semaine / mois (même périmètre : modules EN_COURS)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    modules_avec_seance_semaine = modules_qs.filter(
        statut__in=['EN_COURS', 'PLANIFIEE'],
        sessions__date_journee__range=(week_start, week_end),
    ).distinct()
    participants_attendus_semaine = ModuleParticipant.objects.filter(
        module__in=modules_avec_seance_semaine
    ).values('participant').distinct().count()
    formateurs_attendus_semaine = ModuleFormateur.objects.filter(
        module__in=modules_avec_seance_semaine
    ).values('formateur').distinct().count()
    total_attendus_semaine = participants_attendus_semaine + formateurs_attendus_semaine
    participants_presents_semaine = Pointage.objects.filter(
        session__module__in=modules_avec_seance_semaine,
        date_journee__range=(week_start, week_end),
        participant__isnull=False,
    ).values('participant').distinct().count()
    formateurs_presents_semaine = Pointage.objects.filter(
        session__module__in=modules_avec_seance_semaine,
        date_journee__range=(week_start, week_end),
        formateur__isnull=False,
    ).values('formateur').distinct().count()
    presents_semaine = participants_presents_semaine + formateurs_presents_semaine
    taux_presence_semaine = round((presents_semaine / total_attendus_semaine * 100), 1) if total_attendus_semaine > 0 else 0

    modules_avec_seance_mois = modules_qs.filter(
        statut__in=['EN_COURS', 'PLANIFIEE'],
        sessions__date_journee__range=(month_start, today),
    ).distinct()
    participants_attendus_mois = ModuleParticipant.objects.filter(
        module__in=modules_avec_seance_mois
    ).values('participant').distinct().count()
    formateurs_attendus_mois = ModuleFormateur.objects.filter(
        module__in=modules_avec_seance_mois
    ).values('formateur').distinct().count()
    total_attendus_mois = participants_attendus_mois + formateurs_attendus_mois
    participants_presents_mois = Pointage.objects.filter(
        session__module__in=modules_avec_seance_mois,
        date_journee__range=(month_start, today),
        participant__isnull=False,
    ).values('participant').distinct().count()
    formateurs_presents_mois = Pointage.objects.filter(
        session__module__in=modules_avec_seance_mois,
        date_journee__range=(month_start, today),
        formateur__isnull=False,
    ).values('formateur').distinct().count()
    presents_mois = participants_presents_mois + formateurs_presents_mois
    taux_presence_mois = round((presents_mois / total_attendus_mois * 100), 1) if total_attendus_mois > 0 else 0

    modules_avec_seance_annee = modules_qs.filter(
        statut__in=['EN_COURS', 'PLANIFIEE'],
        sessions__date_journee__range=(year_start, today),
    ).distinct()
    participants_attendus_annee = ModuleParticipant.objects.filter(
        module__in=modules_avec_seance_annee
    ).values('participant').distinct().count()
    formateurs_attendus_annee = ModuleFormateur.objects.filter(
        module__in=modules_avec_seance_annee
    ).values('formateur').distinct().count()
    total_attendus_annee = participants_attendus_annee + formateurs_attendus_annee
    participants_presents_annee = Pointage.objects.filter(
        session__module__in=modules_avec_seance_annee,
        date_journee__range=(year_start, today),
        participant__isnull=False,
    ).values('participant').distinct().count()
    formateurs_presents_annee = Pointage.objects.filter(
        session__module__in=modules_avec_seance_annee,
        date_journee__range=(year_start, today),
        formateur__isnull=False,
    ).values('formateur').distinct().count()
    presents_annee = participants_presents_annee + formateurs_presents_annee
    taux_presence_annee = round((presents_annee / total_attendus_annee * 100), 1) if total_attendus_annee > 0 else 0

    # Retard moyen d'arrivée (minutes positives uniquement)
    retards = []
    current_tz = timezone.get_current_timezone()
    pointages_scope_today = Pointage.objects.filter(
        session__module__in=modules_avec_seance_aujourd_hui,
        date_journee=today,
    ).select_related('session').exclude(timestamp_entree__isnull=True)
    for pt in pointages_scope_today:
        if not pt.session or not pt.session.heure_debut_prevue:
            continue
        start_dt = timezone.make_aware(
            datetime.combine(pt.date_journee, pt.session.heure_debut_prevue),
            current_tz,
        )
        delay_minutes = (pt.timestamp_entree - start_dt).total_seconds() / 60
        if delay_minutes > 0:
            retards.append(delay_minutes)
    retard_moyen_minutes = round(sum(retards) / len(retards), 1) if retards else 0

    derniers_pointages = []
    for pt in Pointage.objects.filter(
        session__module__in=modules_qs,
        timestamp_entree__isnull=False,
    ).select_related('participant', 'formateur', 'encadrant', 'session__module').order_by('-timestamp_entree')[:8]:
        if pt.formateur_id:
            personne = pt.formateur
            type_personne = 'formateur'
        elif pt.encadrant_id:
            personne = pt.encadrant
            type_personne = 'encadrant'
        else:
            personne = pt.participant
            type_personne = 'participant'

        nom = '—'
        if personne:
            nom = (
                f"{getattr(personne, 'nom', '')} {getattr(personne, 'prenom', '')}".strip()
                or f"{getattr(personne, 'last_name', '')} {getattr(personne, 'first_name', '')}".strip()
                or getattr(personne, 'username', '')
                or '—'
            )
        derniers_pointages.append({
            'nom': nom,
            'matricule': (
                getattr(personne, 'numerobadge', None)
                or getattr(personne, 'matricule', None)
                or getattr(personne, 'numero', None)
                or '—'
            ),
            'type': type_personne,
            'module': pt.session.module.intitule or '',
            'date': pt.date_journee,
            'heure_entree': pt.timestamp_entree,
            'heure_sortie': pt.timestamp_sortie,
        })

    prochaines_seances = []
    now_local = timezone.localtime(timezone.now())
    midi = time(12, 0)
    tomorrow = today + timedelta(days=1)

    # Règle dashboard:
    # - Le matin: montrer les séances d'après-midi/soir du jour.
    # - La veille (après-midi/soir): montrer les séances du matin du lendemain.
    if now_local.time() < midi:
        prochaines_qs = PresenceSessionModule.objects.filter(
            module__in=modules_qs,
            date_journee=today,
            demarree_le__isnull=True,
        ).filter(
            Q(heure_debut_prevue__gte=midi) | Q(heure_debut_prevue__isnull=True)
        )
    else:
        prochaines_qs = PresenceSessionModule.objects.filter(
            module__in=modules_qs,
            date_journee=tomorrow,
            demarree_le__isnull=True,
        ).filter(
            Q(heure_debut_prevue__lt=midi) | Q(heure_debut_prevue__isnull=True)
        )

    prochaines_qs = prochaines_qs.select_related(
        'module', 'module__formation'
    ).order_by('date_journee', 'heure_debut_prevue', 'numero')

    # Fallback: si aucune séance ne correspond à la règle, prendre les plus proches.
    if not prochaines_qs.exists():
        prochaines_qs = PresenceSessionModule.objects.filter(
            module__in=modules_qs,
            date_journee__gte=today,
            demarree_le__isnull=True,
        ).select_related('module', 'module__formation').order_by(
            'date_journee', 'heure_debut_prevue', 'numero'
        )[:10]
    for sess in prochaines_qs:
        label = sess.intitule or f"Séance {sess.numero}"
        prochaines_seances.append({
            'session_id': sess.id,
            'module_id': sess.module_id,
            'formation_id': sess.module.formation_id,
            'module': sess.module.intitule,
            'formation': sess.module.formation.formation if sess.module.formation else '',
            'session_label': label,
            'date_journee': sess.date_journee,
            'heure_debut_prevue': sess.heure_debut_prevue,
        })

    return Response({
        'total_modules': total_formations,
        'modules_en_cours': formations_actives,
        'modules_termines': formations_terminees,
        'modules_planifies': formations_planifiees,
        'groupes_en_cours': groupes_en_cours,
        'total_participants': total_participants,
        'volume_horaire_total_heures': volume_horaire_total_heures,
        'volume_horaire_effectue_heures': volume_horaire_effectue_heures,
        'volume_horaire_effectue_taux': volume_horaire_effectue_taux,
        'periode': periode_api_payload(period['date_debut'], period['date_fin'], period['meta']),
        'total_formateurs': total_formateurs,
        'seances_actives': seances_actives,
        'seances_planifiees_aujourd_hui': seances_planifiees_aujourd_hui,
        'pointages_aujourd_hui': pointages_aujourd_hui,
        'en_salle_now': en_salle_now,
        'auditeurs_attendus_jour': participants_attendus_jour,
        'auditeurs_presents_jour': participants_pointes,
        'formateurs_attendus_jour': formateurs_attendus_jour,
        'formateurs_presents_jour': formateurs_pointes,
        'total_attendus_jour': total_attendus_jour,
        'presents_aujourd_hui': presents_aujourd_hui,
        'absents_aujourd_hui': absents_aujourd_hui,
        'taux_presence': taux_presence,
        'taux_absence': taux_absence,
        'total_attendus_semaine': total_attendus_semaine,
        'presents_semaine': presents_semaine,
        'taux_presence_semaine': taux_presence_semaine,
        'total_attendus_mois': total_attendus_mois,
        'presents_mois': presents_mois,
        'taux_presence_mois': taux_presence_mois,
        'total_attendus_annee': total_attendus_annee,
        'presents_annee': presents_annee,
        'taux_presence_annee': taux_presence_annee,
        'retard_moyen_minutes': retard_moyen_minutes,
        'prochaines_seances': prochaines_seances,
        'derniers_pointages': derniers_pointages,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def formation_list_api(request):
    """
    List modules (une ligne par module) with optional filtering.
    Query params: statut, search, module, categorie, grade, secretariat_type, vague, groupe, actives, page, page_size, date_mode, date
    """
    from presences.models import Pointage
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 50))

    queryset = Module.objects.select_related(
        'formation', 'secretariat__type', 'formateur', 'superviseur', 'creee_par'
    )

    # Restriction par rôle
    if request.user.is_authenticated and request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        if request.user.secretariat:
            queryset = queryset.filter(secretariat=request.user.secretariat)
        else:
            queryset = queryset.none()
    elif request.user.is_authenticated and request.user.role == 'ENCADRANT':
        queryset = queryset.filter(superviseur=request.user)

    # Filtres
    statut = request.query_params.get('statut')
    if statut:
        queryset = queryset.filter(statut=statut)

    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(intitule__icontains=search) | Q(formation__formation__icontains=search)
        ).distinct()

    module_filter = request.query_params.get('module')
    if module_filter:
        queryset = queryset.filter(intitule__icontains=module_filter)

    categorie = request.query_params.get('categorie')
    if categorie:
        queryset = queryset.filter(grade__istartswith=categorie)

    grade_param = (request.query_params.get('grade') or '').strip()
    if grade_param:
        queryset = queryset.filter(grade__iexact=grade_param)

    secretariat_type = request.query_params.get('secretariat_type')
    if secretariat_type:
        queryset = queryset.filter(secretariat__type_id=secretariat_type)

    secretariat_id = request.query_params.get('secretariat')
    if secretariat_id and request.user.role in ('CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'DIRECTION'):
        queryset = queryset.filter(secretariat_id=secretariat_id)

    vague_filter = request.query_params.get('vague')
    if vague_filter:
        queryset = queryset.filter(vague__iexact=vague_filter)

    groupe_param = request.query_params.get('groupe')
    if groupe_param:
        groupe_normalise = _normalize_groupe_value(groupe_param)
        if groupe_normalise:
            matching_ids = [
                mid
                for mid, g in queryset.values_list('id', 'groupe')
                if _normalize_groupe_value(g) == groupe_normalise
            ]
            queryset = queryset.filter(id__in=matching_ids)

    actives_only = request.query_params.get('actives')
    if actives_only == 'true':
        queryset = queryset.filter(statut__in=['PLANIFIEE', 'EN_COURS'])

    seance_en_cours_only = request.query_params.get('seance_en_cours')
    if seance_en_cours_only == 'true':
        queryset = queryset.filter(
            sessions__demarree_le__isnull=False,
            sessions__terminee_le__isnull=True,
        ).distinct()

    date_mode = request.query_params.get('date_mode')
    date_value = request.query_params.get('date')
    if date_mode in ('today', 'date'):
        target_date = timezone.localdate()
        if date_mode == 'date':
            if not date_value:
                return Response({'detail': 'Le paramètre date est requis pour date_mode=date.'}, status=400)
            try:
                target_date = datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                return Response({'detail': 'Format de date invalide. Utilisez YYYY-MM-DD.'}, status=400)
        queryset = queryset.filter(sessions__date_journee=target_date).distinct()

    # Tri : modules les plus proches d'abord, dates vides en dernier
    queryset = queryset.order_by(
        F('date_debut').asc(nulls_last=True),
        F('date_fin').asc(nulls_last=True),
        'id',
    )

    # Pagination
    total_count = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    modules_page = queryset[start:end]

    today = timezone.localdate()
    results = []
    for m in modules_page:
        f = m.formation
        nb_p = ModuleParticipant.objects.filter(module=m).count()
        nb_presents = (
            Pointage.objects
            .filter(session__module=m, date_journee=today, participant__isnull=False)
            .values('participant').distinct().count()
        )
        superviseur = m.superviseur
        creee_par = m.creee_par
        results.append({
            'id': f.id,
            'module_id': m.id,
            'numero_formation': f.numero_formation,
            'formation': f.formation,
            'intitule': f.formation,
            'module': m.intitule,
            'statut': m.statut,
            'grade': m.grade,
            'categorie': m.grade,
            'groupe': m.groupe,
            'vague': m.vague,
            'site': (m.site.nom if m.site else (m.site_legacy or '')),
            'site_id': m.site_id,
            'batiment': m.batiment,
            'salle': m.salle,
            'date_debut': m.date_debut,
            'date_fin': m.date_fin,
            'date_debut_prevue': m.date_debut,
            'date_fin_prevue': m.date_fin,
            'secretariat': m.secretariat_id,
            'secretariat_nom': m.secretariat.nom if m.secretariat else None,
            'secretariat_type': m.secretariat.type_id if m.secretariat else None,
            'secretariat_type_libelle': m.secretariat.type.libelle if m.secretariat and m.secretariat.type else None,
            'superviseur': superviseur.id if superviseur else None,
            'superviseur_nom': superviseur.get_full_name() if superviseur else None,
            'creee_par': creee_par.id if creee_par else None,
            'creee_par_nom': creee_par.get_full_name() if creee_par else None,
            'nb_participants': nb_p,
            'nb_presents': nb_presents,
            'created_at': f.created_at,
            'updated_at': f.updated_at,
        })

    return Response({
        'results': results,
        'count': total_count,
        'total_pages': (total_count + page_size - 1) // page_size,
        'current_page': page,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def participant_list_api(request):
    """
    List participants with optional search.
    Query params:
    - search: recherche textuelle (nom, prenom, matricule, email, concours, grade, groupe, secretariat)
    - secretariat: filtre par nom/type de secretariat
    - grade: filtre sur le grade
    - groupe: filtre sur le groupe
    - type_concours: filtre sur le type de concours
    - page: pagination
    """
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 50))

    queryset = Participant.objects.all()
    if request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        if request.user.secretariat:
            queryset = queryset.filter(secretariat=request.user.secretariat)
        else:
            queryset = queryset.filter(secretariat__isnull=True)
    elif request.user.role == 'ENCADRANT':
        queryset = queryset.filter(
            modules_inscrits__module__superviseur=request.user
        ).distinct()

    scoped_queryset = queryset
    raw_groupes = (
        scoped_queryset.exclude(groupe__isnull=True)
        .exclude(groupe='')
        .values_list('groupe', flat=True)
    )
    groupes_normalises = sorted(
        {g for g in (_normalize_groupe_value(v) for v in raw_groupes) if g},
        key=_groupe_sort_key,
    )
    filter_options = {
        'secretariats': list(
            scoped_queryset.exclude(secretariat__nom__isnull=True)
            .exclude(secretariat__nom='')
            .values_list('secretariat__nom', flat=True)
            .distinct()
            .order_by('secretariat__nom')
        ),
        'grades': list(
            scoped_queryset.exclude(grade__isnull=True)
            .exclude(grade='')
            .values_list('grade', flat=True)
            .distinct()
            .order_by('grade')
        ),
        'groupes': groupes_normalises,
        'types_concours': list(
            scoped_queryset.exclude(type_concours__isnull=True)
            .exclude(type_concours='')
            .values_list('type_concours', flat=True)
            .distinct()
            .order_by('type_concours')
        ),
    }

    # Apply search
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(nom__icontains=search) |
            Q(prenom__icontains=search) |
            Q(matricule__icontains=search) |
            Q(email__icontains=search) |
            Q(type_concours__icontains=search) |
            Q(libelle_concours__icontains=search) |
            Q(grade__icontains=search) |
            Q(groupe__icontains=search) |
            Q(secretariat__nom__icontains=search) |
            Q(secretariat__type__libelle__icontains=search)
        )

    secretariat = request.query_params.get('secretariat')
    if secretariat:
        queryset = queryset.filter(
            Q(secretariat__nom__icontains=secretariat) |
            Q(secretariat__type__libelle__icontains=secretariat)
        )

    grade = request.query_params.get('grade')
    if grade:
        queryset = queryset.filter(grade__icontains=grade)

    groupe = request.query_params.get('groupe')
    if groupe:
        groupe_normalise = _normalize_groupe_value(groupe)
        matching_ids = [
            participant_id
            for participant_id, participant_groupe in queryset.values_list('id', 'groupe')
            if _normalize_groupe_value(participant_groupe) == groupe_normalise
        ]
        queryset = queryset.filter(id__in=matching_ids)

    type_concours = request.query_params.get('type_concours')
    if type_concours:
        queryset = queryset.filter(type_concours__icontains=type_concours)

    sexe = request.query_params.get('sexe')
    if sexe:
        queryset = queryset.filter(sexe=sexe)

    vague = request.query_params.get('vague')
    if vague:
        queryset = queryset.filter(vague__iexact=vague)

    queryset = queryset.order_by('nom', 'prenom')
    
    # Pagination
    total_count = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    participants = queryset[start:end]
    
    serializer = ParticipantSerializer(participants, many=True)
    
    return Response({
        'results': serializer.data,
        'count': total_count,
        'total_pages': (total_count + page_size - 1) // page_size,
        'current_page': page,
        'filter_options': filter_options,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def participant_formations_api(request, pk):
    """Return all modules a participant is enrolled in (with their formation)."""
    try:
        participant = Participant.objects.get(pk=pk)
    except Participant.DoesNotExist:
        return Response({'error': 'Participant introuvable.'}, status=404)

    modules = (
        Module.objects
        .filter(module_participants__participant=participant)
        .select_related('formation', 'secretariat')
        .order_by('-id')
        .distinct()
    )

    data = []
    for m in modules:
        data.append({
            'id': m.id,
            'formation_id': m.formation_id,
            'formation': m.formation.formation if m.formation else '',
            'module': m.intitule,
            'grade': m.grade,
            'groupe': m.groupe,
            'vague': m.vague,
            'site': (m.site.nom if m.site else (m.site_legacy or '')),
            'site_id': m.site_id,
            'batiment': m.batiment,
            'salle': m.salle,
            'date_debut': m.date_debut,
            'date_fin': m.date_fin,
            'statut': m.statut,
            'secretariat_nom': m.secretariat.nom if m.secretariat else None,
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def formateur_list_api(request):
    """
    List formateurs with optional search.
    Query params:
    - search: search in name
    - page: pagination
    """
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 50))
    
    queryset = Formateur.objects.all()
    
    # Apply search
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(nom__icontains=search) | 
            Q(prenom__icontains=search) |
            Q(specialite__icontains=search)
        )
    
    queryset = queryset.order_by('nom', 'prenom')
    
    # Pagination
    total_count = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    formateurs = queryset[start:end]
    
    serializer = FormateurSerializer(formateurs, many=True)
    
    return Response({
        'results': serializer.data,
        'count': total_count,
        'total_pages': (total_count + page_size - 1) // page_size,
        'current_page': page,
    })


def _finance_realized_minutes(realized_minutes, planned_minutes):
    """Temps réalisé retenu : 0 si pas d'horaire planifié, sinon plafonné à la durée de la séance."""
    planned = float(planned_minutes or 0)
    if planned <= 0:
        return 0.0
    return round(min(float(realized_minutes or 0), planned), 1)


# Alias conservé pour les imports existants
_finance_realized_for_taux = _finance_realized_minutes


def _finance_taux_realisation_pct(realized_for_taux_total, planned_for_taux_total):
    """Taux de réalisation (0–100 %), hors séances sans horaire, présence plafonnée par séance."""
    planned = float(planned_for_taux_total or 0)
    if planned <= 0:
        return 0.0
    realized = float(realized_for_taux_total or 0)
    return round(min((realized / planned) * 100, 100.0), 1)


def _finance_allowed_roles():
    return {'FINANCE', 'DIRECTION'}


def _check_finance_access(request):
    return request.user.is_authenticated and request.user.role in _finance_allowed_roles()


def _sync_ref_formations_from_cycles():
    """Ajoute au référentiel les cycles de formation présents dans les données sans entrée RefFormation."""
    labels = set()
    for label in Formation.objects.exclude(formation='').values_list('formation', flat=True):
        s = (label or '').strip()
        if s:
            labels.add(s)
    for label in Module.objects.exclude(cycle='').values_list('cycle', flat=True):
        s = (label or '').strip()
        if s:
            labels.add(s)

    existing_keys = {
        r.intitule.strip().lower()
        for r in RefFormation.objects.all()
    }
    for label in labels:
        if label.strip().lower() not in existing_keys:
            RefFormation.objects.create(intitule=label, actif=True)
            existing_keys.add(label.strip().lower())


def _finance_normalize_label(label):
    """Normalise un libellé de formation pour la recherche de tarif."""
    s = (label or '').strip().lower()
    return re.sub(r'\s+', ' ', s)


def _finance_prix_heure():
    return float(FinanceSettings.get_solo().prix_heure_realisee or 0)


def _finance_build_prix_map():
    """Retourne (tarif_par_défaut, dict intitulé_formation_normalisé → tarif)."""
    default = _finance_prix_heure()
    prix_map = {}
    for ref in RefFormation.objects.exclude(prix_heure_realisee__isnull=True):
        key = _finance_normalize_label(ref.intitule)
        if key:
            prix_map[key] = float(ref.prix_heure_realisee or 0)
    return default, prix_map


def _finance_formation_label_candidates(formation_label=None, module_obj=None):
    """Libellés possibles pour retrouver le tarif d'une formation."""
    labels = []
    for raw in (formation_label,):
        if raw and str(raw).strip():
            labels.append(str(raw).strip())
    if module_obj:
        if getattr(module_obj, 'cycle', None) and str(module_obj.cycle).strip():
            labels.append(str(module_obj.cycle).strip())
        if module_obj.formation_id and module_obj.formation:
            f = (module_obj.formation.formation or '').strip()
            if f:
                labels.append(f)
    seen = set()
    ordered = []
    for lbl in labels:
        key = _finance_normalize_label(lbl)
        if key and key not in seen:
            seen.add(key)
            ordered.append(lbl)
    return ordered


def _finance_prix_heure_for_formation(formation_label, prix_map=None, default=None, module_obj=None):
    if default is None:
        default = _finance_prix_heure()
    if prix_map is None:
        _, prix_map = _finance_build_prix_map()
    for raw in _finance_formation_label_candidates(formation_label, module_obj):
        key = _finance_normalize_label(raw)
        if key and key in prix_map:
            return prix_map[key]
    return default


def _finance_module_formation_label(module_obj):
    if not module_obj:
        return ''
    if module_obj.formation_id and module_obj.formation:
        label = (module_obj.formation.formation or '').strip()
        if label:
            return label
    return (module_obj.cycle or '').strip()


def _finance_resolve_prix_heure(formation_label, *, prix_heure_override=None, prix_map=None, default=None, module_obj=None):
    if prix_heure_override is not None:
        return float(prix_heure_override or 0)
    return _finance_prix_heure_for_formation(
        formation_label, prix_map=prix_map, default=default, module_obj=module_obj,
    )


def _finance_montant_from_minutes(minutes, prix_heure):
    return round((float(minutes or 0) / 60) * float(prix_heure or 0), 2)


def _finance_session_in_range(session, date_debut, date_fin):
    """Filtre une séance par ``date_journee`` (intervalle inclusif)."""
    if date_debut is None and date_fin is None:
        return True
    d = session.date_journee
    if not d:
        return False
    if date_debut and d < date_debut:
        return False
    if date_fin and d > date_fin:
        return False
    return True


def _finance_secretariat_id_from_request(request):
    raw = (request.query_params.get('secretariat_id') or request.query_params.get('secretariat') or '').strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _finance_filter_formateur_queryset(queryset, secretariat_id):
    if not secretariat_id:
        return queryset
    return queryset.filter(
        Q(secretariats__id=secretariat_id) |
        Q(modules_assignes__module__secretariat_id=secretariat_id) |
        Q(modules__secretariat_id=secretariat_id),
    ).distinct()


def _finance_previous_period(date_debut, date_fin, meta):
    """Calcule la période immédiatement précédente (pour comparaison dashboard)."""
    preset = (meta or {}).get('preset')
    if preset == 'tout':
        return None
    today = timezone.localdate()
    try:
        if preset == 'mois':
            mois = (meta or {}).get('mois') or today.strftime('%Y-%m')
            year, month = [int(x) for x in mois.split('-')]
            if month == 1:
                year, month = year - 1, 12
            else:
                month -= 1
            last_day = calendar.monthrange(year, month)[1]
            d0, d1 = date(year, month, 1), date(year, month, last_day)
            prev_mois = f'{year}-{month:02d}'
            return {
                'error': False,
                'date_debut': d0,
                'date_fin': d1,
                'meta': {
                    'preset': 'mois',
                    'mois': prev_mois,
                    'type': 'intervalle',
                    'label': f"Mois de {d0.strftime('%m/%Y')}",
                    'description': 'Période de comparaison (mois précédent).',
                },
            }
        if preset == 'trimestre':
            trimestre = (meta or {}).get('trimestre') or f'{today.year}-Q{(today.month - 1) // 3 + 1}'
            year_s, q_s = trimestre.upper().split('-Q', 1)
            year, q = int(year_s), int(q_s)
            if q == 1:
                year, q = year - 1, 4
            else:
                q -= 1
            start_month = (q - 1) * 3 + 1
            end_month = start_month + 2
            last_day = calendar.monthrange(year, end_month)[1]
            d0 = date(year, start_month, 1)
            d1 = date(year, end_month, last_day)
            return {
                'error': False,
                'date_debut': d0,
                'date_fin': d1,
                'meta': {
                    'preset': 'trimestre',
                    'trimestre': f'{year}-Q{q}',
                    'type': 'intervalle',
                    'label': f'Trimestre {q} — {year}',
                    'description': 'Période de comparaison (trimestre précédent).',
                },
            }
        if preset == 'annee':
            year = int((meta or {}).get('annee') or today.year) - 1
            d0, d1 = date(year, 1, 1), date(year, 12, 31)
            return {
                'error': False,
                'date_debut': d0,
                'date_fin': d1,
                'meta': {
                    'preset': 'annee',
                    'annee': year,
                    'type': 'intervalle',
                    'label': f'Année {year}',
                    'description': 'Période de comparaison (année précédente).',
                },
            }
        if preset == 'custom' and date_debut and date_fin:
            span_days = (date_fin - date_debut).days
            prev_fin = date_debut - timedelta(days=1)
            prev_debut = prev_fin - timedelta(days=span_days)
            return {
                'error': False,
                'date_debut': prev_debut,
                'date_fin': prev_fin,
                'meta': {
                    'preset': 'custom',
                    'type': 'intervalle',
                    'label': 'Période précédente (même durée)',
                    'description': 'Intervalle de même longueur, immédiatement avant la période sélectionnée.',
                },
            }
    except (ValueError, TypeError):
        return None
    return None


def _heures_entieres(minutes):
    """Convertit des minutes en heures entières (affichage stats / finance)."""
    return int(round(float(minutes or 0) / 60))


def _finance_canonical_volume_kpis(rows, *, date_debut=None, date_fin=None):
    """Volume horaire global (séances uniques) aligné dashboard web / statistiques."""
    from .volume_horaire import compute_volume_horaire_from_module_ids

    module_ids = set()
    for row in rows:
        for mod in row.get('modules') or []:
            mid = mod.get('module_id')
            if mid:
                module_ids.add(mid)
    return compute_volume_horaire_from_module_ids(
        module_ids,
        date_debut=date_debut,
        date_fin=date_fin,
        integer_hours=True,
    )


def _finance_apply_canonical_volume_kpis(kpis, volume_totals):
    kpis['total_duree_minutes'] = volume_totals['prevu_minutes']
    kpis['total_duree_heures'] = volume_totals['prevu_heures']
    kpis['total_duree_realisee_minutes'] = volume_totals['realise_minutes']
    kpis['total_duree_realisee_heures'] = volume_totals['realise_heures']
    kpis['taux_realisation_global_pct'] = volume_totals['taux_pct']


def _finance_kpis_from_rows(rows, prix_heure):
    """Agrège les KPI dashboard à partir des lignes rapport finance."""
    total_formateurs = len(rows)
    formateurs_actifs = sum(1 for r in rows if (r.get('sessions_count') or 0) > 0)
    formateurs_inactifs = total_formateurs - formateurs_actifs
    total_sessions = sum(int(r.get('sessions_count') or 0) for r in rows)
    total_duree_minutes = round(sum(float(r.get('total_duree_minutes') or 0) for r in rows), 1)
    total_duree_heures = _heures_entieres(total_duree_minutes)
    total_duree_realisee_minutes = round(
        sum(float(r.get('total_duree_realisee_minutes') or 0) for r in rows), 1,
    )
    total_duree_realisee_heures = _heures_entieres(total_duree_realisee_minutes)
    total_montant_realise = round(sum(float(r.get('montant_total_realise') or 0) for r in rows), 2)
    taux_planned = sum(
        float((r.get('statistiques') or {}).get('taux_planned_minutes') or 0) for r in rows
    )
    taux_realized_capped = sum(
        float((r.get('statistiques') or {}).get('taux_realized_capped_minutes') or 0) for r in rows
    )
    taux_realisation_global = _finance_taux_realisation_pct(taux_realized_capped, taux_planned)
    sessions_avec_pointage = sum(
        int((r.get('statistiques') or {}).get('sessions_avec_pointage') or 0) for r in rows
    )
    tarifs_variables = any(r.get('tarifs_variables') for r in rows)
    tarifs_appliques = set()
    for r in rows:
        if r.get('tarifs_variables'):
            for mod in r.get('modules') or []:
                ph = mod.get('prix_heure_realisee')
                if ph is not None:
                    tarifs_appliques.add(float(ph))
        elif r.get('prix_heure_realisee') is not None:
            tarifs_appliques.add(float(r.get('prix_heure_realisee') or 0))
    prix_heure_moyen_effectif = round(
        total_montant_realise / (total_duree_realisee_minutes / 60), 2,
    ) if total_duree_realisee_minutes > 0 else 0
    return {
        'total_formateurs': total_formateurs,
        'formateurs_actifs': formateurs_actifs,
        'formateurs_inactifs': formateurs_inactifs,
        'total_sessions': total_sessions,
        'sessions_avec_pointage': sessions_avec_pointage,
        'total_duree_minutes': total_duree_minutes,
        'total_duree_heures': total_duree_heures,
        'total_duree_realisee_minutes': total_duree_realisee_minutes,
        'total_duree_realisee_heures': total_duree_realisee_heures,
        'total_montant_realise': total_montant_realise,
        'prix_heure_realisee': prix_heure,
        'prix_heure_defaut': prix_heure,
        'tarifs_variables': tarifs_variables,
        'tarifs_appliques': sorted(tarifs_appliques),
        'prix_heure_moyen_effectif': prix_heure_moyen_effectif,
        'taux_realisation_global_pct': taux_realisation_global,
        'moyenne_heures_par_formateur': int(round(
            total_duree_heures / formateurs_actifs,
        )) if formateurs_actifs > 0 else 0,
        'moyenne_heures_realisees_par_formateur': int(round(
            total_duree_realisee_heures / formateurs_actifs,
        )) if formateurs_actifs > 0 else 0,
        'moyenne_montant_par_formateur_actif': round(
            (total_montant_realise / formateurs_actifs), 2,
        ) if formateurs_actifs > 0 else 0,
    }


def _finance_dashboard_modules_breakdown(rows, *, date_debut, date_fin, secretariat_id=None):
    """Ventilation dashboard par module (volume horaire canonique par séances)."""
    from .volume_horaire import _accumulate_module_session_volumes

    meta_by_id = {}
    for row in rows:
        for mod in row.get('modules') or []:
            mid = mod.get('module_id')
            if not mid:
                continue
            if mid not in meta_by_id:
                meta_by_id[mid] = {
                    'module_id': mid,
                    'module_intitule': mod.get('module_intitule') or mod.get('module_intitule_brut') or '',
                    'formation_intitule': mod.get('formation_intitule') or '',
                    'grade': mod.get('grade') or '',
                    'groupe': mod.get('groupe') or '',
                    'secretariat_nom': mod.get('secretariat_nom') or '',
                    'prix_heure_realisee': mod.get('prix_heure_realisee'),
                }

    if not meta_by_id:
        return []

    module_ids = list(meta_by_id.keys())
    modules_by_id = {
        m.id: m for m in Module.objects.filter(id__in=module_ids).select_related(
            'formation', 'secretariat', 'ref_module',
        )
    }

    results = []
    for mid in module_ids:
        mod_obj = modules_by_id.get(mid)
        if secretariat_id and (not mod_obj or mod_obj.secretariat_id != secretariat_id):
            continue
        vol = _accumulate_module_session_volumes(
            mod_obj,
            date_debut=date_debut,
            date_fin=date_fin,
        )
        planned = round(vol['prevu_min'], 1)
        realized = round(vol['realise_min'], 1)
        prix = meta_by_id[mid].get('prix_heure_realisee')
        montant = _finance_montant_from_minutes(realized, prix)
        taux = _finance_taux_realisation_pct(realized, planned)
        meta = meta_by_id[mid]
        results.append({
            **meta,
            'sessions_count': vol['nb_sessions'],
            'total_duree_minutes': planned,
            'total_duree_heures': _heures_entieres(planned) if planned else 0,
            'total_duree_realisee_minutes': realized,
            'total_duree_realisee_heures': _heures_entieres(realized) if realized else 0,
            'taux_realisation_pct': taux,
            'montant_realise': montant,
        })

    return sorted(results, key=lambda m: m.get('module_intitule') or '')


def _finance_kpi_evolution(current, previous):
    """Écarts absolus et relatifs entre deux jeux de KPI."""
    keys = (
        'total_montant_realise',
        'total_duree_realisee_minutes',
        'total_duree_minutes',
        'total_sessions',
        'formateurs_actifs',
        'taux_realisation_global_pct',
    )
    evolution = {}
    for key in keys:
        c = float(current.get(key) or 0)
        p = float(previous.get(key) or 0)
        delta = round(c - p, 2)
        evolution[key] = {
            'delta': delta,
            'pourcent': round((delta / p) * 100, 1) if p else (100.0 if c else 0.0),
        }
    return evolution


def _finance_join_unique_labels(values):
    """Concatène des libellés uniques (grade, groupe…) triés."""
    cleaned = sorted({str(v).strip() for v in values if v and str(v).strip()})
    return ', '.join(cleaned)


def _finance_recap_par_module(modules, *, settings=None):
    """Fiche récapitulative des modules dispensés par formateur."""
    from .finance_tolerance import evaluate_volume_tolerance

    recap = []
    for mod in modules or []:
        planned = round(float(mod.get('total_duree_minutes') or 0), 1)
        realized = round(float(mod.get('total_duree_realisee_minutes') or 0), 1)
        tol = evaluate_volume_tolerance(planned, realized, settings=settings)
        recap.append({
            'module_id': mod.get('module_id'),
            'module_intitule': mod.get('module_intitule') or mod.get('module_intitule_brut') or '',
            'formation_intitule': mod.get('formation_intitule') or '',
            'grade': mod.get('grade') or '',
            'groupe': mod.get('groupe') or '',
            'sessions_count': int(mod.get('sessions_count') or 0),
            'total_duree_minutes': planned,
            'total_duree_realisee_minutes': realized,
            'total_duree_heures': mod.get('total_duree_heures') or 0,
            'total_duree_realisee_heures': mod.get('total_duree_realisee_heures') or 0,
            'taux_realisation_pct': mod.get('taux_realisation_pct') or 0,
            'montant_realise': round(float(mod.get('montant_realise') or 0), 2),
            'prix_heure_realisee': mod.get('prix_heure_realisee'),
            'tolerance': tol,
        })
    return sorted(
        recap,
        key=lambda x: (x.get('grade') or '', x.get('groupe') or '', x.get('module_intitule') or ''),
    )


def _finance_enrich_row_tolerance(row, settings=None):
    """Ajoute l'évaluation tolérance au formateur et à chaque module."""
    from .finance_tolerance import evaluate_volume_tolerance, tolerance_settings_payload

    tol_row = evaluate_volume_tolerance(
        row.get('total_duree_minutes'),
        row.get('total_duree_realisee_minutes'),
        settings=settings,
    )
    row['tolerance'] = tol_row
    row['tolerance_parametres'] = tolerance_settings_payload(settings)

    modules = row.get('modules') or []
    for mod in modules:
        mod['tolerance'] = evaluate_volume_tolerance(
            mod.get('total_duree_minutes'),
            mod.get('total_duree_realisee_minutes'),
            settings=settings,
        )

    recap = row.get('recap_modules') or []
    for item in recap:
        if 'tolerance' not in item:
            item['tolerance'] = evaluate_volume_tolerance(
                item.get('total_duree_minutes'),
                item.get('total_duree_realisee_minutes'),
                settings=settings,
            )
    return row


def _finance_group_sessions_by_groupe(sessions):
    """Regroupe les séances par grade + groupe avec sous-totaux."""
    groups = {}
    for session in sessions or []:
        grade = (session.get('grade') or '').strip()
        groupe = (session.get('groupe') or '').strip()
        key = (grade, groupe)
        entry = groups.setdefault(key, {
            'grade': grade,
            'groupe': groupe,
            'sessions': [],
            'sous_total': {
                'creneau_minutes': 0.0,
                'realise_minutes': 0.0,
                'montant': 0.0,
                'sessions_count': 0,
            },
        })
        creneau = float(session.get('duree_minutes') or 0)
        realise = float(session.get('duree_realisee_minutes') or 0)
        montant = float(session.get('montant_realise') or 0)
        entry['sessions'].append(session)
        entry['sous_total']['creneau_minutes'] += creneau
        entry['sous_total']['realise_minutes'] += realise
        entry['sous_total']['montant'] += montant
        entry['sous_total']['sessions_count'] += 1

    result = []
    for key in sorted(groups.keys()):
        entry = groups[key]
        entry['sessions'].sort(
            key=lambda s: (str(s.get('date_journee') or ''), int(s.get('numero') or 0)),
        )
        st = entry['sous_total']
        st['creneau_minutes'] = round(st['creneau_minutes'], 1)
        st['realise_minutes'] = round(st['realise_minutes'], 1)
        st['montant'] = round(st['montant'], 2)
        result.append(entry)
    return result


def _finance_build_statistiques(
    *,
    total_minutes,
    total_realized_minutes,
    session_count,
    sessions_with_pointage,
    session_dates,
    montant_total,
    prix_heure,
    taux_planned_minutes=0,
    taux_realized_capped_minutes=0,
):
    total_minutes = float(total_minutes or 0)
    total_realized = float(total_realized_minutes or 0)
    session_count = int(session_count or 0)
    sessions_with_pointage = int(sessions_with_pointage or 0)
    taux = _finance_taux_realisation_pct(taux_realized_capped_minutes, taux_planned_minutes)
    dates_sorted = sorted(d for d in session_dates if d)
    return {
        'taux_realisation_pct': taux,
        'taux_planned_minutes': round(float(taux_planned_minutes or 0), 1),
        'taux_realized_capped_minutes': round(float(taux_realized_capped_minutes or 0), 1),
        'sessions_avec_pointage': sessions_with_pointage,
        'sessions_sans_pointage': max(session_count - sessions_with_pointage, 0),
        'moyenne_duree_seance_minutes': round(total_minutes / session_count, 1) if session_count else 0,
        'moyenne_realisee_seance_minutes': round(total_realized / session_count, 1) if session_count else 0,
        'ecart_planifie_realise_minutes': round(total_minutes - total_realized, 1),
        'premiere_seance_date': dates_sorted[0].isoformat() if dates_sorted else None,
        'derniere_seance_date': dates_sorted[-1].isoformat() if dates_sorted else None,
        'moyenne_montant_par_seance': round(float(montant_total or 0) / session_count, 2) if session_count else 0,
        'prix_heure_applique': float(prix_heure or 0),
    }


def _finance_report_rows(
    formateurs,
    *,
    include_sessions,
    prix_heure=None,
    global_aggregates=None,
    date_debut=None,
    date_fin=None,
    secretariat_id=None,
):
    """Construit les lignes rapport finance pour une liste de Formateur (déjà résolus)."""
    use_variable_rates = prix_heure is None
    if use_variable_rates:
        default_prix, prix_map = _finance_build_prix_map()
    else:
        default_prix = float(prix_heure or 0)
        prix_map = {}
    formateur_ids = [f.id for f in formateurs]
    if not formateur_ids:
        return []

    module_formateur_map = {}
    for module_id, formateur_id in ModuleFormateur.objects.filter(
        formateur_id__in=formateur_ids
    ).values_list('module_id', 'formateur_id'):
        module_formateur_map.setdefault(formateur_id, set()).add(module_id)

    for module_id, formateur_id in Module.objects.filter(
        formateur_id__in=formateur_ids
    ).values_list('id', 'formateur_id'):
        module_formateur_map.setdefault(formateur_id, set()).add(module_id)

    all_module_ids = sorted({
        mid
        for module_ids in module_formateur_map.values()
        for mid in module_ids
    })
    modules_by_id = {}
    if all_module_ids:
        for module in Module.objects.filter(id__in=all_module_ids).select_related(
            'formation', 'secretariat', 'site', 'ref_module',
        ):
            modules_by_id[module.id] = module
    sessions_by_module = {}
    if all_module_ids:
        for session in SessionModule.objects.filter(module_id__in=all_module_ids).select_related(
            'module',
            'module__formation',
        ).order_by('date_journee', 'numero'):
            sessions_by_module.setdefault(session.module_id, []).append(session)

    realized_by_formateur_session = {}
    if formateur_ids:
        now = timezone.now()
        pointages = Pointage.objects.filter(
            formateur_id__in=formateur_ids,
            session__module_id__in=all_module_ids,
            session_id__isnull=False,
        ).only('formateur_id', 'session_id', 'duree_presence_minutes', 'timestamp_entree', 'timestamp_sortie')
        for pt in pointages:
            minutes = 0.0
            if pt.duree_presence_minutes is not None:
                minutes = float(pt.duree_presence_minutes)
            elif pt.timestamp_entree and pt.timestamp_sortie:
                minutes = max((pt.timestamp_sortie - pt.timestamp_entree).total_seconds() / 60, 0)
            elif pt.timestamp_entree and not pt.timestamp_sortie:
                # Pointage encore ouvert: compter le temps écoulé jusqu'à maintenant.
                minutes = max((now - pt.timestamp_entree).total_seconds() / 60, 0)
            key = (pt.formateur_id, pt.session_id)
            realized_by_formateur_session[key] = realized_by_formateur_session.get(key, 0.0) + minutes

    from .volume_horaire import (
        _session_prevu_minutes,
        _session_realise_minutes,
        module_planned_minutes_for_period,
    )

    finance_settings = FinanceSettings.get_solo()
    results = []
    for formateur in formateurs:
        module_ids = sorted(module_formateur_map.get(formateur.id, set()))
        sessions_data = []
        modules_data = {}
        total_minutes = 0.0
        total_realized_minutes = 0.0
        taux_planned_minutes = 0.0
        taux_realized_capped_minutes = 0.0
        session_count = 0
        sessions_with_pointage = 0
        session_dates = []
        rates_used = set()
        grades_seen = set()
        groupes_seen = set()
        for module_id in module_ids:
            module_obj = modules_by_id.get(module_id)
            if secretariat_id and (
                not module_obj or module_obj.secretariat_id != secretariat_id
            ):
                continue
            module_formation_label = _finance_module_formation_label(module_obj)
            module_prix_heure = _finance_resolve_prix_heure(
                module_formation_label,
                prix_heure_override=None if use_variable_rates else default_prix,
                prix_map=prix_map,
                default=default_prix,
                module_obj=module_obj,
            )
            module_sessions = sessions_by_module.get(module_id, [])
            sessions_in_period = [
                s for s in module_sessions
                if _finance_session_in_range(s, date_debut, date_fin)
            ]
            if not sessions_in_period:
                continue
            module_planned = round(module_planned_minutes_for_period(
                module_obj,
                len(sessions_in_period),
                len(module_sessions),
                sessions_in_period,
            ), 1)
            canonical_intitule = module_obj.canonical_intitule() if module_obj else ''
            mod_entry = modules_data.setdefault(module_id, {
                'module_id': module_id,
                'module_intitule': canonical_intitule,
                'module_intitule_brut': module_obj.intitule if module_obj else '',
                'formation_intitule': (
                    module_obj.formation.formation
                    if module_obj and module_obj.formation_id else ''
                ),
                'grade': module_obj.grade if module_obj else '',
                'groupe': module_obj.groupe if module_obj else '',
                'statut': module_obj.statut if module_obj else '',
                'site': (
                    module_obj.site.nom if module_obj and module_obj.site_id and module_obj.site
                    else (module_obj.site_legacy if module_obj else '')
                ),
                'salle': module_obj.salle if module_obj else '',
                'date_debut': module_obj.date_debut if module_obj else None,
                'date_fin': module_obj.date_fin if module_obj else None,
                'secretariat_nom': (
                    f"{module_obj.secretariat.nom} ({module_obj.secretariat.numero})"
                    if module_obj and module_obj.secretariat_id else ''
                ),
                'sessions_count': 0,
                'total_duree_minutes': module_planned,
                'total_duree_realisee_minutes': 0.0,
                'taux_planned_minutes': module_planned,
                'taux_realized_capped_minutes': 0.0,
                'montant_realise': 0.0,
                'prix_heure_realisee': module_prix_heure,
            })
            total_minutes += module_planned
            if module_planned > 0:
                taux_planned_minutes += module_planned
            if module_obj:
                grade_val = (module_obj.grade or '').strip()
                groupe_val = (module_obj.groupe or '').strip()
                if grade_val:
                    grades_seen.add(grade_val)
                if groupe_val:
                    groupes_seen.add(groupe_val)
            if use_variable_rates and module_prix_heure is not None:
                rates_used.add(module_prix_heure)
            for session in sessions_in_period:
                session_count += 1
                creneau_minutes = round(_session_prevu_minutes(session), 1)
                realized_minutes = round(_session_realise_minutes(session), 1)
                pointage_minutes = round(
                    realized_by_formateur_session.get((formateur.id, session.id), 0.0), 1,
                )
                if pointage_minutes > 0:
                    sessions_with_pointage += 1
                if session.date_journee:
                    session_dates.append(session.date_journee)
                    if global_aggregates is not None:
                        d = session.date_journee
                        month_key = d.strftime('%Y-%m')
                        global_aggregates['activite_par_mois'][month_key] = (
                            global_aggregates['activite_par_mois'].get(month_key, 0.0) + realized_minutes
                        )
                        session_montant = _finance_montant_from_minutes(realized_minutes, module_prix_heure)
                        montant_par_mois = global_aggregates.setdefault('activite_montant_par_mois', {})
                        montant_par_mois[month_key] = montant_par_mois.get(month_key, 0.0) + session_montant
                        cur_min = global_aggregates.get('date_min')
                        cur_max = global_aggregates.get('date_max')
                        if cur_min is None or d < cur_min:
                            global_aggregates['date_min'] = d
                        if cur_max is None or d > cur_max:
                            global_aggregates['date_max'] = d
                mod_entry['sessions_count'] += 1
                mod_entry['total_duree_realisee_minutes'] += realized_minutes
                mod_entry['taux_realized_capped_minutes'] += realized_minutes
                if include_sessions:
                    taux_sess = (
                        _finance_taux_realisation_pct(realized_minutes, creneau_minutes)
                        if creneau_minutes > 0 else 0
                    )
                    sessions_data.append({
                        'session_id': session.id,
                        'date_journee': session.date_journee,
                        'numero': session.numero,
                        'intitule': session.intitule or f"Session {session.numero}",
                        'module_id': session.module_id,
                        'module_intitule': canonical_intitule,
                        'formation_id': session.module.formation_id if session.module else None,
                        'formation_intitule': (
                            session.module.formation.formation
                            if session.module and session.module.formation else ''
                        ),
                        'grade': module_obj.grade if module_obj else '',
                        'groupe': module_obj.groupe if module_obj else '',
                        'duree_minutes': creneau_minutes,
                        'duree_realisee_minutes': realized_minutes,
                        'montant_realise': _finance_montant_from_minutes(realized_minutes, module_prix_heure),
                        'prix_heure_realisee': module_prix_heure,
                        'taux_realisation_pct': taux_sess,
                        'a_pointage': pointage_minutes > 0,
                    })
            realized_module = mod_entry['total_duree_realisee_minutes']
            if module_planned > 0:
                realized_module = min(realized_module, module_planned)
            mod_entry['total_duree_realisee_minutes'] = realized_module
            mod_entry['taux_realized_capped_minutes'] = realized_module
            mod_entry['montant_realise'] = _finance_montant_from_minutes(
                realized_module, module_prix_heure,
            )
            total_realized_minutes += realized_module
            taux_realized_capped_minutes += realized_module
        modules_list = []
        for mid in module_ids:
            entry = modules_data.get(mid)
            if not entry:
                continue
            entry = dict(entry)
            entry['total_duree_minutes'] = round(entry['total_duree_minutes'], 1)
            entry['total_duree_realisee_minutes'] = round(entry['total_duree_realisee_minutes'], 1)
            entry['total_duree_heures'] = _heures_entieres(entry['total_duree_minutes'])
            entry['total_duree_realisee_heures'] = _heures_entieres(entry['total_duree_realisee_minutes'])
            if entry.get('date_debut'):
                entry['date_debut'] = entry['date_debut'].isoformat()
            if entry.get('date_fin'):
                entry['date_fin'] = entry['date_fin'].isoformat()
            entry['taux_realisation_pct'] = _finance_taux_realisation_pct(
                entry.get('taux_realized_capped_minutes', 0),
                entry.get('taux_planned_minutes', 0),
            )
            entry['taux_planned_minutes'] = round(float(entry.get('taux_planned_minutes') or 0), 1)
            entry['taux_realized_capped_minutes'] = round(float(entry.get('taux_realized_capped_minutes') or 0), 1)
            modules_list.append(entry)
        montant_total = round(sum(float(m.get('montant_realise') or 0) for m in modules_list), 2)
        row_prix_heure = default_prix
        tarifs_variables = False
        if use_variable_rates:
            if len(rates_used) == 1:
                row_prix_heure = next(iter(rates_used))
            elif len(rates_used) > 1:
                row_prix_heure = None
                tarifs_variables = True
        statistiques = _finance_build_statistiques(
            total_minutes=total_minutes,
            total_realized_minutes=total_realized_minutes,
            session_count=session_count,
            sessions_with_pointage=sessions_with_pointage,
            session_dates=session_dates,
            montant_total=montant_total,
            prix_heure=row_prix_heure if row_prix_heure is not None else default_prix,
            taux_planned_minutes=taux_planned_minutes,
            taux_realized_capped_minutes=taux_realized_capped_minutes,
        )
        row = {
            'id': formateur.id,
            'numerobadge': formateur.numerobadge,
            'nom': formateur.nom,
            'prenom': formateur.prenom,
            'email': formateur.email or '',
            'telephone': formateur.telephone or '',
            'specialite': formateur.specialite or '',
            'organisation': formateur.organisation or '',
            'grades': _finance_join_unique_labels(grades_seen) or '-',
            'groupes': _finance_join_unique_labels(groupes_seen) or '-',
            'secretariats_noms': [
                f"{s.nom} ({s.numero})" for s in formateur.secretariats.all()
            ],
            'numero_piece_identite': formateur.numero_piece_identite or '',
            'numero_compte_bancaire': formateur.numero_compte_bancaire or '',
            'nb_formations': len(modules_list),
            'created_at': formateur.created_at,
            'prix_heure_realisee': row_prix_heure,
            'tarifs_variables': tarifs_variables,
            'montant_total_realise': montant_total,
            'total_duree_minutes': round(total_minutes, 1),
            'total_duree_heures': _heures_entieres(total_minutes),
            'total_duree_realisee_minutes': round(total_realized_minutes, 1),
            'total_duree_realisee_heures': _heures_entieres(total_realized_minutes),
            'sessions_count': session_count,
            'statistiques': statistiques,
            'modules': modules_list,
            'recap_modules': _finance_recap_par_module(modules_list, settings=finance_settings),
        }
        if include_sessions:
            row['sessions'] = sessions_data
            row['sessions_by_groupe'] = _finance_group_sessions_by_groupe(sessions_data)
        _finance_enrich_row_tolerance(row, settings=finance_settings)
        results.append(row)
    return results


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def formateur_finance_report_api(request):
    """Rapport finance : temps de cours par formateur, par séance, + total.

    Query params:
    - ``formateur_id`` : si fourni, retourne une seule ligne avec le détail des séances (pagination ignorée).
    - ``include_sessions`` : pour la liste paginée, ``1`` / ``true`` inclut les séances (lourd). Par défaut ``0`` :
      totaux et ``sessions_count`` seulement.
    """
    allowed_roles = _finance_allowed_roles()
    if request.user.role not in allowed_roles:
        return Response({'detail': 'Accès réservé à la Direction et au service Finance.'}, status=403)

    period = parse_period_from_request(request)
    if period['error']:
        return Response({'detail': period['detail']}, status=400)

    secretariat_id = _finance_secretariat_id_from_request(request)

    formateur_id_raw = (request.query_params.get('formateur_id') or '').strip()
    if formateur_id_raw:
        try:
            fid = int(formateur_id_raw)
        except ValueError:
            return Response({'detail': 'formateur_id invalide.'}, status=400)
        try:
            formateur = Formateur.objects.prefetch_related('secretariats').get(pk=fid)
        except Formateur.DoesNotExist:
            return Response({'detail': 'Formateur introuvable.'}, status=404)
        global_agg = {'activite_par_mois': {}, 'date_min': None, 'date_max': None}
        results = _finance_report_rows(
            [formateur],
            include_sessions=True,
            date_debut=period['date_debut'],
            date_fin=period['date_fin'],
            global_aggregates=global_agg,
            secretariat_id=secretariat_id,
        )
        payload = {
            'results': results,
            'count': 1,
            'total_pages': 1,
            'current_page': 1,
            'periode': periode_api_payload(
                period['date_debut'],
                period['date_fin'],
                period['meta'],
                global_agg.get('date_min'),
                global_agg.get('date_max'),
            ),
        }
        if secretariat_id:
            try:
                sec = Secretariat.objects.get(pk=secretariat_id)
                payload['secretariat_filtre'] = {'id': sec.id, 'nom': sec.nom, 'numero': sec.numero}
            except Secretariat.DoesNotExist:
                pass
        if request.user.role != 'FINANCE':
            for row in results:
                row.pop('numero_piece_identite', None)
                row.pop('numero_compte_bancaire', None)
        return Response(payload)

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 25))
    include_sessions = request.query_params.get('include_sessions', '0').lower() in ('1', 'true', 'yes')

    queryset = Formateur.objects.prefetch_related('secretariats').order_by('nom', 'prenom')
    queryset = _finance_filter_formateur_queryset(queryset, secretariat_id)
    search = (request.query_params.get('search') or '').strip()
    if search:
        queryset = queryset.filter(
            Q(nom__icontains=search) |
            Q(prenom__icontains=search) |
            Q(specialite__icontains=search)
        )

    total_count = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    formateurs = list(queryset[start:end])
    results = _finance_report_rows(
        formateurs,
        include_sessions=include_sessions,
        date_debut=period['date_debut'],
        date_fin=period['date_fin'],
        secretariat_id=secretariat_id,
    )

    list_payload = {
        'results': results,
        'count': total_count,
        'total_pages': (total_count + page_size - 1) // page_size,
        'current_page': page,
        'periode': periode_api_payload(period['date_debut'], period['date_fin'], period['meta']),
    }
    if secretariat_id:
        try:
            sec = Secretariat.objects.get(pk=secretariat_id)
            list_payload['secretariat_filtre'] = {'id': sec.id, 'nom': sec.nom, 'numero': sec.numero}
        except Secretariat.DoesNotExist:
            pass
    if request.user.role != 'FINANCE':
        for row in results:
            row.pop('numero_piece_identite', None)
            row.pop('numero_compte_bancaire', None)
    return Response(list_payload)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def formateur_donnees_sensibles_api(request, pk):
    """Pièce d'identité et compte bancaire — visible/éditable par FINANCE ou le formateur lui-même."""
    try:
        formateur = Formateur.objects.get(pk=pk)
    except Formateur.DoesNotExist:
        return Response({'detail': 'Formateur introuvable.'}, status=404)

    if not can_view_formateur_sensitive_data(request.user, formateur):
        return Response({'detail': 'Accès interdit.'}, status=403)

    if request.method == 'GET':
        return Response(formateur_sensitive_payload(formateur))

    if not can_edit_formateur_sensitive_data(request.user, formateur):
        return Response({'detail': 'Modification interdite.'}, status=403)

    update_fields = []
    for field in ('numero_piece_identite', 'numero_compte_bancaire'):
        if field in request.data:
            setattr(formateur, field, str(request.data.get(field) or '').strip())
            update_fields.append(field)
    if update_fields:
        formateur.save(update_fields=update_fields)
    return Response(formateur_sensitive_payload(formateur))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finance_dashboard_api(request):
    """Dashboard finance: agrégats globaux + top formateurs."""
    if request.user.role not in _finance_allowed_roles():
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    period = parse_period_from_request(request)
    if period['error']:
        return Response({'detail': period['detail']}, status=400)

    secretariat_id = _finance_secretariat_id_from_request(request)
    compare_previous = request.query_params.get('compare', '').lower() in ('1', 'true', 'yes')

    formateurs_qs = Formateur.objects.prefetch_related('secretariats').order_by('nom', 'prenom')
    formateurs_qs = _finance_filter_formateur_queryset(formateurs_qs, secretariat_id)
    formateurs = list(formateurs_qs)
    global_aggregates = {'activite_par_mois': {}, 'activite_montant_par_mois': {}, 'date_min': None, 'date_max': None}
    rows = _finance_report_rows(
        formateurs,
        include_sessions=False,
        global_aggregates=global_aggregates,
        date_debut=period['date_debut'],
        date_fin=period['date_fin'],
        secretariat_id=secretariat_id,
    )

    date_min = global_aggregates.get('date_min')
    date_max = global_aggregates.get('date_max')

    prix_heure = _finance_prix_heure()
    kpis = _finance_kpis_from_rows(rows, prix_heure)
    vh_totals = _finance_canonical_volume_kpis(
        rows,
        date_debut=period['date_debut'],
        date_fin=period['date_fin'],
    )
    _finance_apply_canonical_volume_kpis(kpis, vh_totals)

    from .finance_tolerance import tolerance_settings_payload
    tol_settings = tolerance_settings_payload()
    kpis['tolerance'] = {
        **tol_settings,
        'formateurs_conformes': sum(
            1 for r in rows if (r.get('tolerance') or {}).get('statut') == 'ok'
        ),
        'formateurs_alerte': sum(
            1 for r in rows if (r.get('tolerance') or {}).get('statut') == 'alerte'
        ),
        'formateurs_anomalie': sum(
            1 for r in rows if (r.get('tolerance') or {}).get('statut') == 'anomalie'
        ),
        'formateurs_ecart': sum(
            1 for r in rows if (r.get('tolerance') or {}).get('statut') == 'ecart'
        ),
    }

    montant_par_mois = global_aggregates.get('activite_montant_par_mois') or {}
    activite_par_mois = [
        {
            'mois': mois,
            'label': datetime.strptime(mois, '%Y-%m').strftime('%b %Y'),
            'minutes_realisees': round(minutes, 1),
            'heures_realisees': _heures_entieres(minutes),
            'montant': round(float(montant_par_mois.get(mois, 0.0)), 2),
        }
        for mois, minutes in sorted(global_aggregates['activite_par_mois'].items())
    ]

    repartition_specialites = {}
    for r in rows:
        key = (r.get('specialite') or '').strip() or 'Non renseignée'
        repartition_specialites[key] = repartition_specialites.get(key, 0) + 1

    top_temps_planifie = sorted(rows, key=lambda r: float(r.get('total_duree_minutes') or 0), reverse=True)[:10]
    top_temps_realise = sorted(
        rows, key=lambda r: float(r.get('total_duree_realisee_minutes') or 0), reverse=True,
    )[:10]
    top_montants = sorted(rows, key=lambda r: float(r.get('montant_total_realise') or 0), reverse=True)[:10]

    periode_payload = periode_api_payload(
        period['date_debut'],
        period['date_fin'],
        period['meta'],
        date_min,
        date_max,
    )
    periode_payload['description'] = (
        period['meta'].get('description')
        or (
            'Le volume horaire prévu est le volume contractuel du module '
            '(duree_prevue_heures), indépendant des modifications d\'emploi du temps. '
            'Le volume réalisé est la durée réelle des '
            'séances terminées, plafonnée au créneau prévu (même règle que le dashboard web '
            'et les statistiques). Les montants sont calculés sur le volume réalisé selon '
            'le tarif du cycle de formation (paramétrage Finance).'
        )
    )

    comparaison = None
    if compare_previous and period['meta'].get('preset') != 'tout':
        prev_period = _finance_previous_period(
            period['date_debut'], period['date_fin'], period['meta'],
        )
        if prev_period:
            prev_rows = _finance_report_rows(
                formateurs,
                include_sessions=False,
                date_debut=prev_period['date_debut'],
                date_fin=prev_period['date_fin'],
                secretariat_id=secretariat_id,
            )
            prev_kpis = _finance_kpis_from_rows(prev_rows, prix_heure)
            prev_vh = _finance_canonical_volume_kpis(
                prev_rows,
                date_debut=prev_period['date_debut'],
                date_fin=prev_period['date_fin'],
            )
            _finance_apply_canonical_volume_kpis(prev_kpis, prev_vh)
            comparaison = {
                'periode': periode_api_payload(
                    prev_period['date_debut'],
                    prev_period['date_fin'],
                    prev_period['meta'],
                ),
                'kpis': prev_kpis,
                'evolution': _finance_kpi_evolution(kpis, prev_kpis),
            }

    dashboard_payload = {
        'periode': periode_payload,
        'kpis': kpis,
        'volumes_par_module': _finance_dashboard_modules_breakdown(
            rows,
            date_debut=period['date_debut'],
            date_fin=period['date_fin'],
            secretariat_id=secretariat_id,
        ),
        'top_formateurs': top_temps_planifie,
        'top_temps_realise': top_temps_realise,
        'top_montants': top_montants,
        'activite_par_mois': activite_par_mois,
        'repartition_specialites': [
            {'specialite': k, 'count': v} for k, v in sorted(
                repartition_specialites.items(), key=lambda x: -x[1],
            )
        ],
        'synthese_formateurs': rows,
        'generated_at': timezone.now(),
    }
    if comparaison:
        dashboard_payload['comparaison'] = comparaison
    if secretariat_id:
        try:
            sec = Secretariat.objects.get(pk=secretariat_id)
            dashboard_payload['secretariat_filtre'] = {
                'id': sec.id, 'nom': sec.nom, 'numero': sec.numero,
            }
        except Secretariat.DoesNotExist:
            pass
    return Response(dashboard_payload)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def finance_settings_api(request):
    """Paramètres finance : tarif horaire par défaut et tarifs par formation (référentiel)."""
    if not _check_finance_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    settings_obj = FinanceSettings.get_solo()

    def _serialize_tarifs():
        _sync_ref_formations_from_cycles()
        tarifs = []
        for ref in RefFormation.objects.order_by('intitule'):
            tarifs.append({
                'id': ref.id,
                'intitule': ref.intitule,
                'actif': ref.actif,
                'prix_heure_realisee': (
                    float(ref.prix_heure_realisee) if ref.prix_heure_realisee is not None else None
                ),
            })
        return tarifs

    def _settings_payload():
        return {
            'prix_heure_realisee': float(settings_obj.prix_heure_realisee or 0),
            'tarifs_formations': _serialize_tarifs(),
            'afficher_montants_exports': bool(settings_obj.afficher_montants_exports),
            'export_titre_document': settings_obj.export_titre_document or '',
            'export_entete_ligne1': settings_obj.export_entete_ligne1 or '',
            'export_entete_ligne2': settings_obj.export_entete_ligne2 or '',
            'export_organisme': settings_obj.export_organisme or '',
            'export_adresse': settings_obj.export_adresse or '',
            'export_reference_prefix': settings_obj.export_reference_prefix or 'EFI',
            'export_mention_legale': settings_obj.export_mention_legale or '',
            'export_signataire_nom': settings_obj.export_signataire_nom or '',
            'export_signataire_fonction': settings_obj.export_signataire_fonction or '',
            'tolerance_active': bool(settings_obj.tolerance_active),
            'tolerance_minutes': int(settings_obj.tolerance_minutes or 0),
            'tolerance_pct': float(settings_obj.tolerance_pct or 0),
            'updated_at': settings_obj.updated_at,
            'updated_by': (
                settings_obj.updated_by.get_full_name() or settings_obj.updated_by.username
            ) if settings_obj.updated_by else None,
        }

    if request.method == 'GET':
        return Response(_settings_payload())

    if request.user.role != 'FINANCE':
        return Response({'detail': 'Seul le service Finance peut modifier les paramètres.'}, status=403)

    updated = False

    if 'prix_heure_realisee' in request.data:
        raw = request.data.get('prix_heure_realisee')
        if raw is None or raw == '':
            return Response({'detail': 'prix_heure_realisee invalide.'}, status=400)
        try:
            prix = float(raw)
        except (TypeError, ValueError):
            return Response({'detail': 'prix_heure_realisee invalide.'}, status=400)
        if prix < 0:
            return Response({'detail': 'Le prix doit être positif ou nul.'}, status=400)
        settings_obj.prix_heure_realisee = round(prix, 2)
        updated = True

    tarifs = request.data.get('tarifs_formations')
    if tarifs is not None:
        if not isinstance(tarifs, list):
            return Response({'detail': 'tarifs_formations doit être une liste.'}, status=400)
        for item in tarifs:
            if not isinstance(item, dict) or 'id' not in item:
                return Response({'detail': 'Chaque tarif doit contenir un id.'}, status=400)
            try:
                ref = RefFormation.objects.get(pk=int(item['id']))
            except (RefFormation.DoesNotExist, TypeError, ValueError):
                return Response({'detail': f"Formation référentiel introuvable (id={item.get('id')})."}, status=400)
            raw_prix = item.get('prix_heure_realisee')
            if raw_prix is None or raw_prix == '':
                ref.prix_heure_realisee = None
            else:
                try:
                    prix_ref = float(raw_prix)
                except (TypeError, ValueError):
                    return Response({'detail': f"Tarif invalide pour {ref.intitule}."}, status=400)
                if prix_ref < 0:
                    return Response({'detail': f"Le tarif de {ref.intitule} doit être positif ou nul."}, status=400)
                ref.prix_heure_realisee = round(prix_ref, 2)
            ref.save(update_fields=['prix_heure_realisee'])
        updated = True

    export_bool_fields = ('afficher_montants_exports', 'tolerance_active')
    for field in export_bool_fields:
        if field in request.data:
            setattr(settings_obj, field, bool(request.data.get(field)))
            updated = True

    if 'tolerance_minutes' in request.data:
        try:
            mins = int(request.data.get('tolerance_minutes'))
        except (TypeError, ValueError):
            return Response({'detail': 'tolerance_minutes invalide.'}, status=400)
        if mins < 0:
            return Response({'detail': 'La tolérance en minutes doit être positive ou nulle.'}, status=400)
        settings_obj.tolerance_minutes = mins
        updated = True

    if 'tolerance_pct' in request.data:
        try:
            pct = float(request.data.get('tolerance_pct'))
        except (TypeError, ValueError):
            return Response({'detail': 'tolerance_pct invalide.'}, status=400)
        if pct < 0 or pct > 100:
            return Response({'detail': 'La tolérance en % doit être entre 0 et 100.'}, status=400)
        settings_obj.tolerance_pct = round(pct, 2)
        updated = True

    export_text_fields = (
        'export_titre_document', 'export_entete_ligne1', 'export_entete_ligne2',
        'export_organisme', 'export_adresse', 'export_reference_prefix',
        'export_mention_legale', 'export_signataire_nom', 'export_signataire_fonction',
    )
    for field in export_text_fields:
        if field in request.data:
            setattr(settings_obj, field, str(request.data.get(field) or '').strip())
            updated = True

    if not updated:
        return Response({'detail': 'Aucun paramètre à mettre à jour.'}, status=400)

    settings_obj.updated_by = request.user
    settings_obj.save()

    payload = _settings_payload()
    payload['updated_by'] = request.user.get_full_name() or request.user.username
    return Response(payload)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def finance_ajustements_api(request):
    """Liste et proposition d'ajustements horaires sur séances réelles."""
    if not _check_finance_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    from .finance_ajustements import (
        propose_ajustement,
        serialize_ajustement,
        _log_finance_audit,
    )

    if request.method == 'GET':
        statut = (request.query_params.get('statut') or '').strip().upper()
        qs = FinanceAjustement.objects.select_related(
            'session',
            'session__module',
            'session__module__formation',
            'formateur',
            'proposed_by',
            'validated_by',
            'rejected_by',
        )
        if statut:
            valid_statuts = {s.value for s in FinanceAjustement.Statut}
            if statut not in valid_statuts:
                return Response({'detail': 'Statut invalide.'}, status=400)
            qs = qs.filter(statut=statut)
        formateur_id = request.query_params.get('formateur_id')
        if formateur_id:
            try:
                qs = qs.filter(formateur_id=int(formateur_id))
            except (TypeError, ValueError):
                return Response({'detail': 'formateur_id invalide.'}, status=400)
        session_id = request.query_params.get('session_id')
        if session_id:
            try:
                qs = qs.filter(session_id=int(session_id))
            except (TypeError, ValueError):
                return Response({'detail': 'session_id invalide.'}, status=400)
        items = [serialize_ajustement(a) for a in qs[:200]]
        pending_count = FinanceAjustement.objects.filter(
            statut=FinanceAjustement.Statut.EN_ATTENTE,
        ).count()
        return Response({'items': items, 'pending_count': pending_count})

    session_id = request.data.get('session_id')
    formateur_id = request.data.get('formateur_id')
    minutes_delta = request.data.get('minutes_delta')
    motif = request.data.get('motif', '')

    try:
        session = SessionModule.objects.select_related(
            'module', 'module__formation',
        ).get(pk=int(session_id))
    except (SessionModule.DoesNotExist, TypeError, ValueError):
        return Response({'detail': 'Séance introuvable.'}, status=404)

    try:
        formateur = Formateur.objects.get(pk=int(formateur_id))
    except (Formateur.DoesNotExist, TypeError, ValueError):
        return Response({'detail': 'Formateur introuvable.'}, status=404)

    ajustement, errors = propose_ajustement(
        session, formateur, minutes_delta, motif, request.user,
    )
    if errors:
        return Response({'detail': errors[0], 'errors': errors}, status=400)

    _log_finance_audit('FINANCE_AJUSTEMENT_PROPOSE', request, ajustement)
    return Response(serialize_ajustement(ajustement), status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finance_ajustement_valider_api(request, pk):
    """Valide un ajustement horaire (Direction/Finance)."""
    if not _check_finance_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    from .finance_ajustements import valider_ajustement, serialize_ajustement

    try:
        ajustement = FinanceAjustement.objects.select_related(
            'session', 'session__module', 'session__module__formation', 'formateur',
        ).get(pk=pk)
    except FinanceAjustement.DoesNotExist:
        return Response({'detail': 'Ajustement introuvable.'}, status=404)

    ajustement, errors = valider_ajustement(ajustement, request.user, request=request)
    if errors:
        return Response({'detail': errors[0], 'errors': errors}, status=400)
    return Response(serialize_ajustement(ajustement))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def finance_encadrants_api(request):
    """Liste des encadrants : groupe, volume planifié, volume réalisé (JSON)."""
    if not _check_finance_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    period = parse_period_from_request(request)
    if period['error']:
        return Response({'detail': period['detail']}, status=400)

    from .finance_encadrants import finance_encadrants_report

    secretariat_id = _finance_secretariat_id_from_request(request)
    report = finance_encadrants_report(
        date_debut=period['date_debut'],
        date_fin=period['date_fin'],
        secretariat_id=secretariat_id,
    )
    payload = {
        **report,
        'periode': periode_api_payload(
            period['date_debut'],
            period['date_fin'],
            period['meta'],
            None,
            None,
        ),
    }
    return Response(payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finance_ajustement_rejeter_api(request, pk):
    """Rejette un ajustement horaire (Direction/Finance)."""
    if not _check_finance_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    from .finance_ajustements import rejeter_ajustement, serialize_ajustement

    try:
        ajustement = FinanceAjustement.objects.select_related(
            'session', 'session__module', 'session__module__formation', 'formateur',
        ).get(pk=pk)
    except FinanceAjustement.DoesNotExist:
        return Response({'detail': 'Ajustement introuvable.'}, status=404)

    ajustement, errors = rejeter_ajustement(
        ajustement,
        request.user,
        rejection_motif=request.data.get('motif', ''),
        request=request,
    )
    if errors:
        return Response({'detail': errors[0], 'errors': errors}, status=400)
    return Response(serialize_ajustement(ajustement))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def formation_detail_api(request, pk):
    """
    Get formation details by ID.
    """
    try:
        formation = Formation.objects.prefetch_related(
            'modules__sessions',
            'modules__module_participants__participant',
            'modules__secretariat',
        ).get(pk=pk)
    except Formation.DoesNotExist:
        return Response({'detail': 'Formation introuvable.'}, status=404)

    if request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        sec = request.user.secretariat
        if not sec or not formation.modules.filter(secretariat=sec).exists():
            return Response({'detail': 'Formation introuvable.'}, status=404)
    
    serializer = FormationDetailSerializer(formation)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_generate_qr(request, formation_pk, session_pk=None):
    """
    Generate QR code for a formation or session.
    """
    try:
        formation = Formation.objects.get(pk=formation_pk)
    except Formation.DoesNotExist:
        return Response({'detail': 'Formation introuvable.'}, status=404)
    
    if not session_pk:
        return Response({'detail': 'session_pk est obligatoire pour générer un QR.'}, status=400)
    try:
        session = SessionModule.objects.get(pk=session_pk, module__formation=formation)
    except SessionModule.DoesNotExist:
        return Response({'detail': 'Séance introuvable.'}, status=404)
    if session.est_terminee:
        return Response(
            {'detail': 'Impossible de générer un QR pour une séance terminée.'},
            status=400,
        )
    
    # Deactivate old QR tokens
    qr_filter = QRToken.objects.filter(session__module__formation=formation, actif=True)
    if session:
        qr_filter = qr_filter.filter(session=session)
    qr_filter.update(actif=False)
    
    # Create new token
    qr_token = QRToken.objects.create(
        session=session,
        genere_par=request.user,
        expire_at=timezone.now() + timedelta(hours=24),
    )
    
    return Response({
        'detail': 'QR code généré.',
        'qr_url': f'/api/formations/{formation_pk}/sessions/{session_pk}/qr-image/' if session else f'/api/formations/{formation_pk}/qr-image/',
        'token': str(qr_token.token),
    }, status=201)


@api_view(['POST'])
@permission_classes([IsSecretariatOrDFRC])
@parser_classes([MultiPartParser])
def api_import_excel(request):
    """
    Import Excel (.xlsx) or CSV (.csv) file for formations, participants, or formateurs.
    Expects multipart form with 'file' and 'type' fields.
    Returns JSON with created count and errors.
    """
    uploaded = request.FILES.get('file')
    import_type = request.data.get('type', '')

    if not uploaded:
        return Response({'error': 'Veuillez fournir un fichier.'}, status=400)
    if import_type not in ('formations', 'participants', 'formateurs', 'seances', 'emploi_du_temps'):
        return Response({'error': 'Type invalide. Utilisez: formations, participants, formateurs, seances, emploi_du_temps.'}, status=400)

    # Vérification fine par type d'import — respecte les permissions réelles du groupe.
    _import_perm_map = {
        'formations':     'formations.add_formation',
        'participants':   'formations.add_participant',
        'formateurs':     'formations.add_formateur',
        'seances':        'formations.add_sessionmodule',
        'emploi_du_temps': 'formations.add_module',
    }
    required_perm = _import_perm_map.get(import_type)
    if required_perm and not request.user.has_perm(required_perm):
        return Response(
            {'error': f"Vous n'avez pas le droit d'importer des \"{import_type}\"."},
            status=403,
        )

    from .management.commands.import_excel import Command as ImportCommand

    cmd = ImportCommand()
    _logs = []
    class _Stdout:
        def write(self, msg): _logs.append(str(msg))
    cmd.stdout = _Stdout()

    errors = []
    stats = {}

    filename = uploaded.name.lower()
    is_csv = filename.endswith('.csv')
    file_content = uploaded.read()

    # Pour SECRETARIAT : utilise le secrétariat de l'user
    # Pour ADMIN/DFRC : secretariat=None → auto-affectation par catégorie dans _import_participants
    secretariat = request.user.secretariat if request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT') else None

    try:
        with transaction.atomic():
            if is_csv:
                ws = cmd._load_csv_from_bytes(file_content)
                if import_type == 'formations':
                    stats['created'], stats['updated'] = cmd._import_formations(ws, errors, secretariat=secretariat)
                elif import_type == 'participants':
                    stats['created'] = cmd._import_participants(ws, errors, secretariat=secretariat)
                elif import_type == 'formateurs':
                    stats['created'] = cmd._import_formateurs(ws, errors)
                elif import_type == 'emploi_du_temps':
                    stats['created'] = cmd._import_emploi_du_temps(ws, errors)
                elif import_type == 'seances':
                    stats['created'], stats['updated'] = cmd._import_seances(ws, errors)
            else:
                try:
                    from openpyxl import load_workbook
                except ImportError:
                    return Response({'error': 'openpyxl non installé sur le serveur.'}, status=500)

                try:
                    wb = load_workbook(BytesIO(file_content), read_only=True)
                except Exception as e:
                    return Response({'error': f'Impossible de lire le fichier: {e}'}, status=400)

                # Map type to expected sheet name
                sheet_map = {
                    'formations': 'Formations',
                    'participants': 'Participants',
                    'formateurs': 'Formateurs',
                    'seances': 'Séances',
                    'emploi_du_temps': 'Emploi du temps',
                }
                sheet_name = sheet_map[import_type]
                # Comme manage.py import_excel : feuille « Séances » ou « Seances » (sans accent).
                if import_type == 'seances' and sheet_name not in wb.sheetnames and 'Seances' in wb.sheetnames:
                    sheet_name = 'Seances'

                def _looks_like_participant_sheet(ws):
                    """Return True if the first row contains an inscription number column."""
                    try:
                        first_row = next(ws.iter_rows(values_only=True, max_row=1), None)
                        if not first_row:
                            return False
                        headers = [str(h).strip().lower() if h else '' for h in first_row]
                        keywords = ["d'inscription", "d inscription", "inscription", "fncp", "nom"]
                        return any(any(k in h for k in keywords) for h in headers)
                    except Exception:
                        return False

                if sheet_name not in wb.sheetnames:
                    if import_type == 'participants':
                        # Try RECAP first, then any sheet that looks like participant data
                        candidate_sheets = []
                        for sn in wb.sheetnames:
                            if sn.upper() in ('RECAP', 'RECAPITULATIF', 'PARTICIPANTS', 'LISTE'):
                                candidate_sheets.insert(0, sn)
                            elif _looks_like_participant_sheet(wb[sn]):
                                candidate_sheets.append(sn)
                        if not candidate_sheets:
                            wb.close()
                            return Response({'error': 'Aucune feuille de participants trouvée dans le fichier.'}, status=400)
                        total_created = 0
                        for sn in candidate_sheets:
                            total_created += cmd._import_participants(wb[sn], errors, secretariat=secretariat)
                        stats['created'] = total_created
                        wb.close()
                        debug_headers = [l for l in _logs if '[DEBUG]' in l]
                        return Response({
                            'created': stats.get('created', 0),
                            'accounts': cmd.account_provision_stats.get('auditeurs', {}),
                            'errors': errors[:20],
                            'debug_headers': debug_headers,
                        })
                    else:
                        ws = wb.active
                        if ws is None:
                            wb.close()
                            return Response({'error': f'Feuille "{sheet_name}" introuvable dans le fichier.'}, status=400)
                        wb_sheets = {sheet_name: ws}
                else:
                    wb_sheets = {sheet_name: wb[sheet_name]}

                if import_type == 'formations':
                    stats['created'], stats['updated'] = cmd._import_formations(wb_sheets[sheet_name], errors, secretariat=secretariat)
                elif import_type == 'participants':
                    stats['created'] = cmd._import_participants(wb_sheets[sheet_name], errors, secretariat=secretariat)
                elif import_type == 'formateurs':
                    stats['created'] = cmd._import_formateurs(wb_sheets[sheet_name], errors)
                elif import_type == 'emploi_du_temps':
                    stats['created'] = cmd._import_emploi_du_temps(wb_sheets[sheet_name], errors)
                elif import_type == 'seances':
                    formation_id = request.data.get('formation_id')
                    if formation_id:
                        try:
                            formation = Formation.objects.get(pk=formation_id)
                            stats['created'] = cmd._import_seances_for_formation(wb_sheets[sheet_name], errors, formation)
                            stats['updated'] = 0
                        except Formation.DoesNotExist:
                            wb.close()
                            return Response({'error': 'Formation introuvable.'}, status=404)
                    else:
                        stats['created'], stats['updated'] = cmd._import_seances(wb_sheets[sheet_name], errors)

                wb.close()

    except Exception as e:
        return Response({'error': f"Erreur lors de l'import: {e}"}, status=500)

    debug_headers = [l for l in _logs if '[DEBUG]' in l]
    return Response({
        'created': stats.get('created', 0),
        'updated': stats.get('updated', 0),
        'accounts': cmd.account_provision_stats,
        'errors': errors[:20],
        'debug_headers': debug_headers,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_formation_list(request):
    if request.method == 'GET':
        data = list(RefFormation.objects.values('id', 'intitule', 'actif'))
        return Response(data)
    obj = RefFormation.objects.create(intitule=request.data.get('intitule', ''), actif=request.data.get('actif', True))
    return Response({'id': obj.id, 'intitule': obj.intitule, 'actif': obj.actif}, status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_formation_detail(request, pk):
    try:
        obj = RefFormation.objects.get(pk=pk)
    except RefFormation.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.intitule = request.data.get('intitule', obj.intitule)
        obj.actif = request.data.get('actif', obj.actif)
        obj.save()
        return Response({'id': obj.id, 'intitule': obj.intitule, 'actif': obj.actif})
    obj.delete()
    return Response(status=204)


def _ref_module_response(obj, status_code=200):
    return Response(
        {
            'id': obj.id,
            'intitule': obj.intitule,
            'volume_horaire': obj.volume_horaire,
            'actif': obj.actif,
        },
        status=status_code,
    )


def _ref_module_validation_response(exc):
    if hasattr(exc, 'message_dict'):
        return Response(exc.message_dict, status=400)
    return Response({'detail': exc.messages}, status=400)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_module_list(request):
    if request.method == 'GET':
        data = list(RefModule.objects.values('id', 'intitule', 'volume_horaire', 'actif'))
        return Response(data)
    obj = RefModule(
        intitule=request.data.get('intitule', ''),
        volume_horaire=request.data.get('volume_horaire') or None,
        actif=request.data.get('actif', True),
    )
    try:
        obj.save()
    except ValidationError as exc:
        return _ref_module_validation_response(exc)
    return _ref_module_response(obj, status_code=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_module_detail(request, pk):
    try:
        obj = RefModule.objects.get(pk=pk)
    except RefModule.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.intitule = request.data.get('intitule', obj.intitule)
        obj.volume_horaire = request.data.get('volume_horaire') or None
        obj.actif = request.data.get('actif', obj.actif)
        try:
            obj.save()
        except ValidationError as exc:
            return _ref_module_validation_response(exc)
        return _ref_module_response(obj)
    obj.delete()
    return Response(status=204)


SITE_FIELDS = (
    'id', 'nom', 'actif',
    'geofence_latitude', 'geofence_longitude', 'geofence_rayon_m',
)


def _serialize_site(obj):
    return {
        'id': obj.id,
        'nom': obj.nom,
        'actif': obj.actif,
        'geofence_latitude': (
            float(obj.geofence_latitude) if obj.geofence_latitude is not None else None
        ),
        'geofence_longitude': (
            float(obj.geofence_longitude) if obj.geofence_longitude is not None else None
        ),
        'geofence_rayon_m': obj.geofence_rayon_m,
    }


def _coerce_decimal(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_site_list(request):
    if request.method == 'GET':
        data = [_serialize_site(s) for s in RefSite.objects.all()]
        return Response(data)
    obj = RefSite.objects.create(
        nom=request.data.get('nom', ''),
        actif=request.data.get('actif', True),
        geofence_latitude=_coerce_decimal(request.data.get('geofence_latitude')),
        geofence_longitude=_coerce_decimal(request.data.get('geofence_longitude')),
        geofence_rayon_m=request.data.get('geofence_rayon_m', 200) or 200,
    )
    return Response(_serialize_site(obj), status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_site_detail(request, pk):
    try:
        obj = RefSite.objects.get(pk=pk)
    except RefSite.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.nom = request.data.get('nom', obj.nom)
        obj.actif = request.data.get('actif', obj.actif)
        if 'geofence_latitude' in request.data:
            obj.geofence_latitude = _coerce_decimal(request.data.get('geofence_latitude'))
        if 'geofence_longitude' in request.data:
            obj.geofence_longitude = _coerce_decimal(request.data.get('geofence_longitude'))
        if 'geofence_rayon_m' in request.data:
            rayon = request.data.get('geofence_rayon_m')
            obj.geofence_rayon_m = int(rayon) if rayon not in (None, '') else 200
        obj.save()
        return Response(_serialize_site(obj))
    obj.delete()
    return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_batiment_list(request):
    if request.method == 'GET':
        data = list(RefBatiment.objects.values('id', 'nom', 'site_id', 'actif'))
        return Response(data)
    obj = RefBatiment.objects.create(
        nom=request.data.get('nom', ''),
        site_id=request.data.get('site_id'),
        actif=request.data.get('actif', True),
    )
    return Response({'id': obj.id, 'nom': obj.nom, 'site_id': obj.site_id, 'actif': obj.actif}, status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_batiment_detail(request, pk):
    try:
        obj = RefBatiment.objects.get(pk=pk)
    except RefBatiment.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.nom = request.data.get('nom', obj.nom)
        obj.site_id = request.data.get('site_id', obj.site_id)
        obj.actif = request.data.get('actif', obj.actif)
        obj.save()
        return Response({'id': obj.id, 'nom': obj.nom, 'site_id': obj.site_id, 'actif': obj.actif})
    obj.delete()
    return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_salle_list(request):
    if request.method == 'GET':
        data = list(RefSalle.objects.values('id', 'nom', 'site_id', 'batiment_id', 'actif'))
        return Response(data)
    obj = RefSalle.objects.create(
        nom=request.data.get('nom', ''),
        site_id=request.data.get('site_id'),
        batiment_id=request.data.get('batiment_id') or None,
        actif=request.data.get('actif', True),
    )
    return Response({'id': obj.id, 'nom': obj.nom, 'site_id': obj.site_id, 'batiment_id': obj.batiment_id, 'actif': obj.actif}, status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_salle_detail(request, pk):
    try:
        obj = RefSalle.objects.get(pk=pk)
    except RefSalle.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.nom = request.data.get('nom', obj.nom)
        obj.site_id = request.data.get('site_id', obj.site_id)
        obj.batiment_id = request.data.get('batiment_id') or None
        obj.actif = request.data.get('actif', obj.actif)
        obj.save()
        return Response({'id': obj.id, 'nom': obj.nom, 'site_id': obj.site_id, 'batiment_id': obj.batiment_id, 'actif': obj.actif})
    obj.delete()
    return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_categorie_list(request):
    if request.method == 'GET':
        data = list(RefCategorie.objects.values('id', 'libelle', 'actif'))
        return Response(data)
    obj = RefCategorie.objects.create(
        libelle=request.data.get('libelle', ''),
        actif=request.data.get('actif', True),
    )
    return Response({'id': obj.id, 'libelle': obj.libelle, 'actif': obj.actif}, status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_categorie_detail(request, pk):
    try:
        obj = RefCategorie.objects.get(pk=pk)
    except RefCategorie.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.libelle = request.data.get('libelle', obj.libelle)
        obj.actif = request.data.get('actif', obj.actif)
        obj.save()
        return Response({'id': obj.id, 'libelle': obj.libelle, 'actif': obj.actif})
    obj.delete()
    return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_grade_list(request):
    if request.method == 'GET':
        data = list(RefGrade.objects.values('id', 'libelle', 'categorie_id', 'actif'))
        return Response(data)
    obj = RefGrade.objects.create(
        libelle=request.data.get('libelle', ''),
        categorie_id=request.data.get('categorie_id') or None,
        actif=request.data.get('actif', True),
    )
    return Response({'id': obj.id, 'libelle': obj.libelle, 'categorie_id': obj.categorie_id, 'actif': obj.actif}, status=201)

@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_grade_detail(request, pk):
    try:
        obj = RefGrade.objects.get(pk=pk)
    except RefGrade.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.libelle = request.data.get('libelle', obj.libelle)
        obj.categorie_id = request.data.get('categorie_id') or None
        obj.actif = request.data.get('actif', obj.actif)
        obj.save()
        return Response({'id': obj.id, 'libelle': obj.libelle, 'categorie_id': obj.categorie_id, 'actif': obj.actif})
    obj.delete()
    return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_type_secretariat_list(request):
    if request.method == 'GET':
        data = list(RefTypeSecretariat.objects.values('id', 'libelle', 'actif'))
        return Response(data)
    obj = RefTypeSecretariat.objects.create(
        libelle=request.data.get('libelle', ''),
        actif=request.data.get('actif', True),
    )
    return Response({'id': obj.id, 'libelle': obj.libelle, 'actif': obj.actif}, status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def ref_type_secretariat_detail(request, pk):
    try:
        obj = RefTypeSecretariat.objects.get(pk=pk)
    except RefTypeSecretariat.DoesNotExist:
        return Response({'error': 'Introuvable'}, status=404)
    if request.method == 'PUT':
        obj.libelle = request.data.get('libelle', obj.libelle)
        obj.actif = request.data.get('actif', obj.actif)
        obj.save()
        return Response({'id': obj.id, 'libelle': obj.libelle, 'actif': obj.actif})
    obj.delete()
    return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def module_list_api(request, formation_pk):
    """List or create modules for a formation."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
    except Formation.DoesNotExist:
        return Response({'detail': 'Formation introuvable.'}, status=404)

    if request.method == 'GET':
        modules = formation.modules.prefetch_related('sessions').all()
        return Response(ModuleSerializer(modules, many=True).data)

    # POST — create module
    intitule = request.data.get('intitule', '').strip()
    if not intitule:
        return Response({'detail': 'intitule est requis.'}, status=400)
    duree = request.data.get('duree_prevue_heures', 0)
    ordre = request.data.get('ordre', formation.modules.count() + 1)
    from django.db import IntegrityError
    try:
        site_id = request.data.get('site_id')
        site_name = (request.data.get('site', '') or '').strip()
        site_obj = None
        if site_id not in (None, '', 0, '0'):
            try:
                site_obj = RefSite.objects.get(pk=int(site_id))
            except (RefSite.DoesNotExist, ValueError, TypeError):
                site_obj = None
        elif site_name:
            # On crée au besoin pour éviter un FK null qui casserait la géofence.
            site_obj, _ = RefSite.objects.get_or_create(nom=site_name, defaults={'actif': True})

        module = Module.objects.create(
            formation=formation,
            intitule=intitule,
            duree_prevue_heures=duree,
            ordre=ordre,
            grade=request.data.get('grade', ''),
            groupe=request.data.get('groupe', ''),
            vague=request.data.get('vague', ''),
            statut=request.data.get('statut', 'PLANIFIEE'),
            date_debut=request.data.get('date_debut') or None,
            date_fin=request.data.get('date_fin') or None,
            site=site_obj,
            site_legacy=site_name,
            batiment=request.data.get('batiment', ''),
            salle=request.data.get('salle', ''),
        )
    except IntegrityError:
        return Response({'detail': f'Un module "{intitule}" existe déjà pour cette formation.'}, status=400)
    return Response(ModuleSerializer(module).data, status=201)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def module_detail_api(request, formation_pk, module_pk):
    """Get, update or delete a module."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
        module = Module.objects.get(pk=module_pk, formation=formation)
    except Formation.DoesNotExist:
        return Response({'detail': 'Formation introuvable.'}, status=404)
    except Module.DoesNotExist:
        return Response({'detail': 'Module introuvable.'}, status=404)

    if request.method == 'GET':
        return Response(ModuleSerializer(module).data)

    if request.method in ('PUT', 'PATCH'):
        fields = [
            'intitule', 'duree_prevue_heures', 'ordre', 'statut',
            'grade', 'groupe', 'vague',
            'site', 'site_id', 'batiment', 'salle',
            'date_debut', 'date_fin',
            'formateur', 'secretariat', 'superviseur',
        ]
        old_date_debut = module.date_debut  # avant modification
        # Champs dont une valeur vide doit être convertie en NULL
        nullable_fields = {'formateur', 'secretariat', 'superviseur', 'duree_prevue_heures',
                           'date_debut', 'date_fin', 'grade', 'groupe', 'vague'}

        # Champs texte qui stockent '' plutôt que NULL
        str_fields = {'batiment', 'salle', 'intitule', 'statut'}

        with transaction.atomic():
            for f in fields:
                if f in request.data:
                    val = request.data[f]
                    if f in ('site', 'site_id'):
                        # Normalisation: on accepte soit site_id, soit site (nom).
                        new_site = None
                        if 'site_id' in request.data:
                            raw_id = request.data.get('site_id')
                            if raw_id not in (None, '', 0, '0'):
                                try:
                                    new_site = RefSite.objects.get(pk=int(raw_id))
                                except (RefSite.DoesNotExist, ValueError, TypeError):
                                    new_site = None
                        if new_site is None and 'site' in request.data:
                            raw_name = (request.data.get('site') or '').strip()
                            if raw_name:
                                new_site, _ = RefSite.objects.get_or_create(
                                    nom=raw_name, defaults={'actif': True}
                                )
                                module.site_legacy = raw_name
                            else:
                                module.site_legacy = ''
                        module.site = new_site
                        continue
                    if f in nullable_fields and val in (None, '', ''):
                        val = None
                    elif f in str_fields and val is None:
                        val = ''
                    setattr(module, f, val)
            module.save()
            module.refresh_from_db()

            # Si date_debut a changé, décaler toutes les séances non démarrées
            # du même delta (préserve les écarts relatifs entre séances).
            new_date_debut = module.date_debut
            if (
                'date_debut' in request.data
                and old_date_debut and new_date_debut
                and old_date_debut != new_date_debut
            ):
                delta = new_date_debut - old_date_debut
                sessions_to_shift = list(
                    module.sessions.filter(demarree_le__isnull=True)
                )
                # Ordre descendant si décalage vers l'avant, ascendant sinon,
                # pour éviter les collisions temporaires sur unique_together
                # (module, date_journee, numero).
                sessions_to_shift.sort(
                    key=lambda s: (s.date_journee, s.numero),
                    reverse=(delta.days > 0),
                )
                for s in sessions_to_shift:
                    s.date_journee = s.date_journee + delta
                    s.save(update_fields=['date_journee'])

        return Response(ModuleSerializer(module).data)

    # DELETE
    if module.sessions.exists():
        return Response({'detail': 'Impossible de supprimer un module qui a des séances.'}, status=400)
    module.delete()
    return Response(status=204)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def module_full_detail_api(request, formation_pk, module_pk):
    """Retourne le détail complet d'un module : infos + séances + participants de la formation."""
    try:
        formation = Formation.objects.get(pk=formation_pk)
        module = Module.objects.get(pk=module_pk, formation=formation)
    except Formation.DoesNotExist:
        return Response({'detail': 'Formation introuvable.'}, status=404)
    except Module.DoesNotExist:
        return Response({'detail': 'Module introuvable.'}, status=404)

    from .serializers import SessionSerializer, ParticipantSerializer
    from .duree_prevue_resolve import ensure_module_duree_prevue
    from presences.models import Pointage
    module = Module.objects.select_related(
        'secretariat', 'formateur', 'superviseur', 'ref_module',
    ).get(pk=module_pk, formation=formation)
    ensure_module_duree_prevue(module)
    sessions = module.sessions.all().order_by('date_journee', 'numero')
    participants = module.module_participants.select_related('participant').all()
    formateurs_assignes = module.module_formateurs.select_related('formateur').all()

    formateur_nom = None
    if module.formateur:
        formateur_nom = f"{module.formateur.prenom} {module.formateur.nom}".strip()

    # Présences participants
    pointages_part_qs = Pointage.objects.filter(
        session__module=module, participant__isnull=False
    ).select_related('participant', 'session').order_by('date_journee', 'timestamp_entree')

    # Présences formateurs
    pointages_fmt_qs = Pointage.objects.filter(
        session__module=module, formateur__isnull=False
    ).select_related('formateur', 'session').order_by('date_journee', 'timestamp_entree')

    # Présences encadrants
    pointages_enc_qs = Pointage.objects.filter(
        session__module=module, encadrant__isnull=False
    ).select_related('encadrant', 'session').order_by('date_journee', 'timestamp_entree')

    presences = []
    for pt in pointages_part_qs:
        p = pt.participant
        s = pt.session
        presences.append({
            'type_personne': 'participant',
            'participant_id': p.id,
            'formateur_id': None,
            'nom': p.nom,
            'prenom': p.prenom,
            'matricule': p.matricule,
            'numerobadge': None,
            'date_journee': str(pt.date_journee),
            'session_id': pt.session_id,
            'session_date': str(s.date_journee) if s and s.date_journee else None,
            'session_intitule': s.intitule if s and s.intitule else (f'Séance {s.numero}' if s else ''),
            'session_numero': s.numero if s else None,
            'timestamp_entree': pt.timestamp_entree.isoformat() if pt.timestamp_entree else None,
            'timestamp_sortie': pt.timestamp_sortie.isoformat() if pt.timestamp_sortie else None,
            'duree_minutes': float(pt.duree_presence_minutes or 0),
            'statut': pt.statut,
        })

    for pt in pointages_fmt_qs:
        f_obj = pt.formateur
        s = pt.session
        presences.append({
            'type_personne': 'formateur',
            'participant_id': None,
            'formateur_id': f_obj.id,
            'nom': f_obj.nom,
            'prenom': f_obj.prenom,
            'matricule': None,
            'numerobadge': f_obj.numerobadge,
            'date_journee': str(pt.date_journee),
            'session_id': pt.session_id,
            'session_date': str(s.date_journee) if s and s.date_journee else None,
            'session_intitule': s.intitule if s and s.intitule else (f'Séance {s.numero}' if s else ''),
            'session_numero': s.numero if s else None,
            'timestamp_entree': pt.timestamp_entree.isoformat() if pt.timestamp_entree else None,
            'timestamp_sortie': pt.timestamp_sortie.isoformat() if pt.timestamp_sortie else None,
            'duree_minutes': float(pt.duree_presence_minutes or 0),
            'statut': pt.statut,
        })

    for pt in pointages_enc_qs:
        enc = pt.encadrant
        s = pt.session
        presences.append({
            'type_personne': 'encadrant',
            'participant_id': None,
            'formateur_id': None,
            'encadrant_id': enc.id if enc else None,
            'nom': (enc.last_name or '') if enc else '',
            'prenom': (enc.first_name or '') if enc else '',
            'matricule': enc.matricule if enc else '',
            'numerobadge': None,
            'date_journee': str(pt.date_journee),
            'session_id': pt.session_id,
            'session_date': str(s.date_journee) if s and s.date_journee else None,
            'session_intitule': s.intitule if s and s.intitule else (f'Séance {s.numero}' if s else ''),
            'session_numero': s.numero if s else None,
            'timestamp_entree': pt.timestamp_entree.isoformat() if pt.timestamp_entree else None,
            'timestamp_sortie': pt.timestamp_sortie.isoformat() if pt.timestamp_sortie else None,
            'duree_minutes': float(pt.duree_presence_minutes or 0),
            'statut': pt.statut,
        })

    presences.sort(key=lambda x: (x['date_journee'] or '', x['timestamp_entree'] or ''))

    nb_presents = (
        Pointage.objects.filter(session__module=module, participant__isnull=False).values('participant').distinct().count()
        + Pointage.objects.filter(session__module=module, formateur__isnull=False).values('formateur').distinct().count()
        + Pointage.objects.filter(session__module=module, encadrant__isnull=False).values('encadrant').distinct().count()
    )

    encadrants = []
    if module.superviseur_id:
        sup = module.superviseur
        encadrants.append({
            'id': sup.id,
            'nom': sup.last_name or '',
            'prenom': sup.first_name or '',
            'matricule': sup.matricule or '',
            'email': sup.email or '',
            'telephone': sup.telephone or '',
            'username': sup.username,
        })

    return Response({
        'id': module.id,
        'intitule': module.intitule,
        'duree_prevue_heures': module.duree_prevue_heures,
        'ordre': module.ordre,
        'statut': module.statut,
        'statut_label': module.get_statut_display(),
        'site':     (module.site.nom if module.site else (module.site_legacy or '')),
        'site_id':  module.site_id,
        'batiment': module.batiment,
        'salle':    module.salle,
        'date_debut': module.date_debut,
        'date_fin':   module.date_fin,
        'formateur_id':  module.formateur_id,
        'formateur_nom': formateur_nom,
        'formation_id': formation.id,
        'formation': formation.formation,
        'grade':     module.grade,
        'groupe':    module.groupe,
        'vague':     module.vague,
        'categorie': (lambda: (
            (lambda lib: lib.replace('FAB', '').strip()[:1].upper() if lib else '')(
                module.secretariat.type.libelle if module.secretariat and module.secretariat.type else ''
            )
            or (module.grade[:1].upper() if module.grade else '')
        ))(),
        'secretariat_id':  module.secretariat_id,
        'secretariat_nom': module.secretariat.nom if module.secretariat else None,
        'superviseur_id':  module.superviseur_id,
        'superviseur_nom': module.superviseur.get_full_name() if module.superviseur else None,
        'nb_participants': len(participants),
        'nb_presents': nb_presents,
        'sessions': SessionSerializer(sessions, many=True).data,
        'participants': ParticipantSerializer(
            [fp.participant for fp in participants], many=True
        ).data,
        'presences': presences,
        'encadrants': encadrants,
        'formateurs': [
            {
                'id': mf.formateur.id,
                'nom': mf.formateur.nom,
                'prenom': mf.formateur.prenom,
                'numerobadge': mf.formateur.numerobadge,
                'specialite': mf.formateur.specialite,
                'email': mf.formateur.email,
            }
            for mf in formateurs_assignes
        ],
    })


@api_view(['POST'])
@permission_classes([CanManageModuleParticipant])
def module_add_participant(request, formation_pk, module_pk):
    """Inscrire un participant à un module — respecte les permissions du groupe (add_moduleparticipant)."""
    try:
        module = Module.objects.get(pk=module_pk, formation_id=formation_pk)
    except Module.DoesNotExist:
        return Response({'detail': 'Module introuvable.'}, status=404)
    participant_id = request.data.get('participant_id')
    if not participant_id:
        return Response({'detail': 'participant_id requis.'}, status=400)
    try:
        participant = Participant.objects.get(pk=participant_id)
    except Participant.DoesNotExist:
        return Response({'detail': 'Participant introuvable.'}, status=404)
    if ModuleParticipant.objects.filter(module=module, participant=participant).exists():
        return Response({'detail': 'Déjà inscrit.'}, status=400)
    ModuleParticipant.objects.create(module=module, participant=participant)
    return Response({'detail': f'{participant} inscrit au module.'}, status=201)


@api_view(['DELETE'])
@permission_classes([CanManageModuleParticipant])
def module_remove_participant(request, formation_pk, module_pk, participant_id):
    """Retirer un participant d'un module — respecte les permissions du groupe (delete_moduleparticipant)."""
    try:
        module = Module.objects.get(pk=module_pk, formation_id=formation_pk)
        mp = ModuleParticipant.objects.get(module=module, participant_id=participant_id)
    except (Module.DoesNotExist, ModuleParticipant.DoesNotExist):
        return Response({'detail': 'Inscription introuvable.'}, status=404)
    mp.delete()
    return Response(status=204)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def module_add_formateur(request, formation_pk, module_pk):
    """Assigner un formateur à un module."""
    try:
        module = Module.objects.get(pk=module_pk, formation_id=formation_pk)
    except Module.DoesNotExist:
        return Response({'detail': 'Module introuvable.'}, status=404)
    formateur_id = request.data.get('formateur_id')
    if not formateur_id:
        return Response({'detail': 'formateur_id requis.'}, status=400)
    try:
        formateur = Formateur.objects.get(pk=formateur_id)
    except Formateur.DoesNotExist:
        return Response({'detail': 'Formateur introuvable.'}, status=404)
    if ModuleFormateur.objects.filter(module=module, formateur=formateur).exists():
        return Response({'detail': 'Déjà assigné.'}, status=400)
    ModuleFormateur.objects.create(module=module, formateur=formateur)
    return Response({'detail': f'{formateur} assigné au module.'}, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def module_remove_formateur(request, formation_pk, module_pk, formateur_id):
    """Retirer un formateur d'un module."""
    try:
        module = Module.objects.get(pk=module_pk, formation_id=formation_pk)
        mf = ModuleFormateur.objects.get(module=module, formateur_id=formateur_id)
    except (Module.DoesNotExist, ModuleFormateur.DoesNotExist):
        return Response({'detail': 'Assignation introuvable.'}, status=404)
    mf.delete()
    return Response(status=204)


@api_view(['POST'])
@permission_classes([IsSecretariatOrDFRC])
def module_assign_superviseur(request, formation_pk, module_pk):
    """Assigner (ou retirer) un encadrant superviseur à un module.

    - Rôles autorisés : SECRETARIAT, CHEF_SECRETARIAT, CPFAE_ADMIN, CHEF_CPFAE_ADMIN.
    - Scope : SECRETARIAT/CHEF_SECRETARIAT ne peuvent agir que sur les modules
      de leur propre secrétariat.
    - Body : { "superviseur_id": <int|null> }  (null ou omis => retrait).
    """
    try:
        formation = Formation.objects.get(pk=formation_pk)
        module = Module.objects.select_related('secretariat', 'superviseur').get(
            pk=module_pk, formation=formation,
        )
    except Formation.DoesNotExist:
        return Response({'detail': 'Formation introuvable.'}, status=404)
    except Module.DoesNotExist:
        return Response({'detail': 'Module introuvable.'}, status=404)

    # Scope secrétariat
    user = request.user
    if user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        if not user.secretariat or module.secretariat_id != user.secretariat_id:
            return Response(
                {'detail': "Ce module n'appartient pas à votre secrétariat."},
                status=403,
            )

    superviseur_id = request.data.get('superviseur_id')
    superviseur = None
    if superviseur_id not in (None, '', 0, '0'):
        User = get_user_model()
        try:
            superviseur = User.objects.get(pk=superviseur_id, role='ENCADRANT')
        except User.DoesNotExist:
            return Response(
                {'detail': 'Encadrant introuvable ou rôle incorrect.'},
                status=400,
            )

    module.superviseur = superviseur
    module.save(update_fields=['superviseur'])

    _log_audit(
        action=AuditLog.Action.MODULE_ASSIGN_SUPERVISEUR,
        request=request,
        formation=formation,
        extra={
            'module_id': module.id,
            'module_intitule': module.intitule,
            'superviseur_id': superviseur.id if superviseur else None,
            'superviseur_nom': superviseur.get_full_name() if superviseur else None,
        },
    )

    return Response({
        'detail': (
            f'Encadrant {superviseur.get_full_name()} assigné au module.'
            if superviseur else 'Encadrant retiré du module.'
        ),
        'superviseur_id': superviseur.id if superviseur else None,
        'superviseur_nom': superviseur.get_full_name() if superviseur else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referentiels_api(request):
    """Retourne les référentiels prédéfinis pour les listes déroulantes."""
    formations = list(RefFormation.objects.filter(actif=True).values('id', 'intitule'))
    formations_reelles = list(Formation.objects.order_by('formation').values('id', 'formation'))
    modules = list(RefModule.objects.filter(actif=True).values('id', 'intitule', 'volume_horaire', 'formation_id'))
    modules_actifs = list(
        Module.objects.values_list('intitule', flat=True).distinct().order_by('intitule')
    )
    sites = list(RefSite.objects.filter(actif=True).values('id', 'nom'))
    batiments = list(RefBatiment.objects.filter(actif=True).values('id', 'nom', 'site_id'))
    salles = list(RefSalle.objects.filter(actif=True).values('id', 'nom', 'site_id', 'batiment_id'))
    categories = list(RefCategorie.objects.filter(actif=True).values('id', 'libelle'))
    grades = list(RefGrade.objects.filter(actif=True).values('id', 'libelle', 'categorie_id'))
    types_secretariat = list(RefTypeSecretariat.objects.filter(actif=True).values('id', 'libelle'))
    vagues = list(RefVague.objects.filter(actif=True).order_by('ordre', 'libelle').values('id', 'libelle', 'ordre'))

    mods_groupes_qs = Module.objects.all()
    if request.user.is_authenticated and request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        if request.user.secretariat:
            mods_groupes_qs = mods_groupes_qs.filter(secretariat=request.user.secretariat)
        else:
            mods_groupes_qs = mods_groupes_qs.none()
    elif request.user.is_authenticated and request.user.role == 'ENCADRANT':
        mods_groupes_qs = mods_groupes_qs.filter(superviseur=request.user)
    raw_module_groupes = (
        mods_groupes_qs.exclude(groupe__isnull=True)
        .exclude(groupe='')
        .values_list('groupe', flat=True)
    )
    groupes_modules = sorted(
        {g for g in (_normalize_groupe_value(v) for v in raw_module_groupes) if g},
        key=_groupe_sort_key,
    )

    raw_module_grades = (
        mods_groupes_qs.exclude(grade__isnull=True)
        .exclude(grade='')
        .values_list('grade', flat=True)
    )
    grades_modules = sorted(
        {str(v).strip() for v in raw_module_grades if str(v).strip()},
        key=lambda x: (x.lower(), x),
    )

    return Response({
        'formations': formations,
        'formations_reelles': formations_reelles,
        'modules': modules,
        'modules_actifs': modules_actifs,
        'groupes': groupes_modules,
        'grades_modules': grades_modules,
        'sites': sites,
        'batiments': batiments,
        'salles': salles,
        'categories': categories,
        'grades': grades,
        'types_secretariat': types_secretariat,
        'vagues': vagues,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def refvague_list_api(request):
    """Lister ou créer une vague dans le référentiel."""
    if request.method == 'GET':
        data = list(RefVague.objects.order_by('ordre', 'libelle').values('id', 'libelle', 'ordre', 'actif'))
        return Response(data)
    obj = RefVague.objects.create(
        libelle=request.data.get('libelle', ''),
        ordre=request.data.get('ordre', 1),
        actif=request.data.get('actif', True),
    )
    return Response({'id': obj.id, 'libelle': obj.libelle, 'ordre': obj.ordre, 'actif': obj.actif}, status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def refvague_detail_api(request, pk):
    """Modifier ou supprimer une vague du référentiel."""
    try:
        obj = RefVague.objects.get(pk=pk)
    except RefVague.DoesNotExist:
        return Response({'detail': 'Vague introuvable.'}, status=404)
    if request.method == 'DELETE':
        obj.delete()
        return Response(status=204)
    obj.libelle = request.data.get('libelle', obj.libelle)
    obj.ordre = request.data.get('ordre', obj.ordre)
    obj.actif = request.data.get('actif', obj.actif)
    obj.save()
    return Response({'id': obj.id, 'libelle': obj.libelle, 'ordre': obj.ordre, 'actif': obj.actif})
