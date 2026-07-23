from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from apps.academics.models import (
    Institution, Department, Program, Promotion, AcademicYear,
    Semester, TeachingUnit, Course, ProgramCourse, Specialization,
    StapsJobNomenclature,
)
from apps.academics.serializers import (
    InstitutionSerializer, DepartmentSerializer, ProgramSerializer,
    PromotionSerializer, AcademicYearSerializer, SemesterSerializer,
    TeachingUnitSerializer, CourseSerializer, ProgramCourseSerializer,
    SpecializationSerializer, StapsJobNomenclatureSerializer,
)
from apps.core.mixins import ExportMixin


class InstitutionViewSet(viewsets.ModelViewSet):
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_module = 'academics'


class DepartmentViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Department.objects.select_related('institution', 'head').filter(is_deleted=False)
    serializer_class = DepartmentSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['institution']
    export_headers = ['Code', 'Nom', 'Institution']
    export_title = 'Départements INJS'
    export_filename = 'departements_injs'

    def get_export_rows(self):
        return [[d.code, d.name, d.institution.name] for d in self.filter_queryset(self.get_queryset())]

    def perform_destroy(self, instance):
        instance.soft_delete()


class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['track', 'is_tronc_commun']


class ProgramViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Program.objects.select_related('department').filter(is_deleted=False)
    serializer_class = ProgramSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['department', 'degree_type', 'is_active']
    export_headers = ['Code', 'Nom', 'Type', 'Département']
    export_title = 'Filières INJS'
    export_filename = 'filieres_injs'

    def get_export_rows(self):
        return [
            [p.code, p.name, p.get_degree_type_display(), p.department.name]
            for p in self.filter_queryset(self.get_queryset())
        ]


class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.select_related('program').all()
    serializer_class = PromotionSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['program', 'is_active']


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.select_related('institution').all()
    serializer_class = AcademicYearSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['institution', 'is_current', 'is_archived']


class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.select_related('academic_year').all()
    serializer_class = SemesterSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['academic_year', 'is_current']


class TeachingUnitViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = TeachingUnit.objects.select_related('department').prefetch_related('courses').filter(is_deleted=False)
    serializer_class = TeachingUnitSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['department', 'semester_number']
    export_headers = ['Code', 'Nom', 'Crédits ECTS', 'Semestre']
    export_title = 'Unités d\'enseignement INJS'
    export_filename = 'ue_injs'

    def get_export_rows(self):
        return [
            [u.code, u.name, u.credits_ects, u.semester_number]
            for u in self.filter_queryset(self.get_queryset())
        ]


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('teaching_unit').filter(is_deleted=False)
    serializer_class = CourseSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['teaching_unit']


class ProgramCourseViewSet(viewsets.ModelViewSet):
    queryset = ProgramCourse.objects.select_related('program', 'teaching_unit').all()
    serializer_class = ProgramCourseSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['program', 'semester_number', 'specialization']


class StapsJobNomenclatureViewSet(ExportMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StapsJobNomenclature.objects.select_related('specialization').filter(is_active=True)
    serializer_class = StapsJobNomenclatureSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['degree_type', 'specialization', 'civil_service_grade', 'track', 'diploma_code']
    export_headers = [
        'Formation', 'Spécialité', 'Grade', 'Emploi', 'Durée (ans)',
        'Diplôme', 'Compétences', 'Débouchés', 'Employeurs',
    ]
    export_title = 'Nomenclature emplois STAPS INJS'
    export_filename = 'nomenclature_emplois_staps'

    def get_export_rows(self):
        return [
            [
                entry.get_degree_type_display(),
                entry.specialization.code,
                entry.civil_service_grade,
                entry.job_title,
                entry.duration_years,
                entry.diploma_code,
                entry.competencies[:200],
                entry.career_outcomes[:200],
                entry.employers[:200],
            ]
            for entry in self.filter_queryset(self.get_queryset())
        ]
