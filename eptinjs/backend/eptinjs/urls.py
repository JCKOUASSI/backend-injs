"""Routage API du module EPT-INJS, monté sur ``/api/v1/eptinjs/``."""
from rest_framework.routers import DefaultRouter

from .views import (
    BadgeViewSet,
    CoursViewSet,
    GroupePedagogiqueViewSet,
    JourFerieViewSet,
    ParametresPlanificationViewSet,
    PeriodeFormationViewSet,
    PlanningRunViewSet,
    ProgrammePeriodeViewSet,
    SeanceViewSet,
)

router = DefaultRouter()
router.register('periodes', PeriodeFormationViewSet, basename='eptinjs-periode')
router.register('parametres', ParametresPlanificationViewSet, basename='eptinjs-parametres')
router.register('jours-feries', JourFerieViewSet, basename='eptinjs-jour-ferie')
router.register('groupes', GroupePedagogiqueViewSet, basename='eptinjs-groupe')
router.register('programmes', ProgrammePeriodeViewSet, basename='eptinjs-programme')
router.register('seances', SeanceViewSet, basename='eptinjs-seance')
router.register('runs', PlanningRunViewSet, basename='eptinjs-run')
router.register('cours', CoursViewSet, basename='eptinjs-cours')
router.register('badge', BadgeViewSet, basename='eptinjs-badge')

urlpatterns = router.urls
