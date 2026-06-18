"""Reconstitue séances et badgeages depuis le journal d'audit (sans dump)."""

from django.core.management.base import BaseCommand

from formations.audit_recovery import recover_pointages_from_audit, recover_sessions_from_audit
from presences.models import AuditLog


class Command(BaseCommand):
    help = (
        'Reconstitue demarree_le/terminee_le et les pointages orphelins '
        'à partir du journal d\'audit (après migration 0076). '
        'Toujours lancer avec --dry-run d\'abord.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule sans écrire en base.',
        )
        parser.add_argument(
            '--since',
            type=str,
            default='2026-06-01',
            help='Date ISO min. pour l\'audit (défaut : 2026-06-01).',
        )
        parser.add_argument(
            '--intitule',
            type=str,
            help='Limiter à un intitulé de module (ex: DEONTOLOGIE).',
        )
        parser.add_argument(
            '--sessions-only',
            action='store_true',
            help='Ne reconstituer que les séances (pas les badgeages).',
        )
        parser.add_argument(
            '--pointages-only',
            action='store_true',
            help='Ne reconstituer que les badgeages (séances déjà récupérées).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        since = options['since']
        intitule = (options.get('intitule') or '').strip()

        audit_qs = AuditLog.objects.filter(
            action__in=(
                AuditLog.Action.SEANCE_START,
                AuditLog.Action.SEANCE_STOP,
                AuditLog.Action.SCAN_SECURE_ENTREE,
                AuditLog.Action.SCAN_SECURE_SORTIE,
                AuditLog.Action.FORCE_ENTREE,
                AuditLog.Action.FORCE_SORTIE,
            ),
        ).order_by('timestamp')
        if since:
            audit_qs = audit_qs.filter(timestamp__date__gte=since)

        prefix = '[dry-run] ' if dry_run else ''
        self.stdout.write(self.style.HTTP_INFO(f'\n{prefix}Reconstitution depuis l\'audit\n'))

        run_sessions = not options['pointages_only']
        run_pointages = not options['sessions_only']

        module_mapping = {}
        deleted_by_module = {}

        if run_sessions:
            session_audit = audit_qs.filter(action__in=(
                AuditLog.Action.SEANCE_START,
                AuditLog.Action.SEANCE_STOP,
            ))
            if intitule:
                session_audit = session_audit.filter(
                    extra__module_intitule__iexact=intitule,
                )

            results, totals, mapping = recover_sessions_from_audit(
                session_audit, dry_run=dry_run,
            )
            module_mapping = mapping
            from formations.audit_recovery import collect_orphan_session_events
            from formations.models import Module, SessionModule
            existing_session_ids = set(SessionModule.objects.values_list('id', flat=True))
            existing_module_ids = set(Module.objects.values_list('id', flat=True))
            deleted_by_module, _ = collect_orphan_session_events(
                session_audit, existing_session_ids, existing_module_ids,
            )

            self.stdout.write(self.style.HTTP_INFO('--- Séances ---'))
            for row in results:
                mid = row['deleted_module_id']
                surv = row['survivor']
                if not surv:
                    meta = row.get('meta') or {}
                    self.stdout.write(self.style.WARNING(
                        f'  module supprimé #{mid} '
                        f'(formation_id={meta.get("formation_id")}) : '
                        f'aucun survivant apparié'
                    ))
                    continue
                st = row['stats']
                meta = row.get('meta') or {}
                inferred = meta.get('inferred_groupe') or '?'
                score = meta.get('match_score', '?')
                edt_cov = meta.get('edt_coverage', '?')
                self.stdout.write(
                    f'  #{mid} → module #{surv.id} '
                    f'({surv.intitule} / {surv.groupe}, score={score}, EDT={edt_cov}) '
                    f'[formation_id={meta.get("formation_id")}] : '
                    f'{st["updated"]} mise(s) à jour, '
                    f'{st["missing"]} EDT manquant(s), '
                    f'{st.get("already_complete", 0)} déjà complète(s)'
                )

            self.stdout.write(
                f'\n{prefix}Modules appariés : {totals["modules"]}, '
                f'séances mises à jour : {totals["sessions_updated"]}, '
                f'non appariés : {totals["unmapped"]}'
            )

        if run_pointages:
            pt_audit = audit_qs.filter(action__in=(
                AuditLog.Action.SCAN_SECURE_ENTREE,
                AuditLog.Action.SCAN_SECURE_SORTIE,
                AuditLog.Action.FORCE_ENTREE,
                AuditLog.Action.FORCE_SORTIE,
            ))
            if intitule:
                from formations.models import Module
                formation_ids = Module.objects.filter(
                    intitule__iexact=intitule,
                ).values_list('formation_id', flat=True).distinct()
                pt_audit = pt_audit.filter(formation_id__in=formation_ids)

            if options['pointages_only'] and not module_mapping:
                from formations.audit_recovery import (
                    collect_orphan_session_events,
                    match_deleted_modules_to_survivors,
                )
                from formations.models import Module, SessionModule
                session_audit = audit_qs.filter(action__in=(
                    AuditLog.Action.SEANCE_START,
                    AuditLog.Action.SEANCE_STOP,
                ))
                if intitule:
                    session_audit = session_audit.filter(
                        extra__module_intitule__iexact=intitule,
                    )
                existing_session_ids = set(SessionModule.objects.values_list('id', flat=True))
                existing_module_ids = set(Module.objects.values_list('id', flat=True))
                deleted_by_module, meta_by_module = collect_orphan_session_events(
                    session_audit, existing_session_ids, existing_module_ids,
                )
                module_mapping = match_deleted_modules_to_survivors(
                    deleted_by_module, meta_by_module,
                )

            pt_stats = recover_pointages_from_audit(
                pt_audit, dry_run=dry_run, intitule_hint=intitule,
                module_mapping=module_mapping or None,
                deleted_by_module=deleted_by_module or None,
            )
            self.stdout.write(self.style.HTTP_INFO('\n--- Badgeages ---'))
            self.stdout.write(
                f'{prefix}Créés : {pt_stats["created"]}, '
                f'ignorés (déjà là) : {pt_stats["skipped"]}, '
                f'sans module : {pt_stats["no_module"]}, '
                f'sans séance : {pt_stats["no_session"]}'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nRelancez sans --dry-run pour appliquer.'
            ))
