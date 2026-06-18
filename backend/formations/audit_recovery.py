"""Reconstitution partielle depuis AuditLog (post-migration 0076, sans dump)."""

import re
from collections import defaultdict
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from formations.models import Formateur, Module, Participant, SessionModule
from presences.models import AuditLog, Pointage


def _parse_date(val):
    if not val:
        return None
    if hasattr(val, 'year'):
        return val
    try:
        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_numero(val):
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _groupe_sort_key(module):
    g = (module.groupe or '').upper()
    nums = re.findall(r'\d+', g)
    return int(nums[0]) if nums else 0


def collect_orphan_session_events(audit_qs, existing_session_ids, existing_module_ids):
    """
    Regroupe les événements SEANCE_START/STOP dont session_id n'existe plus.

    Retourne (events_by_module, meta_by_module) où meta contient formation_id et intitulé.
    """
    by_module = defaultdict(lambda: defaultdict(dict))
    meta_by_module = {}

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
        slot['numero'] = _parse_numero(
            extra.get('session_numero') if extra.get('session_numero') is not None
            else extra.get('numero')
        )
        slot['formation_id'] = log.formation_id
        if log.action == AuditLog.Action.SEANCE_START:
            slot['start'] = log.timestamp
        else:
            slot['stop'] = log.timestamp

        if mid not in meta_by_module:
            meta_by_module[mid] = {
                'formation_id': log.formation_id,
                'intitule': (extra.get('module_intitule') or '').strip(),
            }

    return by_module, meta_by_module


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


def _event_dates(events):
    return frozenset(
        e['date_journee'] for e in events.values() if e.get('date_journee')
    )


def _first_start(events):
    starts = [e['start'] for e in events.values() if e.get('start')]
    return min(starts) if starts else timezone.make_aware(datetime(1970, 1, 1))


def _overlap_score(deleted_slots, module):
    if not deleted_slots:
        deleted_dates = set()
    else:
        deleted_dates = {d for d, _ in deleted_slots}
    surv_slots = _session_slot_set(module)
    if deleted_slots:
        return len(deleted_slots & surv_slots)
    # Secours : chevauchement par dates seules.
    return len(deleted_dates & {d for d, _ in surv_slots})


def match_deleted_modules_to_survivors(deleted_by_module, meta_by_module):
    """
    Associe chaque module supprimé à un survivant (même formation + intitulé,
    score de chevauchement EDT maximal).
    """
    if not deleted_by_module:
        return {}

    by_scope = defaultdict(dict)
    for mid, sessions in deleted_by_module.items():
        meta = meta_by_module.get(mid, {})
        formation_id = meta.get('formation_id')
        intitule = (meta.get('intitule') or '').upper()
        if not intitule:
            continue
        by_scope[(formation_id, intitule)][mid] = sessions

    mapping = {}
    for (formation_id, intitule_key), modules_dict in by_scope.items():
        survivors_qs = Module.objects.filter(intitule__iexact=intitule_key)
        if formation_id:
            survivors_qs = survivors_qs.filter(formation_id=formation_id)
        survivors = list(survivors_qs.prefetch_related('sessions'))
        if not survivors:
            continue

        deleted_items = []
        for mid, sessions in modules_dict.items():
            slots = _event_slot_set(sessions)
            dates = _event_dates(sessions)
            if not slots and not dates:
                continue
            deleted_items.append((mid, sessions, slots, dates, _first_start(sessions)))

        deleted_items.sort(key=lambda x: (-len(x[2]) or -len(x[3]), x[4]))
        used_ids = set()

        for mid, sessions, slots, dates, first_start in deleted_items:
            scored = []
            for mod in survivors:
                if mod.id in used_ids:
                    continue
                score = _overlap_score(slots, mod)
                if not score and dates:
                    surv_dates = {s.date_journee for s in mod.sessions.all()}
                    score = len(dates & surv_dates)
                if score > 0:
                    scored.append((score, _groupe_sort_key(mod), mod))
            if not scored:
                continue
            scored.sort(key=lambda x: (-x[0], x[1]))
            chosen = scored[0][2]
            mapping[mid] = chosen
            used_ids.add(chosen.id)

        # Second passage : appariement par ordre chronologique si même score.
        unmapped = [mid for mid in modules_dict if mid not in mapping]
        free_survivors = [m for m in survivors if m.id not in used_ids]
        if unmapped and free_survivors:
            unmapped_items = [
                (mid, modules_dict[mid], _first_start(modules_dict[mid]))
                for mid in unmapped
            ]
            unmapped_items.sort(key=lambda x: x[2])
            free_survivors.sort(key=_groupe_sort_key)
            for (mid, _, _), surv in zip(unmapped_items, free_survivors):
                mapping[mid] = surv
                used_ids.add(surv.id)

    return mapping


