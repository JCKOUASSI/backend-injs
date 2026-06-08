"""
Forçage en masse des entrées (auditeurs, formateurs, encadrants) — 80–95 % aléatoire par séance.
Utilisé par l'API et les commandes manage.py force_badgeage_*.
"""
import random
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from formations.models import Module, ModuleParticipant, ModuleFormateur, SessionModule
from .models import Pointage, AuditLog, _log_audit

TAUX_MIN_DEFAULT = 0.80
TAUX_MAX_DEFAULT = 0.95


def _views():
    from . import views
    return views


class _ActeurRequest:
    """Porte l'utilisateur pour _log_audit hors requête HTTP."""

    META = {}

    def __init__(self, user):
        self.user = user


def _close_open_pointages_same_module_day(personne, type_personne, module, date_journee, exclude_session_id=None):
    """Clôture les pointages ouverts sur le module/jour (mode test sans contraintes)."""
    filt = {
        'session__module': module,
        'date_journee': date_journee,
        'timestamp_sortie__isnull': True,
    }
    if type_personne == 'formateur':
        filt['formateur'] = personne
    elif type_personne == 'encadrant':
        filt['encadrant'] = personne
    else:
        filt['participant'] = personne
    qs = Pointage.objects.filter(**filt)
    if exclude_session_id is not None:
        qs = qs.exclude(session_id=exclude_session_id)
    now = timezone.now()
    for pt in qs:
        pt.timestamp_sortie = now
        pt.statut = Pointage.Statut.FORCE_DFRC
        pt.calculer_duree()
        pt.save(update_fields=['timestamp_sortie', 'statut', 'duree_presence_minutes', 'updated_at'])


def absent_auditeurs_for_seance(seance, *, ignore_constraints=False):
    """Auditeurs inscrits sans entrée sur cette séance."""
    inscrits = ModuleParticipant.objects.filter(module=seance.module).select_related('participant')
    present_ids = set(
        Pointage.objects.filter(
            session=seance,
            participant__isnull=False,
        ).values_list('participant_id', flat=True)
    )
    absents = []
    for mp in inscrits:
        p = mp.participant
        if p.id in present_ids:
            continue
        if not ignore_constraints and _views()._find_open_pointage_same_module_day(
            p, 'participant', seance.module, seance.date_journee, exclude_session_id=seance.id,
        ):
            continue
        absents.append(p)
    return absents


def force_entree_auditeur(
    formation,
    seance,
    participant,
    date_journee,
    motif,
    *,
    request=None,
    timestamp_entree=None,
    ignore_constraints=False,
):
    """Crée une entrée forcée auditeur (alias)."""
    return force_entree_personne(
        formation, seance, participant, 'participant', date_journee, motif,
        request=request, timestamp_entree=timestamp_entree, ignore_constraints=ignore_constraints,
    )


def force_entree_personne(
    formation,
    seance,
    personne,
    type_personne,
    date_journee,
    motif,
    *,
    request=None,
    timestamp_entree=None,
    ignore_constraints=False,
):
    """Entrée forcée pour auditeur, formateur ou encadrant."""
    v = _views()
    if not ignore_constraints:
        if v._has_unfinished_previous_session(seance):
            return None, 'Séance précédente du même jour non terminée.'
        if v._find_open_pointage_same_module_day(
            personne, type_personne, seance.module, date_journee, exclude_session_id=seance.id,
        ):
            return None, 'Une session est déjà en cours sur ce module pour ce jour.'
    else:
        _close_open_pointages_same_module_day(
            personne, type_personne, seance.module, date_journee, exclude_session_id=seance.id,
        )

    ts_entree_raw = timestamp_entree or timezone.now()
    timestamp_entree_val = v._clamp_to_seance(ts_entree_raw, seance)
    pointage = Pointage.objects.create(
        **v._create_pointage_kwargs(
            personne, type_personne, seance,
            date_journee=date_journee,
            timestamp_entree=timestamp_entree_val,
            statut=Pointage.Statut.FORCE_DFRC,
            device_id='FORCE_DFRC',
        )
    )
    numero = (
        getattr(personne, 'matricule', None)
        or getattr(personne, 'numerobadge', None)
        or getattr(personne, 'username', '')
        or ''
    )
    nom = (
        f"{getattr(personne, 'nom', '')} {getattr(personne, 'prenom', '')}".strip()
        or f"{getattr(personne, 'last_name', '')} {getattr(personne, 'first_name', '')}".strip()
        or getattr(personne, 'username', '—')
    )
    _log_audit(
        action=AuditLog.Action.FORCE_ENTREE,
        request=request,
        cible_type=type_personne,
        cible_numero=numero,
        cible_nom=nom,
        formation=formation,
        pointage=pointage,
        extra={
            'acteur_role': getattr(getattr(request, 'user', None), 'role', 'SYSTEM'),
            'motif': motif,
            'bulk_force_presences': True,
            'ignore_constraints': ignore_constraints,
        },
    )
    return pointage, None


