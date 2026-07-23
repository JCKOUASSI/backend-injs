from django.urls import path
from apps.reports.views import AnalyticsDashboardView, TranscriptPDFView, TranscriptSummaryView

urlpatterns = [
    path('analytics/', AnalyticsDashboardView.as_view(), name='analytics'),
    path('transcript/<uuid:student_id>/pdf/', TranscriptPDFView.as_view(), name='transcript-pdf'),
    path('transcript/<uuid:student_id>/summary/', TranscriptSummaryView.as_view(), name='transcript-summary'),
]
