"""Création automatique des comptes badge (auditeurs / formateurs) et envoi d'email."""

import logging

from django.contrib.auth import get_user_model
from django.db.models import Q

from formations.models import Formateur, Participant

from .emails import send_welcome_email

User = get_user_model()
logger = logging.getLogger(__name__)

DEFAULT_BADGE_PASSWORD = 'OPHIR2025'


def _send_welcome_email_safe(user, password, *, mobile=False):
    """Envoi non bloquant : un échec SMTP ne doit pas faire échouer la provision."""
    try:
        send_welcome_email(user, password, mobile=mobile)
    except Exception as exc:
        logger.warning(
            'Email de bienvenue non envoyé pour %s : %s',
            getattr(user, 'username', user.pk),
            exc,
        )


def _empty_stats():
    return {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'emails_sent': 0,
        'errors': 0,
    }


def _find_user_by_badge(matricule):
    badge = (matricule or '').strip()
    if not badge:
        return None
    return User.objects.filter(
        Q(username__iexact=badge) | Q(matricule__iexact=badge),
    ).first()


def _participant_linked_to_user(user):
    try:
        return user.participant_profile
    except Participant.DoesNotExist:
        return None


def _formateur_linked_to_user(user):
    try:
        return user.formateur_profile
    except Formateur.DoesNotExist:
        return None


def ensure_auditeur_account(
    participant: Participant,
    *,
    password: str = DEFAULT_BADGE_PASSWORD,
    send_email: bool = True,
    skip_existing: bool = False,
    reset_password: bool = False,
) -> str:
    """Crée ou met à jour le compte User lié à un auditeur. Retourne created/updated/skipped."""
    if not participant.matricule:
        return 'skipped'

    if participant.user_id and skip_existing:
        return 'skipped'

    user = participant.user
    if user is None:
        user = _find_user_by_badge(participant.matricule)
        if user is not None:
            linked = _participant_linked_to_user(user)
            if linked is not None and linked.pk != participant.pk:
                return 'skipped'
            participant.user = user
            participant.save(update_fields=['user'])
        else:
            user = User(
                username=participant.matricule,
                email=participant.email or '',
                first_name=participant.prenom[:150],
                last_name=participant.nom[:150],
                role=User.Role.AUDITEUR,
                matricule=participant.matricule,
                secretariat=participant.secretariat,
                is_active=True,
                must_change_password=True,
            )
            user.set_password(password)
            user.save()
            participant.user = user
            participant.save(update_fields=['user'])
            if send_email and user.email:
                _send_welcome_email_safe(user, password, mobile=True)
            return 'created'

    user.username = participant.matricule
    user.email = participant.email or ''
    user.first_name = participant.prenom[:150]
    user.last_name = participant.nom[:150]
    user.role = User.Role.AUDITEUR
    user.matricule = participant.matricule
    user.secretariat = participant.secretariat
    user.is_active = True
    if reset_password:
        user.set_password(password)
        user.must_change_password = True
    user.save()
    return 'updated'


def ensure_formateur_account(
    formateur: Formateur,
    *,
    password: str = DEFAULT_BADGE_PASSWORD,
    send_email: bool = True,
    skip_existing: bool = False,
    reset_password: bool = False,
) -> str:
    """Crée ou met à jour le compte User lié à un formateur. Retourne created/updated/skipped."""
    if not formateur.numerobadge:
        return 'skipped'

    if formateur.user_id and skip_existing:
        return 'skipped'

    user = formateur.user
    if user is None:
        user = _find_user_by_badge(formateur.numerobadge)
        if user is not None:
            linked = _formateur_linked_to_user(user)
            if linked is not None and linked.pk != formateur.pk:
                return 'skipped'
            formateur.user = user
            formateur.save(update_fields=['user'])
        else:
            user = User(
                username=formateur.numerobadge,
                email=formateur.email or '',
                first_name=formateur.prenom[:150],
                last_name=formateur.nom[:150],
                role=User.Role.FORMATEUR,
                matricule=formateur.numerobadge,
                is_active=True,
                must_change_password=True,
            )
            user.set_password(password)
            user.save()
            formateur.user = user
            formateur.save(update_fields=['user'])
            if send_email and user.email:
                _send_welcome_email_safe(user, password, mobile=True)
            return 'created'

    user.username = formateur.numerobadge
    user.email = formateur.email or ''
    user.first_name = formateur.prenom[:150]
    user.last_name = formateur.nom[:150]
    user.role = User.Role.FORMATEUR
    user.matricule = formateur.numerobadge
    user.is_active = True
    if reset_password:
        user.set_password(password)
        user.must_change_password = True
    user.save()
    return 'updated'


def provision_auditeur_accounts(
    participant_ids,
    *,
    password: str = DEFAULT_BADGE_PASSWORD,
    send_email: bool = True,
    reset_password: bool = False,
    log=None,
) -> dict:
    stats = _empty_stats()
    if not participant_ids:
        return stats

    participants = (
        Participant.objects.filter(pk__in=participant_ids)
        .select_related('user', 'secretariat')
        .order_by('nom', 'prenom', 'matricule')
    )

    for participant in participants:
        try:
            action = ensure_auditeur_account(
                participant,
                password=password,
                send_email=send_email,
                reset_password=reset_password,
            )
            stats[action] += 1
            if action == 'created' and send_email and participant.email:
                stats['emails_sent'] += 1
            if log and action in ('created', 'updated'):
                log(
                    f"  🔐 Compte auditeur {action} : {participant.matricule} "
                    f"({participant.prenom} {participant.nom})"
                )
        except Exception as exc:
            stats['errors'] += 1
            logger.exception(
                'provision_auditeur_accounts failed participant_id=%s matricule=%s',
                participant.pk,
                participant.matricule,
            )
            if log:
                log(f"  ❌ Compte auditeur impossible pour {participant.matricule} : {exc}")

    return stats


def provision_formateur_accounts(
    formateur_ids,
    *,
    password: str = DEFAULT_BADGE_PASSWORD,
    send_email: bool = True,
    reset_password: bool = False,
    log=None,
) -> dict:
    stats = _empty_stats()
    if not formateur_ids:
        return stats

    formateurs = (
        Formateur.objects.filter(pk__in=formateur_ids)
        .select_related('user')
        .order_by('nom', 'prenom', 'numerobadge')
    )

    for formateur in formateurs:
        try:
            action = ensure_formateur_account(
                formateur,
                password=password,
                send_email=send_email,
                reset_password=reset_password,
            )
            stats[action] += 1
            if action == 'created' and send_email and formateur.email:
                stats['emails_sent'] += 1
            if log and action in ('created', 'updated'):
                log(
                    f"  🔐 Compte formateur {action} : {formateur.numerobadge} "
                    f"({formateur.prenom} {formateur.nom})"
                )
        except Exception as exc:
            stats['errors'] += 1
            logger.exception(
                'provision_formateur_accounts failed formateur_id=%s badge=%s',
                formateur.pk,
                formateur.numerobadge,
            )
            if log:
                log(f"  ❌ Compte formateur impossible pour {formateur.numerobadge} : {exc}")

    return stats
