import io
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from formations.models import Formation, ModuleParticipant, ModuleFormateur, SessionModule, Formateur, Module
FormationParticipant = ModuleParticipant
FormationFormateur = ModuleFormateur
from presences.models import Pointage, AuditLog


def _calculer_duree_export(pointage):
    """
    Recalcule la durée de présence à la volée pour l'export, en appliquant
    le clamping aux heures prévues de la séance liée au pointage.
    - Entrée avant heure_debut_prevue → ramenée à heure_debut_prevue
    - Sortie après heure_fin_prevue   → ramenée à heure_fin_prevue
    - Pointage en cours (sans sortie) → sortie = maintenant, clampée
    Retourne (duree_minutes: float, heure_entree: str, heure_sortie: str).
    """
    from datetime import datetime as dt
    seance = pointage.session

    entree = timezone.localtime(pointage.timestamp_entree)
    if pointage.timestamp_sortie:
        sortie = timezone.localtime(pointage.timestamp_sortie)
    else:
        sortie = timezone.localtime(timezone.now())

    # Clamp entrée
    if seance and seance.heure_debut_prevue and entree.time() < seance.heure_debut_prevue:
        entree = entree.replace(
            hour=seance.heure_debut_prevue.hour,
            minute=seance.heure_debut_prevue.minute,
            second=0, microsecond=0,
        )

    # Clamp sortie
    if seance and seance.heure_fin_prevue and sortie.time() > seance.heure_fin_prevue:
        sortie = sortie.replace(
            hour=seance.heure_fin_prevue.hour,
            minute=seance.heure_fin_prevue.minute,
            second=0, microsecond=0,
        )

    delta = sortie - entree
    minutes = max(round(delta.total_seconds() / 60, 2), 0)

    h = int(minutes // 60)
    m = int(minutes % 60)
    duree_str = f"{h}h{m:02d}" if h > 0 else f"{m} min"

    heure_entree_str = entree.strftime('%H:%M')
    # Si la sortie n'est pas encore enregistrée, afficher explicitement "En cours"
    # plutôt qu'un tiret pour éviter l'ambiguïté dans les exports.
    heure_sortie_str = sortie.strftime('%H:%M') if pointage.timestamp_sortie else 'En cours'

    return minutes, duree_str, heure_entree_str, heure_sortie_str


# ──────────────────────────────────────────────
# Couleurs branding CI
# ──────────────────────────────────────────────
CI_GREEN_DARK = '#388E3C'
CI_GREEN = '#43A047'
CI_ORANGE = '#F57C00'
CI_LIGHT_GREEN = '#E8F5E9'
CI_LIGHT_ORANGE = '#FFF3E0'


def _check_finance_export_access(request):
    user = request.user
    return bool(user and user.is_authenticated and user.role in ('FINANCE', 'DIRECTION'))


def _session_planned_minutes(session):
    if session.demarree_le and session.terminee_le:
        elapsed = (session.terminee_le - session.demarree_le).total_seconds() / 60
        return round(elapsed, 1) if elapsed > 0 else 0
    if session.heure_debut_prevue and session.heure_fin_prevue:
        start_dt = datetime.combine(session.date_journee, session.heure_debut_prevue)
        end_dt = datetime.combine(session.date_journee, session.heure_fin_prevue)
        elapsed = (end_dt - start_dt).total_seconds() / 60
        return round(elapsed, 1) if elapsed > 0 else 0
    return 0


def _session_realized_minutes_for_formateur(formateur_id, session, now=None):
    now = now or timezone.now()
    total = 0.0
    qset = Pointage.objects.filter(
        formateur_id=formateur_id,
        session_id=session.id,
    ).only('duree_presence_minutes', 'timestamp_entree', 'timestamp_sortie')
    for pt in qset:
        if pt.duree_presence_minutes is not None:
            total += float(pt.duree_presence_minutes)
        elif pt.timestamp_entree and pt.timestamp_sortie:
            total += max((pt.timestamp_sortie - pt.timestamp_entree).total_seconds() / 60, 0)
        elif pt.timestamp_entree and not pt.timestamp_sortie:
            total += max((now - pt.timestamp_entree).total_seconds() / 60, 0)
    return round(total, 1)


def _finance_formateur_summary_rows(formateur, request=None):
    """Lignes détail + totaux pour export fiche de paie (aligné sur le rapport finance API)."""
    from formations.api_views import (
        _parse_finance_date_range,
        _finance_secretariat_id_from_request,
        _finance_report_rows,
        _finance_periode_payload,
        _finance_build_prix_map,
    )

    period = _parse_finance_date_range(request) if request else {
        'error': False, 'date_debut': None, 'date_fin': None, 'meta': {'preset': 'tout'},
    }
    if period.get('error'):
        period = {'error': False, 'date_debut': None, 'date_fin': None, 'meta': {'preset': 'tout'}}
    secretariat_id = _finance_secretariat_id_from_request(request) if request else None
    default_prix, _ = _finance_build_prix_map()
    global_agg = {'activite_par_mois': {}, 'activite_montant_par_mois': {}, 'date_min': None, 'date_max': None}
    results = _finance_report_rows(
        [formateur],
        include_sessions=True,
        date_debut=period['date_debut'],
        date_fin=period['date_fin'],
        global_aggregates=global_agg,
        secretariat_id=secretariat_id,
    )
    row = results[0] if results else {}
    sessions = row.get('sessions') or []

    def _fmt_date(val):
        if not val:
            return '-'
        if hasattr(val, 'strftime'):
            return val.strftime('%d/%m/%Y')
        try:
            from datetime import date as date_cls
            return date_cls.fromisoformat(str(val)[:10]).strftime('%d/%m/%Y')
        except (ValueError, TypeError):
            return str(val)

    rows = []
    for s in sessions:
        realized = float(s.get('duree_realisee_minutes') or 0)
        rows.append({
            'date': _fmt_date(s.get('date_journee')),
            'session': s.get('intitule') or f"Séance {s.get('numero', '')}",
            'module': s.get('module_intitule') or '-',
            'formation': s.get('formation_intitule') or '-',
            'grade': s.get('grade') or '-',
            'groupe': s.get('groupe') or '-',
            'secretariat': '-',
            'duree_seance': float(s.get('duree_minutes') or 0),
            'temps_realise': realized,
            'heures_planifiees': round(float(s.get('duree_minutes') or 0) / 60, 2),
            'heures_realisees': round(realized / 60, 2),
            'montant': float(s.get('montant_realise') or 0),
            'prix_heure': s.get('prix_heure_realisee'),
        })

    stats = row.get('statistiques') or {}
    periode_info = _finance_periode_payload(
        period['date_debut'], period['date_fin'], period['meta'],
        global_agg.get('date_min'), global_agg.get('date_max'),
    )
    return {
        'rows': rows,
        'total_planned': float(row.get('total_duree_minutes') or 0),
        'total_realized': float(row.get('total_duree_realisee_minutes') or 0),
        'total_heures_planifiees': float(row.get('total_duree_heures') or 0),
        'total_heures_realisees': float(row.get('total_duree_realisee_heures') or 0),
        'montant_total': float(row.get('montant_total_realise') or 0),
        'prix_heure': row.get('prix_heure_realisee'),
        'tarifs_variables': bool(row.get('tarifs_variables')),
        'prix_heure_defaut': default_prix,
        'taux_realisation_pct': stats.get('taux_realisation_pct', 0),
        'periode': periode_info,
        'sessions_count': int(row.get('sessions_count') or len(rows)),
        'modules': row.get('modules') or [],
        'recap_formations': _finance_recap_par_formation(row.get('modules') or []),
        'formateur': {
            'numerobadge': formateur.numerobadge or '',
            'nom': formateur.nom or '',
            'prenom': formateur.prenom or '',
            'email': formateur.email or '',
            'telephone': formateur.telephone or '',
            'specialite': formateur.specialite or '',
            'organisation': formateur.organisation or '',
            'grades': row.get('grades') or '-',
            'groupes': row.get('groupes') or '-',
            'secretariats': row.get('secretariats_noms') or [
                f"{sec.nom} ({sec.numero})" for sec in formateur.secretariats.all()
            ],
            'numero_piece_identite': formateur.numero_piece_identite or '',
            'numero_compte_bancaire': formateur.numero_compte_bancaire or '',
        },
    }


def _finance_recap_par_formation(modules):
    """Synthèse par type de formation pour les exports fiche de paie."""
    recap = {}
    for mod in modules:
        label = (mod.get('formation_intitule') or '').strip() or 'Formation non renseignée'
        entry = recap.setdefault(label, {
            'formation': label,
            'prix_heure': mod.get('prix_heure_realisee'),
            'heures_realisees': 0.0,
            'montant': 0.0,
            'seances': 0,
        })
        entry['heures_realisees'] += float(mod.get('total_duree_realisee_heures') or 0)
        entry['montant'] += float(mod.get('montant_realise') or 0)
        entry['seances'] += int(mod.get('sessions_count') or 0)
        if mod.get('prix_heure_realisee') is not None:
            entry['prix_heure'] = mod.get('prix_heure_realisee')
    return sorted(recap.values(), key=lambda x: x['formation'])


def _finance_billing_mode_label(tarifs_variables, prix_label):
    if tarifs_variables:
        return 'Facturation : tarif horaire selon le type de formation (cycle)'
    return f'Facturation : tarif unique {prix_label}'


def _finance_strip_formateur_sensitive(formateur_dict, request):
    if not formateur_dict:
        return formateur_dict
    if request and getattr(request.user, 'role', None) == 'FINANCE':
        return formateur_dict
    out = dict(formateur_dict)
    out.pop('numero_piece_identite', None)
    out.pop('numero_compte_bancaire', None)
    return out


def _parse_bool_query(value, default=True):
    if value is None or value == '':
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'oui', 'on')


def _finance_export_settings():
    from formations.models import FinanceSettings
    return FinanceSettings.get_solo()


def _afficher_montants_export(request):
    settings = _finance_export_settings()
    default = bool(getattr(settings, 'afficher_montants_exports', True))
    if request is not None and request.query_params.get('afficher_montants') is not None:
        return _parse_bool_query(request.query_params.get('afficher_montants'), default)
    return default


def _finance_export_document_options(request, formateur):
    settings = _finance_export_settings()
    prefix = (settings.export_reference_prefix or 'EFI').strip() or 'EFI'
    ref_date = datetime.now().strftime('%Y%m%d')
    badge = formateur.numerobadge or str(formateur.pk)
    return {
        'afficher_montants': _afficher_montants_export(request),
        'titre_document': settings.export_titre_document or 'FICHE DE PAIE DÉTAILLÉE',
        'entete_ligne1': settings.export_entete_ligne1 or '',
        'entete_ligne2': settings.export_entete_ligne2 or '',
        'organisme': settings.export_organisme or '',
        'adresse': settings.export_adresse or '',
        'reference': f'{prefix}-{badge}-{ref_date}',
        'mention_legale': settings.export_mention_legale or '',
        'signataire_nom': settings.export_signataire_nom or '',
        'signataire_fonction': settings.export_signataire_fonction or '',
    }


def _finance_formateur_export_context(formateur, request):
    summary = _finance_formateur_summary_rows(formateur, request)
    options = _finance_export_document_options(request, formateur)
    prix_heure = summary.get('prix_heure')
    tarifs_variables = summary.get('tarifs_variables', False)
    if tarifs_variables or prix_heure is None:
        prix_label = 'Variable (selon formation)'
    else:
        prix_label = f'{float(prix_heure or 0):,.0f} FCFA / h'
    summary['export'] = options
    summary['prix_label'] = prix_label
    summary['billing_label'] = _finance_billing_mode_label(tarifs_variables, prix_label)
    summary['periode_label'] = summary['periode'].get('periode_label') or 'Toutes périodes'
    summary['formateur'] = _finance_strip_formateur_sensitive(summary.get('formateur'), request)
    return summary


def _finance_export_table_headers(afficher_montants):
    headers = [
        'Date', 'Séance', 'Module', 'Formation', 'Grade', 'Groupe', 'Secrétariat',
        'Durée (min)', 'Réalisé (min)', 'Heures réalisées',
    ]
    if afficher_montants:
        headers.append('Tarif (FCFA/h)')
        headers.append('Montant (FCFA)')
    return headers


