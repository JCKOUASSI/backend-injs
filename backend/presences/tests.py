from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import User
from formations.models import Formation, Module, Participant, SessionModule, ModuleParticipant, QRToken
from .models import Pointage


def make_user(username, role='CPFAE_ADMIN'):
    return User.objects.create_user(username=username, password='pass', role=role)


def make_session(statut='PLANIFIEE'):
    f = Formation.objects.create(formation='Formation test')
    m = Module.objects.create(formation=f, intitule='Module test', statut=statut)
    s = SessionModule.objects.create(
        module=m,
        date_journee=timezone.localdate(),
        numero=1,
    )
    return f, m, s


# ──────────────────────────────────────────
# Modèle Pointage
# ──────────────────────────────────────────

class PointageModelTest(TestCase):

    def test_create_pointage_participant(self):
        f, m, s = make_session()
        p = Participant.objects.create(matricule='P001', nom='Test', prenom='User')
        pt = Pointage.objects.create(
            session=s,
            participant=p,
            date_journee=timezone.localdate(),
            timestamp_entree=timezone.now(),
        )
        self.assertIsNotNone(pt.pk)
        self.assertIsNone(pt.timestamp_sortie)

    def test_pointage_statut_default(self):
        f, m, s = make_session()
        p = Participant.objects.create(matricule='P002', nom='Test2', prenom='User2')
        pt = Pointage.objects.create(
            session=s,
            participant=p,
            date_journee=timezone.localdate(),
            timestamp_entree=timezone.now(),
        )
        self.assertEqual(pt.statut, 'EN_COURS')

    def test_pointage_cascade_delete_session(self):
        f, m, s = make_session()
        p = Participant.objects.create(matricule='P003', nom='Test3', prenom='User3')
        pt = Pointage.objects.create(
            session=s,
            participant=p,
            date_journee=timezone.localdate(),
            timestamp_entree=timezone.now(),
        )
        s.delete()
        self.assertFalse(Pointage.objects.filter(pk=pt.pk).exists())


# ──────────────────────────────────────────
# API — sessions (start / stop / delete)
# ──────────────────────────────────────────

class SessionAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user('presuser', role='CPFAE_ADMIN')
        self.client.force_authenticate(self.user)
        self.f, self.m, self.s = make_session()

    def test_session_start(self):
        res = self.client.post(f'/api/formations/{self.f.pk}/sessions/{self.s.pk}/start/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.s.refresh_from_db()
        self.assertIsNotNone(self.s.demarree_le)

    def test_session_start_unauthenticated(self):
        c = APIClient()
        res = c.post(f'/api/formations/{self.f.pk}/sessions/{self.s.pk}/start/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_stop_not_started(self):
        res = self.client.post(f'/api/formations/{self.f.pk}/sessions/{self.s.pk}/stop/')
        self.assertIn(res.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK))

    def test_session_stop_after_start(self):
        self.client.post(f'/api/formations/{self.f.pk}/sessions/{self.s.pk}/start/')
        res = self.client.post(f'/api/formations/{self.f.pk}/sessions/{self.s.pk}/stop/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.s.refresh_from_db()
        self.assertIsNotNone(self.s.terminee_le)

    def test_session_delete(self):
        res = self.client.delete(f'/api/formations/{self.f.pk}/sessions/{self.s.pk}/delete/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SessionModule.objects.filter(pk=self.s.pk).exists())

    def test_session_not_found(self):
        res = self.client.post(f'/api/formations/{self.f.pk}/sessions/99999/start/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────
# API — création de séance
# ──────────────────────────────────────────

class SessionCreateAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user('createuser', role='SECRETARIAT')
        self.client.force_authenticate(self.user)
        self.f, self.m, _ = make_session()

    def test_create_session(self):
        res = self.client.post(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/sessions/new/',
            {'date_journee': str(timezone.localdate()), 'intitule': 'Matin'},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SessionModule.objects.filter(module=self.m, intitule='Matin').exists())

    def test_create_session_missing_date(self):
        res = self.client.post(
            f'/api/formations/{self.f.pk}/modules/{self.m.pk}/sessions/new/',
            {'intitule': 'Sans date'},
        )
        self.assertIn(res.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED))


class ScanModuleExclusivityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()

        self.formation = Formation.objects.create(formation='Formation scan')
        self.module = Module.objects.create(
            formation=self.formation,
            intitule='Module scan',
            statut='EN_COURS',
        )
        self.participant = Participant.objects.create(
            matricule='P1001',
            nom='Doe',
            prenom='Jane',
        )
        ModuleParticipant.objects.create(module=self.module, participant=self.participant)

        self.seance_1 = SessionModule.objects.create(
            module=self.module,
            date_journee=self.today,
            numero=1,
            demarree_le=timezone.now(),
        )
        self.seance_2 = SessionModule.objects.create(
            module=self.module,
            date_journee=self.today,
            numero=2,
            demarree_le=timezone.now(),
        )
        self.token_seance_2 = QRToken.objects.create(
            session=self.seance_2,
            expire_at=timezone.now() + timedelta(hours=1),
            actif=True,
        )

    def test_public_scan_blocks_new_entry_when_other_session_open_same_module_same_day(self):
        Pointage.objects.create(
            participant=self.participant,
            session=self.seance_1,
            date_journee=self.today,
            timestamp_entree=timezone.now(),
            statut=Pointage.Statut.EN_COURS,
        )

        res = self.client.post(
            '/api/scan/',
            {
                'token_qr': str(self.token_seance_2.token),
                'numero_participant': self.participant.matricule,
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get('code'), 'SESSION_ALREADY_OPEN')

    def test_force_pointage_blocks_entry_when_other_session_open_same_module_same_day(self):
        user = make_user('secretariat_for_force', role='SECRETARIAT')
        self.client.force_authenticate(user)

        Pointage.objects.create(
            participant=self.participant,
            session=self.seance_1,
            date_journee=self.today,
            timestamp_entree=timezone.now(),
            statut=Pointage.Statut.EN_COURS,
        )

        res = self.client.post(
            f'/api/formations/{self.formation.pk}/force-pointage/',
            {
                'personne_id': self.participant.pk,
                'type_personne': 'participant',
                'action': 'ENTREE',
                'module_id': self.module.pk,
                'date_journee': str(self.today),
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('déjà en cours sur ce module', res.data.get('detail', ''))

    def test_secure_scan_blocks_new_entry_when_other_session_open_same_module_same_day(self):
        user = make_user('participant_scan_secure', role='PARTICIPANT')
        self.participant.user = user
        self.participant.save(update_fields=['user'])
        self.client.force_authenticate(user)

        Pointage.objects.create(
            participant=self.participant,
            session=self.seance_1,
            date_journee=self.today,
            timestamp_entree=timezone.now(),
            statut=Pointage.Statut.EN_COURS,
        )

        res = self.client.post(
            '/api/scan/secure/',
            {'token_qr': str(self.token_seance_2.token)},
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get('code'), 'SESSION_ALREADY_OPEN')

