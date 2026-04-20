from django.urls import path
from . import views

urlpatterns = [
    # Export par formation
    path('formation/<int:pk>/pdf/', views.export_pdf, name='export-pdf'),
    path('formation/<int:pk>/excel/', views.export_excel, name='export-excel'),
    # Export par session
    path('session/<int:session_pk>/pdf/', views.export_pdf_session, name='export-pdf-session'),
    path('session/<int:session_pk>/excel/', views.export_excel_session, name='export-excel-session'),
]
