from datetime import timedelta, time as dt_time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import User
from .models import (
    Formation, Module, Participant, Formateur,
    Secretariat, ModuleParticipant, ModuleFormateur, SessionModule, RefModule,
)
from .volume_horaire import compute_dashboard_volume_horaire


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
    return Formateur.objects.create(numerobadge=numero, nom=nom, prenom=prenom)


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
        for key in ('total_modules', 'modules_en_cours', 'modules_termines',
                    'modules_planifies', 'groupes_en_cours',
                    'total_participants', 'total_formateurs'):
            self.assertIn(key, res.data)

    def test_stats_counts(self):
        res = self.client.get('/api/formations/stats/')
        self.assertEqual(res.data['total_modules'], 4)
        self.assertEqual(res.data['modules_en_cours'], 2)
        self.assertEqual(res.data['modules_planifies'], 1)
        self.assertEqual(res.data['modules_termines'], 1)
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
        for key in ('formations', 'modules', 'sites', 'batiments', 'salles', 'grades', 'groupes', 'grades_modules'):
            self.assertIn(key, res.data)


# ──────────────────────────────────────────
# API — dispatch secrétariat par matricule
# ──────────────────────────────────────────

class ParticipantSecretariatDispatchByMatriculeAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_user('admin_dispatch_matricule', role='CPFAE_ADMIN')
        self.client.force_authenticate(self.admin)
        self.sec_fab = Secretariat.objects.create(nom='FAB')
        self.sec_fac = Secretariat.objects.create(nom='FAC')

    def test_create_participant_fnce_sets_fab_secretariat(self):
        res = self.client.post('/api/formations/participants/', {
            'matricule': 'FNCE26-001',
            'nom': 'KOUAME',
            'prenom': 'Jean',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        participant = Participant.objects.get(matricule='FNCE26-001')
        self.assertEqual(participant.secretariat_id, self.sec_fab.id)

    def test_create_participant_fncp_sets_fac_secretariat(self):
        res = self.client.post('/api/formations/participants/', {
            'matricule': 'FNCP26-001',
            'nom': 'DIALLO',
            'prenom': 'Mariam',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        participant = Participant.objects.get(matricule='FNCP26-001')
        self.assertEqual(participant.secretariat_id, self.sec_fac.id)

    def test_update_participant_matricule_fncp_reassigns_to_fac(self):
        participant = Participant.objects.create(
            matricule='M0001',
            nom='TRAORE',
            prenom='Fatou',
            secretariat=self.sec_fab,
        )
        res = self.client.patch(f'/api/formations/participants/{participant.pk}/', {
            'matricule': 'FNCP26-777',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        participant.refresh_from_db()
        self.assertEqual(participant.secretariat_id, self.sec_fac.id)


class DashboardVolumeHoraireTest(TestCase):

    def test_prevu_contractuel_independant_edt(self):
        f = make_formation()
        module = make_module(f, duree_prevue_heures=10)
        now = timezone.now()
        for num in range(1, 3):
            SessionModule.objects.create(
                module=module,
                date_journee=timezone.localdate(),
                numero=num,
                demarree_le=now - timedelta(hours=5),
                terminee_le=now,
                heure_debut_prevue=dt_time(8, 0),
                heure_fin_prevue=dt_time(13, 0),
            )
        effectue, total, taux = compute_dashboard_volume_horaire(
            Module.objects.filter(pk=module.pk)
        )
        self.assertEqual(total, 10)
        self.assertEqual(effectue, 10)
        self.assertEqual(taux, 100)

        session = SessionModule.objects.filter(module=module).first()
        session.heure_fin_prevue = dt_time(18, 0)
        session.save(update_fields=['heure_fin_prevue'])
        effectue2, total2, taux2 = compute_dashboard_volume_horaire(
            Module.objects.filter(pk=module.pk)
        )
        self.assertEqual(total2, 10)
        self.assertEqual(effectue2, 10)
        self.assertEqual(taux2, 100)

    def test_realise_plafonne_au_prevu_seance(self):
        """Une séance laissée ouverte ne compte pas plus que son créneau planifié."""
        from .volume_horaire import _accumulate_module_session_volumes

        f = make_formation()
        module = make_module(f, duree_prevue_heures=12)
        SessionModule.objects.create(
            module=module,
            date_journee=timezone.localdate(),
            numero=1,
            demarree_le=timezone.now() - timedelta(days=5),
            terminee_le=timezone.now(),
            heure_debut_prevue=dt_time(8, 0),
            heure_fin_prevue=dt_time(12, 0),
        )
        vol = _accumulate_module_session_volumes(module)
        self.assertEqual(vol['prevu_h'], 12.0)
        self.assertEqual(vol['prevu_edt_h'], 4.0)
        self.assertEqual(vol['realise_h'], 4.0)
        self.assertEqual(vol['ecart_h'], -8.0)

    def test_volume_horaire_canonique_aligne_stats_et_dashboard(self):
        from .volume_horaire import (
            compute_volume_horaire_from_modules,
            compute_dashboard_volume_horaire,
        )

        f = make_formation()
        module = make_module(f, duree_prevue_heures=3)
        now = timezone.now()
        SessionModule.objects.create(
            module=module,
            date_journee=timezone.localdate(),
            numero=1,
            demarree_le=now - timedelta(hours=3),
            terminee_le=now,
            heure_debut_prevue=dt_time(8, 0),
            heure_fin_prevue=dt_time(11, 0),
        )
        qs = Module.objects.filter(pk=module.pk)
        dash = compute_dashboard_volume_horaire(qs)
        canon = compute_volume_horaire_from_modules(qs)
        self.assertEqual(dash[1], canon['prevu_heures'])
        self.assertEqual(dash[0], canon['realise_heures'])


class ModuleRefModuleLinkTest(TestCase):

    def test_link_ref_module_on_create(self):
        f = make_formation()
        module = make_module(f, intitule='Déontologie')
        module.link_ref_module()
        module.refresh_from_db()
        self.assertIsNotNone(module.ref_module_id)
        self.assertEqual(module.ref_module.intitule, 'Déontologie')
        self.assertEqual(module.canonical_intitule(), 'Déontologie')


class RefModuleUniqueIntituleTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user('ref_admin')
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse('api-ref-module-list')

    def test_create_duplicate_case_insensitive_rejected(self):
        RefModule.objects.create(intitule='Déontologie')
        response = self.client.post(self.list_url, {'intitule': 'DÉONTOLOGIE', 'actif': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('intitule', response.data)

    def test_update_to_existing_intitule_case_insensitive_rejected(self):
        first = RefModule.objects.create(intitule='Gestion budgétaire')
        second = RefModule.objects.create(intitule='Communication')
        url = reverse('api-ref-module-detail', args=[second.pk])
        response = self.client.put(url, {'intitule': 'GESTION BUDGÉTAIRE', 'actif': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('intitule', response.data)
        second.refresh_from_db()
        self.assertEqual(second.intitule, 'Communication')
        self.assertEqual(first.intitule, 'Gestion budgétaire')

    def test_update_same_intitule_different_case_allowed(self):
        module = RefModule.objects.create(intitule='Planification')
        url = reverse('api-ref-module-detail', args=[module.pk])
        response = self.client.put(url, {'intitule': 'PLANIFICATION', 'actif': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        module.refresh_from_db()
        self.assertEqual(module.intitule, 'PLANIFICATION')


class ParticipantFormationsScopeAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.sec_a = Secretariat.objects.create(nom='Sec A')
        self.sec_b = Secretariat.objects.create(nom='Sec B')
        self.secretariat_user = make_user('sec-scope', role='SECRETARIAT', secretariat=self.sec_a)
        self.f_a = make_formation('Formation A')
        self.f_b = make_formation('Formation B')
        self.mod_a = make_module(self.f_a, intitule='Mod A', secretariat=self.sec_a)
        self.mod_b = make_module(self.f_b, intitule='Mod B', secretariat=self.sec_b)
        self.participant = make_participant(matricule='P-SCOPE')
        ModuleParticipant.objects.create(module=self.mod_a, participant=self.participant)
        ModuleParticipant.objects.create(module=self.mod_b, participant=self.participant)

    def test_secretariat_only_sees_modules_in_own_perimeter(self):
        self.client.force_authenticate(self.secretariat_user)
        res = self.client.get(f'/api/formations/participants/{self.participant.pk}/formations/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], self.mod_a.id)

    def test_secretariat_cannot_read_participant_outside_perimeter(self):
        outsider = make_participant(matricule='P-OUT')
        ModuleParticipant.objects.create(module=self.mod_b, participant=outsider)
        self.client.force_authenticate(self.secretariat_user)
        res = self.client.get(f'/api/formations/participants/{outsider.pk}/formations/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class FormateurListScopeAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.sec_a = Secretariat.objects.create(nom='Sec Form A')
        self.sec_b = Secretariat.objects.create(nom='Sec Form B')
        self.secretariat_user = make_user('sec-form', role='SECRETARIAT', secretariat=self.sec_a)
        self.formateur_a = make_formateur(numero='FA001', nom='Alpha', prenom='Form')
        self.formateur_b = make_formateur(numero='FB001', nom='Beta', prenom='Form')
        self.formateur_a.secretariats.add(self.sec_a)
        self.formateur_b.secretariats.add(self.sec_b)

    def test_secretariat_formateur_list_scoped(self):
        self.client.force_authenticate(self.secretariat_user)
        res = self.client.get('/api/formations/formateurs/list/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {item['id'] for item in res.data['results']}
        self.assertIn(self.formateur_a.id, ids)
        self.assertNotIn(self.formateur_b.id, ids)

