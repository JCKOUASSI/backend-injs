#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
exec /app/scripts/gunicorn-autoscale.sh
