"""Tests génération relevé de notes INJS."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics.models import (
    AcademicYear, Department, Institution, Program, ProgramCourse, Promotion,
    Semester, Specialization, TeachingUnit, Course,
)
from apps.accounts.models import User
from apps.exams.models import ExamSession, Evaluation, Grade
from apps.reports.services.transcript import build_semester_transcript, render_transcript_pdf
from apps.students.models import Student
from apps.exams.services.lmd_engine import calculate_semester_average


class TranscriptServiceTests(TestCase):
    def setUp(self):
        inst = Institution.objects.create(code='INJS', name='INJS', acronym='INJS')
        dept = Department.objects.create(institution=inst, code='STAPS', name='STAPS')
        spec = Specialization.objects.create(code='TC', name='Tronc Commun', is_tronc_commun=True)
        self.program = Program.objects.create(
            department=dept, code='L-STAPS-PL', name='Licence STAPS PL',
            degree_type='L', track='PL', total_credits=180,
        )
        self.promotion = Promotion.objects.create(
            program=self.program, name='L1-TEST', entry_year=2025, current_semester=1,
        )
        user = User.objects.create_user(
            email='test@demo.injs.ci', password='Test@INJS2026!',
            first_name='Kouassi', last_name='Jean',
        )
        self.student = Student.objects.create(
            user=user, matricule='TEST001', program=self.program,
            promotion=self.promotion,
            date_of_birth=date(2000, 1, 1), gender='M',
        )
        ay = AcademicYear.objects.create(
            institution=inst, label='2025-2026',
            start_date=date(2025, 9, 1), end_date=date(2026, 8, 31), is_current=True,
        )
        self.semester = Semester.objects.create(
            academic_year=ay, number=1, name='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2026, 1, 31),
        )
        self.session = ExamSession.objects.create(
            academic_year=ay, semester=self.semester, session_type='normal',
            start_date=date(2026, 1, 10), end_date=date(2026, 1, 25),
        )
        ue = TeachingUnit.objects.create(
            code='SVS8101', name='Sciences de la Vie', credits_ects=6,
            semester_number=1, department=dept,
        )
        course = Course.objects.create(
            teaching_unit=ue, code='SVS81011', name='Anatomie', hours_cm=10, hours_td=27,
        )
        ProgramCourse.objects.create(
            program=self.program, teaching_unit=ue, specialization=spec,
            semester_number=1, credits_override=6,
        )
        cc = Evaluation.objects.create(
            teaching_unit=ue, course=course, exam_session=self.session,
            name='CC', evaluation_type='cc',
        )
        ct = Evaluation.objects.create(
            teaching_unit=ue, course=course, exam_session=self.session,
            name='CT', evaluation_type='exam',
        )
        Grade.objects.create(student=self.student, evaluation=cc, score=Decimal('12'))
        Grade.objects.create(student=self.student, evaluation=ct, score=Decimal('14'))

    def test_build_semester_transcript(self):
        data = build_semester_transcript(self.student, self.session)
        self.assertEqual(data['student']['matricule'], 'TEST001')
        self.assertEqual(len(data['ue_results']), 1)
        self.assertIsNotNone(data['summary']['semester_average'])

    def test_render_transcript_pdf(self):
        response = render_transcript_pdf(self.student, self.session)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn(b'PDF', response.content[:20])

    def test_lmd_integration(self):
        result = calculate_semester_average(self.student, self.semester, self.session)
        self.assertTrue(result['is_validated'])
        self.assertEqual(result['credits_total'], 6)


class TranscriptAPITests(TestCase):
    def setUp(self):
        inst = Institution.objects.create(code='INJS', name='INJS', acronym='INJS')
        dept = Department.objects.create(institution=inst, code='STAPS', name='STAPS')
        program = Program.objects.create(
            department=dept, code='L-STAPS-PL', name='Licence STAPS PL',
            degree_type='L', track='PL', total_credits=180,
        )
        promotion = Promotion.objects.create(
            program=program, name='L1-API', entry_year=2025, current_semester=1,
        )
        admin = User.objects.create_user(
            email='admin-api@test.ci', password='Test@INJS2026!',
            first_name='Admin', last_name='Test', is_staff=True, is_superuser=True,
        )
        user = User.objects.create_user(
            email='student-api@test.ci', password='Test@INJS2026!',
            first_name='Aya', last_name='Kone',
        )
        self.student = Student.objects.create(
            user=user, matricule='API001', program=program, promotion=promotion,
            date_of_birth=date(2001, 5, 5), gender='F',
        )
        ay = AcademicYear.objects.create(
            institution=inst, label='2025-2026',
            start_date=date(2025, 9, 1), end_date=date(2026, 8, 31), is_current=True,
        )
        semester = Semester.objects.create(
            academic_year=ay, number=1, name='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2026, 1, 31),
        )
        self.session = ExamSession.objects.create(
            academic_year=ay, semester=semester, session_type='normal',
            start_date=date(2026, 1, 10), end_date=date(2026, 1, 25),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=admin)

    def test_transcript_pdf_endpoint(self):
        url = reverse('transcript-pdf', kwargs={'student_id': self.student.id})
        response = self.client.get(url, {'semester': 1, 'academic_year': '2025-2026'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_transcript_json_endpoint(self):
        url = reverse('transcript-pdf', kwargs={'student_id': self.student.id})
        response = self.client.get(
            url, {'semester': 1, 'academic_year': '2025-2026', 'format': 'json'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['student']['matricule'], 'API001')
