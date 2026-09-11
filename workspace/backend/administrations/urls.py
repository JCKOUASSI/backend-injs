"""URLs API Administrations (lot L7)."""
from django.urls import path

from . import api

urlpatterns = [
    # Courriers
    path('courriers/', api.courriers_list_api, name='adm-courriers-list'),
    path('courriers/creer/', api.courrier_creer_api, name='adm-courrier-creer'),
    path('courriers/<int:pk>/transition/', api.courrier_transition_api, name='adm-courrier-transition'),
    # Documents officiels
    path('documents/', api.documents_list_api, name='adm-documents-list'),
    path('documents/creer/', api.document_creer_api, name='adm-document-creer'),
    path('documents/<int:pk>/transition/', api.document_transition_api, name='adm-document-transition'),
    # Réunions / commissions
    path('reunions/', api.reunions_api, name='adm-reunions'),
    path('reunions/<int:pk>/transition/', api.reunion_transition_api, name='adm-reunion-transition'),
    # Missions
    path('missions/', api.missions_api, name='adm-missions'),
    path('missions/<int:pk>/transition/', api.mission_transition_api, name='adm-mission-transition'),
]