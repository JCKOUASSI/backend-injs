#!/usr/bin/env bash
# Render build script
set -o errexit

pip install -r requirements.txt

# Créer le répertoire SQLite si nécessaire
mkdir -p /opt/render/project/src/data

python manage.py collectstatic --no-input
python manage.py migrate

# Charger les données de démo si la base est vide
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from authentication.models import User
if not User.objects.exists():
    print('Base vide — chargement des données de démo...')
    exec(open('seed_data.py').read())
else:
    print('Données existantes — seed ignoré.')
"

# Créer / mettre à jour les comptes mobile (mots de passe déterministes)
python scripts/seed_mobile_users.py
