#!/usr/bin/env bash
# =============================================================================
# LANCEUR INJS-LMD — API Django (8000) + Site web (3000)
# -----------------------------------------------------------------------------
# Usage : bash arena/lancer-tout.sh
# Lance les deux serveurs en parallèle depuis un seul point d'entrée.
#
# Prérequis : bash arena/bootstrap.sh (une fois après réinitialisation)
#
# Ports figés (règle projet, ne jamais modifier) :
#   - API Django  : 8000
#   - Frontend    : 3000
# =============================================================================
set -uo pipefail

# --- Détection automatique de la racine ---
# On utilise la même logique que lancer-api.sh / lancer-front.sh :
# on cherche manage.py et package.json dans l'arborescence.
_RACINE_CANDIDATES=(
  "/Users/jckouassi/Sites/backend-injs/backend-injs"
  "$(pwd)"
  "$(dirname "$0")/.."
  "$(dirname "$0")/../.."
)

_RACINE=""
for _c in "${_RACINE_CANDIDATES[@]}"; do
  if [ -f "$_c/backend/manage.py" ] && [ -f "$_c/frontend/package.json" ]; then
    _RACINE="$_c"
    break
  fi
done

# Fallback : rechercher manage.py + package.json (comme les scripts existants)
if [ -z "$_RACINE" ]; then
  _MANAGE_PY="$(find . -maxdepth 5 -name manage.py -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null | head -1)"
  _PKG_JSON="$(find . -maxdepth 5 -name package.json -not -path '*/node_modules/*' 2>/dev/null | head -1)"
  if [ -n "$_MANAGE_PY" ] && [ -n "$_PKG_JSON" ]; then
    _BACKEND_DIR="$(dirname "$_MANAGE_PY")"
    _FRONTEND_DIR="$(dirname "$_PKG_JSON")"
    if [ "$_BACKEND_DIR" != "$_FRONTEND_DIR" ]; then
      _RACINE="$(cd "$_BACKEND_DIR/.." && pwd)"
    else
      _RACINE="$(pwd)"
    fi
  else
    echo ">> [bloquant] impossible de détecter la racine du projet"
    echo "   Lancez depuis la racine du dépôt ou définissez RACINE"
    exit 2
  fi
fi

BACKEND="$_RACINE/backend"
FRONTEND="$_RACINE/frontend"
PORT_API=8000
PORT_FRONT=3000

echo "======================================================================"
echo " INJS-LMD — Lancement des serveurs"
echo "======================================================================"
echo "  Racine détectée : $_RACINE"
echo "  Backend         : $BACKEND"
echo "  Frontend        : $FRONTEND"
echo "======================================================================"
echo ""

# --- Vérifications préalables ---

# Vérifier l'environnement Python
if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  echo ">> [bloquant] environnement Python absent"
  echo "   → bash arena/bootstrap.sh"
  exit 2
fi

# Vérifier les dépendances frontend
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo ">> [bloquant] dépendances frontend absentes"
  echo "   → bash arena/bootstrap.sh"
  exit 2
fi

# .env.local frontend (idempotent)
cat > "$FRONTEND/.env.local" <<'ENV'
VITE_API_URL=/api
VITE_ADMIN_URL=/admin/
VITE_REFRESH_FALLBACK=1
ENV

# --- Vérifier les ports ---

check_port() {
  local port=$1
  local label=$2
  local busy=0
  if command -v ss >/dev/null 2>&1; then
    ss -tln 2>/dev/null | grep -q ":$port " && busy=1
  elif command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN && busy=1
  fi
  if [ "$busy" -eq 1 ]; then
    echo ">> [attention] un processus écoute déjà sur le port $port ($label)"
    echo "   Libérez-le avant de continuer."
    return 1
  fi
  return 0
}

if ! check_port $PORT_API "API Django"; then
  exit 3
fi
if ! check_port $PORT_FRONT "Frontend Vite"; then
  exit 3
fi

# --- Lancer les serveurs ---

echo ">> [api]   Démarrage API Django sur le port $PORT_API ..."
cd "$BACKEND" || exit 2
export PYTHONPATH="$_RACINE:$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
.venv/bin/python manage.py runserver 0.0.0.0:$PORT_API --settings=arena.settings_sandbox &
_API_PID=$!

echo ">> [front] Démarrage Frontend Vite sur le port $PORT_FRONT ..."
cd "$FRONTEND" || exit 2
env VITE_HMR_PROTOCOL=wss npm run dev -- --host 0.0.0.0 &
_FRONT_PID=$!

# --- Attendre que les serveurs soient prêts ---

_wait_for_server() {
  local url=$1
  local label=$2
  local max_attempts=30
  local attempt=0
  echo -n ">> [$label]   En attente de disponibilité ..."
  while [ $attempt -lt $max_attempts ]; do
    if curl -s --connect-timeout 1 "$url" >/dev/null 2>&1; then
      echo ""
      return 0
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
  done
  echo ""
  echo ">> [attention] $label non disponible après ${max_attempts}s"
  return 1
}

echo ""
echo "======================================================================"
echo "  Serveurs démarrés"
echo "======================================================================"
echo ""
echo "  🐍 API Django        : http://127.0.0.1:$PORT_API"
echo "     • Documentation   : http://127.0.0.1:$PORT_API/api/docs/"
echo "     • Schema OpenAPI  : http://127.0.0.1:$PORT_API/api/schema/"
echo "     • Admin Django    : http://127.0.0.1:$PORT_API/admin/"
echo ""
echo "  🌐 Site web INJS    : http://127.0.0.1:$PORT_FRONT"
echo ""
echo "  PID API  : $_API_PID"
echo "  PID Front: $_FRONT_PID"
echo ""
echo "  Pour arrêter :  kill $_API_PID $_FRONT_PID"
echo "  ou          :  pkill -f 'manage.py runserver' && pkill -f vite"
echo "======================================================================"

# Vérification rapide des serveurs (optionnelle, non bloquante)
_wait_for_server "http://127.0.0.1:$PORT_API/api/" "api" 2>/dev/null || true
_wait_for_server "http://127.0.0.1:$PORT_FRONT/" "front" 2>/dev/null || true

echo ""
echo ">> [ok] Les deux serveurs sont disponibles."
