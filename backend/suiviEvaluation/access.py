"""Périmètre d'accès aux questionnaires d'évaluation."""
from django.db.models import Q

from authentication.role_groups import GLOBAL_ACCESS_ROLES, SECRETARIAT_ROLES
from formations.access import modules_queryset_for_user

from .models import Questionnaire


def _scoped_module_intitules(user):
    return set(modules_queryset_for_user(user).values_list('intitule', flat=True))


def questionnaire_accessible(user, questionnaire):
    """True si l'utilisateur peut consulter / modifier ce questionnaire."""
    if not user or not user.is_authenticated:
        return False
    if user.role in GLOBAL_ACCESS_ROLES or user.role == 'SUPERVISEUR':
        return True
    if user.role in SECRETARIAT_ROLES or user.role == 'ENCADRANT':
        if questionnaire.module_id:
            return modules_queryset_for_user(user).filter(pk=questionnaire.module_id).exists()
        titres = set(questionnaire.titres or [])
        scoped = _scoped_module_intitules(user)
        if not scoped:
            return False
        if not titres:
            return False
        return bool(titres & scoped)
    return False


def questionnaires_queryset_for_user(user, queryset=None):
    """Questionnaires visibles selon le périmètre opérationnel."""
    qs = queryset if queryset is not None else Questionnaire.objects.all()
    if not user or not user.is_authenticated:
        return qs.none()
    if user.role in GLOBAL_ACCESS_ROLES or user.role == 'SUPERVISEUR':
        return qs
    if user.role in SECRETARIAT_ROLES or user.role == 'ENCADRANT':
        scoped_modules = modules_queryset_for_user(user)
        module_ids = list(scoped_modules.values_list('pk', flat=True))
        intitules = _scoped_module_intitules(user)
        if not intitules:
            return qs.none()

        scoped = qs.filter(
            Q(module_id__in=module_ids)
            | Q(module__isnull=True)
        )
        null_module_ids = [
            qid for qid, titres in scoped.filter(module__isnull=True).values_list('id', 'titres')
            if set(titres or []) & intitules
        ]
        return qs.filter(
            Q(module_id__in=module_ids)
            | Q(id__in=null_module_ids)
        ).distinct()
    return qs.none()


def titres_dans_perimetre(user, titres):
    """Vérifie que tous les titres ciblés appartiennent au périmètre de l'utilisateur."""
    if user.role in GLOBAL_ACCESS_ROLES or user.role == 'SUPERVISEUR':
        return True
    if user.role in SECRETARIAT_ROLES or user.role == 'ENCADRANT':
        scoped = _scoped_module_intitules(user)
        if not scoped:
            return False
        return bool(titres) and set(titres).issubset(scoped)
    return False