def _finance_export_table_row(row, afficher_montants):
    values = [
        row['date'],
        row['session'],
        row['module'],
        row['formation'],
        row.get('grade') or '-',
        row.get('groupe') or '-',
        row['secretariat'],
        row['duree_seance'],
        row['temps_realise'],
        row.get('heures_realisees', round(float(row.get('temps_realise') or 0) / 60, 2)),
    ]
    if afficher_montants:
        values.append(row.get('prix_heure', ''))
        values.append(row.get('montant', 0))
    return values


def _finance_synthese_document_options(request):
    settings = _finance_export_settings()
    prefix = (settings.export_reference_prefix or 'EFI').strip() or 'EFI'
    ref_date = datetime.now().strftime('%Y%m%d')
    return {
        'afficher_montants': _afficher_montants_export(request),
        'titre_document': 'FICHE DE PAIE GLOBALE — FORMATEURS',
        'entete_ligne1': settings.export_entete_ligne1 or '',
        'entete_ligne2': settings.export_entete_ligne2 or '',
        'organisme': settings.export_organisme or '',
        'adresse': settings.export_adresse or '',
        'reference': f'{prefix}-SYN-{ref_date}',
        'mention_legale': settings.export_mention_legale or '',
        'signataire_nom': settings.export_signataire_nom or '',
        'signataire_fonction': settings.export_signataire_fonction or '',
    }


def _finance_synthese_export_context(request):
    from django.db.models import Q
    from formations.api_views import (
        _parse_finance_date_range,
        _finance_secretariat_id_from_request,
        _finance_filter_formateur_queryset,
        _finance_report_rows,
        _finance_periode_payload,
        _finance_canonical_volume_kpis,
    )

    period = _parse_finance_date_range(request)
    if period.get('error'):
        return None, period.get('detail') or 'Période invalide.'

    secretariat_id = _finance_secretariat_id_from_request(request)
    queryset = Formateur.objects.prefetch_related('secretariats').order_by('nom', 'prenom')
    queryset = _finance_filter_formateur_queryset(queryset, secretariat_id)
    search = (request.query_params.get('search') or '').strip()
    if search:
        queryset = queryset.filter(
            Q(nom__icontains=search)
            | Q(prenom__icontains=search)
            | Q(specialite__icontains=search)
        )

    formateurs = list(queryset)
    global_agg = {'activite_par_mois': {}, 'date_min': None, 'date_max': None}
    rows = _finance_report_rows(
        formateurs,
        include_sessions=False,
        date_debut=period['date_debut'],
        date_fin=period['date_fin'],
        global_aggregates=global_agg,
        secretariat_id=secretariat_id,
    )
    if request.user.role != 'FINANCE':
        for row in rows:
            row.pop('numero_piece_identite', None)
            row.pop('numero_compte_bancaire', None)

    vh_totals = _finance_canonical_volume_kpis(
        rows,
        date_debut=period['date_debut'],
        date_fin=period['date_fin'],
    )
    totals = {
        'sessions_count': sum(int(r.get('sessions_count') or 0) for r in rows),
        'total_planned': vh_totals['prevu_minutes'],
        'total_realized': vh_totals['realise_minutes'],
        'total_heures_realisees': round(vh_totals['realise_minutes'] / 60, 2),
        'montant_total': round(sum(float(r.get('montant_total_realise') or 0) for r in rows), 2),
        'formateurs_count': len(rows),
        'formateurs_actifs': sum(1 for r in rows if (r.get('sessions_count') or 0) > 0),
    }
    periode_info = _finance_periode_payload(
        period['date_debut'],
        period['date_fin'],
        period['meta'],
        global_agg.get('date_min'),
        global_agg.get('date_max'),
    )
    return {
        'rows': rows,
        'totals': totals,
        'export': _finance_synthese_document_options(request),
        'periode_label': periode_info.get('periode_label') or 'Toutes périodes',
    }, None


def _finance_synthese_table_headers(afficher_montants, include_sensitive=False):
    headers = [
        'N° Badge', 'Nom', 'Prénom', 'Spécialité', 'Grade(s)', 'Groupe(s)', 'Séances',
        'Planifié (min)', 'Réalisé (min)', 'Heures réal.', 'Taux %',
    ]
    if afficher_montants:
        headers.append('Montant (FCFA)')
    if include_sensitive:
        headers.extend(['N° pièce identité', 'N° compte bancaire'])
    return headers


def _finance_synthese_table_row(row, afficher_montants, include_sensitive=False):
    stats = row.get('statistiques') or {}
    values = [
        row.get('numerobadge') or '-',
        row.get('nom') or '',
        row.get('prenom') or '',
        row.get('specialite') or '-',
        row.get('grades') or '-',
        row.get('groupes') or '-',
        row.get('sessions_count') or 0,
        round(float(row.get('total_duree_minutes') or 0), 1),
        round(float(row.get('total_duree_realisee_minutes') or 0), 1),
        round(float(row.get('total_duree_realisee_minutes') or 0) / 60, 2),
        stats.get('taux_realisation_pct', 0),
    ]
    if afficher_montants:
        values.append(round(float(row.get('montant_total_realise') or 0), 2))
    if include_sensitive:
        values.extend([
            row.get('numero_piece_identite') or '-',
            row.get('numero_compte_bancaire') or '-',
        ])
    return values


def _formation_meta(formation):
    """
    Agrège grade / groupe / vague / superviseurs depuis les modules de la formation.
    Ces champs ont été déplacés de Formation vers Module ; cette fonction reconstruit
    une vue unifiée pour les en-têtes des exports.
    """
    modules = list(formation.modules.select_related('superviseur').all())
    grades = sorted({m.grade for m in modules if m.grade})
    groupes = sorted({m.groupe for m in modules if m.groupe})
    vagues = sorted({m.vague for m in modules if m.vague})
    superviseurs = [m.superviseur for m in modules if m.superviseur]
    # Dédoublonner tout en préservant l'ordre d'apparition
    seen, unique_superviseurs = set(), []
    for s in superviseurs:
        if s.pk not in seen:
            seen.add(s.pk)
            unique_superviseurs.append(s)
    return {
        'grade': ', '.join(grades) or '-',
        'groupe': ', '.join(groupes) or '-',
        'vague': ', '.join(vagues) or '-',
        'superviseurs': unique_superviseurs,
    }


