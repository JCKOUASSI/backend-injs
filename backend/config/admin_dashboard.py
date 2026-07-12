"""Contexte enrichi pour la page d'accueil admin (style dashboard)."""

from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from config.admin_charts import build_donut, build_histogram, build_stacked_bars

_MOIS_FR = (
    'jan.', 'fév.', 'mars', 'avr.', 'mai', 'juin',
    'juil.', 'août', 'sep.', 'oct.', 'nov.', 'déc.',
)

_STATUT_COLORS = {
    'EN_COURS': '#16a34a',
    'TERMINE': '#15803d',
    'FORCE_DFRC': '#22c55e',
    'ABSENT_NON_BADGE': '#ea580c',
    'HORS_LIGNE_SUSPECT': '#dc2626',
    'SORTIE_AUTO': '#f97316',
}


def _mois_label(cle_mois):
    year, month = map(int, cle_mois.split('-'))
    return f'{_MOIS_FR[month - 1]} {year}'


def _build_admin_charts():
    from presences.models import Pointage
    from statistiques.views import _historique_mensuel

    historique = _historique_mensuel(mois=6)

    pointages_mensuels = build_histogram([
        {
            'label': _mois_label(item['mois']),
            'value': item['total'],
        }
        for item in historique['pointages_par_mois']
    ], color='#15803d')

    taux_presence = build_stacked_bars([
        {
            'label': _mois_label(item['mois']),
            'presents': item['presents'],
            'absents': item['absents'],
            'display': f"{item['total']:.1f}".replace('.', ',') + '%',
            'detail': _('{p} présents / {a} absents').format(
                p=item['presents'],
                a=item['absents'],
            ),
        }
        for item in historique['taux_presence_par_mois']
    ])

    sessions_mensuelles = build_histogram([
        {
            'label': _mois_label(item['mois']),
            'value': item['total'],
        }
        for item in historique['sessions_par_mois']
    ], color='#0369a1')

    statut_labels = dict(Pointage.Statut.choices)
    statut_rows = list(
        Pointage.objects.values('statut')
        .annotate(value=Count('id'))
        .order_by('-value')
    )
    pointages_par_statut = build_donut([
        {
            'label': statut_labels.get(row['statut'], row['statut']),
            'value': row['value'],
            'color': _STATUT_COLORS.get(row['statut'], '#64748b'),
        }
        for row in statut_rows
        if row['value']
    ])

    return {
        'pointages_mensuels': pointages_mensuels,
        'taux_presence': taux_presence,
        'sessions_mensuelles': sessions_mensuelles,
        'pointages_par_statut': pointages_par_statut,
    }


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
    context['admin_charts'] = _build_admin_charts()
    return context
