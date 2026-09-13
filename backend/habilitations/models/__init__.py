"""Modèles de l'application ``habilitations`` (socle CURP, unité U1).

Répartis par fichier selon la chaîne :
PERSONNE → COMPTE → RÔLE / PERMISSION → PÉRIMÈTRE → ATTRIBUTIONS/DÉLÉGATIONS,
avec la politique de sécurité et le journal append-only chaîné.
"""
from .attribution import AttributionRole, PermissionAttribuee
from .compte import CompteUtilisateur
from .delegation import DelegationHabilitation
from .enums import (
    CanalAcces,
    DomaineMetier,
    NiveauAcces,
    SituationPersonne,
)
from .journal import (
    JournalHabilitation,
    JournalImmuableError,
    JournalQuerySet,
)
from .perimetre import Perimetre
from .permission import PermissionMetier
from .personne import Personne
from .politique import PolitiqueSecurite
from .role import RoleMetier

__all__ = [
    'Personne',
    'CompteUtilisateur',
    'RoleMetier',
    'PermissionMetier',
    'Perimetre',
    'AttributionRole',
    'PermissionAttribuee',
    'DelegationHabilitation',
    'PolitiqueSecurite',
    'JournalHabilitation',
    'JournalImmuableError',
    'JournalQuerySet',
    'NiveauAcces',
    'CanalAcces',
    'DomaineMetier',
    'SituationPersonne',
]
