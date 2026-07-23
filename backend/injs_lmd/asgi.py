"""ASGI config for INJS-LMD project (WebSocket notifications)."""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'injs_lmd.settings.development')

django_asgi_app = get_asgi_application()

try:
    from apps.notifications.routing import websocket_urlpatterns
    from apps.accounts.middleware import JWTAuthMiddlewareStack
    application = ProtocolTypeRouter({
        'http': django_asgi_app,
        'websocket': JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    })
except ImportError:
    application = django_asgi_app
