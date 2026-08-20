"""Tests du module Référentiels : snapshot agrégé, diagnostics et garde-fous."""
from datetime import date

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics.models import (
    AcademicYear, Course, ProgramCourse, Promotion, Semester, TeachingUnit,
)
from apps.academics.services import referentiels as service
from apps.accounts.models import AuditLog, User
from apps.core.tests.test_utils import (
    TEST_PASSWORD, create_institution_bundle, create_student,
)


class ReferentielSnapshotTests(TestCase):
    def setUp(self):
        cache.clear()
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        self.ue = TeachingUnit.objects.create(
            code='UE-REF', name='UE Référentiel', credits_ects=4,
            semester_number=1, department=self.dept,
        )
        Course.objects.create(teaching_unit=self.ue, code='ECUE-REF', name='Physiologie')

    def test_snapshot_exposes_every_dropdown(self):
        snapshot = service.build_snapshot(use_cache=False)
        for key in (
            'institutions', 'academic_years', 'semesters', 'departments',
            'programs', 'promotions', 'specializations', 'teaching_units', 'courses',
        ):
            self.assertIn(key, snapshot)
        self.assertEqual(snapshot['current_academic_year'], self.year.id)
        self.assertEqual(len(snapshot['teaching_units']), 1)
        self.assertEqual(snapshot['programs'][0]['degree_type_display'], 'Licence')

    def test_soft_deleted_entries_are_excluded(self):
        self.ue.soft_delete()
        snapshot = service.build_snapshot(use_cache=False)
        self.assertEqual(snapshot['teaching_units'], [])

    def test_cache_is_invalidated_by_version_bump(self):
        first = service.build_snapshot()
        self.assertEqual(len(first['departments']), 1)

        self.dept.__class__.objects.create(institution=self.inst, code='NEW', name='Nouveau')
        self.assertEqual(len(service.build_snapshot()['departments']), 1, 'le cache doit servir la version précédente')

        service.bump_version()
        self.assertEqual(len(service.build_snapshot()['departments']), 2)


class ReferentielOverviewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()

    def test_counters_grouped_by_family(self):
        overview = service.build_overview(use_cache=False)
        families = {family['key']: family for family in overview['families']}
        self.assertEqual(set(families), {'calendar', 'structure', 'pedagogy', 'nomenclature'})
        structure = {item['key']: item for item in families['structure']['resources']}
        self.assertEqual(structure['program']['count'], 1)
        self.assertEqual(structure['program']['active_count'], 1)
        self.assertEqual(overview['totals']['entries'], sum(r['count'] for r in overview['resources']))

    def test_health_flags_missing_and_duplicate_current_year(self):
        health = service.build_overview(use_cache=False)['health']
        self.assertEqual(health['current_academic_year'], '2025-2026')
        self.assertFalse(health['multiple_current_years'])
        self.assertTrue(health['missing_current_semester'])
        self.assertEqual(health['programs_without_maquette'], 1)

        AcademicYear.objects.create(
            institution=self.inst, label='2026-2027',
            start_date=date(2026, 9, 1), end_date=date(2027, 8, 31), is_current=True,
        )
        health = service.build_overview(use_cache=False)['health']
        self.assertTrue(health['multiple_current_years'])


class ReferentielDependencyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        self.ue = TeachingUnit.objects.create(
            code='UE-DEP', name='UE Dépendances', credits_ects=4,
            semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(teaching_unit=self.ue, code='ECUE-DEP', name='Anatomie')

    def test_cascade_relation_blocks_deletion(self):
        dependencies = service.collect_dependencies(self.program)
        accessors = {item['accessor'] for item in dependencies['blocking']}
        self.assertIn('promotions', accessors)
        with self.assertRaises(service.ReferentialProtectedError):
            service.assert_deletable(self.program)

    def test_protect_relation_blocks_deletion(self):
        create_student(program=self.program, promotion=self.promotion)
        blocking = service.collect_dependencies(self.promotion)['blocking']
        student_entry = next(item for item in blocking if item['accessor'] == 'students')
        self.assertEqual(student_entry['on_delete'], 'PROTECT')
        self.assertEqual(student_entry['label'], 'étudiants')

    def test_composition_relation_only_warns(self):
        dependencies = service.collect_dependencies(self.ue)
        self.assertEqual([item['accessor'] for item in dependencies['warnings']], ['courses'])
        self.assertEqual(dependencies['blocking'], [])
        service.assert_deletable(self.ue)

    def test_free_entry_is_deletable(self):
        semester = Semester.objects.create(
            academic_year=self.year, number=1, name='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2026, 1, 31),
        )
        self.assertEqual(service.assert_deletable(semester), {'blocking': [], 'warnings': []})

    def test_error_message_lists_dependencies(self):
        with self.assertRaises(service.ReferentialProtectedError) as ctx:
            service.assert_deletable(self.program)
        payload = ctx.exception.as_payload()
        self.assertEqual(payload['code'], 'referential_protected')
        self.assertIn('promotions', payload['detail'])
        self.assertTrue(payload['blocking'])


class ReferentielAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        self.ue = TeachingUnit.objects.create(
            code='UE-API-REF', name='UE API', credits_ects=3,
            semester_number=1, department=self.dept,
        )
        ProgramCourse.objects.create(program=self.program, teaching_unit=self.ue, semester_number=1)
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='ref.admin@test.ci', password=TEST_PASSWORD,
            first_name='Ref', last_name='Admin',
        )
        self.client.force_authenticate(user=self.admin)

    def test_snapshot_endpoint(self):
        response = self.client.get(reverse('referentiels-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['programs']), 1)
        self.assertIn('version', response.data)

    def test_overview_endpoint(self):
        response = self.client.get(reverse('referentiels-overview'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('families', response.data)
        self.assertIn('health', response.data)

    def test_dependencies_endpoint(self):
        response = self.client.get(reverse('referentiels-dependencies'), {
            'resource': 'program', 'id': str(self.program.id),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['deletable'])
        self.assertTrue(response.data['blocking'])

    def test_dependencies_endpoint_rejects_unknown_resource(self):
        response = self.client.get(reverse('referentiels-dependencies'), {
            'resource': 'unknown', 'id': str(self.program.id),
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('supported_resources', response.data)

    def test_delete_referenced_entry_returns_409(self):
        response = self.client.delete(reverse('program-detail', args=[self.program.id]))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'referential_protected')
        self.program.refresh_from_db()
        self.assertFalse(self.program.is_deleted)

    def test_delete_free_entry_soft_deletes_and_audits(self):
        promotion = Promotion.objects.create(
            program=self.program, name='L2-LIBRE', entry_year=2026, current_semester=3,
        )
        response = self.client.delete(reverse('promotion-detail', args=[promotion.id]))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Promotion.objects.filter(pk=promotion.pk).exists())
        self.assertTrue(
            AuditLog.objects.filter(action='REFERENTIAL_DELETE', object_id=str(promotion.id)).exists()
        )

    def test_write_bumps_snapshot_version(self):
        before = self.client.get(reverse('referentiels-list')).data['version']
        response = self.client.post(reverse('promotion-list'), {
            'program': str(self.program.id), 'name': 'L3-NEW',
            'entry_year': 2026, 'current_semester': 5, 'is_active': True,
        })
        self.assertEqual(response.status_code, 201)
        after = self.client.get(reverse('referentiels-list'))
        self.assertGreater(after.data['version'], before)
        self.assertEqual(len(after.data['promotions']), 2)
        self.assertTrue(AuditLog.objects.filter(action='REFERENTIAL_CREATE').exists())
