"""Évaluation d'une présence : retard, durée bornée, partiel, auto-absence.

Règles par défaut (surchargeables via PlanningSettings) :
- retard si l'entrée a plus de 15 minutes de retard sur le début prévu
- présence partielle si la durée effective est sous 75 % du créneau
- auto-absence 60 minutes après la fin prévue, sans entrée
La durée est toujours bornée au créneau planifié (entrée avant le début
et sortie après la fin ne comptent pas).
"""
from datetime import datetime, timedelta

from django.utils import timezone

DEFAULT_LATE_AFTER_MINUTES = 15
DEFAULT_PARTIAL_UNDER_PERCENT = 75
DEFAULT_AUTO_ABSENT_AFTER_MINUTES = 60


def resolve_attendance_rules(period=None):
    from apps.faculty.models import PlanningSettings
    settings = PlanningSettings.resolve(period)
    return {
        'late_after_minutes': getattr(settings, 'late_after_minutes', None) or DEFAULT_LATE_AFTER_MINUTES,
        'partial_under_percent': getattr(settings, 'partial_under_percent', None) or DEFAULT_PARTIAL_UNDER_PERCENT,
        'auto_absent_after_minutes': getattr(settings, 'auto_absent_after_minutes', None) or DEFAULT_AUTO_ABSENT_AFTER_MINUTES,
    }


def planned_window(session_date, start_time, end_time, tz=None):
    tz = tz or timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(session_date, start_time), tz)
    end = timezone.make_aware(datetime.combine(session_date, end_time), tz)
    return start, end


