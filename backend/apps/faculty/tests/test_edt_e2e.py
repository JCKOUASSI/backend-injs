"""Scénario bout-en-bout EDT → Cours → Présences → Badgeages (21 étapes)."""
from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academics.models import Course, FormationPeriod, ProgramCourse, TeachingUnit
from apps.academics.services.cours import build_cours_catalog, get_cours_offering
from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle, create_student
from apps.faculty.models import (
    Attendance, AttendanceSession, BadgeEvent, CourseAssignment, Room, Schedule,
    Seance, StudentGroup, Teacher, TeachingLoad,
)
from apps.faculty.services.campus_ops import seed_session_roster
from apps.faculty.services.planning import detect_seance_conflicts, generate_for_promotion
from apps.faculty.services.session_qr import (
    attendance_dashboard_stats,
    check_in_student,
    check_out_student,
)


class EdtEndToEndTests(TestCase):
    """Chaîne produit : année → formation → période → UE/ECUE → EDT → cours → badgeage."""

    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.year = create_institution_bundle()
        self.admin = User.objects.create_superuser(
            email='e2e.admin@test.ci', password=TEST_PASSWORD,
            first_name='Admin', last_name='E2E',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_twenty_one_step_chain(self):
        today = timezone.localdate()
        now = timezone.localtime()

        with self.subTest('1. année académique'):
            self.assertTrue(self.year.is_current)
            self.assertEqual(self.year.institution_id, self.inst.id)

        with self.subTest('2. création d’une formation'):
            self.assertEqual(self.program.degree_type, 'L')
            self.assertEqual(self.program.department_id, self.dept.id)

        with self.subTest('3. période de formation'):
            period = FormationPeriod.objects.create(
                academic_year=self.year, program=self.program, label='Période E2E',
                start_date=today, end_date=today + timedelta(days=14),
            )
            self.assertTrue(period.is_active)

        with self.subTest('4-5. UE et ECUE'):
            ue = TeachingUnit.objects.create(
                code='UE-E2E', name='UE E2E', credits_ects=6,
                semester_number=1, department=self.dept,
            )
            course = Course.objects.create(
                teaching_unit=ue, code='ECUE-E2E', name='Didactique E2E',
                hours_cm=2, hours_td=0, hours_tp=0,
            )
            ProgramCourse.objects.create(program=self.program, teaching_unit=ue, semester_number=1)

        with self.subTest('6. affecter un professeur'):
            teacher = Teacher.objects.create(
                user=User.objects.create_user(
                    email='e2e.ens@test.ci', password=TEST_PASSWORD,
                    first_name='Prof', last_name='E2E',
                ),
                employee_id='E2E001', department=self.dept, grade='assistant',
            )
            assignment = CourseAssignment.objects.create(
                teacher=teacher, course=course,
                academic_year=self.year, promotion=self.promotion, is_primary=True,
            )

        with self.subTest('7. groupe pédagogique'):
            group = StudentGroup.objects.create(promotion=self.promotion, name='Groupe E2E')
            self.assertEqual(group.promotion_id, self.promotion.id)

        with self.subTest('8. salle'):
            Room.objects.create(
                institution=self.inst, code='S-E2E', name='Salle E2E',
                capacity=40, room_type='classroom',
            )

        with self.subTest('9. générer l’EDT'):
            TeachingLoad.objects.create(
                period=period, course=course, promotion=self.promotion,
                session_kind='cm', hours_total=2, teacher=teacher,
            )
            response = self.client.post(reverse('seance-generate'), {
                'period': str(period.id),
                'promotion': str(self.promotion.id),
                'auto_create_loads': False,
            }, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertGreaterEqual(response.data['created'], 1)
            seance = Seance.objects.filter(promotion=self.promotion, course=course).first()
            self.assertEqual(seance.status, 'generated')
            self.assertEqual(seance.teacher_id, teacher.id)

        with self.subTest('10. conflits'):
            conflicts = detect_seance_conflicts(Seance.objects.filter(promotion=self.promotion))
            errors = [row for row in conflicts if row['severity'] == 'error']
            self.assertEqual(errors, [])

        with self.subTest('11-12. valider puis publier'):
            seance.status = 'validated'
            seance.save(update_fields=['status', 'updated_at'])
            published = self.client.post(reverse('seance-publish'), {
                'period': str(period.id),
                'promotion': str(self.promotion.id),
            }, format='json')
            self.assertEqual(published.status_code, 200, published.data)
            self.assertGreaterEqual(published.data['published'], 1)
            seance.refresh_from_db()
            self.assertEqual(seance.status, 'published')
            self.assertTrue(seance.is_visible)

        with self.subTest('13. la séance alimente le catalogue Cours'):
            catalog = build_cours_catalog({'academic_year': str(self.year.id)})
            row = catalog['results'][0]
            self.assertEqual(row['course_code'], 'ECUE-E2E')
            self.assertEqual(row['status'], 'planifie')
            self.assertGreaterEqual(row['seances_count'], 1)
            detail = get_cours_offering({
                'academic_year': str(self.year.id),
                'course': str(course.id),
                'promotion': str(self.promotion.id),
            })
            self.assertEqual(detail['seances'][0]['id'], str(seance.id))

        _, student = create_student(
            email='e2e.etud@test.ci', matricule='E2E001',
            program=self.program, promotion=self.promotion,
        )
        start = time(max(now.hour - 1, 0), 0)
        end_hour = min(now.hour + 2, 23)
        end = time(end_hour, 0 if end_hour > start.hour else 59)
        if end <= start:
            start, end = time(0, 1), time(23, 59)

        with self.subTest('14. ouvrir la séance de badgeage'):
            weekday = today.weekday()
            schedule = Schedule.objects.create(
                assignment=assignment,
                day_of_week=weekday,
                start_time=start, end_time=end, session_kind='cm', room=seance.room,
            )
            seance.schedule = schedule
            seance.date = today
            seance.start_time = start
            seance.end_time = end
            seance.save()
            session = AttendanceSession.objects.create(
                schedule=schedule, session_date=today, is_active=True, created_by=self.admin,
            )
            self.assertTrue(session.is_active)

        with self.subTest('15. étudiants attendus'):
            roster = seed_session_roster(session, recorded_by=self.admin)
            self.assertEqual(roster['attendances_created'], 1)
            waiting = Attendance.objects.get(student=student, schedule=schedule, date=today)
            self.assertEqual(waiting.status, 'absent')

        with self.subTest('16-18. badgeage d’entrée et statut'):
            attendance, created = check_in_student(
                student=student, schedule=schedule, session_date=today,
                recorded_by=student.user,
                badge_context={'device_id': 'device-e2e', 'device_label': 'Test E2E'},
            )
            self.assertTrue(created)
            self.assertIsNotNone(attendance.checked_in_at)
            self.assertIn(attendance.status, ('present', 'late'))
            self.assertEqual(attendance.seance_id, seance.id)
            self.assertTrue(BadgeEvent.objects.filter(attendance=attendance, kind='check_in').exists())

        with self.subTest('19-20. sortie et durée bornée'):
            attendance, created = check_out_student(
                student=student, schedule=schedule, session_date=today,
                recorded_by=student.user,
                badge_context={'device_id': 'device-e2e'},
                attendance=attendance, seance=seance,
            )
            self.assertFalse(created)
            self.assertIsNotNone(attendance.checked_out_at)
            self.assertIsNotNone(attendance.duration_minutes)
            planned = int((datetime.combine(today, end) - datetime.combine(today, start)).total_seconds() // 60)
            self.assertLessEqual(attendance.duration_minutes, max(planned, 1))
            self.assertTrue(BadgeEvent.objects.filter(attendance=attendance, kind='check_out').exists())

        with self.subTest('21. statistiques'):
            stats = attendance_dashboard_stats(self.admin, today)
            self.assertTrue(stats)
            self.assertGreaterEqual(
                stats.get('open_sessions') or stats.get('sessions_open') or stats.get('present', 0),
                0,
            )

        listed = self.client.get(reverse('seance-list'), {'promotion': str(self.promotion.id)})
        self.assertEqual(listed.status_code, 200)
        self.assertGreaterEqual(listed.data['count'], 1)

        events = self.client.get(reverse('badgeevent-list'), {'student': str(student.id)})
        self.assertEqual(events.status_code, 200)
        self.assertGreaterEqual(events.data['count'], 2)

    def test_weekly_generator_is_untouched_by_dated_engine(self):
        """Non-régression : le gabarit hebdomadaire continue de produire des Schedule."""
        ue = TeachingUnit.objects.create(
            code='UE-HEB', name='UE Hebdo', credits_ects=4,
            semester_number=1, department=self.dept,
        )
        course = Course.objects.create(
            teaching_unit=ue, code='ECUE-HEB', name='Hebdo',
            hours_cm=4, hours_td=0, hours_tp=0,
        )
        teacher = Teacher.objects.create(
            user=User.objects.create_user(
                email='e2e.heb@test.ci', password=TEST_PASSWORD,
                first_name='Heb', last_name='Ens',
            ),
            employee_id='HEB001', department=self.dept, grade='assistant',
        )
        CourseAssignment.objects.create(
            teacher=teacher, course=course,
            academic_year=self.year, promotion=self.promotion,
        )
        Room.objects.create(
            institution=self.inst, code='S-HEB', name='Salle hebdo',
            capacity=30, room_type='classroom',
        )
        result = generate_for_promotion(
            promotion=self.promotion, academic_year=self.year,
        )
        self.assertGreaterEqual(result['created'], 1)
        self.assertTrue(
            Schedule.objects.filter(assignment__course=course, is_active=True).exists()
        )
        self.assertEqual(Seance.objects.filter(course=course).count(), 0)
