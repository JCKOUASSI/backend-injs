from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.students.views import StudentViewSet, EnrollmentViewSet, AcademicRecordViewSet

router = DefaultRouter()
# Routes nommées avant la route générique '' pour éviter que « enrollments » soit pris pour un UUID.
router.register('enrollments', EnrollmentViewSet, basename='enrollment')
router.register('academic-records', AcademicRecordViewSet, basename='academic-record')
router.register('', StudentViewSet, basename='student')

urlpatterns = [path('', include(router.urls))]
