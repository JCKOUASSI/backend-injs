#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Frontend dependencies missing; run npm ci in frontend/ first." >&2
  exit 1
fi

PORT=3000
cd "$FRONTEND"
exec npm run dev -- --host 0.0.0.0 --port "$PORT" --strictPort
