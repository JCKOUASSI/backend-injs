"""Résolution de ``Module.duree_prevue_heures`` lorsque la valeur est absente.

Ordre de priorité :
  1. Valeur déjà renseignée manuellement sur le module (> 0, non auto-remplie)
  2. ``RefModule.volume_horaire`` (lien direct ou recherche par intitulé)
  3. Volume EDT « type » : durée la plus fréquente des séances × nombre de séances
     (évite de figer une somme faussée par une séance aberrante)
"""

from collections import Counter
from decimal import Decimal

from .models import RefModule, SessionModule
from .volume_horaire import _session_prevu_minutes, accumulate_sessions_volume


def _ref_module_volume_hours(module):
    """Volume horaire du référentiel module, si disponible."""
    ref = None
    if getattr(module, 'ref_module_id', None) and getattr(module, 'ref_module', None):
        ref = module.ref_module
    if ref is None:
        intitule = RefModule.normalize_intitule(getattr(module, 'intitule', None))
        if intitule:
            ref = RefModule.objects.filter(intitule__iexact=intitule).first()
    if not ref:
        return 0.0
    heures = float(ref.volume_horaire or 0)
    return heures if heures > 0 else 0.0


def _session_durations_hours(module):
    sessions = SessionModule.objects.filter(module=module).only(
        'heure_debut_prevue', 'heure_fin_prevue', 'date_journee',
        'demarree_le', 'terminee_le',
    )
    durations = []
    for session in sessions:
        minutes = _session_prevu_minutes(session)
        if minutes > 0:
            durations.append(round(minutes / 60, 2))
    return durations


def module_edt_raw_hours(module):
    """Somme brute des créneaux planifiés (peut inclure des écarts ponctuels)."""
    sessions = SessionModule.objects.filter(module=module).only(
        'heure_debut_prevue', 'heure_fin_prevue', 'date_journee',
        'demarree_le', 'terminee_le',
    )
    prevu_min = accumulate_sessions_volume(sessions)['prevu_min']
    return round(prevu_min / 60, 2) if prevu_min > 0 else 0.0


def _typical_session_duration_hours(durations_hours):
    if not durations_hours:
        return 0.0
    counts = Counter(durations_hours)
    top_count = counts.most_common(1)[0][1]
    modes = [duration for duration, count in counts.items() if count == top_count]
    if len(modes) == 1:
        return modes[0]
    sorted_d = sorted(durations_hours)
    mid = len(sorted_d) // 2
    if len(sorted_d) % 2:
        return sorted_d[mid]
    return round((sorted_d[mid - 1] + sorted_d[mid]) / 2, 2)


def module_edt_typical_hours(module):
    """
    Volume contractuel estimé depuis l'EDT : durée type × nombre de séances.

    Ex. six séances de 5 h et une à 6 h → 6 × 5 h = 30 h (et non 31 h).
    """
    durations = _session_durations_hours(module)
    if not durations:
        return 0.0
    typical = _typical_session_duration_hours(durations)
    return round(typical * len(durations), 2)


def module_edt_planned_hours(module):
    """Alias conservé : volume type EDT (pas la somme brute)."""
    return module_edt_typical_hours(module)


def resolve_module_duree_prevue_heures(module, *, include_current=True):
    """
    Retourne ``(heures, source)`` avec source parmi
    ``ref_module``, ``module``, ``sessions_edt`` ou ``None``.

    Le référentiel ``RefModule.volume_horaire`` est prioritaire sur la fiche
    module (souvent remplie à tort par la somme brute de l'EDT à l'import).
    """
    ref_h = _ref_module_volume_hours(module)
    if ref_h > 0:
        return ref_h, 'ref_module'

    if include_current:
        current = float(module.duree_prevue_heures or 0)
        if current > 0:
            return current, 'module'

    edt_h = module_edt_typical_hours(module)
    if edt_h > 0:
        return edt_h, 'sessions_edt'

    return 0.0, None


def _should_overwrite_duree(current, raw_edt, canonical, ref_h):
    if canonical <= 0:
        return False
    if current <= 0:
        return True
    if ref_h > 0 and abs(current - ref_h) >= 0.01:
        return True
    # Corrige une fiche calée sur une somme EDT trop élevée (ex. 31 h ou 35 h au lieu de 30 h).
    if (
        raw_edt > 0
        and abs(current - raw_edt) < 0.01
        and canonical < raw_edt - 0.01
    ):
        return True
    return False


def ensure_module_duree_prevue(module, *, save=True):
    """
    Renseigne ou corrige ``duree_prevue_heures`` sur le module.

    Retourne ``(heures_effectives, source_utilisee)`` ;
    ``source_utilisee`` vaut ``None`` si la valeur en base est déjà correcte.
    """
    current = float(module.duree_prevue_heures or 0)
    raw_edt = module_edt_raw_hours(module)
    ref_h = _ref_module_volume_hours(module)
    canonical, source = resolve_module_duree_prevue_heures(module, include_current=False)

    if ref_h > 0:
        canonical, source = ref_h, 'ref_module'

    if not _should_overwrite_duree(current, raw_edt, canonical, ref_h):
        return current if current > 0 else 0.0, None

    if save and module.pk:
        module.duree_prevue_heures = Decimal(str(round(canonical, 2)))
        module.save(update_fields=['duree_prevue_heures'])

    return canonical, source
