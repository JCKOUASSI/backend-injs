"""Vues DRF du module EPT-INJS."""
from .badge import BadgeViewSet
from .cours import CoursViewSet
from .planning import SeanceViewSet
from .programme import ProgrammePeriodeViewSet
from .referentiel import (
    GroupePedagogiqueViewSet,
    JourFerieViewSet,
    ParametresPlanificationViewSet,
    PeriodeFormationViewSet,
    PlanningRunViewSet,
)

__all__ = [
    'BadgeViewSet',
    'CoursViewSet',
    'GroupePedagogiqueViewSet',
    'JourFerieViewSet',
    'ParametresPlanificationViewSet',
    'PeriodeFormationViewSet',
    'PlanningRunViewSet',
    'ProgrammePeriodeViewSet',
    'SeanceViewSet',
]
