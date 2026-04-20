from django import template

register = template.Library()

ROLE_DFRC = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN']
ROLE_SECRETARIAT = ['CHEF_SECRETARIAT', 'SECRETARIAT']
ROLE_ENCADRANT = ['ENCADRANT']
ROLE_ADMIN_MUTATION = ROLE_DFRC + ROLE_SECRETARIAT


@register.filter
def can_create_formation(user):
    """Vérifie si l'utilisateur peut créer une formation."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_edit_formation(user):
    """Vérifie si l'utilisateur peut modifier/supprimer une formation."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_manage_sessions(user):
    """Vérifie si l'utilisateur peut gérer les sessions (démarrer, terminer, supprimer)."""
    return user.role in ROLE_ADMIN_MUTATION + ROLE_ENCADRANT


@register.filter
def can_generate_qr(user):
    """Vérifie si l'utilisateur peut générer des QR codes."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_force_pointage(user):
    """Vérifie si l'utilisateur peut forcer un pointage."""
    return user.role in ROLE_ADMIN_MUTATION + ROLE_ENCADRANT


@register.filter
def can_assign_superviseur(user):
    """Vérifie si l'utilisateur peut assigner un superviseur."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_assign_formateur(user):
    """Vérifie si l'utilisateur peut assigner un formateur."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_remove_formateur(user):
    """Vérifie si l'utilisateur peut retirer un formateur d'une formation."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_inscrire_participant(user):
    """Vérifie si l'utilisateur peut inscribire un participant."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_remove_participant(user):
    """Vérifie si l'utilisateur peut retirer un participant d'une formation."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_manage_formation_statut(user):
    """Vérifie si l'utilisateur peut changer le statut d'une formation."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_manage_participants(user):
    """Vérifie si l'utilisateur peut gérer les participants (CRUD)."""
    return user.role in ROLE_ADMIN_MUTATION + ['DIRECTION']


@register.filter
def can_manage_formateurs(user):
    """Vérifie si l'utilisateur peut gérer les formateurs (CRUD)."""
    return user.role in ROLE_ADMIN_MUTATION + ['DIRECTION']


@register.filter
def can_manage_users(user):
    """Vérifie si l'utilisateur peut gérer les utilisateurs (CRUD)."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_import_excel(user):
    """Vérifie si l'utilisateur peut importer des données Excel."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def can_view_nav_participants(user):
    """Vérifie si l'utilisateur peut voir la navigation Participants."""
    return user.role in ROLE_ADMIN_MUTATION + ['DIRECTION']


@register.filter
def can_view_nav_formateurs(user):
    """Vérifie si l'utilisateur peut voir la navigation Formateurs."""
    return user.role in ROLE_ADMIN_MUTATION + ['DIRECTION']


@register.filter
def can_view_nav_users(user):
    """Vérifie si l'utilisateur peut voir la navigation Utilisateurs."""
    return user.role in ROLE_ADMIN_MUTATION + ['DIRECTION']


@register.filter
def can_view_nav_import(user):
    """Vérifie si l'utilisateur peut voir la navigation Import Excel."""
    return user.role in ROLE_ADMIN_MUTATION


@register.filter
def get_item(dictionary, key):
    """Access a dictionary item by key in templates."""
    if dictionary is None:
        return None
    return dictionary.get(key)