def attendus_formateurs_module(module):
    """Formateurs attendus sur le module (principal + assignés, sans doublon)."""
    seen = set()
    out = []
    if module.formateur_id and module.formateur_id not in seen:
        seen.add(module.formateur_id)
        if module.formateur:
            out.append(module.formateur)
    for mf in ModuleFormateur.objects.filter(module=module).select_related('formateur'):
        if mf.formateur_id not in seen:
            seen.add(mf.formateur_id)
            out.append(mf.formateur)
    return out


def attendus_encadrants_module(module):
    if module.superviseur_id and module.superviseur:
        return [module.superviseur]
    return []


def _present_ids_on_seance(seance, type_personne):
    filt = {'session': seance, 'timestamp_entree__isnull': False}
    if type_personne == 'formateur':
        filt['formateur__isnull'] = False
        key = 'formateur_id'
    elif type_personne == 'encadrant':
        filt['encadrant__isnull'] = False
        key = 'encadrant_id'
    else:
        filt['participant__isnull'] = False
        key = 'participant_id'
    return set(Pointage.objects.filter(**filt).values_list(key, flat=True))


def absents_formateurs_for_seance(seance, *, ignore_constraints=False):
    present = _present_ids_on_seance(seance, 'formateur')
    absents = []
    for f in attendus_formateurs_module(seance.module):
        if f.id in present:
            continue
        if not ignore_constraints and _views()._find_open_pointage_same_module_day(
            f, 'formateur', seance.module, seance.date_journee, exclude_session_id=seance.id,
        ):
            continue
        absents.append(f)
    return absents


def absents_encadrants_for_seance(seance, *, ignore_constraints=False):
    present = _present_ids_on_seance(seance, 'encadrant')
    absents = []
    for enc in attendus_encadrants_module(seance.module):
        if enc.id in present:
            continue
        if not ignore_constraints and _views()._find_open_pointage_same_module_day(
            enc, 'encadrant', seance.module, seance.date_journee, exclude_session_id=seance.id,
        ):
            continue
        absents.append(enc)
    return absents


def _sample_absents(absents, taux_min=TAUX_MIN_DEFAULT, taux_max=TAUX_MAX_DEFAULT):
    if not absents:
        return []
    taux = random.uniform(taux_min, taux_max)
    n = max(1, round(len(absents) * taux))
    n = min(n, len(absents))
    return random.sample(absents, n)


