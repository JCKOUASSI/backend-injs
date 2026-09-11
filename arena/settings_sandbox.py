# -*- coding: utf-8 -*-
"""Overlay de réglages pour exécuter l'application dans le sandbox Arena.

Généré automatiquement par arena/bootstrap.sh. Ne JAMAIS utiliser en production.
Ce module réimporte TOUS les réglages réels du projet (config.settings) puis ne
remplace que ce que le sandbox ne peut pas fournir : PostgreSQL, SMTP, broker.

Usage :  python manage.py test --settings=arena.settings_sandbox
Le dossier racine du projet doit être sur PYTHONPATH.
"""
from config.settings import *  # noqa: F401,F403
from config.settings import BASE_DIR as _BASE_DIR, INSTALLED_APPS as _INSTALLED_APPS
import os

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

# Prévisualisation Arena : l'hôte est dynamique mais on n'utilise PAS le littéral
# '*' (il ferait échouer le garde-fou de durcissement test_settings_allow_no_wildcard_literal).
# '.e2b.app' matche tous les sous-domaines de prévisualisation dynamiques.
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", ".e2b.app"]
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
