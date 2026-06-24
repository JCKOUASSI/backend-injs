import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

from config.admin_sidebar import get_admin_sidebar_navigation, get_admin_tabs

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Port HTTP du serveur Django en développement local (runserver / gunicorn dev)
DEV_SERVER_PORT = os.environ.get('DJANGO_DEV_PORT', '8001')

_SECRET_KEY_ENV = os.environ.get('SECRET_KEY', '')
if not _SECRET_KEY_ENV:
    if DEBUG:
        _SECRET_KEY_ENV = 'django-insecure-dev-only-do-not-use-in-production'
    else:
        raise RuntimeError(
            'SECRET_KEY environment variable is not set. '
            'Set it before starting the server in production.'
        )
SECRET_KEY = _SECRET_KEY_ENV

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
    if h.strip()
]
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if DEBUG:
    ALLOWED_HOSTS.extend(['localhost', '127.0.0.1', '*'])
# dé-duplication
ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))
if not ALLOWED_HOSTS:
    # fallback local dev (évite un arrêt complet si aucune env n'est fournie)
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Base URL for QR codes (must be reachable by phones scanning the QR).
# In production, set via env var. In dev, auto-detect LAN IP.
BADGE_BASE_URL = os.environ.get('BADGE_BASE_URL', '')
if not BADGE_BASE_URL and DEBUG:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        BADGE_BASE_URL = f'http://{local_ip}:{DEV_SERVER_PORT}'
    except Exception:
        BADGE_BASE_URL = f'http://localhost:{DEV_SERVER_PORT}'

CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        f'http://localhost:{DEV_SERVER_PORT}',
        f'http://127.0.0.1:{DEV_SERVER_PORT}',
        'http://127.0.0.1:57128',
        f'http://{BADGE_BASE_URL.split("//")[-1]}' if BADGE_BASE_URL else f'http://192.168.100.54:{DEV_SERVER_PORT}',
    ])
    # Ajouter l'IP LAN auto-détectée pour que les téléphones puissent badger
    if BADGE_BASE_URL and BADGE_BASE_URL not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(BADGE_BASE_URL)

# Application definition
INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    # Local apps
    'authentication',
    'formations.apps.FormationsConfig',
    'presences',
    'exports',
    'dashboard',
    'statistiques',
    'suiviEvaluation',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dashboard.context_processors.sidebar_counts',
                'config.context_processors.public_urls',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database — PostgreSQL
_postgres_db = os.environ.get('POSTGRES_DB', 'qr_badge')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _postgres_db,
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        # Les tests Django utilisent une base séparée (test_<nom>), jamais la base de dev.
        'TEST': {
            'NAME': f'test_{_postgres_db}',
        },
    }
}

# Cache — Redis en prod si REDIS_URL (multi-réplicas) ; sinon FileBasedCache (workers Gunicorn)
# (LocMemCache n'est pas partagé entre processus → throttling cassé en production)
if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
elif os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ['REDIS_URL'],
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.environ.get('CACHE_DIR', str(BASE_DIR / 'cache')),
            'TIMEOUT': 300,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Custom user model
AUTH_USER_MODEL = 'authentication.User'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S%z',
    'DEFAULT_THROTTLE_RATES': {
        'login': os.environ.get('THROTTLE_LOGIN_RATE', '20/min'),
        'scan': os.environ.get('THROTTLE_SCAN_RATE', '30/min'),
    },
}

# JWT Settings — durées plus longues en développement pour éviter les déconnexions
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(days=1)   if DEBUG else timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30)  if DEBUG else timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# QR Token settings
QR_TOKEN_LIFETIME_HOURS = 24

# Scan QR public (web badge) — désactivé par défaut en production.
# Utiliser l'app mobile (/api/scan/secure/) ou activer explicitement via env.
PUBLIC_QR_SCAN_ENABLED = os.environ.get(
    'PUBLIC_QR_SCAN_ENABLED',
    'True' if DEBUG else 'False',
).lower() in ('true', '1', 'yes')

# Délai avant marquage ABSENT_NON_BADGE (commande auto_close_pointages)
AUTO_ABSENT_DELAI_MINUTES = int(os.environ.get('AUTO_ABSENT_DELAI_MINUTES', 60))

