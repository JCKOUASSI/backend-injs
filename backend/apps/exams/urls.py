from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.exams.views import (
    ExamSessionViewSet, EvaluationViewSet, GradeViewSet,
    DeliberationViewSet, JuryViewSet, DefenseViewSet,
)

router = DefaultRouter()
router.register('sessions', ExamSessionViewSet)
router.register('evaluations', EvaluationViewSet)
router.register('grades', GradeViewSet)
router.register('deliberations', DeliberationViewSet)
router.register('juries', JuryViewSet)
router.register('defenses', DefenseViewSet)

urlpatterns = [path('', include(router.urls))]
