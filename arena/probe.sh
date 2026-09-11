#!/usr/bin/env bash
# =============================================================================
# PROBE ARENA — état réel du projet app-injs-lmd2026
# -----------------------------------------------------------------------------
# À lancer APRÈS le bootstrap et AVANT le premier prompt (P00-01).
# Ce script produit le constat chiffré qui sert de baseline de non-régression.
# Il compare aux chiffres de l'audit [S1] consignés dans le livrable.
#
# Usage :  bash arena/probe.sh
# Sortie : arena/probe-YYYYMMDD-HHMM.txt
# =============================================================================
set -uo pipefail
RACINE="${RACINE:-/home/user}"
OUT="$RACINE/arena/probe-$(date +%Y%m%d-%H%M).txt"
exec > >(tee "$OUT") 2>&1

BACKEND="$(find "$RACINE" -maxdepth 4 -name manage.py -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null | head -1)"
[ -n "$BACKEND" ] && BACKEND="$(dirname "$BACKEND")"
FRONTEND="$(find "$RACINE" -maxdepth 4 -name package.json -not -path '*/node_modules/*' 2>/dev/null | head -1)"
[ -n "$FRONTEND" ] && FRONTEND="$(dirname "$FRONTEND")"
MOBILE="$(find "$RACINE" -maxdepth 4 -name pubspec.yaml 2>/dev/null | head -1)"
[ -n "$MOBILE" ] && MOBILE="$(dirname "$MOBILE")"

echo "======================================================================"
echo " PROBE — $(date '+%Y-%m-%d %H:%M')"
echo "======================================================================"
echo
echo "Colonnes : RELEVE  |  AUDIT [S1]  |  ECART"
echo

ligne() { printf '  %-34s %10s   %10s   %8s\n' "$1" "$2" "$3" "$4"; }
echo "---------------------------------------------------------------------"
echo " PISTE BACKEND"
echo "---------------------------------------------------------------------"
if [ -n "$BACKEND" ]; then
  cd "$BACKEND"
  # shellcheck disable=SC1091
  [ -d .venv ] && . .venv/bin/activate
  # Toutes les mesures EXCLUENT l'environnement virtuel et les dépendances,
  # sinon on compte les sources de Django au lieu de celles du projet.
  PRUNE=(-not -path '*/.venv/*' -not -path '*/node_modules/*' -not -path '*/.git/*')
  PYFILES="$(find . -name '*.py' "${PRUNE[@]}" -print0 2>/dev/null | tr '\0' '\n')"
  ligne "Applications Django" "$(find . -maxdepth 3 -name apps.py "${PRUNE[@]}" | wc -l)" "20" ""
  ligne "Modèles (models.Model)" "$(echo "$PYFILES" | tr '\n' '\0' | xargs -0 grep -hoE 'class [A-Za-z_]+\(models\.Model' 2>/dev/null | wc -l)" "133" ""
  ligne "Migrations" "$(find . -path '*/migrations/*.py' ! -name '__init__.py' "${PRUNE[@]}" | wc -l)" "184" ""
  ligne "Lignes Python" "$(echo "$PYFILES" | tr '\n' '\0' | xargs -0 cat 2>/dev/null | wc -l)" "88068" ""
  ligne "Fichiers de tests" "$(find . -name 'test*.py' "${PRUNE[@]}" | wc -l)" "76" ""
  ligne "Méthodes de test" "$(echo "$PYFILES" | tr '\n' '\0' | xargs -0 grep -hoE '^[[:space:]]+def test_[a-zA-Z0-9_]+' 2>/dev/null | wc -l)" "943" ""
  ligne "print() restants" "$(echo "$PYFILES" | grep -v test | tr '\n' '\0' | xargs -0 grep -ho 'print(' 2>/dev/null | wc -l)" "288" ""
  ligne "select/prefetch_related" "$(echo "$PYFILES" | tr '\n' '\0' | xargs -0 grep -hoE '(select|prefetch)_related' 2>/dev/null | wc -l)" "359" ""
  ligne "Commandes de gestion" "$(find . -path '*/management/commands/*.py' ! -name '__init__.py' "${PRUNE[@]}" | wc -l)" "31" ""
  echo
  echo "  -- versions réellement installées --"
  python - <<'PY'
