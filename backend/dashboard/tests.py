from django.test import TestCase

from formations.models import Secretariat
from .views import _resolve_secretariat_from_matricule


class DashboardParticipantDispatchByMatriculeTest(TestCase):
    def setUp(self):
        self.sec_fab = Secretariat.objects.create(nom='FAB')
        self.sec_fac = Secretariat.objects.create(nom='FAC')

    def test_fnce_matricule_resolves_to_fab(self):
        sec = _resolve_secretariat_from_matricule('FNCE26-001')
        self.assertIsNotNone(sec)
        self.assertEqual(sec.id, self.sec_fab.id)

    def test_fncp_matricule_resolves_to_fac(self):
        sec = _resolve_secretariat_from_matricule('FNCP26-001')
        self.assertIsNotNone(sec)
        self.assertEqual(sec.id, self.sec_fac.id)

    def test_non_matching_matricule_returns_none(self):
        sec = _resolve_secretariat_from_matricule('ABCD26-001')
        self.assertIsNone(sec)
