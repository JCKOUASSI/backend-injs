from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from django.utils import timezone

from apps.students.models import Student, Enrollment, AcademicRecord
from apps.students.serializers import StudentSerializer, EnrollmentSerializer, AcademicRecordSerializer
from apps.core.mixins import ExportMixin
from apps.exams.services.lmd_engine import calculate_semester_average


class StudentViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Student.objects.select_related('user', 'program', 'promotion', 'specialization').all()
    serializer_class = StudentSerializer
    permission_module = 'students'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['program', 'promotion', 'status', 'gender']
    search_fields = ['matricule', 'user__first_name', 'user__last_name', 'user__email']
    ordering_fields = ['matricule', 'user__last_name', 'enrollment_date', 'status']
    ordering = ['matricule']
    export_headers = ['Matricule', 'Nom', 'Prénom', 'Filière', 'Promotion', 'Statut']
    export_title = 'Étudiants INJS'
    export_filename = 'etudiants_injs'

    def get_export_rows(self):
        return [
            [s.matricule, s.user.last_name, s.user.first_name, s.program.name, s.promotion.name, s.get_status_display()]
            for s in self.filter_queryset(self.get_queryset())
        ]

    @action(detail=False, methods=['get'], url_path='meta')
    def meta(self, request):
        """Référentiels + compteurs pour filtres (style salles)."""
        qs = self.get_queryset()
        by_program = {
            str(row['program']): row['c']
            for row in qs.values('program').annotate(c=Count('id'))
            if row['program']
        }
        by_promotion = {
            str(row['promotion']): row['c']
            for row in qs.values('promotion').annotate(c=Count('id'))
            if row['promotion']
        }
        by_status = {
            row['status']: row['c']
            for row in qs.values('status').annotate(c=Count('id'))
        }
        by_gender = {
            (row['gender'] or ''): row['c']
            for row in qs.values('gender').annotate(c=Count('id'))
        }

        from apps.academics.models import Program, Promotion
        programs = [
            {
                'id': str(p.id),
                'code': p.code,
                'name': p.name,
                'count': by_program.get(str(p.id), 0),
            }
            for p in Program.objects.filter(is_active=True).order_by('code')
        ]
        promotions = [
            {
                'id': str(pr.id),
                'name': pr.name,
                'program': str(pr.program_id),
                'program_code': pr.program.code,
                'count': by_promotion.get(str(pr.id), 0),
            }
            for pr in Promotion.objects.filter(is_active=True).select_related('program').order_by('program__code', 'name')
            if by_promotion.get(str(pr.id), 0) > 0
        ]

        return Response({
            'statuses': [{'value': v, 'label': l} for v, l in Student._meta.get_field('status').choices],
            'genders': [{'value': 'M', 'label': 'Hommes'}, {'value': 'F', 'label': 'Femmes'}],
            'programs': programs,
            'promotions': promotions,
            'counts': {
                'total': qs.count(),
                'by_program': by_program,
                'by_promotion': by_promotion,
                'by_status': by_status,
                'by_gender': by_gender,
                'men': by_gender.get('M', 0),
                'women': by_gender.get('F', 0),
            },
        })

    @action(detail=True, methods=['get'])
    def academic_summary(self, request, pk=None):
        student = self.get_object()
        from apps.exams.models import ExamSession
        session = ExamSession.objects.filter(is_open=False, results_published=True).first()
        if not session:
            return Response({'message': 'Aucune session publiée'})
        result = calculate_semester_average(student, session.semester, session)
        return Response(result)

    @action(detail=True, methods=['get'])
    def career_path(self, request, pk=None):
        student = self.get_object()
        from apps.academics.services.nomenclature import resolve_job_nomenclature
        from apps.academics.serializers import StapsJobNomenclatureSerializer

        entry = resolve_job_nomenclature(student)
        if not entry:
            return Response({
                'message': 'Aucune nomenclature emploi trouvée pour ce parcours',
                'specialization': student.specialization.code if student.specialization_id else None,
                'program_track': student.program.track,
            })
        return Response(StapsJobNomenclatureSerializer(entry).data)

    @action(detail=True, methods=['get'])
    def card(self, request, pk=None):
        student = self.get_object()
        return Response({
            'matricule': student.matricule,
            'full_name': student.user.get_full_name(),
            'program': student.program.name,
            'promotion': student.promotion.name,
            'photo_url': StudentSerializer(student, context={'request': request}).data.get('photo_url'),
            'qr_code_url': StudentSerializer(student, context={'request': request}).data.get('qr_code_url'),
            'institution': 'INJS - Côte d\'Ivoire',
        })


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related('student', 'student__user', 'academic_year').all()
    serializer_class = EnrollmentSerializer
    permission_module = 'students'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'academic_year', 'enrollment_type', 'status']

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = 'approved'
        enrollment.validated_by = request.user
        enrollment.validated_at = timezone.now()
        enrollment.save()
        return Response(EnrollmentSerializer(enrollment).data)


class AcademicRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AcademicRecord.objects.select_related('student', 'academic_year', 'semester').all()
    serializer_class = AcademicRecordSerializer
    permission_module = 'students'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'academic_year']
