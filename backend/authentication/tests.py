from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from .role_groups import ROLE_GROUP_NAMES, ensure_role_groups

User = get_user_model()

URL = '/api/auth/me/change-password/'
USERS_URL = '/api/auth/users/'


def make_user(username='testuser', password='oldpass123', role='SECRETARIAT'):
    u = User.objects.create_user(username=username, password=password)
    u.role = role
    u.save()
    return u


class ChangePasswordTests(TestCase):

    def setUp(self):
        self.password = 'oldpass123'
        self.user = make_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # ── happy path ──────────────────────────────────────────────────────────

    def test_change_password_success(self):
        """Valid old + new password → 200 + detail message."""
        resp = self.client.post(URL, {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('detail', resp.data)

        # token invalide après changement du mdp ? Non — on vérifie juste que le hash a changé
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))
        self.assertFalse(self.user.check_password('oldpass123'))

    # ── mauvais ancien mot de passe ─────────────────────────────────────────

    def test_wrong_old_password(self):
        """Incorrect old_password → 400 with field error."""
        resp = self.client.post(URL, {
            'old_password': 'wrongpass!',
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('old_password', resp.data)

    # ── nouveau = ancien ────────────────────────────────────────────────────

    def test_new_same_as_old(self):
        """new_password identical to old_password → 400."""
        resp = self.client.post(URL, {
            'old_password': 'oldpass123',
            'new_password': 'oldpass123',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('new_password', resp.data)

    # ── mot de passe trop court ─────────────────────────────────────────────

    def test_new_password_too_short(self):
        """new_password shorter than 8 chars → 400."""
        resp = self.client.post(URL, {
            'old_password': 'oldpass123',
            'new_password': 'abc',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('new_password', resp.data)

    # ── champs manquants ────────────────────────────────────────────────────

    def test_missing_old_password(self):
        """Missing old_password → 400."""
        resp = self.client.post(URL, {'new_password': 'newpass456'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('old_password', resp.data)

    def test_missing_new_password(self):
        """Missing new_password → 400."""
        resp = self.client.post(URL, {'old_password': 'oldpass123'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('new_password', resp.data)

    # ── non authentifié ─────────────────────────────────────────────────────

    def test_unauthenticated(self):
        """No token → 401."""
        anon = APIClient()
        resp = anon.post(URL, {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    # ── tous rôles peuvent changer leur mdp ─────────────────────────────────

    def test_auditeur_can_change_password(self):
        """AUDITEUR role can also change password."""
        u = make_user(username='auditeur1', password='oldpass123', role='AUDITEUR')
        c = APIClient()
        c.force_authenticate(user=u)
        resp = c.post(URL, {
            'old_password': 'oldpass123',
            'new_password': 'newpass789',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        u.refresh_from_db()
        self.assertTrue(u.check_password('newpass789'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class WelcomeEmailTests(TestCase):
    """Tests pour l'envoi d'email de bienvenue lors de la création d'un utilisateur."""

    def setUp(self):
        self.admin = make_user(username='email_admin', password='adminpass', role='CHEF_CPFAE_ADMIN')
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    # ── email envoyé si adresse renseignée ──────────────────────────────────

    def test_welcome_email_sent_when_email_provided(self):
        """Créer un utilisateur avec email → 1 email envoyé."""
        resp = self.client.post(USERS_URL, {
            'username': 'newuser1',
            'password': 'pass1234!',
            'email': 'newuser1@example.com',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'role': 'SECRETARIAT',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('newuser1@example.com', sent.to)
        self.assertIn('newuser1', sent.body)
        self.assertIn('pass1234!', sent.body)

    def test_welcome_email_contains_credentials(self):
        """Le corps de l'email contient bien le username et le mot de passe en clair."""
        self.client.post(USERS_URL, {
            'username': 'usertest',
            'password': 'monSecret9',
            'email': 'usertest@example.com',
            'role': 'ENCADRANT',
        }, format='json')
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('usertest', body)
        self.assertIn('monSecret9', body)

    # ── pas d'email si adresse absente ──────────────────────────────────────

    def test_no_email_sent_when_no_email(self):
        """Créer un utilisateur sans email → aucun email envoyé."""
        resp = self.client.post(USERS_URL, {
            'username': 'noemail',
            'password': 'pass1234!',
            'role': 'ENCADRANT',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(mail.outbox), 0)

    # ── plusieurs créations → autant d'emails ───────────────────────────────

    def test_each_user_gets_own_email(self):
        """Deux utilisateurs avec email → deux emails distincts."""
        for i in range(2):
            self.client.post(USERS_URL, {
                'username': f'user{i}',
                'password': 'pass1234!',
                'email': f'user{i}@example.com',
                'role': 'ENCADRANT',
            }, format='json')
        self.assertEqual(len(mail.outbox), 2)
        recipients = [m.to[0] for m in mail.outbox]
        self.assertIn('user0@example.com', recipients)
        self.assertIn('user1@example.com', recipients)


class RoleGroupsTest(TestCase):

    def setUp(self):
        ensure_role_groups()

    def test_creates_one_group_per_role(self):
        for group_name in ROLE_GROUP_NAMES.values():
            self.assertTrue(
                Group.objects.filter(name=group_name).exists(),
                f"Groupe manquant: {group_name}",
            )

    def test_assign_group_on_user_create(self):
        user = make_user(username='group-user-create', role=User.Role.SECRETARIAT)
        self.assertTrue(user.groups.filter(name=ROLE_GROUP_NAMES[User.Role.SECRETARIAT]).exists())

    def test_move_group_on_role_change(self):
        user = make_user('group-user-update', role=User.Role.AUDITEUR)
        old_group = ROLE_GROUP_NAMES[User.Role.AUDITEUR]
        new_group = ROLE_GROUP_NAMES[User.Role.ENCADRANT]

        self.assertTrue(user.groups.filter(name=old_group).exists())

        user.role = User.Role.ENCADRANT
        user.save()

        self.assertFalse(user.groups.filter(name=old_group).exists())
        self.assertTrue(user.groups.filter(name=new_group).exists())

