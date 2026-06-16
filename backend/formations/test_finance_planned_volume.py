from datetime import timedelta, time as dt_time

from django.test import TestCase
from django.utils import timezone

from .models import Formation, Module, Formateur, ModuleFormateur, RefModule, SessionModule
from .api_views import (
    _finance_dashboard_modules_breakdown,
    _finance_module_planned_minutes,
    _finance_report_rows,
)


def _make_formation(titre='Cycle test'):
    return Formation.objects.create(formation=titre)


def _make_formateur():
    return Formateur.objects.create(numerobadge='F200', nom='Martin', prenom='Paul')


class FinancePlannedVolumeTest(TestCase):

    def setUp(self):
        self.formation = _make_formation()
        self.ref = RefModule.objects.create(intitule='Finances Publiques', volume_horaire=30)
        self.module = Module.objects.create(
            formation=self.formation,
            intitule='Finances Publiques',
            ref_module=self.ref,
            statut='PLANIFIEE',
            grade='A4',
            groupe='GROUPE 6',
            duree_prevue_heures=30,
        )
        self.formateur = _make_formateur()
        ModuleFormateur.objects.create(module=self.module, formateur=self.formateur)
        now = timezone.now()
        # Séance terminée : 48 h de badge réel mais créneau EDT 5 h seulement
        SessionModule.objects.create(
            module=self.module,
            date_journee=timezone.localdate(),
            numero=1,
            demarree_le=now - timedelta(days=2),
            terminee_le=now,
            heure_debut_prevue=dt_time(7, 30),
            heure_fin_prevue=dt_time(12, 30),
        )
        SessionModule.objects.create(
            module=self.module,
            date_journee=timezone.localdate(),
            numero=2,
            heure_debut_prevue=dt_time(13, 0),
            heure_fin_prevue=dt_time(18, 0),
        )

    def test_module_planned_sums_session_slots_capped_by_ref(self):
        sessions = list(SessionModule.objects.filter(module=self.module))
        planned = _finance_module_planned_minutes(self.module, sessions)
        self.assertEqual(planned, 600.0)  # 2 × 5h EDT = 600min < ref 30h=1800min → min=600

    def test_report_rows_module_planned_from_session_slots(self):
        rows = _finance_report_rows([self.formateur], include_sessions=True)
        self.assertEqual(len(rows), 1)
        mod = rows[0]['modules'][0]
        self.assertEqual(mod['total_duree_minutes'], 600.0)  # 2 × 5h EDT, plafonné à ref 30h
        self.assertEqual(rows[0]['total_duree_minutes'], 600.0)
        self.assertEqual(mod['sessions_count'], 2)
        sess = rows[0]['sessions']
        self.assertEqual(len(sess), 2)
        self.assertEqual(sess[0]['duree_minutes'], 300.0)

    def test_realized_capped_at_module_planned(self):
        """Somme réalisée séances plafonnée au planifié contractuel (duree_prevue_heures)."""
        small = Module.objects.create(
            formation=self.formation,
            intitule='Petit module',
            ref_module=RefModule.objects.create(intitule='Petit module', volume_horaire=2),
            statut='PLANIFIEE',
            grade='A4',
            groupe='GROUPE 1',
            duree_prevue_heures=2,
        )
        ModuleFormateur.objects.create(module=small, formateur=self.formateur)
        now = timezone.now()
        for n in (1, 2):
            SessionModule.objects.create(
                module=small,
                date_journee=timezone.localdate(),
                numero=n,
                demarree_le=now - timedelta(hours=2),
                terminee_le=now,
                heure_debut_prevue=dt_time(7, 30),
                heure_fin_prevue=dt_time(12, 30),
            )
        rows = _finance_report_rows([self.formateur], include_sessions=False)
        small_mod = next(m for m in rows[0]['modules'] if m['module_id'] == small.id)
        self.assertEqual(small_mod['total_duree_minutes'], 120.0)  # 2×5h=600min > ref 2h=120min → plafonné à 120min
        self.assertEqual(small_mod['total_duree_realisee_minutes'], 120.0)  # 2×2h badge plafonnés à 120min
        self.assertLessEqual(small_mod['total_duree_realisee_minutes'], small_mod['total_duree_minutes'])

    def test_dashboard_breakdown_module_planned_from_session_slots(self):
        rows = _finance_report_rows([self.formateur], include_sessions=False)
        breakdown = _finance_dashboard_modules_breakdown(rows, date_debut=None, date_fin=None)
        fin = next(b for b in breakdown if b['module_id'] == self.module.id)
        self.assertEqual(fin['total_duree_minutes'], 600.0)  # 2×5h EDT plafonné ref 30h
        self.assertEqual(fin['sessions_count'], 2)
        self.assertLessEqual(
            fin['total_duree_realisee_minutes'],
            fin['total_duree_minutes'],
        )

    def test_dashboard_realized_never_exceeds_planned(self):
        rows = _finance_report_rows([self.formateur], include_sessions=False)
        breakdown = _finance_dashboard_modules_breakdown(rows, date_debut=None, date_fin=None)
        for row in breakdown:
            self.assertLessEqual(
                row['total_duree_realisee_minutes'],
                row['total_duree_minutes'],
            )

    def test_partial_period_sums_only_sessions_in_range(self):
        """Seules les séances de la période sont sommées, plafonnées au référentiel."""
        future = timezone.localdate() + timedelta(days=30)
        SessionModule.objects.create(
            module=self.module,
            date_journee=future,
            numero=3,
            heure_debut_prevue=dt_time(7, 30),
            heure_fin_prevue=dt_time(12, 30),
        )
        sessions = list(SessionModule.objects.filter(module=self.module))
        today = timezone.localdate()
        planned = _finance_module_planned_minutes(
            self.module, sessions, date_debut=today, date_fin=today,
        )
        self.assertEqual(planned, 600.0)  # 2 séances du jour × 5h = 600min, pas la future

    def test_assigned_module_visible_even_without_sessions_in_period(self):
        """Module rattaché au formateur : visible même si aucune séance dans la période."""
        future = timezone.localdate() + timedelta(days=60)
        SessionModule.objects.filter(module=self.module).update(date_journee=future)
        today = timezone.localdate()
        rows = _finance_report_rows(
            [self.formateur],
            include_sessions=True,
            date_debut=today,
            date_fin=today,
        )
        self.assertEqual(len(rows[0]['recap_modules']), 1)
        self.assertEqual(rows[0]['recap_modules'][0]['module_intitule'], 'Finances Publiques')
        self.assertEqual(rows[0]['recap_modules'][0]['total_duree_minutes'], 0.0)
        self.assertEqual(rows[0]['sessions_count'], 0)

    def test_canonical_volume_horaire_uses_session_slots_capped_by_ref(self):
        from .volume_horaire import compute_volume_horaire_from_module_ids

        totals = compute_volume_horaire_from_module_ids([self.module.id])
        self.assertEqual(totals['prevu_minutes'], 600.0)  # 2×5h EDT < ref 30h → 600min
        self.assertEqual(totals['prevu_heures'], 10.0)
