from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from apps.exams.models import ExamSession, Evaluation, Grade, Deliberation, Jury, Defense
from apps.exams.serializers import (
    ExamSessionSerializer, EvaluationSerializer, GradeSerializer,
    DeliberationSerializer, JurySerializer, DefenseSerializer,
)
from apps.exams.services.lmd_engine import run_deliberation, calculate_ue_average
from apps.core.mixins import ExportMixin


class ExamSessionViewSet(viewsets.ModelViewSet):
    queryset = ExamSession.objects.select_related('academic_year', 'semester').all()
    serializer_class = ExamSessionSerializer
    permission_module = 'exams'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['academic_year', 'semester', 'session_type']


class EvaluationViewSet(viewsets.ModelViewSet):
    queryset = Evaluation.objects.select_related('teaching_unit', 'exam_session').all()
    serializer_class = EvaluationSerializer
    permission_module = 'exams'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['teaching_unit', 'exam_session', 'evaluation_type']


class GradeViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Grade.objects.select_related(
        'student', 'student__user', 'evaluation',
        'evaluation__teaching_unit', 'evaluation__course',
    ).all()
    serializer_class = GradeSerializer
    permission_module = 'exams'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'evaluation']
    export_headers = ['Matricule', 'Étudiant', 'Évaluation', 'Note']
    export_title = 'Notes INJS'
    export_filename = 'notes_injs'

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)

    def get_export_rows(self):
        return [
            [g.student.matricule, g.student.user.get_full_name(), g.evaluation.name, g.score or 'ABS']
            for g in self.filter_queryset(self.get_queryset())
        ]


class DeliberationViewSet(viewsets.ModelViewSet):
    queryset = Deliberation.objects.select_related('exam_session', 'program', 'promotion').all()
    serializer_class = DeliberationSerializer
    permission_module = 'exams'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['exam_session', 'program', 'promotion', 'status']

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        deliberation = self.get_object()
        summary = run_deliberation(deliberation)
        return Response(summary)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        deliberation = self.get_object()
        deliberation.status = 'validated'
        deliberation.validated_by = request.user
        deliberation.deliberation_date = timezone.now()
        deliberation.save()
        run_deliberation(deliberation)
        return Response(DeliberationSerializer(deliberation).data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        deliberation = self.get_object()
        deliberation.status = 'published'
        deliberation.save()
        deliberation.exam_session.results_published = True
        deliberation.exam_session.save()
        return Response({'message': 'Résultats publiés'})


class JuryViewSet(viewsets.ModelViewSet):
    queryset = Jury.objects.select_related('member', 'deliberation').all()
    serializer_class = JurySerializer
    permission_module = 'exams'


class DefenseViewSet(viewsets.ModelViewSet):
    queryset = Defense.objects.select_related('student', 'room').all()
    serializer_class = DefenseSerializer
    permission_module = 'exams'
