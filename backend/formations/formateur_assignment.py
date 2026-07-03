"""Règles métier pour l'assignation des formateurs aux modules."""
from __future__ import annotations

from datetime import timedelta

from .models import Module, SessionModule


def _module_session_dates(module: Module) -> set:
    dates = set(
        SessionModule.objects.filter(module=module).values_list('date_journee', flat=True)
    )
    if dates:
        return dates
    if module.date_debut and module.date_fin:
        start = module.date_debut
        end = module.date_fin
        if end < start:
            start, end = end, start
        cursor = start
        out = set()
        while cursor <= end:
            out.add(cursor)
            cursor += timedelta(days=1)
        return out
    if module.date_debut:
        return {module.date_debut}
    return set()


def _session_label(session: SessionModule) -> str:
    return session.intitule or f'Séance {session.numero}'


def check_formateur_groupe_jour_conflict(formateur, target_module: Module) -> str | None:
    """
    Vérifie qu'un formateur peut être assigné à un module :
    refuse si déjà assigné à un autre module ayant une activité le même jour.

    Retourne un message d'erreur lisible, ou None si l'assignation est autorisée.
    """
    target_dates = _module_session_dates(target_module)
    if not target_dates:
        return None

    formateur_label = str(formateur)
    target_module_label = target_module.intitule or f'Module #{target_module.pk}'

    assigned_modules = (
        Module.objects.filter(module_formateurs__formateur=formateur)
        .exclude(pk=target_module.pk)
        .distinct()
    )

    for other in assigned_modules:
        other_dates = _module_session_dates(other)
        common_dates = sorted(target_dates & other_dates)
        if not common_dates:
            continue

        conflict_date = common_dates[0]
        other_module_label = other.intitule or f'Module #{other.pk}'
        date_label = conflict_date.strftime('%d/%m/%Y')
        session = (
            SessionModule.objects.filter(module=other, date_journee=conflict_date)
            .order_by('numero')
            .first()
        )
        if session:
            seance_label = _session_label(session)
            return (
                f'Impossible d\'assigner {formateur_label} au module « {target_module_label} » : '
                f'il est déjà assigné au cours « {other_module_label} » le {date_label} '
                f'({seance_label}). Un formateur ne peut pas enseigner deux cours le même jour.'
            )
        return (
            f'Impossible d\'assigner {formateur_label} au module « {target_module_label} » : '
            f'il est déjà assigné au module « {other_module_label} » le {date_label}. '
            f'Un formateur ne peut pas enseigner deux cours le même jour.'
        )

    return None
