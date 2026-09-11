#!/usr/bin/env bash
# =============================================================================
# BOOTSTRAP ARENA — app-injs-lmd2026
# -----------------------------------------------------------------------------
# À lancer EN DÉBUT DE CHAQUE SESSION Arena.
# Raison : le snapshot du workspace conserve les fichiers sous /home/user mais
# EXCLUT .venv, node_modules, dist, build, __pycache__. L'environnement d'exécution
# est donc perdu entre deux sessions alors que le code, lui, persiste.
#
# Ce script est idempotent : le relancer ne casse rien et ne réinstalle que
# ce qui manque.
#
# Usage :  bash arena/bootstrap.sh
# =============================================================================
set -uo pipefail

RACINE="${RACINE:-/home/user}"
LOG="$RACINE/arena/.bootstrap.log"
mkdir -p "$RACINE/arena"
: > "$LOG"

ok()   { printf '  \033[32m[ok]\033[0m    %s\n' "$1"; }
warn() { printf '  \033[33m[attention]\033[0m %s\n' "$1"; }
ko()   { printf '  \033[31m[bloquant]\033[0m %s\n' "$1"; }
etape(){ printf '\n\033[1m== %s\033[0m\n' "$1"; }

echo "======================================================================"
echo " BOOTSTRAP ARENA — app-injs-lmd2026"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"

# --- 1. Localiser les trois pistes -------------------------------------------
etape "1. Localisation des pistes"
BACKEND="$(find "$RACINE" -maxdepth 4 -name manage.py -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null | head -1)"
FRONTEND="$(find "$RACINE" -maxdepth 4 -name package.json -not -path '*/node_modules/*' 2>/dev/null | head -1)"
MOBILE="$(find "$RACINE" -maxdepth 4 -name pubspec.yaml -not -path '*/node_modules/*' 2>/dev/null | head -1)"

if [ -n "$BACKEND" ]; then BACKEND="$(dirname "$BACKEND")"; ok "backend  : $BACKEND"; else ko "backend  : manage.py introuvable — le code n'est pas dans le workspace"; fi
if [ -n "$FRONTEND" ]; then FRONTEND="$(dirname "$FRONTEND")"; ok "frontend : $FRONTEND"; else ko "frontend : package.json introuvable"; fi
if [ -n "$MOBILE" ]; then MOBILE="$(dirname "$MOBILE")"; ok "mobile   : $MOBILE"; else warn "mobile   : pubspec.yaml introuvable (piste Flutter absente)"; fi
if [ -z "$BACKEND" ]; then echo; ko "ARRÊT : rien à préparer. Voir l'étape 0 du mode opératoire (amener le code)."; exit 2; fi

# --- 2. Interpréteur Python --------------------------------------------------
etape "2. Interpréteur Python"
PYV="$(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:2])))')"
if [ "$PYV" = "3.12" ]; then ok "Python $PYV — conforme au projet";
else warn "Python $PYV — le projet vise 3.12. Aucun 3.12 n'est disponible dans le sandbox.";
     warn "Conséquence : certaines dépendances épinglées peuvent exiger un ajustement."; fi

if [ ! -d "$BACKEND/.venv" ]; then
  python3 -m venv "$BACKEND/.venv" && ok "venv créé : $BACKEND/.venv"
else ok "venv déjà présent"; fi
# shellcheck disable=SC1091
. "$BACKEND/.venv/bin/activate"
python -m pip install --quiet --upgrade pip 2>>"$LOG" && ok "pip à jour"

# --- 3. Dépendances Python ---------------------------------------------------
etape "3. Dépendances Python"
if [ -f "$BACKEND/requirements.txt" ]; then REQ="$BACKEND/requirements.txt";
elif [ -f "$BACKEND/pyproject.toml" ]; then REQ=""; else REQ=""; warn "ni requirements.txt ni pyproject.toml"; fi
if [ -n "${REQ:-}" ]; then
  # psycopg2 n'a pas de serveur PostgreSQL dans le sandbox : on tente d'abord la
  # dépendance réelle, puis on retombe sur la variante binaire, puis on ignore.
  if python -m pip install --quiet -r "$REQ" 2>>"$LOG"; then ok "requirements installés";
  else warn "installation complète en échec (voir $LOG) — tentative sans psycopg2";
       grep -viE '^psycopg2' "$REQ" > "$BACKEND/.requirements-sans-pg.txt"
       python -m pip install --quiet -r "$BACKEND/.requirements-sans-pg.txt" 2>>"$LOG" \
         && ok "installé sans psycopg2 (SQLite de secours)" \
         || ko "installation impossible — lire $LOG"; fi
