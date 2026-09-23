#!/usr/bin/env bash
# =============================================================================
# LANCEUR API DJANGO — port FIGÉ 8000 — base PostgreSQL OFFICIELLE de dev
# -----------------------------------------------------------------------------
# Base : injs_lmd_current @ 127.0.0.1:5432 (user injs_user) — cf. .clinerules §6
# Usage : bash arena/lancer-api-pg.sh
# Ne jamais changer le port 8000 jusqu'à la fin du projet (règle §18).
# =============================================================================
set -uo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$RACINE/backend"
PORT=8000

if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  echo ">> [bloquant] environnement absent ($BACKEND/.venv)"
  exit 2
fi

if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iTCP:$PORT -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
    echo ">> [attention] un processus écoute déjà sur le port $PORT."
    echo "   Libérez-le (pkill -f 'manage.py runserver') plutôt que de changer de port."
    exit 3
  fi
fi

cd "$BACKEND" || exit 2
# Base officielle INJS-LMD (jamais la base Docker 5436, jamais qr_badge/postgres)
export DEBUG=True
export POSTGRES_DB="${POSTGRES_DB:-injs_lmd_current}"
export POSTGRES_USER="${POSTGRES_USER:-injs_user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
export POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
exec .venv/bin/python manage.py runserver 0.0.0.0:$PORT
