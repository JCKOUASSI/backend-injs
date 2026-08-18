#!/bin/sh
set -e

# Conteneurs annexes (cron / celery) : pas de migrate
if [ "${SKIP_DB_SETUP:-}" = "true" ]; then
  if [ "$#" -gt 0 ]; then
    echo "[injs] SKIP_DB_SETUP exec: $*"
    exec "$@"
  fi
  echo "[injs] SKIP_DB_SETUP sans commande" >&2
  exit 1
fi

echo "[injs-be] waiting for database..."
python <<'PY'
import os, sys, time
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'injs_lmd.settings')
django.setup()

from django.db import connection

for attempt in range(60):
    try:
        connection.ensure_connection()
        print('[injs-be] database ready')
        sys.exit(0)
    except Exception as exc:
        print(f'[injs-be] db not ready ({attempt + 1}/60): {exc}')
        time.sleep(2)
print('[injs-be] database unavailable', file=sys.stderr)
sys.exit(1)
PY

echo "[injs-be] migrate..."
python manage.py migrate --noinput

echo "[injs-be] collectstatic..."
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo "[injs-be] ensure superuser..."
  python <<'PY'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'injs_lmd.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ['DJANGO_SUPERUSER_EMAIL'].strip().lower()
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin')
last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'INJS')

user = User.objects.filter(email=email).first()
if user is None:
    User.objects.create_superuser(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    print(f'[injs-be] superuser created: {email}')
else:
    print(f'[injs-be] superuser already exists: {email}')
PY
fi

if [ "$#" -gt 0 ]; then
  echo "[injs-be] exec: $*"
  exec "$@"
fi

WORKERS="${GUNICORN_WORKERS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "[injs-be] starting gunicorn (workers=${WORKERS}, timeout=${TIMEOUT})"
exec gunicorn injs_lmd.wsgi:application \
  --bind "0.0.0.0:${PORT:-8001}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