mods = [("Django","django"),("DRF","rest_framework"),("SimpleJWT","rest_framework_simplejwt")]
for lib, m in mods:
    try:
        mod = __import__(m)
        v = getattr(mod, "__version__", None) or getattr(mod, "VERSION", None) or getattr(mod, "get_version", lambda: "?")()
        print(f"  {lib:12s} {v}")
    except Exception:
        print(f"  {lib:12s} ABSENT")
import sys
print(f"  Python       {sys.version.split()[0]}   (le projet vise 3.12)")
PY
  echo
  echo "  -- le plus gros fichier --"
  find . -name '*.py' -not -path './.venv/*' | xargs wc -l 2>/dev/null | sort -rn | sed -n '2p' | sed 's/^/  /'
  echo "    (audit : formations/api_views.py 4 980 l.)"
else
  echo "  AUCUN backend trouvé dans le workspace."
fi

echo
echo "---------------------------------------------------------------------"
echo " PISTE FRONTEND"
echo "---------------------------------------------------------------------"
if [ -n "$FRONTEND" ]; then
  cd "$FRONTEND"
  ligne "Fichiers .jsx/.js (hors node_modules)" "$(find . -name '*.jsx' -o -name '*.js' | grep -v node_modules | wc -l)" "105" ""
  ligne "Lignes" "$(find . \( -name '*.jsx' -o -name '*.js' \) -not -path './node_modules/*' | xargs cat 2>/dev/null | wc -l)" "35495" ""
  ligne "Fichiers de test" "$(find . \( -name '*.test.jsx' -o -name '*.test.js' -o -name '*.spec.js*' \) -not -path './node_modules/*' | wc -l)" "0" ""
  ligne "Fichiers > 650 lignes" "$(find . \( -name '*.jsx' -o -name '*.js' \) -not -path './node_modules/*' | xargs wc -l 2>/dev/null | awk '$1>650 && $2!="total"' | wc -l)" "9" ""
  echo
  echo "  -- le plus gros fichier --"
  find . \( -name '*.jsx' -o -name '*.js' \) -not -path './node_modules/*' | xargs wc -l 2>/dev/null | sort -rn | sed -n '2p' | sed 's/^/  /'
  echo "    (audit : Statistiques.jsx 5 508 l.)"
else
  echo "  AUCUN frontend trouvé dans le workspace."
fi

echo
echo "---------------------------------------------------------------------"
echo " PISTE MOBILE"
echo "---------------------------------------------------------------------"
if [ -n "$MOBILE" ]; then
  cd "$MOBILE"
  ligne "Fichiers Dart" "$(find . -name '*.dart' | wc -l)" "40" ""
  ligne "Lignes Dart" "$(find . -name '*.dart' | xargs cat 2>/dev/null | wc -l)" "7818" ""
  command -v flutter >/dev/null 2>&1 && echo "  flutter : présent" \
    || echo "  flutter : ABSENT du sandbox -> le 3e feu vert ne peut PAS être levé ici."
else
  echo "  AUCUN projet Flutter trouvé."
  echo "  flutter : ABSENT du sandbox -> le 3e feu vert ne peut PAS être levé ici."
fi

echo
echo "---------------------------------------------------------------------"
echo " CAPACITÉS DU SANDBOX (conditionnent les gates)"
echo "---------------------------------------------------------------------"
cap() { command -v "$1" >/dev/null 2>&1 && echo "  $2 : présent" || echo "  $2 : ABSENT"; }
cap psql "PostgreSQL (client)"; cap docker "Docker"
cap node "Node $(node --version 2>/dev/null)"; cap git "Git $(git --version 2>/dev/null | awk '{print $3}')"
python3 -c 'import sqlite3;print(f"  SQLite : {sqlite3.sqlite_version} (base de secours)")'
echo "  Réseau : $(curl -sS -m 10 -o /dev/null -w '%{http_code}' https://pypi.org/simple/ 2>/dev/null) vers pypi.org"

echo
echo "---------------------------------------------------------------------"
echo " VERDICT POUR P00-01 (baseline de non-régression)"
echo "---------------------------------------------------------------------"
if [ -n "$BACKEND" ]; then
  echo "  Le backend est présent : P00-01 peut être exécuté."
  echo "  ATTENTION : relevez les écarts ci-dessus AVANT de commencer. Toute"
  echo "  différence avec l'audit [S1] doit être tranchée par le pilote, car"
  echo "  l'audit fait foi (incohérence J.8)."
else
  echo "  BLOQUANT : amenez d'abord le code dans le workspace (mode opératoire, étape 0)."
fi
echo
echo "Rapport écrit dans : $OUT"
