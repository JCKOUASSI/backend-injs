from datetime import date

from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from apps.faculty.services.session_qr import (
    build_badge_url,
    build_session_payload,
    frontend_base_url,
    parse_session_payload,
    SessionQrError,
    validate_session_date,
    ensure_sessions_for_date,
)
from apps.faculty.models import Schedule, AttendanceSession


class SessionQrServiceTests(TestCase):
    def test_build_and_parse_payload(self):
        schedule_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
        session_date = date(2026, 7, 10)
        payload = build_session_payload(schedule_id, session_date)
        parsed_id, parsed_date = parse_session_payload(payload)
        self.assertEqual(parsed_id, schedule_id)
        self.assertEqual(parsed_date, session_date)

    def test_parse_invalid_payload(self):
        with self.assertRaises(SessionQrError):
            parse_session_payload('INJS:bad')

    def test_validate_session_date_wrong_weekday(self):
        schedule = Schedule(day_of_week=0)  # Lundi
        with self.assertRaises(SessionQrError):
            # 2026-07-10 is a Friday (weekday 4)
            validate_session_date(schedule, date(2026, 7, 10))

    def test_ensure_sessions_skips_sunday(self):
        # Dimanche : pas de créneau dans l'emploi du temps standard
        sessions = ensure_sessions_for_date(date(2026, 7, 12))
        self.assertEqual(sessions, [])


@override_settings(
    INJS_FRONTEND_URL='',
    CORS_ALLOWED_ORIGINS=['https://spa.injs.ci'],
    CSRF_TRUSTED_ORIGINS=[],
)
class FrontendBaseUrlTests(TestCase):
    """Le QR doit envoyer le téléphone sur le SPA, et nulle part ailleurs."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_declared_spa_origin_wins(self):
        request = self.factory.get('/', HTTP_ORIGIN='https://spa.injs.ci')
        self.assertEqual(frontend_base_url(request), 'https://spa.injs.ci')

    def test_referer_accepted_when_trusted(self):
        request = self.factory.get('/', HTTP_REFERER='https://spa.injs.ci/professeur/seances')
        self.assertEqual(frontend_base_url(request), 'https://spa.injs.ci')

    def test_forged_origin_falls_back_to_request_host(self):
        request = self.factory.get('/', HTTP_ORIGIN='https://pirate.example')
        self.assertEqual(frontend_base_url(request), 'http://testserver')

    @override_settings(INJS_FRONTEND_URL='https://forced.injs.ci')
    def test_explicit_setting_overrides_headers(self):
        request = self.factory.get('/', HTTP_ORIGIN='https://spa.injs.ci')
        self.assertEqual(frontend_base_url(request), 'https://forced.injs.ci')

    def test_badge_url_targets_student_attendance_page(self):
        request = self.factory.get('/', HTTP_ORIGIN='https://spa.injs.ci')
        payload = build_session_payload('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', date(2026, 7, 10))
        url = build_badge_url(payload, request=request)
        self.assertTrue(url.startswith('https://spa.injs.ci/etudiant/presences?token='))
