"""Mécanismes de badgeage sécurisé INJS (appareil, géofence, heartbeat, audit).

Inspiré des garde-fous SYGEP-CPFAE, appliqué aux séances LMD / salles campus.
"""
from __future__ import annotations

from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.utils import timezone

from apps.faculty.models import BadgeDevice, Room

HEARTBEAT_AUDIT_INTERVAL = timedelta(minutes=5)


def _qr_error(message, code):
    from apps.faculty.services.session_qr import SessionQrError
    raise SessionQrError(message, code)


def distance_meters(lat1, lon1, lat2, lon2) -> float:
    radius = 6371000
    phi1, phi2 = radians(float(lat1)), radians(float(lat2))
    d_phi = radians(float(lat2) - float(lat1))
    d_lambda = radians(float(lon2) - float(lon1))
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * radius * asin(sqrt(min(a, 1)))


def default_radius_m() -> int:
    return int(getattr(settings, 'INJS_GEOFENCE_RADIUS_M', 250))


def geofence_for_schedule(schedule) -> tuple[float, float, int] | None:
    room = getattr(schedule, 'room', None)
    if room and room.latitude is not None and room.longitude is not None:
        return float(room.latitude), float(room.longitude), default_radius_m()

    campus = Room.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False,
    )
    if room and room.institution_id:
        campus = campus.filter(institution_id=room.institution_id)
    coords = list(campus.values_list('latitude', 'longitude')[:40])
    if not coords:
        return None
    lat = sum(float(item[0]) for item in coords) / len(coords)
    lon = sum(float(item[1]) for item in coords) / len(coords)
    return lat, lon, default_radius_m()


def assert_device_bound(user, device_id: str, device_label: str = '') -> BadgeDevice:
    token = (device_id or '').strip()
    if not token:
        _qr_error('Identifiant appareil requis pour badger', 'device_required')

    active = BadgeDevice.objects.filter(user=user, is_active=True).order_by('-created_at').first()
    if active is None:
        return BadgeDevice.objects.create(
            user=user,
            device_id=token[:80],
            device_label=(device_label or '')[:120],
            last_seen_at=timezone.now(),
        )
    if active.device_id != token:
        _qr_error(
            'Cet appareil n’est pas autorisé pour votre badge. Contactez l’administration.',
            'device_mismatch',
        )
    active.last_seen_at = timezone.now()
    if device_label and active.device_label != device_label[:120]:
        active.device_label = device_label[:120]
        active.save(update_fields=['last_seen_at', 'device_label', 'updated_at'])
    else:
        active.save(update_fields=['last_seen_at', 'updated_at'])
    return active


def assert_geofence(schedule, latitude, longitude, accuracy_m=None) -> dict:
    fence = geofence_for_schedule(schedule)
    if fence is None:
        return {'required': False, 'ok': True, 'distance_m': None, 'radius_m': None}

    if latitude is None or longitude is None:
        _qr_error(
            'La position GPS est requise pour badger sur ce campus',
            'gps_required',
        )

    site_lat, site_lon, radius_m = fence
    max_accuracy = getattr(settings, 'INJS_GEOFENCE_MAX_ACCURACY_M', 80)
    if accuracy_m is not None and float(accuracy_m) > max_accuracy:
        _qr_error(
            'Précision GPS insuffisante. Rapprochez-vous de la salle et réessayez.',
            'gps_inaccurate',
        )

    distance = distance_meters(latitude, longitude, site_lat, site_lon)
    if distance > radius_m:
        _qr_error(
            f'Vous êtes hors du périmètre de la salle ({int(distance)} m / {radius_m} m).',
            'outside_geofence',
        )
    return {
        'required': True,
        'ok': True,
        'distance_m': round(distance, 1),
        'radius_m': radius_m,
    }


def apply_badge_security(*, user, schedule, context: dict | None):
    context = context or {}
    assert_device_bound(user, context.get('device_id') or '', context.get('device_label') or '')
    return assert_geofence(
        schedule,
        context.get('latitude'),
        context.get('longitude'),
        context.get('accuracy_m'),
    )


def stamp_badge_fields(instance, context: dict | None) -> list[str]:
    context = context or {}
    fields = []
    device_id = (context.get('device_id') or '').strip()
    if device_id:
        instance.device_id = device_id[:80]
        fields.append('device_id')
    if context.get('latitude') is not None:
        instance.latitude = context['latitude']
        fields.append('latitude')
    if context.get('longitude') is not None:
        instance.longitude = context['longitude']
        fields.append('longitude')
    if context.get('accuracy_m') is not None:
        instance.accuracy_m = context['accuracy_m']
        fields.append('accuracy_m')
    instance.last_heartbeat_at = timezone.now()
    fields.append('last_heartbeat_at')
    return fields


def log_badge_event(*, user, action, object_id='', object_repr='', changes=None):
    try:
        from apps.accounts.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action=action,
            module='faculty',
            object_type='Attendance',
            object_id=str(object_id or ''),
            object_repr=(object_repr or '')[:255],
            changes=changes or {},
        )
    except Exception:
        pass


def record_badge_event(
    *,
    kind,
    source='qr',
    actor=None,
    attendance=None,
    staff_attendance=None,
    seance=None,
    schedule=None,
    session_date=None,
    student=None,
    teacher=None,
    previous_status='',
    new_status='',
    reason='',
    context=None,
    extra=None,
):
    """Écrit un BadgeEvent immuable et un AuditLog générique."""
    from apps.faculty.models import BadgeEvent

    context = context or {}
    if attendance is not None:
        student = student or attendance.student
        schedule = schedule or attendance.schedule
        session_date = session_date or attendance.date
        seance = seance or getattr(attendance, 'seance', None)
        new_status = new_status or attendance.status
    if staff_attendance is not None:
        teacher = teacher or staff_attendance.teacher
        schedule = schedule or staff_attendance.schedule
        session_date = session_date or staff_attendance.date
        seance = seance or getattr(staff_attendance, 'seance', None)
        new_status = new_status or staff_attendance.status
    if session_date is None:
        session_date = timezone.localdate()

    event = BadgeEvent.objects.create(
        kind=kind,
        source=source,
        actor=actor,
        student=student,
        teacher=teacher,
        attendance=attendance,
        staff_attendance=staff_attendance,
        seance=seance,
        schedule=schedule,
        session_date=session_date,
        previous_status=previous_status or '',
        new_status=new_status or '',
        reason=(reason or '')[:255],
        device_id=(context.get('device_id') or '')[:80],
        latitude=context.get('latitude'),
        longitude=context.get('longitude'),
        accuracy_m=context.get('accuracy_m'),
        extra=extra or {},
    )
    log_badge_event(
        user=actor,
        action=f'badge_{kind}',
        object_id=event.id,
        object_repr=str(seance or schedule or event.id),
        changes={
            'kind': kind,
            'source': source,
            'previous_status': previous_status,
            'new_status': new_status,
            'reason': reason or '',
        },
    )
    return event


def should_audit_heartbeat(previous_heartbeat_at) -> bool:
    if previous_heartbeat_at is None:
        return True
    return timezone.now() - previous_heartbeat_at >= HEARTBEAT_AUDIT_INTERVAL
