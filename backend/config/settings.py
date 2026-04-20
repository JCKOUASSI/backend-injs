import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

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
        BADGE_BASE_URL = f'http://{local_ip}:8000'
    except Exception:
        BADGE_BASE_URL = 'http://localhost:8000'

CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://127.0.0.1:57128',
        f'http://{BADGE_BASE_URL.split("//")[-1]}' if BADGE_BASE_URL else 'http://192.168.100.54:8000',
    ])
    # Ajouter l'IP LAN auto-détectée pour que les téléphones puissent badger
    if BADGE_BASE_URL and BADGE_BASE_URL not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(BADGE_BASE_URL)

# Application definition
INSTALLED_APPS = [
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
    'formations',
    'presences',
    'exports',
    'dashboard',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database — PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'qr_badge'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Cache — FileBasedCache en production pour partager le cache entre workers Gunicorn
# (LocMemCache n'est pas partagé entre processus → throttling cassé en production)
if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
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

# Délai avant marquage ABSENT_NON_BADGE (commande auto_close_pointages)
AUTO_ABSENT_DELAI_MINUTES = int(os.environ.get('AUTO_ABSENT_DELAI_MINUTES', 60))

# CORS — liste stricte d'origines (ou vide = rien)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin
]
if DEBUG:
    CORS_ALLOWED_ORIGINS.extend([
        'http://localhost:3000',
        'http://localhost:8000',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:8000',
        'http://192.168.1.90:3000',
        'http://192.168.1.90:8000',
        'http://192.168.1.90:8001',
        'http://192.168.100.54:3000',
        'http://192.168.100.54:8000',
        'http://192.168.100.54:8001',
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
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@qrbadge.local')

DATA_UPLOAD_MAX_NUMBER_FIELDS = None

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'QR Badge API',
    'DESCRIPTION': 'API de gestion des formations, participants et badgeage QR.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
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
