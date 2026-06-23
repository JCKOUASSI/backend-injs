#!/usr/bin/env bash
set -o errexit

# Commande explicite (CI, debug) : ne pas lancer migrate ni Gunicorn.
if [[ $# -gt 0 ]]; then
  exec "$@"
fi

if [[ "${RUN_MIGRATIONS:-true}" == "true" ]]; then
  python manage.py migrate --noinput
fi

exec /app/scripts/gunicorn-autoscale.sh
