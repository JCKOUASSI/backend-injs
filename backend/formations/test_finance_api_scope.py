"""Périmètre API FINANCE : accès module finance uniquement, pas aux endpoints opérationnels."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Formation, Module

User = get_user_model()


class FinanceApiScopeTest(TestCase):
    """FINANCE ne doit pas accéder aux endpoints opérationnels du dashboard formations."""

    def setUp(self):
        self.finance = User.objects.create_user(
            username='finance_scope', password='test', role='FINANCE',
        )
        self.secretariat = User.objects.create_user(
            username='sec_scope', password='test', role='SECRETARIAT',
        )
        self.formation = Formation.objects.create(formation='Cycle test')
        self.module = Module.objects.create(
            formation=self.formation,
            intitule='Module test',
            statut='PLANIFIEE',
        )
        self.client = APIClient()

    def test_finance_blocked_on_operational_endpoints(self):
        self.client.force_authenticate(user=self.finance)
        blocked = [
            '/api/formations/stats/',
            '/api/formations/list/',
            f'/api/formations/{self.formation.pk}/detail/',
            f'/api/formations/{self.formation.pk}/modules/{self.module.pk}/full/',
            '/api/formations/referentiels/',
        ]
        for url in blocked:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 403, msg=url)

    def test_finance_allowed_on_finance_endpoints(self):
        self.client.force_authenticate(user=self.finance)
        allowed = [
            '/api/formations/finance/dashboard/',
            '/api/formations/finance/settings/',
            '/api/formations/formateurs/finance-report/',
            '/api/formations/finance/encadrants/',
            '/api/formations/finance/ajustements/',
        ]
        for url in allowed:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, msg=url)

    def test_operational_staff_still_access_dashboard_stats(self):
        self.client.force_authenticate(user=self.secretariat)
        res = self.client.get('/api/formations/stats/')
        self.assertEqual(res.status_code, 200)

    def test_formation_accessible_denies_finance(self):
        from .access import formation_accessible

        self.assertIsNone(formation_accessible(self.finance, self.formation.pk))
