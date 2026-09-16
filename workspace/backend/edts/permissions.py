"""Permissions du lot L8 — Emploi du temps.

Gestion :
- Secrétariat, Chef Secrétariat, DFRC, DIRECTION, ADMIN pour la planification ;
- DIRECTION/ADMIN pour la validation et la publication ;
- Enseignants : lecture de leur propre emploi du temps.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from authentication.permissions import _has_role


PLANIFICATION_ROLES = (
    'ADMIN',
    'SECRETARIAT',
    'CHEF_SECRETARIAT',
    'DFRC',
    'DIRECTION',
    'ENCADRANT',
)

VALIDATION_ROLES = ('DIRECTION', 'ADMIN')


def _peut_planifier(user):
    return bool(user and user.is_authenticated and _has_role(user, *PLANIFICATION_ROLES))


def _peut_valider(user):
    return bool(user and user.is_authenticated and _has_role(user, *VALIDATION_ROLES))


class IsEdtPlanification(BasePermission):
    """Accès en écriture réservé aux rôles de planification."""

    def has_permission(self, request, view):
        return _peut_planifier(request.user)


class IsEdtValidation(BasePermission):
    """Validation et publication réservées à la Direction / Admin."""

    def has_permission(self, request, view):
        return _peut_valider(request.user)


class IsEdtReadOnlyOrPlanification(BasePermission):
    """Lecture pour tout authentifié ; écriture pour la planification."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return _peut_planifier(request.user)


class IsEdtEnseignantReadOnly(BasePermission):
    """Lecteur enseignant : peut voir les EDT publiés où il est affecté."""

    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return False
        return bool(request.user and request.user.is_authenticated)


class IsEnseignantOuReadOnly(BasePermission):
    """Enseignant peut lire ses propres affectations ; tout authentifié peut lire."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return _has_role(request.user, 'ENCADRANT')