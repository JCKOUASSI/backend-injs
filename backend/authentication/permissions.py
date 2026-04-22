from rest_framework.permissions import BasePermission

# Hiérarchie stricte : index bas = rang élevé
ROLE_HIERARCHY = ['ADMIN', 'DIRECTION', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'AUDITEUR']


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
    """CHEF_CPFAE_ADMIN/CPFAE_ADMIN : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'):
            return True
        if request.user.role == 'DIRECTION' and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return False


class IsDFRCOrEncadrant(BasePermission):
    """CHEF_CPFAE_ADMIN/CPFAE_ADMIN/Encadrant : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'ENCADRANT'):
            return True
        if request.user.role == 'DIRECTION' and request.method in ('GET', 'HEAD', 'OPTIONS'):
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
            and request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT')
        )


class IsEncadrant(BasePermission):
    """Accès réservé aux encadrants."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'ENCADRANT'
        )


class IsSecretariatOrEncadrant(BasePermission):
    """Secrétariat, Chef Secrétariat et Encadrant : accès en lecture."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT', 'ENCADRANT')
        )


class IsSecretariatOrDFRC(BasePermission):
    """Secrétariat/DFRC : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'):
            return True
        if request.user.role == 'DIRECTION' and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return False


class IsSecretariatOrEncadrantOrDFRC(BasePermission):
    """Secrétariat, Chef Secrétariat, Encadrant, CPFAE_ADMIN, Chef CPFAE_ADMIN : accès complet. Direction : lecture seule."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT', 'ENCADRANT', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'):
            return True
        if request.user.role == 'DIRECTION' and request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return False
