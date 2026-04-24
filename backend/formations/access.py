"""
Helpers de contrôle d'accès aux formations, partagés entre les apps formations et presences.
Centraliser ici évite la duplication et garantit une logique cohérente dans tout le projet.
"""
from .models import Formation


def formation_accessible(user, pk):
    """
    Retourne la Formation si l'utilisateur est autorisé à y accéder, None sinon.

    Règles :
    - ENCADRANT              : au moins un module de la formation doit être supervisé par cet utilisateur.
    - SECRETARIAT /
      CHEF_SECRETARIAT       : au moins un module de la formation doit appartenir au secrétariat de l'utilisateur.
                               Si l'utilisateur n'est rattaché à aucun secrétariat → accès refusé.
    - CPFAE_ADMIN /
      CHEF_CPFAE_ADMIN /
      DIRECTION / ADMIN      : accès complet à toutes les formations.
    """
    if not (user and user.is_authenticated):
        return None

    if user.role == 'ENCADRANT':
        return (
            Formation.objects
            .filter(pk=pk, modules__superviseur=user)
            .distinct()
            .first()
        )

    if user.role in ('SECRETARIAT', 'CHEF_SECRETARIAT'):
        secretariat = getattr(user, 'secretariat', None)
        if not secretariat:
            return None
        return (
            Formation.objects
            .filter(pk=pk, modules__secretariat=secretariat)
            .distinct()
            .first()
        )

    # ADMIN, DFRC, DIRECTION → accès complet
    if user.role in ('ADMIN', 'CPFAE_ADMIN', 'CHEF_CPFAE_ADMIN', 'DIRECTION'):
        return Formation.objects.filter(pk=pk).first()

    # Rôle inconnu → refus
    return None
