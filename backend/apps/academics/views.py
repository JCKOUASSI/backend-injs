from django.core.exceptions import ValidationError
from rest_framework import viewsets, filters, status, exceptions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.academics.models import (
    Institution, Department, Program, Promotion, AcademicYear,
    Semester, TeachingUnit, Course, ProgramCourse, Specialization,
    StapsJobNomenclature, FormationPeriod, Holiday,
)
from apps.academics.serializers import (
    InstitutionSerializer, DepartmentSerializer, ProgramSerializer,
    PromotionSerializer, AcademicYearSerializer, SemesterSerializer,
    TeachingUnitSerializer, CourseSerializer, ProgramCourseSerializer,
    SpecializationSerializer, StapsJobNomenclatureSerializer,
    FormationPeriodSerializer, HolidaySerializer,
)
from apps.core.mixins import ExportMixin
from apps.academics.referential_import import RESOURCE_HEADERS, import_referential_workbook
from apps.academics.services.cours import build_cours_catalog, get_cours_offering
from apps.academics.services import referentiels as referentiels_service


class ReferentialConflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Suppression impossible : entrée référentielle utilisée.'


class ReferentialGuardMixin:
    """Protège et trace les écritures sur les entités référentielles.

    Une entrée référencée par des données opérationnelles ne peut pas être
    supprimée : l'API répond 409 avec le détail des dépendances, à charge de
    l'administrateur de désactiver l'entrée ou de traiter les données liées.
    """

    def perform_create(self, serializer):
        super().perform_create(serializer)
        referentiels_service.bump_version()
        referentiels_service.log_referential_change(
            user=self.request.user, action='REFERENTIAL_CREATE', instance=serializer.instance,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        referentiels_service.bump_version()
        referentiels_service.log_referential_change(
            user=self.request.user, action='REFERENTIAL_UPDATE', instance=serializer.instance,
            changes={'fields': sorted(serializer.validated_data.keys())},
        )

    def perform_destroy(self, instance):
        try:
            dependencies = referentiels_service.assert_deletable(instance)
        except referentiels_service.ReferentialProtectedError as exc:
            raise ReferentialConflict(exc.as_payload())

        object_id, object_repr = str(instance.pk), str(instance)
        soft_delete = getattr(instance, 'soft_delete', None)
        if callable(soft_delete):
            soft_delete()
        else:
            instance.delete()

        referentiels_service.bump_version()
        referentiels_service.log_referential_change(
            user=self.request.user, action='REFERENTIAL_DELETE', instance=instance,
            object_id=object_id, object_repr=object_repr,
            changes={'detached': dependencies['warnings']},
        )


class InstitutionViewSet(ReferentialGuardMixin, viewsets.ModelViewSet):
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'acronym', 'city', 'country']
    ordering_fields = ['code', 'name', 'city', 'country', 'created_at']
    ordering = ['name']


class DepartmentViewSet(ReferentialGuardMixin, ExportMixin, viewsets.ModelViewSet):
    queryset = Department.objects.select_related('institution', 'head').filter(is_deleted=False)
    serializer_class = DepartmentSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['institution']
    search_fields = ['code', 'name', 'description', 'institution__name']
    ordering_fields = ['code', 'name', 'institution__name', 'created_at']
    ordering = ['name']
    export_headers = ['Code', 'Nom', 'Institution']
    export_title = 'Départements INJS'
    export_filename = 'departements_injs'

    def get_export_rows(self):
        return [[d.code, d.name, d.institution.name] for d in self.filter_queryset(self.get_queryset())]


class SpecializationViewSet(ReferentialGuardMixin, viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['track', 'is_tronc_commun']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'track', 'created_at']
    ordering = ['code']


class ProgramViewSet(ReferentialGuardMixin, ExportMixin, viewsets.ModelViewSet):
    queryset = Program.objects.select_related('department').filter(is_deleted=False)
    serializer_class = ProgramSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'degree_type', 'is_active']
    search_fields = ['code', 'name', 'description', 'department__name']
    ordering_fields = ['code', 'name', 'degree_type', 'duration_semesters', 'total_credits', 'created_at']
    ordering = ['degree_type', 'name']
    export_headers = ['Code', 'Nom', 'Type', 'Département']
    export_title = 'Filières INJS'
    export_filename = 'filieres_injs'

    def get_export_rows(self):
        return [
            [p.code, p.name, p.get_degree_type_display(), p.department.name]
            for p in self.filter_queryset(self.get_queryset())
        ]


