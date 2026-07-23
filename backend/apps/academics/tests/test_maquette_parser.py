from django.test import TestCase

from apps.academics.maquette_parser import DEFAULT_MAQUETTE_PATH, parse_maquette_docx


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
