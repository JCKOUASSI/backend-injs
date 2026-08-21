"""Base settings for INJS-LMD platform."""
from datetime import timedelta
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-insecure-change-in-production-injs-2026')

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'daphne',
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
    'django_filters',
    'drf_spectacular',
    'oauth2_provider',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'channels',
    'django_celery_beat',
    'django_celery_results',
    'django_prometheus',
    'storages',
    # INJS apps
    'apps.core',
    'apps.accounts',
    'apps.academics',
    'apps.students',
    'apps.faculty',
    'apps.exams',
    'apps.admissions',
    'apps.finance',
    'apps.notifications',
    'apps.reports',
    'apps.documents',
    'apps.messaging',
    'apps.library',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
    'apps.accounts.middleware.AuditMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'injs_lmd.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'injs_lmd.wsgi.application'
ASGI_APPLICATION = 'injs_lmd.asgi.application'

AUTH_USER_MODEL = 'accounts.User'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'injs_lmd'),
        'USER': os.environ.get('POSTGRES_USER', 'injs'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'injs_dev_password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {'connect_timeout': 10},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redis
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

# Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'amqp://injs:injs@localhost:5672//')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [REDIS_URL]},
    },
}

# MinIO / S3
USE_S3 = os.environ.get('USE_S3', 'false').lower() == 'true'
if USE_S3:
    AWS_ACCESS_KEY_ID = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
    AWS_SECRET_ACCESS_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('MINIO_BUCKET', 'injs-documents')
    AWS_S3_ENDPOINT_URL = os.environ.get('MINIO_ENDPOINT', 'http://localhost:9000')
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Elasticsearch
ELASTICSEARCH_DSL = {
    'default': {'hosts': os.environ.get('ELASTICSEARCH_URL', 'http://localhost:9200')},
}

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'apps.accounts.permissions.HasModulePermission',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '5000/hour',
        'login': '10/minute',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'INJS-LMD API',
    'DESCRIPTION': 'API de gestion académique LMD - Institut National de la Jeunesse et des Sports',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v1',
}

OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': 'Read scope',
        'write': 'Write scope',
        'openid': 'OpenID Connect',
    },
    'OIDC_ENABLED': True,
}

CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080'
).split(',')

# Origine du SPA encodée dans les QR de séance : le téléphone qui scanne doit
# atterrir sur le frontend, servi le cas échéant par un autre hôte que l'API.
# Vide = déduite de l'origine annoncée par le navigateur si elle figure parmi
# les origines de confiance, sinon de l'origine de la requête.
INJS_FRONTEND_URL = os.environ.get('INJS_FRONTEND_URL', '').strip().rstrip('/')

# INJS branding
INJS_PRIMARY_COLOR = '#0D47A1'
INJS_SECONDARY_COLOR = '#42A5F5'
INJS_INSTITUTION_NAME = 'Institut National de la Jeunesse et des Sports'

# Payment providers (sandbox keys via env)
PAYMENT_PROVIDERS = {
    'orange_money': {
        'enabled': os.environ.get('ORANGE_MONEY_ENABLED', 'true').lower() == 'true',
        'merchant_id': os.environ.get('ORANGE_MONEY_MERCHANT_ID', ''),
        'api_key': os.environ.get('ORANGE_MONEY_API_KEY', ''),
        'callback_url': os.environ.get('PAYMENT_CALLBACK_URL', 'http://localhost:8001/api/v1/finance/webhooks/orange/'),
    },
    'mtn_momo': {
        'enabled': os.environ.get('MTN_MOMO_ENABLED', 'true').lower() == 'true',
        'subscription_key': os.environ.get('MTN_MOMO_SUBSCRIPTION_KEY', ''),
        'api_user': os.environ.get('MTN_MOMO_API_USER', ''),
        'callback_url': os.environ.get('PAYMENT_CALLBACK_URL', 'http://localhost:8001/api/v1/finance/webhooks/mtn/'),
    },
    'moov_money': {
        'enabled': os.environ.get('MOOV_MONEY_ENABLED', 'true').lower() == 'true',
        'merchant_code': os.environ.get('MOOV_MONEY_MERCHANT_CODE', ''),
        'api_key': os.environ.get('MOOV_MONEY_API_KEY', ''),
    },
    'wave': {
        'enabled': os.environ.get('WAVE_ENABLED', 'true').lower() == 'true',
        'api_key': os.environ.get('WAVE_API_KEY', ''),
        'business_id': os.environ.get('WAVE_BUSINESS_ID', ''),
    },
    'visa_card': {
        'enabled': os.environ.get('STRIPE_ENABLED', 'true').lower() == 'true',
        'stripe_secret_key': os.environ.get('STRIPE_SECRET_KEY', ''),
        'stripe_publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY', ''),
    },
}

# LMD rules (Arrêté INJS / conditions de validation)
LMD_PASSING_AVERAGE = float(os.environ.get('LMD_PASSING_AVERAGE', '10.0'))
LMD_COMPENSATION_FLOOR = float(os.environ.get('LMD_COMPENSATION_FLOOR', '8.0'))
LMD_CC_WEIGHT = float(os.environ.get('LMD_CC_WEIGHT', '0.4'))
LMD_CT_WEIGHT = float(os.environ.get('LMD_CT_WEIGHT', '0.6'))
LMD_MIN_CREDITS_RATIO = float(os.environ.get('LMD_MIN_CREDITS_RATIO', '0.8'))
LMD_MAX_ABSENCE_RATE = float(os.environ.get('LMD_MAX_ABSENCE_RATE', '0.25'))
LMD_MENTION_THRESHOLDS = {
    'tres_bien': float(os.environ.get('LMD_MENTION_TRES_BIEN', '16.0')),
    'bien': float(os.environ.get('LMD_MENTION_BIEN', '14.0')),
    'assez_bien': float(os.environ.get('LMD_MENTION_ASSEZ_BIEN', '12.0')),
    'passable': float(os.environ.get('LMD_MENTION_PASSABLE', '10.0')),
}

# Badgeage QR — géofence campus (salles avec coordonnées)
INJS_GEOFENCE_RADIUS_M = int(os.environ.get('INJS_GEOFENCE_RADIUS_M', '250'))
INJS_GEOFENCE_MAX_ACCURACY_M = int(os.environ.get('INJS_GEOFENCE_MAX_ACCURACY_M', '80'))

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}
