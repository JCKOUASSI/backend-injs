from django.core.management import call_command
from django.test import TestCase
from io import StringIO

from apps.academics.maquette_parser import DEFAULT_MAQUETTE_PATH, parse_maquette_docx
from apps.academics.models import Course, Department, Institution, TeachingUnit


class MaquetteParserTests(TestCase):
    def test_parse_official_maquette(self):
        ues = parse_maquette_docx(DEFAULT_MAQUETTE_PATH)
        self.assertGreaterEqual(len(ues), 80)
        s1 = [u for u in ues if u.semester == 1 and u.specialization_code == 'TC']
        self.assertGreaterEqual(len(s1), 7)
        self.assertTrue(all(u.ecues for u in s1))
        codes = {u.code for u in ues}
        self.assertIn('SVS8101', codes)
        self.assertIn('SHS8102', codes)


class SyncCmFromMaquetteTests(TestCase):
    def setUp(self):
        inst = Institution.objects.create(code='INJS', name='INJS', acronym='INJS')
        self.dept = Department.objects.create(institution=inst, code='STAPS', name='STAPS')
        ue = TeachingUnit.objects.create(
            code='SVS8101', name='SVS', credits_ects=6,
            semester_number=1, department=self.dept,
        )
        # Volume volontairement faux pour vérifier la correction CM
        self.course = Course.objects.create(
            teaching_unit=ue, code='SVS81011', name='Anatomie',
            hours_cm=1, hours_td=1, hours_tp=1,
        )

    def test_sync_cm_only_from_official_doc(self):
        out = StringIO()
        call_command('sync_cm_from_maquette', '--cm-only', stdout=out)
        self.course.refresh_from_db()
        self.assertEqual(self.course.hours_cm, 10)
        # TD/TP non touchés en mode --cm-only
        self.assertEqual(self.course.hours_td, 1)
        self.assertEqual(self.course.hours_tp, 1)
        self.assertIn('Mis à jour', out.getvalue())
