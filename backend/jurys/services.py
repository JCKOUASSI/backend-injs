"""Services du module Jurys : workflow, calcul, décisions, PV, publication.

Règles (Prompt 13) :
  - seuls les étudiants concernés (inscriptions VALIDEE de la session) sont inclus ;
  - les propositions proviennent du moteur ECTS de ``scolarite`` (lot L3),
    uniquement à partir de notes VALIDÉES et verrouillées (lot L1) ;
  - toute décision manuelle est justifiée ;
  - une session VERROUILLE ne se modifie plus librement ; la rectification
    passe par une session dédiée (type RECTIFICATION) ;
  - toutes les délibérations sont journalisées (JournalScolarite, append-only).
"""
import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import transaction

from scolarite.models import InscriptionAdministrative, journaliser
from scolarite.validation_services import (
    _ponderee,
    calculer_validation_etudiant,
    regle_pour,
)

from .models import DecisionJury, MembreJury, PropositionJury, SessionJury


def transition(session, user):
    """Fait avancer la session vers l'état suivant de la chaîne contrôlée."""
    suivant = SessionJury.TRANSITIONS.get(session.statut)
    if suivant is None:
        raise ValidationError('La session est déjà à son état final (PUBLIE).')

    # Garde-fous spécifiques avant transition.
    if suivant == SessionJury.Statut.PV_GENERE:
        if not DecisionJury.objects.filter(session=session).exists():
            raise ValidationError(
                "Aucune décision enregistrée : le PV exige au moins une décision."
            )
    if suivant == SessionJury.Statut.DELIBERATION:
        if not PropositionJury.objects.filter(session=session).exists():
            raise ValidationError(
                "Aucune proposition calculée : exécutez d'abord l'action CALCUL."
            )

    ancien = session.statut
    with transaction.atomic():
        session.statut = suivant
        session.save(update_fields=['statut', 'updated_at'])
        journaliser(
            'JURY_TRANSITION', objet=session, acteur=user,
            ancienne_valeur=ancien, nouvelle_valeur=suivant,
        )
    return session


def ajouter_membre(session, user_cible, fonction, user):
    """Ajoute un membre au jury (session non verrouillée) et journalise."""
    if session.verrouillee:
        raise ValidationError('Session verrouillée : les membres ne peuvent plus être modifiés.')
    membre, created = MembreJury.objects.get_or_create(
        session=session, user=user_cible,
        defaults={'fonction': fonction, 'ajoute_par': user},
    )
    if created:
        journaliser('JURY_MEMBRE', objet=session, acteur=user,
                    nouvelle_valeur=f'{user_cible} – {fonction}')
    return membre


def inscriptions_concernees(session):
    """Étudiants concernés : inscriptions VALIDEE couvrant la session."""
    qs = InscriptionAdministrative.objects.filter(
        annee_academique=session.annee_academique,
        ref_formation=session.ref_formation,
        niveau=session.niveau,
        statut=InscriptionAdministrative.Statut.VALIDEE,
    ).select_related('etudiant')
    if session.parcours_id:
        qs = qs.filter(parcours=session.parcours)
    return qs


def _empreinte(resultat):
    """SHA-256 d'un résultat moteur (reproductibilité)."""
    brut = json.dumps(resultat, sort_keys=True, default=str).encode()
    return hashlib.sha256(brut).hexdigest()


def _nettoyer_resultat(resultat):
    """Nettoie un dict résultat avant stockage JSONField : Decimal → float.

    PostgreSQL/Django n'acceptent pas les ``decimal.Decimal`` dans un
    JSONField natif ; on convertit donc récursivement les Decimals en
    ``float`` (perte de précision négligeable pour des moyennes /20).
    """
    from decimal import Decimal

    def _clean(v):
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, list):
            return [_clean(x) for x in v]
        if isinstance(v, dict):
            return {k: _clean(val) for k, val in v.items()}
        return v

    return _clean(resultat)


def _moyenne_generale(resultat):
    """Moyenne générale = moyenne des semestres pondérée par crédits attendus."""
    paires = [
        (sem['moyenne'], sem['credits_attendus'])
        for sem in resultat.get('semestres', [])
        if sem.get('moyenne') is not None
    ]
    valeur = _ponderee(paires)
    return None if valeur is None else round(valeur, 2)


