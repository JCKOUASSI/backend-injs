"""URLs API du module GET-INJS (lot L8) — Emploi du temps.

Préfixe : /api/edts/. L'alias /api/timetable/ (exigence P11) est monté dans
config/urls.py sur le même jeu de routes — les deux chemins sont équivalents
et versionnés ensemble.
"""

from django.urls import path

from . import api

# Pas d'app_name volontaire : le jeu de routes est monté deux fois
# (/api/edts/ et /api/timetable/) — un namespace dupliqué déclenche urls.W005.
urlpatterns = [
    # Référentiel horaire (P01)
    path('creneaux-types/', api.creneaux_types_api, name='edt-creneau-templates'),
    path('creneaux-types/<int:pk>/', api.creneau_template_detail_api, name='edt-creneau-template-detail'),

    # Emplois du temps + workflow (P05)
    path('emplois/', api.emplois_du_temps_api, name='edt-emplois-list'),
    path('emplois/<int:pk>/', api.emploi_du_temps_detail_api, name='edt-emploi-detail'),
    path('emplois/<int:pk>/soumettre/', api.emploi_du_temps_soumettre_api, name='edt-emploi-soumettre'),
    path('emplois/<int:pk>/valider/', api.emploi_du_temps_valider_api, name='edt-emploi-valider'),
    path('emplois/<int:pk>/publier/', api.emploi_du_temps_publier_api, name='edt-emploi-publier'),
    path('emplois/<int:pk>/depublier/', api.emploi_du_temps_depublier_api, name='edt-emploi-depublier'),
    path('emplois/<int:pk>/archiver/', api.emploi_du_temps_archiver_api, name='edt-emploi-archiver'),
    path('emplois/<int:pk>/generer/', api.emploi_du_temps_generer_api, name='edt-emploi-generer'),
    path('emplois/<int:pk>/grille/', api.emploi_du_temps_grille_api, name='edt-emploi-grille'),
    path('emplois/<int:pk>/export.csv/', api.emploi_du_temps_export_api, name='edt-emploi-export-csv'),
    path('emplois/<int:pk>/conflits/', api.emploi_du_temps_detecter_conflits_api,
         name='edt-emploi-detecter-conflits'),

    # Placements (P05, P08)
    path('affectations/', api.affectations_api, name='edt-affectations'),
    path('affectations/<int:pk>/', api.affectation_detail_api, name='edt-affectation-detail'),
    path('affectations/<int:pk>/deplacer/', api.affectation_deplacer_api, name='edt-affectation-deplacer'),

    # Conflits (P07)
    path('conflits/', api.conflits_api, name='edt-conflits'),
    path('conflits/<int:pk>/resoudre/', api.conflit_resoudre_api, name='edt-conflit-resoudre'),

    # Lecture allégée & annuaires pour sélecteurs
    path('publics/', api.edt_publics_api, name='edt-publics'),
    path('referentiel-enseignants/', api.referentiel_enseignants_api, name='edt-referentiel-enseignants'),
]
