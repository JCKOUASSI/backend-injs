"""Tests des fondations calendaires de l'EDT : périodes, paramètres, groupes, charges."""
from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academics.models import Course, FormationPeriod, Holiday, TeachingUnit
from apps.core.tests.test_utils import create_institution_bundle, create_student
from apps.faculty.models import (
    GroupSchedulingConfig,
    PlanningSettings,
    StudentGroup,
    StudentGroupMember,
    TeachingLoad,
)


class FormationPeriodTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()

    def _period(self, **kwargs):
        defaults = {
            'academic_year': self.ay,
            'program': self.program,
            'label': 'Semestre 1',
            'start_date': date(2025, 9, 1),
            'end_date': date(2025, 12, 20),
        }
        defaults.update(kwargs)
        return FormationPeriod(**defaults)

    def test_end_date_before_start_is_rejected(self):
        period = self._period(end_date=date(2025, 8, 1))
        with self.assertRaises(ValidationError) as ctx:
            period.full_clean()
        self.assertIn('end_date', ctx.exception.message_dict)

    def test_covers_only_dates_inside_the_window(self):
        period = self._period()
        period.save()
        self.assertTrue(period.covers(date(2025, 9, 1)))
        self.assertTrue(period.covers(date(2025, 10, 15)))
        self.assertTrue(period.covers(date(2025, 12, 20)))
        self.assertFalse(period.covers(date(2025, 8, 31)))
        self.assertFalse(period.covers(date(2025, 12, 21)))

    def test_label_is_unique_per_year_and_program(self):
        self._period().save()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._period().save()

    def test_period_can_be_shared_across_programs(self):
        self._period(program=None).save()
        self.assertEqual(FormationPeriod.objects.filter(program__isnull=True).count(), 1)


class HolidayTests(TestCase):
    def setUp(self):
        self.inst, *_ = create_institution_bundle()

    def test_one_holiday_per_date_and_institution(self):
        Holiday.objects.create(institution=self.inst, date=date(2025, 12, 25), label='Noël')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Holiday.objects.create(
                    institution=self.inst, date=date(2025, 12, 25), label='Doublon',
                )


class PlanningSettingsTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()
        self.period = FormationPeriod.objects.create(
            academic_year=self.ay, program=self.program, label='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2025, 12, 20),
        )

    def test_resolve_returns_usable_defaults_without_any_row(self):
        settings = PlanningSettings.resolve()
        self.assertEqual(PlanningSettings.objects.count(), 0)
        self.assertTrue(settings._state.adding)
        self.assertEqual(settings.morning_start, time(8, 0))
        self.assertEqual(settings.afternoon_end, time(18, 0))
        self.assertEqual(settings.active_days, [0, 1, 2, 3, 4])
        self.assertEqual(settings.session_duration_minutes, 120)

    def test_a_second_global_settings_row_is_rejected(self):
        PlanningSettings.objects.create(session_duration_minutes=180)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlanningSettings.objects.create(session_duration_minutes=90)

    def test_set_global_updates_the_single_row(self):
        PlanningSettings.set_global(session_duration_minutes=180)
        PlanningSettings.set_global(session_duration_minutes=90)
        self.assertEqual(PlanningSettings.objects.filter(is_global=True).count(), 1)
        self.assertEqual(PlanningSettings.resolve().session_duration_minutes, 90)

    def test_period_settings_take_precedence_over_global(self):
        PlanningSettings.objects.create(max_sessions_per_day=2)
        PlanningSettings.objects.create(period=self.period, max_sessions_per_day=5)
        self.assertEqual(PlanningSettings.resolve(self.period).max_sessions_per_day, 5)
        self.assertEqual(PlanningSettings.resolve().max_sessions_per_day, 2)

    def test_period_without_own_settings_falls_back_to_global(self):
        PlanningSettings.objects.create(capacity_tolerance=4)
        self.assertEqual(PlanningSettings.resolve(self.period).capacity_tolerance, 4)


class StudentGroupTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()
        self.group = StudentGroup.objects.create(promotion=self.promotion, name='Groupe 1')

    def test_headcount_counts_members(self):
        self.assertEqual(self.group.headcount, 0)
        for index in range(3):
            _, student = create_student(
                email=f'etu{index}@test.ci', matricule=f'MAT{index}',
                program=self.program, promotion=self.promotion,
            )
            StudentGroupMember.objects.create(group=self.group, student=student)
        self.assertEqual(self.group.headcount, 3)

    def test_a_student_joins_a_group_only_once(self):
        _, student = create_student(program=self.program, promotion=self.promotion)
        StudentGroupMember.objects.create(group=self.group, student=student)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentGroupMember.objects.create(group=self.group, student=student)

    def test_group_name_is_unique_within_a_promotion(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentGroup.objects.create(promotion=self.promotion, name='Groupe 1')

    def test_scheduling_config_defaults_to_weekdays(self):
        config = GroupSchedulingConfig.objects.create(group=self.group)
        self.assertEqual(config.active_days, [0, 1, 2, 3, 4])
        self.assertTrue(config.morning_enabled)
        self.assertEqual(config.afternoon_start, time(14, 0))


class TeachingLoadTests(TestCase):
    def setUp(self):
        self.inst, self.dept, self.program, self.promotion, self.ay = create_institution_bundle()
        self.period = FormationPeriod.objects.create(
            academic_year=self.ay, program=self.program, label='Semestre 1',
            start_date=date(2025, 9, 1), end_date=date(2025, 12, 20),
        )
        ue = TeachingUnit.objects.create(
            code='UE-EDT', name='UE EDT', credits_ects=6, semester_number=1, department=self.dept,
        )
        self.course = Course.objects.create(
            teaching_unit=ue, code='ECUE-EDT', name='ECUE EDT', hours_cm=30, hours_td=15,
        )

    def _load(self, **kwargs):
        defaults = {
            'period': self.period,
            'course': self.course,
            'promotion': self.promotion,
            'session_kind': 'cm',
            'hours_total': 30,
        }
        defaults.update(kwargs)
        return TeachingLoad.objects.create(**defaults)

    def test_audience_is_the_promotion_when_no_group(self):
        load = self._load()
        self.assertEqual(load.audience, self.promotion)

    def test_audience_is_the_group_when_set(self):
        group = StudentGroup.objects.create(promotion=self.promotion, name='Groupe TP')
        load = self._load(group=group, session_kind='tp')
        self.assertEqual(load.audience, group)

    def test_same_course_can_be_planned_twice_with_different_kinds(self):
        self._load(session_kind='cm')
        self._load(session_kind='td', hours_total=15)
        self.assertEqual(TeachingLoad.objects.count(), 2)

    def test_duplicate_load_for_same_kind_is_rejected(self):
        self._load(session_kind='cm')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._load(session_kind='cm')

    def test_hours_total_must_be_positive(self):
        load = TeachingLoad(
            period=self.period, course=self.course, promotion=self.promotion,
            session_kind='cm', hours_total=0,
        )
        with self.assertRaises(ValidationError):
            load.full_clean()
