"""Tests de la séance datée et de la reprise des présences existantes."""
from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from importlib import import_module

from apps.academics.models import Course, FormationPeriod, TeachingUnit
from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle, create_student
from apps.faculty.models import (
    Attendance,
    AttendanceSession,
    CourseAssignment,
    Room,
    Schedule,
    Seance,
    StaffAttendance,
    StudentGroup,
    Teacher,
)


class SeanceTestBase(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()
        ue = TeachingUnit.objects.create(
            code='UE-SEA', name='UE Séance', credits_ects=6,
            semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(
            teaching_unit=ue, code='ECUE-SEA', name='ECUE Séance', hours_cm=30,
        )
        self.teacher = Teacher.objects.create(
            user=User.objects.create_user(
                email='ens.seance@test.ci', password=TEST_PASSWORD,
                first_name='Ens', last_name='Seance',
            ),
            employee_id='ENS-SEA', department=self.dept, grade='assistant',
        )
        self.encadrant = Teacher.objects.create(
            user=User.objects.create_user(
                email='enc.seance@test.ci', password=TEST_PASSWORD,
                first_name='Enc', last_name='Seance',
            ),
            employee_id='ENC-SEA', department=self.dept, grade='assistant',
        )
        self.room = Room.objects.create(
            institution=self.inst, code='SC-SEA', name='Salle séance',
            capacity=40, room_type='classroom',
        )
        self.assignment = CourseAssignment.objects.create(
            teacher=self.teacher, supervisor=self.encadrant, course=self.course,
            academic_year=self.ay, promotion=self.promotion,
        )
        self.schedule = Schedule.objects.create(
            assignment=self.assignment, room=self.room, session_kind='cm',
            day_of_week=0, start_time=time(8, 0), end_time=time(10, 0),
        )

    def make_seance(self, **kwargs):
        defaults = {
            'course': self.course,
            'promotion': self.promotion,
            'teacher': self.teacher,
            'room': self.room,
            'date': date(2025, 9, 15),
            'start_time': time(8, 0),
            'end_time': time(10, 0),
        }
        defaults.update(kwargs)
        return Seance.objects.create(**defaults)


class SeanceModelTests(SeanceTestBase):
    def test_duration_and_day_of_week(self):
        seance = self.make_seance()
        self.assertEqual(seance.duration_minutes, 120)
        self.assertEqual(seance.day_of_week, 0)  # 15/09/2025 est un lundi

    def test_end_before_start_is_rejected(self):
        seance = Seance(
            course=self.course, promotion=self.promotion, date=date(2025, 9, 15),
            start_time=time(10, 0), end_time=time(8, 0),
        )
        with self.assertRaises(ValidationError) as ctx:
            seance.full_clean()
        self.assertIn('end_time', ctx.exception.message_dict)

    def test_date_outside_its_period_is_rejected(self):
        period = FormationPeriod.objects.create(
            academic_year=self.ay, program=self.program, label='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2025, 12, 20),
        )
        seance = Seance(
            course=self.course, promotion=self.promotion, period=period,
            date=date(2026, 3, 1), start_time=time(8, 0), end_time=time(10, 0),
        )
        with self.assertRaises(ValidationError) as ctx:
            seance.full_clean()
        self.assertIn('date', ctx.exception.message_dict)

    def test_default_status_is_draft_and_not_visible(self):
        seance = self.make_seance()
        self.assertEqual(seance.status, 'draft')
        self.assertFalse(seance.is_visible)

    def test_published_seance_is_visible(self):
        self.assertTrue(self.make_seance(status='published').is_visible)
        self.assertTrue(self.make_seance(date=date(2025, 9, 16), status='done').is_visible)
        self.assertFalse(self.make_seance(date=date(2025, 9, 17), status='cancelled').is_visible)

    def test_all_eight_statuses_are_available(self):
        self.assertEqual(
            [code for code, _ in Seance.STATUSES],
            ['draft', 'generated', 'validated', 'published',
             'in_progress', 'done', 'cancelled', 'archived'],
        )

    def test_a_schedule_cannot_produce_two_seances_the_same_day(self):
        self.make_seance(schedule=self.schedule)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_seance(schedule=self.schedule)

    def test_two_standalone_seances_may_share_a_date(self):
        self.make_seance()
        self.make_seance(start_time=time(14, 0), end_time=time(16, 0))
        self.assertEqual(Seance.objects.count(), 2)

    def test_supervisor_falls_back_to_the_schedule(self):
        seance = self.make_seance(schedule=self.schedule)
        self.assertEqual(seance.resolved_supervisor(), self.encadrant)

    def test_own_supervisor_takes_precedence(self):
        seance = self.make_seance(schedule=self.schedule, supervisor=self.teacher)
        self.assertEqual(seance.resolved_supervisor(), self.teacher)

    def test_group_is_optional(self):
        group = StudentGroup.objects.create(promotion=self.promotion, name='Groupe TP')
        self.assertIsNone(self.make_seance().group)
        self.assertEqual(self.make_seance(date=date(2025, 9, 16), group=group).group, group)


class AttendanceLinkTests(SeanceTestBase):
    def test_attendance_can_reference_a_seance(self):
        _, student = create_student(program=self.program, promotion=self.promotion)
        seance = self.make_seance(schedule=self.schedule)
        attendance = Attendance.objects.create(
            student=student, schedule=self.schedule, seance=seance,
            date=seance.date, status='present',
        )
        self.assertEqual(seance.attendances.get(), attendance)

    def test_seance_link_stays_optional(self):
        _, student = create_student(program=self.program, promotion=self.promotion)
        attendance = Attendance.objects.create(
            student=student, schedule=self.schedule, date=date(2025, 9, 15),
        )
        self.assertIsNone(attendance.seance_id)

    def test_staff_attendance_can_reference_a_seance(self):
        seance = self.make_seance(schedule=self.schedule)
        staff = StaffAttendance.objects.create(
            teacher=self.teacher, schedule=self.schedule, seance=seance,
            date=seance.date, role='formateur',
        )
        self.assertEqual(seance.staff_attendances.get(), staff)


class _CurrentApps:
    """Expose les modèles courants à la fonction de migration, telle quelle."""

    @staticmethod
    def get_model(app_label, model_name):
        from django.apps import apps as django_apps
        return django_apps.get_model(app_label, model_name)


class BackfillTests(SeanceTestBase):
    """Exerce la fonction de reprise de la migration 0010 sur des données réelles."""

    def _run_backfill(self):
        migration = import_module('apps.faculty.migrations.0010_backfill_seances')
        migration.backfill_seances(_CurrentApps(), None)

    def test_sessions_become_seances_and_presences_are_repointed(self):
        _, student = create_student(program=self.program, promotion=self.promotion)
        past = timezone.localdate() - timedelta(days=7)
        session = AttendanceSession.objects.create(
            schedule=self.schedule, session_date=past, teacher_checked_in=True,
        )
        attendance = Attendance.objects.create(
            student=student, schedule=self.schedule, date=past, status='present',
        )
        staff = StaffAttendance.objects.create(
            teacher=self.teacher, schedule=self.schedule, date=past, role='formateur',
        )

        self._run_backfill()

        seance = Seance.objects.get(schedule=self.schedule, date=past)
        self.assertEqual(seance.course_id, self.course.id)
        self.assertEqual(seance.promotion_id, self.promotion.id)
        self.assertEqual(seance.teacher_id, self.teacher.id)
        self.assertEqual(seance.supervisor_id, self.encadrant.id)
        self.assertEqual(seance.room_id, self.room.id)
        self.assertEqual(seance.start_time, self.schedule.start_time)
        self.assertEqual(seance.status, 'done')
        self.assertTrue(seance.teacher_checked_in)

        attendance.refresh_from_db()
        staff.refresh_from_db()
        self.assertEqual(attendance.seance_id, seance.id)
        self.assertEqual(staff.seance_id, seance.id)
        self.assertEqual(session.session_date, seance.date)

    def test_orphan_attendance_without_session_still_gets_a_seance(self):
        _, student = create_student(program=self.program, promotion=self.promotion)
        past = timezone.localdate() - timedelta(days=3)
        attendance = Attendance.objects.create(
            student=student, schedule=self.schedule, date=past, status='absent',
        )

        self._run_backfill()

        attendance.refresh_from_db()
        self.assertIsNotNone(attendance.seance_id)
        self.assertEqual(attendance.seance.date, past)

    def test_future_session_is_marked_published(self):
        future = timezone.localdate() + timedelta(days=5)
        AttendanceSession.objects.create(schedule=self.schedule, session_date=future)

        self._run_backfill()

        self.assertEqual(Seance.objects.get(date=future).status, 'published')

    def test_backfill_is_idempotent(self):
        past = timezone.localdate() - timedelta(days=2)
        AttendanceSession.objects.create(schedule=self.schedule, session_date=past)

        self._run_backfill()
        self._run_backfill()

        self.assertEqual(Seance.objects.filter(schedule=self.schedule, date=past).count(), 1)
