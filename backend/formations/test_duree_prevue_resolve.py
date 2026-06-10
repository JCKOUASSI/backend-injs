from datetime import date, time, timedelta

from django.test import TestCase

from formations.duree_prevue_resolve import (
    ensure_module_duree_prevue,
    module_edt_planned_hours,
    module_edt_raw_hours,
    module_edt_typical_hours,
    resolve_module_duree_prevue_heures,
)
from formations.models import Formation, Module, RefModule, SessionModule


def _formation():
    return Formation.objects.create(formation='Cycle resolve')


def _module(formation, intitule='Module test', **kwargs):
    return Module.objects.create(formation=formation, intitule=intitule, **kwargs)


def _session(module, day_offset, debut, fin):
    return SessionModule.objects.create(
        module=module,
        date_journee=date(2026, 3, 1) + timedelta(days=day_offset),
        numero=1,
        heure_debut_prevue=debut,
        heure_fin_prevue=fin,
    )


class DureePrevueResolveTest(TestCase):
    def test_from_ref_module_linked(self):
        ref = RefModule.objects.create(intitule='Comptabilité', volume_horaire=30)
        module = _module(_formation(), intitule='Comptabilité', ref_module=ref, duree_prevue_heures=0)

        heures, source = resolve_module_duree_prevue_heures(module)
        self.assertEqual(heures, 30)
        self.assertEqual(source, 'ref_module')

    def test_from_ref_module_by_intitule(self):
        RefModule.objects.create(intitule='Gestion RH', volume_horaire=24)
        module = _module(_formation(), intitule='Gestion RH', duree_prevue_heures=None)

        heures, source = resolve_module_duree_prevue_heures(module)
        self.assertEqual(heures, 24)
        self.assertEqual(source, 'ref_module')

    def test_from_sessions_edt_when_no_ref(self):
        module = _module(_formation(), duree_prevue_heures=0)
        _session(module, 0, time(8, 0), time(18, 0))
        _session(module, 1, time(8, 0), time(20, 0))

        heures, source = resolve_module_duree_prevue_heures(module)
        self.assertEqual(heures, 22)
        self.assertEqual(source, 'sessions_edt')
        self.assertEqual(module_edt_planned_hours(module), 22)

    def test_ref_module_takes_priority_over_sessions(self):
        ref = RefModule.objects.create(intitule='Priorité ref', volume_horaire=30)
        module = _module(_formation(), intitule='Priorité ref', ref_module=ref, duree_prevue_heures=0)
        _session(module, 0, time(8, 0), time(18, 0))

        heures, source = resolve_module_duree_prevue_heures(module)
        self.assertEqual(heures, 30)
        self.assertEqual(source, 'ref_module')

    def test_ensure_persists_from_sessions_edt(self):
        module = _module(_formation(), duree_prevue_heures=0)
        _session(module, 0, time(8, 0), time(18, 0))
        _session(module, 1, time(8, 0), time(18, 0))
        _session(module, 2, time(8, 0), time(18, 0))

        heures, source = ensure_module_duree_prevue(module)
        module.refresh_from_db()

        self.assertEqual(heures, 30)
        self.assertEqual(source, 'sessions_edt')
        self.assertEqual(float(module.duree_prevue_heures), 30)

    def test_ensure_keeps_existing_value(self):
        module = _module(_formation(), duree_prevue_heures=28)
        _session(module, 0, time(8, 0), time(18, 0))

        heures, source = ensure_module_duree_prevue(module)
        module.refresh_from_db()

        self.assertEqual(heures, 28)
        self.assertIsNone(source)
        self.assertEqual(float(module.duree_prevue_heures), 28)

    def test_typical_hours_ignores_outlier_session(self):
        module = _module(_formation(), duree_prevue_heures=0)
        for day in range(5):
            _session(module, day, time(7, 30), time(12, 30))
        _session(module, 5, time(7, 30), time(13, 30))

        self.assertEqual(module_edt_raw_hours(module), 31)
        self.assertEqual(module_edt_typical_hours(module), 30)

    def test_ensure_corrects_raw_edt_mistake(self):
        module = _module(_formation(), duree_prevue_heures=31)
        for day in range(5):
            _session(module, day, time(7, 30), time(12, 30))
        _session(module, 5, time(13, 0), time(19, 0))

        heures, source = ensure_module_duree_prevue(module)
        module.refresh_from_db()

        self.assertEqual(heures, 30)
        self.assertEqual(source, 'sessions_edt')
        self.assertEqual(float(module.duree_prevue_heures), 30)
