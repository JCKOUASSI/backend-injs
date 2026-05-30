from datetime import time, timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Formation, Module, SessionModule, QRToken
from .session_views import _auto_manage_sessions, reactiver_session_et_qr


class SessionReactivationTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.local_now = timezone.localtime(self.now)
        self.today = self.local_now.date()
        self.formation = Formation.objects.create(formation='Formation réactivation')
        self.module = Module.objects.create(
            formation=self.formation,
            intitule='Module test',
            statut='TERMINEE',
        )
        past_fin = (
            self.local_now - timedelta(hours=2)
        ).time().replace(second=0, microsecond=0)
        self.session = SessionModule.objects.create(
            module=self.module,
            date_journee=self.today,
            numero=1,
            heure_fin_prevue=past_fin,
            demarree_le=self.now - timedelta(hours=4),
            terminee_le=self.now - timedelta(hours=1),
        )
        self.qr = QRToken.objects.create(
            session=self.session,
            expire_at=self.now + timedelta(hours=1),
            actif=False,
        )

    def test_reactivation_survives_auto_manage(self):
        reactiver_session_et_qr(self.session)
        self.session.refresh_from_db()
        self.qr.refresh_from_db()

        self.assertIsNone(self.session.terminee_le)
        self.assertTrue(self.qr.actif)
        self.assertGreater(self.session.heure_fin_prevue, self.local_now.time())

        _auto_manage_sessions(self.formation)
        self.session.refresh_from_db()
        self.qr.refresh_from_db()

        self.assertIsNone(self.session.terminee_le)
        self.assertTrue(self.qr.actif)

    def test_reactivation_bumps_past_date_to_today(self):
        yesterday = self.today - timedelta(days=1)
        self.session.date_journee = yesterday
        self.session.heure_fin_prevue = time(12, 0)
        self.session.save(update_fields=['date_journee', 'heure_fin_prevue'])

        reactiver_session_et_qr(self.session)
        self.session.refresh_from_db()

        self.assertEqual(self.session.date_journee, self.today)
        self.assertIsNone(self.session.terminee_le)

        _auto_manage_sessions(self.formation)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.terminee_le)
