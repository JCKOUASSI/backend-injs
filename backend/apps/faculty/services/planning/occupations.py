"""Index mémoire des occupations pour la génération d'un emploi du temps daté."""
from __future__ import annotations

from collections import defaultdict
from datetime import time


def overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return a_start < b_end and a_end > b_start


class OccupationBoard:
    """Occupations salles / personnels / promotions / groupes, en mémoire.

    Une séance « promotion entière » (sans groupe) bloque tous les groupes de
    cette promotion. Deux groupes distincts d'une même promotion peuvent en
    revanche siéger en parallèle — c'est le cas d'usage des TD et des TP.
    """

    BLOCKING_STATUSES = ('draft', 'generated', 'validated', 'published', 'in_progress', 'done')

    def __init__(self):
        self.rooms = defaultdict(list)
        self.staff = defaultdict(list)
        self.groups = defaultdict(list)
        self.promo_wide = defaultdict(list)
        self.promotions = defaultdict(list)
        self.room_usage = defaultdict(int)
        self.course_room_usage = defaultdict(int)
        self.day_load = defaultdict(int)
        self.locked_rooms = {}

    def load(self, seances):
        for seance in seances:
            if getattr(seance, 'status', 'generated') in self.BLOCKING_STATUSES:
                self.reserve(seance)

    def _busy(self, bucket, start, end) -> bool:
        return any(overlaps(start, end, existing_start, existing_end) for existing_start, existing_end in bucket)

    def room_free(self, day, room_id, start, end) -> bool:
        if not room_id:
            return True
        return not self._busy(self.rooms[(day, room_id)], start, end)

    def staff_free(self, day, staff_ids, start, end) -> bool:
        for teacher_id in staff_ids or ():
            if teacher_id and self._busy(self.staff[(day, teacher_id)], start, end):
                return False
        return True

    def audience_free(self, day, promotion_id, group_id, start, end) -> bool:
        if self._busy(self.promo_wide[(day, promotion_id)], start, end):
            return False
        if group_id:
            return not self._busy(self.groups[(day, group_id)], start, end)
        return not self._busy(self.promotions[(day, promotion_id)], start, end)

    def day_count(self, day, promotion_id, group_id) -> int:
        key = (day, promotion_id, group_id)
        return self.day_load[key]

    def reserve(self, seance):
        day = seance.date
        start, end = seance.start_time, seance.end_time
        promotion_id = seance.promotion_id
        group_id = getattr(seance, 'group_id', None)

        if seance.room_id:
            self.rooms[(day, seance.room_id)].append((start, end))
            self.room_usage[seance.room_id] += 1
            if seance.course_id:
                self.course_room_usage[(seance.course_id, seance.room_id)] += 1

        for teacher_id in _staff_ids(seance):
            self.staff[(day, teacher_id)].append((start, end))

        self.promotions[(day, promotion_id)].append((start, end))
        if group_id:
            self.groups[(day, group_id)].append((start, end))
        else:
            self.promo_wide[(day, promotion_id)].append((start, end))

        self.day_load[(day, promotion_id, group_id)] += 1


def _staff_ids(seance):
    ids = set()
    teacher_id = getattr(seance, 'teacher_id', None)
    if teacher_id:
        ids.add(teacher_id)
    supervisor_id = getattr(seance, 'supervisor_id', None)
    if supervisor_id:
        ids.add(supervisor_id)
    elif hasattr(seance, 'resolved_supervisor'):
        supervisor = seance.resolved_supervisor()
        if supervisor:
            ids.add(supervisor.id)
    return ids
