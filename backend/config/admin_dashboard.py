"""Contexte enrichi pour la page d'accueil admin (style dashboard)."""

from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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


def _bar_rows(items, *, value_key='value', max_value=None):
    values = [item[value_key] for item in items]
    peak = max_value or (max(values) if values else 0) or 1
    rows = []
    for item in items:
        value = item[value_key]
        pct = round(value / peak * 100, 1) if peak else 0
        rows.append({
            **item,
            'pct': pct,
            'pct_width': f'{pct:.1f}',
        })
    return rows


def _build_admin_charts():
    from presences.models import Pointage
    from statistiques.views import _historique_mensuel

    historique = _historique_mensuel(mois=6)

    pointages_mensuels = _bar_rows([
        {
            'label': _mois_label(item['mois']),
            'value': item['total'],
        }
        for item in historique['pointages_par_mois']
    ])

    taux_presence = _bar_rows([
        {
            'label': _mois_label(item['mois']),
            'value': round(item['total'], 1),
            'display': f"{item['total']:.1f}".replace('.', ','),
            'detail': _('{p} présents / {a} absents').format(
                p=item['presents'],
                a=item['absents'],
            ),
        }
        for item in historique['taux_presence_par_mois']
    ], max_value=100)

    sessions_mensuelles = _bar_rows([
        {
            'label': _mois_label(item['mois']),
            'value': item['total'],
        }
        for item in historique['sessions_par_mois']
    ])

    statut_labels = dict(Pointage.Statut.choices)
    statut_rows = list(
        Pointage.objects.values('statut')
        .annotate(value=Count('id'))
        .order_by('-value')
    )
    statut_peak = sum(row['value'] for row in statut_rows) or 1
    pointages_par_statut = [
        {
            'label': statut_labels.get(row['statut'], row['statut']),
            'value': row['value'],
            'pct': round(row['value'] / statut_peak * 100, 1),
            'pct_width': f"{round(row['value'] / statut_peak * 100, 1):.1f}",
            'color': _STATUT_COLORS.get(row['statut'], '#64748b'),
        }
        for row in statut_rows
    ]

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
