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

    def test_module_planned_uses_referential_not_badge_duration(self):
        sessions = list(SessionModule.objects.filter(module=self.module))
        planned = _finance_module_planned_minutes(self.module, sessions)
        self.assertEqual(planned, 1800.0)  # 30 h référentiel, 2/2 séances en période

    def test_report_rows_module_planned_from_referential(self):
        rows = _finance_report_rows([self.formateur], include_sessions=True)
        self.assertEqual(len(rows), 1)
        mod = rows[0]['modules'][0]
        self.assertEqual(mod['total_duree_minutes'], 1800.0)
        self.assertEqual(rows[0]['total_duree_minutes'], 1800.0)
        # Détail séance : créneau EDT, pas durée badge
        self.assertEqual(mod['sessions_count'], 2)
        sess = rows[0]['sessions']
        self.assertEqual(len(sess), 2)
        self.assertEqual(sess[0]['duree_minutes'], 300.0)

    def test_realized_capped_at_module_planned(self):
        """Somme séances > planifié contractuel → réalisé plafonné."""
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
        self.assertEqual(small_mod['total_duree_minutes'], 120.0)  # 2 h contractuel
        self.assertEqual(small_mod['total_duree_realisee_minutes'], 120.0)  # plafonné

    def test_dashboard_breakdown_module_planned_from_referential(self):
        rows = _finance_report_rows([self.formateur], include_sessions=False)
        breakdown = _finance_dashboard_modules_breakdown(rows, date_debut=None, date_fin=None)
        fin = next(b for b in breakdown if b['module_id'] == self.module.id)
        self.assertEqual(fin['total_duree_minutes'], 1800.0)
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

    def test_prorata_when_partial_period(self):
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
        # 2 séances sur 3 dans la période → 30 h × 2/3 = 20 h
        self.assertEqual(planned, 1200.0)
