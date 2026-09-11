#!/usr/bin/env bash
# Synchronise la documentation Statistiques après session ou édition du manuel.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    PY="$c"
    break
  fi
done

if [[ -z "$PY" ]]; then
  exit 0
fi

MD="$ROOT/docs/Manuel utilisateur App Statistiques.md"
DOCX="$ROOT/docs/Manuel utilisateur App Statistiques.docx"
FICHE="$ROOT/Fiche de travaux App - Statistiques.txt"

# Word : régénérer si .md plus récent que .docx
if [[ -f "$MD" ]] && [[ -f "$ROOT/scripts/generate_manuel_statistiques_docx.py" ]]; then
  if [[ ! -f "$DOCX" ]] || [[ "$MD" -nt "$DOCX" ]]; then
    "$PY" "$ROOT/scripts/generate_manuel_statistiques_docx.py" 2>/dev/null || true
  fi
fi

# Fiche de travaux : horodatage
if [[ -f "$FICHE" ]] && [[ -f "$ROOT/scripts/sync_fiche_travaux_statistiques.py" ]]; then
  "$PY" "$ROOT/scripts/sync_fiche_travaux_statistiques.py" 2>/dev/null || true
fi

exit 0
