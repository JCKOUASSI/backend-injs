from io import BytesIO

from django.test import TestCase
from openpyxl import Workbook

from apps.academics.models import Institution, Specialization
from apps.academics.referential_import import import_referential_workbook


def build_workbook(headers, rows):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


class ReferentialImportTests(TestCase):
    def setUp(self):
        self.institution = Institution.objects.create(
            code='INJS',
            name='Institut National de la Jeunesse et des Sports',
            acronym='INJS',
        )

    def test_import_specializations_creates_rows(self):
        workbook = build_workbook(
            ['code', 'name', 'track', 'is_tronc_commun', 'description'],
            [
                ['EM', 'Education et motricite', 'BOTH', 'oui', 'Socle EPS'],
                ['APA', 'Activites physiques adaptees', 'PL', 'non', 'Parcours adapte'],
            ],
        )

        report = import_referential_workbook('specializations', workbook)

        self.assertEqual(report['created'], 2)
        self.assertEqual(report['updated'], 0)
        self.assertEqual(report['skipped'], 0)
        self.assertEqual(Specialization.objects.count(), 2)

    def test_import_specializations_updates_existing_code(self):
        Specialization.objects.create(
            code='EM',
            name='Ancien libelle',
            track='PC',
            is_tronc_commun=False,
        )
        workbook = build_workbook(
            ['code', 'name', 'track', 'is_tronc_commun', 'description'],
            [['EM', 'Education et motricite', 'BOTH', 'oui', 'Nouvelle description']],
        )

        report = import_referential_workbook('specializations', workbook)
        specialization = Specialization.objects.get(code='EM')

        self.assertEqual(report['created'], 0)
        self.assertEqual(report['updated'], 1)
        self.assertEqual(report['skipped'], 0)
        self.assertEqual(specialization.name, 'Education et motricite')
        self.assertEqual(specialization.track, 'BOTH')
        self.assertTrue(specialization.is_tronc_commun)
        self.assertEqual(specialization.description, 'Nouvelle description')
