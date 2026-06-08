#!/usr/bin/env bash
# Régénère Manuel utilisateur App Statistiques.docx si le .md source a changé.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MD="$ROOT/docs/Manuel utilisateur App Statistiques.md"
DOCX="$ROOT/docs/Manuel utilisateur App Statistiques.docx"
SCRIPT="$ROOT/scripts/generate_manuel_statistiques_docx.py"

if [[ ! -f "$MD" ]]; then
  exit 0
fi

if [[ ! -f "$DOCX" ]] || [[ "$MD" -nt "$DOCX" ]]; then
  if [[ -f "$SCRIPT" ]]; then
    python3 "$SCRIPT" 2>/dev/null || python "$SCRIPT" 2>/dev/null || true
  fi
fi

exit 0
