from rest_framework.permissions import BasePermission

from authentication.role_groups import ROLE_GROUP_NAMES

# Hiérarchie stricte : index bas = rang élevé
ROLE_HIERARCHY = ['ADMIN', 'DIRECTION', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'FINANCE', 'ENCADRANT', 'AUDITEUR']


def _cached_user_groups(user):
    """Retourne le set de noms de groupes de l'utilisateur.

    Mis en cache sur l'objet user pour la durée de la requête afin
    d'éviter une requête DB par appel à has_permission().
    """
    if not hasattr(user, '_role_groups_cache'):
        user._role_groups_cache = set(user.groups.values_list('name', flat=True))
    return user._role_groups_cache


def _in_groups(user, *roles):
    """Vérifie si l'utilisateur appartient au groupe de rôle d'au moins un des rôles donnés."""
    target = {ROLE_GROUP_NAMES[r] for r in roles if r in ROLE_GROUP_NAMES}
    return bool(_cached_user_groups(user) & target)


def _model_perm(request, app_label, model_name):
    """Vérifie la permission Django correspondant à la méthode HTTP et au modèle donné.

    Utilise has_perm() qui consulte les permissions des groupes de l'utilisateur.
    Les permissions sont mises en cache par Django après le premier appel.
    """
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        codename = f'{app_label}.view_{model_name}'
    elif request.method == 'POST':
        codename = f'{app_label}.add_{model_name}'
    elif request.method in ('PUT', 'PATCH'):
        codename = f'{app_label}.change_{model_name}'
    elif request.method == 'DELETE':
        codename = f'{app_label}.delete_{model_name}'
    else:
        return False
    return request.user.has_perm(codename)


class HasFormationsPerm(BasePermission):
    """Classe de base : vérifie la permission Django sur un modèle de l'app formations.

    Utilise has_perm() qui consulte les permissions réelles du groupe de l'utilisateur,
    respectant ainsi les changements effectués dans l'admin Django ou via ROLE_POLICY.
    Les sous-classes définissent `model_name` pour cibler un modèle précis.
    """
    model_name = None  # À surcharger dans les sous-classes

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return _model_perm(request, 'formations', self.model_name)


class CanManageParticipant(HasFormationsPerm):
    """Permission basée sur les droits réels du groupe pour le modèle Participant."""
    model_name = 'participant'


class CanManageModuleParticipant(HasFormationsPerm):
    """Permission basée sur les droits réels du groupe pour l'inscription d'un participant à un module."""
    model_name = 'moduleparticipant'


def get_subordinate_roles(role):
    """Retourne les rôles strictement inférieurs au rôle donné."""
    if role not in ROLE_HIERARCHY:
        return []
    idx = ROLE_HIERARCHY.index(role)
    return ROLE_HIERARCHY[idx + 1:]


def get_creatable_roles(role):
    """Retourne les rôles qu'un utilisateur peut créer.
    Même chose que get_subordinate_roles, sauf CHEF_CPFAE_ADMIN qui peut aussi créer DIRECTION."""
    subordinates = get_subordinate_roles(role)
    if role == 'CHEF_CPFAE_ADMIN' and 'DIRECTION' not in subordinates:
        subordinates = ['DIRECTION'] + subordinates
    return subordinates


class IsDFRC(BasePermission):
    """ADMIN/CHEF_CPFAE_ADMIN/CPFAE_ADMIN : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if _in_groups(request.user, 'ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'):
            return True
        if _in_groups(request.user, 'DIRECTION') and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return False


class IsDFRCOrEncadrant(BasePermission):
    """ADMIN/CHEF_CPFAE_ADMIN/CPFAE_ADMIN/Encadrant : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if _in_groups(request.user, 'ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'ENCADRANT'):
            return True
        if _in_groups(request.user, 'DIRECTION') and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return False


class IsParticipantOrReadOnly(BasePermission):
    """Participant peut lire ses propres données."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsSecretariat(BasePermission):
    """Accès réservé aux secrétariats et chef secrétariat."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and _in_groups(request.user, 'SECRETARIAT', 'CHEF_SECRETARIAT')
        )


class IsEncadrant(BasePermission):
    """Accès réservé aux encadrants."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and _in_groups(request.user, 'ENCADRANT')
        )


class IsSecretariatOrEncadrant(BasePermission):
    """Secrétariat, Chef Secrétariat et Encadrant."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and _in_groups(request.user, 'SECRETARIAT', 'CHEF_SECRETARIAT', 'ENCADRANT')
        )


class IsSecretariatOrDFRC(BasePermission):
    """ADMIN/Secrétariat/DFRC : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if _in_groups(request.user, 'ADMIN', 'SECRETARIAT', 'CHEF_SECRETARIAT', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'):
            return True
        if _in_groups(request.user, 'DIRECTION') and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return False


class IsSecretariatOrEncadrantOrDFRC(BasePermission):
    """ADMIN, Secrétariat, Chef Secrétariat, Encadrant, CPFAE_ADMIN, Chef CPFAE_ADMIN : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if _in_groups(request.user, 'ADMIN', 'SECRETARIAT', 'CHEF_SECRETARIAT', 'ENCADRANT', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'):
            return True
        if _in_groups(request.user, 'DIRECTION') and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return False
