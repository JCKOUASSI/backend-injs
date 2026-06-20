from rest_framework.permissions import BasePermission


ROLES_SUPERVISEUR = {'SUPERVISEUR', 'ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN'}

# Aligné sur frontend EVALUATION_ALLOWED_ROLES
ROLES_GESTION_QUESTIONNAIRES = ROLES_SUPERVISEUR | {
    'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT',
}

# Rôles autorisés à saisir/gérer les notes et épreuves
ROLES_GESTION_NOTES = {
    'ADMIN', 'DIRECTION', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN',
    'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'SUPERVISEUR',
}

# Rôles autorisés à valider les décisions pédagogiques
ROLES_DECISION = {
    'ADMIN', 'DIRECTION', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'ENCADRANT', 'SUPERVISEUR',
}

# Rôles ayant accès en lecture aux fiches/tableaux de bord
ROLES_CONSULTATION = ROLES_GESTION_NOTES | {'FINANCE', 'ARCHIVE'}

# Export des fiches et relevés (archiviste : export global)
ROLES_FICHE_EXPORT = ROLES_GESTION_NOTES | {'ARCHIVE'}


class IsSuperviseur(BasePermission):
    """Secrétariat, encadrants, superviseurs et admins peuvent gérer les questionnaires."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ROLES_GESTION_QUESTIONNAIRES


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
        return request.user.role in ROLES_GESTION_QUESTIONNAIRES


class IsGestionNotes(BasePermission):
    """Secrétariat, encadrants et au-dessus peuvent saisir/gérer les notes."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ROLES_GESTION_NOTES


class IsGestionNotesOrReadOnly(BasePermission):
    """Lecture pour tous les rôles de consultation, écriture pour gestion notes."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user.role in ROLES_CONSULTATION
        return request.user.role in ROLES_GESTION_NOTES


class IsDecisionValidator(BasePermission):
    """Direction/encadrants peuvent valider les décisions pédagogiques."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user.role in ROLES_CONSULTATION
        return request.user.role in ROLES_DECISION
