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


def _normalize_groupe(module: Module) -> str:
    return (module.groupe or '').strip()


def _sessions_overlap(a: SessionModule, b: SessionModule) -> bool:
    if (
        a.heure_debut_prevue
        and a.heure_fin_prevue
        and b.heure_debut_prevue
        and b.heure_fin_prevue
    ):
        return (
            a.heure_debut_prevue < b.heure_fin_prevue
            and b.heure_debut_prevue < a.heure_fin_prevue
        )
    return True


def check_formateur_groupe_jour_conflict(formateur, target_module: Module) -> str | None:
    """
    Vérifie qu'un formateur peut être assigné à un module :
    - deux groupes différents le même jour → refus ;
    - même groupe le même jour → refus seulement en cas de conflit horaire ;
    - groupe absent sur l'un des modules → refus dès qu'il y a une activité le même jour.

    Retourne un message d'erreur lisible, ou None si l'assignation est autorisée.
    """
    target_dates = _module_session_dates(target_module)
    if not target_dates:
        return None

    formateur_label = str(formateur)
    target_module_label = target_module.intitule or f'Module #{target_module.pk}'
    target_groupe = _normalize_groupe(target_module)

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

        other_groupe = _normalize_groupe(other)
        other_module_label = other.intitule or f'Module #{other.pk}'

        for conflict_date in common_dates:
            date_label = conflict_date.strftime('%d/%m/%Y')

            if target_groupe and other_groupe and target_groupe != other_groupe:
                return (
                    f'Impossible d\'assigner {formateur_label} au module '
                    f'« {target_module_label} » : conflit le {date_label} entre le groupe '
                    f'{other_groupe} ({other_module_label}) et le groupe {target_groupe} '
                    f'({target_module_label}). Un formateur ne peut pas enseigner '
                    f'deux groupes différents le même jour.'
                )

            if not target_groupe or not other_groupe:
                return (
                    f'Impossible d\'assigner {formateur_label} au module '
                    f'« {target_module_label} » : il est déjà assigné au cours '
                    f'« {other_module_label} » le {date_label}. '
                    f'Un formateur ne peut pas enseigner deux cours le même jour.'
                )

            target_sessions = SessionModule.objects.filter(
                module=target_module,
                date_journee=conflict_date,
            )
            other_sessions = SessionModule.objects.filter(
                module=other,
                date_journee=conflict_date,
            )
            for target_session in target_sessions:
                for other_session in other_sessions:
                    if _sessions_overlap(target_session, other_session):
                        return (
                            f'Impossible d\'assigner {formateur_label} au module '
                            f'« {target_module_label} » : conflit horaire le {date_label} '
                            f'avec le cours « {other_module_label} » (groupe {other_groupe}).'
                        )

    return None
