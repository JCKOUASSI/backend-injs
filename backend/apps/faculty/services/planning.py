"""
Moteur d'emploi du temps INJS — inspiré du PlanningService EMPCPFAE,
adapté au LMD (promotions, UE/ECUE, salles sportives, formateurs, encadrants).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import time, timedelta

from django.utils import timezone

from apps.faculty.models import Schedule, CourseAssignment, Teacher, AttendanceSession
from apps.faculty.services.campus_ops import find_available_rooms, next_occurrence, seed_session_roster


# Créneaux types INJS (2h) — matin / après-midi
DEFAULT_SLOTS = [
    (time(8, 0), time(10, 0)),
    (time(10, 0), time(12, 0)),
    (time(14, 0), time(16, 0)),
    (time(16, 0), time(18, 0)),
]

DAYS = list(range(6))  # Lun–Sam
SEMESTER_WEEKS_DEFAULT = 15
MAX_COURSES_PER_PROMOTION = 24


class PlanningError(Exception):
    def __init__(self, message, code='planning_error'):
        super().__init__(message)
        self.code = code


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and a_end > b_start


def _weekly_session_count(hours, session_hours=2, semester_weeks=SEMESTER_WEEKS_DEFAULT):
    """
    Convertit un volume semestriel (heures maquette) en créneaux hebdomadaires.
    Ex. 30h CM / 15 semaines / 2h = 1 créneau par semaine.
    """
    if not hours or hours <= 0:
        return 0
    weeks = max(1, int(semester_weeks or SEMESTER_WEEKS_DEFAULT))
    weekly_hours = hours / weeks
    return max(1, int((weekly_hours + session_hours - 1) // session_hours))


def _preferred_room_types(kind):
    if kind == 'cm':
        return ['amphitheater', 'classroom', 'conference']
    if kind == 'td':
        return ['td', 'classroom', 'seminar']
    if kind == 'tp':
        return ['tp', 'lab', 'gym', 'sport', 'medical', 'computer']
    return ['classroom']


def _staff_ids(schedule):
    ids = {schedule.assignment.teacher_id}
    supervisor = None
    if hasattr(schedule, 'resolved_supervisor'):
        supervisor = schedule.resolved_supervisor()
    if supervisor:
        ids.add(supervisor.id)
    elif getattr(schedule, 'supervisor_id', None):
        ids.add(schedule.supervisor_id)
    elif getattr(schedule.assignment, 'supervisor_id', None):
        ids.add(schedule.assignment.supervisor_id)
    return ids


def detect_conflicts(queryset=None):
    """
    Détecte les conflits EDT (salle, enseignant, encadrant, promotion).
    Retourne une liste de dicts {type, severity, message, schedule_ids, ...}.
    """
    qs = queryset if queryset is not None else Schedule.objects.filter(is_active=True)
    qs = qs.select_related(
        'assignment__teacher__user',
        'assignment__supervisor__user',
        'assignment__course',
        'assignment__promotion',
        'supervisor__user',
        'room',
    )
    schedules = list(qs)
    conflicts = []

    by_day = defaultdict(list)
    for s in schedules:
        by_day[s.day_of_week].append(s)

    for day, items in by_day.items():
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                if not _overlaps(a.start_time, a.end_time, b.start_time, b.end_time):
                    continue

                if a.room_id and b.room_id and a.room_id == b.room_id:
                    conflicts.append({
                        'type': 'room',
                        'severity': 'error',
                        'message': (
                            f"Salle {a.room.code} en double le {a.get_day_of_week_display()} "
                            f"{a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')} "
                            f"({a.assignment.course.code} vs {b.assignment.course.code})"
                        ),
                        'schedule_ids': [str(a.id), str(b.id)],
                        'day_of_week': day,
                        'resource': a.room.code,
                    })

                overlap_staff = _staff_ids(a) & _staff_ids(b)
                if overlap_staff:
                    if (
                        a.assignment.teacher_id in overlap_staff
                        and a.assignment.teacher_id == b.assignment.teacher_id
                    ):
                        teacher_name = a.assignment.teacher.user.get_full_name()
                        conflicts.append({
                            'type': 'teacher',
                            'severity': 'error',
                            'message': (
                                f"Formateur {teacher_name} en double le {a.get_day_of_week_display()} "
                                f"{a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')}"
                            ),
                            'schedule_ids': [str(a.id), str(b.id)],
                            'day_of_week': day,
                            'resource': teacher_name,
                        })
                    else:
                        sa = a.resolved_supervisor()
                        name = sa.user.get_full_name() if sa else a.assignment.teacher.user.get_full_name()
                        conflicts.append({
                            'type': 'supervisor',
                            'severity': 'error',
                            'message': (
                                f"Encadrant / formateur en double le {a.get_day_of_week_display()} "
                                f"{a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')} "
                                f"({name})"
                            ),
                            'schedule_ids': [str(a.id), str(b.id)],
                            'day_of_week': day,
                            'resource': name,
                        })

                if a.assignment.promotion_id == b.assignment.promotion_id:
                    promo = a.assignment.promotion.name
                    conflicts.append({
                        'type': 'promotion',
                        'severity': 'error',
                        'message': (
                            f"Promotion {promo} : deux cours simultanés "
                            f"({a.assignment.course.code} / {b.assignment.course.code}) "
                            f"le {a.get_day_of_week_display()} "
                            f"{a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')}"
                        ),
                        'schedule_ids': [str(a.id), str(b.id)],
                        'day_of_week': day,
                        'resource': promo,
                    })

    for s in schedules:
        if s.room and s.room.status == 'maintenance':
            conflicts.append({
                'type': 'maintenance',
                'severity': 'warning',
                'message': f"Créneau sur salle en maintenance : {s.room.code} ({s.assignment.course.code})",
                'schedule_ids': [str(s.id)],
                'day_of_week': s.day_of_week,
                'resource': s.room.code,
            })

    for s in schedules:
        if not s.room:
            continue
        effectif = s.assignment.promotion.students.filter(status='active').count()
        if effectif and s.room.capacity < effectif:
            conflicts.append({
                'type': 'capacity',
                'severity': 'warning',
                'message': (
                    f"{s.room.code} trop petite ({s.room.capacity} < {effectif}) "
                    f"pour {s.assignment.course.code} / {s.assignment.promotion.name}"
                ),
                'schedule_ids': [str(s.id)],
                'day_of_week': s.day_of_week,
                'resource': s.room.code,
            })

    return conflicts


def _score_room(room, effectif, usage_counter, preferred_types):
    under = 1 if room.capacity < effectif else 0
    gap = abs(room.capacity - max(effectif, 1))
    type_penalty = 0 if room.room_type in preferred_types else 5
    usage = usage_counter.get(room.id, 0)
    return (under, type_penalty, gap * 10 + usage)


def _pick_room(day, start, end, effectif, preferred_types, usage_counter, exclude_ids=None):
    candidates = find_available_rooms(
        min_capacity=max(effectif, 1),
        day_of_week=day,
        start_time=start,
        end_time=end,
    )
    if exclude_ids:
        candidates = [r for r in candidates if r.id not in exclude_ids]
    if not candidates:
        candidates = find_available_rooms(
            min_capacity=1,
            day_of_week=day,
            start_time=start,
            end_time=end,
        )
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda r: _score_room(r, effectif, usage_counter, preferred_types),
    )
    return ranked[0]


def _slot_free_for_promotion(day, start, end, promotion_id, existing):
    for s in existing:
        if s.day_of_week != day:
            continue
        if s.assignment.promotion_id != promotion_id:
            continue
        if _overlaps(start, end, s.start_time, s.end_time):
            return False
    return True


def _slot_free_for_staff(day, start, end, staff_ids, existing):
    if not staff_ids:
        return True
    staff_ids = set(staff_ids)
    for s in existing:
        if s.day_of_week != day:
            continue
        if not staff_ids & _staff_ids(s):
            continue
        if _overlaps(start, end, s.start_time, s.end_time):
            return False
    return True


def courses_for_promotion(promotion, semester_number=None):
    """ECUE de la maquette pour le semestre courant de la promotion."""
    from apps.academics.models import Course, ProgramCourse

    semester = semester_number or promotion.current_semester or 1
    program = promotion.program
    links = ProgramCourse.objects.filter(program=program, semester_number=semester)
    if not links.exists():
        links = ProgramCourse.objects.filter(program=program)
    tu_ids = list(links.values_list('teaching_unit_id', flat=True))
    qs = Course.objects.filter(is_deleted=False)
    if tu_ids:
        qs = qs.filter(teaching_unit_id__in=tu_ids)
    else:
        qs = qs.filter(
            teaching_unit__department=program.department,
            teaching_unit__semester_number=semester,
        )
    return list(qs.select_related('teaching_unit').order_by('code')[:MAX_COURSES_PER_PROMOTION])


def ensure_assignments_for_promotion(promotion, academic_year, semester_number=None):
    """
    Crée les affectations formateur ↔ ECUE ↔ promotion si absentes,
    et pose un encadrant distinct pour les cours avec TP.
    """
    teachers = list(
        Teacher.objects.filter(
            department=promotion.program.department,
            is_active=True,
        ).select_related('user').order_by('employee_id')
    )
    if not teachers:
        teachers = list(Teacher.objects.filter(is_active=True).select_related('user').order_by('employee_id'))
    if not teachers:
        raise PlanningError(
            'Aucun enseignant actif pour créer les affectations.',
            'no_teachers',
        )

    courses = courses_for_promotion(promotion, semester_number=semester_number)
    if not courses:
        raise PlanningError(
            'Aucun ECUE trouvé pour cette promotion (maquette / semestre).',
            'no_courses',
        )

    created, updated = [], []
    for i, course in enumerate(courses):
        teacher = teachers[i % len(teachers)]
        supervisor = None
        if (course.hours_tp or 0) > 0 and len(teachers) > 1:
            supervisor = teachers[(i + 1) % len(teachers)]
            if supervisor.id == teacher.id and len(teachers) > 2:
                supervisor = teachers[(i + 2) % len(teachers)]
            if supervisor.id == teacher.id:
                supervisor = None

        existing = (
            CourseAssignment.objects.filter(
                course=course,
                academic_year=academic_year,
                promotion=promotion,
            ).select_related('teacher', 'supervisor').order_by('-is_primary').first()
        )
        if existing:
            if not existing.supervisor_id and supervisor and supervisor.id != existing.teacher_id:
                existing.supervisor = supervisor
                existing.save(update_fields=['supervisor', 'updated_at'])
                updated.append(existing)
            continue

        obj = CourseAssignment.objects.create(
            teacher=teacher,
            supervisor=supervisor,
            course=course,
            academic_year=academic_year,
            promotion=promotion,
            is_primary=True,
        )
        created.append(obj)

    return {
        'created': len(created),
        'updated': len(updated),
        'courses': len(courses),
        'teachers': len(teachers),
        'assignments': list(
            CourseAssignment.objects.filter(promotion=promotion, academic_year=academic_year)
        ),
    }


def open_sessions_for_schedules(schedules, *, from_date, weeks=1, recorded_by=None):
    """Ouvre les séances de présence (étudiants + staff) pour N semaines."""
    from apps.faculty.services.session_qr import seed_staff_roster

    weeks = max(1, min(int(weeks or 1), 16))
    opened = 0
    for schedule in schedules:
        for w in range(weeks):
            session_date = next_occurrence(schedule.day_of_week, from_date + timedelta(days=7 * w))
            session, created = AttendanceSession.objects.get_or_create(
                schedule=schedule,
                session_date=session_date,
                defaults={'is_active': True, 'created_by': recorded_by},
            )
            if created:
                opened += 1
            try:
                seed_session_roster(session, recorded_by=recorded_by)
            except Exception:
                pass
            try:
                seed_staff_roster(session, recorded_by=recorded_by)
            except Exception:
                pass
    return {'sessions_opened': opened, 'weeks': weeks, 'from_date': from_date.isoformat()}


def generate_for_promotion(
    *,
    promotion,
    academic_year,
    replace_existing=False,
    max_sessions_per_day=3,
    dry_run=False,
    auto_seed_roster=False,
    seed_from_date=None,
    seed_weeks=1,
    recorded_by=None,
    auto_assign_teachers=True,
    semester_weeks=SEMESTER_WEEKS_DEFAULT,
    semester_number=None,
    open_sessions=True,
):
    """
    Génère un EDT hebdomadaire pour une promotion (mode best_effort).
    Peut créer les affectations formateur/encadrant à partir de la maquette.
    """
    from datetime import date as date_cls
    from apps.faculty.services.campus_ops import seed_rosters_for_schedules

    assignment_info = None
    if auto_assign_teachers:
        assignment_info = ensure_assignments_for_promotion(
            promotion, academic_year, semester_number=semester_number,
        )

    assignments = list(
        CourseAssignment.objects.filter(
            promotion=promotion,
            academic_year=academic_year,
        ).select_related('course', 'teacher__user', 'supervisor__user', 'promotion')
    )
    if not assignments:
        raise PlanningError(
            'Aucune affectation enseignant/cours pour cette promotion et année.',
            'no_assignments',
        )

    existing = list(
        Schedule.objects.filter(
            is_active=True,
            assignment__promotion=promotion,
            assignment__academic_year=academic_year,
        ).select_related('assignment', 'assignment__teacher', 'assignment__supervisor', 'supervisor', 'room')
    )

    if replace_existing and not dry_run:
        for s in existing:
            s.is_active = False
            s.save(update_fields=['is_active', 'updated_at'])
        existing = []
    elif replace_existing and dry_run:
        existing = []

    effectif = promotion.students.filter(status='active').count() or 30
    usage_counter = defaultdict(int)
    for s in existing:
        if s.room_id:
            usage_counter[s.room_id] += 1

    load_per_day = defaultdict(int)
    for s in existing:
        load_per_day[s.day_of_week] += 1

    planned = []
    failures = []
    created_objs = []

    def difficulty(a):
        c = a.course
        return (c.hours_tp or 0) * 3 + (c.hours_td or 0) * 2 + (c.hours_cm or 0)

    assignments.sort(key=difficulty, reverse=True)

    for assignment in assignments:
        course = assignment.course
        needs = [
            ('cm', _weekly_session_count(course.hours_cm, semester_weeks=semester_weeks)),
            ('td', _weekly_session_count(course.hours_td, semester_weeks=semester_weeks)),
            ('tp', _weekly_session_count(course.hours_tp, semester_weeks=semester_weeks)),
        ]
        if sum(n for _, n in needs) == 0:
            needs = [('cm', 1)]

        for kind, count in needs:
            preferred = _preferred_room_types(kind)
            slot_supervisor = assignment.supervisor if kind == 'tp' else None
            staff_ids = {assignment.teacher_id}
            if slot_supervisor:
                staff_ids.add(slot_supervisor.id)

            for _ in range(count):
                placed = False
                days_ordered = sorted(DAYS, key=lambda d: load_per_day[d])
                for day in days_ordered:
                    if load_per_day[day] >= max_sessions_per_day:
                        continue
                    for start, end in DEFAULT_SLOTS:
                        pool = existing + created_objs
                        if not _slot_free_for_promotion(day, start, end, promotion.id, pool):
                            continue
                        if not _slot_free_for_staff(day, start, end, staff_ids, pool):
                            continue
                        room = _pick_room(day, start, end, effectif, preferred, usage_counter)
                        if room:
                            conflict_new = any(
                                c.room_id == room.id and c.day_of_week == day
                                and _overlaps(start, end, c.start_time, c.end_time)
                                for c in created_objs
                            )
                            if conflict_new:
                                room = _pick_room(
                                    day, start, end, effectif, preferred, usage_counter,
                                    exclude_ids={room.id},
                                )

                        draft = {
                            'assignment_id': str(assignment.id),
                            'course_code': course.code,
                            'course_name': course.name,
                            'kind': kind,
                            'day_of_week': day,
                            'start_time': start.strftime('%H:%M'),
                            'end_time': end.strftime('%H:%M'),
                            'room_id': str(room.id) if room else None,
                            'room_code': room.code if room else None,
                            'teacher': assignment.teacher.user.get_full_name(),
                            'supervisor': (
                                slot_supervisor.user.get_full_name() if slot_supervisor else None
                            ),
                            'effectif': effectif,
                        }
                        if dry_run:
                            planned.append(draft)
                            load_per_day[day] += 1
                            if room:
                                usage_counter[room.id] += 1
                            placed = True
                            break

                        obj = Schedule(
                            assignment=assignment,
                            room=room,
                            supervisor=slot_supervisor,
                            session_kind=kind,
                            day_of_week=day,
                            start_time=start,
                            end_time=end,
                            is_active=True,
                        )
                        obj.save()
                        created_objs.append(obj)
                        planned.append({**draft, 'id': str(obj.id)})
                        load_per_day[day] += 1
                        if room:
                            usage_counter[room.id] += 1
                        placed = True
                        break
                    if placed:
                        break

                if not placed:
                    failures.append({
                        'course': course.code,
                        'kind': kind,
                        'reason': 'Aucun créneau libre (formateur / encadrant / promotion / salles)',
                    })

    roster_result = None
    sessions_result = None
    seed_date = seed_from_date or timezone.localdate()
    if isinstance(seed_date, str):
        seed_date = date_cls.fromisoformat(seed_date)

    if auto_seed_roster and not dry_run and created_objs:
        roster_result = seed_rosters_for_schedules(
            created_objs,
            from_date=seed_date,
            weeks=seed_weeks,
            recorded_by=recorded_by,
            default_status='absent',
        )

    if open_sessions and not dry_run and created_objs:
        sessions_result = open_sessions_for_schedules(
            created_objs,
            from_date=seed_date,
            weeks=seed_weeks,
            recorded_by=recorded_by,
        )

    conflicts = detect_conflicts(
        Schedule.objects.filter(
            is_active=True,
            assignment__promotion=promotion,
            assignment__academic_year=academic_year,
        )
    ) if not dry_run else []

    return {
        'promotion': promotion.name,
        'promotion_id': str(promotion.id),
        'academic_year': academic_year.label,
        'assignments': len(assignments),
        'assignments_created': (assignment_info or {}).get('created', 0),
        'created': len(planned),
        'failures': failures,
        'conflicts': conflicts,
        'dry_run': dry_run,
        'slots': planned,
        'effectif_promotion': promotion.students.filter(status='active').count(),
        'roster': roster_result,
        'sessions': sessions_result,
    }


def generate_for_academic_year(academic_year, promotions=None, **kwargs):
    """Génère l'EDT de toutes les promotions actives d'une année."""
    from apps.academics.models import Promotion

    if promotions is None:
        promotions = list(Promotion.objects.filter(is_active=True).select_related('program'))
    results = []
    for promo in promotions:
        try:
            results.append(generate_for_promotion(
                promotion=promo,
                academic_year=academic_year,
                **kwargs,
            ))
        except PlanningError as exc:
            results.append({
                'promotion': promo.name,
                'promotion_id': str(promo.id),
                'error': str(exc),
                'code': exc.code,
                'created': 0,
                'failures': [],
            })
    return {
        'academic_year': academic_year.label,
        'promotions': len(results),
        'created': sum(r.get('created', 0) for r in results),
        'failed_promotions': sum(1 for r in results if r.get('error')),
        'results': results,
    }


def timetable_grid(schedules):
    """Structure grille hebdo pour le frontend (jours × créneaux)."""
    slots = []
    for s in schedules:
        supervisor = s.resolved_supervisor()
        effectif = s.assignment.promotion.students.filter(status='active').count()
        slots.append({
            'id': str(s.id),
            'day_of_week': s.day_of_week,
            'day_display': s.get_day_of_week_display(),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'session_kind': s.session_kind,
            'session_kind_display': s.get_session_kind_display(),
            'course_name': s.assignment.course.name,
            'course_code': s.assignment.course.code,
            'teacher_name': s.assignment.teacher.user.get_full_name(),
            'teacher_id': str(s.assignment.teacher_id),
            'supervisor_name': supervisor.user.get_full_name() if supervisor else None,
            'supervisor_id': str(supervisor.id) if supervisor else None,
            'promotion_name': s.assignment.promotion.name,
            'promotion_id': str(s.assignment.promotion_id),
            'effectif': effectif,
            'assignment': str(s.assignment_id),
            'room_id': str(s.room_id) if s.room_id else None,
            'room_code': s.room.code if s.room else None,
            'room_name': s.room.name if s.room else None,
            'room_capacity': s.room.capacity if s.room else None,
        })
    return {
        'days': [{'value': i, 'label': label} for i, label in Schedule.DAYS],
        'time_slots': [
            {'start': s.strftime('%H:%M'), 'end': e.strftime('%H:%M')}
            for s, e in DEFAULT_SLOTS
        ],
        'schedules': slots,
    }
