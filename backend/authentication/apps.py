import os

from django.apps import AppConfig


def create_superuser_from_env():
    import logging
    from django.contrib.auth import get_user_model

    logger = logging.getLogger(__name__)

    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

    missing = [
        name for name, val in [
            ('DJANGO_SUPERUSER_USERNAME', username),
            ('DJANGO_SUPERUSER_EMAIL', email),
            ('DJANGO_SUPERUSER_PASSWORD', password),
        ]
        if not val
    ]
    if missing:
        logger.warning(
            "Création du super-utilisateur ignorée (variables manquantes: %s).",
            ", ".join(missing),
        )
        return

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        logger.info("Super-utilisateur '%s' existe déjà — ignoré.", username)
        return

    User.objects.create_superuser(username=username, email=email, password=password, role=User.Role.ADMIN)
    logger.info("Super-utilisateur '%s' créé avec succès.", username)


class AuthenticationConfig(AppConfig):
    name = 'authentication'

    def ready(self):
        from django.apps import apps
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_migrate, post_save

        # Après authentication : crée les groupes (souvent avant les permissions
        # des apps métier). Il faut ré‑exécuter ensure_role_groups après formations
        # / presences / … pour compléter les codenames créés plus tard (voir
        # role_groups.ensure_role_groups branche « merge »).
        post_migrate.connect(
            _on_post_migrate,
            sender=self,
            dispatch_uid='authentication_post_migrate',
        )
        for label in ('formations', 'presences', 'exports', 'dashboard'):
            try:
                app_config = apps.get_app_config(label)
            except LookupError:
                continue
            post_migrate.connect(
                _on_post_migrate,
                sender=app_config,
                dispatch_uid=f'authentication_ensure_roles_{label}',
            )
        post_save.connect(_on_user_saved, sender=get_user_model(), dispatch_uid='authentication_sync_role_group')


def _on_post_migrate(sender, **kwargs):
    from .role_groups import ensure_role_groups, sync_all_users_role_groups

    ensure_role_groups()
    sync_all_users_role_groups()
    create_superuser_from_env()


def _on_user_saved(sender, instance, **kwargs):
    from .role_groups import sync_user_role_group

    sync_user_role_group(instance)
