from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [  # noqa: F405
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

# SQLite par défaut en local ; PostgreSQL uniquement si USE_POSTGRES=true (ex. Docker)
if os.environ.get('USE_POSTGRES', 'false').lower() != 'true':  # noqa: F405
    DATABASES = {  # noqa: F405
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
        }
    }
    CACHES = {  # noqa: F405
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    CHANNEL_LAYERS = {  # noqa: F405
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
    }

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
