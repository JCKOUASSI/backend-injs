"""Catalogue référentiel académique : lecture agrégée, diagnostics et garde-fous.

Trois responsabilités :

* ``build_snapshot`` sert toutes les listes déroulantes de l'application en une
  seule requête HTTP, avec un cache invalidé par version à chaque écriture.
* ``build_overview`` alimente la page d'administration (compteurs par onglet et
  contrôles de cohérence de la maquette).
* ``collect_dependencies`` interdit la suppression d'une entrée référencée par
  des données opérationnelles, au lieu de laisser la cascade SQL détruire
  silencieusement promotions, inscriptions ou notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache
from django.db import models
from django.utils import timezone

from apps.academics.models import (
    AcademicYear, Course, Department, Institution, Program, ProgramCourse,
    Promotion, Semester, Specialization, StapsJobNomenclature, TeachingUnit,
)

CACHE_VERSION_KEY = 'academics:referentiels:version'
SNAPSHOT_CACHE_TTL = 300
OVERVIEW_CACHE_TTL = 60

FAMILIES = [
    ('calendar', 'Calendrier académique'),
    ('structure', 'Structure académique'),
    ('pedagogy', 'Pédagogie'),
    ('nomenclature', 'Nomenclatures'),
]


@dataclass(frozen=True)
class ResourceSpec:
    """Décrit une entité référentielle et la façon dont elle est administrée."""

    key: str
    label: str
    family: str
    model: type[models.Model]
    endpoint: str
    status_field: str | None = None
    manageable: bool = True
    soft_deleted: bool = False
    #: Relations inverses de composition : leur présence n'interdit pas la
    #: suppression du parent (ex. les ECUE d'une UE).
    composition: tuple[str, ...] = field(default_factory=tuple)

    @property
    def supports_status(self) -> bool:
        return self.status_field is not None


RESOURCES: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key='academicYear', label='Années académiques', family='calendar',
        model=AcademicYear, endpoint='/academics/academic-years/',
        status_field='is_current',
    ),
    ResourceSpec(
        key='semester', label='Semestres', family='calendar',
        model=Semester, endpoint='/academics/semesters/',
        status_field='is_current',
    ),
    ResourceSpec(
        key='institution', label='Institutions', family='structure',
        model=Institution, endpoint='/academics/institutions/',
        status_field='is_active',
    ),
    ResourceSpec(
        key='department', label='Départements', family='structure',
        model=Department, endpoint='/academics/departments/', soft_deleted=True,
    ),
    ResourceSpec(
        key='program', label='Programmes', family='structure',
        model=Program, endpoint='/academics/programs/',
        status_field='is_active', soft_deleted=True,
    ),
    ResourceSpec(
        key='promotion', label='Promotions', family='structure',
        model=Promotion, endpoint='/academics/promotions/',
        status_field='is_active',
    ),
    ResourceSpec(
        key='specialization', label='Spécialisations', family='structure',
        model=Specialization, endpoint='/academics/specializations/',
    ),
    ResourceSpec(
        key='teachingUnit', label='Unités d’enseignement', family='pedagogy',
        model=TeachingUnit, endpoint='/academics/teaching-units/',
        soft_deleted=True, composition=('courses',),
    ),
    ResourceSpec(
        key='course', label='ECUE', family='pedagogy',
        model=Course, endpoint='/academics/courses/', soft_deleted=True,
    ),
    ResourceSpec(
        key='programCourse', label='Maquettes pédagogiques', family='pedagogy',
        model=ProgramCourse, endpoint='/academics/program-courses/',
    ),
    ResourceSpec(
        key='jobNomenclature', label='Nomenclature emplois STAPS', family='nomenclature',
        model=StapsJobNomenclature, endpoint='/academics/job-nomenclatures/',
        status_field='is_active', manageable=False,
    ),
)

RESOURCES_BY_KEY = {spec.key: spec for spec in RESOURCES}
RESOURCES_BY_MODEL = {spec.model: spec for spec in RESOURCES}


# --------------------------------------------------------------------------- #
# Cache versionné
# --------------------------------------------------------------------------- #

def get_version() -> int:
    version = cache.get(CACHE_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(CACHE_VERSION_KEY, version, None)
    return int(version)


def bump_version() -> int:
    """Invalide snapshot et overview après toute écriture référentielle."""
    try:
        return int(cache.incr(CACHE_VERSION_KEY))
    except ValueError:
        cache.set(CACHE_VERSION_KEY, 2, None)
        return 2


def _live(model: type[models.Model]) -> models.QuerySet:
    queryset = model._default_manager.all()
    if any(f.name == 'is_deleted' for f in model._meta.fields):
        queryset = queryset.filter(is_deleted=False)
    return queryset


# --------------------------------------------------------------------------- #
# Snapshot (listes déroulantes)
# --------------------------------------------------------------------------- #

def build_snapshot(use_cache: bool = True) -> dict[str, Any]:
    version = get_version()
    cache_key = f'academics:referentiels:snapshot:{version}'
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    years = list(
        _live(AcademicYear)
        .order_by('-start_date')
        .values('id', 'label', 'institution', 'start_date', 'end_date', 'is_current', 'is_archived')
    )
    current_year = next((year for year in years if year['is_current']), None)

    semesters = list(
        _live(Semester)
        .select_related('academic_year')
        .order_by('academic_year__start_date', 'number')
        .values('id', 'number', 'name', 'academic_year', 'is_current', 'academic_year__label')
    )
    for item in semesters:
        item['academic_year_label'] = item.pop('academic_year__label')
    current_semester = next((item for item in semesters if item['is_current']), None)

    programs = list(
        _live(Program)
        .order_by('degree_type', 'name')
        .values('id', 'code', 'name', 'degree_type', 'track', 'department', 'duration_semesters', 'is_active')
    )
    degree_labels = dict(Program.DEGREE_TYPES)
    for item in programs:
        item['degree_type_display'] = degree_labels.get(item['degree_type'], item['degree_type'])

    snapshot = {
        'version': version,
        'generated_at': timezone.now().isoformat(),
        'institutions': list(
            _live(Institution).filter(is_active=True).order_by('name')
            .values('id', 'code', 'name', 'acronym')
        ),
        'academic_years': years,
        'current_academic_year': current_year['id'] if current_year else None,
        'semesters': semesters,
        'current_semester': current_semester['id'] if current_semester else None,
        'departments': list(
            _live(Department).order_by('name').values('id', 'code', 'name', 'institution')
        ),
        'programs': programs,
        'promotions': list(
            _live(Promotion).order_by('-entry_year', 'name')
            .values('id', 'name', 'program', 'entry_year', 'current_semester', 'is_active')
        ),
        'specializations': list(
            _live(Specialization).order_by('code')
            .values('id', 'code', 'name', 'track', 'is_tronc_commun')
        ),
        'teaching_units': list(
            _live(TeachingUnit).order_by('semester_number', 'code')
            .values('id', 'code', 'name', 'semester_number', 'credits_ects', 'department')
        ),
        'courses': list(
            _live(Course).order_by('code')
            .values('id', 'code', 'name', 'teaching_unit', 'hours_cm', 'hours_td', 'hours_tp')
        ),
    }

    if use_cache:
        cache.set(cache_key, snapshot, SNAPSHOT_CACHE_TTL)
    return snapshot


# --------------------------------------------------------------------------- #
# Vue d'ensemble (compteurs + cohérence)
# --------------------------------------------------------------------------- #

def _resource_counters(spec: ResourceSpec) -> dict[str, Any]:
    queryset = _live(spec.model)
    total = queryset.count()
    payload = {
        'key': spec.key,
        'label': spec.label,
        'family': spec.family,
        'endpoint': spec.endpoint,
        'manageable': spec.manageable,
        'soft_deleted': spec.soft_deleted,
        'status_field': spec.status_field,
        'count': total,
    }
    if spec.status_field:
        active = queryset.filter(**{spec.status_field: True}).count()
        payload['active_count'] = active
        payload['inactive_count'] = total - active
    return payload


def build_health() -> dict[str, Any]:
    """Contrôles de cohérence exploitables par l'administrateur."""
    current_years = list(_live(AcademicYear).filter(is_current=True).values('id', 'label'))
    return {
        'current_academic_year': current_years[0]['label'] if current_years else None,
        'multiple_current_years': len(current_years) > 1,
        'missing_current_year': not current_years,
        'missing_current_semester': not _live(Semester).filter(is_current=True).exists(),
        'years_without_semester': _live(AcademicYear).filter(semesters__isnull=True).distinct().count(),
        'programs_without_promotion': _live(Program).filter(promotions__isnull=True).distinct().count(),
        'programs_without_maquette': _live(Program).filter(program_courses__isnull=True).distinct().count(),
        'units_without_course': _live(TeachingUnit).filter(
            courses__isnull=True,
        ).distinct().count(),
        'units_outside_maquette': _live(TeachingUnit).filter(program_links__isnull=True).distinct().count(),
    }


