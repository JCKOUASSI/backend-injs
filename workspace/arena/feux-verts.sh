#!/usr/bin/env bash
# =============================================================================
# LES 3 FEUX VERTS — gate de fin de prompt
# -----------------------------------------------------------------------------
# Un prompt n'est PAS terminé tant que ces trois feux ne sont pas verts.
# C'est la règle maîtresse « zéro régression » du livrable (partie A, boucle
# d'exécution, étape 7).
#
# Adaptation Arena : le sandbox n'a ni PostgreSQL ni Flutter. Les feux 1 et 2
# sont levables ici ; le feu 3 est déclaré NON LEVABLE et doit être validé sur
# un poste de développement équipé. Le script ne ment jamais là-dessus : il
# l'affiche en clair plutôt que de simuler un succès.
#
# Usage :  bash arena/feux-verts.sh [nom-du-prompt]
# Sortie : code de retour 0 si les feux levables sont verts, 1 sinon.
# =============================================================================
set -uo pipefail
RACINE="${RACINE:-/home/user}"
PROMPT="${1:-sans-nom}"
LOG="$RACINE/arena/feux-verts.log"
: > "$LOG"

V=0; R=0; J=0; r1=0; r2=0; r3=0; F1="ROUGE"; F2="ROUGE"; F3="NON LEVABLE"

BACKEND="$(find "$RACINE" -maxdepth 4 -name manage.py -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null | head -1)"
[ -n "$BACKEND" ] && BACKEND="$(dirname "$BACKEND")"
FRONTEND="$(find "$RACINE" -maxdepth 4 -name package.json -not -path '*/node_modules/*' 2>/dev/null | head -1)"
[ -n "$FRONTEND" ] && FRONTEND="$(dirname "$FRONTEND")"

# L'overlay arena.settings_sandbox vit sous $RACINE : il faut que $RACINE et le
# dossier du projet soient importables, sinon Django ne le trouve pas.
export PYTHONPATH="$RACINE:$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
# Si un overlay a été généré par le bootstrap, on l'utilise par défaut.
if [ -f "$RACINE/arena/settings_sandbox.py" ] && [ -z "${DJANGO_SETTINGS_MODULE_SANDBOX:-}" ]; then
  DJANGO_SETTINGS_MODULE_SANDBOX="arena.settings_sandbox"
  echo "(overlay de réglages détecté : $DJANGO_SETTINGS_MODULE_SANDBOX)"
fi

echo "======================================================================"
echo " 3 FEUX VERTS — $PROMPT — $(date '+%Y-%m-%d %H:%M')"
echo "======================================================================"

# -----------------------------------------------------------------------------
if [ -n "$BACKEND" ]; then
  echo
  echo "--- FEU 1 : BACKEND (migrations, checks, tests) -------------------"
  cd "$BACKEND"
  # shellcheck disable=SC1091
  [ -d .venv ] && . .venv/bin/activate
  SETTINGS="${DJANGO_SETTINGS_MODULE_SANDBOX:-}"
  OPT=""; [ -n "$SETTINGS" ] && OPT="--settings=$SETTINGS"

  echo "  > makemigrations --check --dry-run"
  if python manage.py makemigrations --check --dry-run $OPT >>"$LOG" 2>&1; then
    echo "    [ok] aucune migration manquante"; ((V++))
  else echo "    [KO] migrations manquantes ou modèle instable — voir $LOG"; ((R++)); ((r1++)); fi

  echo "  > check --deploy"
  python manage.py check $OPT >>"$LOG" 2>&1 && { echo "    [ok] checks Django"; ((V++)); } \
    || { echo "    [KO] checks Django — voir $LOG"; ((R++)); ((r1++)); }

  echo "  > test (SQLite de secours)"
  if python manage.py test $OPT --parallel 2 >>"$LOG" 2>&1; then
    echo "    [ok] suite de tests verte"; ((V++))
  else
    echo "    [KO] tests en échec — voir $LOG"; ((R++)); ((r1++))
    echo "    (si l'échec vient de SQL spécifique PostgreSQL, le relever comme"
    echo "     écart d'environnement et le faire trancher par le pilote)"
  fi
  [ $r1 -eq 0 ] && F1="VERT"
else
  echo; echo "--- FEU 1 : backend absent du workspace ------------------------------"
fi

# -----------------------------------------------------------------------------
if [ -n "$FRONTEND" ]; then
  echo
  echo "--- FEU 2 : FRONTEND (lint, build, tests) --------------------------"
  cd "$FRONTEND"
  echo "  > lint"
  if npm run lint --silent >>"$LOG" 2>&1; then echo "    [ok] ESLint 0 erreur"; ((V++));
  else echo "    [KO] ESLint — voir $LOG"; ((R++)); ((r2++)); fi

  echo "  > build"
  if npm run build --silent >>"$LOG" 2>&1; then echo "    [ok] build Vite"; ((V++));
  else echo "    [KO] build Vite — voir $LOG"; ((R++)); ((r2++)); fi

  echo "  > test"
  if npm run test --silent -- --run >>"$LOG" 2>&1; then echo "    [ok] tests Vitest"; ((V++));
  else echo "    [KO] tests Vitest — voir $LOG (avant P00-04, aucun test n'existe : normal)"; ((R++)); ((r2++)); fi
  [ $r2 -eq 0 ] && F2="VERT"
else
  echo; echo "--- FEU 2 : frontend absent du workspace -----------------------------"
fi

# -----------------------------------------------------------------------------
echo
echo "--- FEU 3 : MOBILE (flutter analyze) ---------------------------------"
if command -v flutter >/dev/null 2>&1; then
  MOBILE="$(find "$RACINE" -maxdepth 4 -name pubspec.yaml 2>/dev/null | head -1)"
  [ -n "$MOBILE" ] && cd "$(dirname "$MOBILE")"
  if flutter analyze >>"$LOG" 2>&1; then echo "    [ok] flutter analyze"; F3="VERT"; ((V++))
  else echo "    [KO] flutter analyze — risque R6 (assets/app.env)"; F3="ROUGE"; ((R++)); ((r3++)); fi
else
  echo "    [--] Flutter n'est pas installé dans le sandbox Arena."
  echo "         Ce feu DOIT être levé sur un poste équipé avant la gate de vague."
  echo "         Ne le considérez jamais comme vert par défaut."
  ((J++))
fi

# -----------------------------------------------------------------------------
echo
echo "======================================================================"
printf "  FEU 1 backend  : %-12s\n" "$F1"
printf "  FEU 2 frontend : %-12s\n" "$F2"
printf "  FEU 3 mobile   : %-12s\n" "$F3"
echo "  contrôles verts : $V   rouges : $R   non levables : $J"
if [ "$R" -eq 0 ] && [ "$F1" = "VERT" ]; then
  echo "  VERDICT : GATE PASSÉE pour ce qui est vérifiable dans Arena."
  echo "            Le feu 3 reste à valider hors sandbox avant la gate de vague."
  echo "======================================================================"
  exit 0
else
  echo "  VERDICT : GATE NON PASSÉE — corriger avant d'ouvrir le prompt suivant."
  echo "======================================================================"
  exit 1
fi
