"""Catalogue opérationnel « Cours (ECUE) ».

Chaque ligne du catalogue est une *offre* = ECUE × promotion. Contrairement à
l'ancienne façade ``academics.services.cours``, les agrégats couvrent **toutes
les périodes de formation** : une offre porte l'ensemble de ses séances, quelle
que soit la période qui les a produites.
"""
from __future__ import annotations

from collections import defaultdict

from django.db.models import Count, Q, Sum

from ..models import PeriodeFormation, Pointage, ProgrammePeriode, Seance
from .common import (
    fold_text,
    heures,
    offering_id,
    paires_ecue_promotion,
    parse_int,
    parse_uuid,
    promotions_filtrees,
    resolve_academic_year,
)

STATUTS = {
    'non_programme': 'Non programmé',
    'programme': 'Programmé',
    'planifie': 'Planifié',
    'en_cours': 'En cours',
    'termine': 'Terminé',
}


def _statut_offre(nb_programmes: int, nb_seances: int, nb_terminees: int, nb_en_cours: int) -> str:
    if not nb_programmes:
        return 'non_programme'
    if not nb_seances:
        return 'programme'
    if nb_en_cours:
        return 'en_cours'
    if nb_terminees == nb_seances:
        return 'termine'
    return 'planifie'


def _agregats_programmes(paires_ids, *, periode_id=None, academic_year_id=None):
    """Programmes par couple (ECUE, promotion), toutes périodes confondues."""
    queryset = ProgrammePeriode.objects.filter(is_active=True).select_related(
        'periode', 'teacher__user', 'supervisor__user',
    )
    if periode_id:
        queryset = queryset.filter(periode_id=periode_id)
    if academic_year_id:
        queryset = queryset.filter(periode__academic_year_id=academic_year_id)

    par_paire = defaultdict(list)
    for programme in queryset:
        cle = (programme.course_id, programme.promotion_id)
        if paires_ids and cle not in paires_ids:
            continue
        par_paire[cle].append(programme)
    return par_paire


def _agregats_seances(*, periode_id=None, academic_year_id=None):
    """Compteurs de séances par couple (ECUE, promotion)."""
    queryset = Seance.objects.exclude(statut='annulee')
    if periode_id:
        queryset = queryset.filter(periode_id=periode_id)
    if academic_year_id:
        queryset = queryset.filter(periode__academic_year_id=academic_year_id)

    lignes = queryset.values('course_id', 'promotion_id').annotate(
        seances=Count('id'),
        minutes=Sum('duree_minutes'),
        terminees=Count('id', filter=Q(statut='terminee')),
        en_cours=Count('id', filter=Q(statut='en_cours')),
        periodes=Count('periode_id', distinct=True),
    )
    return {(ligne['course_id'], ligne['promotion_id']): ligne for ligne in lignes}


def _agregats_presences(*, periode_id=None, academic_year_id=None):
    queryset = Pointage.objects.exclude(seance__statut='annulee')
    if periode_id:
        queryset = queryset.filter(seance__periode_id=periode_id)
    if academic_year_id:
        queryset = queryset.filter(seance__periode__academic_year_id=academic_year_id)

    lignes = queryset.values('seance__course_id', 'seance__promotion_id').annotate(
        attendus=Count('id'),
        presents=Count('id', filter=Q(statut__in=['present', 'retard', 'force'])),
    )
    return {
        (ligne['seance__course_id'], ligne['seance__promotion_id']): ligne
        for ligne in lignes
    }


