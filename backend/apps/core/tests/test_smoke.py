"""Smoke tests — endpoints principaux des modules secondaires."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


class ModuleSmokeTests(TestCase):
    """Vérifie que les routes clés répondent (auth requise, pas d'erreur 500)."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='smoke@test.ci', password='Test@INJS2026!',
            first_name='Smoke', last_name='Test',
        )
        self.client.force_authenticate(user=self.admin)

    def _assert_authenticated_ok_or_empty(self, url_name, **kwargs):
        url = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)
        response = self.client.get(url)
        self.assertIn(response.status_code, (200, 404))

    def test_faculty_teachers_list(self):
        self._assert_authenticated_ok_or_empty('teacher-list')

    def test_admissions_campaigns_list(self):
        self._assert_authenticated_ok_or_empty('admissioncampaign-list')

    def test_documents_list(self):
        self._assert_authenticated_ok_or_empty('document-list')

    def test_notifications_list(self):
        self._assert_authenticated_ok_or_empty('notification-list')

    def test_messaging_conversations_list(self):
        self._assert_authenticated_ok_or_empty('conversation-list')

    def test_library_resources_list(self):
        self._assert_authenticated_ok_or_empty('library-resource-list')

    def test_reports_analytics(self):
        self._assert_authenticated_ok_or_empty('analytics')

    def test_reports_statistics(self):
        self._assert_authenticated_ok_or_empty('academic-statistics')

    def test_academics_cours_list(self):
        self._assert_authenticated_ok_or_empty('cours-list')

    def test_exams_sessions_list(self):
        self._assert_authenticated_ok_or_empty('examsession-list')