def calculer_propositions(session, user):
    """Action CALCUL : exécute le moteur pour chaque étudiant et persiste (append-only)."""
    if session.verrouillee:
        raise ValidationError('Session verrouillée : recalcul impossible.')
    if session.statut not in (
        SessionJury.Statut.PREPARATION,
        SessionJury.Statut.CONTROLE,
        SessionJury.Statut.CALCUL,
    ):
        raise ValidationError(
            "Le calcul n'est possible qu'aux états PREPARATION / CONTROLE / CALCUL."
        )

    regle = regle_pour(session.maquette)
    crees = 0
    with transaction.atomic():
        for inscription in inscriptions_concernees(session):
            resultat = calculer_validation_etudiant(inscription, session.maquette, regle)
            resultat = _nettoyer_resultat(resultat)
            PropositionJury.objects.create(
                session=session,
                inscription=inscription,
                participant=inscription.etudiant.participant,
                resultat=resultat,
                empreinte=_empreinte(resultat),
                decision_proposee=resultat['decision_proposee'],
                credits_acquis=resultat['credits_acquis'],
                calcule_par=user,
            )
            crees += 1
        journaliser('JURY_CALCUL', objet=session, acteur=user, nouvelle_valeur=str(crees))
    return crees


def enregistrer_decision(session, inscription, decision, user,
                         justification='', mention='', decision_manuelle=None):
    """Enregistre la décision officielle d'un étudiant (états DELIBERATION/DECISION).

    Une décision divergeant de la proposition du moteur est considérée
    manuelle et exige une justification.
    """
    if session.verrouillee:
        raise ValidationError('Session verrouillée : les décisions ne sont plus modifiables.')
    if session.statut not in (SessionJury.Statut.DELIBERATION, SessionJury.Statut.DECISION):
        raise ValidationError(
            "Les décisions ne se saisissent qu'aux états DELIBERATION / DECISION."
        )
    derniere = (
        PropositionJury.objects.filter(session=session, inscription=inscription)
        .order_by('-calcule_le').first()
    )
    if derniere is None:
        raise ValidationError("Calculez d'abord les propositions (action CALCUL).")

    if decision_manuelle is None:
        decision_manuelle = decision != derniere.decision_proposee
    if decision_manuelle and not (justification or '').strip():
        raise ValidationError({'justification': 'Toute décision manuelle doit être justifiée.'})

    obj, created = DecisionJury.objects.update_or_create(
        session=session, inscription=inscription,
        defaults={
            'participant': inscription.etudiant.participant,
            'decision': decision,
            'credits_acquis': derniere.credits_acquis,
            'moyenne_generale': _moyenne_generale(derniere.resultat),
            'mention': (mention or '').strip(),
            'decision_manuelle': decision_manuelle,
            'justification': (justification or '').strip(),
            'decide_par': user,
        },
    )
    journaliser(
        'JURY_DECISION', objet=obj, acteur=user,
        ancienne_valeur=derniere.decision_proposee,
        nouvelle_valeur=decision,
        commentaire=(justification or '').strip(),
        extra={'decision_manuelle': decision_manuelle},
    )
    return obj, created


def decisions_verrouillables(session):
    """Vérifie que chaque étudiant concerné dispose d'une décision avant verrouillage."""
    concernes = inscriptions_concernees(session).count()
    decidees = DecisionJury.objects.filter(session=session).count()
    if concernes != decidees:
        raise ValidationError(
            f'Décisions incomplètes : {decidees}/{concernes} étudiants décidés.'
        )


def notifier_publication(session):
    """Publication : notification in-app à la Direction (pattern existant).

    Best-effort : la publication ne doit pas échouer pour une notification.
    """
    from authentication.models import User
    from .models import NotificationJury

    try:
        decisions = DecisionJury.objects.filter(session=session).count()
        for dest in User.objects.filter(role=User.Role.DIRECTION, is_active=True):
            NotificationJury.objects.create(
                destinataire=dest,
                session=session,
                message=(
                    f'Jury publié : {session} — {decisions} décision(s) officielle(s).'
                ),
            )
    except Exception:  # noqa: BLE001
        pass


def publier(session, user):
    """Transition finale VERROUILLE → PUBLIE : notifie la Direction."""
    from .models import PVJury
    if session.statut != SessionJury.Statut.VERROUILLE:
        raise ValidationError('Seule une session verrouillée peut être publiée.')
    if not PVJury.objects.filter(session=session).exists():
        raise ValidationError('Aucun PV généré : la publication exige un PV.')
    session = transition(session, user)
    journaliser('JURY_PUBLICATION', objet=session, acteur=user)
    notifier_publication(session)
    return session