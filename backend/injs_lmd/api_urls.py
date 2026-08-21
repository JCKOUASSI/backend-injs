"""API v1 URL routing."""
from django.urls import path, include

urlpatterns = [
    path('auth/', include('apps.accounts.urls')),
    path('core/', include('apps.core.urls')),
    path('academics/', include('apps.academics.urls')),
    path('students/', include('apps.students.urls')),
    path('faculty/', include('apps.faculty.urls')),
    path('exams/', include('apps.exams.urls')),
    path('admissions/', include('apps.admissions.urls')),
    path('finance/', include('apps.finance.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('reports/', include('apps.reports.urls')),
    path('documents/', include('apps.documents.urls')),
    path('messaging/', include('apps.messaging.urls')),
    path('library/', include('apps.library.urls')),
]