def _check_export_access(request, formation):
    """
    Vérifie que l'utilisateur peut exporter les données de cette formation.

    - DFRC (CPFAE_ADMIN / CHEF_CPFAE_ADMIN) : accès complet.
    - DIRECTION / ADMIN                      : accès complet (lecture).
    - SECRETARIAT / CHEF_SECRETARIAT         : uniquement si au moins un module
                                               de la formation appartient au secrétariat
                                               de l'utilisateur.
    - ENCADRANT                              : uniquement si au moins un module
                                               est supervisé par cet utilisateur.
    - AUDITEUR et autres                     : accès refusé.
    """
    user = request.user
    if not user.is_authenticated:
        return False
    if user.role in ('CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'ADMIN', 'DIRECTION'):
        return True
    if user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        secretariat = getattr(user, 'secretariat', None)
        if not secretariat:
            return False
        return Formation.objects.filter(
            pk=formation.pk,
            modules__secretariat=secretariat,
        ).exists()
    if user.role == 'ENCADRANT':
        return Formation.objects.filter(
            pk=formation.pk,
            modules__superviseur=user,
        ).exists()
    return False


def _get_motif_force(pointage):
    """Retourne le motif de forçage d'un pointage depuis AuditLog, ou chaîne vide."""
    if not pointage or pointage.statut != Pointage.Statut.FORCE_DFRC:
        return ''
    log = AuditLog.objects.filter(
        pointage=pointage,
        action__in=['FORCE_ENTREE', 'FORCE_SORTIE'],
    ).order_by('-timestamp').first()
    if log:
        return log.extra.get('motif', '')
    return ''


def _get_formation_data(pk, module_pk=None):
    """Récupère les données de présence pour export (multi-jours, multi-sessions, participants + formateurs).

    Si module_pk est fourni, filtre les données sur ce seul module.
    """
    formation = Formation.objects.get(pk=pk)

    if module_pk is not None:
        participant_filter = {'module_id': module_pk}
        pointage_filter = {'session__module_id': module_pk}
    else:
        participant_filter = {'module__formation': formation}
        pointage_filter = {'session__module__formation': formation}

    attendus_participants = ModuleParticipant.objects.filter(
        **participant_filter
    ).select_related('participant').order_by('participant__nom', 'participant__prenom').distinct()
    attendus_formateurs = ModuleFormateur.objects.filter(
        **participant_filter
    ).select_related('formateur').order_by('formateur__nom', 'formateur__prenom').distinct()

    all_pointages = Pointage.objects.filter(**pointage_filter).order_by(
        'date_journee', 'timestamp_entree'
    )

    from collections import defaultdict
    part_sessions = defaultdict(list)
    fmt_sessions = defaultdict(list)
    dates_set = set()
    for pt in all_pointages:
        if pt.formateur_id:
            fmt_sessions[(pt.formateur_id, pt.date_journee)].append(pt)
        else:
            part_sessions[(pt.participant_id, pt.date_journee)].append(pt)
        dates_set.add(pt.date_journee)

    dates = sorted(dates_set)
    if not dates:
        dates = [datetime.now().date()]

    # Construire la liste unifiée de personnes attendues
    # IMPORTANT: les formateurs doivent apparaître avant les auditeurs dans les exports.
    personnes = []
    for insc in attendus_formateurs:
        personnes.append(('Formateur', insc.formateur, fmt_sessions))
    for insc in attendus_participants:
        personnes.append(('Auditeur', insc.participant, part_sessions))

    rows = []
    total_present_count = 0
    total_row_count = 0

    for jour in dates:
        for role, p, idx in personnes:
            sessions = idx.get((p.id, jour), [])
            total_row_count += 1

            if sessions:
                nb_sessions = len(sessions)

                if nb_sessions == 1:
                    # Session unique — une seule ligne
                    s = sessions[0]
                    duree_min, duree_str, h_entree, h_sortie = _calculer_duree_export(s)
                    if duree_min == 0:
                        rows.append({
                            'date': jour.strftime('%d/%m/%Y'),
                            'role': role,
                            'matricule': getattr(p, 'matricule', None) or getattr(p, 'numero', ''),
                            'nom': p.nom,
                            'prenom': p.prenom,
                            'organisation': getattr(p, 'organisation', '') or '-',
                            'heure_entree': '-',
                            'heure_sortie': '-',
                            'duree_minutes': '-',
                            'statut': 'Absent',
                            'motif': _get_motif_force(s),
                            'is_detail': False,
                        })
                    else:
                        total_present_count += 1
                        rows.append({
                            'date': jour.strftime('%d/%m/%Y'),
                            'role': role,
                            'matricule': getattr(p, 'matricule', None) or getattr(p, 'numero', ''),
                            'nom': p.nom,
                            'prenom': p.prenom,
                            'organisation': getattr(p, 'organisation', '') or '-',
                            'heure_entree': h_entree,
                            'heure_sortie': h_sortie,
                            'duree_minutes': duree_str,
                            'statut': 'En cours' if not s.timestamp_sortie else 'Présent',
                            'motif': _get_motif_force(s),
                            'is_detail': False,
                        })
                else:
                    # Plusieurs sessions — une ligne par session + ligne récap
                    total_duree = 0
                    all_done = True
                    _matricule_p = getattr(p, 'matricule', None) or getattr(p, 'numero', '')
                    for i, s in enumerate(sessions, 1):
                        duree_min, duree_str, h_entree, h_sortie = _calculer_duree_export(s)
                        total_duree += duree_min
                        if not s.timestamp_sortie:
                            all_done = False
                        rows.append({
                            'date': jour.strftime('%d/%m/%Y') if i == 1 else '',
                            'role': role if i == 1 else '',
                            'matricule': _matricule_p if i == 1 else '',
                            'nom': p.nom if i == 1 else '',
                            'prenom': p.prenom if i == 1 else '',
                            'organisation': getattr(p, 'organisation', '') or '-',
                            'heure_entree': h_entree,
                            'heure_sortie': h_sortie,
                            'duree_minutes': duree_str if duree_min > 0 else '-',
                            'statut': f'Session {i}/{nb_sessions}',
                            'motif': _get_motif_force(s),
                            'is_detail': True,
                        })
                    # Ligne récap total
                    if total_duree == 0:
                        rows.append({
                            'date': '',
                            'role': '',
                            'matricule': '',
                            'nom': f'↳ TOTAL {p.nom} {p.prenom}',
                            'prenom': '',
                            'organisation': '',
                            'heure_entree': '',
                            'heure_sortie': '',
                            'duree_minutes': '-',
                            'statut': f'Absent ({nb_sessions} sessions)',
                            'motif': '',
                            'is_detail': False,
                            'is_recap': True,
                        })
                    else:
                        total_present_count += 1
                        statut_recap = 'Présent' if all_done else 'En cours'
                        th = int(total_duree // 60)
                        tm = int(total_duree % 60)
                        total_str = f"{th}h{tm:02d}" if th > 0 else f"{tm} min"
                        rows.append({
                            'date': '',
                            'role': '',
                            'matricule': '',
                            'nom': f'↳ TOTAL {p.nom} {p.prenom}',
                            'prenom': '',
                            'organisation': '',
                            'heure_entree': '',
                            'heure_sortie': '',
                            'duree_minutes': total_str,
                            'statut': f'{statut_recap} ({nb_sessions} sessions)',
                            'motif': '',
                            'is_detail': False,
                            'is_recap': True,
                        })
            else:
                rows.append({
                    'date': jour.strftime('%d/%m/%Y'),
                    'role': role,
                    'matricule': getattr(p, 'matricule', None) or getattr(p, 'numero', ''),
                    'nom': p.nom,
                    'prenom': p.prenom,
                    'organisation': getattr(p, 'organisation', '') or '-',
                    'heure_entree': '-',
                    'heure_sortie': '-',
                    'duree_minutes': '-',
                    'statut': 'Absent',
                    'motif': '',
                    'is_detail': False,
                })

    nb_total = total_row_count
    nb_presents = total_present_count
    taux = round(nb_presents / nb_total * 100, 1) if nb_total > 0 else 0
    stats = {
        'nb_total': nb_total,
        'nb_presents': nb_presents,
        'nb_absents': nb_total - nb_presents,
        'taux': taux,
        'nb_jours': len(dates),
        'nb_participants': attendus_participants.count(),
        'nb_formateurs': attendus_formateurs.count(),
    }
    return formation, rows, stats


# ──────────────────────────────────────────────
# EXPORT PDF
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_pdf(request, pk):
    """Export PDF du rapport de présence d'une formation."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    formation = get_object_or_404(Formation, pk=pk)
    if not _check_export_access(request, formation):
        return Response(
            {'detail': 'Accès non autorisé à cette formation.'},
            status=403,
        )

    meta = _formation_meta(formation)
    _, rows, stats = _get_formation_data(pk)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()

    # Styles personnalisés
    style_ministry = ParagraphStyle(
        'Ministry', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#555555'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_title = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=16, textColor=colors.HexColor(CI_GREEN_DARK),
        alignment=TA_CENTER, spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#444444'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_stats = ParagraphStyle(
        'Stats', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor(CI_GREEN_DARK),
        spaceAfter=2,
    )

    elements = []

    # En-tête ministère
    elements.append(Paragraph(
        "RÉPUBLIQUE DE CÔTE D'IVOIRE", style_ministry
    ))
    elements.append(Paragraph(
        "Ministère de la Fonction Publique et de la Modernisation de l'Administration",
        style_ministry,
    ))
    elements.append(Paragraph(
        "Direction de la Formation et du Renforcement des Compétences (DFRC)",
        style_ministry,
    ))
    elements.append(Spacer(1, 0.4 * cm))

    # Titre formation
    elements.append(Paragraph(
        f"Rapport de présence", style_title,
    ))
    elements.append(Paragraph(
        f"<b>{formation.formation}</b>", style_subtitle,
    ))

    elements.append(Paragraph(
        f"Grade : {meta['grade']} &nbsp;|&nbsp; "
        f"Groupe : {meta['groupe']} &nbsp;|&nbsp; "
        f"Vague : {meta['vague']}",
        style_subtitle,
    ))
    for sup in meta['superviseurs']:
        elements.append(Paragraph(
            f"Superviseur : {sup.get_full_name()}",
            style_subtitle,
        ))
    # Tableau des sessions superviseur (par journée)
    all_sf = SessionModule.objects.filter(module__formation=formation).order_by('date_journee', 'numero')
    if all_sf.exists():
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("<b>Sessions superviseur</b>", style_stats))
        sf_header = ['Date', 'Session', 'Démarrée à', 'Terminée à', 'Durée (min)']
        sf_data = [sf_header]
        for sf in all_sf:
            duree = sf.duree_minutes
            sf_data.append([
                sf.date_journee.strftime('%d/%m/%Y'),
                f'Session {sf.numero}',
                sf.demarree_le.strftime('%H:%M') if sf.demarree_le else '-',
                sf.terminee_le.strftime('%H:%M') if sf.terminee_le else 'En cours',
                str(duree) if duree else '-',
            ])
        sf_col_widths = [3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm]
        sf_table = Table(sf_data, colWidths=sf_col_widths)
        sf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_ORANGE)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(CI_LIGHT_ORANGE)]),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sf_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Styles cellules tableau (Paragraph → word wrap automatique)
    cell_normal = ParagraphStyle(
        'CellNormal', parent=styles['Normal'],
        fontSize=8, leading=10,
    )
    cell_center = ParagraphStyle(
        'CellCenter', parent=styles['Normal'],
        fontSize=8, leading=10, alignment=TA_CENTER,
    )
    cell_header = ParagraphStyle(
        'CellHeader', parent=styles['Normal'],
        fontSize=9, leading=11, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )

    def _p(text, center=False, hdr=False):
        s = cell_header if hdr else (cell_center if center else cell_normal)
        return Paragraph(str(text), s)

    # Tableau
    header = ['Date', 'Rôle', "N° d'inscription", 'Nom', 'Prénom', 'Entrée', 'Sortie', 'Durée (min)', 'Statut', 'Motif (forçage)']
    data = [[_p(h, hdr=True) for h in header]]
    for r in rows:
        data.append([
            _p(r['date'], center=True),
            _p(r['role'], center=True),
            _p(r['matricule'], center=True),
            _p(r['nom']),
            _p(r['prenom']),
            _p(r['heure_entree'], center=True),
            _p(r['heure_sortie'], center=True),
            _p(r['duree_minutes'], center=True),
            _p(r['statut'], center=True),
            _p(r.get('motif', '') or ''),
        ])

    # Largeurs : total 26.7 cm (A4 paysage 29.7 cm − 3 cm marges)
    col_widths = [2.2 * cm, 2.2 * cm, 3.4 * cm, 4.2 * cm, 4.2 * cm, 1.8 * cm, 1.8 * cm, 2.1 * cm, 2.1 * cm, 2.7 * cm]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    base_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_GREEN_DARK)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor(CI_LIGHT_GREEN)]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]
    # Style detail session rows (light orange) and recap rows (orange bold)
    for i, r in enumerate(rows):
        row_idx = i + 1  # +1 for header row
        if r.get('is_detail'):
            base_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(CI_LIGHT_ORANGE)))
            base_style.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Oblique'))
        elif r.get('is_recap'):
            base_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(CI_LIGHT_ORANGE)))
            base_style.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
            base_style.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.HexColor(CI_ORANGE)))
        if r.get('motif'):
            base_style.append(('TEXTCOLOR', (9, row_idx), (9, row_idx), colors.HexColor(CI_ORANGE)))
            base_style.append(('FONTNAME', (9, row_idx), (9, row_idx), 'Helvetica-Oblique'))
    table.setStyle(TableStyle(base_style))
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))

    # Statistiques
    elements.append(Paragraph(
        f"<b>Résumé :</b> {stats.get('nb_participants', '-')} participants, "
        f"{stats.get('nb_formateurs', 0)} formateur(s) &nbsp;|&nbsp; "
        f"{stats.get('nb_jours', 1)} jour(s) &nbsp;|&nbsp; "
        f"Présences : {stats['nb_presents']}/{stats['nb_total']} &nbsp;|&nbsp; "
        f"Taux global : <b>{stats['taux']}%</b>",
        style_stats,
    ))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        f"<i>Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                       textColor=colors.HexColor('#999999')),
    ))

    doc.build(elements)
    buffer.seek(0)

    filename = f"rapport_presence_{formation.id}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ──────────────────────────────────────────────
# EXPORT EXCEL
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_excel(request, pk):
    """Export Excel du rapport de présence d'une formation."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    formation = get_object_or_404(Formation, pk=pk)
    if not _check_export_access(request, formation):
        return Response(
            {'detail': 'Accès non autorisé à cette formation.'},
            status=403,
        )

    meta = _formation_meta(formation)
    _, rows, stats = _get_formation_data(pk)

    wb = Workbook()
    ws = wb.active
    ws.title = "Présences"

    # Couleurs branding
    green_fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
    orange_fill = PatternFill(start_color='F57C00', end_color='F57C00', fill_type='solid')
    light_green_fill = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')
    light_orange_fill = PatternFill(start_color='FFF3E0', end_color='FFF3E0', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=10)
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    # En-tête ministère
    ws.merge_cells('A1:J1')
    ws['A1'] = "RÉPUBLIQUE DE CÔTE D'IVOIRE — Ministère de la Fonction Publique"
    ws['A1'].font = Font(size=9, color='555555')
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:J2')
    ws['A2'] = "Direction de la Formation et du Renforcement des Compétences (DFRC)"
    ws['A2'].font = Font(size=9, color='555555')
    ws['A2'].alignment = Alignment(horizontal='center')

    # Titre formation
    ws.merge_cells('A3:J3')
    ws['A3'] = f"Rapport de présence — {formation.formation}"
    ws['A3'].font = Font(bold=True, size=14, color='388E3C')
    ws['A3'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A4:J4')
    ws['A4'] = f"Grade : {meta['grade']} | Groupe : {meta['groupe']} | Vague : {meta['vague']}"
    ws['A4'].font = Font(size=10, color='444444')
    ws['A4'].alignment = Alignment(horizontal='center')

    next_row = 5
    for sup in meta['superviseurs']:
        ws.merge_cells(start_row=next_row, start_column=1, end_row=next_row, end_column=10)
        ws.cell(row=next_row, column=1, value=f"Superviseur : {sup.get_full_name()}")
        ws.cell(row=next_row, column=1).font = Font(size=10, color='444444')
        ws.cell(row=next_row, column=1).alignment = Alignment(horizontal='center')
        next_row += 1

    # Tableau des sessions superviseur
    all_sf = SessionModule.objects.filter(module__formation=formation).order_by('date_journee', 'numero')
    if all_sf.exists():
        ws.merge_cells(start_row=next_row, start_column=1, end_row=next_row, end_column=5)
        ws.cell(row=next_row, column=1, value="Sessions superviseur")
        ws.cell(row=next_row, column=1).font = Font(bold=True, size=10, color='F57C00')
        next_row += 1
        sf_headers = ['Date', 'Session', 'Démarrée à', 'Terminée à', 'Durée (min)']
        for col, h in enumerate(sf_headers, 1):
            cell = ws.cell(row=next_row, column=col, value=h)
            cell.font = Font(bold=True, color='FFFFFF', size=9)
            cell.fill = orange_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        next_row += 1
        for sf in all_sf:
            duree = sf.duree_minutes
            sf_vals = [
                sf.date_journee.strftime('%d/%m/%Y'),
                f'Session {sf.numero}',
                sf.demarree_le.strftime('%H:%M') if sf.demarree_le else '-',
                sf.terminee_le.strftime('%H:%M') if sf.terminee_le else 'En cours',
                str(duree) if duree else '-',
            ]
            for col, val in enumerate(sf_vals, 1):
                cell = ws.cell(row=next_row, column=col, value=val)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='center')
                if not sf.terminee_le:
                    cell.font = Font(bold=True, color='F57C00')
                else:
                    cell.fill = light_orange_fill
            next_row += 1
        next_row += 1

    data_start_row = next_row

    # En-têtes colonnes
    headers = ['Date', 'Rôle', "N° d'inscription", 'Nom', 'Prénom', 'Organisation', 'Entrée', 'Sortie', 'Durée (min)', 'Statut', 'Motif (forçage)']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=data_start_row, column=col, value=h)
        cell.font = header_font
        cell.fill = green_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    # Données
    for i, r in enumerate(rows):
        row_num = data_start_row + 1 + i
        values = [
            r['date'], r['role'], r.get('numero', r.get('matricule', '')), r['nom'], r['prenom'], r['organisation'],
            r['heure_entree'], r['heure_sortie'], r['duree_minutes'], r['statut'], r.get('motif', '') or '',
        ]
        is_detail = r.get('is_detail', False)
        is_recap = r.get('is_recap', False)

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
            if col >= 7:
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # Session detail rows: light orange + italic
            if is_detail:
                cell.fill = light_orange_fill
                cell.font = Font(italic=True, size=10)
            # Recap rows: light orange + bold orange
            elif is_recap:
                cell.fill = light_orange_fill
                cell.font = Font(bold=True, color='F57C00', size=10)
            # Normal rows: alternating colors
            elif i % 2 == 1:
                cell.fill = light_green_fill

        # Colorer le statut (sauf detail/recap déjà stylés)
        if not is_detail and not is_recap:
            statut_cell = ws.cell(row=row_num, column=10)
            if r['statut'] == 'Absent':
                statut_cell.font = Font(color='C62828', bold=True)
            elif 'En cours' in r['statut']:
                statut_cell.font = Font(color='F57C00', bold=True)
            else:
                statut_cell.font = Font(color='388E3C', bold=True)
            if r.get('motif'):
                ws.cell(row=row_num, column=11).font = Font(color='F57C00', italic=True, size=10)

    # Ligne résumé
    summary_row = data_start_row + 1 + len(rows) + 1
    ws.merge_cells(start_row=summary_row, start_column=1, end_row=summary_row, end_column=6)
    ws.cell(row=summary_row, column=1, value="RÉSUMÉ").font = Font(bold=True, size=10)

    labels = [
        (7, f"Jours: {stats.get('nb_jours', 1)}"),
        (8, f"Présents: {stats['nb_presents']}"),
        (9, f"Absents: {stats['nb_absents']}"),
        (10, f"Taux: {stats['taux']}%"),
    ]
    for col, val in labels:
        cell = ws.cell(row=summary_row, column=col, value=val)
        cell.font = Font(bold=True, size=10, color='FFFFFF')
        cell.fill = orange_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Date d'export
    footer_row = summary_row + 1
    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=11)
    ws.cell(row=footer_row, column=1,
            value=f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}").font = Font(
        size=8, color='999999', italic=True)

    # Largeur colonnes
    col_widths = {'A': 12, 'B': 12, 'C': 10, 'D': 16, 'E': 16, 'F': 18, 'G': 10, 'H': 10, 'I': 12, 'J': 14, 'K': 28}
    for letter, width in col_widths.items():
        ws.column_dimensions[letter].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"rapport_presence_{formation.id}.xlsx"
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ──────────────────────────────────────────────
# MODULE-BASED EXPORTS (toutes séances d'un module)
# ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_pdf_module(request, module_pk):
    """Export PDF du rapport de présence d'un module (toutes ses séances)."""
    from formations.models import Module
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    module = get_object_or_404(Module.objects.select_related('formation', 'superviseur'), pk=module_pk)
    formation = module.formation

    if not _check_export_access(request, formation):
        return Response(
            {'detail': 'Accès non autorisé à ce module.'},
            status=403,
        )

    meta = {
        'grade': module.grade or '-',
        'groupe': module.groupe or '-',
        'vague': module.vague or '-',
        'superviseurs': [module.superviseur] if module.superviseur else [],
    }
    _, rows, stats = _get_formation_data(formation.pk, module_pk=module_pk)
    all_sf = SessionModule.objects.filter(module=module).order_by('date_journee', 'numero')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()

    style_ministry = ParagraphStyle(
        'Ministry_m', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#555555'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_title = ParagraphStyle(
        'CustomTitle_m', parent=styles['Title'],
        fontSize=16, textColor=colors.HexColor(CI_GREEN_DARK),
        alignment=TA_CENTER, spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        'Subtitle_m', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#444444'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_stats = ParagraphStyle(
        'Stats_m', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor(CI_GREEN_DARK),
        spaceAfter=2,
    )

    elements = []
    elements.append(Paragraph("RÉPUBLIQUE DE CÔTE D'IVOIRE", style_ministry))
    elements.append(Paragraph(
        "Ministère de la Fonction Publique et de la Modernisation de l'Administration",
        style_ministry,
    ))
    elements.append(Paragraph(
        "Direction de la Formation et du Renforcement des Compétences (DFRC)",
        style_ministry,
    ))
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("Rapport de présence — Module", style_title))
    elements.append(Paragraph(f"<b>{module.intitule}</b>", style_subtitle))
    elements.append(Paragraph(f"Formation : {formation.formation}", style_subtitle))
    elements.append(Paragraph(
        f"Grade : {meta['grade']} &nbsp;|&nbsp; "
        f"Groupe : {meta['groupe']} &nbsp;|&nbsp; "
        f"Vague : {meta['vague']}",
        style_subtitle,
    ))
    for sup in meta['superviseurs']:
        elements.append(Paragraph(f"Encadrant : {sup.get_full_name()}", style_subtitle))

    if all_sf.exists():
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("<b>Séances du module</b>", style_stats))
        sf_header = ['Date', 'Séance', 'Démarrée à', 'Terminée à', 'Durée (min)']
        sf_data = [sf_header]
        for sf in all_sf:
            duree = sf.duree_minutes
            sf_data.append([
                sf.date_journee.strftime('%d/%m/%Y'),
                sf.intitule or f'Séance {sf.numero}',
                sf.demarree_le.strftime('%H:%M') if sf.demarree_le else '-',
                sf.terminee_le.strftime('%H:%M') if sf.terminee_le else 'En cours',
                str(duree) if duree else '-',
            ])
        sf_col_widths = [3 * cm, 5 * cm, 3 * cm, 3 * cm, 3 * cm]
        sf_table = Table(sf_data, colWidths=sf_col_widths)
        sf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_ORANGE)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(CI_LIGHT_ORANGE)]),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sf_table)
    elements.append(Spacer(1, 0.5 * cm))

    cell_normal = ParagraphStyle('CellNormalM', parent=styles['Normal'], fontSize=8, leading=10)
    cell_center = ParagraphStyle('CellCenterM', parent=styles['Normal'], fontSize=8, leading=10, alignment=TA_CENTER)
    cell_header = ParagraphStyle(
        'CellHeaderM', parent=styles['Normal'],
        fontSize=9, leading=11, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )

    def _p(text, center=False, hdr=False):
        s = cell_header if hdr else (cell_center if center else cell_normal)
        return Paragraph(str(text), s)

    header = ['Date', 'Rôle', "N° d'inscription", 'Nom', 'Prénom', 'Entrée', 'Sortie', 'Durée (min)', 'Statut', 'Motif (forçage)']
    data = [[_p(h, hdr=True) for h in header]]
    for r in rows:
        data.append([
            _p(r['date'], center=True),
            _p(r['role'], center=True),
            _p(r['matricule'], center=True),
            _p(r['nom']),
            _p(r['prenom']),
            _p(r['heure_entree'], center=True),
            _p(r['heure_sortie'], center=True),
            _p(r['duree_minutes'], center=True),
            _p(r['statut'], center=True),
            _p(r.get('motif', '') or ''),
        ])

    col_widths = [2.2 * cm, 2.2 * cm, 3.4 * cm, 4.2 * cm, 4.2 * cm, 1.8 * cm, 1.8 * cm, 2.1 * cm, 2.1 * cm, 2.7 * cm]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    base_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_GREEN_DARK)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(CI_LIGHT_GREEN)]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]
    for i, r in enumerate(rows):
        row_idx = i + 1
        if r.get('is_detail'):
            base_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(CI_LIGHT_ORANGE)))
            base_style.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Oblique'))
        elif r.get('is_recap'):
            base_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(CI_LIGHT_ORANGE)))
            base_style.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
            base_style.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.HexColor(CI_ORANGE)))
        if r.get('motif'):
            base_style.append(('TEXTCOLOR', (9, row_idx), (9, row_idx), colors.HexColor(CI_ORANGE)))
            base_style.append(('FONTNAME', (9, row_idx), (9, row_idx), 'Helvetica-Oblique'))
    table.setStyle(TableStyle(base_style))
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph(
        f"<b>Résumé :</b> {stats.get('nb_participants', '-')} auditeur(s), "
        f"{stats.get('nb_formateurs', 0)} formateur(s) &nbsp;|&nbsp; "
        f"{stats.get('nb_jours', 1)} jour(s) &nbsp;|&nbsp; "
        f"Présences : {stats['nb_presents']}/{stats['nb_total']} &nbsp;|&nbsp; "
        f"Taux global : <b>{stats['taux']}%</b>",
        style_stats,
    ))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        f"<i>Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>",
        ParagraphStyle('FooterM', parent=styles['Normal'], fontSize=7,
                       textColor=colors.HexColor('#999999')),
    ))

    doc.build(elements)
    buffer.seek(0)

    filename = f"rapport_module_{module.pk}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_excel_module(request, module_pk):
    """Export Excel du rapport de présence d'un module (toutes ses séances)."""
    from formations.models import Module
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    module = get_object_or_404(Module.objects.select_related('formation', 'superviseur'), pk=module_pk)
    formation = module.formation

    if not _check_export_access(request, formation):
        return Response(
            {'detail': 'Accès non autorisé à ce module.'},
            status=403,
        )

    meta = {
        'grade': module.grade or '-',
        'groupe': module.groupe or '-',
        'vague': module.vague or '-',
        'superviseurs': [module.superviseur] if module.superviseur else [],
    }
    _, rows, stats = _get_formation_data(formation.pk, module_pk=module_pk)
    all_sf = SessionModule.objects.filter(module=module).order_by('date_journee', 'numero')

    wb = Workbook()
    ws = wb.active
    ws.title = "Présences"

    green_fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
    orange_fill = PatternFill(start_color='F57C00', end_color='F57C00', fill_type='solid')
    light_green_fill = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')
    light_orange_fill = PatternFill(start_color='FFF3E0', end_color='FFF3E0', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=10)
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    ws.merge_cells('A1:J1')
    ws['A1'] = "RÉPUBLIQUE DE CÔTE D'IVOIRE — Ministère de la Fonction Publique"
    ws['A1'].font = Font(size=9, color='555555')
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:J2')
    ws['A2'] = "Direction de la Formation et du Renforcement des Compétences (DFRC)"
    ws['A2'].font = Font(size=9, color='555555')
    ws['A2'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A3:J3')
    ws['A3'] = f"Rapport de présence — Module : {module.intitule}"
    ws['A3'].font = Font(bold=True, size=14, color='388E3C')
    ws['A3'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A4:J4')
    ws['A4'] = f"Formation : {formation.formation}"
    ws['A4'].font = Font(size=11, color='388E3C')
    ws['A4'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A5:J5')
    ws['A5'] = f"Grade : {meta['grade']} | Groupe : {meta['groupe']} | Vague : {meta['vague']}"
    ws['A5'].font = Font(size=10, color='444444')
    ws['A5'].alignment = Alignment(horizontal='center')

    next_row = 6
    for sup in meta['superviseurs']:
        ws.merge_cells(start_row=next_row, start_column=1, end_row=next_row, end_column=10)
        ws.cell(row=next_row, column=1, value=f"Encadrant : {sup.get_full_name()}")
        ws.cell(row=next_row, column=1).font = Font(size=10, color='444444')
        ws.cell(row=next_row, column=1).alignment = Alignment(horizontal='center')
        next_row += 1

    if all_sf.exists():
        ws.merge_cells(start_row=next_row, start_column=1, end_row=next_row, end_column=5)
        ws.cell(row=next_row, column=1, value="Séances du module")
        ws.cell(row=next_row, column=1).font = Font(bold=True, size=10, color='F57C00')
        next_row += 1
        sf_headers = ['Date', 'Séance', 'Démarrée à', 'Terminée à', 'Durée (min)']
        for col, h in enumerate(sf_headers, 1):
            cell = ws.cell(row=next_row, column=col, value=h)
            cell.font = Font(bold=True, color='FFFFFF', size=9)
            cell.fill = orange_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        next_row += 1
        for sf in all_sf:
            duree = sf.duree_minutes
            sf_vals = [
                sf.date_journee.strftime('%d/%m/%Y'),
                sf.intitule or f'Séance {sf.numero}',
                sf.demarree_le.strftime('%H:%M') if sf.demarree_le else '-',
                sf.terminee_le.strftime('%H:%M') if sf.terminee_le else 'En cours',
                str(duree) if duree else '-',
            ]
            for col, val in enumerate(sf_vals, 1):
                cell = ws.cell(row=next_row, column=col, value=val)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='center')
                if not sf.terminee_le:
                    cell.font = Font(bold=True, color='F57C00')
                else:
                    cell.fill = light_orange_fill
            next_row += 1
        next_row += 1

    data_start_row = next_row

    headers = ['Date', 'Rôle', "N° d'inscription", 'Nom', 'Prénom', 'Organisation', 'Entrée', 'Sortie', 'Durée (min)', 'Statut', 'Motif (forçage)']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=data_start_row, column=col, value=h)
        cell.font = header_font
        cell.fill = green_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    for i, r in enumerate(rows):
        row_num = data_start_row + 1 + i
        values = [
            r['date'], r['role'], r.get('numero', r.get('matricule', '')), r['nom'], r['prenom'], r['organisation'],
            r['heure_entree'], r['heure_sortie'], r['duree_minutes'], r['statut'], r.get('motif', '') or '',
        ]
        is_detail = r.get('is_detail', False)
        is_recap = r.get('is_recap', False)

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
            if col >= 7:
                cell.alignment = Alignment(horizontal='center', vertical='center')
            if is_detail:
                cell.fill = light_orange_fill
                cell.font = Font(italic=True, size=10)
            elif is_recap:
                cell.fill = light_orange_fill
                cell.font = Font(bold=True, color='F57C00', size=10)
            elif i % 2 == 1:
                cell.fill = light_green_fill

        if not is_detail and not is_recap:
            statut_cell = ws.cell(row=row_num, column=10)
            if r['statut'] == 'Absent':
                statut_cell.font = Font(color='C62828', bold=True)
            elif 'En cours' in r['statut']:
                statut_cell.font = Font(color='F57C00', bold=True)
            else:
                statut_cell.font = Font(color='388E3C', bold=True)
            if r.get('motif'):
                ws.cell(row=row_num, column=11).font = Font(color='F57C00', italic=True, size=10)

    summary_row = data_start_row + 1 + len(rows) + 1
    ws.merge_cells(start_row=summary_row, start_column=1, end_row=summary_row, end_column=6)
    ws.cell(row=summary_row, column=1, value="RÉSUMÉ").font = Font(bold=True, size=10)

    labels = [
        (7, f"Jours: {stats.get('nb_jours', 1)}"),
        (8, f"Présents: {stats['nb_presents']}"),
        (9, f"Absents: {stats['nb_absents']}"),
        (10, f"Taux: {stats['taux']}%"),
    ]
    for col, val in labels:
        cell = ws.cell(row=summary_row, column=col, value=val)
        cell.font = Font(bold=True, size=10, color='FFFFFF')
        cell.fill = orange_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    footer_row = summary_row + 1
    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=11)
    ws.cell(row=footer_row, column=1,
            value=f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}").font = Font(
        size=8, color='999999', italic=True)

    col_widths = {'A': 12, 'B': 12, 'C': 10, 'D': 16, 'E': 16, 'F': 18, 'G': 10, 'H': 10, 'I': 12, 'J': 14, 'K': 28}
    for letter, width in col_widths.items():
        ws.column_dimensions[letter].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"rapport_module_{module.pk}.xlsx"
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ──────────────────────────────────────────────
# SESSION-BASED EXPORTS
# ──────────────────────────────────────────────

