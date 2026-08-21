"""Détection des conflits sur les séances datées."""
from __future__ import annotations

from collections import defaultdict

from apps.faculty.models import Seance
from apps.faculty.services.planning.occupations import overlaps


def detect_seance_conflicts(queryset=None):
    """Retourne les collisions salle / enseignant / encadrant / groupe / promotion.

    Les séances annulées ou archivées sont ignorées. Le message est formulé pour
    l'utilisateur final, pas pour le journal technique.
    """
    qs = queryset if queryset is not None else Seance.objects.all()
    qs = qs.exclude(status__in=('cancelled', 'archived')).select_related(
        'course', 'promotion', 'group', 'teacher__user', 'supervisor__user', 'room', 'period',
    )
    seances = list(qs)
    conflicts = []
    by_day = defaultdict(list)
    for seance in seances:
        by_day[seance.date].append(seance)

    for day, items in by_day.items():
        for index, first in enumerate(items):
            for second in items[index + 1:]:
                if not overlaps(first.start_time, first.end_time, second.start_time, second.end_time):
                    continue
                slot = (
                    f"le {day:%d/%m/%Y} de {first.start_time:%H:%M} à {first.end_time:%H:%M}"
                )
                ids = [str(first.id), str(second.id)]

                if first.room_id and first.room_id == second.room_id:
                    conflicts.append({
                        'type': 'room',
                        'severity': 'error',
                        'message': (
                            f"Impossible de placer deux séances dans la salle {first.room.code} {slot} "
                            f"({first.course.code} et {second.course.code})."
                        ),
                        'seance_ids': ids,
                        'date': day.isoformat(),
                        'resource': first.room.code,
                    })

                staff_overlap = first.staff_ids() & second.staff_ids()
                if staff_overlap:
                    if first.teacher_id and first.teacher_id == second.teacher_id:
                        name = first.teacher.user.get_full_name() if first.teacher_id else 'enseignant'
                        conflicts.append({
                            'type': 'teacher',
                            'severity': 'error',
                            'message': (
                                f"Impossible de publier : le professeur {name} est déjà affecté "
                                f"à une séance {slot}."
                            ),
                            'seance_ids': ids,
                            'date': day.isoformat(),
                            'resource': name,
                        })
                    else:
                        supervisor = first.resolved_supervisor() or second.resolved_supervisor()
                        name = supervisor.user.get_full_name() if supervisor else 'encadrant'
                        conflicts.append({
                            'type': 'supervisor',
                            'severity': 'error',
                            'message': (
                                f"L'encadrant {name} est déjà affecté à une autre séance {slot}."
                            ),
                            'seance_ids': ids,
                            'date': day.isoformat(),
                            'resource': name,
                        })

                if first.promotion_id == second.promotion_id:
                    same_group = first.group_id and first.group_id == second.group_id
                    promo_wide = not first.group_id or not second.group_id
                    if same_group or promo_wide:
                        if first.group_id and first.group_id == second.group_id:
                            label = first.group.name
                            kind = 'group'
                        else:
                            label = first.promotion.name
                            kind = 'promotion'
                        conflicts.append({
                            'type': kind,
                            'severity': 'error',
                            'message': (
                                f"{label} a déjà une séance {slot} "
                                f"({first.course.code} et {second.course.code})."
                            ),
                            'seance_ids': ids,
                            'date': day.isoformat(),
                            'resource': label,
                        })

                if first.course_id == second.course_id and first.group_id == second.group_id:
                    conflicts.append({
                        'type': 'ecue',
                        'severity': 'warning',
                        'message': (
                            f"L'ECUE {first.course.code} est programmé deux fois {slot} "
                            f"pour le même public."
                        ),
                        'seance_ids': ids,
                        'date': day.isoformat(),
                        'resource': first.course.code,
                    })

    for seance in seances:
        if seance.period_id and seance.date and not seance.period.covers(seance.date):
            conflicts.append({
                'type': 'period',
                'severity': 'error',
                'message': (
                    f"La séance {seance.course.code} du {seance.date:%d/%m/%Y} "
                    f"est hors de la période « {seance.period.label} »."
                ),
                'seance_ids': [str(seance.id)],
                'date': seance.date.isoformat(),
                'resource': seance.period.label,
            })
        if seance.room_id and seance.room.status == 'maintenance':
            conflicts.append({
                'type': 'maintenance',
                'severity': 'warning',
                'message': (
                    f"La salle {seance.room.code} est en maintenance "
                    f"({seance.course.code} le {seance.date:%d/%m/%Y})."
                ),
                'seance_ids': [str(seance.id)],
                'date': seance.date.isoformat(),
                'resource': seance.room.code,
            })

    return conflicts