class PromotionViewSet(ReferentialGuardMixin, viewsets.ModelViewSet):
    queryset = Promotion.objects.select_related('program').all()
    serializer_class = PromotionSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['program', 'program__department', 'entry_year', 'current_semester', 'is_active']
    search_fields = ['name', 'program__name', 'program__code']
    ordering_fields = ['name', 'entry_year', 'current_semester', 'created_at']
    ordering = ['-entry_year', 'name']


class AcademicYearViewSet(ReferentialGuardMixin, viewsets.ModelViewSet):
    queryset = AcademicYear.objects.select_related('institution').all()
    serializer_class = AcademicYearSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['institution', 'is_current', 'is_archived']
    search_fields = ['label', 'institution__name']
    ordering_fields = ['label', 'start_date', 'end_date', 'created_at']
    ordering = ['-start_date']

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._enforce_single_current(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._enforce_single_current(serializer.instance)

    @staticmethod
    def _enforce_single_current(instance):
        """Une seule année courante par institution."""
        if instance.is_current:
            AcademicYear.objects.filter(
                institution_id=instance.institution_id, is_current=True,
            ).exclude(pk=instance.pk).update(is_current=False)


class SemesterViewSet(ReferentialGuardMixin, viewsets.ModelViewSet):
    queryset = Semester.objects.select_related('academic_year').all()
    serializer_class = SemesterSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['academic_year', 'is_current']
    search_fields = ['name', 'academic_year__label']
    ordering_fields = ['number', 'name', 'start_date', 'end_date', 'created_at']
    ordering = ['academic_year', 'number']

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._enforce_single_current(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._enforce_single_current(serializer.instance)

    @staticmethod
    def _enforce_single_current(instance):
        """Un seul semestre courant par année académique."""
        if instance.is_current:
            Semester.objects.filter(
                academic_year_id=instance.academic_year_id, is_current=True,
            ).exclude(pk=instance.pk).update(is_current=False)


class TeachingUnitViewSet(ReferentialGuardMixin, ExportMixin, viewsets.ModelViewSet):
    queryset = TeachingUnit.objects.select_related('department').prefetch_related('courses').filter(is_deleted=False)
    serializer_class = TeachingUnitSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'semester_number']
    search_fields = ['code', 'name', 'description', 'department__name']
    ordering_fields = ['code', 'name', 'semester_number', 'credits_ects', 'created_at']
    ordering = ['semester_number', 'code']
    export_headers = ['Code', 'Nom', 'Crédits ECTS', 'Semestre']
    export_title = 'Unités d\'enseignement INJS'
    export_filename = 'ue_injs'

    def get_export_rows(self):
        return [
            [u.code, u.name, u.credits_ects, u.semester_number]
            for u in self.filter_queryset(self.get_queryset())
        ]


class CourseViewSet(ReferentialGuardMixin, viewsets.ModelViewSet):
    queryset = Course.objects.select_related('teaching_unit').filter(is_deleted=False)
    serializer_class = CourseSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['teaching_unit', 'teaching_unit__department', 'teaching_unit__semester_number']
    search_fields = ['code', 'name', 'teaching_unit__code', 'teaching_unit__name']
    ordering_fields = ['code', 'name', 'hours_cm', 'created_at']
    ordering = ['code']


class ProgramCourseViewSet(ReferentialGuardMixin, viewsets.ModelViewSet):
    queryset = ProgramCourse.objects.select_related('program', 'teaching_unit', 'specialization').all()
    serializer_class = ProgramCourseSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['program', 'teaching_unit', 'semester_number', 'specialization', 'is_mandatory']
    search_fields = ['program__code', 'program__name', 'teaching_unit__code', 'teaching_unit__name', 'specialization__code']
    ordering_fields = ['semester_number', 'credits_override', 'program__name', 'teaching_unit__code', 'created_at']
    ordering = ['program__name', 'semester_number', 'teaching_unit__code']


class StapsJobNomenclatureViewSet(ExportMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StapsJobNomenclature.objects.select_related('specialization').filter(is_active=True)
    serializer_class = StapsJobNomenclatureSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['degree_type', 'specialization', 'civil_service_grade', 'track', 'diploma_code']
    search_fields = ['job_title', 'competencies', 'career_outcomes', 'employers', 'specialization__code']
    ordering_fields = ['degree_type', 'civil_service_grade', 'duration_years', 'job_title', 'created_at']
    ordering = ['degree_type', 'specialization__code', 'job_title']
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


class AcademicImportViewSet(viewsets.ViewSet):
    permission_module = 'academics'
    parser_classes = [MultiPartParser, FormParser]

    @action(detail=False, methods=['post'], url_path='referentials')
    def referentials(self, request):
        resource = request.data.get('resource')
        upload = request.FILES.get('file')
        if not resource:
            return Response({'detail': "Le champ 'resource' est requis."}, status=400)
        if not upload:
            return Response({'detail': "Le champ 'file' est requis."}, status=400)

        try:
            report = import_referential_workbook(resource, upload)
        except ValueError as exc:
            return Response(
                {
                    'detail': str(exc),
                    'supported_resources': list(RESOURCE_HEADERS.keys()),
                    'expected_headers': RESOURCE_HEADERS.get(resource),
                },
                status=400,
            )

        referentiels_service.bump_version()
        return Response(report)


class ReferentielViewSet(viewsets.ViewSet):
    """Lecture agrégée du catalogue référentiel.

    ``list`` remplace les appels unitaires aux dix ViewSets par une seule
    réponse mise en cache ; ``overview`` fournit compteurs et contrôles de
    cohérence ; ``dependencies`` permet d'avertir l'utilisateur avant une
    suppression destructive.
    """

    permission_module = 'academics'

    def list(self, request):
        refresh = request.query_params.get('refresh') in {'1', 'true', 'True'}
        return Response(referentiels_service.build_snapshot(use_cache=not refresh))

    @action(detail=False, methods=['get'])
    def overview(self, request):
        refresh = request.query_params.get('refresh') in {'1', 'true', 'True'}
        return Response(referentiels_service.build_overview(use_cache=not refresh))

    @action(detail=False, methods=['get'])
    def dependencies(self, request):
        resource = request.query_params.get('resource')
        object_id = request.query_params.get('id')
        spec = referentiels_service.RESOURCES_BY_KEY.get(resource or '')
        if not spec or not object_id:
            return Response(
                {
                    'detail': "Paramètres 'resource' et 'id' requis.",
                    'supported_resources': sorted(referentiels_service.RESOURCES_BY_KEY),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance = spec.model._default_manager.get(pk=object_id)
        except (spec.model.DoesNotExist, ValueError, ValidationError):
            return Response({'detail': 'Entrée référentielle introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        dependencies = referentiels_service.collect_dependencies(instance)
        return Response({
            'resource': spec.key,
            'label': spec.label,
            'object_repr': str(instance),
            'deletable': not dependencies['blocking'],
            'soft_deleted': spec.soft_deleted,
            **dependencies,
        })


class CoursViewSet(viewsets.ViewSet):
    """Façade produit Cours (ECUE × promotion × année) — pas de table dédiée."""

    permission_module = 'academics'

    def list(self, request):
        return Response(build_cours_catalog(request.query_params))

    @action(detail=False, methods=['get'], url_path='offering')
    def offering(self, request):
        payload = get_cours_offering(request.query_params)
        if not payload:
            return Response(
                {'detail': 'Offre de cours introuvable (course, promotion, academic_year).'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(payload)


class FormationPeriodViewSet(viewsets.ModelViewSet):
    queryset = FormationPeriod.objects.select_related('academic_year', 'program', 'semester')
    serializer_class = FormationPeriodSerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['academic_year', 'program', 'semester', 'is_active']
    search_fields = ['label']
    ordering_fields = ['order', 'start_date', 'label']


class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.select_related('institution')
    serializer_class = HolidaySerializer
    permission_module = 'academics'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['institution', 'is_active', 'date']
    search_fields = ['label']
    ordering_fields = ['date', 'label']
