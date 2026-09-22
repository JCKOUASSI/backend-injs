#!/usr/bin/env bash
# =============================================================================
# fix_nginx_api_prod.sh — INJS-LMD production (VPS)
#
# Incident du 2026-09-22 : le reverse-proxy du VPS sert le SPA React pour
# TOUTES les routes ; /api/, /admin/, /static/ et /media/ ne sont plus
# proxifiés vers Django => POST /api/auth/login/ -> 405, connexion admin
# impossible (cf. backend/docs/ADMIN_DEPANNAGE.md §10.4).
#
# Ce script :
#   1. localise la config nginx/openresty du domaine (ou celle passée en $1) ;
#   2. détecte le port du conteneur backend (injs-be) ;
#   3. SAUVEGARDE la conf ;
#   4. insère les location proxy AVANT le location / du SPA (si absents) ;
#   5. valide avec nginx -t (restaure la sauvegarde si échec) ;
#   6. recharge nginx/openresty (demande confirmation, sauf --yes).
#
# Usage (sur le VPS, en root) :
#   bash fix_nginx_api_prod.sh              # auto-détection
#   bash fix_nginx_api_prod.sh /chemin/conf.conf
#   bash fix_nginx_api_prod.sh --yes        # sans confirmation interactive
#
# Lecture seule si rien à corriger. Idempotent.
# =============================================================================
set -euo pipefail

DOMAIN="injs.badge-qr-code.pro"
AUTO_YES=0
CONF_ARG=""
for arg in "$@"; do
  case "$arg" in
    --yes) AUTO_YES=1 ;;
    *) CONF_ARG="$arg" ;;
  esac
done

