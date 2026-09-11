from django.urls import path

from . import api

urlpatterns = [
    path('sessions/', api.session_list, name='api-jury-sessions'),
    path('sessions/<int:pk>/', api.session_detail, name='api-jury-session-detail'),
    path('sessions/<int:pk>/action/', api.session_action, name='api-jury-session-action'),
    path('sessions/<int:pk>/membres/', api.membre_ajout, name='api-jury-membre-ajout'),
    path('sessions/<int:pk>/decisions/', api.decision_saisie, name='api-jury-decision'),
    path('sessions/<int:pk>/pv/', api.pv_telechargement, name='api-jury-pv'),
    path('notifications/', api.notifications_jury, name='api-jury-notifications'),
]