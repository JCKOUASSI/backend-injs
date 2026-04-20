from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import User
from .models import (
    Formation, Module, Participant, Formateur,
    Secretariat, ModuleParticipant, ModuleFormateur,
)


def make_user(username, role='CPFAE_ADMIN', **kwargs):
    u = User.objects.create_user(username=username, password='pass', role=role, **kwargs)
    return u


def make_formation(titre='Cycle test'):
    return Formation.objects.create(formation=titre)


def make_module(formation, intitule='Module test', statut='PLANIFIEE', **kwargs):
    return Module.objects.create(formation=formation, intitule=intitule, statut=statut, **kwargs)


def make_participant(matricule='M001', nom='Dupont', prenom='Jean'):
    return Participant.objects.create(matricule=matricule, nom=nom, prenom=prenom)


def make_formateur(numero='F001', nom='Martin', prenom='Paul'):
    return Formateur.objects.create(numero=numero, nom=nom, prenom=prenom)


# ──────────────────────────────────────────
# Modèles
# ──────────────────────────────────────────

class FormationModelTest(TestCase):

    def test_creation(self):
        f = make_formation('Formation Alpha')
        self.assertEqual(str(f), 'Formation Alpha')
        self.assertIsNotNone(f.created_at)

    def test_modules_relation(self):
        f = make_formation()
        m1 = make_module(f, 'Mod A')
        m2 = make_module(f, 'Mod B')
        self.assertEqual(f.modules.count(), 2)

    def test_cascade_delete(self):
        f = make_formation()
        m = make_module(f)
        f.delete()
        self.assertEqual(Module.objects.filter(pk=m.pk).count(), 0)


class ModuleModelTest(TestCase):

    def setUp(self):
        self.f = make_formation()

    def test_str(self):
        m = make_module(self.f, 'Droit Admin')
        self.assertIn('Droit Admin', str(m))

    def test_statut_default(self):
        m = make_module(self.f)
        self.assertEqual(m.statut, 'PLANIFIEE')

    def test_statut_choices(self):
        for s in ('PLANIFIEE', 'EN_COURS', 'SUSPENDUE', 'TERMINEE'):
            m = make_module(self.f, statut=s)
            self.assertEqual(m.statut, s)

    def test_module_participant_unique(self):
        m = make_module(self.f)
        p = make_participant()
        ModuleParticipant.objects.create(module=m, participant=p)
        with self.assertRaises(Exception):
            ModuleParticipant.objects.create(module=m, participant=p)

    def test_module_formateur_unique(self):
        m = make_module(self.f)
        f = make_formateur()
        ModuleFormateur.objects.create(module=m, formateur=f)
        with self.assertRaises(Exception):
            ModuleFormateur.objects.create(module=m, formateur=f)


class SecretariatModelTest(TestCase):

    def test_auto_numero(self):
        s = Secretariat.objects.create(nom='Secrétariat A')
        self.assertTrue(s.numero.startswith('S'))

    def test_numero_unique(self):
        s1 = Secretariat.objects.create(nom='Sec 1')
        s2 = Secretariat.objects.create(nom='Sec 2')
        self.assertNotEqual(s1.numero, s2.numero)


# ──────────────────────────────────────────
# API — authentification requise
# ──────────────────────────────────────────

class APIAuthTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.f = make_formation()
        self.m = make_module(self.f)

    def test_module_list_unauthenticated(self):
        res = self.client.get(f'/api/formations/{self.f.pk}/modules/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_module_full_unauthenticated(self):
        res = self.client.get(f'/api/formations/{self.f.pk}/modules/{self.m.pk}/full/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_unauthenticated(self):
        res = self.client.get('/api/formations/stats/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# ──────────────────────────────────────────
# API — module CRUD
# ──────────────────────────────────────────

class ModuleAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin_module', role='CPFAE_ADMIN')
        self.client.force_authenticate(self.admin)
        self.f = make_formation()
        self.m = make_module(self.f, intitule='Module API', statut='PLANIFIEE')

    def test_list_modules(self):
        res = self.client.get(f'/api/formations/{self.f.pk}/modules/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_module(self):
        res = self.client.post(f'/api/formations/{self.f.pk}/modules/', {
            'intitule': 'Nouveau module',
            'statut': 'PLANIFIEE',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Module.objects.filter(intitule='Nouveau module').exists())

    def test_get_module_full(self):
        res = self.client.get(f'/api/formations/{self.f.pk}/modules/{self.m.pk}/full/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(data['intitule'], 'Module API')
        self.assertIn('sessions', data)
        self.assertIn('participants', data)
        self.assertIn('formateurs', data)
        self.assertIn('presences', data)

    def test_patch_module(self):
        res = self.client.patch(f'/api/formations/{self.f.pk}/modules/{self.m.pk}/', {
            'statut': 'EN_COURS',
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.m.refresh_from_db()
        self.assertEqual(self.m.statut, 'EN_COURS')

    def test_delete_module(self):
        res = self.client.delete(f'/api/formations/{self.f.pk}/modules/{self.m.pk}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Module.objects.filter(pk=self.m.pk).exists())

    def test_module_not_found(self):
        res = self.client.get(f'/api/formations/{self.f.pk}/modules/99999/full/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────
# API — add/remove participants
# ──────────────────────────────────────────

class ModuleParticipantAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin_mp', role='CPFAE_ADMIN')
        self.client.force_authenticate(self.admin)
        self.f = make_formation()
        self.m = make_module(self.f)
        self.p = make_participant()

    def test_add_participant(self):
        res = self.client.post(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/participants/add/',
            {'participant_id': self.p.pk},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ModuleParticipant.objects.filter(module=self.m, participant=self.p).exists())

    def test_add_participant_already_enrolled(self):
        ModuleParticipant.objects.create(module=self.m, participant=self.p)
        res = self.client.post(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/participants/add/',
            {'participant_id': self.p.pk},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_participant_missing_id(self):
        res = self.client.post(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/participants/add/',
            {},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_participant(self):
        ModuleParticipant.objects.create(module=self.m, participant=self.p)
        res = self.client.delete(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/participants/{self.p.pk}/remove/',
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ModuleParticipant.objects.filter(module=self.m, participant=self.p).exists())

    def test_remove_participant_not_found(self):
        res = self.client.delete(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/participants/99999/remove/',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────
# API — add/remove formateurs
# ──────────────────────────────────────────

class ModuleFormateurAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin_mf', role='CPFAE_ADMIN')
        self.client.force_authenticate(self.admin)
        self.f = make_formation()
        self.m = make_module(self.f)
        self.fmt = make_formateur()

    def test_add_formateur(self):
        res = self.client.post(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/formateurs/add/',
            {'formateur_id': self.fmt.pk},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ModuleFormateur.objects.filter(module=self.m, formateur=self.fmt).exists())

    def test_add_formateur_already_assigned(self):
        ModuleFormateur.objects.create(module=self.m, formateur=self.fmt)
        res = self.client.post(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/formateurs/add/',
            {'formateur_id': self.fmt.pk},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_formateur(self):
        ModuleFormateur.objects.create(module=self.m, formateur=self.fmt)
        res = self.client.delete(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/formateurs/{self.fmt.pk}/remove/',
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ModuleFormateur.objects.filter(module=self.m, formateur=self.fmt).exists())

    def test_remove_formateur_not_found(self):
        res = self.client.delete(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/formateurs/99999/remove/',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────
# API — dashboard stats
# ──────────────────────────────────────────

class DashboardStatsAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin_stats', role='CPFAE_ADMIN')
        self.client.force_authenticate(self.admin)
        f = make_formation()
        make_module(f, statut='EN_COURS', groupe='GROUPE 1')
        make_module(f, statut='EN_COURS', groupe='GROUPE 2')
        make_module(f, statut='PLANIFIEE')
        make_module(f, statut='TERMINEE')

    def test_stats_keys(self):
        res = self.client.get('/api/formations/stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for key in ('total_formations', 'formations_actives', 'formations_terminees',
                    'formations_planifiees', 'groupes_en_cours',
                    'total_participants', 'total_formateurs'):
            self.assertIn(key, res.data)

    def test_stats_counts(self):
        res = self.client.get('/api/formations/stats/')
        self.assertEqual(res.data['total_formations'], 4)
        self.assertEqual(res.data['formations_actives'], 2)
        self.assertEqual(res.data['formations_planifiees'], 1)
        self.assertEqual(res.data['formations_terminees'], 1)
        self.assertEqual(res.data['groupes_en_cours'], 2)


# ──────────────────────────────────────────
# API — referentiels
# ──────────────────────────────────────────

class ReferentielsAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        u = make_user('admin_ref', role='CPFAE_ADMIN')
        self.client.force_authenticate(u)

    def test_referentiels(self):
        res = self.client.get('/api/formations/referentiels/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for key in ('formations', 'modules', 'sites', 'batiments', 'salles', 'grades'):
            self.assertIn(key, res.data)