log() { printf '[fix-nginx] %s\n' "$*"; }
die() { printf '[fix-nginx] ERREUR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- détection
if [ -n "$CONF_ARG" ]; then
  [ -f "$CONF_ARG" ] || die "fichier introuvable: $CONF_ARG"
  CONF="$CONF_ARG"
else
  log "Recherche de la config routant le domaine $DOMAIN…"
  CONF=$(grep -rl "$DOMAIN" /etc/nginx/sites-enabled /etc/nginx/conf.d \
        /etc/nginx/nginx.conf /usr/local/openresty/nginx/conf 2>/dev/null \
        | head -1 || true)
  [ -n "$CONF" ] || die "aucune config trouvée pour $DOMAIN — passez le chemin en argument: bash fix_nginx_api_prod.sh /chemin/conf"
fi
log "Config cible: $CONF"

grep -q "$DOMAIN" "$CONF" || die "$CONF ne mentionne pas $DOMAIN — vérifiez manuellement."

# ------------------------------------------------------- port backend détecté
BACKEND_PORT="${BACKEND_PORT:-}"
if [ -z "$BACKEND_PORT" ]; then
  PORTS=$(docker ps --format '{{.Names}}\t{{.Ports}}' 2>/dev/null \
          | grep -i 'injs-be\|qrcode-badge\|qr-badge-app' | head -1 || true)
  if echo "$PORTS" | grep -qoE '0\.0\.0\.0:[0-9]+'; then
    BACKEND_PORT=$(echo "$PORTS" | grep -oE '0\.0\.0\.0:[0-9]+' | head -1 | cut -d: -f2)
  fi
fi
BACKEND_PORT="${BACKEND_PORT:-8000}"
log "Port backend retenu: $BACKEND_PORT (imposable via BACKEND_PORT=…)"
docker exec injs-be sh -c "curl -s -m 8 http://localhost:${BACKEND_PORT}/api/health/" >/dev/null 2>&1 \
  || log "ATTENTION: l'API n'a pas répondu en interne sur ${BACKEND_PORT} — vérifiez 'docker ps' avant de recharger."

# ------------------------------------------------------- blocs proxy à insérer
PROXY_HEADERS='proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme;'

PROXY_BLOCKS="    # --- routage API/admin vers Django (fix 2026-09-22, §10.4 ADMIN_DEPANNAGE) ---
    location /api/     { proxy_pass http://127.0.0.1:${BACKEND_PORT}; ${PROXY_HEADERS} }
    location /admin/   { proxy_pass http://127.0.0.1:${BACKEND_PORT}; ${PROXY_HEADERS} }"

# Statique déjà gérée par nginx (volume staticfiles) ? => on ne touche pas /static/
if ! grep -qE 'location[[:space:]]+/static/' "$CONF"; then
  PROXY_BLOCKS="${PROXY_BLOCKS}
    location /static/  { proxy_pass http://127.0.0.1:${BACKEND_PORT}; proxy_set_header Host \$host; proxy_set_header X-Forwarded-Proto \$scheme; }"
else
  log "/static/ déjà défini dans la conf — non modifié."
fi
if ! grep -qE 'location[[:space:]]+/media/' "$CONF"; then
  PROXY_BLOCKS="${PROXY_BLOCKS}
    location /media/   { proxy_pass http://127.0.0.1:${BACKEND_PORT}; proxy_set_header Host \$host; proxy_set_header X-Forwarded-Proto \$scheme; }"
fi
PROXY_BLOCKS="${PROXY_BLOCKS}
    # --- fin routage API/admin ---"

if grep -qE 'location[[:space:]]+/api/' "$CONF"; then
  log "location /api/ déjà présent — rien à faire (config déjà corrigée)."
  exit 0
fi

# ---------------------------------------------------------------- sauvegarde
BAK="${CONF}.bak-$(date +%F-%H%M%S)"
cp -a "$CONF" "$BAK"
log "Sauvegarde: $BAK"

# ---------------------------------------------------------------- insertion
# Blocs insérés juste AVANT le premier "location /" (fallback SPA).
LN=$(grep -nE 'location[[:space:]]+/[[:space:]]*\{' "$CONF" | head -1 | cut -d: -f1 || true)
[ -n "$LN" ] || die "insertion impossible : aucun 'location / {' repéré dans $CONF — correction manuelle requise (§10.4)."

TMP=$(mktemp)
head -n $((LN - 1)) "$CONF" > "$TMP"
printf '%s\n' "$PROXY_BLOCKS" >> "$TMP"
tail -n +"$LN" "$CONF" >> "$TMP"

mv "$TMP" "$CONF"
log "Blocs proxy insérés avant le fallback SPA."

# ------------------------------------------------------------- test + reload
NGINX_BIN=$(command -v nginx || command -v openresty || true)
[ -n "$NGINX_BIN" ] || die "nginx/openresty introuvable — validez manuellement avant de recharger."

if ! "$NGINX_BIN" -t 2>/dev/null; then
  log "nginx -t en ÉCHEC — restauration de la sauvegarde."
  cp -a "$BAK" "$CONF"
  "$NGINX_BIN" -t || true
  die "config restaurée depuis $BAK ; corrigez manuellement (§10.4)."
fi
log "nginx -t OK."

if [ "$AUTO_YES" -ne 1 ]; then
  printf '[fix-nginx] Recharger nginx/openresty maintenant ? [oui/non] '
  read -r REP
  [ "$REP" = "oui" ] || { log "Rechargement annulé — la config prendra effet au prochain reload."; exit 0; }
fi

if command -v openresty >/dev/null 2>&1 && systemctl is-active openresty >/dev/null 2>&1; then
  openresty -s reload
else
  systemctl reload nginx 2>/dev/null || nginx -s reload
fi
log "Reload effectué."

# ------------------------------------------------------------ vérification
sleep 1
log "=== Vérifications ==="
echo "--- GET /api/health/ (JSON attendu) ---"
curl -s --max-time 15 "https://${DOMAIN}/api/health/" | head -c 300; echo
echo "--- POST /api/auth/login/ admin (200 + JWT attendu) ---"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' --max-time 15 \
  -X POST "https://${DOMAIN}/api/auth/login/" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
echo "--- GET /admin/ (200 text/html Django attendu) ---"
curl -s -o /dev/null -w 'HTTP %{http_code} (%{content_type})\n' --max-time 15 "https://${DOMAIN}/admin/"
log "Terminé. Sauvegarde conservée : $BAK"
