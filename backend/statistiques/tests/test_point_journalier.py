"""Tests point journalier — format CPFAE (modèle FAC)."""
from django.test import SimpleTestCase
from types import SimpleNamespace

from statistiques.point_journalier import (
    _titre_ligne1,
    _organisme_label,
    _aggregate_total,
)


class PointJournalierFormatUnitTest(SimpleTestCase):
    def test_titre_ligne1_fac_cat_a(self):
        formation = SimpleNamespace(formation='Formation en Accompagnement de Carrières (FAC)')
        titre = _titre_ligne1(formation, 'A')
        self.assertIn("FORMATION D'ACCOMPAGNEMENT DE CARRIER CAT A", titre)
        self.assertIn('POINT DES PRÉSENCES_CPFAE', titre)

    def test_titre_ligne1_fab(self):
        formation = SimpleNamespace(formation='Formation en Administration de Base')
        self.assertEqual(
            _titre_ligne1(formation),
            'FORMATION EN ADMINISTRATION DE BASE_POINT DES PRÉSENCES_CPFAE',
        )

    def test_organisme_label_includes_grade(self):
        self.assertEqual(_organisme_label('A', 'A3'), 'CATÉGORIE A_GRADE A3')

    def test_aggregate_total_matches_excel_formula(self):
        """Colonne N du modèle Excel = somme effectifs / somme présents."""
        groupes = [
            {'effectif': 55, 'presents': 53, 'absents': 2},
            {'effectif': 55, 'presents': 55, 'absents': 0},
            {'effectif': 53, 'presents': 52, 'absents': 1},
        ]
        total = _aggregate_total(groupes)
        self.assertEqual(total['effectif'], 163)
        self.assertEqual(total['presents'], 160)
        self.assertEqual(total['absents'], 3)
        self.assertAlmostEqual(total['taux_presence'], 160 / 163, places=4)
        self.assertAlmostEqual(total['taux_absence'], 3 / 163, places=4)
