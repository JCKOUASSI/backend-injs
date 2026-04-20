from django.urls import path
from . import views

urlpatterns = [
    # Scan QR (participant — pas besoin d'auth)
    path('scan/', views.scan_view, name='scan'),

    # Scan sécurisé (app mobile — anti-fraude, auth requise)
    path('scan/secure/', views.secure_scan_view, name='secure-scan'),

    # Historique personnel (app mobile)
    path('me/historique/', views.my_historique, name='my-historique'),

    # Dashboard & présences (DFRC / Superviseur)
    path('formations/<int:pk>/dashboard/', views.formation_dashboard, name='formation-dashboard'),
    path('formations/<int:pk>/presences/', views.formation_presences, name='formation-presences'),
    path('formations/<int:pk>/force-pointage/', views.force_pointage, name='force-pointage'),
    path('formations/<int:pk>/close-session/', views.close_session, name='close-session'),

    # Offline badging data
    path('formations/<uuid:token>/offline-data/', views.formation_offline_data, name='formation-offline-data'),

    # Participant
    path('participant/<int:pk>/historique/', views.participant_historique, name='participant-historique'),
    path('participant/lookup/', views.participant_lookup, name='participant-lookup'),

    # Gestion liaisons appareils (superviseur / DFRC)
    path('devices/', views.list_device_bindings, name='device-bindings'),
    path('devices/<str:device_id>/unbind/', views.unbind_device, name='unbind-device'),

    # Journal d'audit (DFRC / Encadrant)
    path('audit-logs/', views.audit_log_list, name='audit-log-list'),

    # Vérification statut badgeage avant confirmation (public)
    path('scan/check-status/', views.check_badge_status, name='check-badge-status'),
]
