"""WSGI config for INJS-LMD project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'injs_lmd.settings.production')
application = get_wsgi_application()
