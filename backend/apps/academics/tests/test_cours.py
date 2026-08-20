"""Tests du catalogue opérationnel Cours (façade ECUE × promotion)."""
from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics.models import Course, ProgramCourse, TeachingUnit
from apps.academics.services.cours import build_cours_catalog, get_cours_offering, slot_hours
from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle, create_student
from apps.faculty.models import AttendanceSession, CourseAssignment, Schedule, Teacher


class SlotHoursTests(TestCase):
    def test_two_hour_slot(self):
        self.assertEqual(slot_hours(time(8, 0), time(10, 0)), 2.0)


class CoursCatalogServiceTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        self.ue = TeachingUnit.objects.create(
            code='UE-CRS', name='UE Cours', credits_ects=6,
            semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(
            teaching_unit=self.ue, code='ECUE-CRS', name='Biomécanique',
            hours_cm=30, hours_td=15, hours_tp=0,
        )
        ProgramCourse.objects.create(
            program=self.program, teaching_unit=self.ue, semester_number=1,
        )
        teacher_user = User.objects.create_user(
            email='cours.teacher@test.ci', password=TEST_PASSWORD,
            first_name='Awa', last_name='Traore',
        )
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id='ENS-CRS', department=self.dept, grade='assistant',
        )

    def test_unassigned_offering_from_maquette(self):
        payload = build_cours_catalog({'academic_year': str(self.year.id)})
        self.assertEqual(payload['count'], 1)
        row = payload['results'][0]
        self.assertEqual(row['course_code'], 'ECUE-CRS')
        self.assertEqual(row['status'], 'non_affecte')
        self.assertEqual(payload['kpis']['unassigned'], 1)
        self.assertEqual(payload['kpis']['assigned'], 0)

    def test_assigned_then_planned(self):
        assignment = CourseAssignment.objects.create(
            teacher=self.teacher, course=self.course,
            academic_year=self.year, promotion=self.promotion, is_primary=True,
        )
        payload = build_cours_catalog({'academic_year': str(self.year.id)})
        self.assertEqual(payload['results'][0]['status'], 'affecte')
        self.assertEqual(payload['results'][0]['teacher_name'], 'Awa Traore')

        Schedule.objects.create(
            assignment=assignment, day_of_week=0,
            start_time=time(8, 0), end_time=time(10, 0), session_kind='cm',
        )
        payload = build_cours_catalog({'academic_year': str(self.year.id)})
        row = payload['results'][0]
        self.assertEqual(row['status'], 'planifie')
        self.assertEqual(row['slots_count'], 1)
        self.assertEqual(row['weekly_hours'], 2.0)
        self.assertEqual(payload['kpis']['planned'], 1)

    def test_status_filter(self):
        payload = build_cours_catalog({'academic_year': str(self.year.id), 'status': 'non_affecte'})
        self.assertEqual(payload['count'], 1)
        payload = build_cours_catalog({'academic_year': str(self.year.id), 'status': 'planifie'})
        self.assertEqual(payload['count'], 0)

    def test_search_and_offering_detail(self):
        CourseAssignment.objects.create(
            teacher=self.teacher, course=self.course,
            academic_year=self.year, promotion=self.promotion,
        )
        payload = build_cours_catalog({'academic_year': str(self.year.id), 'search': 'biome'})
        self.assertEqual(payload['count'], 1)
        detail = get_cours_offering({
            'academic_year': str(self.year.id),
            'course': str(self.course.id),
            'promotion': str(self.promotion.id),
        })
        self.assertIsNotNone(detail)
        self.assertEqual(len(detail['assignments']), 1)
        self.assertEqual(detail['assignments'][0]['teacher_name'], 'Awa Traore')

    def test_students_count_and_offering_id(self):
        create_student(
            email='cours.student@test.ci',
            matricule='CRS001',
            program=self.program,
            promotion=self.promotion,
        )
        payload = build_cours_catalog({'academic_year': str(self.year.id)})
        self.assertEqual(payload['results'][0]['students_count'], 1)
        offering_id = payload['results'][0]['id']
        detail = get_cours_offering({'id': offering_id})
        self.assertEqual(detail['course_code'], 'ECUE-CRS')
        self.assertEqual(detail['students_count'], 1)

    def test_sessions_in_offering(self):
        assignment = CourseAssignment.objects.create(
            teacher=self.teacher, course=self.course,
            academic_year=self.year, promotion=self.promotion,
        )
        schedule = Schedule.objects.create(
            assignment=assignment, day_of_week=0,
            start_time=time(8, 0), end_time=time(10, 0), session_kind='cm',
        )
        AttendanceSession.objects.create(schedule=schedule, session_date=date(2026, 8, 20), is_active=True)
        detail = get_cours_offering({
            'academic_year': str(self.year.id),
            'course': str(self.course.id),
            'promotion': str(self.promotion.id),
        })
        self.assertEqual(detail['sessions_count'], 1)
        self.assertEqual(detail['sessions'][0]['status'], 'en_cours')
        self.assertEqual(detail['session_hours'], 2.0)


class CoursAPITests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        self.ue = TeachingUnit.objects.create(
            code='UE-API', name='UE API', credits_ects=5,
            semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(
            teaching_unit=self.ue, code='ECUE-API', name='Didactique',
            hours_cm=20, hours_td=10, hours_tp=0,
        )
        ProgramCourse.objects.create(
            program=self.program, teaching_unit=self.ue, semester_number=1,
        )
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='cours.admin@test.ci', password=TEST_PASSWORD,
            first_name='Cours', last_name='Admin',
        )
        self.client.force_authenticate(user=self.admin)

    def test_list_endpoint(self):
        response = self.client.get(reverse('cours-list'), {'academic_year': str(self.year.id)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('kpis', response.data)
        self.assertEqual(response.data['results'][0]['course_code'], 'ECUE-API')

    def test_offering_endpoint(self):
        response = self.client.get(reverse('cours-offering'), {
            'academic_year': str(self.year.id),
            'course': str(self.course.id),
            'promotion': str(self.promotion.id),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['course_code'], 'ECUE-API')
        self.assertIn('assignments', response.data)
        self.assertIn('schedules', response.data)
        self.assertIn('sessions', response.data)

    def test_offering_by_composite_id(self):
        offering_id = f'{self.course.id}:{self.promotion.id}:{self.year.id}'
        response = self.client.get(reverse('cours-offering'), {'id': offering_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], offering_id)

    def test_assignment_filter_by_course(self):
        teacher_user = User.objects.create_user(
            email='cours.assign@test.ci', password=TEST_PASSWORD,
            first_name='Koffi', last_name='Yao',
        )
        teacher = Teacher.objects.create(
            user=teacher_user, employee_id='ENS-API', department=self.dept, grade='assistant',
        )
        assignment = CourseAssignment.objects.create(
            teacher=teacher, course=self.course,
            academic_year=self.year, promotion=self.promotion,
        )
        response = self.client.get(reverse('courseassignment-list'), {'course': str(self.course.id)})
        self.assertEqual(response.status_code, 200)
        ids = [row['id'] for row in response.data['results']]
        self.assertIn(str(assignment.id), ids)
        self.assertIn('teaching_unit_code', response.data['results'][0])
        self.assertIn('schedules_count', response.data['results'][0])
