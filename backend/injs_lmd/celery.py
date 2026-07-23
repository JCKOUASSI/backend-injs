import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'injs_lmd.settings.development')

app = Celery('injs_lmd')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