def planned_minutes(planned_start, planned_end):
    return max(0, int((planned_end - planned_start).total_seconds() // 60))


def clamp_interval(checked_in_at, checked_out_at, planned_start, planned_end):
    """Borne l'intervalle badgeé au créneau prévu."""
    if checked_in_at is None or checked_out_at is None:
        return None, None, 0
    effective_in = max(checked_in_at, planned_start)
    effective_out = min(checked_out_at, planned_end)
    if effective_out < effective_in:
        effective_out = effective_in
    duration = int((effective_out - effective_in).total_seconds() // 60)
    duration = min(duration, planned_minutes(planned_start, planned_end))
    return effective_in, effective_out, duration


def late_minutes(checked_in_at, planned_start):
    if not checked_in_at or checked_in_at <= planned_start:
        return 0
    return int((checked_in_at - planned_start).total_seconds() // 60)


def evaluate_presence(
    *,
    checked_in_at,
    checked_out_at,
    planned_start,
    planned_end,
    late_after_minutes=DEFAULT_LATE_AFTER_MINUTES,
    partial_under_percent=DEFAULT_PARTIAL_UNDER_PERCENT,
):
    """Retourne status, late_minutes, duration_minutes."""
    delay = late_minutes(checked_in_at, planned_start)
    if checked_in_at is None:
        return {
            'status': 'absent',
            'late_minutes': 0,
            'duration_minutes': 0,
        }
    if checked_out_at is None:
        return {
            'status': 'late' if delay > late_after_minutes else 'present',
            'late_minutes': delay,
            'duration_minutes': None,
        }
    _in, _out, duration = clamp_interval(
        checked_in_at, checked_out_at, planned_start, planned_end,
    )
    planned = planned_minutes(planned_start, planned_end)
    threshold = planned * partial_under_percent / 100
    if planned and duration < threshold:
        status = 'partial'
    elif delay > late_after_minutes:
        status = 'late'
    else:
        status = 'present'
    return {
        'status': status,
        'late_minutes': delay,
        'duration_minutes': duration,
    }


def auto_absent_deadline(planned_end, auto_absent_after_minutes=DEFAULT_AUTO_ABSENT_AFTER_MINUTES):
    return planned_end + timedelta(minutes=auto_absent_after_minutes)


def should_auto_absent(*, checked_in_at, now, planned_end, auto_absent_after_minutes=DEFAULT_AUTO_ABSENT_AFTER_MINUTES):
    if checked_in_at is not None:
        return False
    return now >= auto_absent_deadline(planned_end, auto_absent_after_minutes)


def apply_evaluation(attendance, *, planned_start, planned_end, rules=None, now=None):
    """Écrit status / durée / retard sur une ligne Attendance ou StaffAttendance."""
    rules = rules or resolve_attendance_rules()
    result = evaluate_presence(
        checked_in_at=attendance.checked_in_at,
        checked_out_at=attendance.checked_out_at,
        planned_start=planned_start,
        planned_end=planned_end,
        late_after_minutes=rules['late_after_minutes'],
        partial_under_percent=rules['partial_under_percent'],
    )
    if attendance.status != 'excused':
        attendance.status = result['status']
    attendance.late_minutes = result['late_minutes']
    attendance.duration_minutes = result['duration_minutes']
    return result


def close_overdue_attendances(*, schedule, session_date, now=None, seance=None):
    """Clôt les présences ouvertes et marque les absents après le délai d'auto-absence."""
    from apps.faculty.models import Attendance, StaffAttendance

    now = now or timezone.localtime()
    start, end = planned_window(session_date, schedule.start_time, schedule.end_time)
    period = getattr(seance, 'period', None) if seance is not None else None
    rules = resolve_attendance_rules(period)
    deadline = auto_absent_deadline(end, rules['auto_absent_after_minutes'])
    if now < deadline:
        return {'closed': 0, 'absents': 0}

    closed = 0
    absents = 0
    for model in (Attendance, StaffAttendance):
        qs = model.objects.filter(schedule=schedule, date=session_date)
        for row in qs:
            if row.status == 'excused':
                continue
            if row.checked_in_at and not row.checked_out_at:
                previous = row.status
                row.checked_out_at = end
                apply_evaluation(row, planned_start=start, planned_end=end, rules=rules, now=now)
                row.save()
                closed += 1
                _record_system_event(row, kind='check_out', previous=previous, seance=seance)
            elif not row.checked_in_at and row.status != 'absent':
                previous = row.status
                row.status = 'absent'
                row.duration_minutes = 0
                row.late_minutes = 0
                row.save(update_fields=['status', 'duration_minutes', 'late_minutes', 'updated_at'])
                absents += 1
                _record_system_event(row, kind='auto_absent', previous=previous, seance=seance)
            elif not row.checked_in_at and row.status == 'absent':
                absents += 1
    return {'closed': closed, 'absents': absents}


def close_overdue_for_date(session_date, now=None):
    """Clôture les présences ouvertes d’un jour (sessions + séances datées)."""
    from apps.faculty.models import AttendanceSession, Seance

    now = now or timezone.localtime()
    totals = {'closed': 0, 'absents': 0, 'sessions': 0}
    seen = set()

    sessions = AttendanceSession.objects.filter(session_date=session_date).select_related('schedule')
    for session in sessions:
        key = (str(session.schedule_id), session_date.isoformat())
        if key in seen:
            continue
        seen.add(key)
        seance = Seance.objects.filter(schedule=session.schedule, date=session_date).first()
        result = close_overdue_attendances(
            schedule=session.schedule, session_date=session_date, now=now, seance=seance,
        )
        totals['closed'] += result['closed']
        totals['absents'] += result['absents']
        totals['sessions'] += 1

    for seance in Seance.objects.filter(
        date=session_date, status__in=('published', 'validated', 'in_progress', 'done'),
    ).select_related('schedule'):
        if not seance.schedule_id:
            continue
        key = (str(seance.schedule_id), session_date.isoformat())
        if key in seen:
            continue
        seen.add(key)
        result = close_overdue_attendances(
            schedule=seance.schedule, session_date=session_date, now=now, seance=seance,
        )
        totals['closed'] += result['closed']
        totals['absents'] += result['absents']
        totals['sessions'] += 1
    return totals


def _record_system_event(row, *, kind, previous, seance=None):
    from apps.faculty.models import Attendance
    from apps.faculty.services.badge_security import record_badge_event

    kwargs = {
        'kind': kind,
        'source': 'system',
        'seance': seance or getattr(row, 'seance', None),
        'previous_status': previous,
        'new_status': row.status,
        'reason': 'Clôture automatique',
    }
    if isinstance(row, Attendance):
        kwargs['attendance'] = row
    else:
        kwargs['staff_attendance'] = row
    record_badge_event(**kwargs)
