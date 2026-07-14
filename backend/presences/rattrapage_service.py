"""Logique métier des rattrapages inter-cohorte.

Un rattrapage permet à un auditeur de suivre une séance dispensée à une autre
cohorte (groupe / grade / vague / secrétariat) que la sienne, sans l'inscrire
au module d'accueil (pas de ``ModuleParticipant``) afin de ne pas fausser les
effectifs attendus de cette cohorte.

La présence est matérialisée par un ``Pointage`` forcé, réutilisant
l'infrastructure de badgeage forcé existante.
"""
from django.db import transaction

from .bulk_force_auditeurs import (
    force_entree_personne,
    force_presence_auditeur,
    force_sortie_pointage,
)
from .duree import rattrapage_creneau_timestamps
from .models import AuditLog, Pointage, Rattrapage, _log_audit


class RattrapageError(Exception):
    """Erreur métier lors de la génération d'une présence de rattrapage."""


def _audit_rattrapage(action, rattrapage, request=None, extra=None):
    participant = rattrapage.participant
    module = rattrapage.module_rattrapage
    _log_audit(
        action=action,
        request=request,
        cible_type='participant',
        cible_numero=getattr(participant, 'matricule', '') or str(participant.pk),
        cible_nom=f"{participant.nom} {participant.prenom}".strip(),
        formation=module.formation if module else None,
        pointage=rattrapage.pointage,
        extra={
            'rattrapage_id': rattrapage.pk,
            'seance_rattrapage_id': rattrapage.seance_rattrapage_id,
            'module_origine_id': rattrapage.module_origine_id,
            'seance_manquee_id': rattrapage.seance_manquee_id,
            'motif': rattrapage.motif,
            **(extra or {}),
        },
    )


def lier_rattrapage_au_badge(participant, seance, pointage, *, request=None):
    """Associe un badge naturel au rattrapage planifié sur cette séance."""
    rattrapage = (
        Rattrapage.objects
        .filter(
            participant=participant,
            seance_rattrapage=seance,
            statut=Rattrapage.Statut.PLANIFIE,
        )
        .first()
    )
    if rattrapage is None:
        return None

    rattrapage.pointage = pointage
    rattrapage.statut = Rattrapage.Statut.EFFECTUE
    rattrapage.save(update_fields=['pointage', 'statut', 'updated_at'])
    _audit_rattrapage(
        AuditLog.Action.RATTRAPAGE_PRESENCE,
        rattrapage,
        request=request,
        extra={'via_badge': True, 'pointage_created': True},
    )
    return rattrapage


def generer_presence_rattrapage(rattrapage, *, request=None, with_sortie=True, motif=None):
    """Force la présence de l'auditeur sur la séance de rattrapage et la lie.

    Idempotent : si un pointage existe déjà pour (séance, auditeur), il est
    réutilisé. Passe le rattrapage au statut ``EFFECTUE``.
    """
    seance = rattrapage.seance_rattrapage
    participant = rattrapage.participant
    if seance is None or participant is None:
        raise RattrapageError("Rattrapage incomplet : séance ou auditeur manquant.")

    formation = seance.module.formation
    motif_final = motif or rattrapage.motif or 'Rattrapage inter-cohorte'
    seance_date = seance.date_journee

    with transaction.atomic():
        pointage = (
            Pointage.objects.filter(session=seance, participant=participant)
            .order_by('-timestamp_entree')
            .first()
        )
        created = False
        if pointage is None:
            if with_sortie:
                pointage, err = force_presence_auditeur(
                    formation,
                    seance,
                    participant,
                    seance_date,
                    motif_final,
                    request=request,
                    ignore_constraints=True,
                )
            else:
                ts_entree, _ = rattrapage_creneau_timestamps(seance)
                pointage, err = force_entree_personne(
                    formation,
                    seance,
                    participant,
                    'participant',
                    seance_date,
                    motif_final,
                    request=request,
                    timestamp_entree=ts_entree,
                    ignore_constraints=True,
                )
            if err:
                raise RattrapageError(err)
            created = True
        elif with_sortie and not pointage.timestamp_sortie:
            _, err = force_sortie_pointage(
                formation,
                pointage,
                seance,
                participant,
                'participant',
                motif_final,
                request=request,
                creneau_complet=True,
            )
            if err:
                raise RattrapageError(err)

        rattrapage.pointage = pointage
        rattrapage.statut = Rattrapage.Statut.EFFECTUE
        rattrapage.save(update_fields=['pointage', 'statut', 'updated_at'])
        _audit_rattrapage(
            AuditLog.Action.RATTRAPAGE_PRESENCE,
            rattrapage,
            request=request,
            extra={'pointage_created': created},
        )

    return pointage


def annuler_rattrapage(rattrapage, *, request=None, supprimer_pointage=False):
    """Annule un rattrapage. Optionnellement supprime le pointage généré."""
    with transaction.atomic():
        pointage = rattrapage.pointage
        if supprimer_pointage and pointage is not None:
            rattrapage.pointage = None
            rattrapage.save(update_fields=['pointage', 'updated_at'])
            pointage.delete()
        rattrapage.statut = Rattrapage.Statut.ANNULE
        rattrapage.save(update_fields=['statut', 'updated_at'])
        _audit_rattrapage(
            AuditLog.Action.RATTRAPAGE_CANCEL,
            rattrapage,
            request=request,
            extra={'pointage_supprime': supprimer_pointage},
        )
    return rattrapage
