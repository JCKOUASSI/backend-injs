from datetime import timedelta, time as dt_time

from django.test import TestCase
from django.utils import timezone

from .models import Formation, Module, Formateur, ModuleFormateur, SessionModule
from .api_views import (
    _finance_recap_par_module,
    _finance_group_sessions_by_groupe,
    _finance_report_rows,
)


def _make_formation(titre='Cycle test'):
    return Formation.objects.create(formation=titre)


def _make_module(formation, intitule='Module test', **kwargs):
    return Module.objects.create(
        formation=formation, intitule=intitule, statut='PLANIFIEE', **kwargs,
    )


def _make_formateur():
    return Formateur.objects.create(numerobadge='F100', nom='Dupont', prenom='Jean')


class FinanceRecapModulesTest(TestCase):

    def test_recap_par_module_sorted_by_grade_groupe(self):
        modules = [
            {'module_id': 2, 'module_intitule': 'B', 'grade': 'A4', 'groupe': 'G2',
             'sessions_count': 1, 'total_duree_minutes': 60, 'total_duree_realisee_minutes': 30,
             'taux_realisation_pct': 50, 'montant_realise': 1000},
            {'module_id': 1, 'module_intitule': 'A', 'grade': 'A4', 'groupe': 'G1',
             'sessions_count': 2, 'total_duree_minutes': 120, 'total_duree_realisee_minutes': 90,
             'taux_realisation_pct': 75, 'montant_realise': 2000},
        ]
        recap = _finance_recap_par_module(modules)
        self.assertEqual([r['module_intitule'] for r in recap], ['A', 'B'])

    def test_group_sessions_by_groupe_with_subtotals(self):
        sessions = [
            {'session_id': 1, 'grade': 'A4', 'groupe': 'G1', 'date_journee': '2026-01-02',
             'numero': 2, 'duree_minutes': 120, 'duree_realisee_minutes': 100, 'montant_realise': 5000},
            {'session_id': 2, 'grade': 'A4', 'groupe': 'G1', 'date_journee': '2026-01-01',
             'numero': 1, 'duree_minutes': 60, 'duree_realisee_minutes': 60, 'montant_realise': 3000},
            {'session_id': 3, 'grade': 'A3', 'groupe': 'G2', 'date_journee': '2026-01-03',
             'numero': 1, 'duree_minutes': 90, 'duree_realisee_minutes': 45, 'montant_realise': 2000},
        ]
        groups = _finance_group_sessions_by_groupe(sessions)
        self.assertEqual(len(groups), 2)
        g1 = next(g for g in groups if g['groupe'] == 'G1')
        self.assertEqual(g1['sous_total']['sessions_count'], 2)
        self.assertEqual(g1['sous_total']['creneau_minutes'], 180.0)
        self.assertEqual(g1['sous_total']['realise_minutes'], 160.0)
        self.assertEqual(g1['sessions'][0]['numero'], 1)

    def test_report_rows_includes_recap_and_groups(self):
        f = _make_formation()
        module = _make_module(
            f, intitule='Déontologie', grade='A4', groupe='GROUPE 4', duree_prevue_heures=4,
        )
        formateur = _make_formateur()
        ModuleFormateur.objects.create(module=module, formateur=formateur)
        now = timezone.now()
        SessionModule.objects.create(
            module=module,
            date_journee=timezone.localdate(),
            numero=1,
            demarree_le=now - timedelta(hours=2),
            terminee_le=now,
            heure_debut_prevue=dt_time(8, 0),
            heure_fin_prevue=dt_time(10, 0),
        )
        rows = _finance_report_rows([formateur], include_sessions=True)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(len(row['recap_modules']), 1)
        self.assertEqual(row['recap_modules'][0]['module_intitule'], 'Déontologie')
        self.assertEqual(len(row['sessions_by_groupe']), 1)
        self.assertEqual(row['sessions_by_groupe'][0]['groupe'], 'GROUPE 4')
        self.assertEqual(row['sessions_by_groupe'][0]['sous_total']['sessions_count'], 1)
