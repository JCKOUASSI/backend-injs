"""Services métier des inscriptions administratives.

Opération centrale : ``convertir_admission_en_inscription``, qui transforme un
candidat admis en étudiant régulièrement inscrit. Entièrement transactionnelle.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from formations.models import Participant

from .matricules import generer_matricule
from .models import (
    DossierEtudiant,
    InscriptionAdministrative,
    JournalScolarite,
    StatutEtudiant,
    journaliser,
)

S = InscriptionAdministrative.Statut

# Transitions autorisées du cycle de vie d'une inscription administrative.
TRANSITIONS = {
    S.BROUILLON: {S.EN_ATTENTE, S.ANNULEE},
    S.EN_ATTENTE: {S.A_VALIDER, S.REJETEE, S.ANNULEE},
    S.A_VALIDER: {S.VALIDEE, S.REJETEE, S.EN_ATTENTE, S.ANNULEE},
    S.VALIDEE: {S.SUSPENDUE, S.TERMINEE, S.ANNULEE},
    S.SUSPENDUE: {S.VALIDEE, S.ANNULEE, S.TERMINEE},
    S.REJETEE: {S.EN_ATTENTE, S.ANNULEE},
    S.ANNULEE: set(),
    S.TERMINEE: set(),
}


class InscriptionImpossible(ValidationError):
    """L'opération demandée est incompatible avec l'état du dossier."""


def transitions_possibles(inscription):
    return sorted(TRANSITIONS.get(inscription.statut, set()))


@transaction.atomic
def appliquer_transition(inscription, nouveau_statut, acteur=None, commentaire=''):
    """Applique une transition de statut d'inscription, horodate la validation."""
    if nouveau_statut == inscription.statut:
        raise InscriptionImpossible(
            f'L’inscription est déjà au statut « {inscription.get_statut_display()} ».'
        )
    if nouveau_statut not in TRANSITIONS.get(inscription.statut, set()):
        raise InscriptionImpossible(
            f'Transition interdite : « {inscription.get_statut_display()} » ne peut pas '
            f'passer à « {InscriptionAdministrative.Statut(nouveau_statut).label} ».'
        )

    ancien = inscription.statut
    inscription.statut = nouveau_statut
    champs = ['statut', 'updated_at']

    if nouveau_statut == S.VALIDEE:
        _verifier_unicite_inscription_validee(inscription)
        inscription.date_validation = timezone.now()
        inscription.valide_par = acteur if getattr(acteur, 'pk', None) else None
        champs += ['date_validation', 'valide_par']

    inscription.save(update_fields=champs)

    journaliser(
        JournalScolarite.Action.INSCRIPTION_TRANSITION,
        objet=inscription,
        acteur=acteur,
        ancienne_valeur=ancien,
        nouvelle_valeur=nouveau_statut,
        commentaire=commentaire,
    )
    return inscription


def _verifier_unicite_inscription_validee(inscription):
    """Empêche deux inscriptions validées sur le même couple année/formation/niveau."""
    doublon = InscriptionAdministrative.objects.filter(
        etudiant=inscription.etudiant,
        annee_academique=inscription.annee_academique,
        ref_formation=inscription.ref_formation,
        parcours=inscription.parcours,
        niveau=inscription.niveau,
        statut=S.VALIDEE,
    ).exclude(pk=inscription.pk)
    if doublon.exists():
        raise InscriptionImpossible(
            'Cet étudiant a déjà une inscription validée pour cette année, '
            'cette formation et ce niveau.'
        )


def _statut_par_defaut():
    return StatutEtudiant.objects.filter(code='ACTIF', actif=True).first()


@transaction.atomic
def creer_ou_retrouver_participant(candidat, annee_academique, acteur=None, matricule=None):
    """Retrouve le Participant lié au candidat, ou le crée avec un matricule généré.

    Le Participant est l'identité opérationnelle utilisée par les présences, les
    notes et la finance : on le réutilise s'il existe déjà.
    """
    if candidat.participant_id:
        return candidat.participant, False

    matricule = matricule or generer_matricule(annee_academique)
    if Participant.objects.filter(matricule=matricule).exists():
        raise InscriptionImpossible(f'Le matricule {matricule} est déjà attribué.')

    participant = Participant.objects.create(
        matricule=matricule,
        nom=candidat.nom,
        prenom=candidat.prenom,
        sexe='MASCULIN' if candidat.sexe == 'M' else ('FEMININ' if candidat.sexe == 'F' else ''),
        date_naissance=candidat.date_naissance,
        lieu_naissance=candidat.lieu_naissance or '',
        email=candidat.email or '',
        telephone=candidat.telephone or '',
        telephone2=candidat.telephone2 or '',
    )
    candidat.participant = participant
    candidat.save(update_fields=['participant'])

    journaliser(
        JournalScolarite.Action.MATRICULE_GENERE,
        objet=participant,
        acteur=acteur,
        nouvelle_valeur=matricule,
        extra={'candidat_id': candidat.id},
    )
    return participant, True


