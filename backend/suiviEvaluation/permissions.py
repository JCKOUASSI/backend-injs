from rest_framework.permissions import BasePermission


ROLES_SUPERVISEUR = {'SUPERVISEUR', 'ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'}


class IsSuperviseur(BasePermission):
    """Encadrants, CPFAE_ADMIN et au-dessus peuvent gérer les questionnaires."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ROLES_SUPERVISEUR


class IsAuditeur(BasePermission):
    """Seuls les auditeurs peuvent soumettre des réponses."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'AUDITEUR'


class IsSuperviseurOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role in ROLES_SUPERVISEUR
