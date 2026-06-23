import hashlib

from django.core.cache import cache


def request_cache_key(prefix, request, extra=()):
    """Clé de cache stable par utilisateur + query string."""
    user = request.user
    qp = '&'.join(
        f'{k}={request.query_params.get(k, "")}'
        for k in sorted(request.query_params.keys())
    )
    parts = (
        prefix,
        str(getattr(user, 'pk', 'anon')),
        getattr(user, 'role', ''),
        str(getattr(user, 'secretariat_id', '') or ''),
        *[str(x) for x in extra],
        qp,
    )
    return hashlib.md5('|'.join(parts).encode()).hexdigest()


def get_cached_response(key):
    return cache.get(key)


def set_cached_response(key, data, timeout):
    cache.set(key, data, timeout)


def invalidate_referentiels_cache():
    """Invalidation best-effort (LocMem/FileBased : clé fixe par déploiement)."""
    pass
