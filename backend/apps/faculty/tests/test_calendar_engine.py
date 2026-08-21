"""Tests du moteur calendaire : génération datée, conflits, extension de gabarit."""
from datetime import date, time

from django.test import TestCase

from apps.academics.models import Course, FormationPeriod, Holiday, TeachingUnit
from apps.accounts.models import User
from apps.core.tests.test_utils import TEST_PASSWORD, create_institution_bundle
from apps.faculty.models import (
    CourseAssignment,
    PlanningSettings,
    Room,
    Schedule,
    Seance,
    Teacher,
    TeachingLoad,
)
from apps.faculty.services.planning import (
    PlanningError,
    detect_seance_conflicts,
    expand_schedules_for_period,
    generate_for_period,
    generate_for_promotion,
    iter_eligible_dates,
    publish_seances,
)


class CalendarEngineTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()
        self.period = FormationPeriod.objects.create(
            academic_year=self.ay, program=self.program, label='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2025, 9, 21),
        )
        ue = TeachingUnit.objects.create(
            code='UE-CAL', name='UE Cal', credits_ects=6, semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(
            teaching_unit=ue, code='ECUE-CAL', name='ECUE Cal', hours_cm=4,
        )
        self.teacher = Teacher.objects.create(
            user=User.objects.create_user(
                email='cal.ens@test.ci', password=TEST_PASSWORD,
                first_name='Cal', last_name='Ens',
            ),
            employee_id='CAL001', department=self.dept, grade='assistant',
        )
        Room.objects.create(
            institution=self.inst, code='AMP-CAL', name='Amphi cal',
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

    def test_eligible_dates_skip_weekends_and_holidays(self):
        Holiday.objects.create(institution=self.inst, date=date(2025, 9, 8), label='Lundi férié')
        settings = PlanningSettings.resolve(self.period)
        days = list(iter_eligible_dates(self.period, settings, {date(2025, 9, 8)}))
        self.assertNotIn(date(2025, 9, 6), days)   # samedi
        self.assertNotIn(date(2025, 9, 7), days)   # dimanche
        self.assertNotIn(date(2025, 9, 8), days)   # férié
        self.assertIn(date(2025, 9, 1), days)      # lundi

    def test_generate_creates_dated_seances_from_teaching_load(self):
        result = generate_for_period(
            period=self.period, promotion=self.promotion, auto_create_loads=False,
        )
        self.assertEqual(result['created'], 2)  # 4h / créneaux de 2h
        seances = list(Seance.objects.filter(promotion=self.promotion).order_by('date', 'start_time'))
        self.assertEqual(len(seances), 2)
        self.assertEqual(seances[0].status, 'generated')
        self.assertEqual(seances[0].course_id, self.course.id)
        self.assertEqual(seances[0].teacher_id, self.teacher.id)
        self.assertEqual(seances[0].period_id, self.period.id)
        self.assertTrue(seances[0].room_id)
        self.assertNotEqual((seances[0].date, seances[0].start_time), (seances[1].date, seances[1].start_time))

    def test_dry_run_does_not_persist(self):
        result = generate_for_period(
            period=self.period, promotion=self.promotion, dry_run=True, auto_create_loads=False,
        )
        self.assertEqual(result['created'], 2)
        self.assertEqual(Seance.objects.count(), 0)

    def test_holiday_is_not_used_as_a_session_day(self):
        Holiday.objects.create(institution=self.inst, date=date(2025, 9, 1), label='Rentrée fériée')
        generate_for_period(period=self.period, promotion=self.promotion, auto_create_loads=False)
        self.assertFalse(Seance.objects.filter(date=date(2025, 9, 1)).exists())

    def test_teacher_conflict_is_detected(self):
        generate_for_period(period=self.period, promotion=self.promotion, auto_create_loads=False)
        first = Seance.objects.order_by('date', 'start_time').first()
        other_course = Course.objects.create(
            teaching_unit=self.course.teaching_unit, code='ECUE-CAL2', name='Autre',
        )
        clone = Seance.objects.create(
            period=self.period, course=other_course, promotion=self.promotion,
            teacher=self.teacher, date=first.date,
            start_time=first.start_time, end_time=first.end_time, status='generated',
        )
        conflicts = detect_seance_conflicts(Seance.objects.filter(id__in=[first.id, clone.id]))
        types = {row['type'] for row in conflicts}
        self.assertIn('teacher', types)
        self.assertTrue(any('déjà affecté' in row['message'] for row in conflicts))

    def test_two_groups_may_sit_in_parallel(self):
        from apps.faculty.models import StudentGroup
        g1 = StudentGroup.objects.create(promotion=self.promotion, name='G1')
        g2 = StudentGroup.objects.create(promotion=self.promotion, name='G2')
        day = date(2025, 9, 2)
        a = Seance.objects.create(
            course=self.course, promotion=self.promotion, group=g1, date=day,
            start_time=time(8, 0), end_time=time(10, 0), status='generated',
        )
        b = Seance.objects.create(
            course=self.course, promotion=self.promotion, group=g2, date=day,
            start_time=time(8, 0), end_time=time(10, 0), status='generated',
        )
        conflicts = detect_seance_conflicts(Seance.objects.filter(id__in=[a.id, b.id]))
        self.assertFalse(any(row['type'] in ('group', 'promotion') for row in conflicts))

    def test_promotion_wide_session_blocks_a_group(self):
        from apps.faculty.models import StudentGroup
        group = StudentGroup.objects.create(promotion=self.promotion, name='G1')
        day = date(2025, 9, 2)
        a = Seance.objects.create(
            course=self.course, promotion=self.promotion, date=day,
            start_time=time(8, 0), end_time=time(10, 0), status='generated',
        )
        b = Seance.objects.create(
            course=self.course, promotion=self.promotion, group=group, date=day,
            start_time=time(8, 0), end_time=time(10, 0), status='generated',
        )
        conflicts = detect_seance_conflicts(Seance.objects.filter(id__in=[a.id, b.id]))
        self.assertTrue(any(row['type'] == 'promotion' for row in conflicts))

    def test_publish_is_blocked_by_an_error_conflict(self):
        generate_for_period(period=self.period, promotion=self.promotion, auto_create_loads=False)
        first = Seance.objects.order_by('date').first()
        Seance.objects.create(
            period=self.period, course=self.course, promotion=self.promotion,
            teacher=self.teacher, room=first.room, date=first.date,
            start_time=first.start_time, end_time=first.end_time, status='generated',
        )
        with self.assertRaises(PlanningError) as ctx:
            publish_seances(Seance.objects.filter(promotion=self.promotion))
        self.assertEqual(ctx.exception.code, 'conflicts')
        self.assertTrue(Seance.objects.filter(status='generated').exists())

    def test_publish_marks_seances_visible(self):
        generate_for_period(period=self.period, promotion=self.promotion, auto_create_loads=False)
        result = publish_seances(Seance.objects.filter(promotion=self.promotion))
        self.assertEqual(result['published'], 2)
        self.assertTrue(all(row.is_visible for row in Seance.objects.all()))

    def test_replace_cancels_generated_but_keeps_published(self):
        generate_for_period(period=self.period, promotion=self.promotion, auto_create_loads=False)
        kept = Seance.objects.order_by('date').first()
        kept.status = 'published'
        kept.save(update_fields=['status'])
        generate_for_period(
            period=self.period, promotion=self.promotion, replace_existing=True, auto_create_loads=False,
        )
        kept.refresh_from_db()
        self.assertEqual(kept.status, 'published')
        self.assertTrue(Seance.objects.filter(status='cancelled').exists())
        self.assertTrue(Seance.objects.filter(status='generated').exists())

    def test_weekly_generation_still_works(self):
        result = generate_for_promotion(
            promotion=self.promotion, academic_year=self.ay,
            replace_existing=True, open_sessions=False, auto_seed_roster=False,
        )
        self.assertGreaterEqual(result['created'], 1)
        self.assertTrue(Schedule.objects.filter(assignment__promotion=self.promotion, is_active=True).exists())

    def test_expand_weekly_template_to_dated_seances(self):
        generate_for_promotion(
            promotion=self.promotion, academic_year=self.ay,
            replace_existing=True, open_sessions=False, auto_seed_roster=False,
        )
        result = expand_schedules_for_period(period=self.period, promotion=self.promotion)
        self.assertGreaterEqual(result['created'], 1)
        seance = Seance.objects.filter(schedule__isnull=False).first()
        self.assertEqual(seance.course_id, self.course.id)
        self.assertEqual(seance.status, 'generated')
        self.assertEqual(seance.date.weekday(), seance.schedule.day_of_week)

    def test_session_outside_period_is_a_period_conflict(self):
        seance = Seance.objects.create(
            period=self.period, course=self.course, promotion=self.promotion,
            date=date(2026, 1, 10), start_time=time(8, 0), end_time=time(10, 0),
        )
        conflicts = detect_seance_conflicts(Seance.objects.filter(pk=seance.pk))
        self.assertTrue(any(row['type'] == 'period' for row in conflicts))
