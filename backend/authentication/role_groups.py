from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()


ROLE_GROUP_NAMES = {
    User.Role.ADMIN: "ROLE_ADMIN",
    User.Role.DIRECTION: "ROLE_DIRECTION",
    User.Role.CHEF_CPFAE_ADMIN: "ROLE_CHEF_CPFAE_ADMIN",
    User.Role.CPFAE_ADMIN: "ROLE_CPFAE_ADMIN",
    User.Role.CHEF_SECRETARIAT: "ROLE_CHEF_SECRETARIAT",
    User.Role.SECRETARIAT: "ROLE_SECRETARIAT",
    User.Role.FINANCE: "ROLE_FINANCE",
    User.Role.ENCADRANT: "ROLE_ENCADRANT",
    User.Role.AUDITEUR: "ROLE_AUDITEUR",
}

CORE_APPS = ("authentication", "formations", "presences", "exports")

ROLE_POLICY = {
    User.Role.ADMIN: {
        "apps": CORE_APPS,
        "actions": ("view", "add", "change", "delete"),
    },
    User.Role.CHEF_CPFAE_ADMIN: {
        "apps": CORE_APPS,
        "actions": ("view", "add", "change", "delete"),
    },
    User.Role.CPFAE_ADMIN: {
        "apps": CORE_APPS,
        "actions": ("view", "add", "change", "delete"),
    },
    User.Role.DIRECTION: {
        "apps": CORE_APPS,
        "actions": ("view",),
    },
    User.Role.CHEF_SECRETARIAT: {
        "apps": ("formations", "presences"),
        "actions": ("view", "add", "change", "delete"),
        # Interdit uniquement la création de nouvelles fiches auditeur.
        # Toutes les autres actions (y compris suppression) restent autorisées.
        "exclude_codenames": ("add_participant",),
    },
    User.Role.SECRETARIAT: {
        "apps": ("formations", "presences"),
        "actions": ("view", "add", "change", "delete"),
        "exclude_codenames": ("add_participant",),
    },
    User.Role.FINANCE: {
        "apps": ("formations", "presences", "exports"),
        "actions": ("view",),
    },
    User.Role.ENCADRANT: {
        "apps": ("formations", "presences"),
        "actions": ("view", "change"),
    },
    User.Role.AUDITEUR: {
        "apps": ("formations", "presences"),
        "actions": ("view",),
    },
}


def _permission_codenames(actions, model_name):
    return [f"{action}_{model_name}" for action in actions]


def _permissions_for_policy(policy):
    exclude = set(policy.get("exclude_codenames", ()))
    permissions = Permission.objects.none()
    for app_label in policy["apps"]:
        for model in apps.get_app_config(app_label).get_models():
            codenames = [
                c for c in _permission_codenames(policy["actions"], model._meta.model_name)
                if c not in exclude
            ]
            if codenames:
                permissions = permissions | Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename__in=codenames,
                )
    return permissions.distinct()


def ensure_role_groups(force_reset=False):
    """Crée les groupes de rôles et initialise leurs permissions.

    Par défaut (force_reset=False) :
        - Si le groupe n'existe pas encore → le crée et lui applique le ROLE_POLICY.
        - Si le groupe existe déjà → on ajoute les permissions de la politique
          encore absentes (nouveaux modèles après la création du groupe).
          Les permissions retirées manuellement dans l'admin ne sont pas ré‑ajoutées
          si elles ne figurent plus dans la politique ; pour un réalignement complet,
          utiliser force_reset=True.

    Avec force_reset=True :
        - Remet les permissions de TOUS les groupes à l'état défini dans ROLE_POLICY,
          écrasant les modifications manuelles éventuelles.
          Utile pour revenir aux valeurs par défaut.
    """
    for role, group_name in ROLE_GROUP_NAMES.items():
        group, created = Group.objects.get_or_create(name=group_name)
        policy = ROLE_POLICY[role]
        permissions = _permissions_for_policy(policy)
        if created or force_reset:
            group.permissions.set(permissions)
        else:
            # Nouvelles permissions (nouveaux modèles / migrations après création du groupe).
            have = set(group.permissions.values_list("id", flat=True))
            want_ids = set(permissions.values_list("id", flat=True))
            missing = want_ids - have
            if missing:
                group.permissions.add(
                    *Permission.objects.filter(pk__in=missing)
                )


def sync_user_role_group(user):
    """Synchronise l'appartenance du user à son groupe de rôle unique."""
    if not user or not user.pk:
        return

    role_group_names = set(ROLE_GROUP_NAMES.values())
    target_group_name = ROLE_GROUP_NAMES.get(user.role)
    if not target_group_name:
        return

    current_role_groups = user.groups.filter(name__in=role_group_names)
    user.groups.remove(*current_role_groups)

    target_group = Group.objects.filter(name=target_group_name).first()
    if target_group:
        user.groups.add(target_group)


def sync_all_users_role_groups():
    for user in User.objects.all().only("id", "role"):
        sync_user_role_group(user)
