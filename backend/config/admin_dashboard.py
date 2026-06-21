"""Contexte enrichi pour la page d'accueil admin (style dashboard Finexy)."""

from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def admin_dashboard_callback(request, context):
    from formations.models import Formation, Module, Participant
    from presences.models import Pointage

    user = request.user
    first_name = (user.first_name or user.get_username()).split('@')[0]

    hour = timezone.localtime().hour
    if hour < 12:
        greeting = _('Bonjour')
    elif hour < 18:
        greeting = _('Bon après-midi')
    else:
        greeting = _('Bonsoir')

    stats = [
        {
            'label': _('Formations'),
            'value': Formation.objects.count(),
            'icon': 'school',
            'link': 'admin:formations_formation_changelist',
            'highlight': True,
        },
        {
            'label': _('Modules'),
            'value': Module.objects.count(),
            'icon': 'menu_book',
            'link': 'admin:formations_module_changelist',
        },
        {
            'label': _('Auditeurs'),
            'value': Participant.objects.count(),
            'icon': 'groups',
            'link': 'admin:formations_participant_changelist',
        },
        {
            'label': _('Pointages'),
            'value': Pointage.objects.count(),
            'icon': 'fingerprint',
            'link': 'admin:presences_pointage_changelist',
        },
    ]

    context['admin_greeting'] = greeting
    context['admin_user_name'] = first_name
    context['admin_stats'] = stats
    return context
