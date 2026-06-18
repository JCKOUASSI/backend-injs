"""Reconstitution partielle depuis AuditLog (post-migration 0076, sans dump)."""

import re
from collections import defaultdict
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from formations.models import Formateur, Module, Participant, SessionModule
from presences.models import Pointage


def _parse_date(val):
    if not val:
        return None
    if hasattr(val, 'year'):
        return val
    try:
        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _groupe_sort_key(module):
    g = (module.groupe or '').upper()
    nums = re.findall(r'\d+', g)
    return int(nums[0]) if nums else 0


def collect_orphan_session_events(audit_qs, existing_session_ids, existing_module_ids):
    """
    Regroupe les événements SEANCE_START/STOP dont session_id n'existe plus.
    Retourne {deleted_module_id: {session_id: {start, stop, date, numero, intitule}}}.
    """
    by_module = defaultdict(lambda: defaultdict(dict))

    for log in audit_qs.filter(action__in=(
        AuditLog.Action.SEANCE_START,
        AuditLog.Action.SEANCE_STOP,
    )).order_by('timestamp'):
        extra = log.extra or {}
        sid = extra.get('session_id')
        mid = extra.get('module_id')
        if not sid or sid in existing_session_ids:
            continue
        if not mid or mid in existing_module_ids:
            continue

        slot = by_module[mid][sid]
        slot['intitule'] = extra.get('module_intitule') or ''
        slot['date_journee'] = _parse_date(extra.get('date_journee'))
        slot['numero'] = extra.get('session_numero')
        if log.action == AuditLog.Action.SEANCE_START:
            slot['start'] = log.timestamp
        else:
            slot['stop'] = log.timestamp

    return by_module


def _session_slot_set(module):
    return frozenset(
        (s.date_journee, s.numero)
        for s in module.sessions.all()
    )


def _event_slot_set(events):
    return frozenset(
        (e['date_journee'], e['numero'])
        for e in events.values()
        if e.get('date_journee') and e.get('numero') is not None
    )


def _first_start(events):
    starts = [e['start'] for e in events.values() if e.get('start')]
    return min(starts) if starts else timezone.make_aware(datetime(1970, 1, 1))


def match_deleted_modules_to_survivors(deleted_by_module):
    """
    Associe chaque module supprimé (id) à un module encore présent
    ayant le même intitulé et les mêmes créneaux EDT.
    """
    if not deleted_by_module:
        return {}

    by_intitule = defaultdict(dict)
    for mid, sessions in deleted_by_module.items():
        label = (next(iter(sessions.values())).get('intitule') or '').strip()
        if label:
            by_intitule[label.upper()][mid] = sessions

    mapping = {}
    for intitule_key, modules_dict in by_intitule.items():
        survivors = list(
            Module.objects.filter(intitule__iexact=intitule_key)
            .prefetch_related('sessions')
        )
        if not survivors:
            continue

        deleted_items = []
        for mid, sessions in modules_dict.items():
            slots = _event_slot_set(sessions)
            if slots:
                deleted_items.append((mid, sessions, slots, _first_start(sessions)))

        if not deleted_items:
            continue

        # Regrouper par signature EDT identique (groupes parallèles).
        by_slots = defaultdict(list)
        for item in deleted_items:
            by_slots[item[2]].append(item)

        for slots, group in by_slots.items():
            used_ids = {v.id for v in mapping.values()}
            candidates = [
                m for m in survivors
                if slots <= _session_slot_set(m) and m.id not in used_ids
            ]
            if not candidates:
                continue

            group.sort(key=lambda x: x[3])
            candidates.sort(key=_groupe_sort_key)

            if len(group) != len(candidates):
                # Appariement partiel : au moins le premier de chaque côté.
                for (mid, sessions, _, _), surv in zip(group, candidates):
                    mapping[mid] = surv
                continue

            for (mid, sessions, _, _), surv in zip(group, candidates):
                mapping[mid] = surv

    return mapping


def apply_session_recovery(module, sessions_by_id, *, dry_run=False):
    """Repose demarree_le / terminee_le sur les séances EDT du module conservé."""
    stats = {'updated': 0, 'skipped': 0, 'missing': 0}

    for _sid, event in sessions_by_id.items():
        date_j = event.get('date_journee')
        numero = event.get('numero')
        if not date_j or numero is None:
            stats['skipped'] += 1
            continue

        try:
            session = SessionModule.objects.get(
                module=module,
                date_journee=date_j,
                numero=numero,
            )
        except SessionModule.DoesNotExist:
            stats['missing'] += 1
            continue

        if session.demarree_le and session.terminee_le:
            stats['skipped'] += 1
            continue

        updates = []
        if event.get('start') and not session.demarree_le:
            session.demarree_le = event['start']
            updates.append('demarree_le')
        if event.get('stop') and not session.terminee_le:
            session.terminee_le = event['stop']
            updates.append('terminee_le')

        if not updates:
            stats['skipped'] += 1
            continue

        if not dry_run:
            session.save(update_fields=updates)
        stats['updated'] += 1

    if not dry_run and stats['updated']:
        open_count = module.sessions.filter(
            demarree_le__isnull=False,
            terminee_le__isnull=True,
        ).count()
        if open_count:
            if module.statut != 'EN_COURS':
                module.statut = 'EN_COURS'
                module.save(update_fields=['statut'])
        elif module.sessions.filter(demarree_le__isnull=False).exists():
            if module.statut not in ('TERMINEE', 'EN_COURS'):
                module.statut = 'TERMINEE'
                module.save(update_fields=['statut'])

    return stats


