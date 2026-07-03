"""Règles métier pour l'assignation des formateurs aux modules."""
from __future__ import annotations

import re
from datetime import timedelta, time

from .models import Module, ModuleFormateur, SessionModule


def normalize_groupe(value) -> str:
    """Normalise les variantes de groupe (1, 01, GROUPE 1) vers GROUPE N."""
    raw = str(value or '').strip()
    if not raw:
        return ''
    compact = re.sub(r'\s+', ' ', raw).strip()
    match = re.fullmatch(r'(?:GROUPE\s*)?0*(\d+)', compact, flags=re.IGNORECASE)
    if match:
        return f'GROUPE {int(match.group(1))}'
    return compact.upper()


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


def _format_time(value: time | None) -> str:
    return value.strftime('%H:%M') if value else '?'


def _sessions_overlap_in_time(a: SessionModule, b: SessionModule) -> bool:
    """True si deux séances ont des plages horaires qui se chevauchent."""
    if not all([
        a.heure_debut_prevue, a.heure_fin_prevue,
        b.heure_debut_prevue, b.heure_fin_prevue,
    ]):
        return False
    return a.heure_debut_prevue < b.heure_fin_prevue and b.heure_debut_prevue < a.heure_fin_prevue


def _sessions_for_module_on_date(module: Module, day) -> list[SessionModule]:
    return list(
        SessionModule.objects.filter(module=module, date_journee=day).order_by('numero')
    )


def check_formateur_groupe_jour_conflict(formateur, target_module: Module) -> str | None:
    """
    Vérifie qu'un formateur peut être assigné à un module :
    - pas deux groupes différents le même jour ;
    - pas deux cours le même jour dans le même groupe si les séances se chevauchent.

    Retourne un message d'erreur lisible, ou None si l'assignation est autorisée.
    """
    target_dates = _module_session_dates(target_module)
    if not target_dates:
        return None

    target_groupe = normalize_groupe(target_module.groupe)
    formateur_label = str(formateur)
    target_module_label = target_module.intitule or f'Module #{target_module.pk}'

    assigned_modules = (
        Module.objects.filter(module_formateurs__formateur=formateur)
        .exclude(pk=target_module.pk)
        .distinct()
    )

    for other in assigned_modules:
        other_groupe = normalize_groupe(other.groupe)
        other_dates = _module_session_dates(other)
        common_dates = sorted(target_dates & other_dates)
        if not common_dates:
            continue

        other_module_label = other.intitule or f'Module #{other.pk}'

        # Règle 1 : groupes différents le même jour
        if target_groupe and other_groupe and other_groupe != target_groupe:
            conflict_date = common_dates[0]
            session = (
                SessionModule.objects.filter(module=other, date_journee=conflict_date)
                .order_by('numero')
                .first()
            )
            date_label = conflict_date.strftime('%d/%m/%Y')
            if session:
                seance_label = _session_label(session)
                return (
                    f'Impossible d\'assigner {formateur_label} au module « {target_module_label} » '
                    f'({target_groupe}) : il est déjà assigné au cours « {other_module_label} » '
                    f'({other_groupe}) le {date_label} ({seance_label}). '
                    f'Un formateur ne peut pas enseigner deux groupes différents le même jour.'
                )
            return (
                f'Impossible d\'assigner {formateur_label} au module « {target_module_label} » '
                f'({target_groupe}) : il est déjà assigné au module « {other_module_label} » '
                f'({other_groupe}) le {date_label}. '
                f'Un formateur ne peut pas enseigner deux groupes différents le même jour.'
            )

        # Règle 2 : même groupe, conflit horaire le même jour
        if target_groupe and other_groupe and other_groupe == target_groupe:
            for conflict_date in common_dates:
                target_sessions = _sessions_for_module_on_date(target_module, conflict_date)
                other_sessions = _sessions_for_module_on_date(other, conflict_date)
                for target_session in target_sessions:
                    for other_session in other_sessions:
                        if not _sessions_overlap_in_time(target_session, other_session):
                            continue
                        date_label = conflict_date.strftime('%d/%m/%Y')
                        return (
                            f'Impossible d\'assigner {formateur_label} au module « {target_module_label} » '
                            f'({target_groupe}) : conflit horaire le {date_label} avec le cours '
                            f'« {other_module_label} » ({_session_label(other_session)}, '
                            f'{_format_time(other_session.heure_debut_prevue)}–'
                            f'{_format_time(other_session.heure_fin_prevue)}) '
                            f'et la séance « {_session_label(target_session)} » '
                            f'({_format_time(target_session.heure_debut_prevue)}–'
                            f'{_format_time(target_session.heure_fin_prevue)}).'
                        )

    return None