def _resolve_session(module, date_j, numero, events_for_day):
    """Retrouve la séance EDT cible (numero exact, sinon séance unique du jour)."""
    if date_j is None:
        return None

    if numero is not None:
        try:
            return SessionModule.objects.get(
                module=module,
                date_journee=date_j,
                numero=numero,
            )
        except SessionModule.DoesNotExist:
            pass

    day_sessions = list(
        SessionModule.objects.filter(module=module, date_journee=date_j).order_by('numero')
    )
    if len(day_sessions) == 1:
        return day_sessions[0]

    # Plusieurs séances le même jour : préférer celle sans démarrage.
    if numero is not None:
        for s in day_sessions:
            if s.numero == numero:
                return s

    empty = [s for s in day_sessions if not s.demarree_le]
    if len(empty) == 1:
        return empty[0]

    return None


def apply_session_recovery(module, sessions_by_id, *, dry_run=False):
    """Repose demarree_le / terminee_le sur les séances EDT du module conservé."""
    stats = {
        'updated': 0,
        'skipped': 0,
        'missing': 0,
        'already_complete': 0,
        'no_slot': 0,
    }

    # Fusionner par (date, numero) au cas où START/STOP portent sur des session_id distincts.
    merged = defaultdict(dict)
    for event in sessions_by_id.values():
        date_j = event.get('date_journee')
        numero = event.get('numero')
        key = (date_j, numero)
        if not date_j:
            stats['no_slot'] += 1
            continue
        if event.get('start'):
            merged[key]['start'] = event['start']
        if event.get('stop'):
            merged[key]['stop'] = event['stop']
        merged[key]['date_journee'] = date_j
        merged[key]['numero'] = numero

    for key, event in merged.items():
        date_j, numero = key
        session = _resolve_session(module, date_j, numero, event)
        if not session:
            stats['missing'] += 1
            continue

        if session.demarree_le and session.terminee_le:
            stats['already_complete'] += 1
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
    deleted_by_module, meta_by_module = collect_orphan_session_events(
        audit_qs, existing_session_ids, existing_module_ids,
    )
    mapping = match_deleted_modules_to_survivors(deleted_by_module, meta_by_module)

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
                'meta': meta_by_module.get(mid),
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
            'meta': meta_by_module.get(mid),
        })

    return results, totals, mapping


def _resolve_personne(cible_type, cible_numero):
    if cible_type == 'formateur':
        return Formateur.objects.filter(numerobadge=cible_numero).first(), 'formateur'
    if cible_type == 'participant':
        return Participant.objects.filter(matricule=cible_numero).first(), 'participant'
    return None, cible_type


def _find_module_for_scan(log, personne, type_personne, *, intitule_hint=''):
    if not log.formation_id or not personne:
        return None

    def _candidates(qs):
        modules = list(qs.prefetch_related('sessions'))
        day = timezone.localtime(log.timestamp).date()
        started = [m for m in modules if m.sessions.filter(
            date_journee=day, demarree_le__isnull=False,
        ).exists()]
        if len(started) == 1:
            return started[0]
        if len(modules) == 1:
            return modules[0]
        return None

    qs = Module.objects.filter(formation_id=log.formation_id)
    if intitule_hint:
        qs = qs.filter(intitule__iexact=intitule_hint)

    if type_personne == 'participant':
        grade = getattr(personne, 'grade', '') or ''
        groupe = getattr(personne, 'groupe', '') or ''
        vague = getattr(personne, 'vague', '') or ''
        for filters in (
            {'grade__iexact': grade, 'groupe__iexact': groupe, 'vague__iexact': vague},
            {'grade__iexact': grade, 'groupe__iexact': groupe},
            {'grade__iexact': grade},
            {},
        ):
            filt = {k: v for k, v in filters.items() if v}
            hit = _candidates(qs.filter(**filt) if filt else qs)
            if hit:
                return hit
    return _candidates(qs)


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


def recover_pointages_from_audit(audit_qs, *, dry_run=False, intitule_hint=''):
    """
    Recrée les pointages dont l'audit existe mais le lien pointage_id est mort.
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
        module = _find_module_for_scan(
            entree, personne, type_personne, intitule_hint=intitule_hint,
        )
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