def recover_sessions_from_audit(audit_qs, *, dry_run=False):
    existing_session_ids = set(SessionModule.objects.values_list('id', flat=True))
    existing_module_ids = set(Module.objects.values_list('id', flat=True))
    deleted_by_module = collect_orphan_session_events(
        audit_qs, existing_session_ids, existing_module_ids,
    )
    mapping = match_deleted_modules_to_survivors(deleted_by_module)

    results = []
    totals = {'modules': 0, 'sessions_updated': 0, 'sessions_missing': 0, 'unmapped': 0}

    for mid, sessions in deleted_by_module.items():
        survivor = mapping.get(mid)
        if not survivor:
            totals['unmapped'] += 1
            results.append({
                'deleted_module_id': mid,
                'survivor': None,
                'stats': None,
            })
            continue

        if dry_run:
            stats = apply_session_recovery(survivor, sessions, dry_run=True)
        else:
            with transaction.atomic():
                stats = apply_session_recovery(survivor, sessions, dry_run=False)

        totals['modules'] += 1
        totals['sessions_updated'] += stats['updated']
        totals['sessions_missing'] += stats['missing']
        results.append({
            'deleted_module_id': mid,
            'survivor': survivor,
            'stats': stats,
        })

    return results, totals, mapping


def _resolve_personne(cible_type, cible_numero):
    if cible_type == 'formateur':
        return Formateur.objects.filter(numerobadge=cible_numero).first(), 'formateur'
    if cible_type == 'participant':
        return Participant.objects.filter(matricule=cible_numero).first(), 'participant'
    return None, cible_type


def _find_module_for_scan(log, personne, type_personne):
    if not log.formation_id or not personne:
        return None

    qs = Module.objects.filter(formation_id=log.formation_id)
    if type_personne == 'participant':
        grade = getattr(personne, 'grade', '') or ''
        groupe = getattr(personne, 'groupe', '') or ''
        vague = getattr(personne, 'vague', '') or ''
        if grade:
            qs = qs.filter(grade__iexact=grade)
        if groupe:
            qs = qs.filter(groupe__iexact=groupe)
        if vague:
            qs = qs.filter(vague__iexact=vague)
    modules = list(qs.prefetch_related('sessions'))
    if len(modules) == 1:
        return modules[0]
    # Plusieurs modules : celui avec une séance démarrée ce jour-là.
    day = timezone.localtime(log.timestamp).date()
    started = [
        m for m in modules
        if m.sessions.filter(date_journee=day, demarree_le__isnull=False).exists()
    ]
    if len(started) == 1:
        return started[0]
    return None


def _find_session_for_scan(module, ts):
    day = timezone.localtime(ts).date()
    sessions = list(
        module.sessions.filter(
            date_journee=day,
            demarree_le__isnull=False,
        ).order_by('numero')
    )
    for s in sessions:
        start = s.demarree_le
        end = s.terminee_le or ts
        if start <= ts <= end:
            return s
    return sessions[0] if len(sessions) == 1 else None


def recover_pointages_from_audit(audit_qs, *, dry_run=False):
    """
    Recrée les pointages dont l'audit existe mais le lien pointage_id est mort.
    Apparie ENTREE → SORTIE par matricule + séance.
    """
    entree_actions = (
        AuditLog.Action.SCAN_SECURE_ENTREE,
        AuditLog.Action.FORCE_ENTREE,
    )
    sortie_actions = (
        AuditLog.Action.SCAN_SECURE_SORTIE,
        AuditLog.Action.FORCE_SORTIE,
    )

    entrees = list(
        audit_qs.filter(action__in=entree_actions, pointage__isnull=True)
        .exclude(cible_numero='')
        .order_by('timestamp')
    )
    sorties = list(
        audit_qs.filter(action__in=sortie_actions, pointage__isnull=True)
        .exclude(cible_numero='')
        .order_by('timestamp')
    )

    sorties_by_key = defaultdict(list)
    for log in sorties:
        key = (log.cible_numero, log.cible_type, log.formation_id)
        sorties_by_key[key].append(log)

    stats = {'created': 0, 'skipped': 0, 'no_module': 0, 'no_session': 0}

    for entree in entrees:
        personne, type_personne = _resolve_personne(entree.cible_type, entree.cible_numero)
        module = _find_module_for_scan(entree, personne, type_personne)
        if not module:
            stats['no_module'] += 1
            continue

        session = _find_session_for_scan(module, entree.timestamp)
        if not session:
            stats['no_session'] += 1
            continue

        key = (entree.cible_numero, entree.cible_type, entree.formation_id)
        sortie_log = None
        for candidate in sorties_by_key.get(key, []):
            if candidate.timestamp > entree.timestamp:
                sortie_log = candidate
                break

        lookup = {'session': session, 'date_journee': timezone.localtime(entree.timestamp).date()}
        if type_personne == 'participant':
            lookup['participant'] = personne
        elif type_personne == 'formateur':
            lookup['formateur'] = personne

        if Pointage.objects.filter(**lookup).exists():
            stats['skipped'] += 1
            continue

        if dry_run:
            stats['created'] += 1
            continue

        with transaction.atomic():
            pt = Pointage(
                session=session,
                date_journee=lookup['date_journee'],
                timestamp_entree=entree.timestamp,
                timestamp_sortie=sortie_log.timestamp if sortie_log else None,
                device_id=entree.device_id or '',
                statut=Pointage.Statut.TERMINE if sortie_log else Pointage.Statut.EN_COURS,
            )
            if type_personne == 'participant':
                pt.participant = personne
            elif type_personne == 'formateur':
                pt.formateur = personne
            if sortie_log:
                pt.calculer_duree()
            pt.save()
            stats['created'] += 1

    return stats
