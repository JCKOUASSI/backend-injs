#!/usr/bin/env bash
# =============================================================================
# LANCEUR API DJANGO — port FIGÉ 8000 (ne jamais changer jusqu'à fin de projet)
# -----------------------------------------------------------------------------
# Usage : bash arena/lancer-api.sh
# Le port est imposé ici ET rien d'autre ne doit écouter sur 8000.
# Prérequis : bash arena/bootstrap.sh une fois après chaque réinitialisation.
# =============================================================================
set -uo pipefail
RACINE="${RACINE:-/home/user}"
BACKEND="$(find "$RACINE" -maxdepth 4 -name manage.py -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null | head -1)"
BACKEND="$(dirname "$BACKEND")"
PORT=8000

if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  echo ">> [bloquant] environnement absent : lancez d'abord  bash arena/bootstrap.sh"
  exit 2
fi

if ss -tln 2>/dev/null | grep -q ":$PORT "; then
  echo ">> [attention] un processus écoute déjà sur le port $PORT."
  echo "   L'API doit rester sur $PORT : libérez-le (pkill -f 'manage.py runserver')"
  echo "   plutôt que de lancer l'API sur un autre port."
  exit 3
fi

cd "$BACKEND" || exit 2
export PYTHONPATH="$RACINE:$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
exec .venv/bin/python manage.py runserver 0.0.0.0:$PORT --settings=arena.settings_sandbox
