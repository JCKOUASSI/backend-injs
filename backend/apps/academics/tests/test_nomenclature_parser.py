from django.test import TestCase

from apps.academics.nomenclature_parser import DEFAULT_NOMENCLATURE_PATH, parse_nomenclature_xlsx


class NomenclatureParserTests(TestCase):
    def test_parse_official_nomenclature(self):
        rows = parse_nomenclature_xlsx(DEFAULT_NOMENCLATURE_PATH)
        self.assertEqual(len(rows), 8)

        licence = [r for r in rows if r.degree_type == 'L']
        master = [r for r in rows if r.degree_type == 'M']
        self.assertEqual(len(licence), 4)
        self.assertEqual(len(master), 4)

        grades = {r.civil_service_grade for r in rows}
        self.assertEqual(grades, {'A3', 'A4'})

        specs = {r.specialization_code for r in rows}
        self.assertEqual(specs, {'APA', 'EM', 'ES', 'MS'})

    def test_licence_em_is_capeceps_college(self):
        rows = parse_nomenclature_xlsx(DEFAULT_NOMENCLATURE_PATH)
        em_licence = next(r for r in rows if r.degree_type == 'L' and r.specialization_code == 'EM')
        self.assertEqual(em_licence.civil_service_grade, 'A3')
        self.assertEqual(em_licence.track, 'PC')
        self.assertEqual(em_licence.diploma_code, 'CAPCEPS')
        self.assertIn('COLLEGE', em_licence.job_title.upper())

    def test_master_es_is_caps_lycee(self):
        rows = parse_nomenclature_xlsx(DEFAULT_NOMENCLATURE_PATH)
        es_master = next(r for r in rows if r.degree_type == 'M' and r.specialization_code == 'ES')
        self.assertEqual(es_master.civil_service_grade, 'A4')
        self.assertEqual(es_master.track, 'PL')
        self.assertEqual(es_master.diploma_code, 'CAPS')
        self.assertEqual(es_master.duration_years, 5)
