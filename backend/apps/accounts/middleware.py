import json
from django.utils.deprecation import MiddlewareMixin
from apps.accounts.models import AuditLog


class AuditMiddleware(MiddlewareMixin):
    """Log mutating API requests."""

    AUDIT_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    def process_response(self, request, response):
        if request.method not in self.AUDIT_METHODS:
            return response
        if not request.path.startswith('/api/'):
            return response
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return response
        try:
            module = request.path.split('/')[3] if len(request.path.split('/')) > 3 else 'unknown'
            AuditLog.objects.create(
                user=user,
                action=request.method,
                module=module,
                object_type=request.path,
                object_repr=request.path[:255],
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                changes={'status_code': response.status_code},
            )
        except Exception:
            pass
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class JWTAuthMiddlewareStack:
    """Channels JWT auth middleware placeholder."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        return await self.inner(scope, receive, send)
