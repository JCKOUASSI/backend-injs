"""
API views for the React frontend.
These views complement the existing DRF views with additional endpoints
needed for the frontend dashboard.
"""
from io import BytesIO
from datetime import timedelta, datetime, time
import re
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

from .models import Formation, Participant, Formateur, QRToken, SessionModule, ModuleParticipant, ModuleFormateur, RefFormation, RefModule, RefSite, RefBatiment, RefSalle, RefCategorie, RefGrade, RefTypeSecretariat, RefVague, Module
FormationParticipant = ModuleParticipant
FormationFormateur = ModuleFormateur
from .serializers import (
    FormationListSerializer,
    FormationDetailSerializer,
    ParticipantSerializer,
    FormateurSerializer,
    ModuleSerializer,
)


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

    volume_horaire_total_heures = int(
        sum(float(v or 0) for v in modules_qs.values_list('duree_prevue_heures', flat=True))
    )
    volume_horaire_effectue_minutes = 0.0
    for session in (
        SessionModule.objects.filter(module__in=modules_qs)
        .exclude(demarree_le__isnull=True)
        .exclude(terminee_le__isnull=True)
        .only('demarree_le', 'terminee_le')
    ):
        elapsed = (session.terminee_le - session.demarree_le).total_seconds() / 60
        if elapsed > 0:
            volume_horaire_effectue_minutes += elapsed
    volume_horaire_effectue_heures = int(volume_horaire_effectue_minutes / 60)
    volume_horaire_effectue_taux = (
        int((volume_horaire_effectue_heures / volume_horaire_total_heures) * 100)
        if volume_horaire_total_heures > 0 else 0
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
            'site': m.site,
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
            'site': m.site,
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


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def ref_module_list(request):
    if request.method == 'GET':
        data = list(RefModule.objects.values('id', 'intitule', 'volume_horaire', 'actif'))
        return Response(data)
    obj = RefModule.objects.create(
        intitule=request.data.get('intitule', ''),
        volume_horaire=request.data.get('volume_horaire') or None,
        actif=request.data.get('actif', True),
    )
    return Response({'id': obj.id, 'intitule': obj.intitule, 'volume_horaire': obj.volume_horaire, 'actif': obj.actif}, status=201)

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
        obj.save()
        return Response({'id': obj.id, 'intitule': obj.intitule, 'volume_horaire': obj.volume_horaire, 'actif': obj.actif})
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
            site=request.data.get('site', ''),
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
            'site', 'batiment', 'salle',
            'date_debut', 'date_fin',
            'formateur', 'secretariat', 'superviseur',
        ]
        old_date_debut = module.date_debut  # avant modification
        # Champs dont une valeur vide doit être convertie en NULL
        nullable_fields = {'formateur', 'secretariat', 'superviseur', 'duree_prevue_heures',
                           'date_debut', 'date_fin', 'grade', 'groupe', 'vague'}

        # Champs texte qui stockent '' plutôt que NULL
        str_fields = {'site', 'batiment', 'salle', 'intitule', 'statut'}

        with transaction.atomic():
            for f in fields:
                if f in request.data:
                    val = request.data[f]
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
    from presences.models import Pointage
    module = Module.objects.select_related('secretariat', 'formateur', 'superviseur').get(pk=module_pk, formation=formation)
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
        'site':     module.site,
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
