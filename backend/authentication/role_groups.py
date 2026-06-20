import logging

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()
logger = logging.getLogger(__name__)


# Rôles pouvant accéder à l'admin Django ET à la plateforme web.
DUAL_ACCESS_ROLES = frozenset({
    User.Role.ADMIN,
    User.Role.CHEF_CPFAE_ADMIN,
    User.Role.CPFAE_ADMIN,
})

# Rôles réservés à l'application mobile (pas de plateforme web ni admin Django).
MOBILE_ONLY_ROLES = frozenset({
    User.Role.AUDITEUR,
    User.Role.FORMATEUR,
})

# Rôles autorisés sur la plateforme web React (sans device_id mobile).
ALLOWED_WEB_ROLES = frozenset({
    *DUAL_ACCESS_ROLES,
    User.Role.DIRECTION,
    User.Role.CHEF_SECRETARIAT,
    User.Role.SECRETARIAT,
    User.Role.FINANCE,
    User.Role.ARCHIVE,
    User.Role.ENCADRANT,
    User.Role.SUPERVISEUR,
})

# Personnel web hors module Finance (badgeage, formations, modules, dashboard opérationnel).
OPERATIONAL_WEB_ROLES = frozenset(ALLOWED_WEB_ROLES - {User.Role.FINANCE})

# Alias sémantique — même ensemble que DUAL_ACCESS_ROLES.
ADMIN_LEVEL_ROLES = DUAL_ACCESS_ROLES

SECRETARIAT_ROLES = frozenset({
    User.Role.CHEF_SECRETARIAT,
    User.Role.SECRETARIAT,
})

# Accès global formations / dashboard (filtre secrétariat optionnel).
GLOBAL_ACCESS_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.DIRECTION,
    User.Role.ARCHIVE,
})

DASHBOARD_SECRETARIAT_FILTER_ROLES = GLOBAL_ACCESS_ROLES

PARTICIPANT_LIST_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.DIRECTION,
    User.Role.ARCHIVE,
    *SECRETARIAT_ROLES,
    User.Role.ENCADRANT,
})

LISTE_CLASSE_EXPORT_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.DIRECTION,
    User.Role.ARCHIVE,
    *SECRETARIAT_ROLES,
    User.Role.ENCADRANT,
})

STATS_ACCESS_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.DIRECTION,
    User.Role.ARCHIVE,
    *SECRETARIAT_ROLES,
    User.Role.FINANCE,
    User.Role.ENCADRANT,
})

GLOBAL_STATS_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.DIRECTION,
    User.Role.ARCHIVE,
    User.Role.FINANCE,
})

USERS_PAGE_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.DIRECTION,
    *SECRETARIAT_ROLES,
})

USER_MUTATION_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    *SECRETARIAT_ROLES,
})

BADGE_ACCOUNT_ROLES = MOBILE_ONLY_ROLES

USER_MANAGEABLE_ROLES = frozenset({
    User.Role.DIRECTION,
    User.Role.CHEF_CPFAE_ADMIN,
    User.Role.CPFAE_ADMIN,
    *SECRETARIAT_ROLES,
    User.Role.FINANCE,
    User.Role.ARCHIVE,
    User.Role.ENCADRANT,
    User.Role.SUPERVISEUR,
    *MOBILE_ONLY_ROLES,
})

FINANCE_MODULE_ROLES = frozenset({
    User.Role.FINANCE,
    User.Role.DIRECTION,
    User.Role.ARCHIVE,
})

FORMATION_MUTATION_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    *SECRETARIAT_ROLES,
})

PRESENCE_VIEW_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.DIRECTION,
    User.Role.ARCHIVE,
    *SECRETARIAT_ROLES,
    User.Role.ENCADRANT,
})

PRESENCE_ACTION_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.ENCADRANT,
    *SECRETARIAT_ROLES,
})

SUPERVISION_ROLES = frozenset({
    *ADMIN_LEVEL_ROLES,
    User.Role.ENCADRANT,
    *SECRETARIAT_ROLES,
})

IMPORT_ROLES = FORMATION_MUTATION_ROLES

# Hiérarchie stricte : index bas = rang élevé.
ROLE_HIERARCHY = [
    User.Role.ADMIN,
    User.Role.DIRECTION,
    User.Role.CHEF_CPFAE_ADMIN,
    User.Role.CPFAE_ADMIN,
    User.Role.CHEF_SECRETARIAT,
    User.Role.SECRETARIAT,
    User.Role.FINANCE,
    User.Role.ARCHIVE,
    User.Role.ENCADRANT,
    User.Role.SUPERVISEUR,
    User.Role.FORMATEUR,
    User.Role.AUDITEUR,
]

ROLE_LABELS = {value: str(label) for value, label in User.Role.choices}

