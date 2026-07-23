"""Services campus INJS : auto-affectation salles / étudiants (extensibles via metadata)."""
from __future__ import annotations

from datetime import datetime, time as time_cls

from django.utils import timezone

from apps.faculty.models import Room, Schedule, Attendance, RoomReservation


class CampusOpsError(Exception):
    def __init__(self, message, code='campus_ops_error'):
        super().__init__(message)
        self.code = code


def _as_time(value):
    if value is None:
        return None
    if isinstance(value, time_cls):
        return value
    if isinstance(value, str):
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    return value


def _equipment_match(room_equipment, required):
    if not required:
        return True
    tags = {str(t).lower() for t in (room_equipment or [])}
    return all(str(req).lower() in tags for req in required)


def find_available_rooms(
    *,
    min_capacity=1,
    day_of_week=None,
    start_time=None,
    end_time=None,
    required_equipment=None,
    room_type=None,
    building=None,
    exclude_schedule_id=None,
):
    """Retourne une liste de salles libres, filtrées capacité / équipements / créneau."""
    qs = Room.objects.filter(is_active=True, status='available')
    if min_capacity:
        qs = qs.filter(capacity__gte=min_capacity)
    if room_type:
        qs = qs.filter(room_type=room_type)
    if building:
        qs = qs.filter(building=building)

    start_time = _as_time(start_time)
    end_time = _as_time(end_time)

    if day_of_week is not None and start_time and end_time:
        busy = Schedule.objects.filter(
            is_active=True,
            day_of_week=day_of_week,
            start_time__lt=end_time,
            end_time__gt=start_time,
            room__isnull=False,
        )
        if exclude_schedule_id:
            busy = busy.exclude(pk=exclude_schedule_id)
        qs = qs.exclude(id__in=busy.values_list('room_id', flat=True))

        approved = RoomReservation.objects.filter(status='approved')
        conflicting_ids = []
        for res in approved.select_related('room'):
            if res.start_datetime.weekday() != int(day_of_week):
                continue
            r_start = res.start_datetime.time()
            r_end = res.end_datetime.time()
            if r_start < end_time and r_end > start_time:
                conflicting_ids.append(res.room_id)
        if conflicting_ids:
            qs = qs.exclude(id__in=conflicting_ids)

    rooms = list(qs.order_by('capacity', 'code'))
    required = required_equipment or []
    if required:
        rooms = [r for r in rooms if _equipment_match(r.equipment, required)]
    return rooms


def auto_assign_room(schedule, required_equipment=None, room_type=None):
    """Affecte automatiquement la plus petite salle adaptée au créneau."""
    if not schedule:
        raise CampusOpsError('Créneau introuvable', 'schedule_not_found')

    promotion = schedule.assignment.promotion
    min_capacity = promotion.students.filter(status='active').count()
    min_capacity = max(min_capacity, 1)

    candidates = find_available_rooms(
        min_capacity=min_capacity,
        day_of_week=schedule.day_of_week,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        required_equipment=required_equipment,
        room_type=room_type,
        exclude_schedule_id=schedule.id,
    )
    if not candidates:
        raise CampusOpsError(
            f'Aucune salle libre (capacité ≥ {min_capacity}'
            + (f', équipements {required_equipment}' if required_equipment else '')
            + ').',
            'no_room',
        )

    room = candidates[0]
    schedule.room = room
    schedule.save(update_fields=['room', 'updated_at'])
    return room


def _promotion_students(promotion):
    from apps.students.models import Student
    return Student.objects.filter(promotion=promotion, status='active').select_related('user')


