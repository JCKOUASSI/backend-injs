"""Routes de l'API d'habilitation (U2 + console U4), préfixe /api/habilitations/."""
from django.urls import path

from . import views
from . import views_admin
from . import views_admin_cycle as vc
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

    # ── U5 : cycle de vie, file de provisionnement, imports et délégation ──
    path(
        'propositions/',
        vc.PropositionListView.as_view(), name='hab-propositions',
    ),
    path(
        'propositions/<int:pk>/approuver/',
        vc.PropositionApprouverView.as_view(), name='hab-proposition-approuver',
    ),
    path(
        'propositions/<int:pk>/rejeter/',
        vc.PropositionRejeterView.as_view(), name='hab-proposition-rejeter',
    ),
    path(
        'provisions/scanner/',
        vc.ProvisionScanView.as_view(), name='hab-provisions-scanner',
    ),
    path(
        'comptes/imports/',
        vc.ImportExecuterView.as_view(), name='hab-comptes-imports-executer',
    ),
    path(
        'comptes/imports/<str:reference>/',
        vc.ImportDetailView.as_view(), name='hab-comptes-import-detail',
    ),
    path(
        'comptes/imports/<str:reference>/annuler/',
        vc.ImportAnnulerView.as_view(), name='hab-comptes-import-annuler',
    ),
    path(
        'notifications/',
        vc.NotificationListView.as_view(), name='hab-notifications',
    ),
    path(
        'notifications/tout-lire/',
        vc.NotificationToutLireView.as_view(), name='hab-notifications-tout-lire',
    ),
    path(
        'notifications/<int:pk>/lire/',
        vc.NotificationLireView.as_view(), name='hab-notification-lire',
    ),
    path(
        'delegations/<int:pk>/activer/',
        vc.DelegationActiverView.as_view(), name='hab-delegation-activer',
    ),
    path(
        'delegations/<int:pk>/action/',
        vc.DelegationActionView.as_view(), name='hab-delegation-action',
    ),
]
