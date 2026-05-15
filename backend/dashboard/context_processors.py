from formations.models import Formation, Participant, Formateur
from django.contrib.auth import get_user_model

User = get_user_model()

ALLOWED_WEB_ROLES = (
    'DIRECTION',
    'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN',
    'CHEF_SECRETARIAT', 'SECRETARIAT',
    'FINANCE',
    'ENCADRANT',
)


def sidebar_counts(request):
    """Inject sidebar badge counts for authenticated staff users."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}
    if request.user.role not in ALLOWED_WEB_ROLES:
        return {}

    if request.user.role == 'ENCADRANT':
        nb_formations = Formation.objects.filter(superviseur=request.user).count()
    else:
        nb_formations = Formation.objects.count()

    counts = {'sidebar_formations_count': nb_formations}

    if request.user.role in ('CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'DIRECTION'):
        counts['sidebar_participants_count'] = Participant.objects.count()
        counts['sidebar_formateurs_count'] = Formateur.objects.count()
        counts['sidebar_users_count'] = User.objects.count()

    return counts
