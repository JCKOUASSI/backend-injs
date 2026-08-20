"""Fiche détaillée d'une offre « Cours (ECUE) ».

Alimente les cinq onglets de la fiche (Séances, Informations, Étudiants,
Présences, Enseignants) en agrégeant **toutes les périodes de formation**.
"""
from __future__ import annotations

from collections import defaultdict

from django.db.models import Count, Q

from apps.academics.models import Course, Promotion
from apps.students.models import Student

from ..models import GroupePedagogique, Pointage, ProgrammePeriode, Seance
from .common import heures, offering_id, parse_offering_id, parse_uuid, resolve_academic_year


def _serialiser_seance(seance, stats) -> dict:
    return {
        'id': str(seance.id),
        'programme': str(seance.programme_id),
        'periode': str(seance.periode_id),
        'periode_code': seance.periode.code,
        'periode_libelle': seance.periode.libelle,
        'numero': seance.numero,
        'intitule': seance.intitule,
        'date': seance.date.isoformat(),
        'day_display': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'][
            seance.date.weekday()
        ],
        'heure_debut': seance.heure_debut.strftime('%H:%M'),
        'heure_fin': seance.heure_fin.strftime('%H:%M'),
        'duree_heures': seance.duree_heures,
        'session_kind': seance.session_kind,
        'session_kind_display': seance.get_session_kind_display(),
        'statut': seance.statut,
        'statut_display': seance.get_statut_display(),
        'origine': seance.origine,
        'groupe': str(seance.groupe_id) if seance.groupe_id else None,
        'groupe_code': seance.groupe.code if seance.groupe_id else None,
        'room': str(seance.room_id) if seance.room_id else None,
        'room_code': seance.room.code if seance.room_id else None,
        'room_name': seance.room.name if seance.room_id else None,
        'teacher': str(seance.teacher_id) if seance.teacher_id else None,
        'teacher_name': seance.teacher.user.get_full_name() if seance.teacher_id else None,
        'supervisor_name': seance.supervisor.user.get_full_name() if seance.supervisor_id else None,
        'attendus_count': stats.get('attendus', 0),
        'presents_count': stats.get('presents', 0),
        'absents_count': stats.get('absents', 0),
        'taux_presence': (
            round(stats.get('presents', 0) / stats['attendus'] * 100, 1) if stats.get('attendus') else 0.0
        ),
        'is_open': seance.statut == 'en_cours',
    }


def _serialiser_programme(programme, minutes_par_programme) -> dict:
    cible = programme.volume_horaire_minutes or programme.volume_maquette_minutes()
    place = minutes_par_programme.get(programme.id, 0)
    return {
        'id': str(programme.id),
        'periode': str(programme.periode_id),
        'periode_code': programme.periode.code,
        'periode_libelle': programme.periode.libelle,
        'periode_debut': programme.periode.date_debut.isoformat(),
        'periode_fin': programme.periode.date_fin.isoformat(),
        'session_kind': programme.session_kind,
        'session_kind_display': programme.get_session_kind_display(),
        'creneau_mode': programme.creneau_mode,
        'teacher': str(programme.teacher_id) if programme.teacher_id else None,
        'teacher_name': programme.teacher.user.get_full_name() if programme.teacher_id else None,
        'supervisor': str(programme.supervisor_id) if programme.supervisor_id else None,
        'supervisor_name': (
            programme.supervisor.user.get_full_name() if programme.supervisor_id else None
        ),
        'volume_cible_heures': heures(cible),
        'heures_planifiees': heures(place),
        'taux_couverture': round(place / cible * 100, 1) if cible else 0.0,
        'groupes': [
            {'id': str(groupe.id), 'code': groupe.code, 'name': groupe.name}
            for groupe in programme.groupes.all()
        ],
        'is_active': programme.is_active,
    }


