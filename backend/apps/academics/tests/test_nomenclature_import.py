from django.core.management import call_command
from django.test import TestCase

from apps.academics.models import Specialization, StapsJobNomenclature
from apps.academics.nomenclature_parser import DEFAULT_NOMENCLATURE_PATH, parse_nomenclature_xlsx


class NomenclatureImportTests(TestCase):
    def setUp(self):
        for code, name in (
            ('APA', 'Activités Physiques Adaptées'),
            ('EM', 'Éducation et Motricité'),
            ('ES', 'Entraînement Sportif'),
            ('MS', 'Management du Sport'),
        ):
            Specialization.objects.create(code=code, name=name)

    def test_import_command(self):
        call_command('import_nomenclature_staps', '--replace', f'--file={DEFAULT_NOMENCLATURE_PATH}')
        self.assertEqual(StapsJobNomenclature.objects.count(), 8)
        self.assertEqual(StapsJobNomenclature.objects.filter(degree_type='L').count(), 4)
        self.assertEqual(StapsJobNomenclature.objects.filter(diploma_code='CAPCEPS').count(), 1)
        self.assertEqual(StapsJobNomenclature.objects.filter(diploma_code='CAPEPS').count(), 1)

    def test_unique_degree_specialization(self):
        rows = parse_nomenclature_xlsx(DEFAULT_NOMENCLATURE_PATH)
        call_command('import_nomenclature_staps', '--replace', f'--file={DEFAULT_NOMENCLATURE_PATH}')
        call_command('import_nomenclature_staps', f'--file={DEFAULT_NOMENCLATURE_PATH}')
        self.assertEqual(StapsJobNomenclature.objects.count(), len(rows))
