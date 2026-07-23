"""Tests auth JWT et RBAC INJS."""
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User, GroupProfile
from apps.accounts.rbac import sync_module_permissions, make_perm
from apps.core.tests.test_utils import TEST_PASSWORD, create_student


class AuthLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='login@test.ci', password=TEST_PASSWORD,
            first_name='Jean', last_name='Kouassi',
        )

    def test_login_returns_tokens_and_permissions(self):
        response = self.client.post(reverse('token_obtain_pair'), {
            'email': 'login@test.ci',
            'password': TEST_PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'login@test.ci')
        self.assertIsInstance(response.data['permissions'], list)

    def test_login_invalid_password(self):
        response = self.client.post(reverse('token_obtain_pair'), {
            'email': 'login@test.ci',
            'password': 'wrong',
        }, format='json')
        self.assertEqual(response.status_code, 401)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 401)

    def test_me_returns_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'login@test.ci')


class RBACTests(TestCase):
    def setUp(self):
        sync_module_permissions()
        self.group = Group.objects.create(name='Responsable Scolarité')
        GroupProfile.objects.create(group=self.group, code='resp_sco', level=2)
        perm = Permission.objects.get(codename='students_view')
        self.group.permissions.add(perm)
        self.user = User.objects.create_user(
            email='sco@test.ci', password=TEST_PASSWORD,
            first_name='Sco', last_name='Larité',
        )
        self.user.groups.add(self.group)

    def test_has_module_permission_with_group_perm(self):
        self.assertTrue(self.user.has_module_permission('students', 'view'))
        self.assertFalse(self.user.has_module_permission('students', 'delete'))

    def test_superuser_has_all_permissions(self):
        admin = User.objects.create_superuser(
            email='admin@test.ci', password=TEST_PASSWORD,
            first_name='Admin', last_name='Test',
        )
        self.assertTrue(admin.has_module_permission('finance', 'create'))
        self.assertIn('finance.create', admin.get_permission_codes())

    def test_student_contextual_permission(self):
        student_group = Group.objects.create(name='Étudiant')
        GroupProfile.objects.create(group=student_group, code='etudiant', level=4)
        _, student = create_student(email='ctx@test.ci', matricule='CTX001')
        student.user.groups.add(student_group)

        self.assertTrue(
            student.user.has_module_permission(
                'students', 'view', context={'student_id': str(student.id)}
            )
        )
        self.assertFalse(
            student.user.has_module_permission(
                'students', 'view', context={'student_id': '00000000-0000-0000-0000-000000000000'}
            )
        )

    def test_make_perm_format(self):
        self.assertEqual(make_perm('exams', 'create'), 'accounts.exams_create')

    def test_group_level_from_profile(self):
        self.assertEqual(self.user.get_group_level(), 2)
