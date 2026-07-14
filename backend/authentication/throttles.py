import logging

from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)


def _client_ip(request) -> str:
    # REMOTE_ADDR est suffisant ici; si besoin, tu peux ajouter X-Forwarded-For.
    return (request.META.get('REMOTE_ADDR') or '').strip()


class LoginRateThrottle(SimpleRateThrottle):
    """Throttling anti bruteforce sur l'endpoint login."""

    scope = 'login'

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)
        if not allowed:
            logger.warning(
                'login_throttled ip=%s',
                _client_ip(request),
            )
        return allowed

    def get_cache_key(self, request, view):
        ip = _client_ip(request)
        if not ip:
            return None
        return f'login:{ip}'


class ScanRateThrottle(SimpleRateThrottle):
    """Throttling anti spam sur les endpoints de scan QR.

    - Compte authentifié (app mobile) : quota par utilisateur (+ appareil si fourni),
      pour éviter qu'une salle entière partage le même plafond derrière un NAT WiFi.
    - Scan public (web) : quota par IP + token QR.
    """

    scope = 'scan'

    def _request_value(self, request, key):
        try:
            val = (request.data or {}).get(key, '')
            if val:
                return str(val).strip()
        except Exception:
            pass
        if hasattr(request, 'POST'):
            val = request.POST.get(key, '')
            if val:
                return str(val).strip()
        return ''

    def _scan_device_id(self, request):
        return self._request_value(request, 'device_id')

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            device_id = self._scan_device_id(request)
            device_key = device_id[:64] if device_id else 'no-device'
            return f'scan:user:{user.pk}:{device_key}'

        ip = _client_ip(request)
        if not ip:
            return None

        token = self._request_value(request, 'token_qr')
        if not token:
            query_params = getattr(request, 'query_params', None) or getattr(request, 'GET', None) or {}
            token = query_params.get('token_qr', '') or ''

        token_key = str(token).split('-')[0] if token else 'no-token'
        return f'scan:ip:{ip}:{token_key}'


class OfflineDataRateThrottle(SimpleRateThrottle):
    """Throttling anti polling agressif sur l'endpoint offline-data."""

    scope = 'offline_data'

    def get_cache_key(self, request, view):
        token = (
            (request.query_params or {}).get('token', '')
            or getattr(view, 'kwargs', {}).get('token', '')
            or ''
        )
        token = str(token).strip().lower()
        if not token:
            ip = _client_ip(request)
            return f'offline_data:{ip}:no-token'
        return f'offline_data:{token}'

