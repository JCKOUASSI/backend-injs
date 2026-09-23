#!/usr/bin/env bash
# Vérification hors base de données de l'image backend construite en CI/Docker Hub.
# L'ENTRYPOINT normal attend PostgreSQL et migre la base : ne jamais l'exécuter
# pour inspecter une image qui n'a pas de base attachée.
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ] || [ -z "$1" ]; then
  echo "Usage: $0 IMAGE [PLATFORM]" >&2
  exit 2
fi

image="$1"
args=(--rm)
if [ "$#" -eq 2 ] && [ -n "$2" ]; then
  args+=(--platform "$2")
fi

docker run "${args[@]}" --entrypoint /bin/sh "$image" -ec '
  if [ "$(id -un)" != appuser ]; then
    echo "::error::Le conteneur backend doit démarrer sous appuser" >&2
    exit 1
  fi
  if [ ! -d /app/staticfiles ]; then
    echo "::error::/app/staticfiles est absent dans le conteneur" >&2
    exit 1
  fi
  owner=$(stat -c %U /app/staticfiles)
  if [ "$owner" != appuser ] || [ ! -w /app/staticfiles ]; then
    echo "::error::/app/staticfiles doit appartenir à appuser et être accessible en écriture (propriétaire : $owner)" >&2
    exit 1
  fi
  if [ -z "$(find /app/staticfiles -type f -print -quit)" ]; then
    echo "::error::Aucun fichier statique collecté dans le conteneur" >&2
    exit 1
  fi
  python manage.py collectstatic --noinput --dry-run
'
