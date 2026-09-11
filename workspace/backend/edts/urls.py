"""URLs API du lot L8 — Emploi du temps.

Préfixe : /api/edts/
"""

from django.urls import path

from . import api

urlpatterns = [
    path('creneaux-types/', api.creneau_templates_api, name='edt-creneau-templates'),
    path('creneaux-types/<int:pk>/', api.creneau_template_detail_api, name='edt-creneau-template-detail'),

    path('emplois/', api.emplois_du_temps_api, name='edt-emplois-list'),
    path('emplois/<int:pk>/', api.emploi_du_temps_detail_api, name='edt-emploi-detail'),
    path('emplois/<int:pk>/valider/', api.emploi_du_temps_valider_api, name='edt-emploi-valider'),
    path('emplois/<int:pk>/conflits/', api.emploi_du_temps_detecter_conflits_api, name='edt-emploi-detecter-conflits'),

    path('affectations/', api.affectations_api, name='edt-affectations'),
    path('affectations/<int:pk>/', api.affectation_detail_api, name='edt-affectation-detail'),

    path('conflits/', api.conflits_api, name='edt-conflits'),
    path('conflits/<int:pk>/resoudre/', api.conflit_resoudre_api, name='edt-conflit-resoudre'),

    path('publics/', api.edt_publics_api, name='edt-publics'),
]