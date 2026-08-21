"""Choix et scoring des salles pour une séance datée."""
from __future__ import annotations

from apps.faculty.models import Room

PREFERRED_TYPES = {
    'cm': ['amphitheater', 'classroom', 'conference'],
    'td': ['td', 'classroom', 'seminar'],
    'tp': ['tp', 'lab', 'gym', 'sport', 'medical', 'computer'],
}


def preferred_types_for(kind: str, override: str = '') -> list[str]:
    if override:
        return [override]
    return PREFERRED_TYPES.get(kind, ['classroom'])


def score_room(room, effectif, board, course_id, preferred_types, weights) -> tuple:
    """Plus petit score = meilleure salle. Reprend la logique d'eptcpfaefinal."""
    under = 1 if room.capacity < max(effectif, 1) else 0
    gap = abs(room.capacity - max(effectif, 1))
    type_penalty = 0 if room.room_type in preferred_types else 5
    weight_gap, weight_rotation, weight_balance = weights
    usage_course = board.course_room_usage.get((course_id, room.id), 0) if course_id else 0
    usage_global = board.room_usage.get(room.id, 0)
    weighted = (
        gap * max(1, weight_gap)
        + usage_course * max(1, weight_rotation)
        + usage_global * max(1, weight_balance)
    )
    return (under, type_penalty, weighted, room.code)


def candidate_rooms(*, effectif, tolerance, preferred_types, exclude_ids=None):
    qs = Room.objects.filter(is_active=True).exclude(status='maintenance')
    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)
    min_capacity = max(effectif - max(tolerance, 0), 1)
    sized = qs.filter(capacity__gte=min_capacity)
    pool = sized if sized.exists() else qs
    if preferred_types:
        typed = pool.filter(room_type__in=preferred_types)
        if typed.exists():
            pool = typed
    return list(pool)


def pick_room(*, day, start, end, effectif, tolerance, preferred_types, board, course_id, weights, exclude_ids=None, locked_room=None):
    if locked_room and board.room_free(day, locked_room.id, start, end):
        if locked_room.status != 'maintenance' and locked_room.is_active:
            return locked_room

    ranked = []
    for room in candidate_rooms(
        effectif=effectif, tolerance=tolerance, preferred_types=preferred_types, exclude_ids=exclude_ids,
    ):
        if not board.room_free(day, room.id, start, end):
            continue
        ranked.append((score_room(room, effectif, board, course_id, preferred_types, weights), room))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0])
    return ranked[0][1]
