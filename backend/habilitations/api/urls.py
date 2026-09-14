"""Routes de l'API d'habilitation (U2 + console U4), préfixe /api/habilitations/."""
from django.urls import path

from . import views
from . import views_admin
from . import views_admin_workflow as wf

urlpatterns = [
    # ── U2 ─────────────────────────────────────────────────────────────
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

    # ── U4 : console d'administration (drapeau flag.curp_ui_admin) ─────
    path('comptes/', views_admin.CompteListCreateView.as_view(), name='hab-comptes'),
    path(
        'comptes/import-simuler/',
        wf.ImportApercuView.as_view(), name='hab-comptes-import-simuler',
    ),
    path(
        'comptes/revue/',
        wf.RevueConsultationView.as_view(), name='hab-revue',
    ),
    path('personnes/', views_admin.PersonneRechercheView.as_view(), name='hab-personnes'),
    path('comptes/<int:pk>/', views_admin.CompteDetailView.as_view(), name='hab-compte-detail'),
    path(
        'comptes/<int:pk>/simuler-modification/',
        views_admin.CompteDifferentialView.as_view(), name='hab-compte-differential',
    ),
    path(
        'comptes/<int:pk>/modifier/',
        views_admin.CompteModifierView.as_view(), name='hab-compte-modifier',
    ),
    path(
        'comptes/<int:pk>/statut/',
        views_admin.CompteStatutView.as_view(), name='hab-compte-statut',
    ),
    path('roles/<str:code>/', views_admin.RoleDetailView.as_view(), name='hab-role-detail'),
    path('matrice/', views_admin.MatriceView.as_view(), name='hab-matrice'),
    path('journal/', views_admin.JournalView.as_view(), name='hab-journal'),
    path(
        'journal/integrite/',
        views_admin.JournalIntegriteView.as_view(), name='hab-journal-integrite',
    ),
    path('derogations/', wf.DerogationListCreateView.as_view(), name='hab-derogations'),
    path(
        'derogations/<int:pk>/revoquer/',
        wf.DerogationRevokeView.as_view(), name='hab-derogation-revoquer',
    ),
    path('delegations/', wf.DelegationListCreateView.as_view(), name='hab-delegations'),
    path(
        'delegations/<int:pk>/terminer/',
        wf.DelegationTerminateView.as_view(), name='hab-delegation-terminer',
    ),
]