def build_overview(use_cache: bool = True) -> dict[str, Any]:
    version = get_version()
    cache_key = f'academics:referentiels:overview:{version}'
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    resources = [_resource_counters(spec) for spec in RESOURCES]
    by_key = {item['key']: item for item in resources}
    families = [
        {
            'key': key,
            'label': label,
            'resources': [by_key[spec.key] for spec in RESOURCES if spec.family == key],
        }
        for key, label in FAMILIES
    ]

    overview = {
        'version': version,
        'generated_at': timezone.now().isoformat(),
        'families': families,
        'resources': resources,
        'totals': {
            'resources': len(resources),
            'entries': sum(item['count'] for item in resources),
            'manageable': sum(1 for spec in RESOURCES if spec.manageable),
        },
        'health': build_health(),
    }

    if use_cache:
        cache.set(cache_key, overview, OVERVIEW_CACHE_TTL)
    return overview


# --------------------------------------------------------------------------- #
# Garde-fous de suppression
# --------------------------------------------------------------------------- #

class ReferentialProtectedError(Exception):
    """Suppression refusée : l'entrée est référencée ailleurs."""

    def __init__(self, resource_label: str, blocking: list[dict[str, Any]]):
        self.resource_label = resource_label
        self.blocking = blocking
        super().__init__(self.message)

    @property
    def message(self) -> str:
        details = ', '.join(f"{item['count']} {item['label']}" for item in self.blocking)
        return (
            f'Suppression impossible : cette entrée « {self.resource_label} » est '
            f'référencée par {details}. Désactivez-la ou supprimez d’abord les '
            f'données liées.'
        )

    def as_payload(self) -> dict[str, Any]:
        return {
            'code': 'referential_protected',
            'detail': self.message,
            'blocking': self.blocking,
        }


