from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import User
from formations.models import (
    Formation,
    Module,
    Participant,
    Formateur,
    Secretariat,
    SessionModule,
    ModuleParticipant,
    ModuleFormateur,
    QRToken,
)
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

        self.secretariat = Secretariat.objects.create(nom='Sec scan test')
        self.formation = Formation.objects.create(formation='Formation scan')
        self.module = Module.objects.create(
            formation=self.formation,
            intitule='Module scan',
            statut='EN_COURS',
            secretariat=self.secretariat,
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

    def test_public_scan_accepts_participant_identifier_with_spaces(self):
        # seance_1 doit être terminée pour que seance_2 soit accessible
        self.seance_1.terminee_le = timezone.now()
        self.seance_1.save(update_fields=['terminee_le'])

        res = self.client.post(
            '/api/scan/',
            {
                'token_qr': str(self.token_seance_2.token),
                'numero_participant': 'P 1001',
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data.get('type_personne'), 'participant')
        self.assertEqual(
            res.data.get('participant', {}).get('numero'),
            self.participant.matricule,
        )

    def test_force_pointage_blocks_entry_when_other_session_open_same_module_same_day(self):
        user = make_user('secretariat_for_force', role='SECRETARIAT')
        user.secretariat = self.secretariat
        user.save(update_fields=['secretariat'])
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
                'motif': 'Test: ouverture déjà existante',
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('déjà en cours sur ce module', res.data.get('detail', ''))

    def test_force_pointage_requires_motif(self):
        user = make_user('secretariat_for_force_motif', role='SECRETARIAT')
        user.secretariat = self.secretariat
        user.save(update_fields=['secretariat'])
        self.client.force_authenticate(user)

        res = self.client.post(
            f'/api/formations/{self.formation.pk}/force-pointage/',
            {
                'personne_id': self.participant.pk,
                'type_personne': 'participant',
                'action': 'ENTREE',
                'module_id': self.module.pk,
                'date_journee': str(self.today),
                # motif manquant
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motif', res.data)

    def test_force_pointage_entry_creates_pointage_and_logs_motif(self):
        from presences.models import AuditLog, Pointage

        user = make_user('secretariat_for_force_ok', role='SECRETARIAT')
        user.secretariat = self.secretariat
        user.save(update_fields=['secretariat'])
        self.client.force_authenticate(user)

        motif = 'Rattrapage — badge cassé'
        res = self.client.post(
            f'/api/formations/{self.formation.pk}/force-pointage/',
            {
                'personne_id': self.participant.pk,
                'type_personne': 'participant',
                'action': 'ENTREE',
                'module_id': self.module.pk,
                'date_journee': str(self.today),
                'motif': motif,
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        pointage_id = res.data.get('pointage', {}).get('id')
        self.assertTrue(Pointage.objects.filter(pk=pointage_id, statut=Pointage.Statut.FORCE_DFRC).exists())
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.FORCE_ENTREE, pointage_id=pointage_id, extra__motif=motif).exists()
        )

    def test_force_badgeage_auditeurs_bulk_applies_ratio(self):
        from presences.models import AuditLog

        user = make_user('bulk_force_user', role='CPFAE_ADMIN')
        self.client.force_authenticate(user)

        participants = []
        for i in range(10):
            p = Participant.objects.create(matricule=f'BULK{i:03d}', nom=f'N{i}', prenom=f'P{i}')
            ModuleParticipant.objects.create(module=self.module, participant=p)
            participants.append(p)

        self.seance_1.terminee_le = timezone.now()
        self.seance_1.save(update_fields=['terminee_le'])

        with patch('presences.bulk_force_auditeurs.random.uniform', return_value=0.90):
            res = self.client.post(
                f'/api/formations/{self.formation.pk}/force-badgeage-auditeurs-bulk/',
                {
                    'module_id': self.module.pk,
                    'session_id': self.seance_2.pk,
                    'date_journee': str(self.today),
                    'motif': 'Test forçage masse 90%',
                },
                format='json',
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # 11 auditeurs absents (10 créés + P1001) × 90 % ≈ 10 entrées forcées
        expected = max(1, round(11 * 0.90))
        self.assertEqual(res.data['total_badges'], expected)
        self.assertEqual(
            Pointage.objects.filter(session=self.seance_2, statut=Pointage.Statut.FORCE_DFRC).count(),
            expected,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.FORCE_ENTREE,
                extra__bulk_force_auditeurs=True,
            ).exists()
        )

    def test_secure_scan_blocks_new_entry_when_other_session_open_same_module_same_day(self):
        user = make_user(self.participant.matricule, role='AUDITEUR')
        user.matricule = self.participant.matricule
        user.save(update_fields=['matricule'])
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.user_id, user.id)
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


class ScanFormateurBadgeNormalizationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()

        self.formation = Formation.objects.create(formation='Formation formateur')
        self.module = Module.objects.create(
            formation=self.formation,
            intitule='Module formateur',
            statut='EN_COURS',
        )
        self.seance = SessionModule.objects.create(
            module=self.module,
            date_journee=self.today,
            numero=1,
            demarree_le=timezone.now(),
        )
        self.token = QRToken.objects.create(
            session=self.seance,
            expire_at=timezone.now() + timedelta(hours=1),
            actif=True,
        )
        self.formateur = Formateur.objects.create(
            numerobadge='F0042',
            nom='Kouadio',
            prenom='Jean',
        )
        ModuleFormateur.objects.create(module=self.module, formateur=self.formateur)

    def test_scan_formateur_accepts_lowercase_badge(self):
        res = self.client.post(
            '/api/scan/',
            {
                'token_qr': str(self.token.token),
                'numero_participant': 'f0042',
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data.get('type_personne'), 'formateur')
        self.assertEqual(
            res.data.get('formateur', {}).get('numero'),
            self.formateur.numerobadge,
        )

    def test_scan_formateur_accepts_numeric_short_badge(self):
        res = self.client.post(
            '/api/scan/',
            {
                'token_qr': str(self.token.token),
                'numero_participant': '42',
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data.get('type_personne'), 'formateur')


class SecureScanFormateurEncadrantTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()

        self.formation = Formation.objects.create(formation='Formation mobile')
        self.module = Module.objects.create(
            formation=self.formation,
            intitule='Module mobile',
            statut='EN_COURS',
        )
        self.seance = SessionModule.objects.create(
            module=self.module,
            date_journee=self.today,
            numero=1,
            demarree_le=timezone.now(),
        )
        self.token = QRToken.objects.create(
            session=self.seance,
            expire_at=timezone.now() + timedelta(hours=1),
            actif=True,
        )

        self.formateur = Formateur.objects.create(
            numerobadge='F0099',
            nom='Traoré',
            prenom='Awa',
        )
        ModuleFormateur.objects.create(module=self.module, formateur=self.formateur)
        self.formateur_user = make_user('F0099', role='FORMATEUR')
        self.formateur_user.matricule = 'F0099'
        self.formateur_user.save(update_fields=['matricule'])
        self.formateur.user = self.formateur_user
        self.formateur.save(update_fields=['user'])

        self.encadrant = make_user('encadrant_mobile', role='ENCADRANT')
        self.encadrant.matricule = 'ENC001'
        self.encadrant.first_name = 'Paul'
        self.encadrant.last_name = 'Koné'
        self.encadrant.save(update_fields=['matricule', 'first_name', 'last_name'])
        self.module.superviseur = self.encadrant
        self.module.save(update_fields=['superviseur'])

    def test_secure_scan_formateur_entree(self):
        self.client.force_authenticate(self.formateur_user)
        res = self.client.post(
            '/api/scan/secure/',
            {'token_qr': str(self.token.token), 'device_id': 'test-device-fmt'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data.get('action'), 'ENTREE')
        self.assertEqual(res.data.get('type_personne'), 'formateur')
        self.assertTrue(
            Pointage.objects.filter(
                formateur=self.formateur,
                session=self.seance,
                timestamp_sortie__isnull=True,
            ).exists()
        )

    def test_secure_scan_encadrant_entree(self):
        self.client.force_authenticate(self.encadrant)
        res = self.client.post(
            '/api/scan/secure/',
            {'token_qr': str(self.token.token), 'device_id': 'test-device-enc'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data.get('action'), 'ENTREE')
        self.assertEqual(res.data.get('type_personne'), 'encadrant')
        self.assertTrue(
            Pointage.objects.filter(
                encadrant=self.encadrant,
                session=self.seance,
                timestamp_sortie__isnull=True,
            ).exists()
        )

    def test_resolve_personne_prioritizes_encadrant_role_over_participant_profile(self):
        participant = Participant.objects.create(
            matricule='P9999',
            nom='Dupont',
            prenom='Marie',
        )
        participant.user = self.encadrant
        participant.save(update_fields=['user'])

        self.client.force_authenticate(self.encadrant)
        res = self.client.post(
            '/api/scan/secure/',
            {'token_qr': str(self.token.token), 'device_id': 'test-device-enc2'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data.get('type_personne'), 'encadrant')


class VolumeHoraireFicheStatsTest(TestCase):

    def test_effectue_ne_depasse_pas_prevu(self):
        from presences.views import _compute_volume_horaire_stats

        f = Formation.objects.create(formation='F')
        m_inscrit = Module.objects.create(
            formation=f, intitule='Inscrit', duree_prevue_heures=10,
        )
        m_hors = Module.objects.create(
            formation=f, intitule='Hors inscription', duree_prevue_heures=50,
        )
        s1 = SessionModule.objects.create(
            module=m_inscrit, date_journee=timezone.localdate(), numero=1,
        )
        s2 = SessionModule.objects.create(
            module=m_hors, date_journee=timezone.localdate(), numero=1,
        )
        p = Participant.objects.create(matricule='VH001', nom='A', prenom='B')
        ModuleParticipant.objects.create(module=m_inscrit, participant=p)
        entree = timezone.now() - timedelta(hours=20)
        Pointage.objects.create(
            session=s1,
            participant=p,
            date_journee=timezone.localdate(),
            timestamp_entree=entree,
            timestamp_sortie=timezone.now(),
            duree_presence_minutes=20 * 60,
        )
        Pointage.objects.create(
            session=s2,
            participant=p,
            date_journee=timezone.localdate(),
            timestamp_entree=entree,
            timestamp_sortie=timezone.now(),
            duree_presence_minutes=30 * 60,
        )
        modules_data = [{'id': m_inscrit.id, 'duree_prevue_heures': 10}]
        pointages_qs = Pointage.objects.filter(participant=p)
        stats = _compute_volume_horaire_stats(modules_data, pointages_qs)

        self.assertEqual(stats['volume_horaire_total_heures'], 10.0)
        self.assertEqual(stats['volume_horaire_effectue_heures'], 10.0)
        self.assertEqual(stats['volume_horaire_effectue_taux'], 100.0)

    def test_total_prevu_deduplique_par_module(self):
        from presences.views import _compute_volume_horaire_stats

        f = Formation.objects.create(formation='F')
        m = Module.objects.create(formation=f, intitule='M', duree_prevue_heures=12)
        modules_data = [
            {'id': m.id, 'duree_prevue_heures': 12},
            {'id': m.id, 'duree_prevue_heures': 8},
        ]
        stats = _compute_volume_horaire_stats(modules_data, Pointage.objects.none())
        self.assertEqual(stats['volume_horaire_total_heures'], 12.0)

