"""Disposable, local-only Django settings for a SQLite-backed preview.

Use with ``python manage.py <command> --settings=arena.settings_sandbox`` from
the backend directory. Never deploy this profile: it deliberately allows preview
hosts and enables the demo-only admin middleware.
"""
import os
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("SECRET_KEY", "arena-sandbox-only-not-for-production")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("USE_SQLITE", "1")
os.environ.setdefault(
    "SQLITE_PATH", str(_REPOSITORY_ROOT / "backend" / "db_sandbox.sqlite3")
)

from config.settings import *  # noqa: E402,F403

# Keep the preview profile intentionally separate from production settings.
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".e2b.app"]
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([
    *CSRF_TRUSTED_ORIGINS,
    "https://*.e2b.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]))
CORS_ALLOWED_ORIGINS = list(dict.fromkeys([
    *CORS_ALLOWED_ORIGINS,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]))

SESSION_COOKIE_NAME = "injs_sessionid"
CSRF_COOKIE_NAME = "injs_csrftoken"
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False
X_FRAME_OPTIONS = "DENY"
DEV_FRAME_ANCESTORS = "'self' https://*.e2b.app http://localhost:3000"

# bootstrap.sh provisions this disposable account with a random password;
# AutoLoginApercuMiddleware still checks DEBUG, the admin path, and its flags.
PREVIEW_AUTOLOGIN_USERNAME = "admin"
PREVIEW_AUTOLOGIN_ENABLED = True

MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(0, "arena.partitioned_cookies.PartitionedCookieMiddleware")
# AuthenticationMiddleware must have populated request.user before the
# preview-only auto-login checks it.
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
    "arena.preview_autologin.AutoLoginApercuMiddleware",
)
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.clickjacking.XFrameOptionsMiddleware"),
    "config.dev_middleware.DevPreviewFrameMiddleware",
)