def construire_catalogue(params) -> dict:
    """Catalogue paginé avec KPI, filtres et agrégats multi-périodes."""
    year = resolve_academic_year(parse_uuid(params.get('academic_year')))
    periode_id = parse_uuid(params.get('periode'))
    department_id = parse_uuid(params.get('department'))
    program_id = parse_uuid(params.get('program'))
    promotion_id = parse_uuid(params.get('promotion'))
    teaching_unit_id = parse_uuid(params.get('teaching_unit'))
    teacher_id = parse_uuid(params.get('teacher'))
    specialization_id = parse_uuid(params.get('specialization'))
    session_kind = (params.get('session_kind') or '').strip()
    statut_filtre = (params.get('statut') or params.get('status') or '').strip()
    recherche = fold_text(params.get('search') or params.get('q') or '')
    page = parse_int(params, 'page', 1, minimum=1, maximum=10_000)
    page_size = parse_int(params, 'page_size', 25, minimum=1, maximum=200)

    semester_number = params.get('semester_number')
    try:
        semester_number = int(semester_number) if semester_number not in (None, '') else None
    except (TypeError, ValueError):
        semester_number = None

    if not year:
        return {
            'count': 0, 'page': page, 'page_size': page_size, 'results': [],
            'kpis': _kpis([]),
            'filtre': {'warning': 'Aucune année académique courante n’est définie.'},
        }

    promotions = promotions_filtrees(
        department_id=department_id, program_id=program_id, promotion_id=promotion_id,
    )
    paires = paires_ecue_promotion(
        promotions,
        department_id=department_id,
        teaching_unit_id=teaching_unit_id,
        specialization_id=specialization_id,
        semester_number=semester_number,
    )
    promotions_par_id = {promo.id: promo for promo in promotions}
    paires_ids = {(course.id, promo.id) for course, promo in paires}

    programmes_par_paire = _agregats_programmes(
        paires_ids, periode_id=periode_id, academic_year_id=year.id,
    )
    # Une offre programmée hors maquette doit rester visible.
    for cle, programmes in programmes_par_paire.items():
        if cle in paires_ids:
            continue
        exemple = programmes[0]
        promo = promotions_par_id.get(exemple.promotion_id)
        if promo is None:
            continue
        paires.append((exemple.course, promo))
        paires_ids.add(cle)

    seances_par_paire = _agregats_seances(periode_id=periode_id, academic_year_id=year.id)
    presences_par_paire = _agregats_presences(periode_id=periode_id, academic_year_id=year.id)

    lignes = []
    for course, promo in paires:
        cle = (course.id, promo.id)
        programmes = programmes_par_paire.get(cle, [])
        if session_kind:
            programmes = [item for item in programmes if item.session_kind == session_kind]
        stats = seances_par_paire.get(cle, {})
        presences = presences_par_paire.get(cle, {})

        nb_seances = stats.get('seances', 0)
        minutes_planifiees = stats.get('minutes', 0) or 0
        minutes_cible = sum(
            item.volume_horaire_minutes or item.volume_maquette_minutes() for item in programmes
        )
        volume_maquette = ((course.hours_cm or 0) + (course.hours_td or 0) + (course.hours_tp or 0))
        enseignants = [item for item in programmes if item.teacher_id]
        titulaire = enseignants[0].teacher if enseignants else None

        statut = _statut_offre(
            len(programmes), nb_seances, stats.get('terminees', 0), stats.get('en_cours', 0),
        )
        attendus = presences.get('attendus', 0)
        presents = presences.get('presents', 0)

        ligne = {
            'id': offering_id(course.id, promo.id),
            'course': str(course.id),
            'course_code': course.code,
            'course_name': course.name,
            'teaching_unit': str(course.teaching_unit_id),
            'teaching_unit_code': course.teaching_unit.code,
            'teaching_unit_name': course.teaching_unit.name,
            'semester_number': course.teaching_unit.semester_number,
            'credits_ects': course.teaching_unit.credits_ects,
            'coefficient': float(course.coefficient or 0),
            'program': str(promo.program_id),
            'program_code': promo.program.code,
            'program_name': promo.program.name,
            'degree_type': promo.program.degree_type,
            'degree_type_display': promo.program.get_degree_type_display(),
            'promotion': str(promo.id),
            'promotion_name': promo.name,
            'academic_year': str(year.id),
            'academic_year_label': year.label,
            'hours_cm': course.hours_cm,
            'hours_td': course.hours_td,
            'hours_tp': course.hours_tp,
            'volume_maquette_heures': volume_maquette,
            'volume_cible_heures': heures(minutes_cible),
            'heures_planifiees': heures(minutes_planifiees),
            'taux_couverture': (
                round(minutes_planifiees / minutes_cible * 100, 1) if minutes_cible else 0.0
            ),
            'programmes_count': len(programmes),
            'periodes_count': stats.get('periodes', 0),
            'periodes': sorted({item.periode.code for item in programmes}),
            'seances_count': nb_seances,
            'seances_terminees': stats.get('terminees', 0),
            'seances_en_cours': stats.get('en_cours', 0),
            'teacher': str(titulaire.id) if titulaire else None,
            'teacher_name': titulaire.user.get_full_name() if titulaire else None,
            'enseignants_count': len({item.teacher_id for item in enseignants}),
            'attendus_count': attendus,
            'presents_count': presents,
            'taux_presence': round(presents / attendus * 100, 1) if attendus else 0.0,
            'statut': statut,
            'statut_label': STATUTS[statut],
            '_teachers': {str(item.teacher_id) for item in programmes if item.teacher_id}
            | {str(item.supervisor_id) for item in programmes if item.supervisor_id},
            '_search': fold_text(' '.join([
                course.code, course.name, course.teaching_unit.code, course.teaching_unit.name,
                promo.name, promo.program.code, promo.program.name,
                titulaire.user.get_full_name() if titulaire else '',
            ])),
        }
        lignes.append(ligne)

    if statut_filtre in STATUTS:
        lignes = [ligne for ligne in lignes if ligne['statut'] == statut_filtre]
    if teacher_id:
        lignes = [ligne for ligne in lignes if str(teacher_id) in ligne['_teachers']]
    if session_kind:
        lignes = [ligne for ligne in lignes if ligne['programmes_count']]
    if recherche:
        lignes = [ligne for ligne in lignes if recherche in ligne['_search']]

    lignes.sort(key=lambda item: (item['program_code'], item['promotion_name'], item['course_code']))
    kpis = _kpis(lignes)

    total = len(lignes)
    debut = (page - 1) * page_size
    page_lignes = lignes[debut:debut + page_size]
    for ligne in page_lignes:
        ligne.pop('_search', None)
        ligne.pop('_teachers', None)

    return {
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': page_lignes,
        'kpis': kpis,
        'filtre': {
            'academic_year': str(year.id),
            'academic_year_label': year.label,
            'periode': str(periode_id) if periode_id else None,
            'periodes_disponibles': [
                {'id': str(item.id), 'code': item.code, 'libelle': item.libelle}
                for item in PeriodeFormation.objects.filter(academic_year=year, is_active=True)
            ],
            'department': str(department_id) if department_id else None,
            'program': str(program_id) if program_id else None,
            'promotion': str(promotion_id) if promotion_id else None,
            'teaching_unit': str(teaching_unit_id) if teaching_unit_id else None,
            'teacher': str(teacher_id) if teacher_id else None,
            'semester_number': semester_number,
            'session_kind': session_kind or None,
            'statut': statut_filtre or None,
            'search': params.get('search') or None,
        },
    }


def _kpis(lignes) -> dict:
    total = len(lignes)
    programmees = sum(1 for ligne in lignes if ligne['programmes_count'])
    planifiees = sum(1 for ligne in lignes if ligne['seances_count'])
    sans_enseignant = sum(1 for ligne in lignes if not ligne['teacher'])
    heures_planifiees = round(sum(ligne['heures_planifiees'] for ligne in lignes), 2)
    heures_cible = round(sum(ligne['volume_cible_heures'] for ligne in lignes), 2)
    attendus = sum(ligne['attendus_count'] for ligne in lignes)
    presents = sum(ligne['presents_count'] for ligne in lignes)
    return {
        'offres': total,
        'programmees': programmees,
        'planifiees': planifiees,
        'non_programmees': total - programmees,
        'sans_enseignant': sans_enseignant,
        'seances': sum(ligne['seances_count'] for ligne in lignes),
        'heures_planifiees': heures_planifiees,
        'heures_cible': heures_cible,
        'taux_planification': round(planifiees / total * 100, 1) if total else 0.0,
        'taux_couverture': round(heures_planifiees / heures_cible * 100, 1) if heures_cible else 0.0,
        'taux_presence': round(presents / attendus * 100, 1) if attendus else 0.0,
    }