def seed_schedule_roster(schedule, session_date, recorded_by=None, default_status='absent'):
    """Affecte automatiquement tous les étudiants actifs de la promotion au créneau+date."""
    if not schedule:
        raise CampusOpsError('Créneau introuvable', 'schedule_not_found')
    promotion = schedule.assignment.promotion
    students = _promotion_students(promotion)
    created = 0
    for student in students:
        _, was_created = Attendance.objects.get_or_create(
            student=student,
            schedule=schedule,
            date=session_date,
            defaults={
                'status': default_status,
                'recorded_by': recorded_by,
            },
        )
        if was_created:
            created += 1
    return {
        'promotion': promotion.name,
        'students_total': students.count(),
        'attendances_created': created,
        'schedule_id': str(schedule.id),
        'date': session_date.isoformat(),
    }


def seed_session_roster(session, recorded_by=None, default_status='absent'):
    """Affecte automatiquement les étudiants de la promotion du créneau à la séance."""
    if not session:
        raise CampusOpsError('Séance introuvable', 'session_not_found')
    result = seed_schedule_roster(
        session.schedule,
        session.session_date,
        recorded_by=recorded_by,
        default_status=default_status,
    )
    result['session_id'] = str(session.id)
    return result


def list_schedule_roster(schedule, session_date):
    """Liste les étudiants affectés + disponibles (promotion) pour un créneau+date."""
    if not schedule:
        raise CampusOpsError('Créneau introuvable', 'schedule_not_found')
    promotion = schedule.assignment.promotion
    promo_students = list(_promotion_students(promotion))
    attendances = list(
        Attendance.objects.filter(schedule=schedule, date=session_date)
        .select_related('student__user')
        .order_by('student__matricule')
    )
    assigned_ids = {a.student_id for a in attendances}
    assigned = [
        {
            'attendance_id': str(a.id),
            'student_id': str(a.student_id),
            'matricule': a.student.matricule,
            'name': a.student.user.get_full_name(),
            'gender': a.student.gender or '',
            'status': a.status,
            'status_display': a.get_status_display(),
            'status_label': (
                'Présente' if a.status == 'present' and a.student.gender == 'F'
                else 'Présent' if a.status == 'present'
                else 'En retard' if a.status == 'late'
                else 'Absente' if a.status == 'absent' and a.student.gender == 'F'
                else 'Absent' if a.status == 'absent'
                else a.get_status_display()
            ),
        }
        for a in attendances
    ]
    available = [
        {
            'student_id': str(s.id),
            'matricule': s.matricule,
            'name': s.user.get_full_name(),
        }
        for s in promo_students
        if s.id not in assigned_ids
    ]
    return {
        'schedule_id': str(schedule.id),
        'date': session_date.isoformat(),
        'promotion': promotion.name,
        'promotion_id': str(promotion.id),
        'effectif_promotion': len(promo_students),
        'roster_count': len(assigned),
        'assigned': assigned,
        'available': available,
    }


def add_students_to_roster(schedule, session_date, student_ids, recorded_by=None, default_status='absent'):
    """Ajout manuel d'étudiants au roster d'un créneau+date."""
    if not schedule:
        raise CampusOpsError('Créneau introuvable', 'schedule_not_found')
    if not student_ids:
        raise CampusOpsError('Aucun étudiant sélectionné', 'no_students')

    from apps.students.models import Student

    promotion = schedule.assignment.promotion
    students = Student.objects.filter(
        id__in=student_ids,
        promotion=promotion,
        status='active',
    )
    found = {str(s.id): s for s in students}
    missing = [sid for sid in student_ids if str(sid) not in found]
    if missing:
        raise CampusOpsError(
            'Certains étudiants ne font pas partie de la promotion du créneau.',
            'student_not_in_promotion',
        )

    created = 0
    for student in students:
        _, was_created = Attendance.objects.get_or_create(
            student=student,
            schedule=schedule,
            date=session_date,
            defaults={'status': default_status, 'recorded_by': recorded_by},
        )
        if was_created:
            created += 1
    return {
        'added': created,
        'requested': len(student_ids),
        **list_schedule_roster(schedule, session_date),
    }