def run_bulk_force_seance(
    formation,
    seance,
    *,
    motif,
    request=None,
    ignore_constraints=False,
    taux_min=TAUX_MIN_DEFAULT,
    taux_max=TAUX_MAX_DEFAULT,
    types=('participant', 'formateur', 'encadrant'),
):
    """Force 80–95 % des absents par type sur une séance. Retourne compteurs par type."""
    seance_date = seance.date_journee
    _prepare_seance_for_force(seance, ignore_constraints=ignore_constraints)

    if not ignore_constraints and _views()._has_unfinished_previous_session(seance):
        return {'skipped': True, 'detail': 'Séance précédente non terminée.', 'auditeurs': 0, 'formateurs': 0, 'encadrants': 0}

    counts = {'auditeurs': 0, 'formateurs': 0, 'encadrants': 0, 'erreurs': []}
    pools = []
    if 'participant' in types:
        pools.append(('participant', 'auditeurs', absent_auditeurs_for_seance, lambda p: p))
    if 'formateur' in types:
        pools.append(('formateur', 'formateurs', absents_formateurs_for_seance, lambda p: p))
    if 'encadrant' in types:
        pools.append(('encadrant', 'encadrants', absents_encadrants_for_seance, lambda p: p))

    base_ts = timezone.now()
    offset = 0
    for type_str, key, absent_fn, identity in pools:
        absents = absent_fn(seance, ignore_constraints=ignore_constraints)
        for person in _sample_absents(absents, taux_min, taux_max):
            ts = base_ts + timedelta(seconds=offset)
            offset += 3
            _, err = force_entree_personne(
                formation, seance, person, type_str, seance_date, motif,
                request=request, timestamp_entree=ts, ignore_constraints=ignore_constraints,
            )
            if err:
                counts['erreurs'].append({'type': type_str, 'detail': err})
            else:
                counts[key] += 1

    counts['skipped'] = False
    return counts


def _prepare_seance_for_force(seance, *, ignore_constraints=False):
    """Démarre la séance si besoin (mode test)."""
    if not ignore_constraints:
        return
    updates = []
    if not seance.demarree_le:
        seance.demarree_le = timezone.now()
        updates.append('demarree_le')
    if seance.terminee_le:
        seance.terminee_le = None
        updates.append('terminee_le')
    if updates:
        seance.save(update_fields=updates)


def resolve_seances(module, *, date_journee=None, session_id=None, all_sessions=False, ignore_constraints=False):
    """Liste des séances à traiter selon les filtres."""
    if session_id:
        qs = SessionModule.objects.filter(pk=session_id, module=module)
        if date_journee:
            qs = qs.filter(date_journee=date_journee)
        return list(qs.order_by('numero'))

    qs = SessionModule.objects.filter(module=module)
    if date_journee:
        qs = qs.filter(date_journee=date_journee)
    if all_sessions or ignore_constraints:
        return list(qs.order_by('date_journee', 'numero'))

    return list(
        qs.filter(
            demarree_le__isnull=False,
            terminee_le__isnull=True,
        ).order_by('date_journee', 'numero')
    )


def run_bulk_force_badgeage_auditeurs(
    formation,
    module,
    *,
    motif,
    request=None,
    date_journee=None,
    session_id=None,
    all_sessions=False,
    ignore_constraints=False,
):
    """
    Exécute le forçage 80–95 % par séance.
    Retourne (result_dict, http_status_hint) où status_hint est 201 ou 400.
    """
    # Filtre séances : date explicite, sinon toutes les dates si all_sessions / test
    filter_date = date_journee
    if filter_date is None and not (all_sessions or ignore_constraints):
        filter_date = timezone.localdate()

    seances = resolve_seances(
        module,
        date_journee=filter_date,
        session_id=session_id,
        all_sessions=all_sessions,
        ignore_constraints=ignore_constraints,
    )

    if not seances:
        return {
            'detail': 'Aucune séance à traiter.',
            'sessions': [],
            'total_badges': 0,
        }, 400

    sessions_result = []
    totals = {'auditeurs': 0, 'formateurs': 0, 'encadrants': 0}

    with transaction.atomic():
        for seance in seances:
            seance_date = seance.date_journee or date_journee
            counts = run_bulk_force_seance(
                formation,
                seance,
                motif=motif,
                request=request,
                ignore_constraints=ignore_constraints,
                types=('participant',),
            )
            if counts.get('skipped'):
                sessions_result.append({
                    'session_id': seance.id,
                    'session_intitule': seance.intitule or f'Séance {seance.numero}',
                    'session_date': str(seance_date),
                    'nb_badges': 0,
                    'skipped': True,
                    'detail': counts.get('detail', ''),
                })
                continue

            nb_ok = counts['auditeurs']
            totals['auditeurs'] += nb_ok
            sessions_result.append({
                'session_id': seance.id,
                'session_intitule': seance.intitule or f'Séance {seance.numero}',
                'session_date': str(seance_date),
                'nb_badges': nb_ok,
                'auditeurs': nb_ok,
                'skipped': False,
            })

    total_badges = totals['auditeurs']
    if total_badges == 0 and all(
        s.get('skipped') or s.get('nb_badges', 0) == 0 for s in sessions_result
    ):
        return {
            'detail': 'Aucun badgeage forcé (séances non éligibles ou aucun absent).',
            'sessions': sessions_result,
            'total_badges': 0,
            'totals': totals,
        }, 400

    return {
        'detail': f'{total_badges} entrée(s) auditeur(s) forcée(s) sur {len(sessions_result)} séance(s).',
        'sessions': sessions_result,
        'total_badges': total_badges,
        'totals': totals,
        'ignore_constraints': ignore_constraints,
    }, 201


