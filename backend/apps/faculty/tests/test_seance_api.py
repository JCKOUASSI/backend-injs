"""Tests API des séances datées, périodes et génération calendaire."""
from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics.models import Course, FormationPeriod, TeachingUnit
from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle
from apps.faculty.models import CourseAssignment, Room, Seance, Teacher, TeachingLoad


class SeanceApiTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()
        self.period = FormationPeriod.objects.create(
            academic_year=self.ay, program=self.program, label='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2025, 9, 21),
        )
        ue = TeachingUnit.objects.create(
            code='UE-API', name='UE API', credits_ects=6, semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(
            teaching_unit=ue, code='ECUE-API', name='ECUE API', hours_cm=4,
        )
        self.teacher = Teacher.objects.create(
            user=User.objects.create_user(
                email='api.ens@test.ci', password=TEST_PASSWORD,
                first_name='Api', last_name='Ens',
            ),
            employee_id='API001', department=self.dept, grade='assistant',
        )
        Room.objects.create(
            institution=self.inst, code='AMP-API', name='Amphi API',
            capacity=80, room_type='amphitheater',
        )
        CourseAssignment.objects.create(
            teacher=self.teacher, course=self.course,
            academic_year=self.ay, promotion=self.promotion,
        )
        TeachingLoad.objects.create(
            period=self.period, course=self.course, promotion=self.promotion,
            session_kind='cm', hours_total=4, teacher=self.teacher,
        )
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='api.admin@test.ci', password=TEST_PASSWORD,
            first_name='Admin', last_name='Api',
        )
        self.client.force_authenticate(user=self.admin)

    def test_list_formation_periods(self):
        response = self.client.get(reverse('formationperiod-list'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_generate_and_list_seances(self):
        response = self.client.post(reverse('seance-generate'), {
            'period': str(self.period.id),
            'promotion': str(self.promotion.id),
            'auto_create_loads': False,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['created'], 2)

        listed = self.client.get(reverse('seance-list'), {'promotion': str(self.promotion.id)})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data['count'], 2)

        dashboard = self.client.get(reverse('seance-dashboard'), {'promotion': str(self.promotion.id)})
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data['generated'], 2)

    def test_publish_without_conflicts(self):
        self.client.post(reverse('seance-generate'), {
            'period': str(self.period.id),
            'promotion': str(self.promotion.id),
            'auto_create_loads': False,
        }, format='json')
        response = self.client.post(reverse('seance-publish'), {
            'period': str(self.period.id),
            'promotion': str(self.promotion.id),
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['published'], 2)
        self.assertTrue(all(row.status == 'published' for row in Seance.objects.all()))

    def test_generate_rejects_missing_period(self):
        response = self.client.post(reverse('seance-generate'), {
            'promotion': str(self.promotion.id),
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_visible_filter_hides_drafts_and_date_from_clips_the_past(self):
        past = Seance.objects.create(
            course=self.course, promotion=self.promotion, teacher=self.teacher,
            date=date(2025, 9, 2), start_time=time(8, 0), end_time=time(10, 0), status='published',
        )
        Seance.objects.create(
            course=self.course, promotion=self.promotion, teacher=self.teacher,
            date=date(2025, 9, 9), start_time=time(8, 0), end_time=time(10, 0), status='draft',
        )
        future = Seance.objects.create(
            course=self.course, promotion=self.promotion, teacher=self.teacher,
            date=date(2025, 9, 16), start_time=time(8, 0), end_time=time(10, 0), status='published',
        )
        response = self.client.get(reverse('seance-list'), {
            'visible': 'true',
            'date_from': '2025-09-10',
        })
        self.assertEqual(response.status_code, 200)
        ids = {row['id'] for row in response.data['results']}
        self.assertIn(str(future.id), ids)
        self.assertNotIn(str(past.id), ids)

    def test_qr_action_returns_seance_payload(self):
        seance = Seance.objects.create(
            course=self.course, promotion=self.promotion, teacher=self.teacher,
            date=date(2025, 9, 15), start_time=time(8, 0), end_time=time(10, 0),
            status='published',
        )
        response = self.client.get(reverse('seance-qr', args=[seance.id]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['payload'].startswith('INJS:SEANCE:'))
        self.assertIn(str(seance.id), response.data['payload'])

    def test_qr_action_rejects_draft(self):
        seance = Seance.objects.create(
            course=self.course, promotion=self.promotion, teacher=self.teacher,
            date=date(2025, 9, 15), start_time=time(8, 0), end_time=time(10, 0),
            status='draft',
        )
        response = self.client.get(reverse('seance-qr', args=[seance.id]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('code'), 'seance_not_published')
