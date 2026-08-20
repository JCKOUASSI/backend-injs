"""Index d'occupation des ressources.

Une ressource est identifiée par un couple ``(kind, key)`` : ``('room', <uuid>)``,
``('teacher', <uuid>)``, ``('promotion', <uuid>)`` ou ``('groupe', <uuid>)``.
Les créneaux sont stockés en minutes depuis minuit pour des comparaisons rapides.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date as date_cls, time as time_cls


def to_minutes(moment: time_cls) -> int:
    return moment.hour * 60 + moment.minute


def to_time(minutes: int) -> time_cls:
    return time_cls(hour=(minutes // 60) % 24, minute=minutes % 60)


class OccupationIndex:
    """Occupations existantes et créées pendant une génération."""

    def __init__(self):
        self._slots: dict[tuple[str, str, date_cls], list[tuple[int, int]]] = defaultdict(list)
        self._par_jour: Counter[tuple[str, str, date_cls]] = Counter()
        self._usage: Counter[tuple[str, str]] = Counter()

    def add(self, kind: str, key, jour: date_cls, debut: int, fin: int) -> None:
        if key is None:
            return
        index = (kind, str(key), jour)
        self._slots[index].append((debut, fin))
        self._par_jour[index] += 1
        self._usage[(kind, str(key))] += 1

    def est_libre(self, kind: str, key, jour: date_cls, debut: int, fin: int) -> bool:
        if key is None:
            return True
        for occupe_debut, occupe_fin in self._slots[(kind, str(key), jour)]:
            if debut < occupe_fin and occupe_debut < fin:
                return False
        return True

    def compte_du_jour(self, kind: str, key, jour: date_cls) -> int:
        if key is None:
            return 0
        return self._par_jour[(kind, str(key), jour)]

    def usage_total(self, kind: str, key) -> int:
        if key is None:
            return 0
        return self._usage[(kind, str(key))]

    def creneaux(self, kind: str, key, jour: date_cls) -> list[tuple[int, int]]:
        if key is None:
            return []
        return list(self._slots[(kind, str(key), jour)])

    @classmethod
    def depuis_seances(cls, seances) -> 'OccupationIndex':
        """Construit l'index à partir de séances déjà persistées."""
        index = cls()
        for seance in seances:
            debut = to_minutes(seance.heure_debut)
            fin = to_minutes(seance.heure_fin)
            index.add('room', seance.room_id, seance.date, debut, fin)
            index.add('teacher', seance.teacher_id, seance.date, debut, fin)
            index.add('teacher', seance.supervisor_id, seance.date, debut, fin)
            if seance.groupe_id:
                index.add('groupe', seance.groupe_id, seance.date, debut, fin)
            else:
                index.add('promotion', seance.promotion_id, seance.date, debut, fin)
        return index


class AudienceLock:
    """Disponibilité d'un auditoire (promotion entière ou sous-groupe).

    Une séance de promotion bloque tous ses groupes ; une séance de groupe
    n'empêche pas les autres groupes de la même promotion de travailler en
    parallèle, mais reste incompatible avec une séance de promotion entière.
    """

    def __init__(self, occupations: OccupationIndex, groupes_par_promotion: dict[str, list[str]]):
        self.occupations = occupations
        self.groupes_par_promotion = groupes_par_promotion

    def est_libre(self, promotion_id, groupe_id, jour: date_cls, debut: int, fin: int) -> bool:
        if not self.occupations.est_libre('promotion', promotion_id, jour, debut, fin):
            return False
        if groupe_id:
            return self.occupations.est_libre('groupe', groupe_id, jour, debut, fin)
        return all(
            self.occupations.est_libre('groupe', autre, jour, debut, fin)
            for autre in self.groupes_par_promotion.get(str(promotion_id), [])
        )

    def reserver(self, promotion_id, groupe_id, jour: date_cls, debut: int, fin: int) -> None:
        if groupe_id:
            self.occupations.add('groupe', groupe_id, jour, debut, fin)
        else:
            self.occupations.add('promotion', promotion_id, jour, debut, fin)

    def compte_du_jour(self, promotion_id, groupe_id, jour: date_cls) -> int:
        if groupe_id:
            return self.occupations.compte_du_jour('groupe', groupe_id, jour)
        return self.occupations.compte_du_jour('promotion', promotion_id, jour)