def run_bulk_force_application(
    *,
    motif,
    request=None,
    ignore_constraints=True,
    module_ids=None,
    taux_min=TAUX_MIN_DEFAULT,
    taux_max=TAUX_MAX_DEFAULT,
):
    """
    Forçage 80–95 % sur toutes les séances de l'application
    (auditeurs + formateurs + encadrants attendus par séance).
    """
    seances_qs = SessionModule.objects.select_related(
        'module', 'module__formation', 'module__formateur', 'module__superviseur',
    ).order_by('module__formation_id', 'date_journee', 'numero')
    if module_ids:
        seances_qs = seances_qs.filter(module_id__in=module_ids)

    totals = defaultdict(int)
    sessions_result = []
    seance_count = 0

    with transaction.atomic():
        for seance in seances_qs.iterator(chunk_size=200):
            formation = seance.module.formation
            counts = run_bulk_force_seance(
                formation,
                seance,
                motif=motif,
                request=request,
                ignore_constraints=ignore_constraints,
                taux_min=taux_min,
                taux_max=taux_max,
            )
            seance_count += 1
            if counts.get('skipped'):
                continue
            for key in ('auditeurs', 'formateurs', 'encadrants'):
                totals[key] += counts.get(key, 0)
            if any(counts.get(k, 0) for k in ('auditeurs', 'formateurs', 'encadrants')):
                sessions_result.append({
                    'session_id': seance.id,
                    'module_id': seance.module_id,
                    'session_date': str(seance.date_journee),
                    'auditeurs': counts['auditeurs'],
                    'formateurs': counts['formateurs'],
                    'encadrants': counts['encadrants'],
                })

    total_badges = totals['auditeurs'] + totals['formateurs'] + totals['encadrants']
    return {
        'detail': (
            f'{total_badges} entrée(s) forcée(s) — '
            f'{totals["auditeurs"]} aud. · {totals["formateurs"]} form. · {totals["encadrants"]} enc. '
            f'sur {seance_count} séance(s).'
        ),
        'totals': dict(totals),
        'total_badges': total_badges,
        'nb_seances': seance_count,
        'sessions': sessions_result[:50],
        'ignore_constraints': ignore_constraints,
    }, 201 if total_badges else 400


def find_module_for_test(*, module_id=None, intitule_contains=None):
    """Recherche un module par id ou intitulé (icontains)."""
    if module_id:
        return Module.objects.select_related('formation').filter(pk=module_id).first()
    if intitule_contains:
        return (
            Module.objects.select_related('formation')
            .filter(intitule__icontains=intitule_contains)
            .order_by('-id')
            .first()
        )
    return None
