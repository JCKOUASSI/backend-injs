"""Tests API étudiants INJS."""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics.models import StapsJobNomenclature
from apps.academics.nomenclature_parser import DEFAULT_NOMENCLATURE_PATH
from apps.accounts.models import User
from apps.core.tests.test_utils import (
    TEST_PASSWORD, create_institution_bundle, create_specializations,
    create_student, create_students_viewer,
)


class StudentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        _, _, self.program, self.promotion, _ = create_institution_bundle()
        specs = create_specializations()
        call_command('import_nomenclature_staps', f'--file={DEFAULT_NOMENCLATURE_PATH}')
        self.admin = User.objects.create_superuser(
            email='admin-students@test.ci', password=TEST_PASSWORD,
            first_name='Admin', last_name='Students',
        )
        _, self.student = create_student(
            email='student-api@test.ci', matricule='API001',
            program=self.program, promotion=self.promotion,
            specialization=specs['APA'],
        )
        self.client.force_authenticate(user=self.admin)

    def test_student_list(self):
        response = self.client.get(reverse('student-list'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_student_card(self):
        url = reverse('student-card', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['matricule'], 'API001')
        self.assertIn('full_name', response.data)
        self.assertIn('INJS', response.data['institution'])

    def test_career_path_with_specialization(self):
        url = reverse('student-career-path', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['diploma_code'], 'CAPCS')
        self.assertEqual(response.data['civil_service_grade'], 'A3')
        self.assertTrue(
            StapsJobNomenclature.objects.filter(
                degree_type='L', specialization__code='APA'
            ).exists()
        )

    def test_career_path_without_specialization(self):
        self.student.specialization = None
        self.student.save(update_fields=['specialization'])
        url = reverse('student-career-path', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)

    def test_student_requires_permission(self):
        viewer = create_students_viewer()
        outsider = viewer.__class__.objects.create_user(
            email='no.perm@test.ci', password=TEST_PASSWORD,
            first_name='No', last_name='Perm',
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.get(reverse('student-list'))
        self.assertEqual(response.status_code, 403)