else python -c 'import django' 2>/dev/null && ok "Django déjà importable" || ko "aucune source de dépendances"; fi
python - <<'PY' 2>>"$LOG" || warn "Django non importable"
import django, sys
print(f"  Django {django.get_version()} sur Python {sys.version.split()[0]}")
PY

# --- 4. Dépendances frontend -------------------------------------------------
etape "4. Dépendances frontend"
if [ -n "$FRONTEND" ]; then
  cd "$FRONTEND"
  if [ -d node_modules ] && [ -f node_modules/.package-lock.json ]; then ok "node_modules déjà présent";
  else
    if [ -f package-lock.json ]; then npm ci --no-audit --no-fund >>"$LOG" 2>&1 && ok "npm ci terminé";
    else npm install --no-audit --no-fund >>"$LOG" 2>&1 && ok "npm install terminé" \
         || ko "npm install en échec — lire $LOG"; fi
  fi
fi

# --- 5. Configuration de secours pour le sandbox -----------------------------
etape "5. Réglages de sandbox (non invasifs)"
# Module de réglages réel du projet, lu dans manage.py : l'overlay doit le
# réimporter, sinon on perd INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK, etc.
SET_MOD="$(grep -oE 'DJANGO_SETTINGS_MODULE"?, ?"[A-Za-z0-9_.]+"' "$BACKEND/manage.py" \
           | grep -oE '"[A-Za-z0-9_.]+"$' | tr -d '"' | head -1)"
[ -z "$SET_MOD" ] && SET_MOD="$(grep -rhoE "DJANGO_SETTINGS_MODULE[^\"']*[\"'][A-Za-z0-9_.]+" "$BACKEND" --include='*.py' 2>/dev/null \
           | grep -oE '[A-Za-z0-9_.]+$' | head -1)"
[ -z "$SET_MOD" ] && { warn "module de réglages non détecté — l'overlay ne pourra pas être utilisé tel quel"; SET_MOD="projet.settings"; }
mkdir -p "$RACINE/arena"
touch "$RACINE/arena/__init__.py"
{
cat <<PY
# -*- coding: utf-8 -*-
"""Overlay de réglages pour exécuter l'application dans le sandbox Arena.

Généré automatiquement par arena/bootstrap.sh. Ne JAMAIS utiliser en production.
Ce module réimporte TOUS les réglages réels du projet ($SET_MOD) puis ne
remplace que ce que le sandbox ne peut pas fournir : PostgreSQL, SMTP, broker.

Usage :  python manage.py test --settings=arena.settings_sandbox
Le dossier racine du projet doit être sur PYTHONPATH.
"""
from $SET_MOD import *  # noqa: F401,F403
from $SET_MOD import BASE_DIR as _BASE_DIR, INSTALLED_APPS as _INSTALLED_APPS
import os
PY
cat <<'PY'

# SQLite si le projet importe django.contrib.postgres, la suite ne peut PAS
# tourner ici : relever l'écart et faire valider la piste sur PostgreSQL réel.
if any("contrib.postgres" in a for a in _INSTALLED_APPS):
    import warnings
    warnings.warn(
        "django.contrib.postgres est actif : SQLite ne suffira pas. "
        "Les tests doivent être joués contre un PostgreSQL réel.",
        RuntimeWarning,
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(_BASE_DIR, "db_sandbox.sqlite3"),
        "TEST": {"NAME": ":memory:"},
    }
}
PY
cat <<'PY'

# Prévisualisation Arena : l'hôte est dynamique, on ouvre en développement.
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["https://*.e2b.app"]
DEBUG = True

# Courriel : le SMTP Gmail du projet n'est pas joignable ici.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Tâches de fond : exécution immédiate et synchrone, pas de broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Stockage : médias locaux, pas de S3.
for _name in ("DEFAULT_FILE_STORAGE", "STORAGES"):
    if _name in globals():
        del globals()[_name]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PY
} > "$RACINE/arena/settings_sandbox.py"
ok "arena/settings_sandbox.py écrit (overlay de $SET_MOD)"


# --- 6. Garde-fous de dépôt --------------------------------------------------
etape "6. Garde-fous"
GITIGNORE="$RACINE/.gitignore-arena"
cat > "$GITIGNORE" <<'GI'
.venv/
node_modules/
db_sandbox.sqlite3
__pycache__/
*.pyc
.pytest_cache/
arena/.bootstrap.log
GI
ok ".gitignore-arena écrit (ne commitez JAMAIS .venv ni node_modules)"

DJ="$(python -c 'import django;print(django.VERSION[:2])' 2>/dev/null || echo '?')"
echo
echo "======================================================================"
echo " PRÊT — Django $DJ · backend $BACKEND"
echo " Prochaine étape : bash arena/probe.sh"
echo "======================================================================"
