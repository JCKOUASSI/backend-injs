"""Tests du moteur de génération d'emploi du temps."""
from datetime import date, time

from django.test import TestCase

from apps.academics.models import Course, TeachingUnit
from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle
from apps.faculty.models import CourseAssignment, Room, Schedule, StaffAttendance, Teacher
from apps.faculty.services.planning import (
    _weekly_session_count,
    ensure_assignments_for_promotion,
    generate_for_promotion,
)
from apps.faculty.services.session_qr import (
    check_in_staff,
    seed_staff_roster,
    SessionQrError,
)


class WeeklyCountTests(TestCase):
    def test_semester_hours_to_weekly_slots(self):
        self.assertEqual(_weekly_session_count(30), 1)
        self.assertEqual(_weekly_session_count(45), 2)
        self.assertEqual(_weekly_session_count(12), 1)
        self.assertEqual(_weekly_session_count(0), 0)


class PlanningGenerationTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()
        self.ue = TeachingUnit.objects.create(
            code='UE-TST', name='UE Test', credits_ects=6,
            semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(
            teaching_unit=self.ue, code='ECUE-TST', name='ECUE Test',
            hours_cm=30, hours_td=15, hours_tp=30,
        )
        u1 = User.objects.create_user(
            email='formateur@test.ci', password=TEST_PASSWORD,
            first_name='Formateur', last_name='Martin',
        )
        u2 = User.objects.create_user(
            email='encadrant@test.ci', password=TEST_PASSWORD,
            first_name='Encadrant', last_name='Kone',
        )
        self.formateur = Teacher.objects.create(
            user=u1, employee_id='ENS001', department=self.dept, grade='assistant',
        )
        self.encadrant = Teacher.objects.create(
            user=u2, employee_id='ENS002', department=self.dept, grade='assistant',
        )
        Room.objects.create(
            institution=self.inst, code='AMP-T', name='Amphi test',
            capacity=80, room_type='amphitheater', status='available',
        )
        Room.objects.create(
            institution=self.inst, code='GYM-T', name='Gymnase test',
            capacity=40, room_type='gym', status='available',
        )

    def test_ensure_assignments_sets_supervisor_for_tp(self):
        info = ensure_assignments_for_promotion(self.promotion, self.ay)
        self.assertGreaterEqual(info['created'], 1)
        assignment = CourseAssignment.objects.get(course=self.course, promotion=self.promotion)
        self.assertIsNotNone(assignment.supervisor_id)
        self.assertNotEqual(assignment.teacher_id, assignment.supervisor_id)

    def test_generate_creates_kinded_slots(self):
        result = generate_for_promotion(
            promotion=self.promotion,
            academic_year=self.ay,
            replace_existing=True,
            dry_run=False,
            auto_assign_teachers=True,
            auto_seed_roster=False,
            open_sessions=False,
        )
        self.assertGreaterEqual(result['created'], 1)
        kinds = set(
            Schedule.objects.filter(
                assignment__promotion=self.promotion, is_active=True,
            ).values_list('session_kind', flat=True)
        )
        self.assertTrue(kinds.intersection({'cm', 'td', 'tp'}))
        tp = Schedule.objects.filter(
            assignment__promotion=self.promotion, session_kind='tp', is_active=True,
        ).first()
        if tp:
            self.assertIsNotNone(tp.resolved_supervisor())


class StaffAttendanceTests(TestCase):
    def setUp(self):
        inst, dept, program, promotion, ay = create_institution_bundle()
        ue = TeachingUnit.objects.create(
            code='UE-P', name='UE Presence', credits_ects=3,
            semester_number=1, department=dept,
        )
        course = Course.objects.create(
            teaching_unit=ue, code='ECUE-P', name='Presence',
            hours_cm=15, hours_tp=15,
        )
        u1 = User.objects.create_user(
            email='f@test.ci', password=TEST_PASSWORD, first_name='F', last_name='A',
        )
        u2 = User.objects.create_user(
            email='e@test.ci', password=TEST_PASSWORD, first_name='E', last_name='B',
        )
        self.formateur = Teacher.objects.create(
            user=u1, employee_id='F001', department=dept, grade='assistant',
        )
        self.encadrant = Teacher.objects.create(
            user=u2, employee_id='E001', department=dept, grade='assistant',
        )
        assignment = CourseAssignment.objects.create(
            teacher=self.formateur, supervisor=self.encadrant,
            course=course, academic_year=ay, promotion=promotion,
        )
        today = date.today()
        weekday = today.weekday()
        if weekday > 5:
            weekday = 0
        self.schedule = Schedule.objects.create(
            assignment=assignment,
            day_of_week=weekday,
            start_time=time(8, 0),
            end_time=time(10, 0),
            session_kind='tp',
            supervisor=self.encadrant,
            is_active=True,
        )

    def test_staff_roster_and_check_in(self):
        from apps.faculty.models import AttendanceSession
        session_date = date.today()
        if session_date.weekday() != self.schedule.day_of_week:
            self.schedule.day_of_week = session_date.weekday() if session_date.weekday() < 6 else 0
            self.schedule.save(update_fields=['day_of_week', 'updated_at'])
            if session_date.weekday() > 5:
                self.skipTest('Pas de créneau le dimanche')
        session = AttendanceSession.objects.create(
            schedule=self.schedule, session_date=session_date, is_active=True,
        )
        seed_staff_roster(session)
        self.assertTrue(
            StaffAttendance.objects.filter(schedule=self.schedule, role='formateur').exists()
        )
        self.assertTrue(
            StaffAttendance.objects.filter(schedule=self.schedule, role='encadrant').exists()
        )
        result = check_in_staff(
            teacher=self.formateur, schedule=self.schedule, session_date=session_date,
            badge_context={'device_id': 'device-formateur', 'device_label': 'Test F001'},
        )
        self.assertIn('formateur', result['roles'])
        enc = check_in_staff(
            teacher=self.encadrant, schedule=self.schedule, session_date=session_date,
            badge_context={'device_id': 'device-encadrant', 'device_label': 'Test E001'},
        )
        self.assertIn('encadrant', enc['roles'])

    def test_wrong_teacher_rejected(self):
        other_user = User.objects.create_user(
            email='other@test.ci', password=TEST_PASSWORD, first_name='X', last_name='Y',
        )
        other = Teacher.objects.create(
            user=other_user, employee_id='X009', department=self.formateur.department, grade='vacataire',
        )
        with self.assertRaises(SessionQrError):
            check_in_staff(
                teacher=other, schedule=self.schedule, session_date=date.today(),
            )
