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
    """Lignes détail + totaux pour la fiche résumé finance (période et secrétariat optionnels)."""
    from formations.api_views import (
        _parse_finance_date_range,
        _finance_session_in_range,
        _finance_prix_heure,
        _finance_montant_from_minutes,
        _finance_secretariat_id_from_request,
        _finance_periode_payload,
    )

    period = _parse_finance_date_range(request) if request else {
        'error': False, 'date_debut': None, 'date_fin': None, 'meta': {'preset': 'tout'},
    }
    if period.get('error'):
        period = {'error': False, 'date_debut': None, 'date_fin': None, 'meta': {'preset': 'tout'}}
    secretariat_id = _finance_secretariat_id_from_request(request) if request else None
    prix_heure = _finance_prix_heure()

    module_ids = set(
        ModuleFormateur.objects.filter(formateur_id=formateur.pk).values_list('module_id', flat=True)
    )
    module_ids.update(
        Module.objects.filter(formateur_id=formateur.pk).values_list('id', flat=True)
    )
    modules_by_id = {
        m.id: m for m in Module.objects.filter(id__in=module_ids).select_related(
            'formation', 'secretariat',
        )
    }
    sessions = list(
        SessionModule.objects.filter(module_id__in=module_ids)
        .select_related('module', 'module__formation', 'module__secretariat')
        .order_by('date_journee', 'numero')
    )
    now = timezone.now()
    rows = []
    total_planned = 0.0
    total_realized = 0.0
    date_min = None
    date_max = None
    for s in sessions:
        mod = modules_by_id.get(s.module_id) if s.module_id else None
        if secretariat_id and (not mod or mod.secretariat_id != secretariat_id):
            continue
        if not _finance_session_in_range(s, period['date_debut'], period['date_fin']):
            continue
        planned = _session_planned_minutes(s)
        realized = _session_realized_minutes_for_formateur(formateur.pk, s, now=now)
        montant = _finance_montant_from_minutes(realized, prix_heure)
        total_planned += planned
        total_realized += realized
        if s.date_journee:
            if date_min is None or s.date_journee < date_min:
                date_min = s.date_journee
            if date_max is None or s.date_journee > date_max:
                date_max = s.date_journee
        sec_nom = ''
        if mod and mod.secretariat_id and mod.secretariat:
            sec_nom = f"{mod.secretariat.nom} ({mod.secretariat.numero})"
        rows.append({
            'date': s.date_journee.strftime('%d/%m/%Y') if s.date_journee else '-',
            'session': s.intitule or f'Séance {s.numero}',
            'module': s.module.intitule if s.module else '-',
            'formation': s.module.formation.formation if s.module and s.module.formation else '-',
            'secretariat': sec_nom or '-',
            'duree_seance': planned,
            'temps_realise': realized,
            'montant': montant,
        })
    montant_total = _finance_montant_from_minutes(total_realized, prix_heure)
    taux = round((total_realized / total_planned) * 100, 1) if total_planned > 0 else 0
    periode_info = _finance_periode_payload(
        period['date_debut'], period['date_fin'], period['meta'], date_min, date_max,
    )
    meta = {
        'rows': rows,
        'total_planned': total_planned,
        'total_realized': total_realized,
        'montant_total': montant_total,
        'prix_heure': prix_heure,
        'taux_realisation_pct': taux,
        'periode': periode_info,
        'sessions_count': len(rows),
    }
    return meta


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
    """Export PDF de la fiche résumé d'un formateur (finance/direction)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    if not _check_finance_export_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    formateur = get_object_or_404(Formateur, pk=formateur_pk)
    summary = _finance_formateur_summary_rows(formateur, request)
    rows = summary['rows']
    total_planned = summary['total_planned']
    total_realized = summary['total_realized']
    montant_total = summary['montant_total']
    prix_heure = summary['prix_heure']
    periode_label = summary['periode'].get('periode_label') or 'Toutes périodes'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'FinFmtTitle', parent=styles['Title'],
        fontSize=16, textColor=colors.HexColor(CI_GREEN_DARK),
        alignment=TA_CENTER, spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        'FinFmtSub', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#444444'),
        alignment=TA_CENTER, spaceAfter=2,
    )
    style_stats = ParagraphStyle(
        'FinFmtStats', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor(CI_GREEN_DARK),
        spaceAfter=8,
    )
    cell_normal = ParagraphStyle('FinFmtCell', parent=styles['Normal'], fontSize=8, leading=10)
    cell_center = ParagraphStyle('FinFmtCellC', parent=styles['Normal'], fontSize=8, leading=10, alignment=TA_CENTER)
    cell_header = ParagraphStyle(
        'FinFmtHdr', parent=styles['Normal'],
        fontSize=9, leading=11, alignment=TA_CENTER,
        textColor=colors.white, fontName='Helvetica-Bold',
    )

    def _p(text, center=False, hdr=False):
        s = cell_header if hdr else (cell_center if center else cell_normal)
        return Paragraph(str(text), s)

    elements = []
    elements.append(Paragraph('FICHE RÉSUMÉ FORMATEUR — FINANCE', style_title))
    elements.append(Paragraph(
        f"<b>{formateur.nom} {formateur.prenom}</b> — {formateur.numerobadge or '-'}",
        style_subtitle,
    ))
    elements.append(Paragraph(f"Période : <b>{periode_label}</b>", style_subtitle))
    elements.append(Paragraph(
        f"Planifié : <b>{round(total_planned, 1)}</b> min &nbsp;|&nbsp; "
        f"Réalisé : <b>{round(total_realized, 1)}</b> min &nbsp;|&nbsp; "
        f"Taux : <b>{summary['taux_realisation_pct']}%</b> &nbsp;|&nbsp; "
        f"Tarif : <b>{prix_heure:,.0f}</b> FCFA/h &nbsp;|&nbsp; "
        f"À verser : <b>{montant_total:,.0f}</b> FCFA",
        style_stats,
    ))
    elements.append(Spacer(1, 0.3 * cm))

    header = [
        'Date', 'Séance', 'Module', 'Formation', 'Secrétariat',
        'Durée (min)', 'Réalisé (min)', 'Montant (FCFA)',
    ]
    data = [[_p(h, hdr=True) for h in header]]
    for r in rows:
        data.append([
            _p(r['date'], center=True),
            _p(r['session']),
            _p(r['module']),
            _p(r['formation']),
            _p(r['secretariat']),
            _p(r['duree_seance'], center=True),
            _p(r['temps_realise'], center=True),
            _p(f"{r['montant']:,.0f}", center=True),
        ])

    col_widths = [2.0 * cm, 2.8 * cm, 4.5 * cm, 4.8 * cm, 3.2 * cm, 1.8 * cm, 1.8 * cm, 2.2 * cm]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
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
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph(
        f"<i>Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</i>",
        ParagraphStyle('FinFmtFoot', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#999999')),
    ))

    doc.build(elements)
    buffer.seek(0)
    filename = f"fiche_resume_formateur_{formateur.numerobadge or formateur.pk}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_finance_formateur_excel(request, formateur_pk):
    """Export Excel de la fiche résumé d'un formateur (finance/direction)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    if not _check_finance_export_access(request):
        return Response({'detail': 'Accès réservé à la direction et à la finance.'}, status=403)

    formateur = get_object_or_404(Formateur, pk=formateur_pk)
    summary = _finance_formateur_summary_rows(formateur, request)
    rows = summary['rows']
    total_planned = summary['total_planned']
    total_realized = summary['total_realized']
    montant_total = summary['montant_total']
    prix_heure = summary['prix_heure']
    periode_label = summary['periode'].get('periode_label') or 'Toutes périodes'
    last_col = 8

    wb = Workbook()
    ws = wb.active
    ws.title = "Résumé formateur"

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

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    ws['A1'] = "FICHE RÉSUMÉ FORMATEUR — FINANCE"
    ws['A1'].font = Font(bold=True, size=13, color='388E3C')
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=last_col)
    ws['A2'] = f"{formateur.nom} {formateur.prenom} ({formateur.numerobadge})"
    ws['A2'].font = Font(size=11, color='444444')
    ws['A2'].alignment = Alignment(horizontal='center')

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=last_col)
    ws['A3'] = f"Période : {periode_label}"
    ws['A3'].font = Font(size=10, color='555555', italic=True)
    ws['A3'].alignment = Alignment(horizontal='center')

    ws['A5'] = "Planifié (min)"
    ws['B5'] = round(total_planned, 1)
    ws['C5'] = "Réalisé (min)"
    ws['D5'] = round(total_realized, 1)
    ws['E5'] = "Taux %"
    ws['F5'] = summary['taux_realisation_pct']
    ws['G5'] = "À verser (FCFA)"
    ws['H5'] = montant_total
    for c in ('A5', 'B5', 'C5', 'D5', 'E5', 'F5', 'G5', 'H5'):
        ws[c].fill = orange_fill
        ws[c].font = Font(bold=True, color='FFFFFF', size=9)
        ws[c].alignment = Alignment(horizontal='center')
        ws[c].border = thin_border

    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=last_col)
    ws['A6'] = f"Tarif horaire appliqué : {prix_heure:,.0f} FCFA / h réalisée"
    ws['A6'].font = Font(size=9, color='388E3C')
    ws['A6'].alignment = Alignment(horizontal='center')

    headers = [
        'Date', 'Séance', 'Module', 'Formation', 'Secrétariat',
        'Durée séance (min)', 'Temps réalisé (min)', 'Montant (FCFA)',
    ]
    start_row = 8
    for idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=idx, value=h)
        cell.font = header_font
        cell.fill = green_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    for i, r in enumerate(rows, start=1):
        row_num = start_row + i
        values = [
            r['date'], r['session'], r['module'], r['formation'], r['secretariat'],
            r['duree_seance'], r['temps_realise'], r['montant'],
        ]
        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
            if col >= 6:
                cell.alignment = Alignment(horizontal='center', vertical='center')
            if i % 2 == 0:
                cell.fill = light_green_fill

    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 24
    ws.column_dimensions['D'].width = 26
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 14
    ws.column_dimensions['G'].width = 14
    ws.column_dimensions['H'].width = 14

    footer_row = start_row + len(rows) + 2
    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=last_col)
    ws.cell(row=footer_row, column=1, value=f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    ws.cell(row=footer_row, column=1).font = Font(size=8, color='999999', italic=True)
    ws.cell(row=footer_row, column=1).alignment = Alignment(horizontal='right')

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"fiche_resume_formateur_{formateur.numerobadge or formateur.pk}.xlsx"
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
