"""Contrôle d'accès des endpoints React (formations/api_views.py)."""
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from authentication.role_groups import ALLOWED_WEB_ROLES
from authentication.permissions import IsDFRC, IsSecretariatOrDFRC, IsSecretariatOrEncadrantOrDFRC

from .access import formation_accessible
from .models import Module

# Réexport des classes DRF déjà utilisées ailleurs dans le projet.
__all__ = [
    'IsWebStaff',
    'CanListParticipants',
    'IsDFRC',
    'IsSecretariatOrDFRC',
    'IsSecretariatOrEncadrantOrDFRC',
    'formation_or_response',
    'module_or_response',
    'deny_if_not_formation_accessible',
]

PARTICIPANT_LIST_ROLES = frozenset({
    'ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'DIRECTION',
    'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT',
})


class IsWebStaff(BasePermission):
    """Refuse AUDITEUR / FORMATEUR et tout rôle hors plateforme web."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in ALLOWED_WEB_ROLES)


class CanListParticipants(BasePermission):
    """Liste auditeurs : pas FINANCE / FORMATEUR / AUDITEUR."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in PARTICIPANT_LIST_ROLES)


def formation_or_response(user, pk):
    """Retourne (formation, None) ou (None, Response 404)."""
    formation = formation_accessible(user, pk)
    if formation:
        return formation, None
    return None, Response({'detail': 'Formation introuvable ou non autorisée.'}, status=404)


def module_or_response(user, formation_pk, module_pk):
    """Retourne (formation, module, None) ou (None, None, Response)."""
    formation, err = formation_or_response(user, formation_pk)
    if err:
        return None, None, err
    try:
        module = Module.objects.get(pk=module_pk, formation=formation)
    except Module.DoesNotExist:
        return formation, None, Response({'detail': 'Module introuvable.'}, status=404)
    return formation, module, None


def deny_if_not_formation_accessible(user, pk):
    """Alias court pour les vues qui n'ont besoin que du garde-fou."""
    return formation_or_response(user, pk)
