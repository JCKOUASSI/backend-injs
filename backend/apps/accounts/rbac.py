"""Permissions métier INJS basées sur django.contrib.auth."""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

MODULES = [
    'accounts', 'students', 'faculty', 'academics', 'exams',
    'finance', 'admissions', 'documents', 'messaging', 'library', 'reports', 'notifications',
]

ACTIONS = [
    'view', 'create', 'update', 'delete',
    'export_pdf', 'export_excel', 'export_word', 'approve',
]

MODULE_LABELS = {
    'accounts': 'Comptes',
    'students': 'Étudiants',
    'faculty': 'Enseignants',
    'academics': 'Académique',
    'exams': 'Examens',
    'finance': 'Finance',
    'admissions': 'Admissions',
    'documents': 'Documents',
    'messaging': 'Messagerie',
    'library': 'Bibliothèque',
    'reports': 'Rapports',
    'notifications': 'Notifications',
}

ACTION_LABELS = {
    'view': 'Visualisation',
    'create': 'Création',
    'update': 'Modification',
    'delete': 'Suppression',
    'export_pdf': 'Export PDF',
    'export_excel': 'Export Excel',
    'export_word': 'Export Word',
    'approve': 'Validation',
}

GROUP_LEVELS = [
    (0, 'Niveau 0 - Super Admin'),
    (1, 'Niveau 1 - Direction'),
    (2, 'Niveau 2 - Responsables'),
    (3, 'Niveau 3 - Pédagogique'),
    (4, 'Niveau 4 - Étudiant'),
]


def make_codename(module: str, action: str) -> str:
    return f'{module}_{action}'


def make_perm(module: str, action: str) -> str:
    return f'accounts.{make_codename(module, action)}'


def parse_codename(codename: str) -> tuple[str | None, str | None]:
    for module in MODULES:
        prefix = f'{module}_'
        if codename.startswith(prefix):
            action = codename[len(prefix):]
            if action in ACTIONS:
                return module, action
    return None, None


def to_display_codename(codename: str) -> str:
    module, action = parse_codename(codename)
    if module and action:
        return f'{module}.{action}'
    return codename


def sync_module_permissions() -> int:
    """Crée ou met à jour les permissions Django module_action."""
    from apps.accounts.models import ModulePermissionRegistry

    ct = ContentType.objects.get_for_model(ModulePermissionRegistry)
    created = 0
    for module in MODULES:
        for action in ACTIONS:
            codename = make_codename(module, action)
            label = f'{MODULE_LABELS[module]} — {ACTION_LABELS[action]}'
            _, was_created = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={'name': label},
            )
            if was_created:
                created += 1
    return created


def module_permissions_queryset():
    return Permission.objects.filter(
        content_type__app_label='accounts',
        content_type__model='modulepermissionregistry',
    )