def remove_students_from_roster(schedule, session_date, student_ids=None, attendance_ids=None):
    """Retrait manuel d'étudiants du roster."""
    if not schedule:
        raise CampusOpsError('Créneau introuvable', 'schedule_not_found')
    qs = Attendance.objects.filter(schedule=schedule, date=session_date)
    if attendance_ids:
        qs = qs.filter(id__in=attendance_ids)
    elif student_ids:
        qs = qs.filter(student_id__in=student_ids)
    else:
        raise CampusOpsError('Indiquez student_ids ou attendance_ids', 'no_ids')
    deleted, _ = qs.delete()
    return {
        'removed': deleted,
        **list_schedule_roster(schedule, session_date),
    }


def next_occurrence(day_of_week, from_date):
    """Prochaine date (incluse) correspondant au jour Django 0=Lun…5=Sam."""
    from datetime import timedelta
    delta = (day_of_week - from_date.weekday()) % 7
    return from_date + timedelta(days=delta)


def seed_rosters_for_schedules(schedules, *, from_date, weeks=1, recorded_by=None, default_status='absent'):
    """
    Affectation auto des étudiants de la promo pour les N prochaines occurrences
    de chaque créneau (utilisé après génération EDT).
    """
    from datetime import timedelta
    weeks = max(1, min(int(weeks or 1), 8))
    summary = []
    total_created = 0
    for schedule in schedules:
        for w in range(weeks):
            base = from_date + timedelta(days=7 * w)
            session_date = next_occurrence(schedule.day_of_week, base)
            result = seed_schedule_roster(
                schedule,
                session_date,
                recorded_by=recorded_by,
                default_status=default_status,
            )
            total_created += result['attendances_created']
            summary.append(result)
    return {
        'schedules': len(list(schedules)),
        'weeks': weeks,
        'from_date': from_date.isoformat(),
        'attendances_created': total_created,
        'details': summary,
    }


def sync_room_status_from_tickets(room):
    """Si ticket ouvert → maintenance ; sinon disponible."""
    open_statuses = ('open', 'in_progress')
    has_open = room.maintenance_tickets.filter(status__in=open_statuses).exists()
    if has_open and room.status != 'maintenance':
        room.status = 'maintenance'
        room.save(update_fields=['status', 'updated_at'])
    elif not has_open and room.status == 'maintenance':
        room.status = 'available'
        room.save(update_fields=['status', 'updated_at'])
    return room


def approve_reservation(reservation, actor=None):
    """Approuve une réservation si pas de conflit EDT / autre réservation."""
    room = reservation.room
    start = reservation.start_datetime
    end = reservation.end_datetime
    if end <= start:
        raise CampusOpsError('La fin doit être après le début', 'invalid_range')

    day = start.weekday()
    if day > 5:
        raise CampusOpsError('Réservation le dimanche non gérée dans l’EDT hebdo', 'sunday')

    conflict_sched = Schedule.objects.filter(
        room=room,
        is_active=True,
        day_of_week=day,
        start_time__lt=end.time(),
        end_time__gt=start.time(),
    ).exists()
    if conflict_sched:
        raise CampusOpsError('Conflit avec un créneau EDT', 'schedule_conflict')

    conflict_res = RoomReservation.objects.filter(
        room=room,
        status='approved',
        start_datetime__lt=end,
        end_datetime__gt=start,
    ).exclude(pk=reservation.pk).exists()
    if conflict_res:
        raise CampusOpsError('Conflit avec une autre réservation', 'reservation_conflict')

    if reservation.attendees_count and room.capacity < reservation.attendees_count:
        raise CampusOpsError(
            f'Capacité insuffisante ({room.capacity} < {reservation.attendees_count})',
            'capacity',
        )

    if not _equipment_match(room.equipment, reservation.required_equipment):
        raise CampusOpsError('Équipements requis absents de la salle', 'equipment')

    reservation.status = 'approved'
    reservation.metadata = {
        **(reservation.metadata or {}),
        'approved_at': timezone.now().isoformat(),
        'approved_by': getattr(actor, 'email', None),
    }
    reservation.save()
    return reservation
