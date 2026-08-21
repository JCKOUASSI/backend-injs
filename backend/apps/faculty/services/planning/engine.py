"""Génération calendaire d'un emploi du temps à partir des charges et des périodes."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.academics.models import Holiday
from apps.faculty.models import (
    CourseAssignment,
    PlanningSettings,
    Schedule,
    Seance,
    TeachingLoad,
    TimetableRun,
)
from apps.faculty.services.planning.occupations import OccupationBoard
from apps.faculty.services.planning.rooms import pick_room, preferred_types_for
from apps.faculty.services.planning.weekly import (
    PlanningError,
    courses_for_promotion,
    ensure_assignments_for_promotion,
)

REPLACEABLE_STATUSES = ('draft', 'generated')
RHYTHM_MAX_WEEK = {
    'full': 5,
    'w1': 1,
    'w1_2': 2,
    'w1_3': 3,
}


def week_of_month(day: date) -> int:
    return ((day.day - 1) // 7) + 1


def rhythm_allows(rhythm: str, day: date) -> bool:
    return week_of_month(day) <= RHYTHM_MAX_WEEK.get(rhythm or 'full', 5)


def iter_eligible_dates(period, settings, holidays: set[date]):
    current = period.start_date
    active_days = set(settings.active_days or [0, 1, 2, 3, 4])
    while current <= period.end_date:
        if current.weekday() in active_days and current not in holidays and rhythm_allows(period.weekly_rhythm, current):
            yield current
        current += timedelta(days=1)


def build_slots(settings, slot_mode='both') -> list[tuple[time, time]]:
    duration = timedelta(minutes=int(settings.session_duration_minutes or 120))
    windows = []
    if slot_mode in ('morning', 'both'):
        windows.append((settings.morning_start, settings.morning_end))
    if slot_mode in ('afternoon', 'both'):
        windows.append((settings.afternoon_start, settings.afternoon_end))
    slots = []
    dummy = date(2000, 1, 1)
    for start, end in windows:
        cursor = datetime.combine(dummy, start)
        limit = datetime.combine(dummy, end)
        while cursor + duration <= limit:
            slots.append((cursor.time(), (cursor + duration).time()))
            cursor += duration
    return slots


def _holidays_for(period) -> set[date]:
    institution_id = period.academic_year.institution_id
    return set(
        Holiday.objects.filter(
            institution_id=institution_id,
            is_active=True,
            date__gte=period.start_date,
            date__lte=period.end_date,
        ).values_list('date', flat=True)
    )


def _effectif(load) -> int:
    if load.group_id:
        return load.group.headcount or load.group.max_students or 25
    return load.promotion.students.filter(status='active').count() or 30


def _staff_for(load) -> tuple:
    teacher = load.teacher
    supervisor = load.supervisor if load.session_kind == 'tp' else None
    if teacher is None:
        assignment = (
            CourseAssignment.objects.filter(
                course=load.course,
                promotion=load.promotion,
            ).select_related('teacher', 'supervisor').order_by('-is_primary').first()
        )
        if assignment:
            teacher = assignment.teacher
            if supervisor is None and load.session_kind == 'tp':
                supervisor = assignment.supervisor
    return teacher, supervisor


def ensure_teaching_loads(period, promotion, academic_year):
    """Crée les charges CM/TD/TP à partir de la maquette si elles n'existent pas encore."""
    ensure_assignments_for_promotion(promotion, academic_year, semester_number=promotion.current_semester)
    courses = courses_for_promotion(promotion, semester_number=promotion.current_semester)
    assignments = {
        row.course_id: row
        for row in CourseAssignment.objects.filter(promotion=promotion, academic_year=academic_year)
    }
    created = 0
    for course in courses:
        assignment = assignments.get(course.id)
        for kind, hours in (('cm', course.hours_cm), ('td', course.hours_td), ('tp', course.hours_tp)):
            if not hours:
                continue
            _, was_created = TeachingLoad.objects.get_or_create(
                period=period,
                course=course,
                promotion=promotion,
                group=None,
                session_kind=kind,
                defaults={
                    'hours_total': hours,
                    'teacher': assignment.teacher if assignment else None,
                    'supervisor': assignment.supervisor if assignment and kind == 'tp' else None,
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
    return created


class _Draft:
    """Séance pas encore persistée, compatible avec OccupationBoard."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def generate_for_period(
    *,
    period,
    promotion,
    academic_year=None,
    replace_existing=False,
    dry_run=False,
    mode='best_effort',
    actor=None,
    auto_create_loads=True,
):
    """Place des séances datées pour une promotion sur une période de formation."""
    from apps.faculty.services.planning.conflicts import detect_seance_conflicts

    academic_year = academic_year or period.academic_year
    settings = PlanningSettings.resolve(period)
    holidays = _holidays_for(period)
    dates = list(iter_eligible_dates(period, settings, holidays))
    if not dates:
        raise PlanningError(
            'Aucun jour ouvrable dans cette période (calendrier, jours fériés ou rythme).',
            'no_eligible_dates',
        )

    created_loads = 0
    if auto_create_loads:
        created_loads = ensure_teaching_loads(period, promotion, academic_year)

    loads = list(
        TeachingLoad.objects.filter(
            period=period, promotion=promotion, is_active=True,
        ).select_related('course', 'promotion', 'group', 'teacher__user', 'supervisor__user')
    )
    if not loads:
        raise PlanningError(
            'Aucune charge à planifier pour cette promotion sur cette période.',
            'no_teaching_loads',
        )

    run = None
    if not dry_run:
        run = TimetableRun.objects.create(
            period=period, promotion=promotion, actor=actor, mode=mode, status='running',
        )

    try:
        with transaction.atomic():
            result = _place_loads(
                period=period,
                promotion=promotion,
                loads=loads,
                settings=settings,
                dates=dates,
                replace_existing=replace_existing,
                dry_run=dry_run,
                mode=mode,
            )
            result['loads_created'] = created_loads
            result['eligible_dates'] = len(dates)
            result['holidays'] = len(holidays)
            if not dry_run:
                result['conflicts'] = detect_seance_conflicts(
                    Seance.objects.filter(period=period, promotion=promotion)
                )
            if run is not None:
                run.status = 'done'
                run.summary = {
                    'created': result['created'],
                    'failures': result['failures'],
                    'loads_created': created_loads,
                }
                run.finished_at = timezone.now()
                run.save(update_fields=['status', 'summary', 'finished_at'])
                result['run_id'] = str(run.id)
            return result
    except Exception:
        if run is not None:
            run.status = 'error'
            run.finished_at = timezone.now()
            run.save(update_fields=['status', 'finished_at'])
        raise


def _place_loads(*, period, promotion, loads, settings, dates, replace_existing, dry_run, mode):
    board = OccupationBoard()
    existing_qs = Seance.objects.filter(
        date__gte=period.start_date,
        date__lte=period.end_date,
    ).exclude(status__in=('cancelled', 'archived')).select_related('course', 'teacher', 'supervisor', 'room')

    if replace_existing and not dry_run:
        Seance.objects.filter(
            period=period,
            promotion=promotion,
            status__in=REPLACEABLE_STATUSES,
        ).update(
            status='cancelled',
            cancelled_reason='Remplacée par une nouvelle génération',
            is_active=False,
        )
        existing_qs = existing_qs.exclude(period=period, promotion=promotion, status='cancelled')
    elif replace_existing and dry_run:
        existing_qs = existing_qs.exclude(period=period, promotion=promotion, status__in=REPLACEABLE_STATUSES)

    board.load(existing_qs)

    weights = (
        settings.weight_capacity_gap,
        settings.weight_room_rotation,
        settings.weight_global_balance,
    )
    duration = int(settings.session_duration_minutes or 120)
    planned = []
    created_objs = []
    failures = []
    locked_rooms = {}

    loads = sorted(
        loads,
        key=lambda load: (
            {'tp': 3, 'td': 2, 'cm': 1}.get(load.session_kind, 0),
            load.hours_total,
        ),
        reverse=True,
    )

    for load in loads:
        remaining = int(load.hours_total) * 60
        teacher, supervisor = _staff_for(load)
        staff_ids = {tid for tid in (getattr(teacher, 'id', None), getattr(supervisor, 'id', None)) if tid}
        preferred = preferred_types_for(load.session_kind, load.preferred_room_type)
        slots = build_slots(settings, load.slot_mode)
        effectif = _effectif(load)
        lock_key = (load.group_id, load.promotion_id, load.course_id)
        placed_for_load = []

        while remaining >= duration:
            placed = _try_place(
                load=load,
                period=period,
                dates=dates,
                slots=slots,
                board=board,
                teacher=teacher,
                supervisor=supervisor,
                staff_ids=staff_ids,
                preferred=preferred,
                effectif=effectif,
                settings=settings,
                weights=weights,
                locked_rooms=locked_rooms,
                lock_key=lock_key,
                dry_run=dry_run,
                created_objs=created_objs,
                planned=planned,
            )
            if not placed:
                break
            remaining -= duration
            placed_for_load.append(placed)

        if remaining > 0 and settings.spread_remainder and placed_for_load and remaining >= 30:
            remaining = 0

        if remaining > 0:
            failure = {
                'course': load.course.code,
                'kind': load.session_kind,
                'remaining_minutes': remaining,
                'reason': (
                    f"Impossible de placer {remaining} minute(s) pour {load.course.code} "
                    f"({load.get_session_kind_display()}) : plus aucun créneau libre "
                    f"pour le professeur, le groupe ou les salles."
                ),
            }
            failures.append(failure)
            if mode == 'strict':
                raise PlanningError(failure['reason'], 'unplaced_hours')

    return {
        'period': period.label,
        'period_id': str(period.id),
        'promotion': promotion.name,
        'promotion_id': str(promotion.id),
        'created': len(planned),
        'failures': failures,
        'dry_run': dry_run,
        'slots': planned,
        'mode': mode,
    }


def _try_place(
    *, load, period, dates, slots, board, teacher, supervisor, staff_ids,
    preferred, effectif, settings, weights, locked_rooms, lock_key, dry_run, created_objs, planned,
):
    ordered_dates = sorted(
        dates,
        key=lambda day: board.day_count(day, load.promotion_id, load.group_id),
    )
    locked = locked_rooms.get(lock_key) if settings.lock_room_per_group else None

    for day in ordered_dates:
        if board.day_count(day, load.promotion_id, load.group_id) >= settings.max_sessions_per_day:
            continue
        for start, end in slots:
            if not board.audience_free(day, load.promotion_id, load.group_id, start, end):
                continue
            if not board.staff_free(day, staff_ids, start, end):
                continue
            room = pick_room(
                day=day,
                start=start,
                end=end,
                effectif=effectif,
                tolerance=settings.capacity_tolerance,
                preferred_types=preferred,
                board=board,
                course_id=load.course_id,
                weights=weights,
                locked_room=locked,
            )
            draft = _Draft(
                period_id=period.id,
                teaching_load_id=load.id,
                course_id=load.course_id,
                promotion_id=load.promotion_id,
                group_id=load.group_id,
                teacher_id=getattr(teacher, 'id', None),
                supervisor_id=getattr(supervisor, 'id', None),
                room_id=getattr(room, 'id', None),
                session_kind=load.session_kind,
                date=day,
                start_time=start,
                end_time=end,
                status='generated',
                course=load.course,
                promotion=load.promotion,
                group=load.group,
                teacher=teacher,
                supervisor=supervisor,
                room=room,
            )
            payload = {
                'course_code': load.course.code,
                'course_name': load.course.name,
                'kind': load.session_kind,
                'date': day.isoformat(),
                'start_time': start.strftime('%H:%M'),
                'end_time': end.strftime('%H:%M'),
                'room_id': str(room.id) if room else None,
                'room_code': room.code if room else None,
                'teacher': teacher.user.get_full_name() if teacher else None,
                'supervisor': supervisor.user.get_full_name() if supervisor else None,
                'group': load.group.name if load.group_id else None,
            }
            if dry_run:
                board.reserve(draft)
                if room and settings.lock_room_per_group:
                    locked_rooms[lock_key] = room
                planned.append(payload)
                return draft

            seance = Seance(
                period=period,
                teaching_load=load,
                course=load.course,
                promotion=load.promotion,
                group=load.group,
                teacher=teacher,
                supervisor=supervisor,
                room=room,
                session_kind=load.session_kind,
                date=day,
                start_time=start,
                end_time=end,
                status='generated',
            )
            seance.save()
            board.reserve(seance)
            if room and settings.lock_room_per_group:
                locked_rooms[lock_key] = room
            payload['id'] = str(seance.id)
            planned.append(payload)
            created_objs.append(seance)
            return seance
    return None


def expand_schedules_for_period(*, period, promotion, replace_existing=False, dry_run=False, actor=None):
    """Matérialise les créneaux hebdomadaires en séances datées sur la période."""
    settings = PlanningSettings.resolve(period)
    holidays = _holidays_for(period)
    dates = list(iter_eligible_dates(period, settings, holidays))
    schedules = list(
        Schedule.objects.filter(
            is_active=True,
            assignment__promotion=promotion,
            assignment__academic_year=period.academic_year,
        ).select_related(
            'assignment__course', 'assignment__teacher__user',
            'assignment__supervisor__user', 'assignment__promotion', 'room', 'supervisor',
        )
    )
    if not schedules:
        raise PlanningError(
            'Aucun créneau hebdomadaire à étendre pour cette promotion.',
            'no_schedules',
        )

    created = []
    skipped = 0
    with transaction.atomic():
        if replace_existing and not dry_run:
            Seance.objects.filter(
                period=period, promotion=promotion, schedule__isnull=False,
                status__in=REPLACEABLE_STATUSES,
            ).update(status='cancelled', cancelled_reason='Remplacée par une extension de gabarit')

        for schedule in schedules:
            assignment = schedule.assignment
            for day in dates:
                if day.weekday() != schedule.day_of_week:
                    continue
                if dry_run:
                    created.append({
                        'schedule_id': str(schedule.id),
                        'date': day.isoformat(),
                        'course_code': assignment.course.code,
                    })
                    continue
                seance, was_created = Seance.objects.get_or_create(
                    schedule=schedule,
                    date=day,
                    defaults={
                        'period': period,
                        'course': assignment.course,
                        'promotion': assignment.promotion,
                        'teacher': assignment.teacher,
                        'supervisor': schedule.resolved_supervisor(),
                        'room': schedule.room,
                        'session_kind': schedule.session_kind,
                        'start_time': schedule.start_time,
                        'end_time': schedule.end_time,
                        'status': 'generated',
                    },
                )
                if was_created:
                    created.append(seance)
                else:
                    skipped += 1

    return {
        'period': period.label,
        'promotion': promotion.name,
        'created': len(created),
        'skipped': skipped,
        'dry_run': dry_run,
        'schedules': len(schedules),
    }


def publish_seances(queryset, *, actor=None):
    """Passe les séances validées ou générées à l'état publié, après contrôle des conflits."""
    from apps.faculty.services.planning.conflicts import detect_seance_conflicts

    seances = list(queryset.exclude(status__in=('cancelled', 'archived', 'done')))
    if not seances:
        return {'published': 0, 'conflicts': []}
    conflicts = [row for row in detect_seance_conflicts(queryset) if row['severity'] == 'error']
    if conflicts:
        first = conflicts[0]['message']
        raise PlanningError(first, 'conflicts')
    now = timezone.now()
    ids = [row.id for row in seances]
    updated = Seance.objects.filter(id__in=ids).exclude(status='published').update(
        status='published', published_at=now, is_active=True,
    )
    return {'published': updated, 'conflicts': []}
