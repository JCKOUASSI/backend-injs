from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.academics.views import (
    InstitutionViewSet, DepartmentViewSet, ProgramViewSet, PromotionViewSet,
    AcademicYearViewSet, SemesterViewSet, TeachingUnitViewSet,
    CourseViewSet, ProgramCourseViewSet, SpecializationViewSet,
    StapsJobNomenclatureViewSet,
)

router = DefaultRouter()
router.register('specializations', SpecializationViewSet)
router.register('job-nomenclatures', StapsJobNomenclatureViewSet)
router.register('institutions', InstitutionViewSet)
router.register('departments', DepartmentViewSet)
router.register('programs', ProgramViewSet)
router.register('promotions', PromotionViewSet)
router.register('academic-years', AcademicYearViewSet)
router.register('semesters', SemesterViewSet)
router.register('teaching-units', TeachingUnitViewSet)
router.register('courses', CourseViewSet)
router.register('program-courses', ProgramCourseViewSet)

urlpatterns = [path('', include(router.urls))]