def synchroniser_champs_operationnels(participant, admission):
    """Reporte catégorie, grade et vague sur le Participant, au format texte attendu.

    Les écrans, filtres et statistiques existants lisent ces champs texte libres.
    On ne remplit que ce qui est vide : une valeur déjà saisie n'est jamais écrasée.
    """
    correspondances = {
        'categorie': admission.categorie.libelle if admission.categorie_id else '',
        'grade': admission.grade.libelle if admission.grade_id else '',
        'vague': admission.vague.libelle if admission.vague_id else '',
    }
    modifies = [
        champ for champ, valeur in correspondances.items()
        if valeur and not getattr(participant, champ)
    ]
    for champ in modifies:
        setattr(participant, champ, correspondances[champ])
    if modifies:
        participant.save(update_fields=modifies)
    return modifies


@transaction.atomic
def creer_ou_retrouver_dossier(participant, acteur=None):
    dossier = DossierEtudiant.objects.filter(participant=participant).first()
    if dossier is not None:
        return dossier, False
    dossier = DossierEtudiant.objects.create(
        participant=participant,
        statut=_statut_par_defaut(),
        date_premiere_inscription=timezone.localdate(),
    )
    return dossier, True


@transaction.atomic
def convertir_admission_en_inscription(admission, acteur=None, matricule=None,
                                       valider=False, **surcharges):
    """Transforme une admission en inscription administrative.

    Enchaîne, dans une seule transaction : contrôle de l'admission, contrôle des
    pièces obligatoires, création ou reprise du Participant, génération du
    matricule, création du dossier étudiant, puis création de l'inscription.
    """
    if not admission.permet_inscription:
        if admission.est_expiree:
            raise InscriptionImpossible(
                f'Admission expirée depuis le {admission.date_limite_inscription:%d/%m/%Y}.'
            )
        raise InscriptionImpossible(
            f'La décision « {admission.get_decision_display()} » ne permet pas d’inscrire ce candidat.'
        )

    candidature = admission.candidature
    if not candidature.dossier_complet:
        validees, total = candidature.completude
        raise InscriptionImpossible(
            f'Dossier de pièces incomplet : {validees}/{total} pièce(s) obligatoire(s) validée(s).'
        )

    participant, participant_cree = creer_ou_retrouver_participant(
        admission.candidat, admission.annee_academique, acteur=acteur, matricule=matricule,
    )
    synchroniser_champs_operationnels(participant, admission)
    dossier, _ = creer_ou_retrouver_dossier(participant, acteur=acteur)

    champs = {
        'etudiant': dossier,
        'annee_academique': admission.annee_academique,
        'ref_formation': admission.ref_formation,
        'parcours': admission.parcours,
        'niveau': admission.niveau,
        'vague': admission.vague,
        'categorie': admission.categorie,
        'grade': admission.grade,
        'regime': candidature.regime,
        'statut_etudiant': _statut_par_defaut(),
        'admission': admission,
        'type_inscription': InscriptionAdministrative.Type.PREMIERE,
    }
    champs.update({cle: valeur for cle, valeur in surcharges.items() if valeur is not None})

    inscription = InscriptionAdministrative(**champs)
    inscription.full_clean(exclude=['date_validation'])
    inscription.save()

    journaliser(
        JournalScolarite.Action.INSCRIPTION_CREEE,
        objet=inscription,
        acteur=acteur,
        nouvelle_valeur=inscription.statut,
        extra={
            'admission_id': admission.id,
            'matricule': participant.matricule,
            'participant_cree': participant_cree,
        },
    )

    if valider:
        appliquer_transition(inscription, S.EN_ATTENTE, acteur=acteur)
        appliquer_transition(inscription, S.A_VALIDER, acteur=acteur)
        appliquer_transition(inscription, S.VALIDEE, acteur=acteur)

    return inscription
