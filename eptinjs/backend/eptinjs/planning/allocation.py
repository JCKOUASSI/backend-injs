"""Choix des salles et des enseignants.

Portage de ``room_allocator.py`` / ``trainer_allocator.py`` : filtrage des
candidats puis score pondéré (plus le score est bas, meilleur est le candidat).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls

from .occupations import OccupationIndex

# Types de salle adaptés à chaque nature de séance ; simple préférence, pas un
# filtre strict, pour éviter de rendre un créneau infaisable.
TYPES_PREFERES = {
    'cm': {'amphitheater', 'conference', 'classroom'},
    'td': {'td', 'classroom', 'seminar'},
    'tp': {'tp', 'lab', 'computer', 'gym', 'sport', 'specialized'},
}

PENALITE_TYPE_INADAPTE = 40
PENALITE_SOUS_CAPACITE = 1000


@dataclass
class SalleCandidate:
    room: object
    score: float


def capacite_minimale(effectif: int, tolerance_pct: int) -> int:
    """Capacité en dessous de laquelle une salle est écartée."""
    if effectif <= 0:
        return 0
    return int(round(effectif * (1 - (tolerance_pct or 0) / 100)))


def score_salle(
    room,
    *,
    effectif: int,
    session_kind: str,
    occupations: OccupationIndex,
    salle_precedente_id,
    poids_ecart_capacite: int,
    poids_rotation_salle: int,
    poids_equilibrage_salles: int,
) -> float:
    """Score pondéré : ajustement de capacité, rotation, équilibrage global."""
    capacite = room.capacity or 0
    ecart = capacite - effectif
    score = 0.0

    if ecart < 0:
        # Salle plus petite que l'effectif : tolérée mais fortement pénalisée.
        score += PENALITE_SOUS_CAPACITE + abs(ecart) * poids_ecart_capacite
    else:
        score += ecart * poids_ecart_capacite

    if room.room_type not in TYPES_PREFERES.get(session_kind, set()):
        score += PENALITE_TYPE_INADAPTE

    if salle_precedente_id and str(room.id) != str(salle_precedente_id):
        score += poids_rotation_salle * 10

    score += occupations.usage_total('room', room.id) * poids_equilibrage_salles
    return score


def choisir_salle(
    rooms,
    *,
    jour: date_cls,
    debut: int,
    fin: int,
    effectif: int,
    session_kind: str,
    occupations: OccupationIndex,
    tolerance_pct: int,
    salle_imposee=None,
    salle_precedente_id=None,
    poids_ecart_capacite: int = 5,
    poids_rotation_salle: int = 2,
    poids_equilibrage_salles: int = 1,
):
    """Meilleure salle libre sur le créneau, ou ``None`` si aucune ne convient."""
    if salle_imposee is not None:
        if occupations.est_libre('room', salle_imposee.id, jour, debut, fin):
            return salle_imposee
        return None

    minimum = capacite_minimale(effectif, tolerance_pct)
    candidates: list[SalleCandidate] = []
    for room in rooms:
        if not room.is_active or room.status != 'available':
            continue
        if (room.capacity or 0) < minimum:
            continue
        if not occupations.est_libre('room', room.id, jour, debut, fin):
            continue
        candidates.append(SalleCandidate(
            room=room,
            score=score_salle(
                room,
                effectif=effectif,
                session_kind=session_kind,
                occupations=occupations,
                salle_precedente_id=salle_precedente_id,
                poids_ecart_capacite=poids_ecart_capacite,
                poids_rotation_salle=poids_rotation_salle,
                poids_equilibrage_salles=poids_equilibrage_salles,
            ),
        ))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item.score, item.room.code))
    return candidates[0].room


def enseignant_disponible(teacher_id, jour: date_cls, debut: int, fin: int, occupations: OccupationIndex) -> bool:
    """Un enseignant non renseigné n'impose aucune contrainte."""
    if not teacher_id:
        return True
    return occupations.est_libre('teacher', teacher_id, jour, debut, fin)
