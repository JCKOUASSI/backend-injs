#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
PYTHON="${PYTHON:-$BACKEND/.venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
  echo "Python environment missing; run bash arena/bootstrap.sh first." >&2
  exit 1
fi

PORT=8000
cd "$BACKEND"
exec env DJANGO_SETTINGS_MODULE=arena.settings_sandbox \
  SECRET_KEY=arena-sandbox-only-not-for-production DEBUG=True USE_SQLITE=1 \
  "$PYTHON" manage.py runserver 0.0.0.0:$PORT
