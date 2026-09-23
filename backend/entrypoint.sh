#!/bin/sh
set -e

# Entrypoint backend INJS-LMD
# 1. Préparation répertoires  2. Attente PostgreSQL  3. Migrations
# 4. Collectstatic            5. Superutilisateur     6. Gunicorn

mkdir -p /app/media/students/qr /app/staticfiles

if [ "${SKIP_DB_SETUP:-}" = "true" ]; then
  if [ "$#" -gt 0 ]; then
    echo "[injs-be] SKIP_DB_SETUP exec: $*"
    exec "$@"
  fi
  echo "[injs-be] SKIP_DB_SETUP sans commande" >&2
  exit 1
fi

# Attente de PostgreSQL si USE_POSTGRES est vrai ou non défini
if [ "${USE_SQLITE:-0}" != "1" ] && [ "${USE_POSTGRES:-true}" = "true" ]; then
  echo "[injs-be] waiting for database..."
  python3 - <<'PY'
import os, sys, time
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
for attempt in range(60):
    try:
        connection.ensure_connection()
        print('[injs-be] database ready')
        sys.exit(0)
    except Exception as exc:
        print(f'[injs-be] db not ready ({attempt+1}/60): {exc}')
        time.sleep(2)
print('[injs-be] database unavailable', file=sys.stderr)
sys.exit(1)
PY
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[injs-be] migrate..."
  python manage.py migrate --noinput
fi

if [ "${COLLECTSTATIC:-true}" = "true" ]; then
  echo "[injs-be] collectstatic..."
  python manage.py collectstatic --noinput
fi

# Création superutilisateur idempotent si variables présentes
if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo "[injs-be] ensure superuser..."
  python3 - <<'PY'
import os, django
from django.contrib.auth import get_user_model
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
User = get_user_model()
email = os.environ['DJANGO_SUPERUSER_EMAIL'].strip().lower()
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', email.split('@')[0])
first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin')
last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'INJS')
role = getattr(User.Role, 'ADMIN', 'ADMIN') if hasattr(User, 'Role') else None
user = User.objects.filter(username=username).first()
if not user and email:
    user = User.objects.filter(email=email).first()

if not user:
    user = User.objects.create_superuser(
        username=username, email=email, password=password,
        first_name=first_name, last_name=last_name,
        is_staff=True, is_superuser=True,
    )
    if role and hasattr(user, 'role'):
        user.role = role
        user.save()
    print(f'[injs-be] superuser created: {username} ({email})')
else:
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    if role and hasattr(user, 'role'):
        user.role = role
    user.save()
    print(f'[injs-be] superuser updated/verified: {username} ({email})')
PY
fi

if [ "$#" -gt 0 ]; then
  echo "[injs-be] exec: $*"
  exec "$@"
fi

WORKERS="${GUNICORN_WORKERS:-auto}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"
PORT="${PORT:-8000}"

if [ "$WORKERS" = "auto" ]; then
  NP="$(nproc 2>/dev/null || echo 1)"
  W="$(( NP * 2 + 1 ))"
  [ "$W" -gt 8 ] && W=8
  [ "$W" -lt 2 ] && W=2
  echo "[injs-be] gunicorn workers=auto (CPUs=$NP -> $W workers)"
else
  W="$WORKERS"
  echo "[injs-be] gunicorn workers=$W"
fi

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "$W" \
  --timeout "$TIMEOUT" \
  --access-logfile - \
  --error-logfile -
