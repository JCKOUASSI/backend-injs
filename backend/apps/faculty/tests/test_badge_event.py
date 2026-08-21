"""BadgeEvent : journal immuable et permissions EDT par rôle."""
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics.models import Course, FormationPeriod, Promotion, TeachingUnit
from apps.accounts.models import User
from apps.core.tests.test_utils import (
    TEST_PASSWORD, create_institution_bundle, create_student, create_user_with_permission,
)
from apps.faculty.models import (
    Attendance, AttendanceSession, BadgeEvent, CourseAssignment, Schedule, Seance, Teacher,
)
from apps.faculty.services.attendance_eval import close_overdue_attendances, planned_window
from apps.faculty.services.session_qr import force_badge_students, mark_student_attendances


class BadgeEventTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        ue = TeachingUnit.objects.create(
            code='UE-BDG', name='UE Badge', credits_ects=4, semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(teaching_unit=ue, code='ECUE-BDG', name='Badge')
        teacher_user = User.objects.create_user(
            email='bdg.ens@test.ci', password=TEST_PASSWORD, first_name='Ens', last_name='Bdg',
        )
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id='BDG001', department=self.dept, grade='assistant',
        )
        assignment = CourseAssignment.objects.create(
            teacher=self.teacher, course=self.course,
            academic_year=self.year, promotion=self.promotion,
        )
        self.schedule = Schedule.objects.create(
            assignment=assignment, day_of_week=0, start_time=time(8, 0), end_time=time(10, 0),
        )
        _, self.student = create_student(
            email='bdg.etud@test.ci', matricule='BDG001',
            program=self.program, promotion=self.promotion,
        )
        self.day = date(2025, 9, 15)
        self.session = AttendanceSession.objects.create(
            schedule=self.schedule, session_date=self.day, is_active=True,
        )
        self.admin = User.objects.create_superuser(
            email='bdg.admin@test.ci', password=TEST_PASSWORD,
            first_name='Admin', last_name='Bdg',
        )

    def test_force_badge_writes_an_event_with_previous_status(self):
        Attendance.objects.create(
            student=self.student, schedule=self.schedule, date=self.day, status='absent',
        )
        force_badge_students(
            self.session, [self.student.id], recorded_by=self.admin, motif='Oubli de badge', status='present',
        )
        event = BadgeEvent.objects.get(student=self.student, kind='force')
        self.assertEqual(event.previous_status, 'absent')
        self.assertEqual(event.new_status, 'present')
        self.assertEqual(event.reason, 'Oubli de badge')
        self.assertEqual(event.source, 'admin')
        self.assertEqual(event.actor, self.admin)

    def test_manual_mark_is_a_correction_event(self):
        mark_student_attendances(
            self.session, [self.student.id], status='excused',
            recorded_by=self.admin, notes='Certificat médical',
        )
        event = BadgeEvent.objects.get(kind='correction')
        self.assertEqual(event.new_status, 'excused')
        self.assertEqual(event.reason, 'Certificat médical')

    def test_auto_absent_writes_a_system_event(self):
        Attendance.objects.create(
            student=self.student, schedule=self.schedule, date=self.day, status='present',
        )
        start, end = planned_window(self.day, time(8, 0), time(10, 0))
        close_overdue_attendances(
            schedule=self.schedule, session_date=self.day,
            now=end + timedelta(minutes=61),
        )
        event = BadgeEvent.objects.get(kind='auto_absent')
        self.assertEqual(event.source, 'system')
        self.assertEqual(event.previous_status, 'present')
        self.assertEqual(event.new_status, 'absent')

    def test_student_lists_own_events_only(self):
        force_badge_students(self.session, [self.student.id], recorded_by=self.admin, status='present')
        other_user, other = create_student(
            email='bdg.other@test.ci', matricule='BDG002',
            program=self.program, promotion=self.promotion,
        )
        AttendanceSession.objects.get_or_create(schedule=self.schedule, session_date=self.day)
        force_badge_students(self.session, [other.id], recorded_by=self.admin, status='present')

        client = APIClient()
        client.force_authenticate(user=self.student.user)
        response = client.get(reverse('badgeevent-list'))
        self.assertEqual(response.status_code, 200)
        student_ids = {str(row['student']) for row in response.data['results']}
        self.assertEqual(student_ids, {str(self.student.id)})


class EdtPermissionTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        self.period = FormationPeriod.objects.create(
            academic_year=self.year, program=self.program, label='S1',
            start_date=date(2025, 9, 1), end_date=date(2025, 9, 30),
        )
        ue = TeachingUnit.objects.create(
            code='UE-PERM', name='UE Perm', credits_ects=4, semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(teaching_unit=ue, code='ECUE-PERM', name='Perm')
        teacher_user = User.objects.create_user(
            email='perm.ens@test.ci', password=TEST_PASSWORD, first_name='P', last_name='Ens',
        )
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id='PERM1', department=self.dept, grade='assistant',
        )
        _, self.student = create_student(
            email='perm.etud@test.ci', matricule='PERM1',
            program=self.program, promotion=self.promotion,
        )
        self.published = Seance.objects.create(
            course=self.course, promotion=self.promotion, teacher=self.teacher,
            date=date(2025, 9, 8), start_time=time(8, 0), end_time=time(10, 0),
            status='published',
        )
        self.draft = Seance.objects.create(
            course=self.course, promotion=self.promotion, teacher=self.teacher,
            date=date(2025, 9, 9), start_time=time(8, 0), end_time=time(10, 0),
            status='generated',
        )
        other_promo = Promotion.objects.create(
            program=self.program, name='L1-OTHER', entry_year=2025, current_semester=1,
        )
        self.foreign = Seance.objects.create(
            course=self.course, promotion=other_promo, teacher=self.teacher,
            date=date(2025, 9, 10), start_time=time(8, 0), end_time=time(10, 0),
            status='published',
        )
        self.client = APIClient()

    def test_student_sees_only_published_seances_of_own_promotion(self):
        self.client.force_authenticate(user=self.student.user)
        response = self.client.get(reverse('seance-list'))
        self.assertEqual(response.status_code, 200)
        ids = {row['id'] for row in response.data['results']}
        self.assertIn(str(self.published.id), ids)
        self.assertNotIn(str(self.draft.id), ids)
        self.assertNotIn(str(self.foreign.id), ids)

    def test_teacher_without_admin_level_cannot_generate(self):
        planner_denied = create_user_with_permission(
            'faculty', 'create', level=3, email='perm.teacher.create@test.ci',
        )
        self.client.force_authenticate(user=planner_denied)
        response = self.client.post(reverse('seance-generate'), {
            'period': str(self.period.id),
            'promotion': str(self.promotion.id),
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_teacher_sees_own_draft_seances(self):
        self.client.force_authenticate(user=self.teacher.user)
        response = self.client.get(reverse('seance-list'))
        self.assertEqual(response.status_code, 200)
        ids = {row['id'] for row in response.data['results']}
        self.assertIn(str(self.draft.id), ids)
        self.assertIn(str(self.published.id), ids)

    def test_teacher_without_admin_level_cannot_create_student_group(self):
        creator = create_user_with_permission(
            'faculty', 'create', level=3, email='perm.group.create@test.ci',
        )
        self.client.force_authenticate(user=creator)
        response = self.client.post(reverse('studentgroup-list'), {
            'promotion': str(self.promotion.id),
            'name': 'Groupe TP',
            'max_students': 20,
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_seance_export_excel_respects_promotion_filter(self):
        planner = create_user_with_permission(
            'faculty', 'view', level=2, email='perm.export@test.ci',
        )
        self.client.force_authenticate(user=planner)
        response = self.client.get(
            reverse('seance-export', kwargs={'export_format': 'excel'}),
            {'promotion': str(self.promotion.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            response['Content-Type'],
            ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'),
        )


class AttendanceScopeTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        ue = TeachingUnit.objects.create(
            code='UE-SCP', name='UE Scope', credits_ects=4, semester_number=1, department=self.dept,
        )
        course = Course.objects.create(teaching_unit=ue, code='ECUE-SCP', name='Scope')
        teacher_user = create_user_with_permission(
            'faculty', 'view', level=3, email='scp.ens@test.ci',
        )
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id='SCP1', department=self.dept, grade='assistant',
        )
        other_user = create_user_with_permission(
            'faculty', 'view', level=3, email='scp.other@test.ci',
        )
        other_teacher = Teacher.objects.create(
            user=other_user, employee_id='SCP2', department=self.dept, grade='assistant',
        )
        assignment = CourseAssignment.objects.create(
            teacher=self.teacher, course=course,
            academic_year=self.year, promotion=self.promotion,
        )
        other_assignment = CourseAssignment.objects.create(
            teacher=other_teacher, course=course,
            academic_year=self.year, promotion=self.promotion, is_primary=False,
        )
        self.schedule = Schedule.objects.create(
            assignment=assignment, day_of_week=0, start_time=time(8, 0), end_time=time(10, 0),
        )
        other_schedule = Schedule.objects.create(
            assignment=other_assignment, day_of_week=1, start_time=time(8, 0), end_time=time(10, 0),
        )
        _, self.student = create_student(
            email='scp.etud@test.ci', matricule='SCP001',
            program=self.program, promotion=self.promotion,
        )
        _, other_student = create_student(
            email='scp.other.etud@test.ci', matricule='SCP002',
            program=self.program, promotion=self.promotion,
        )
        self.own = Attendance.objects.create(
            student=self.student, schedule=self.schedule, date=date(2025, 9, 15), status='present',
        )
        self.foreign = Attendance.objects.create(
            student=other_student, schedule=other_schedule, date=date(2025, 9, 16), status='absent',
        )
        self.client = APIClient()

    def test_teacher_lists_only_attendances_of_own_courses(self):
        self.client.force_authenticate(user=self.teacher.user)
        response = self.client.get(reverse('attendance-list'))
        self.assertEqual(response.status_code, 200)
        ids = {row['id'] for row in response.data['results']}
        self.assertIn(str(self.own.id), ids)
        self.assertNotIn(str(self.foreign.id), ids)

    def test_student_history_is_own_rows_only(self):
        self.client.force_authenticate(user=self.student.user)
        response = self.client.get(reverse('attendance-my-history'))
        self.assertEqual(response.status_code, 200)
        ids = {row['id'] for row in response.data['results']}
        self.assertEqual(ids, {str(self.own.id)})
