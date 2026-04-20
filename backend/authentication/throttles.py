from rest_framework.throttling import SimpleRateThrottle


def _client_ip(request) -> str:
    # REMOTE_ADDR est suffisant ici; si besoin, tu peux ajouter X-Forwarded-For.
    return (request.META.get('REMOTE_ADDR') or '').strip()


class LoginRateThrottle(SimpleRateThrottle):
    """Throttling anti bruteforce sur l'endpoint login."""

    scope = 'login'

    def get_cache_key(self, request, view):
        ip = _client_ip(request)
        if not ip:
            return None
        return f'login:{ip}'


class ScanRateThrottle(SimpleRateThrottle):
    """Throttling anti spam sur l'endpoint public de scan QR."""

    scope = 'scan'

    def get_cache_key(self, request, view):
        ip = _client_ip(request)
        if not ip:
            return None

        token = ''
        try:
            token = (request.data or {}).get('token_qr', '')
        except Exception:
            token = ''

        # On limite l'impact par IP + token (utile contre de multiples scans concurrents).
        token_key = str(token).split('-')[0] if token else 'no-token'
        return f'scan:{ip}:{token_key}'