#: Comportements ``on_delete`` qui détruisent ou verrouillent les données liées.
_BLOCKING_ON_DELETE = {'CASCADE', 'PROTECT', 'RESTRICT'}

#: Libellés métier des relations inverses, pour un message d'erreur lisible.
RELATION_LABELS = {
    'academics.AcademicYear': 'années académiques',
    'academics.Course': 'ECUE',
    'academics.Department': 'départements',
    'academics.Program': 'programmes',
    'academics.ProgramCourse': 'lignes de maquette',
    'academics.Promotion': 'promotions',
    'academics.Semester': 'semestres',
    'academics.TeachingUnit': 'unités d’enseignement',
    'academics.StapsJobNomenclature': 'nomenclatures emploi',
    'admissions.AdmissionCampaign': 'campagnes d’admission',
    'exams.Deliberation': 'délibérations',
    'exams.Evaluation': 'évaluations',
    'exams.ExamSession': 'sessions d’examen',
    'faculty.CourseAssignment': 'affectations d’enseignement',
    'faculty.EquipmentAsset': 'équipements',
    'faculty.Room': 'salles',
    'faculty.Teacher': 'enseignants',
    'finance.FeeType': 'types de frais',
    'finance.PaymentConfig': 'configurations de paiement',
    'students.Enrollment': 'inscriptions',
    'students.Student': 'étudiants',
    'students.Transcript': 'relevés de notes',
}


def _relation_label(related_model: type[models.Model]) -> str:
    meta = related_model._meta
    label = RELATION_LABELS.get(meta.label)
    if label:
        return label
    return str(meta.verbose_name_plural or meta.verbose_name or meta.model_name).lower()


def collect_dependencies(instance: models.Model) -> dict[str, list[dict[str, Any]]]:
    """Inventorie les objets pointant vers ``instance``.

    ``blocking`` interdit la suppression (cascade destructive ou PROTECT),
    ``warnings`` signale des références qui seront simplement détachées.
    """
    spec = RESOURCES_BY_MODEL.get(type(instance))
    composition = set(spec.composition) if spec else set()
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for relation in instance._meta.related_objects:
        accessor = relation.get_accessor_name()
        if accessor is None:
            continue
        related_model = relation.related_model
        try:
            queryset = related_model._default_manager.filter(**{relation.field.name: instance})
        except Exception:
            continue
        if any(f.name == 'is_deleted' for f in related_model._meta.fields):
            queryset = queryset.filter(is_deleted=False)
        count = queryset.count()
        if not count:
            continue

        on_delete = getattr(getattr(relation, 'on_delete', None), '__name__', '')
        entry = {
            'accessor': accessor,
            'model': related_model._meta.label,
            'label': _relation_label(related_model),
            'count': count,
            'on_delete': on_delete or 'M2M',
        }
        if accessor in composition or on_delete not in _BLOCKING_ON_DELETE:
            warnings.append(entry)
        else:
            blocking.append(entry)

    blocking.sort(key=lambda item: -item['count'])
    warnings.sort(key=lambda item: -item['count'])
    return {'blocking': blocking, 'warnings': warnings}


def assert_deletable(instance: models.Model) -> dict[str, list[dict[str, Any]]]:
    dependencies = collect_dependencies(instance)
    if dependencies['blocking']:
        spec = RESOURCES_BY_MODEL.get(type(instance))
        label = spec.label if spec else instance._meta.verbose_name
        raise ReferentialProtectedError(str(label), dependencies['blocking'])
    return dependencies


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #

def log_referential_change(
    *,
    user,
    action: str,
    instance: models.Model,
    changes: dict | None = None,
    object_id: str | None = None,
    object_repr: str | None = None,
) -> None:
    """Trace une écriture référentielle avec l'objet réellement touché.

    Le middleware d'audit ne journalise que la route appelée ; on complète ici
    avec le type, l'identifiant et le libellé de l'entrée. Une suppression
    physique vide ``instance.pk`` : l'appelant transmet alors l'identité
    capturée avant l'appel.
    """
    try:
        from apps.accounts.models import AuditLog

        AuditLog.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            action=action,
            module='academics',
            object_type=instance._meta.label,
            object_id=object_id if object_id is not None else str(instance.pk),
            object_repr=(object_repr if object_repr is not None else str(instance))[:255],
            changes=changes or {},
        )
    except Exception:  # l'audit ne doit jamais casser une écriture métier
        pass
