from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.faculty.services.session_qr import (
    build_session_payload,
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
