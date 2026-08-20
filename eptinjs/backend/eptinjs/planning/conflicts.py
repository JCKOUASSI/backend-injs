"""Détection de conflits sur un emploi du temps existant.

Fusionne ``conflicts.py`` (contrôles intra-groupe) et ``overlap.py``
(collisions de salles inter-formations) de l'application source.
"""
from __future__ import annotations

from collections import defaultdict

from django.db.models import Count

from apps.students.models import Student

from ..models import JourFerie, ParametresPlanification, Seance
from .occupations import to_minutes

GRAVITES = {'bloquant': 3, 'majeur': 2, 'mineur': 1}


def _conflit(type_conflit, gravite, message, seances):
    return {
        'type': type_conflit,
        'gravite': gravite,
        'message': message,
        'seances': [str(item.id) for item in seances],
        'date': seances[0].date.isoformat() if seances else None,
    }


def _chevauchements(seances, cle, libelle_ressource, type_conflit):
    """Détecte les doubles réservations d'une même ressource."""
    conflits = []
    par_ressource = defaultdict(list)
    for seance in seances:
        valeur = cle(seance)
        if valeur:
            par_ressource[(str(valeur), seance.date)].append(seance)

    for (_ressource, _jour), groupe in par_ressource.items():
        ordonnees = sorted(groupe, key=lambda item: item.heure_debut)
        for index, seance in enumerate(ordonnees):
            for suivante in ordonnees[index + 1:]:
                if suivante.heure_debut >= seance.heure_fin:
                    break
                conflits.append(_conflit(
                    type_conflit,
                    'bloquant',
                    f'{libelle_ressource(seance)} occupé·e deux fois le {seance.date} '
                    f'({seance.heure_debut:%H:%M}–{seance.heure_fin:%H:%M} vs '
                    f'{suivante.heure_debut:%H:%M}–{suivante.heure_fin:%H:%M}).',
                    [seance, suivante],
                ))
    return conflits


def detecter_conflits(periode=None, *, seances=None) -> dict:
    """Analyse un lot de séances et renvoie les anomalies détectées."""
    if seances is None:
        queryset = Seance.objects.exclude(statut='annulee').select_related(
            'course', 'promotion', 'groupe', 'room', 'teacher__user', 'supervisor__user', 'periode',
        )
        if periode is not None:
            queryset = queryset.filter(periode=periode)
        seances = list(queryset)
    seances = list(seances)

    if not seances:
        return {'count': 0, 'par_type': {}, 'conflits': []}

    conflits: list[dict] = []

    conflits += _chevauchements(
        seances,
        lambda item: item.room_id,
        lambda item: f'Salle {item.room.code}' if item.room_id else 'Salle',
        'salle_double_reservation',
    )
    conflits += _chevauchements(
        seances,
        lambda item: item.teacher_id,
        lambda item: f'Enseignant {item.teacher.user.get_full_name()}' if item.teacher_id else 'Enseignant',
        'enseignant_double_reservation',
    )
    conflits += _chevauchements(
        seances,
        lambda item: item.groupe_id or item.promotion_id,
        lambda item: f'Auditoire {item.groupe.code if item.groupe_id else item.promotion.name}',
        'auditoire_double_reservation',
    )

    periodes = {seance.periode for seance in seances if seance.periode_id}
    institutions = {periode_item.academic_year.institution_id for periode_item in periodes}
    feries = {
        row.date: row.libelle
        for row in JourFerie.objects.filter(institution_id__in=institutions, is_active=True)
    }

    params_par_periode = {
        periode_item.id: ParametresPlanification.resolve(periode_item) for periode_item in periodes
    }

    effectifs = {
        str(row['promotion_id']): row['total']
        for row in Student.objects
        .filter(status='active', promotion_id__in={seance.promotion_id for seance in seances})
        .values('promotion_id').annotate(total=Count('id'))
    }

    seances_par_jour = defaultdict(int)
    for seance in seances:
        cle = (str(seance.groupe_id or seance.promotion_id), seance.date)
        seances_par_jour[cle] += 1

    for seance in seances:
        params = params_par_periode.get(seance.periode_id)

        if seance.date in feries:
            conflits.append(_conflit(
                'jour_ferie', 'majeur',
                f'Séance planifiée le jour férié « {feries[seance.date]} » ({seance.date}).',
                [seance],
            ))

        if params:
            if seance.date.weekday() not in (params.jours_actifs or []):
                conflits.append(_conflit(
                    'jour_non_ouvre', 'mineur',
                    f'Séance hors des jours ouvrés paramétrés ({seance.date}).',
                    [seance],
                ))

            debut, fin = to_minutes(seance.heure_debut), to_minutes(seance.heure_fin)
            dans_une_plage = any(
                debut >= to_minutes(plage_debut) and fin <= to_minutes(plage_fin)
                for _label, plage_debut, plage_fin in params.creneaux()
            )
            if params.creneaux() and not dans_une_plage:
                conflits.append(_conflit(
                    'hors_plage_horaire', 'mineur',
                    f'Créneau {seance.heure_debut:%H:%M}–{seance.heure_fin:%H:%M} hors des plages paramétrées.',
                    [seance],
                ))

            cle_jour = (str(seance.groupe_id or seance.promotion_id), seance.date)
            if seances_par_jour[cle_jour] > params.max_seances_par_jour:
                conflits.append(_conflit(
                    'trop_de_seances', 'mineur',
                    f'{seances_par_jour[cle_jour]} séances le {seance.date} pour cet auditoire '
                    f'(maximum {params.max_seances_par_jour}).',
                    [seance],
                ))

        if seance.room_id:
            effectif = effectifs.get(str(seance.promotion_id), 0)
            if seance.groupe_id:
                effectif = seance.groupe.effectif or seance.groupe.effectif_max
            if effectif and (seance.room.capacity or 0) < effectif:
                conflits.append(_conflit(
                    'capacite_insuffisante', 'majeur',
                    f'Salle {seance.room.code} ({seance.room.capacity} places) '
                    f'pour {effectif} étudiants le {seance.date}.',
                    [seance],
                ))
        else:
            conflits.append(_conflit(
                'salle_manquante', 'majeur',
                f'Aucune salle affectée le {seance.date} à {seance.heure_debut:%H:%M}.',
                [seance],
            ))

        if not seance.teacher_id:
            conflits.append(_conflit(
                'enseignant_manquant', 'majeur',
                f'Aucun enseignant affecté le {seance.date} à {seance.heure_debut:%H:%M}.',
                [seance],
            ))

    par_type: dict[str, int] = defaultdict(int)
    for conflit in conflits:
        par_type[conflit['type']] += 1

    conflits.sort(key=lambda item: (-GRAVITES.get(item['gravite'], 0), item['date'] or ''))
    return {'count': len(conflits), 'par_type': dict(par_type), 'conflits': conflits}
