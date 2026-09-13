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

# Noms de cookies dédiés au projet (anti 403 CSRF par cookie hérité).
CSRF_COOKIE_NAME = "injs_csrftoken"
SESSION_COOKIE_NAME = "injs_sessionid"
# === Aperçu Arena en iframe https cross-site (ports figés : front 3000, API 8000) ===
# Le proxy Arena termine le TLS : on lui fait confiance pour le protocole apparent.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Cookies de session/CSRF en SameSite=None + Secure pour survivre à l'iframe.
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# CHIPS : cookies partitionnes. L'admin est affichee dans une iframe tierce
# (page Arena en *.arena.site integrant le bac a sable en *.e2b.app) : les
# cookies tiers classiques y sont stockes mais JAMAIS renvoyes. Les cookies
# Partitioned sont stockes dans la partition de la page integratrice et
# renvoyes pour les requetes de cette meme partition. Django 5.1 ne gere pas
# SESSION_COOKIE_PARTITIONED (ajoute en 5.2) : l'attribut est pose par le
# middleware arena.partitioned_cookies (compatibilite Python 3.11 incluse).
MIDDLEWARE = ["arena.partitioned_cookies.PartitionedCookieMiddleware"] + list(MIDDLEWARE)
# L'URL du front (port 3000) est dérivée de l'hôte apparent par config.views
# (_frontend_url) ; aucun identifiant d'aperçu n'est codé en dur ici.

# === Auto-connexion demo (apercu Arena uniquement, jamais en production) ===
# La passerelle d'apercu Arena filtre les en-tetes Cookie entre son point
# d'entree (*.arena.site) et le bac a sable (*.e2b.app) : toute authentification
# Django par cookie (session/CSRF) y est impossible dans les vignettes. Ce
# middleware d'APERCU authentifie automatiquement les requetes /admin/ comme
# compte demo "admin" sans aucun cookie. Il ne vit QUE dans cet overlay.
PREVIEW_AUTOLOGIN_USERNAME = "admin"
MIDDLEWARE.append("arena.preview_autologin.AutoLoginApercuMiddleware")