ROLE_GROUP_NAMES = {
    User.Role.ADMIN: "ROLE_ADMIN",
    User.Role.DIRECTION: "ROLE_DIRECTION",
    User.Role.CHEF_CPFAE_ADMIN: "ROLE_CHEF_CPFAE_ADMIN",
    User.Role.CPFAE_ADMIN: "ROLE_CPFAE_ADMIN",
    User.Role.CHEF_SECRETARIAT: "ROLE_CHEF_SECRETARIAT",
    User.Role.SECRETARIAT: "ROLE_SECRETARIAT",
    User.Role.FINANCE: "ROLE_FINANCE",
    User.Role.ARCHIVE: "ROLE_ARCHIVE",
    User.Role.ENCADRANT: "ROLE_ENCADRANT",
    User.Role.SUPERVISEUR: "ROLE_SUPERVISEUR",
    User.Role.FORMATEUR: "ROLE_FORMATEUR",
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
        "apps": ("formations", "presences", "suiviEvaluation"),
        "actions": ("view", "add", "change", "delete"),
        # Interdit uniquement la création de nouvelles fiches auditeur.
        # Toutes les autres actions (y compris suppression) restent autorisées.
        "exclude_codenames": ("add_participant",),
    },
    User.Role.SECRETARIAT: {
        "apps": ("formations", "presences", "suiviEvaluation"),
        "actions": ("view", "add", "change", "delete"),
        "exclude_codenames": ("add_participant",),
    },
    User.Role.FINANCE: {
        "apps": ("formations", "presences", "exports"),
        "actions": ("view",),
    },
    User.Role.ARCHIVE: {
        "apps": CORE_APPS + ("suiviEvaluation",),
        "actions": ("view",),
    },
    User.Role.ENCADRANT: {
        "apps": ("formations", "presences", "suiviEvaluation"),
        "actions": ("view", "add", "change", "delete"),
    },
    User.Role.SUPERVISEUR: {
        "apps": ("suiviEvaluation",),
        "actions": ("view", "add", "change", "delete"),
    },
    User.Role.FORMATEUR: {
        "apps": ("formations", "presences"),
        "actions": ("view",),
    },
    User.Role.AUDITEUR: {
        "apps": ("formations", "presences"),
        "actions": ("view",),
    },
}


def get_subordinate_roles(role):
    """Retourne les rôles strictement inférieurs au rôle donné."""
    if role not in ROLE_HIERARCHY:
        return []
    idx = ROLE_HIERARCHY.index(role)
    return ROLE_HIERARCHY[idx + 1:]


def get_creatable_roles(role):
    """Retourne les rôles qu'un utilisateur peut créer."""
    subordinates = get_subordinate_roles(role)
    if role == User.Role.CHEF_CPFAE_ADMIN and User.Role.DIRECTION not in subordinates:
        return [User.Role.DIRECTION, *subordinates]
    return subordinates


def get_manageable_roles(role):
    """Rôles créables visibles dans la page Utilisateurs (hors ADMIN système)."""
    return [r for r in get_creatable_roles(role) if r in USER_MANAGEABLE_ROLES]


def get_staff_filter_roles(role):
    """Rôles proposés dans le filtre personnel de la page Utilisateurs."""
    staff_roles = [r for r in USER_MANAGEABLE_ROLES if r not in BADGE_ACCOUNT_ROLES]
    if role in USER_MUTATION_ROLES:
        manageable = get_manageable_roles(role)
        return [r for r in staff_roles if r in manageable]
    if role in USERS_PAGE_ROLES:
        return staff_roles
    return []


def user_role_context(user):
    """Métadonnées rôles pour le frontend (login / auth/me)."""
    role = getattr(user, 'role', None)
    return {
        'hierarchy': ROLE_HIERARCHY,
        'labels': ROLE_LABELS,
        'creatable_roles': get_creatable_roles(role),
        'manageable_roles': get_manageable_roles(role),
        'staff_filter_roles': get_staff_filter_roles(role),
        'badge_account_roles': list(BADGE_ACCOUNT_ROLES),
        'can_mutate_users': role in USER_MUTATION_ROLES,
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
        logger.warning(
            'sync_user_role_group_skipped user_id=%s username=%s reason=unknown_role role=%s',
            user.pk,
            getattr(user, 'username', None),
            user.role,
        )
        return

    current_role_groups = user.groups.filter(name__in=role_group_names)
    user.groups.remove(*current_role_groups)

    target_group = Group.objects.filter(name=target_group_name).first()
    if target_group:
        user.groups.add(target_group)
    else:
        logger.error(
            'sync_user_role_group_failed user_id=%s username=%s role=%s missing_group=%s',
            user.pk,
            getattr(user, 'username', None),
            user.role,
            target_group_name,
        )


def sync_user_staff_status(user):
    """Active is_staff pour les rôles autorisés sur l'admin Django."""
    if not user or not user.pk or user.is_superuser:
        return

    should_be_staff = user.role in DUAL_ACCESS_ROLES
    if user.is_staff != should_be_staff:
        User.objects.filter(pk=user.pk).update(is_staff=should_be_staff)
        user.is_staff = should_be_staff


def sync_all_users_role_groups():
    for user in User.objects.all().only("id", "role", "is_staff", "is_superuser"):
        sync_user_role_group(user)
        sync_user_staff_status(user)
