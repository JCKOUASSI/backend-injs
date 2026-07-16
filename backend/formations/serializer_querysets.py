"""Querysets annotés pour éviter les N+1 dans les serializers."""
from django.db.models import Count, Prefetch, Q

from .models import Module, Secretariat, SessionModule


def annotate_sessions_for_serializer(qs):
    return qs.select_related('module', 'module__formateur').annotate(
        _nb_presences_part=Count(
            'pointages__participant',
            filter=Q(pointages__participant_id__isnull=False),
            distinct=True,
        ),
        _nb_presences_fmt=Count(
            'pointages__formateur',
            filter=Q(pointages__formateur_id__isnull=False),
            distinct=True,
        ),
        _nb_attendus_part=Count('module__module_participants__participant', distinct=True),
        _nb_attendus_fmt=Count('module__module_formateurs__formateur', distinct=True),
    )


def annotate_modules_for_serializer(qs):
    session_qs = annotate_sessions_for_serializer(
        SessionModule.objects.order_by('date_journee', 'numero')
    )
    return qs.select_related(
        'formation', 'secretariat', 'secretariat__type', 'formateur', 'site',
    ).annotate(
        _nb_participants=Count('module_participants', distinct=True),
    ).prefetch_related(
        Prefetch('sessions', queryset=session_qs),
    )


def secretariat_queryset_for_serializer():
    return Secretariat.objects.select_related(
        'responsable', 'type',
    ).annotate(
        _nb_participants=Count('participants', distinct=True),
        _nb_modules=Count('modules_secretariat', distinct=True),
        _nb_formations=Count('modules_secretariat__formation', distinct=True),
    ).prefetch_related('membres').order_by('nom')
