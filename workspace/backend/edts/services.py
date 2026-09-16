from django.db import transaction

from .models import (
    AffectationCreneau,
    ConflitCreneau,
)


def _plages_creneau(aff):
    """Retourne les plages horaires effectives d'une affectation (par semaine)."""
    return aff.creneau_template


def _sont_en_conflit(a, b):
    """Vérifie si deux affectations sont en conflit horaire.

    Deux affectations entrent en conflit si leurs plages chevauchent
    la même semaine et le même créneau.
    """
    if a.semaine_fin < b.semaine_debut or b.semaine_fin < a.semaine_debut:
        return False

    ct_a = a.creneau_template
    ct_b = b.creneau_template
    if not ct_a or not ct_b:
        return False
    if ct_a.jour != ct_b.jour:
        return False
    if ct_a.heure_debut == ct_b.heure_debut and ct_a.heure_fin == ct_b.heure_fin:
        return True
    debut_max = ct_a.heure_debut if ct_a.heure_debut > ct_b.heure_debut else ct_b.heure_debut
    fin_min = ct_a.heure_fin if ct_a.heure_fin < ct_b.heure_fin else ct_b.heure_fin
    return debut_max < fin_min


def _type_conflit_for(a, b):
    """Détermine le type de conflit principal entre deux affectations."""
    if a.enseignant_id and b.enseignant_id and a.enseignant_id == b.enseignant_id:
        return 'HORAIRE_ENSEIGNANT'
    if a.enseignant_id and b.groupe_id:
        return 'HORAIRE_GROUPETUDIANT'
    if a.groupe_id and b.groupe_id and a.groupe_id == b.groupe_id:
        return 'HORAIRE_GROUPETUDIANT'
    if a.formation_id and b.formation_id and a.formation_id == b.formation_id:
        return 'HORAIRE_MODULE'
    return 'HORAIRE_SALLE'


def _creer_conflit(emploi_du_temps, a, b):
    """Crée ou réactive un conflit entre deux affectations."""
    from django.utils import timezone

    with transaction.atomic():
        existing = ConflitCreneau.objects.filter(
            emploi_du_temps=emploi_du_temps,
            type_conflit=_type_conflit_for(a, b),
            lignes_creneaux__contains=[a.pk, b.pk],
            actif=True,
        ).first()
        if existing:
            existing.lignes_creneaux = list(
                set(existing.lignes_creneaux + [a.pk, b.pk])
            )
            existing.recalcule_le = timezone.now()
            existing.save(update_fields=['lignes_creneaux', 'recalcule_le'])
            return existing

        return ConflitCreneau.objects.create(
            emploi_du_temps=emploi_du_temps,
            type_conflit=_type_conflit_for(a, b),
            description=(
                f"Conflit détecté entre {a.creneau_template} et "
                f"{b.creneau_template}."
            ),
            lignes_creneaux=[a.pk, b.pk],
        )


def detecter_conflits(emploi_du_temps):
    """Détecte les conflits horaires dans un EDT et les enregistre.

    Retourne un dict avec les statistiques de détection.
    """
    affectations = AffectationCreneau.objects.filter(
        emploi_du_temps=emploi_du_temps,
        actif=True,
    ).select_related('creneau_template', 'formation', 'groupe')

    conflits_detectes = []
    affected_ids = set()

    for aff in affectations:
        for other in affectations.exclude(pk=aff.pk):
            if _sont_en_conflit(aff, other):
                pair = tuple(sorted([aff.pk, other.pk]))
                if pair not in affected_ids:
                    affected_ids.add(pair)
                    conflits_detectes.append(
                        _creer_conflit(
                            emploi_du_temps,
                            aff,
                            other,
                        )
                    )

    return {
        'affectations_consultrees': affectations.count(),
        'conflits_detectes': len(conflits_detectes),
    }
