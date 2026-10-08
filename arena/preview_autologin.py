"""Auto-authentication for the disposable admin account in local previews.

This middleware is intentionally isolated under ``arena`` and is loaded only
by ``arena.settings_sandbox``. It must never be added to production settings.
"""
from django.conf import settings
from django.contrib.auth import get_user_model


class AutoLoginApercuMiddleware:
    """Authenticate the configured active staff account on sandbox admin URLs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        enabled = (
            getattr(settings, "DEBUG", False)
            and getattr(settings, "PREVIEW_AUTOLOGIN_ENABLED", False)
            and request.path.startswith("/admin/")
        )
        if enabled:
            username = getattr(settings, "PREVIEW_AUTOLOGIN_USERNAME", "")
            if username and not getattr(request.user, "is_authenticated", False):
                User = get_user_model()
                user = User._default_manager.filter(
                    username=username,
                    is_active=True,
                    is_staff=True,
                    is_superuser=True,
                ).first()
                if user is not None:
                    # This identity is rebuilt from the disposable fixture on
                    # every request, so no third-party session cookie is needed.
                    # The bypass is limited to the sandbox admin endpoint.
                    request.user = user
                    request.csrf_processing_done = True
        return self.get_response(request)
