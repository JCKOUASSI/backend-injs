"""Routes de l'API d'habilitation (unité U2), préfixe ``/api/habilitations/``."""
from django.urls import path

from . import views

urlpatterns = [
    path('mes-acces/', views.mes_acces_view, name='hab-mes-acces'),
    path('evaluer/', views.EvaluerView.as_view(), name='hab-evaluer'),
    path(
        'observations/synthese/',
        views.ObservationsSyntheseView.as_view(),
        name='hab-observations-synthese',
    ),
    path(
        'observations/remettre-a-zero/',
        views.ObservationsResetView.as_view(),
        name='hab-observations-reset',
    ),
    path('roles/', views.RoleListView.as_view(), name='hab-roles'),
    path('permissions/', views.PermissionListView.as_view(), name='hab-permissions'),
]
