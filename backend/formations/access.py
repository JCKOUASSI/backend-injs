"""
Helpers de contrôle d'accès aux formations, partagés entre les apps formations et presences.
Centraliser ici évite la duplication et garantit une logique cohérente dans tout le projet.
"""
from django.db.models import Q

from authentication.role_groups import (
    DASHBOARD_SECRETARIAT_FILTER_ROLES,
    GLOBAL_ACCESS_ROLES,
    SECRETARIAT_ROLES,
    get_user_role,
    user_has_perm,
)

from .models import Formation, Module, Participant, Formateur


def formation_accessible(user, pk):
    """
    Retourne la Formation si l'utilisateur est autorisé à y accéder, None sinon.

    Règles :
    - AUDITEUR               : au moins un module de la formation doit contenir le participant lié à cet utilisateur.
    - ENCADRANT              : au moins un module de la formation doit être supervisé par cet utilisateur.
    - SECRETARIAT /
      CHEF_SECRETARIAT       : au moins un module de la formation doit appartenir au secrétariat de l'utilisateur.
                               Si l'utilisateur n'est rattaché à aucun secrétariat → accès refusé.
    - CPFAE_ADMIN /
      CHEF_CPFAE_ADMIN /
      DIRECTION / ARCHIVE / ADMIN      : accès complet à toutes les formations.
    - FINANCE                : accès refusé ici (module finance dédié).
    """
    if not (user and user.is_authenticated):
        return None

    role = get_user_role(user)

    if role == 'ENCADRANT':
        return (
            Formation.objects
            .filter(pk=pk, modules__superviseur=user)
            .distinct()
            .first()
        )

    if role in SECRETARIAT_ROLES:
        secretariat = getattr(user, 'secretariat', None)
        if not secretariat:
            return None
        return (
            Formation.objects
            .filter(pk=pk, modules__secretariat=secretariat)
            .distinct()
            .first()
        )

    if role == 'AUDITEUR':
        return (
            Formation.objects
            .filter(pk=pk, modules__module_participants__participant__user=user)
            .distinct()
            .first()
        )

    if role in GLOBAL_ACCESS_ROLES or user_has_perm(user, 'authentication.global_scope'):
        return Formation.objects.filter(pk=pk).first()

    return None


def modules_queryset_for_user(user, queryset=None):
    """Modules visibles selon le périmètre opérationnel de l'utilisateur."""
    qs = queryset if queryset is not None else Module.objects.all()
    if not (user and user.is_authenticated):
        return qs.none()
    role = get_user_role(user)
    if role in SECRETARIAT_ROLES:
        if user.secretariat:
            return qs.filter(secretariat=user.secretariat)
        return qs.none()
    if role == 'ENCADRANT':
        return qs.filter(superviseur=user)
    if role in GLOBAL_ACCESS_ROLES or user_has_perm(user, 'authentication.global_scope'):
        return qs
    if role == 'FINANCE':
        return qs.none()
    return qs


def participants_queryset_for_user(user, queryset=None):
    """Participants visibles selon le périmètre opérationnel de l'utilisateur."""
    qs = queryset if queryset is not None else Participant.objects.all()
    if not (user and user.is_authenticated):
        return qs.none()
    role = get_user_role(user)
    if role in SECRETARIAT_ROLES:
        if user.secretariat:
            return qs.filter(
                Q(secretariat=user.secretariat)
                | Q(modules_inscrits__module__secretariat=user.secretariat)
            ).distinct()
        return qs.filter(secretariat__isnull=True)
    if role == 'ENCADRANT':
        return qs.filter(
            modules_inscrits__module__superviseur=user
        ).distinct()
    if role in GLOBAL_ACCESS_ROLES or user_has_perm(user, 'authentication.global_scope'):
        return qs
    if role == 'FINANCE':
        return qs.none()
    return qs


def participant_accessible(user, pk):
    """Retourne le Participant si l'utilisateur est autorisé à le consulter."""
    if not (user and user.is_authenticated):
        return None
    return participants_queryset_for_user(user).filter(pk=pk).first()


def formateurs_queryset_for_user(user, queryset=None):
    """Formateurs visibles selon le périmètre opérationnel de l'utilisateur."""
    qs = queryset if queryset is not None else Formateur.objects.all()
    if not (user and user.is_authenticated):
        return qs.none()
    role = get_user_role(user)
    if role in SECRETARIAT_ROLES:
        sec = user.secretariat
        if not sec:
            return qs.none()
        return qs
    if role == 'ENCADRANT':
        return qs.filter(
            modules_assignes__module__superviseur=user
        ).distinct()
    if role in GLOBAL_ACCESS_ROLES or user_has_perm(user, 'authentication.global_scope'):
        return qs
    if role == 'FINANCE':
        return qs.none()
    return qs


def can_filter_modules_by_secretariat(user):
    """Indique si l'utilisateur peut appliquer un filtre secrétariat sur les listes modules."""
    role = get_user_role(user)
    return role in DASHBOARD_SECRETARIAT_FILTER_ROLES or user_has_perm(user, 'authentication.global_scope')
