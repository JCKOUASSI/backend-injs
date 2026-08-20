"""Utilitaires partagés par les services EPT-INJS."""
from __future__ import annotations

from collections import defaultdict
from datetime import date as date_cls, datetime, time as time_cls
from unicodedata import combining, normalize
from uuid import UUID

from apps.academics.models import AcademicYear, Course, ProgramCourse, Promotion


def parse_uuid(value):
    if not value:
        return None
    try:
        return UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return None


def parse_uuid_list(value):
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(',')
    return [parsed for parsed in (parse_uuid(item) for item in value) if parsed]


def parse_int(params, key, default, *, minimum=1, maximum=500):
    raw = params.get(key)
    if raw in (None, ''):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def parse_date(value) -> date_cls | None:
    if not value:
        return None
    if isinstance(value, date_cls):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def fold_text(value: str) -> str:
    """Normalise pour une recherche insensible aux accents et à la casse."""
    text = normalize('NFKD', value or '')
    return ''.join(char for char in text if not combining(char)).lower()


def heures(minutes: int | None) -> float:
    return round((minutes or 0) / 60, 2)


def minutes_between(debut: time_cls, fin: time_cls) -> int:
    pivot = date_cls(2000, 1, 1)
    return max(int((datetime.combine(pivot, fin) - datetime.combine(pivot, debut)).total_seconds() // 60), 0)


def offering_id(course_id, promotion_id) -> str:
    return f'{course_id}:{promotion_id}'


def parse_offering_id(value) -> tuple[UUID | None, UUID | None]:
    parts = str(value or '').split(':')
    # Tolère l'ancien format course:promotion:academic_year.
    if len(parts) not in (2, 3):
        return None, None
    return parse_uuid(parts[0]), parse_uuid(parts[1])


def resolve_academic_year(year_id=None):
    if year_id:
        year = AcademicYear.objects.filter(pk=year_id).first()
        if year:
            return year
    return AcademicYear.objects.filter(is_current=True).order_by('-start_date').first()


def promotions_filtrees(*, department_id=None, program_id=None, promotion_id=None):
    queryset = Promotion.objects.select_related('program', 'program__department')
    if not promotion_id:
        queryset = queryset.filter(is_active=True)
    if department_id:
        queryset = queryset.filter(program__department_id=department_id)
    if program_id:
        queryset = queryset.filter(program_id=program_id)
    if promotion_id:
        queryset = queryset.filter(pk=promotion_id)
    return list(queryset.order_by('program__code', 'name'))


def paires_ecue_promotion(
    promotions,
    *,
    department_id=None,
    teaching_unit_id=None,
    specialization_id=None,
    semester_number=None,
):
    """Couples (ECUE, promotion) issus de la maquette LMD.

    Reprend la logique de rattachement ``ProgramCourse → TeachingUnit → Course``,
    avec repli sur le département et le semestre courant quand la maquette n'est
    pas encore saisie pour la filière.
    """
    if not promotions:
        return []

    program_ids = {promo.program_id for promo in promotions}
    liens = ProgramCourse.objects.filter(program_id__in=program_ids)
    if specialization_id:
        liens = liens.filter(specialization_id=specialization_id)
    if semester_number:
        liens = liens.filter(semester_number=semester_number)

    ue_par_programme = defaultdict(set)
    for program_id, teaching_unit_id_lien in liens.values_list('program_id', 'teaching_unit_id'):
        ue_par_programme[program_id].add(teaching_unit_id_lien)

    course_qs = Course.objects.filter(is_deleted=False).select_related(
        'teaching_unit', 'teaching_unit__department',
    )
    if teaching_unit_id:
        course_qs = course_qs.filter(teaching_unit_id=teaching_unit_id)
    if department_id:
        course_qs = course_qs.filter(teaching_unit__department_id=department_id)
    if semester_number:
        course_qs = course_qs.filter(teaching_unit__semester_number=semester_number)

    courses = list(course_qs.order_by('code'))
    courses_par_ue = defaultdict(list)
    for course in courses:
        courses_par_ue[course.teaching_unit_id].append(course)

    paires = []
    vues = set()
    for promo in promotions:
        ue_ids = ue_par_programme.get(promo.program_id)
        if ue_ids:
            candidats = [course for ue_id in ue_ids for course in courses_par_ue.get(ue_id, [])]
        else:
            semestre = semester_number or promo.current_semester or 1
            candidats = [
                course for course in courses
                if course.teaching_unit.department_id == promo.program.department_id
                and course.teaching_unit.semester_number == semestre
            ]
        for course in candidats:
            cle = (course.id, promo.id)
            if cle in vues:
                continue
            vues.add(cle)
            paires.append((course, promo))
    return paires
