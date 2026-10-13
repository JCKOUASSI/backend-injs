from django.urls import path
from .views import (
    DashboardView,
    SecretariatsStatsView,
    AlertesSeuilsView,
    RapportsListView,
    RapportDetailView,
    RapportWorkflowView,
    RapportNotificationsView,
    ObservationsView,
    BilanFACView,
    BilanFACPerimetreView,
    bilan_fac_export,
)

urlpatterns = [
    path('',                                          DashboardView.as_view(),          name='statistiques-dashboard'),
    path('secretariats/',                             SecretariatsStatsView.as_view(),  name='statistiques-secretariats'),
    path('alertes/seuils/',                           AlertesSeuilsView.as_view(),      name='statistiques-alertes-seuils'),
    path('rapports/',                                 RapportsListView.as_view(),       name='statistiques-rapports-list'),
    path('rapports/notifications/',                   RapportNotificationsView.as_view(), name='statistiques-rapports-notifications'),
    path('rapports/<int:rapport_id>/',                RapportDetailView.as_view(),      name='statistiques-rapport-detail'),
    path('rapports/<int:rapport_id>/workflow/',       RapportWorkflowView.as_view(),    name='statistiques-rapport-workflow'),
    path('rapports/<int:rapport_id>/observations/',   ObservationsView.as_view(),       name='statistiques-observations'),
    path('bilan-fac/',                                BilanFACView.as_view(),           name='statistiques-bilan-fac'),
    path('bilan-fac/perimetre/',                      BilanFACPerimetreView.as_view(),  name='statistiques-bilan-fac-perimetre'),
    path('bilan-fac-export/',                         bilan_fac_export,                 name='statistiques-bilan-fac-export'),
]