def _get_session_data(session_pk):
    """Récupère les données de présence pour export d'une session spécifique."""
    session = SessionModule.objects.select_related('module__formation').get(pk=session_pk)
    formation = session.module.formation

    # Récupérer tous les pointages pour cette session
    all_pointages = Pointage.objects.filter(
        session=session,
    ).order_by('timestamp_entree')

    # Participants attendus
    attendus_participants = ModuleParticipant.objects.filter(
        module=session.module
    ).select_related('participant').order_by('participant__nom', 'participant__prenom').distinct()

    # Formateurs attendus = formateur principal + formateurs assignés au module
    _module = session.module
    attendus_formateurs_list = []
    seen_formateur_ids = set()

    formateur_du_module = _module.formateur if _module and _module.formateur else None
    if formateur_du_module:
        attendus_formateurs_list.append(formateur_du_module)
        seen_formateur_ids.add(formateur_du_module.id)

    formateurs_assignes = ModuleFormateur.objects.filter(
        module=session.module
    ).select_related('formateur').order_by('formateur__nom', 'formateur__prenom').distinct()
    for insc in formateurs_assignes:
        if insc.formateur_id and insc.formateur_id not in seen_formateur_ids:
            attendus_formateurs_list.append(insc.formateur)
            seen_formateur_ids.add(insc.formateur_id)

    from collections import defaultdict
    part_sessions = defaultdict(list)
    fmt_sessions = defaultdict(list)

    for pt in all_pointages:
        if pt.formateur_id:
            fmt_sessions[pt.formateur_id].append(pt)
        else:
            part_sessions[pt.participant_id].append(pt)

    # Construire la liste unifiée de personnes attendues
    # IMPORTANT: le formateur doit apparaître avant les auditeurs dans les exports.
    personnes = []
    for fmt in attendus_formateurs_list:
        personnes.append(('Formateur', fmt, fmt_sessions))
    for insc in attendus_participants:
        personnes.append(('Auditeur', insc.participant, part_sessions))

    rows = []
    total_present_count = 0
    total_row_count = 0

    for role, p, idx in personnes:
        sessions = idx.get(p.id, [])
        total_row_count += 1

        if sessions:
            nb_sessions = len(sessions)

            if nb_sessions == 1:
                s = sessions[0]
                duree_min, duree_str, h_entree, h_sortie = _calculer_duree_export(s)
                if duree_min == 0:
                    rows.append({
                        'date': session.date_journee.strftime('%d/%m/%Y'),
                        'role': role,
                        'matricule': getattr(p, 'matricule', None) or getattr(p, 'numero', ''),
                        'nom': p.nom,
                        'prenom': p.prenom,
                        'organisation': getattr(p, 'organisation', '') or '-',
                        'heure_entree': '-',
                        'heure_sortie': '-',
                        'duree_minutes': '-',
                        'statut': 'Absent',
                        'motif': _get_motif_force(s),
                        'is_detail': False,
                    })
                else:
                    total_present_count += 1
                    rows.append({
                        'date': session.date_journee.strftime('%d/%m/%Y'),
                        'role': role,
                        'matricule': getattr(p, 'matricule', None) or getattr(p, 'numero', ''),
                        'nom': p.nom,
                        'prenom': p.prenom,
                        'organisation': getattr(p, 'organisation', '') or '-',
                        'heure_entree': h_entree,
                        'heure_sortie': h_sortie,
                        'duree_minutes': duree_str,
                        'statut': 'En cours' if not s.timestamp_sortie else 'Présent',
                        'motif': _get_motif_force(s),
                        'is_detail': False,
                    })
            else:
                total_duree = 0
                all_done = True
                _matricule_p2 = getattr(p, 'matricule', None) or getattr(p, 'numero', '')
                for i, s in enumerate(sessions, 1):
                    duree_min, duree_str, h_entree, h_sortie = _calculer_duree_export(s)
                    total_duree += duree_min
                    if not s.timestamp_sortie:
                        all_done = False
                    rows.append({
                        'date': session.date_journee.strftime('%d/%m/%Y'),
                        'role': role,
                        'matricule': _matricule_p2,
                        'nom': p.nom,
                        'prenom': p.prenom,
                        'organisation': getattr(p, 'organisation', '') or '-',
                        'heure_entree': h_entree,
                        'heure_sortie': h_sortie,
                        'duree_minutes': duree_str if duree_min > 0 else '-',
                        'statut': f'Session {i}/{nb_sessions}',
                        'motif': _get_motif_force(s),
                        'is_detail': True,
                    })
                if total_duree == 0:
                    rows.append({
                        'date': '',
                        'role': '',
                        'matricule': '',
                        'nom': f'↳ TOTAL {p.nom} {p.prenom}',
                        'prenom': '',
                        'organisation': '',
                        'heure_entree': '',
                        'heure_sortie': '',
                        'duree_minutes': '-',
                        'statut': f'Absent ({nb_sessions} sessions)',
                        'motif': '',
                        'is_detail': False,
                        'is_recap': True,
                    })
                else:
                    total_present_count += 1
                    statut_recap = 'Présent' if all_done else 'En cours'
                    th = int(total_duree // 60)
                    tm = int(total_duree % 60)
                    total_str = f"{th}h{tm:02d}" if th > 0 else f"{tm} min"
                    rows.append({
                        'date': '',
                        'role': '',
                        'matricule': '',
                        'nom': f'↳ TOTAL {p.nom} {p.prenom}',
                        'prenom': '',
                        'organisation': '',
                        'heure_entree': '',
                        'heure_sortie': '',
                        'duree_minutes': total_str,
                        'statut': f'{statut_recap} ({nb_sessions} sessions)',
                        'motif': '',
                        'is_detail': False,
                        'is_recap': True,
                    })
        else:
            rows.append({
                'date': session.date_journee.strftime('%d/%m/%Y'),
                'role': role,
                'matricule': getattr(p, 'matricule', None) or getattr(p, 'numero', ''),
                'nom': p.nom,
                'prenom': p.prenom,
                'organisation': getattr(p, 'organisation', '') or '-',
                'heure_entree': '-',
                'heure_sortie': '-',
                'duree_minutes': '-',
                'statut': 'Absent',
                'motif': '',
                'is_detail': False,
            })

    nb_total = total_row_count
    nb_presents = total_present_count
    taux = round(nb_presents / nb_total * 100, 1) if nb_total > 0 else 0
    stats = {
        'nb_total': nb_total,
        'nb_presents': nb_presents,
        'nb_absents': nb_total - nb_presents,
        'taux': taux,
        'nb_jours': 1,
        'nb_participants': attendus_participants.count(),
        'nb_formateurs': len(attendus_formateurs_list),
    }
    return session, formation, rows, stats


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_pdf_session(request, session_pk):
    """Export PDF du rapport de présence d'une session de formation."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    session = get_object_or_404(SessionModule.objects.select_related('module__formation'), pk=session_pk)
    formation = session.module.formation
    if not _check_export_access(request, formation):
        return Response(
            {'detail': 'Accès non autorisé à cette formation.'},
            status=403,
        )

    _, _, rows, stats = _get_session_data(session_pk)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()

    style_ministry = ParagraphStyle(
        'Ministry', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#555555'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_title = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=16, textColor=colors.HexColor(CI_GREEN_DARK),
        alignment=TA_CENTER, spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#444444'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_stats = ParagraphStyle(
        'Stats', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor(CI_GREEN_DARK),
        spaceAfter=2,
    )

    elements = []

    # En-tête ministère
    elements.append(Paragraph(
        "RÉPUBLIQUE DE CÔTE D'IVOIRE", style_ministry
    ))
    elements.append(Paragraph(
        "Ministère de la Fonction Publique et de la Modernisation de l'Administration",
        style_ministry,
    ))
    elements.append(Paragraph(
        "Direction de la Formation et du Renforcement des Compétences (DFRC)",
        style_ministry,
    ))
    elements.append(Spacer(1, 0.4 * cm))

    # Titre session
    session_label = session.intitule or f"Session {session.numero}"
    elements.append(Paragraph(
        f"Rapport de présence — Session", style_title,
    ))
    elements.append(Paragraph(
        f"<b>{formation.formation}</b>", style_subtitle,
    ))
    elements.append(Paragraph(
        f"{session.date_journee.strftime('%d/%m/%Y')} — {session_label}",
        style_subtitle,
    ))

    _mod = session.module if session.module else None
    _s_site = (_mod.site     if _mod and _mod.site     else '') or ''
    _s_bat  = (_mod.batiment if _mod and _mod.batiment else '') or ''
    _s_sal  = (_mod.salle    if _mod and _mod.salle    else '') or ''
    _mod_lbl = (_mod.intitule if _mod else '') or ''
    _mod_grade = (_mod.grade if _mod and _mod.grade else '') or ''
    _mod_groupe = (_mod.groupe if _mod and _mod.groupe else '') or ''
    _heure_debut = session.heure_debut_prevue.strftime('%H:%M') if session.heure_debut_prevue else '-'
    _heure_fin = session.heure_fin_prevue.strftime('%H:%M') if session.heure_fin_prevue else '-'
    _date_seance = session.date_journee.strftime('%d/%m/%Y')
    # Infos session
    if _mod_lbl or _mod_grade or _mod_groupe:
        elements.append(Paragraph(
            f"Module : <b>{_mod_lbl or '-'}</b> &nbsp;|&nbsp; "
            f"Grade : <b>{_mod_grade or '-'}</b> &nbsp;|&nbsp; "
            f"Groupe : <b>{_mod_groupe or '-'}</b>",
            style_subtitle,
        ))
    elements.append(Paragraph(
        f"Date séance : {_date_seance} &nbsp;|&nbsp; Heures séance : {_heure_debut} - {_heure_fin}",
        style_subtitle,
    ))
    elements.append(Paragraph(
        f"Site : {_s_site or '-'} | Bât. : {_s_bat or '-'} | Salle : {_s_sal or '-'} &nbsp;|&nbsp; "
        f"Début prévu : {_heure_debut} &nbsp;|&nbsp; "
        f"Fin prévue : {_heure_fin}",
        style_subtitle,
    ))
    if session.demarree_le:
        elements.append(Paragraph(
            f"Démarrée à : {session.demarree_le.strftime('%H:%M')} &nbsp;|&nbsp; "
            f"Terminée à : {session.terminee_le.strftime('%H:%M') if session.terminee_le else 'En cours'}",
            style_subtitle,
        ))

    elements.append(Spacer(1, 0.5 * cm))

    # Styles cellules tableau (Paragraph → word wrap automatique)
    cell_normal = ParagraphStyle(
        'CellNormal2', parent=styles['Normal'],
        fontSize=8, leading=10,
    )
    cell_center = ParagraphStyle(
        'CellCenter2', parent=styles['Normal'],
        fontSize=8, leading=10, alignment=TA_CENTER,
    )
    cell_header = ParagraphStyle(
        'CellHeader2', parent=styles['Normal'],
        fontSize=9, leading=11, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )

    def _p(text, center=False, hdr=False):
        s = cell_header if hdr else (cell_center if center else cell_normal)
        return Paragraph(str(text), s)

    # Tableau
    header = ['Date', 'Rôle', "N° d'inscription", 'Nom', 'Prénom', 'Entrée', 'Sortie', 'Durée (min)', 'Statut', 'Motif (forçage)']
    data = [[_p(h, hdr=True) for h in header]]
    for r in rows:
        data.append([
            _p(r['date'], center=True),
            _p(r['role'], center=True),
            _p(r['matricule'], center=True),
            _p(r['nom']),
            _p(r['prenom']),
            _p(r['heure_entree'], center=True),
            _p(r['heure_sortie'], center=True),
            _p(r['duree_minutes'], center=True),
            _p(r['statut'], center=True),
            _p(r.get('motif', '') or ''),
        ])

    # Largeurs : total 26.7 cm (A4 paysage 29.7 cm − 3 cm marges)
    col_widths = [2.2 * cm, 2.2 * cm, 3.4 * cm, 4.2 * cm, 4.2 * cm, 1.8 * cm, 1.8 * cm, 2.1 * cm, 2.1 * cm, 2.7 * cm]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    base_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_GREEN_DARK)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor(CI_LIGHT_GREEN)]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]
    for i, r in enumerate(rows):
        row_idx = i + 1
        if r.get('is_detail'):
            base_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(CI_LIGHT_ORANGE)))
            base_style.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Oblique'))
        elif r.get('is_recap'):
            base_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(CI_LIGHT_ORANGE)))
            base_style.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
            base_style.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.HexColor(CI_ORANGE)))
        if r.get('motif'):
            base_style.append(('TEXTCOLOR', (9, row_idx), (9, row_idx), colors.HexColor(CI_ORANGE)))
            base_style.append(('FONTNAME', (9, row_idx), (9, row_idx), 'Helvetica-Oblique'))
    table.setStyle(TableStyle(base_style))
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))

    # Statistiques
    elements.append(Paragraph(
        f"<b>Résumé :</b> {stats.get('nb_participants', '-')} participants, "
        f"{stats.get('nb_formateurs', 0)} formateur(s) &nbsp;|&nbsp; "
        f"Présences : {stats['nb_presents']}/{stats['nb_total']} &nbsp;|&nbsp; "
        f"Taux : <b>{stats['taux']}%</b>",
        style_stats,
    ))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        f"<i>Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                       textColor=colors.HexColor('#999999')),
    ))

    doc.build(elements)
    buffer.seek(0)

    filename = f"rapport_session_{session.id}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_excel_session(request, session_pk):
    """Export Excel du rapport de présence d'une session de formation."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    session = get_object_or_404(SessionModule.objects.select_related('module__formation'), pk=session_pk)
    formation = session.module.formation
    if not _check_export_access(request, formation):
        return Response(
            {'detail': 'Accès non autorisé à cette formation.'},
            status=403,
        )

    _, _, rows, stats = _get_session_data(session_pk)

    wb = Workbook()
    ws = wb.active
    ws.title = "Présences"

    green_fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
    orange_fill = PatternFill(start_color='F57C00', end_color='F57C00', fill_type='solid')
    light_green_fill = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')
    light_orange_fill = PatternFill(start_color='FFF3E0', end_color='FFF3E0', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=10)
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    # En-tête ministère
    ws.merge_cells('A1:J1')
    ws['A1'] = "RÉPUBLIQUE DE CÔTE D'IVOIRE — Ministère de la Fonction Publique"
    ws['A1'].font = Font(size=9, color='555555')
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:J2')
    ws['A2'] = "Direction de la Formation et du Renforcement des Compétences (DFRC)"
    ws['A2'].font = Font(size=9, color='555555')
    ws['A2'].alignment = Alignment(horizontal='center')

    # Titre session
    session_label = session.intitule or f"Session {session.numero}"
    ws.merge_cells('A3:J3')
    ws['A3'] = f"Rapport de présence — Session"
    ws['A3'].font = Font(bold=True, size=14, color='388E3C')
    ws['A3'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A4:J4')
    ws['A4'] = f"{formation.formation}"
    ws['A4'].font = Font(bold=True, size=12, color='388E3C')
    ws['A4'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A5:J5')
    ws['A5'] = f"{session.date_journee.strftime('%d/%m/%Y')} — {session_label}"
    ws['A5'].font = Font(size=10, color='444444')
    ws['A5'].alignment = Alignment(horizontal='center')

    # Infos session
    ws.merge_cells('A6:J6')
    heure_debut = session.heure_debut_prevue.strftime('%H:%M') if session.heure_debut_prevue else '-'
    heure_fin = session.heure_fin_prevue.strftime('%H:%M') if session.heure_fin_prevue else '-'
    _sm = session.module if session.module else None
    _xs = (
        (_sm.site.nom if getattr(_sm, 'site', None) else getattr(_sm, 'site_legacy', ''))
        if _sm else ''
    ) or ''
    _xb = (_sm.batiment if _sm and _sm.batiment else '') or ''
    _xl = (_sm.salle    if _sm and _sm.salle    else '') or ''
    _xml = (_sm.intitule if _sm else '') or ''
    _xgrade = (_sm.grade if _sm and _sm.grade else '') or ''
    _xgroupe = (_sm.groupe if _sm and _sm.groupe else '') or ''
    if _xml or _xgrade or _xgroupe:
        ws.merge_cells('A6:J6')
        ws['A6'] = f"Module : {_xml or '-'} | Grade : {_xgrade or '-'} | Groupe : {_xgroupe or '-'}"
        ws['A6'].font = Font(bold=True, size=10, color='388E3C')
        ws['A6'].alignment = Alignment(horizontal='center')
        ws.merge_cells('A7:J7')
        ws['A7'] = (
            f"Date séance : {session.date_journee.strftime('%d/%m/%Y')} | "
            f"Heures séance : {heure_debut} - {heure_fin} | "
            f"Site : {_xs or '-'} | Bât. : {_xb or '-'} | Salle : {_xl or '-'}"
        )
        ws['A7'].font = Font(size=10, color='444444')
        ws['A7'].alignment = Alignment(horizontal='center')
        data_start_row = 9
    else:
        ws['A6'] = (
            f"Date séance : {session.date_journee.strftime('%d/%m/%Y')} | "
            f"Heures séance : {heure_debut} - {heure_fin} | "
            f"Site : {_xs or '-'} | Bât. : {_xb or '-'} | Salle : {_xl or '-'}"
        )
        ws['A6'].font = Font(size=10, color='444444')
        ws['A6'].alignment = Alignment(horizontal='center')
        data_start_row = 8

    # En-têtes colonnes
    headers = ['Date', 'Rôle', "N° d'inscription", 'Nom', 'Prénom', 'Organisation', 'Entrée', 'Sortie', 'Durée (min)', 'Statut', 'Motif (forçage)']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=data_start_row, column=col, value=h)
        cell.font = header_font
        cell.fill = green_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    # Données
    for i, r in enumerate(rows):
        row_num = data_start_row + 1 + i
        values = [
            r['date'], r['role'], r['matricule'], r['nom'], r['prenom'], r['organisation'],
            r['heure_entree'], r['heure_sortie'], r['duree_minutes'], r['statut'], r.get('motif', '') or '',
        ]
        is_detail = r.get('is_detail', False)
        is_recap = r.get('is_recap', False)

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
            if col >= 7:
                cell.alignment = Alignment(horizontal='center', vertical='center')

            if is_detail:
                cell.fill = light_orange_fill
                cell.font = Font(italic=True, size=10)
            elif is_recap:
                cell.fill = light_orange_fill
                cell.font = Font(bold=True, color='F57C00', size=10)
            elif i % 2 == 1:
                cell.fill = light_green_fill

        if not is_detail and not is_recap:
            statut_cell = ws.cell(row=row_num, column=10)
            if r['statut'] == 'Absent':
                statut_cell.font = Font(color='C62828', bold=True)
            elif 'En cours' in r['statut']:
                statut_cell.font = Font(color='F57C00', bold=True)
            else:
                statut_cell.font = Font(color='388E3C', bold=True)
            if r.get('motif'):
                ws.cell(row=row_num, column=11).font = Font(color='F57C00', italic=True, size=10)

    # Ligne résumé
    summary_row = data_start_row + 1 + len(rows) + 1
    ws.merge_cells(start_row=summary_row, start_column=1, end_row=summary_row, end_column=6)
    ws.cell(row=summary_row, column=1, value="RÉSUMÉ").font = Font(bold=True, size=10)

    labels = [
        (7, f"Présents: {stats['nb_presents']}"),
        (8, f"Absents: {stats['nb_absents']}"),
        (9, f"Taux: {stats['taux']}%"),
        (10, f"Participants: {stats['nb_participants']}"),
    ]
    for col, val in labels:
        cell = ws.cell(row=summary_row, column=col, value=val)
        cell.font = Font(bold=True, size=10, color='FFFFFF')
        cell.fill = orange_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Date d'export
    footer_row = summary_row + 1
    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=11)
    ws.cell(row=footer_row, column=1,
            value=f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}").font = Font(
        size=8, color='999999', italic=True)

    # Largeur colonnes
    col_widths = {'A': 12, 'B': 12, 'C': 10, 'D': 16, 'E': 16, 'F': 18, 'G': 10, 'H': 10, 'I': 12, 'J': 14, 'K': 28}
    for letter, width in col_widths.items():
        ws.column_dimensions[letter].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"rapport_session_{session.id}.xlsx"
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_finance_formateur_pdf(request, formateur_pk):
    """Export PDF état financier formateur (finance/direction)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    if not _check_finance_export_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    formateur = get_object_or_404(Formateur.objects.prefetch_related('secretariats'), pk=formateur_pk)
    ctx = _finance_formateur_export_context(formateur, request)
    rows = ctx['rows']
    export_opts = ctx['export']
    afficher_montants = export_opts['afficher_montants']
    fmt = ctx.get('formateur') or {}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.0 * cm, rightMargin=1.0 * cm,
        topMargin=1.0 * cm, bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'FinFmtTitle', parent=styles['Title'],
        fontSize=15, textColor=colors.HexColor(CI_GREEN_DARK),
        alignment=TA_CENTER, spaceAfter=3,
    )
    style_sub = ParagraphStyle(
        'FinFmtSub', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#444444'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_info = ParagraphStyle(
        'FinFmtInfo', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#333333'), leading=11,
    )
    style_stats = ParagraphStyle(
        'FinFmtStats', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor(CI_GREEN_DARK), spaceAfter=6,
    )
    cell_normal = ParagraphStyle('FinFmtCell', parent=styles['Normal'], fontSize=7, leading=9)
    cell_center = ParagraphStyle('FinFmtCellC', parent=styles['Normal'], fontSize=7, leading=9, alignment=TA_CENTER)
    cell_header = ParagraphStyle(
        'FinFmtHdr', parent=styles['Normal'],
        fontSize=8, leading=10, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )

    def _p(text, center=False, hdr=False):
        s = cell_header if hdr else (cell_center if center else cell_normal)
        return Paragraph(str(text).replace('&', '&amp;'), s)

    elements = []
    if export_opts.get('entete_ligne1'):
        elements.append(Paragraph(export_opts['entete_ligne1'], style_sub))
    if export_opts.get('entete_ligne2'):
        elements.append(Paragraph(export_opts['entete_ligne2'], style_sub))
    if export_opts.get('organisme'):
        elements.append(Paragraph(f"<b>{export_opts['organisme']}</b>", style_sub))
    if export_opts.get('adresse'):
        elements.append(Paragraph(export_opts['adresse'].replace('\n', '<br/>'), style_sub))

    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph(export_opts.get('titre_document') or 'FICHE DE PAIE DÉTAILLÉE', style_title))
    elements.append(Paragraph(f"Réf. : <b>{export_opts.get('reference', '-')}</b>", style_sub))
    elements.append(Paragraph(f"Période : <b>{ctx['periode_label']}</b>", style_sub))
    elements.append(Spacer(1, 0.15 * cm))

    identite_lines = [
        f"<b>Formateur :</b> {fmt.get('prenom', '')} {fmt.get('nom', '')} — N° {fmt.get('numerobadge') or '-'}",
        f"<b>Spécialité :</b> {fmt.get('specialite') or '-'} &nbsp;|&nbsp; <b>Organisation :</b> {fmt.get('organisation') or '-'}",
        f"<b>Grade(s) :</b> {fmt.get('grades') or '-'} &nbsp;|&nbsp; <b>Groupe(s) :</b> {fmt.get('groupes') or '-'}",
        f"<b>E-mail :</b> {fmt.get('email') or '-'} &nbsp;|&nbsp; <b>Tél. :</b> {fmt.get('telephone') or '-'}",
        f"<b>Secrétariat(s) :</b> {', '.join(fmt.get('secretariats') or []) or '-'}",
    ]
    if fmt.get('numero_piece_identite'):
        identite_lines.append(f"<b>N° pièce d'identité :</b> {fmt.get('numero_piece_identite')}")
    if fmt.get('numero_compte_bancaire'):
        identite_lines.append(f"<b>N° compte bancaire :</b> {fmt.get('numero_compte_bancaire')}")
    for line in identite_lines:
        elements.append(Paragraph(line, style_info))
    elements.append(Spacer(1, 0.2 * cm))

    stats_parts = [
        f"Planifié : <b>{round(ctx['total_planned'], 1)}</b> min",
        f"Réalisé : <b>{round(ctx['total_realized'], 1)}</b> min ({ctx.get('total_heures_realisees', 0)} h)",
        f"Taux : <b>{ctx['taux_realisation_pct']}%</b>",
        f"Séances : <b>{ctx['sessions_count']}</b>",
    ]
    if afficher_montants:
        stats_parts.append(f"Tarif : <b>{ctx['prix_label']}</b>")
        stats_parts.append(f"À verser : <b>{ctx['montant_total']:,.0f}</b> FCFA")
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(stats_parts), style_stats))
    elements.append(Paragraph(ctx.get('billing_label', ''), style_info))
    elements.append(Spacer(1, 0.15 * cm))

    recap = ctx.get('recap_formations') or []
    if afficher_montants and recap:
        elements.append(Paragraph('<b>Ventilation par type de formation</b>', style_info))
        recap_headers = ['Formation (cycle)', 'Tarif / h', 'Heures réal.', 'Montant (FCFA)']
        recap_data = [[_p(h, hdr=True) for h in recap_headers]]
        for item in recap:
            recap_data.append([
                _p(item.get('formation') or '-'),
                _p(f"{float(item.get('prix_heure') or 0):,.0f}", center=True),
                _p(round(float(item.get('heures_realisees') or 0), 2), center=True),
                _p(f"{float(item.get('montant') or 0):,.0f}", center=True),
            ])
        recap_table = Table(recap_data, colWidths=[6 * cm, 2.5 * cm, 2.5 * cm, 3 * cm])
        recap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_GREEN_DARK)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(CI_LIGHT_GREEN)]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(recap_table)
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(Paragraph('<b>Détail par séance</b>', style_info))
        elements.append(Spacer(1, 0.1 * cm))

    headers = _finance_export_table_headers(afficher_montants)
    data = [[_p(h, hdr=True) for h in headers]]
    for r in rows:
        row_vals = _finance_export_table_row(r, afficher_montants)
        formatted = []
        for i, val in enumerate(row_vals):
            if afficher_montants and i == len(row_vals) - 1:
                formatted.append(_p(f"{float(val or 0):,.0f}", center=True))
            elif afficher_montants and i == len(row_vals) - 2 and val not in ('', None):
                formatted.append(_p(f"{float(val):,.0f}", center=True))
            elif i >= 7:
                formatted.append(_p(val, center=True))
            else:
                formatted.append(_p(val))
        data.append(formatted)

    base_widths = [1.8, 2.4, 3.2, 3.6, 1.2, 1.6, 2.4, 1.5, 1.5, 1.6]
    if afficher_montants:
        base_widths.extend([1.8, 2.0])
    col_widths = [w * cm for w in base_widths]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_GREEN_DARK)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(CI_LIGHT_GREEN)]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.35 * cm))

    if export_opts.get('signataire_nom') or export_opts.get('signataire_fonction'):
        sig_style = ParagraphStyle(
            'FinFmtSig', parent=styles['Normal'], fontSize=9,
            alignment=TA_RIGHT, textColor=colors.HexColor('#333333'),
        )
        sig_lines = []
        if export_opts.get('signataire_fonction'):
            sig_lines.append(export_opts['signataire_fonction'])
        if export_opts.get('signataire_nom'):
            sig_lines.append(f"<b>{export_opts['signataire_nom']}</b>")
        elements.append(Paragraph('<br/>'.join(sig_lines), sig_style))
        elements.append(Spacer(1, 0.2 * cm))

    foot_parts = [f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"]
    if export_opts.get('mention_legale'):
        foot_parts.append(export_opts['mention_legale'])
    elements.append(Paragraph(
        '<br/>'.join(foot_parts),
        ParagraphStyle('FinFmtFoot', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#999999')),
    ))

    doc.build(elements)
    buffer.seek(0)
    filename = f"fiche_paie_{formateur.numerobadge or formateur.pk}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_finance_formateur_excel(request, formateur_pk):
    """Export Excel état financier formateur (finance/direction)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    if not _check_finance_export_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    formateur = get_object_or_404(Formateur.objects.prefetch_related('secretariats'), pk=formateur_pk)
    ctx = _finance_formateur_export_context(formateur, request)
    rows = ctx['rows']
    export_opts = ctx['export']
    afficher_montants = export_opts['afficher_montants']
    fmt = ctx.get('formateur') or {}
    headers = _finance_export_table_headers(afficher_montants)
    last_col = len(headers)

    wb = Workbook()
    ws = wb.active
    ws.title = "État financier"

    green_fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
    light_green_fill = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')
    orange_fill = PatternFill(start_color='F57C00', end_color='F57C00', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=10)
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    row_idx = 1
    for line in (
        export_opts.get('entete_ligne1'),
        export_opts.get('entete_ligne2'),
        export_opts.get('organisme'),
    ):
        if line:
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
            ws.cell(row=row_idx, column=1, value=line).alignment = Alignment(horizontal='center')
            row_idx += 1
    if export_opts.get('adresse'):
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
        ws.cell(row=row_idx, column=1, value=export_opts['adresse']).alignment = Alignment(horizontal='center', wrap_text=True)
        row_idx += 1

    row_idx += 1
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
    ws.cell(row=row_idx, column=1, value=export_opts.get('titre_document') or 'FICHE DE PAIE DÉTAILLÉE')
    ws.cell(row=row_idx, column=1).font = Font(bold=True, size=13, color='388E3C')
    ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal='center')
    row_idx += 1

    for label, value in (
        ('Référence', export_opts.get('reference', '-')),
        ('Période', ctx['periode_label']),
        ('Formateur', f"{fmt.get('prenom', '')} {fmt.get('nom', '')}".strip()),
        ('N° Badge', fmt.get('numerobadge') or '-'),
        ('Spécialité', fmt.get('specialite') or '-'),
        ('Grade(s)', fmt.get('grades') or '-'),
        ('Groupe(s)', fmt.get('groupes') or '-'),
        ('Organisation', fmt.get('organisation') or '-'),
        ('E-mail', fmt.get('email') or '-'),
        ('Téléphone', fmt.get('telephone') or '-'),
        ('Secrétariat(s)', ', '.join(fmt.get('secretariats') or []) or '-'),
        *(
            [('N° pièce d\'identité', fmt.get('numero_piece_identite') or '-'),
             ('N° compte bancaire', fmt.get('numero_compte_bancaire') or '-')]
            if fmt.get('numero_piece_identite') or fmt.get('numero_compte_bancaire')
            else []
        ),
    ):
        ws.cell(row=row_idx, column=1, value=label).font = Font(bold=True, size=9)
        ws.merge_cells(start_row=row_idx, start_column=2, end_row=row_idx, end_column=last_col)
        ws.cell(row=row_idx, column=2, value=value)
        row_idx += 1

    row_idx += 1
    synth_labels = ['Planifié (min)', 'Réalisé (min)', 'Heures réalisées', 'Taux %', 'Séances']
    synth_values = [
        round(ctx['total_planned'], 1),
        round(ctx['total_realized'], 1),
        ctx.get('total_heures_realisees', 0),
        ctx['taux_realisation_pct'],
        ctx['sessions_count'],
    ]
    if afficher_montants:
        synth_labels.extend(['Tarif horaire', 'À verser (FCFA)'])
        synth_values.extend([ctx['prix_label'], ctx['montant_total']])
    for col, (label, val) in enumerate(zip(synth_labels, synth_values), start=1):
        cell_l = ws.cell(row=row_idx, column=col, value=label)
        cell_v = ws.cell(row=row_idx + 1, column=col, value=val)
        for cell in (cell_l, cell_v):
            cell.fill = orange_fill
            cell.font = Font(bold=True, color='FFFFFF', size=9)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border
    row_idx += 3
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
    ws.cell(row=row_idx, column=1, value=ctx.get('billing_label', ''))
    ws.cell(row=row_idx, column=1).font = Font(size=9, italic=True)
    row_idx += 2

    recap = ctx.get('recap_formations') or []
    if afficher_montants and recap:
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
        ws.cell(row=row_idx, column=1, value='Ventilation par type de formation').font = Font(bold=True, size=10)
        row_idx += 1
        for col, h in enumerate(['Formation (cycle)', 'Tarif / h', 'Heures réal.', 'Montant (FCFA)'], start=1):
            cell = ws.cell(row=row_idx, column=col, value=h)
            cell.font = header_font
            cell.fill = green_fill
            cell.border = thin_border
        row_idx += 1
        for item in recap:
            ws.cell(row=row_idx, column=1, value=item.get('formation') or '-').border = thin_border
            ws.cell(row=row_idx, column=2, value=float(item.get('prix_heure') or 0)).border = thin_border
            ws.cell(row=row_idx, column=3, value=round(float(item.get('heures_realisees') or 0), 2)).border = thin_border
            ws.cell(row=row_idx, column=4, value=round(float(item.get('montant') or 0), 2)).border = thin_border
            row_idx += 1
        row_idx += 1
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
        ws.cell(row=row_idx, column=1, value='Détail par séance').font = Font(bold=True, size=10)
        row_idx += 1

    start_row = row_idx
    for idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=idx, value=h)
        cell.font = header_font
        cell.fill = green_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    for i, r in enumerate(rows, start=1):
        row_num = start_row + i
        values = _finance_export_table_row(r, afficher_montants)
        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
            if col >= 8:
                cell.alignment = Alignment(horizontal='center', vertical='center')
            if i % 2 == 0:
                cell.fill = light_green_fill

    col_widths = [12, 18, 22, 24, 10, 14, 20, 14, 14, 14]
    if afficher_montants:
        col_widths.extend([14, 14])
    for idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    footer_row = start_row + len(rows) + 2
    if export_opts.get('signataire_nom') or export_opts.get('signataire_fonction'):
        ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=last_col)
        sig = ' — '.join(filter(None, [export_opts.get('signataire_fonction'), export_opts.get('signataire_nom')]))
        ws.cell(row=footer_row, column=1, value=sig).alignment = Alignment(horizontal='right')
        footer_row += 1

    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=last_col)
    foot = f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    if export_opts.get('mention_legale'):
        foot = f"{foot} — {export_opts['mention_legale']}"
    ws.cell(row=footer_row, column=1, value=foot)
    ws.cell(row=footer_row, column=1).font = Font(size=8, color='999999', italic=True)
    ws.cell(row=footer_row, column=1).alignment = Alignment(horizontal='right', wrap_text=True)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"fiche_paie_{formateur.numerobadge or formateur.pk}.xlsx"
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_finance_synthese_pdf(request):
    """Export PDF consolidé : synthèse finance de tous les formateurs (période / filtres)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    if not _check_finance_export_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    ctx, err = _finance_synthese_export_context(request)
    if err:
        return Response({'detail': err}, status=400)

    rows = ctx['rows']
    totals = ctx['totals']
    export_opts = ctx['export']
    afficher_montants = export_opts['afficher_montants']
    include_sensitive = request.user.role == 'FINANCE'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=0.8 * cm, rightMargin=0.8 * cm,
        topMargin=1.0 * cm, bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'FinSynTitle', parent=styles['Title'],
        fontSize=14, textColor=colors.HexColor(CI_GREEN_DARK),
        alignment=TA_CENTER, spaceAfter=3,
    )
    style_sub = ParagraphStyle(
        'FinSynSub', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#444444'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_stats = ParagraphStyle(
        'FinSynStats', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor(CI_GREEN_DARK), spaceAfter=6,
    )
    cell_normal = ParagraphStyle('FinSynCell', parent=styles['Normal'], fontSize=7, leading=9)
    cell_center = ParagraphStyle('FinSynCellC', parent=styles['Normal'], fontSize=7, leading=9, alignment=TA_CENTER)
    cell_header = ParagraphStyle(
        'FinSynHdr', parent=styles['Normal'],
        fontSize=8, leading=10, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )

    def _p(text, center=False, hdr=False):
        s = cell_header if hdr else (cell_center if center else cell_normal)
        return Paragraph(str(text).replace('&', '&amp;'), s)

    elements = []
    for line in (export_opts.get('entete_ligne1'), export_opts.get('entete_ligne2'), export_opts.get('organisme')):
        if line:
            elements.append(Paragraph(line, style_sub))
    if export_opts.get('adresse'):
        elements.append(Paragraph(export_opts['adresse'].replace('\n', '<br/>'), style_sub))
    elements.append(Spacer(1, 0.15 * cm))
    elements.append(Paragraph(export_opts.get('titre_document') or 'FICHE DE PAIE GLOBALE', style_title))
    elements.append(Paragraph(f"Réf. : <b>{export_opts.get('reference', '-')}</b>", style_sub))
    elements.append(Paragraph(f"Période : <b>{ctx['periode_label']}</b>", style_sub))
    elements.append(Paragraph(
        'Facturation : tarif horaire selon le type de formation (cycle) pour chaque module.',
        style_sub,
    ))
    elements.append(Spacer(1, 0.15 * cm))

    stats_parts = [
        f"Formateurs : <b>{totals['formateurs_count']}</b> ({totals['formateurs_actifs']} actifs)",
        f"Séances : <b>{totals['sessions_count']}</b>",
        f"Réalisé : <b>{totals['total_realized']}</b> min ({totals['total_heures_realisees']} h)",
    ]
    if afficher_montants:
        stats_parts.append(f"Total à verser : <b>{totals['montant_total']:,.0f}</b> FCFA")
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(stats_parts), style_stats))

    headers = _finance_synthese_table_headers(afficher_montants, include_sensitive)
    data = [[_p(h, hdr=True) for h in headers]]
    for row in rows:
        vals = _finance_synthese_table_row(row, afficher_montants, include_sensitive)
        data.append([_p(v, center=(i >= 6)) for i, v in enumerate(vals)])
    total_vals = ['TOTAL', '', '', '', '', '', totals['sessions_count'], totals['total_planned'],
                  totals['total_realized'], totals['total_heures_realisees'], '']
    if afficher_montants:
        total_vals.append(totals['montant_total'])
    if include_sensitive:
        total_vals.extend(['', ''])
    data.append([_p(v, center=(i >= 6)) for i, v in enumerate(total_vals)])

    col_count = len(headers)
    base_w = [1.4, 1.8, 1.8, 2.2, 1.2, 1.6, 1.0, 1.3, 1.3, 1.2, 1.0]
    if afficher_montants:
        base_w.append(1.6)
    if include_sensitive:
        base_w.extend([1.8, 1.8])
    while len(base_w) < col_count:
        base_w.append(1.5)
    col_widths = [w * cm for w in base_w[:col_count]]

    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CI_GREEN_DARK)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor(CI_LIGHT_GREEN)]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(CI_LIGHT_ORANGE)),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3 * cm))

    if export_opts.get('signataire_nom') or export_opts.get('signataire_fonction'):
        sig_style = ParagraphStyle(
            'FinSynSig', parent=styles['Normal'], fontSize=9,
            alignment=TA_RIGHT, textColor=colors.HexColor('#333333'),
        )
        sig_lines = []
        if export_opts.get('signataire_fonction'):
            sig_lines.append(export_opts['signataire_fonction'])
        if export_opts.get('signataire_nom'):
            sig_lines.append(f"<b>{export_opts['signataire_nom']}</b>")
        elements.append(Paragraph('<br/>'.join(sig_lines), sig_style))

    foot = f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    if export_opts.get('mention_legale'):
        foot += f"<br/>{export_opts['mention_legale']}"
    elements.append(Paragraph(
        foot,
        ParagraphStyle('FinSynFoot', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#999999')),
    ))

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="fiche_paie_globale.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_finance_synthese_excel(request):
    """Export Excel consolidé : synthèse finance de tous les formateurs."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    if not _check_finance_export_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    ctx, err = _finance_synthese_export_context(request)
    if err:
        return Response({'detail': err}, status=400)

    rows = ctx['rows']
    totals = ctx['totals']
    export_opts = ctx['export']
    afficher_montants = export_opts['afficher_montants']
    include_sensitive = request.user.role == 'FINANCE'
    headers = _finance_synthese_table_headers(afficher_montants, include_sensitive)
    last_col = len(headers)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Synthèse formateurs'

    green_fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
    light_green_fill = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')
    orange_fill = PatternFill(start_color='F57C00', end_color='F57C00', fill_type='solid')
    total_fill = PatternFill(start_color='FFF3E0', end_color='FFF3E0', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=10)
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    row_idx = 1
    for line in (export_opts.get('entete_ligne1'), export_opts.get('entete_ligne2'), export_opts.get('organisme')):
        if line:
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
            ws.cell(row=row_idx, column=1, value=line).alignment = Alignment(horizontal='center')
            row_idx += 1
    row_idx += 1
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
    ws.cell(row=row_idx, column=1, value=export_opts.get('titre_document'))
    ws.cell(row=row_idx, column=1).font = Font(bold=True, size=13, color='388E3C')
    ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal='center')
    row_idx += 1
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=last_col)
    ws.cell(row=row_idx, column=1, value=f"Réf. {export_opts.get('reference')} — Période : {ctx['periode_label']}")
    ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal='center')
    row_idx += 2

    synth = [
        ('Formateurs', totals['formateurs_count']),
        ('Actifs', totals['formateurs_actifs']),
        ('Séances', totals['sessions_count']),
        ('Réalisé (min)', totals['total_realized']),
        ('Heures réalisées', totals['total_heures_realisees']),
    ]
    if afficher_montants:
        synth.append(('Total à verser (FCFA)', totals['montant_total']))
    for col, (label, val) in enumerate(synth, start=1):
        ws.cell(row=row_idx, column=col, value=label).fill = orange_fill
        ws.cell(row=row_idx, column=col).font = Font(bold=True, color='FFFFFF', size=9)
        ws.cell(row=row_idx + 1, column=col, value=val).fill = orange_fill
        ws.cell(row=row_idx + 1, column=col).font = Font(bold=True, color='FFFFFF', size=9)
        ws.cell(row=row_idx, column=col).alignment = Alignment(horizontal='center')
        ws.cell(row=row_idx + 1, column=col).alignment = Alignment(horizontal='center')
    row_idx += 4

    start_row = row_idx
    for idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=idx, value=h)
        cell.font = header_font
        cell.fill = green_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    for i, row in enumerate(rows, start=1):
        row_num = start_row + i
        values = _finance_synthese_table_row(row, afficher_montants, include_sensitive)
        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.border = thin_border
            if col >= 7:
                cell.alignment = Alignment(horizontal='center', vertical='center')
            if i % 2 == 0:
                cell.fill = light_green_fill

    total_row = start_row + len(rows) + 1
    total_values = _finance_synthese_table_row(
        {
            'numerobadge': 'TOTAL', 'nom': '', 'prenom': '', 'specialite': '',
            'grades': '', 'groupes': '',
            'sessions_count': totals['sessions_count'],
            'total_duree_minutes': totals['total_planned'],
            'total_duree_realisee_minutes': totals['total_realized'],
            'montant_total_realise': totals['montant_total'],
            'statistiques': {},
        },
        afficher_montants,
        include_sensitive,
    )
    total_values[0] = 'TOTAL'
    for col, val in enumerate(total_values, start=1):
        cell = ws.cell(row=total_row, column=col, value=val)
        cell.border = thin_border
        cell.fill = total_fill
        cell.font = Font(bold=True)
        if col >= 7:
            cell.alignment = Alignment(horizontal='center')

    col_widths = [12, 14, 14, 18, 10, 14, 8, 12, 12, 12, 8]
    if afficher_montants:
        col_widths.append(14)
    if include_sensitive:
        col_widths.extend([16, 16])
    for idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    footer_row = total_row + 2
    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=last_col)
    foot = f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    if export_opts.get('mention_legale'):
        foot += f" — {export_opts['mention_legale']}"
    ws.cell(row=footer_row, column=1, value=foot)
    ws.cell(row=footer_row, column=1).font = Font(size=8, color='999999', italic=True)
    ws.cell(row=footer_row, column=1).alignment = Alignment(horizontal='right', wrap_text=True)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="fiche_paie_globale.xlsx"'
    return response
