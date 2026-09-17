#!/usr/bin/env bash
# =============================================================================
# LANCEUR FRONT VITE — port FIGÉ 3000 (règle projet, ne jamais changer)
# -----------------------------------------------------------------------------
# Usage : bash arena/lancer-front.sh
# Le port 3000 est inscrit dans frontend/vite.config.js avec strictPort:true :
# Vite échoue si 3000 est pris, il ne bascule JAMAIS sur un autre port
# (notamment plus jamais 5173). Prérequis : bash arena/bootstrap.sh.
# =============================================================================
set -uo pipefail
RACINE="${RACINE:-/home/user}"
FRONTEND="$(find "$RACINE" -maxdepth 4 -name package.json -not -path '*/node_modules/*' 2>/dev/null | head -1)"
FRONTEND="$(dirname "$FRONTEND")"
PORT=3000

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo ">> [bloquant] dépendances absentes : lancez d'abord  bash arena/bootstrap.sh"
  exit 2
fi

# .env.local de prévisualisation (chemins relatifs + admin Django), idempotent.
cat > "$FRONTEND/.env.local" <<'ENV'
VITE_API_URL=/api
VITE_ADMIN_URL=/admin/
VITE_REFRESH_FALLBACK=1
ENV

if ss -tln 2>/dev/null | grep -q ":$PORT "; then
  echo ">> [attention] un processus écoute déjà sur le port $PORT."
  echo "   Le front doit rester sur $PORT : libérez-le (pkill -f 'vite')"
  echo "   plutôt que d'accepter un autre port."
  exit 3
fi

cd "$FRONTEND" || exit 2
# Pas de --port : c'est vite.config.js qui fait foi (3000, strictPort).
exec env VITE_HMR_PROTOCOL=wss npm run dev -- --host 0.0.0.0
