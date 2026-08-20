from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.faculty.models import BadgeDevice
from apps.faculty.services.badge_security import assert_device_bound, distance_meters
from apps.faculty.services.session_qr import SessionQrError

User = get_user_model()


class BadgeSecurityUnitTests(TestCase):
    def test_distance_same_point(self):
        self.assertLess(distance_meters(5.36, -4.008, 5.36, -4.008), 1)

    def test_distance_far_point(self):
        self.assertGreater(distance_meters(5.36, -4.008, 5.40, -4.00), 200)

    def test_device_bind_then_mismatch(self):
        user = User.objects.create_user(
            email='badge.device@test.ci', password='Test@INJS2026!',
            first_name='Badge', last_name='Device',
        )
        first = assert_device_bound(user, 'device-A', 'Phone A')
        self.assertEqual(first.device_id, 'device-A')
        self.assertEqual(BadgeDevice.objects.filter(user=user, is_active=True).count(), 1)

        again = assert_device_bound(user, 'device-A', 'Phone A')
        self.assertEqual(again.id, first.id)

        with self.assertRaises(SessionQrError) as ctx:
            assert_device_bound(user, 'device-B', 'Phone B')
        self.assertEqual(ctx.exception.code, 'device_mismatch')
