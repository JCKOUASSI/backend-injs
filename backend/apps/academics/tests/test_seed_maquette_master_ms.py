"""Tests de la maquette démo Master STAPS — Management du Sport."""
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.academics.models import Course, Program, ProgramCourse, TeachingUnit
from apps.academics.services import referentiels as service
from apps.core.tests.test_utils import create_institution_bundle


class SeedMaquetteMasterMsTests(TestCase):
    def setUp(self):
        self.inst, self.dept, _, _, _ = create_institution_bundle()

    def test_seeds_120_ects_maquette_for_m_staps(self):
        call_command('seed_maquette_master_ms')
        program = Program.objects.get(code='M-STAPS')
        links = ProgramCourse.objects.filter(program=program)
        self.assertEqual(links.count(), 21)
        self.assertEqual(
            sum(link.credits for link in links),
            120,
        )
        self.assertEqual(
            TeachingUnit.objects.filter(code__startswith='MST9').count(),
            21,
        )
        self.assertGreaterEqual(
            Course.objects.filter(teaching_unit__code__startswith='MST9').count(),
            21,
        )
        by_semester = {
            semester: links.filter(semester_number=semester).count()
            for semester in (1, 2, 3, 4)
        }
        self.assertEqual(by_semester, {1: 6, 2: 6, 3: 6, 4: 3})

    def test_clears_programs_without_maquette_health_flag(self):
        call_command('seed_maquette_master_ms')
        # Licence du bundle de test n'a pas de maquette → 1 alerte attendue
        health = service.build_health()
        self.assertEqual(health['programs_without_maquette'], 1)

        # Une fois la licence aussi liée, plus aucune alerte
        ue = TeachingUnit.objects.filter(code__startswith='MST9').first()
        licence = Program.objects.get(code='L-STAPS-PL')
        ProgramCourse.objects.create(
            program=licence, teaching_unit=ue, semester_number=1,
        )
        health = service.build_health()
        self.assertEqual(health['programs_without_maquette'], 0)

    def test_replace_required_when_maquette_exists(self):
        call_command('seed_maquette_master_ms')
        with self.assertRaises(CommandError):
            call_command('seed_maquette_master_ms')
        call_command('seed_maquette_master_ms', '--replace')
        self.assertEqual(ProgramCourse.objects.filter(program__code='M-STAPS').count(), 21)
