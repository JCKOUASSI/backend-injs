"""Catalogue opérationnel « Cours » INJS.

Façade produit sur Course (ECUE) × Promotion × année, avec affectations
et créneaux. Aucune table homonyme : academics.Course reste l'ECUE LMD.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from unicodedata import combining, normalize
from uuid import UUID

from django.db.models import Count, Q

from apps.academics.models import AcademicYear, Course, ProgramCourse, Promotion
from apps.faculty.models import Attendance, AttendanceSession, CourseAssignment, Schedule
from apps.students.models import Student

STATUS_LABELS = {
    'non_affecte': 'Non affecté',
    'affecte': 'Affecté',
    'planifie': 'Planifié',
}

SEMESTER_WEEKS = 15


def parse_uuid(value):
    if not value:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def fold_text(value: str) -> str:
    text = normalize('NFKD', value or '')
    return ''.join(char for char in text if not combining(char)).lower()


def slot_hours(start: time, end: time) -> float:
    dummy = date(2000, 1, 1)
    seconds = (datetime.combine(dummy, end) - datetime.combine(dummy, start)).total_seconds()
    return round(max(seconds, 0) / 3600, 2)


def resolve_academic_year(year_id=None):
    if year_id:
        year = AcademicYear.objects.filter(pk=year_id).first()
        if year:
            return year
    return AcademicYear.objects.filter(is_current=True).order_by('-start_date').first()


def _int_param(params, key, default, *, minimum=1, maximum=100):
    raw = params.get(key)
    if raw in (None, ''):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _offering_id(course_id, promotion_id, year_id):
    return f'{course_id}:{promotion_id}:{year_id}'


def parse_offering_id(value):
    parts = str(value or '').split(':')
    if len(parts) != 3:
        return None, None, None
    return parse_uuid(parts[0]), parse_uuid(parts[1]), parse_uuid(parts[2])


def _status(assignments, slots_count):
    if not assignments:
        return 'non_affecte'
    if slots_count:
        return 'planifie'
    return 'affecte'


def _primary_assignment(assignments):
    if not assignments:
        return None
    primaries = [row for row in assignments if row.get('is_primary')]
    return (primaries or assignments)[0]


def build_cours_catalog(params) -> dict:
    year = resolve_academic_year(parse_uuid(params.get('academic_year')))
    department_id = parse_uuid(params.get('department'))
    program_id = parse_uuid(params.get('program'))
    promotion_id = parse_uuid(params.get('promotion'))
    teaching_unit_id = parse_uuid(params.get('teaching_unit'))
    teacher_id = parse_uuid(params.get('teacher'))
    specialization_id = parse_uuid(params.get('specialization'))
    semester_number = params.get('semester_number')
    try:
        semester_number = int(semester_number) if semester_number not in (None, '') else None
    except (TypeError, ValueError):
        semester_number = None
    status_filter = (params.get('status') or '').strip()
    search = fold_text(params.get('search') or params.get('q') or '')
    page = _int_param(params, 'page', 1, minimum=1, maximum=10_000)
    page_size = _int_param(params, 'page_size', 25, minimum=1, maximum=100)

    if not year:
        return {
            'count': 0,
            'page': page,
            'page_size': page_size,
            'results': [],
            'kpis': _empty_kpis(),
            'filtre': {
                'academic_year': None,
                'academic_year_label': None,
                'warning': "Aucune année académique courante.",
            },
        }

    promotions = _promotion_queryset(
        department_id=department_id,
        program_id=program_id,
        promotion_id=promotion_id,
    )
    rows = _build_offerings(
        year=year,
        promotions=promotions,
        department_id=department_id,
        teaching_unit_id=teaching_unit_id,
        teacher_id=teacher_id,
        specialization_id=specialization_id,
        semester_number=semester_number,
    )

    if status_filter in STATUS_LABELS:
        rows = [row for row in rows if row['status'] == status_filter]
    if search:
        rows = [row for row in rows if search in row['search_blob']]
    if teacher_id:
        rows = [
            row for row in rows
            if any(
                str(item.get('teacher')) == str(teacher_id)
                or str(item.get('supervisor') or '') == str(teacher_id)
                for item in row['assignments']
            )
        ]

    kpis = _kpis(rows)
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]
    for row in page_rows:
        row.pop('search_blob', None)
        row.pop('assignments', None)

    return {
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': page_rows,
        'kpis': kpis,
        'filtre': {
            'academic_year': str(year.id),
            'academic_year_label': year.label,
            'department': str(department_id) if department_id else None,
            'program': str(program_id) if program_id else None,
            'promotion': str(promotion_id) if promotion_id else None,
            'teaching_unit': str(teaching_unit_id) if teaching_unit_id else None,
            'teacher': str(teacher_id) if teacher_id else None,
            'semester_number': semester_number,
            'status': status_filter or None,
            'search': search or None,
        },
    }


def get_cours_offering(params) -> dict | None:
    course_id = parse_uuid(params.get('course'))
    promotion_id = parse_uuid(params.get('promotion'))
    year_id = parse_uuid(params.get('academic_year'))
    parsed_course, parsed_promo, parsed_year = parse_offering_id(params.get('id'))
    course_id = course_id or parsed_course
    promotion_id = promotion_id or parsed_promo
    year_id = year_id or parsed_year
    year = resolve_academic_year(year_id)
    if not year or not course_id or not promotion_id:
        return None

    promotions = _promotion_queryset(
        department_id=None, program_id=None, promotion_id=promotion_id,
    )
    rows = _build_offerings(
        year=year,
        promotions=promotions,
        department_id=None,
        teaching_unit_id=None,
        teacher_id=None,
        specialization_id=None,
        semester_number=None,
    )
    offering = next((row for row in rows if str(row['course']) == str(course_id)), None)
    if offering is None:
        return None
    offering.pop('search_blob', None)

    assignments = list(
        CourseAssignment.objects.filter(
            academic_year=year,
            course_id=course_id,
            promotion_id=promotion_id,
        ).select_related(
            'teacher__user', 'supervisor__user', 'course', 'promotion', 'academic_year',
        ).order_by('-is_primary', 'created_at')
    )
    assignment_ids = [item.id for item in assignments]
    schedules = list(
        Schedule.objects.filter(is_active=True, assignment_id__in=assignment_ids)
        .select_related('room', 'assignment', 'supervisor__user')
        .order_by('day_of_week', 'start_time')
    ) if assignment_ids else []

    by_assignment = defaultdict(list)
    for slot in schedules:
        by_assignment[slot.assignment_id].append(slot)
    offering['assignments'] = [
        _serialize_assignment(item, by_assignment.get(item.id, []))
        for item in assignments
    ]
    offering['schedules'] = [_serialize_schedule(item) for item in schedules]
    offering['weekly_hours'] = round(sum(item['hours'] for item in offering['schedules']), 2)
    offering['estimated_semester_hours'] = round(offering['weekly_hours'] * SEMESTER_WEEKS, 1)
    volume = offering['hours_total'] or 0
    offering['coverage_pct'] = (
        round(offering['estimated_semester_hours'] / volume * 100, 1) if volume else 0.0
    )
    offering['sessions'] = _serialize_sessions(schedules)
    offering['sessions_count'] = len(offering['sessions'])
    offering['session_hours'] = round(sum(item['hours'] for item in offering['sessions']), 2)
    offering['volume_objectif'] = volume
    return offering


def _promotion_queryset(*, department_id, program_id, promotion_id):
    qs = Promotion.objects.select_related('program', 'program__department')
    if not promotion_id:
        qs = qs.filter(is_active=True)
    if department_id:
        qs = qs.filter(program__department_id=department_id)
    if program_id:
        qs = qs.filter(program_id=program_id)
    if promotion_id:
        qs = qs.filter(pk=promotion_id)
    return list(qs.order_by('program__code', 'name'))


def _build_offerings(
    *,
    year,
    promotions,
    department_id,
    teaching_unit_id,
    teacher_id,
    specialization_id,
    semester_number,
):
    if not promotions:
        return []

    program_ids = {promo.program_id for promo in promotions}
    links = ProgramCourse.objects.filter(program_id__in=program_ids)
    if specialization_id:
        links = links.filter(Q(specialization_id=specialization_id) | Q(specialization__isnull=True))
    if semester_number:
        links = links.filter(semester_number=semester_number)
    tu_by_program = defaultdict(set)
    for link in links.values_list('program_id', 'teaching_unit_id'):
        tu_by_program[link[0]].add(link[1])

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
    courses_by_id = {course.id: course for course in courses}
    courses_by_tu = defaultdict(list)
    for course in courses:
        courses_by_tu[course.teaching_unit_id].append(course)

    pairs = []
    seen = set()
    for promo in promotions:
        tu_ids = tu_by_program.get(promo.program_id)
        if tu_ids:
            promo_courses = [course for tu_id in tu_ids for course in courses_by_tu.get(tu_id, [])]
        else:
            semester = semester_number or promo.current_semester or 1
            promo_courses = [
                course for course in courses
                if course.teaching_unit.department_id == promo.program.department_id
                and course.teaching_unit.semester_number == semester
            ]
        for course in promo_courses:
            key = (course.id, promo.id)
            if key in seen:
                continue
            seen.add(key)
            pairs.append((course, promo))

    assignment_qs = CourseAssignment.objects.filter(
        academic_year=year,
        promotion_id__in=[promo.id for promo in promotions],
    ).select_related(
        'teacher__user', 'supervisor__user', 'course__teaching_unit', 'promotion',
    )
    if teacher_id:
        assignment_qs = assignment_qs.filter(Q(teacher_id=teacher_id) | Q(supervisor_id=teacher_id))
    assignments = list(assignment_qs)
    assignments_by_pair = defaultdict(list)
    for item in assignments:
        assignments_by_pair[(item.course_id, item.promotion_id)].append(item)
        if (item.course_id, item.promotion_id) not in seen:
            course = courses_by_id.get(item.course_id) or item.course
            if teaching_unit_id and course.teaching_unit_id != teaching_unit_id:
                continue
            promo = next((p for p in promotions if p.id == item.promotion_id), item.promotion)
            seen.add((item.course_id, item.promotion_id))
            pairs.append((course, promo))

    assignment_ids = [item.id for item in assignments]
    schedules_by_assignment = defaultdict(list)
    if assignment_ids:
        for schedule in Schedule.objects.filter(is_active=True, assignment_id__in=assignment_ids):
            schedules_by_assignment[schedule.assignment_id].append(schedule)

    student_counts = {
        row['promotion_id']: row['n']
        for row in Student.objects.filter(
            status='active',
            promotion_id__in=[promo.id for promo in promotions],
        ).values('promotion_id').annotate(n=Count('id'))
    }
    session_count_by_pair = defaultdict(int)
    session_hours_by_pair = defaultdict(float)
    if assignment_ids:
        for session in AttendanceSession.objects.filter(
            schedule__assignment_id__in=assignment_ids,
        ).select_related('schedule', 'schedule__assignment'):
            assignment = session.schedule.assignment
            key = (assignment.course_id, assignment.promotion_id)
            session_count_by_pair[key] += 1
            session_hours_by_pair[key] += slot_hours(
                session.schedule.start_time, session.schedule.end_time,
            )

    rows = []
    for course, promo in pairs:
        pair_assignments = assignments_by_pair.get((course.id, promo.id), [])
        pair_schedules = [
            slot
            for assignment in pair_assignments
            for slot in schedules_by_assignment.get(assignment.id, [])
        ]
        weekly = round(sum(slot_hours(slot.start_time, slot.end_time) for slot in pair_schedules), 2)
        serialized_assignments = [
            _serialize_assignment(item, schedules_by_assignment.get(item.id, []))
            for item in pair_assignments
        ]
        primary = _primary_assignment(serialized_assignments)
        hours_total = (course.hours_cm or 0) + (course.hours_td or 0) + (course.hours_tp or 0)
        status = _status(serialized_assignments, len(pair_schedules))
        row = {
            'id': _offering_id(course.id, promo.id, year.id),
            'course': str(course.id),
            'course_code': course.code,
            'course_name': course.name,
            'teaching_unit': str(course.teaching_unit_id),
            'teaching_unit_code': course.teaching_unit.code,
            'teaching_unit_name': course.teaching_unit.name,
            'semester_number': course.teaching_unit.semester_number,
            'credits_ects': course.teaching_unit.credits_ects,
            'coefficient': float(course.coefficient or 0),
            'degree_type': promo.program.degree_type,
            'degree_type_display': promo.program.get_degree_type_display(),
            'program': str(promo.program_id),
            'program_code': promo.program.code,
            'program_name': promo.program.name,
            'promotion': str(promo.id),
            'promotion_name': promo.name,
            'academic_year': str(year.id),
            'academic_year_label': year.label,
            'hours_cm': course.hours_cm,
            'hours_td': course.hours_td,
            'hours_tp': course.hours_tp,
            'hours_total': hours_total,
            'assignment': primary['id'] if primary else None,
            'teacher': primary['teacher'] if primary else None,
            'teacher_name': primary['teacher_name'] if primary else None,
            'supervisor': primary['supervisor'] if primary else None,
            'supervisor_name': primary['supervisor_name'] if primary else None,
            'assignments_count': len(serialized_assignments),
            'students_count': student_counts.get(promo.id, 0),
            'slots_count': len(pair_schedules),
            'weekly_hours': weekly,
            'sessions_count': session_count_by_pair.get((course.id, promo.id), 0),
            'session_hours': round(session_hours_by_pair.get((course.id, promo.id), 0), 2),
            'status': status,
            'status_label': STATUS_LABELS[status],
            'assignments': serialized_assignments,
            'search_blob': fold_text(' '.join([
                course.code, course.name,
                course.teaching_unit.code, course.teaching_unit.name,
                promo.name, promo.program.code, promo.program.name,
                primary['teacher_name'] if primary else '',
            ])),
        }
        rows.append(row)

    rows.sort(key=lambda item: (item['program_code'], item['promotion_name'], item['course_code']))
    return rows


def _serialize_assignment(item, schedules):
    return {
        'id': str(item.id),
        'teacher': str(item.teacher_id),
        'teacher_name': item.teacher.user.get_full_name(),
        'supervisor': str(item.supervisor_id) if item.supervisor_id else None,
        'supervisor_name': item.supervisor.user.get_full_name() if item.supervisor_id else None,
        'is_primary': item.is_primary,
        'slots_count': len(schedules),
    }


def _serialize_sessions(schedules):
    if not schedules:
        return []
    schedule_ids = [item.id for item in schedules]
    sessions = list(
        AttendanceSession.objects.filter(schedule_id__in=schedule_ids)
        .select_related('schedule', 'schedule__room', 'schedule__assignment')
        .order_by('session_date', 'schedule__start_time')
    )
    if not sessions:
        return []
    counts = {
        (row['schedule_id'], row['date']): row
        for row in Attendance.objects.filter(
            schedule_id__in=schedule_ids,
            date__in=[item.session_date for item in sessions],
        ).values('schedule_id', 'date').annotate(
            total=Count('id'),
            present=Count('id', filter=~Q(status='absent')),
        )
    }
    payload = []
    for session in sessions:
        hours = slot_hours(session.schedule.start_time, session.schedule.end_time)
        stats = counts.get((session.schedule_id, session.session_date), {})
        if session.is_active:
            status, label = 'en_cours', 'En cours'
        else:
            status, label = 'terminee', 'Terminée'
        payload.append({
            'id': str(session.id),
            'schedule': str(session.schedule_id),
            'session_date': session.session_date.isoformat(),
            'is_active': session.is_active,
            'status': status,
            'status_label': label,
            'day_display': session.schedule.get_day_of_week_display(),
            'start_time': session.schedule.start_time.strftime('%H:%M'),
            'end_time': session.schedule.end_time.strftime('%H:%M'),
            'session_kind': session.schedule.session_kind,
            'session_kind_display': session.schedule.get_session_kind_display(),
            'room_code': session.schedule.room.code if session.schedule.room_id else None,
            'present_count': stats.get('present', 0),
            'roster_count': stats.get('total', 0),
            'hours': hours,
        })
    return payload


def _serialize_schedule(item):
    hours = slot_hours(item.start_time, item.end_time)
    return {
        'id': str(item.id),
        'assignment': str(item.assignment_id),
        'day_of_week': item.day_of_week,
        'day_display': item.get_day_of_week_display(),
        'start_time': item.start_time.strftime('%H:%M'),
        'end_time': item.end_time.strftime('%H:%M'),
        'session_kind': item.session_kind,
        'session_kind_display': item.get_session_kind_display(),
        'room_code': item.room.code if item.room_id else None,
        'room_name': item.room.name if item.room_id else None,
        'hours': hours,
    }


def _empty_kpis():
    return {
        'offerings': 0,
        'assigned': 0,
        'unassigned': 0,
        'planned': 0,
        'hours_volume': 0,
        'weekly_hours': 0.0,
        'taux_affectation': 0.0,
        'taux_planification': 0.0,
    }


def _kpis(rows):
    offerings = len(rows)
    assigned = sum(1 for row in rows if row['status'] != 'non_affecte')
    planned = sum(1 for row in rows if row['status'] == 'planifie')
    hours_volume = sum(row['hours_total'] or 0 for row in rows)
    weekly_hours = round(sum(row['weekly_hours'] or 0 for row in rows), 2)
    return {
        'offerings': offerings,
        'assigned': assigned,
        'unassigned': offerings - assigned,
        'planned': planned,
        'hours_volume': hours_volume,
        'weekly_hours': weekly_hours,
        'taux_affectation': round(assigned / offerings * 100, 1) if offerings else 0.0,
        'taux_planification': round(planned / offerings * 100, 1) if offerings else 0.0,
    }