def get_offering(params) -> dict | None:
    """Fiche complète d'une offre ECUE × promotion."""
    course_id = parse_uuid(params.get('course'))
    promotion_id = parse_uuid(params.get('promotion'))
    parsed_course, parsed_promo = parse_offering_id(params.get('id'))
    course_id = course_id or parsed_course
    promotion_id = promotion_id or parsed_promo
    if not course_id or not promotion_id:
        return None

    course = Course.objects.select_related('teaching_unit', 'teaching_unit__department').filter(
        pk=course_id,
    ).first()
    promotion = Promotion.objects.select_related('program', 'program__department').filter(
        pk=promotion_id,
    ).first()
    if not course or not promotion:
        return None

    year = resolve_academic_year(parse_uuid(params.get('academic_year')))
    periode_filtre = parse_uuid(params.get('periode'))

    programmes = list(
        ProgrammePeriode.objects
        .filter(course=course, promotion=promotion)
        .select_related('periode', 'periode__academic_year', 'teacher__user', 'supervisor__user')
        .prefetch_related('groupes')
        .order_by('periode__ordre', 'periode__date_debut', 'session_kind')
    )
    if periode_filtre:
        programmes = [item for item in programmes if item.periode_id == periode_filtre]

    seances_qs = (
        Seance.objects
        .filter(course=course, promotion=promotion)
        .exclude(statut='annulee')
        .select_related('periode', 'room', 'groupe', 'teacher__user', 'supervisor__user')
        .order_by('date', 'heure_debut')
    )
    if periode_filtre:
        seances_qs = seances_qs.filter(periode_id=periode_filtre)
    seances = list(seances_qs)

    stats_par_seance = {
        ligne['seance_id']: ligne
        for ligne in Pointage.objects
        .filter(seance__in=seances)
        .values('seance_id')
        .annotate(
            attendus=Count('id'),
            presents=Count('id', filter=Q(statut__in=['present', 'retard', 'force'])),
            absents=Count('id', filter=Q(statut='absent')),
        )
    }

    minutes_par_programme: dict = defaultdict(int)
    for seance in seances:
        minutes_par_programme[seance.programme_id] += seance.duree_minutes or 0

    etudiants = list(
        Student.objects
        .filter(promotion=promotion, status='active')
        .select_related('user')
        .order_by('matricule')
    )
    presences_par_etudiant = {
        ligne['student_id']: ligne
        for ligne in Pointage.objects
        .filter(seance__in=seances, student__isnull=False)
        .values('student_id')
        .annotate(
            seances=Count('id'),
            presents=Count('id', filter=Q(statut__in=['present', 'retard', 'force'])),
            absents=Count('id', filter=Q(statut='absent')),
        )
    }

    enseignants: dict = {}
    for programme in programmes:
        for role, teacher in (('titulaire', programme.teacher), ('encadrant', programme.supervisor)):
            if teacher is None:
                continue
            entree = enseignants.setdefault(str(teacher.id), {
                'id': str(teacher.id),
                'nom': teacher.user.get_full_name(),
                'employee_id': teacher.employee_id,
                'grade': teacher.get_grade_display(),
                'roles': set(),
                'periodes': set(),
                'seances_count': 0,
            })
            entree['roles'].add(role)
            entree['periodes'].add(programme.periode.code)
    for seance in seances:
        if seance.teacher_id and str(seance.teacher_id) in enseignants:
            enseignants[str(seance.teacher_id)]['seances_count'] += 1

    minutes_planifiees = sum(seance.duree_minutes or 0 for seance in seances)
    minutes_cible = sum(
        item.volume_horaire_minutes or item.volume_maquette_minutes() for item in programmes
    )
    volume_maquette = (course.hours_cm or 0) + (course.hours_td or 0) + (course.hours_tp or 0)
    total_attendus = sum(ligne.get('attendus', 0) for ligne in stats_par_seance.values())
    total_presents = sum(ligne.get('presents', 0) for ligne in stats_par_seance.values())

    seances_serialisees = [
        _serialiser_seance(seance, stats_par_seance.get(seance.id, {})) for seance in seances
    ]
    par_periode: dict = defaultdict(list)
    for item in seances_serialisees:
        par_periode[item['periode']].append(item)

    return {
        'id': offering_id(course.id, promotion.id),
        'course': str(course.id),
        'course_code': course.code,
        'course_name': course.name,
        'teaching_unit': str(course.teaching_unit_id),
        'teaching_unit_code': course.teaching_unit.code,
        'teaching_unit_name': course.teaching_unit.name,
        'department_name': course.teaching_unit.department.name,
        'semester_number': course.teaching_unit.semester_number,
        'credits_ects': course.teaching_unit.credits_ects,
        'coefficient': float(course.coefficient or 0),
        'passing_score': float(course.passing_score or 0),
        'hours_cm': course.hours_cm,
        'hours_td': course.hours_td,
        'hours_tp': course.hours_tp,
        'volume_maquette_heures': volume_maquette,
        'program': str(promotion.program_id),
        'program_code': promotion.program.code,
        'program_name': promotion.program.name,
        'degree_type_display': promotion.program.get_degree_type_display(),
        'promotion': str(promotion.id),
        'promotion_name': promotion.name,
        'academic_year': str(year.id) if year else None,
        'academic_year_label': year.label if year else None,
        'periode_filtre': str(periode_filtre) if periode_filtre else None,

        'programmes': [_serialiser_programme(item, minutes_par_programme) for item in programmes],
        'programmes_count': len(programmes),
        'periodes': [
            {
                'id': str(item.periode_id),
                'code': item.periode.code,
                'libelle': item.periode.libelle,
                'date_debut': item.periode.date_debut.isoformat(),
                'date_fin': item.periode.date_fin.isoformat(),
                'seances_count': len(par_periode.get(str(item.periode_id), [])),
            }
            for item in {programme.periode_id: programme for programme in programmes}.values()
        ],

        'seances': seances_serialisees,
        'seances_count': len(seances),
        'seances_par_periode': dict(par_periode),
        'heures_planifiees': heures(minutes_planifiees),
        'volume_cible_heures': heures(minutes_cible),
        'taux_couverture': round(minutes_planifiees / minutes_cible * 100, 1) if minutes_cible else 0.0,

        'etudiants': [
            {
                'id': str(etudiant.id),
                'matricule': etudiant.matricule,
                'nom': etudiant.user.get_full_name(),
                'statut': etudiant.get_status_display(),
                'seances_suivies': presences_par_etudiant.get(etudiant.id, {}).get('seances', 0),
                'presents': presences_par_etudiant.get(etudiant.id, {}).get('presents', 0),
                'absents': presences_par_etudiant.get(etudiant.id, {}).get('absents', 0),
                'taux_presence': (
                    round(
                        presences_par_etudiant[etudiant.id]['presents']
                        / presences_par_etudiant[etudiant.id]['seances'] * 100, 1,
                    )
                    if presences_par_etudiant.get(etudiant.id, {}).get('seances') else 0.0
                ),
            }
            for etudiant in etudiants
        ],
        'etudiants_count': len(etudiants),

        'groupes': [
            {
                'id': str(groupe.id), 'code': groupe.code, 'name': groupe.name,
                'effectif': groupe.effectif, 'effectif_max': groupe.effectif_max,
            }
            for groupe in GroupePedagogique.objects.filter(promotion=promotion, is_active=True)
        ],

        'enseignants': [
            {**entree, 'roles': sorted(entree['roles']), 'periodes': sorted(entree['periodes'])}
            for entree in enseignants.values()
        ],
        'enseignants_count': len(enseignants),

        'presences': {
            'attendus': total_attendus,
            'presents': total_presents,
            'absents': sum(ligne.get('absents', 0) for ligne in stats_par_seance.values()),
            'taux_presence': round(total_presents / total_attendus * 100, 1) if total_attendus else 0.0,
        },
    }
