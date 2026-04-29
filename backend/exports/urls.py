from django.urls import path
from . import views

urlpatterns = [
    # Export par formation (toutes séances de tous les modules)
    path('formation/<int:pk>/pdf/', views.export_pdf, name='export-pdf'),
    path('formation/<int:pk>/excel/', views.export_excel, name='export-excel'),
    # Export par module (toutes séances d'un module spécifique)
    path('module/<int:module_pk>/pdf/', views.export_pdf_module, name='export-pdf-module'),
    path('module/<int:module_pk>/excel/', views.export_excel_module, name='export-excel-module'),
    # Export par session
    path('session/<int:session_pk>/pdf/', views.export_pdf_session, name='export-pdf-session'),
    path('session/<int:session_pk>/excel/', views.export_excel_session, name='export-pdf-session-excel'),
]
