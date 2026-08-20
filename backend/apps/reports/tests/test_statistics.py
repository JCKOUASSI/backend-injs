"""Tests du service de statistiques académiques INJS."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle, create_student
from apps.exams.models import ExamSession, Evaluation, Grade
from apps.finance.models import FeeType, StudentFee
from apps.reports.services.statistics import StatsScope, build_academic_statistics, rate
from apps.students.models import AcademicRecord, Enrollment
from apps.academics.models import Semester, TeachingUnit


class RateHelperTests(TestCase):
    def test_rate_zero_denominator(self):
        self.assertEqual(rate(5, 0), 0.0)

    def test_rate_rounding(self):
        self.assertEqual(rate(1, 3), 33.3)


class AcademicStatisticsServiceTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        _, self.student = create_student(
            email='stats.student@test.ci',
            matricule='STAT001',
            program=self.program,
            promotion=self.promotion,
        )
        Enrollment.objects.create(
            student=self.student,
            academic_year=self.year,
            enrollment_type='administrative',
            status='approved',
        )
        AcademicRecord.objects.create(
            student=self.student,
            academic_year=self.year,
            semester=Semester.objects.create(
                academic_year=self.year, number=1, name='S1',
                start_date=date(2025, 9, 1), end_date=date(2026, 1, 31),
            ),
            semester_average=Decimal('12.50'),
            credits_acquired=24,
            credits_total=30,
            is_validated=True,
        )
        semester = self.year.semesters.first()
        session = ExamSession.objects.create(
            academic_year=self.year, semester=semester, session_type='normal',
            start_date=date(2026, 1, 10), end_date=date(2026, 1, 25),
        )
        ue = TeachingUnit.objects.create(
            code='STATUE1', name='UE stats', credits_ects=6,
            semester_number=1, department=self.dept,
        )
        evaluation = Evaluation.objects.create(
            teaching_unit=ue, exam_session=session,
            name='CC', evaluation_type='cc',
        )
        Grade.objects.create(student=self.student, evaluation=evaluation, score=Decimal('14'))
        fee_type = FeeType.objects.create(
            code='INSCR', name='Inscription', amount=Decimal('50000'),
            academic_year=self.year,
        )
        StudentFee.objects.create(
            student=self.student, fee_type=fee_type,
            amount_due=Decimal('50000'), amount_paid=Decimal('50000'), status='paid',
        )

    def test_build_payload_sections(self):
        payload = build_academic_statistics(StatsScope(), sections=['kpis', 'pedagogiques', 'admin', 'alertes'])
        self.assertEqual(payload['kpis']['students_active'], 1)
        self.assertEqual(payload['kpis']['credits_acquired'], 24)
        self.assertEqual(payload['kpis']['taux_validation_ects'], 80.0)
        self.assertEqual(payload['pedagogiques']['taux_reussite'], 100.0)
        self.assertEqual(payload['admin']['taux_recouvrement'], 100.0)
        self.assertTrue(payload['alertes']['indicateurs'])

    def test_scope_by_academic_year(self):
        payload = build_academic_statistics(
            StatsScope(academic_year_id=str(self.year.id)),
            sections=['kpis'],
        )
        self.assertEqual(payload['kpis']['students_total'], 1)
        self.assertEqual(payload['filtre']['academic_year_label'], '2025-2026')


class AcademicStatisticsAPITests(TestCase):
    def setUp(self):
        create_institution_bundle()
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='stats.admin@test.ci', password=TEST_PASSWORD,
            first_name='Stats', last_name='Admin',
        )
        self.client.force_authenticate(user=self.admin)

    def test_statistics_endpoint(self):
        response = self.client.get(reverse('academic-statistics'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('kpis', response.data)
        self.assertIn('pedagogiques', response.data)
        self.assertIn('alertes', response.data)

    def test_analytics_compat_still_works(self):
        response = self.client.get(reverse('analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_students', response.data)
        self.assertIn('passing_rates', response.data)
