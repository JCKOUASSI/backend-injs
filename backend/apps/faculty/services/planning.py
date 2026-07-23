"""
Moteur d'emploi du temps INJS — inspiré du PlanningService EMPCPFAE,
adapté au LMD (promotions, UE/ECUE, salles sportives, équipements).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import time, timedelta, datetime, date

from django.db.models import Count

from apps.faculty.models import Schedule, CourseAssignment, Room, RoomReservation
from apps.faculty.services.campus_ops import find_available_rooms, _equipment_match


# Créneaux types INJS (2h) — matin / après-midi
DEFAULT_SLOTS = [
    (time(8, 0), time(10, 0)),
    (time(10, 0), time(12, 0)),
    (time(14, 0), time(16, 0)),
    (time(16, 0), time(18, 0)),
]

DAYS = list(range(6))  # Lun–Sam


class PlanningError(Exception):
    def __init__(self, message, code='planning_error'):
        super().__init__(message)
        self.code = code


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and a_end > b_start


def _session_count_from_hours(hours, session_hours=2):
    """Convertit un volume horaire en nombre de créneaux hebdomadaires (min 1 si hours>0)."""
    if not hours or hours <= 0:
        return 0
    return max(1, int((hours + session_hours - 1) // session_hours))


def _preferred_room_types(kind):
    if kind == 'cm':
        return ['amphitheater', 'classroom', 'conference']
    if kind == 'td':
        return ['td', 'classroom', 'seminar']
    if kind == 'tp':
        return ['tp', 'lab', 'gym', 'sport', 'medical', 'computer']
    return ['classroom']


def detect_conflicts(queryset=None):
    """
    Détecte les conflits EDT (salle, enseignant, promotion) — style EMPCPFAE.
    Retourne une liste de dicts {type, severity, message, schedule_ids, ...}.
    """
    qs = queryset if queryset is not None else Schedule.objects.filter(is_active=True)
    qs = qs.select_related(
        'assignment__teacher__user',
        'assignment__course',
        'assignment__promotion',
        'room',
    )
    schedules = list(qs)
    conflicts = []

    # Index par jour
    by_day = defaultdict(list)
    for s in schedules:
        by_day[s.day_of_week].append(s)

    for day, items in by_day.items():
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                if not _overlaps(a.start_time, a.end_time, b.start_time, b.end_time):
                    continue

                # Conflit salle
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

                # Conflit enseignant
                if a.assignment.teacher_id == b.assignment.teacher_id:
                    teacher_name = a.assignment.teacher.user.get_full_name()
                    conflicts.append({
                        'type': 'teacher',
                        'severity': 'error',
                        'message': (
                            f"Enseignant {teacher_name} en double le {a.get_day_of_week_display()} "
                            f"{a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')}"
                        ),
                        'schedule_ids': [str(a.id), str(b.id)],
                        'day_of_week': day,
                        'resource': teacher_name,
                    })

                # Conflit promotion (même cohort au même moment)
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

    # Salles en maintenance utilisées
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

    # Capacité insuffisante
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
    """Score EMPCPFAE-like : écart capacité + type préféré + équilibrage usage."""
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
        # fallback : capacité assouplie
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


def _slot_free_for_teacher(day, start, end, teacher_id, existing):
    for s in existing:
        if s.day_of_week != day:
            continue
        if s.assignment.teacher_id != teacher_id:
            continue
        if _overlaps(start, end, s.start_time, s.end_time):
            return False
    return True


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
):
    """
    Génère un EDT hebdomadaire pour une promotion (mode best_effort EMPCPFAE).
    S'appuie sur les CourseAssignment existants + volumes CM/TD/TP des ECUE.
    Option auto_seed_roster : affecte les étudiants de la promo aux prochaines occurrences.
    """
    from datetime import date as date_cls
    from django.utils import timezone
    from apps.faculty.services.campus_ops import seed_rosters_for_schedules

    assignments = list(
        CourseAssignment.objects.filter(
            promotion=promotion,
            academic_year=academic_year,
        ).select_related('course', 'teacher__user', 'promotion')
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
        ).select_related('assignment', 'room')
    )

    if replace_existing and not dry_run:
        for s in existing:
            s.is_active = False
            s.save(update_fields=['is_active', 'updated_at'])
        existing = []

    effectif = promotion.students.filter(status='active').count() or 30
    usage_counter = defaultdict(int)
    for s in existing:
        if s.room_id:
            usage_counter[s.room_id] += 1

    # Charge par jour (promotion)
    load_per_day = defaultdict(int)
    for s in existing:
        load_per_day[s.day_of_week] += 1

    planned = []
    failures = []
    created_objs = []

    # Ordre difficulté : plus d'heures TP d'abord (salles rares)
    def difficulty(a):
        c = a.course
        return (c.hours_tp or 0) * 3 + (c.hours_td or 0) * 2 + (c.hours_cm or 0)

    assignments.sort(key=difficulty, reverse=True)

    for assignment in assignments:
        course = assignment.course
        needs = [
            ('cm', _session_count_from_hours(course.hours_cm)),
            ('td', _session_count_from_hours(course.hours_td)),
            ('tp', _session_count_from_hours(course.hours_tp)),
        ]
        # Au moins 1 créneau si le cours existe sans heures renseignées
        if sum(n for _, n in needs) == 0:
            needs = [('cm', 1)]

        for kind, count in needs:
            preferred = _preferred_room_types(kind)
            for _ in range(count):
                placed = False
                # Parcourir jours les moins chargés
                days_ordered = sorted(DAYS, key=lambda d: load_per_day[d])
                for day in days_ordered:
                    if load_per_day[day] >= max_sessions_per_day:
                        continue
                    for start, end in DEFAULT_SLOTS:
                        if not _slot_free_for_promotion(day, start, end, promotion.id, existing + created_objs):
                            continue
                        if not _slot_free_for_teacher(day, start, end, assignment.teacher_id, existing + created_objs):
                            continue
                        room = _pick_room(day, start, end, effectif, preferred, usage_counter)
                        # Vérifier aussi conflits avec créneaux déjà créés dans ce run
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
                        'reason': 'Aucun créneau libre (enseignant / promotion / salles)',
                    })

    roster_result = None
    if auto_seed_roster and not dry_run and created_objs:
        seed_date = seed_from_date or timezone.localdate()
        if isinstance(seed_date, str):
            seed_date = date_cls.fromisoformat(seed_date)
        roster_result = seed_rosters_for_schedules(
            created_objs,
            from_date=seed_date,
            weeks=seed_weeks,
            recorded_by=recorded_by,
            default_status='absent',
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
        'academic_year': academic_year.label,
        'assignments': len(assignments),
        'created': len(planned),
        'failures': failures,
        'conflicts': conflicts,
        'dry_run': dry_run,
        'slots': planned,
        'effectif_promotion': promotion.students.filter(status='active').count(),
        'roster': roster_result,
    }


def timetable_grid(schedules):
    """Structure grille hebdo pour le frontend (jours × créneaux)."""
    slots = []
    for s in schedules:
        effectif = s.assignment.promotion.students.filter(status='active').count()
        slots.append({
            'id': str(s.id),
            'day_of_week': s.day_of_week,
            'day_display': s.get_day_of_week_display(),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'course_name': s.assignment.course.name,
            'course_code': s.assignment.course.code,
            'teacher_name': s.assignment.teacher.user.get_full_name(),
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
