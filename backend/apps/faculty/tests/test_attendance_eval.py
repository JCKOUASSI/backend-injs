"""Règles de présence : retard, durée bornée, partiel, auto-absence."""
from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.academics.models import Course, TeachingUnit
from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle, create_student
from apps.faculty.models import Attendance, CourseAssignment, Schedule, Teacher
from apps.faculty.services.attendance_eval import (
    clamp_interval,
    close_overdue_attendances,
    close_overdue_for_date,
    evaluate_presence,
    late_minutes,
    planned_window,
    should_auto_absent,
)


class AttendanceEvalTests(TestCase):
    def setUp(self):
        self.tz = timezone.get_current_timezone()
        self.day = date(2025, 9, 15)
        self.start, self.end = planned_window(self.day, time(8, 0), time(10, 0), self.tz)

    def _dt(self, hour, minute):
        return timezone.make_aware(datetime.combine(self.day, time(hour, minute)), self.tz)

    def test_on_time_full_presence(self):
        result = evaluate_presence(
            checked_in_at=self._dt(8, 0),
            checked_out_at=self._dt(10, 0),
            planned_start=self.start,
            planned_end=self.end,
        )
        self.assertEqual(result['status'], 'present')
        self.assertEqual(result['duration_minutes'], 120)
        self.assertEqual(result['late_minutes'], 0)

    def test_late_after_fifteen_minutes(self):
        result = evaluate_presence(
            checked_in_at=self._dt(8, 16),
            checked_out_at=None,
            planned_start=self.start,
            planned_end=self.end,
        )
        self.assertEqual(result['status'], 'late')
        self.assertEqual(result['late_minutes'], 16)

    def test_fifteen_minutes_is_still_present(self):
        result = evaluate_presence(
            checked_in_at=self._dt(8, 15),
            checked_out_at=None,
            planned_start=self.start,
            planned_end=self.end,
        )
        self.assertEqual(result['status'], 'present')

    def test_partial_under_75_percent(self):
        result = evaluate_presence(
            checked_in_at=self._dt(8, 0),
            checked_out_at=self._dt(9, 20),
            planned_start=self.start,
            planned_end=self.end,
        )
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['duration_minutes'], 80)

    def test_duration_is_clamped_to_planned_slot(self):
        _, _, duration = clamp_interval(
            self._dt(7, 30), self._dt(11, 0), self.start, self.end,
        )
        self.assertEqual(duration, 120)
        result = evaluate_presence(
            checked_in_at=self._dt(7, 30),
            checked_out_at=self._dt(11, 0),
            planned_start=self.start,
            planned_end=self.end,
        )
        self.assertEqual(result['status'], 'present')
        self.assertEqual(result['duration_minutes'], 120)

    def test_early_check_in_is_not_late(self):
        self.assertEqual(late_minutes(self._dt(7, 45), self.start), 0)

    def test_auto_absent_after_sixty_minutes(self):
        now = self.end + timedelta(minutes=60)
        self.assertTrue(should_auto_absent(checked_in_at=None, now=now, planned_end=self.end))
        self.assertFalse(should_auto_absent(
            checked_in_at=None, now=self.end + timedelta(minutes=59), planned_end=self.end,
        ))
        self.assertFalse(should_auto_absent(
            checked_in_at=self._dt(8, 5), now=now, planned_end=self.end,
        ))

    def test_no_check_in_is_absent(self):
        result = evaluate_presence(
            checked_in_at=None, checked_out_at=None,
            planned_start=self.start, planned_end=self.end,
        )
        self.assertEqual(result['status'], 'absent')


class AutoAbsenceCloseTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        ue = TeachingUnit.objects.create(
            code='UE-ABS', name='UE Abs', credits_ects=4, semester_number=1, department=self.dept,
        )
        course = Course.objects.create(teaching_unit=ue, code='ECUE-ABS', name='Absences')
        teacher_user = User.objects.create_user(
            email='abs.teacher@test.ci', password=TEST_PASSWORD, first_name='A', last_name='B',
        )
        teacher = Teacher.objects.create(
            user=teacher_user, employee_id='ENS-ABS', department=self.dept, grade='assistant',
        )
        assignment = CourseAssignment.objects.create(
            teacher=teacher, course=course, academic_year=self.year, promotion=self.promotion,
        )
        self.schedule = Schedule.objects.create(
            assignment=assignment, day_of_week=0, start_time=time(8, 0), end_time=time(10, 0),
        )
        _, self.student = create_student(
            email='abs.student@test.ci', matricule='ABS001',
            program=self.program, promotion=self.promotion,
        )
        self.day = date(2025, 9, 15)
        tz = timezone.get_current_timezone()
        self.start, self.end = planned_window(self.day, time(8, 0), time(10, 0), tz)

    def test_open_check_in_is_closed_at_planned_end(self):
        attendance = Attendance.objects.create(
            student=self.student, schedule=self.schedule, date=self.day,
            status='present', checked_in_at=self.start,
        )
        result = close_overdue_attendances(
            schedule=self.schedule, session_date=self.day,
            now=self.end + timedelta(minutes=61),
        )
        attendance.refresh_from_db()
        self.assertEqual(result['closed'], 1)
        self.assertEqual(attendance.checked_out_at, self.end)
        self.assertEqual(attendance.duration_minutes, 120)
        self.assertEqual(attendance.status, 'present')

    def test_excused_is_left_untouched(self):
        attendance = Attendance.objects.create(
            student=self.student, schedule=self.schedule, date=self.day, status='excused',
        )
        close_overdue_attendances(
            schedule=self.schedule, session_date=self.day,
            now=self.end + timedelta(minutes=61),
        )
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, 'excused')
        self.assertIsNone(attendance.checked_out_at)

    def test_close_overdue_for_date_covers_the_session(self):
        Attendance.objects.create(
            student=self.student, schedule=self.schedule, date=self.day,
            status='present', checked_in_at=self.start,
        )
        from apps.faculty.models import AttendanceSession
        AttendanceSession.objects.create(schedule=self.schedule, session_date=self.day, is_active=True)
        result = close_overdue_for_date(self.day, now=self.end + timedelta(minutes=61))
        self.assertEqual(result['closed'], 1)
        self.assertGreaterEqual(result['sessions'], 1)