# Paramètres anti-fraude mobile (heartbeat + geofence)
MOBILE_HEARTBEAT_SUSPECT_TIMEOUT_MINUTES = int(
    os.environ.get('MOBILE_HEARTBEAT_SUSPECT_TIMEOUT_MINUTES', 60)
)
MOBILE_HEARTBEAT_AUTO_EXIT_TIMEOUT_MINUTES = int(
    os.environ.get('MOBILE_HEARTBEAT_AUTO_EXIT_TIMEOUT_MINUTES', 120)
)
MOBILE_GEOFENCE_DEFAULT_RADIUS_M = int(
    os.environ.get('MOBILE_GEOFENCE_DEFAULT_RADIUS_M', 200)
)
MOBILE_GEOFENCE_MAX_ACCURACY_M = int(
    os.environ.get('MOBILE_GEOFENCE_MAX_ACCURACY_M', 80)
)
MOBILE_GEOFENCE_OUTSIDE_CONFIRMATIONS = int(
    os.environ.get('MOBILE_GEOFENCE_OUTSIDE_CONFIRMATIONS', 2)
)

# CORS — liste stricte d'origines (ou vide = rien)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin
]
if DEBUG:
    CORS_ALLOWED_ORIGINS.extend([
        'http://localhost:3000',
        'http://localhost:3001',
        f'http://localhost:{DEV_SERVER_PORT}',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:3001',
        f'http://127.0.0.1:{DEV_SERVER_PORT}',
        f'http://192.168.1.90:3000',
        f'http://192.168.1.90:{DEV_SERVER_PORT}',
        f'http://192.168.100.54:3000',
        f'http://192.168.100.54:{DEV_SERVER_PORT}',
    ])
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(CORS_ALLOWED_ORIGINS))
CORS_EXPOSE_HEADERS = ['Content-Disposition', 'Content-Type']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend' if not DEBUG
    else 'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '15'))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@qrbadge.local')

DATA_UPLOAD_MAX_NUMBER_FIELDS = None

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'SYGEP-CPFAE API',
    'DESCRIPTION': 'API de gestion des formations, participants et badgeage QR.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# URL publique de l'application web (bouton « Voir le site » dans l'admin Unfold).
PUBLIC_APP_URL = os.environ.get('PUBLIC_APP_URL', 'https://app.sygepcpfae.org').rstrip('/')

# ── Django Unfold (admin) ─────────────────────────────────────────────────────
UNFOLD = {
    'SITE_TITLE': 'SYGEP-CPFAE Admin',
    'SITE_HEADER': 'SYGEP-CPFAE',
    'SITE_SUBHEADER': 'Gestion des formations et présences',
    'SITE_URL': PUBLIC_APP_URL,
    'SITE_SYMBOL': 'school',
    'THEME': 'light',
    'BORDER_RADIUS': '20px',
    'COLORS': {
        'primary': {
            '50': 'oklch(97% 0.02 250)',
            '100': 'oklch(94% 0.04 248)',
            '200': 'oklch(88% 0.08 246)',
            '300': 'oklch(78% 0.12 244)',
            '400': 'oklch(65% 0.15 242)',
            '500': 'oklch(52% 0.15 250)',   # #1565C0
            '600': 'oklch(48% 0.14 248)',   # #1976D2
            '700': 'oklch(42% 0.12 246)',
            '800': 'oklch(35% 0.10 244)',
            '900': 'oklch(28% 0.08 242)',
            '950': 'oklch(20% 0.06 240)',
        },
        'base': {
            '50': 'oklch(98.5% 0.002 260)',
            '100': 'oklch(97% 0.003 260)',
            '200': 'oklch(93% 0.005 260)',
            '300': 'oklch(88% 0.008 260)',
            '400': 'oklch(72% 0.015 260)',
            '500': 'oklch(58% 0.02 260)',
            '600': 'oklch(48% 0.025 260)',
            '700': 'oklch(40% 0.028 260)',
            '800': 'oklch(30% 0.03 260)',
            '900': 'oklch(22% 0.032 260)',
            '950': 'oklch(16% 0.028 260)',
        },
    },
    'STYLES': [
        lambda request: static('admin/custom_admin.css'),
    ],
    'DASHBOARD_CALLBACK': 'config.admin_dashboard.admin_dashboard_callback',
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': get_admin_sidebar_navigation(PUBLIC_APP_URL),
    },
    'TABS': get_admin_tabs(),
}

# ── Production security (activé quand DEBUG=False) ──
# NOTE: SECURE_SSL_REDIRECT est intentionnellement désactivé — la redirection
# HTTP→HTTPS doit être gérée par Nginx/le reverse proxy, pas par Django.
# Si Django gère lui-même le SSL redirect, il entre en conflit avec le proxy
# et casse le CSRF sur les endpoints publics comme /api/scan/.
if not DEBUG:
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
