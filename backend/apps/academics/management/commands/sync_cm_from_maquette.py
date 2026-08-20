"""Synchronise les volumes horaires CM/TD/TP depuis la maquette officielle INJS."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.maquette_parser import DEFAULT_MAQUETTE_PATH, parse_maquette_docx
from apps.academics.models import Course


class Command(BaseCommand):
    help = (
        'Met à jour hours_cm / hours_td / hours_tp de tous les ECUE '
        'à partir du document officiel maquette STAPS 2026 (elements/).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(DEFAULT_MAQUETTE_PATH),
            help='Chemin du docx maquette officielle',
        )
        parser.add_argument(
            '--cm-only',
            action='store_true',
            help='Ne synchroniser que la colonne CM (Cours magistraux)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Afficher les écarts sans écrire en base',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = options['file']
        cm_only = options['cm_only']
        dry_run = options['dry_run']

        self.stdout.write(f'Lecture maquette officielle : {path}')
        ues = parse_maquette_docx(path)
        if not ues:
            self.stderr.write(self.style.ERROR('Aucune UE extraite du document.'))
            return

        official = {}
        for ue in ues:
            for ecue in ue.ecues:
                official[ecue.code] = ecue

        courses = list(Course.objects.filter(is_deleted=False).select_related('teaching_unit'))
        updated = unchanged = missing_in_doc = missing_in_db = 0
        cm_before = sum(c.hours_cm or 0 for c in courses)
        changes = []

        for course in courses:
            ecue = official.get(course.code)
            if not ecue:
                missing_in_doc += 1
                continue

            fields = []
            if (course.hours_cm or 0) != (ecue.hours_cm or 0):
                fields.append(('hours_cm', course.hours_cm or 0, ecue.hours_cm or 0))
            if not cm_only:
                if (course.hours_td or 0) != (ecue.hours_td or 0):
                    fields.append(('hours_td', course.hours_td or 0, ecue.hours_td or 0))
                if (course.hours_tp or 0) != (ecue.hours_tp or 0):
                    fields.append(('hours_tp', course.hours_tp or 0, ecue.hours_tp or 0))

            if not fields:
                unchanged += 1
                continue

            changes.append((course.code, fields))
            if not dry_run:
                if cm_only:
                    course.hours_cm = ecue.hours_cm or 0
                    course.save(update_fields=['hours_cm', 'updated_at'])
                else:
                    course.hours_cm = ecue.hours_cm or 0
                    course.hours_td = ecue.hours_td or 0
                    course.hours_tp = ecue.hours_tp or 0
                    course.save(update_fields=['hours_cm', 'hours_td', 'hours_tp', 'updated_at'])
            updated += 1

        official_codes = set(official)
        db_codes = {c.code for c in courses}
        missing_in_db = len(official_codes - db_codes)

        if dry_run:
            transaction.set_rollback(True)

        courses_after = Course.objects.filter(is_deleted=False)
        cm_after = sum(c.hours_cm or 0 for c in courses_after) if not dry_run else (
            cm_before + sum(new - old for _, fields in changes for field, old, new in fields if field == 'hours_cm')
        )
        cm_zero = courses_after.filter(hours_cm=0).count() if not dry_run else None

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'{"[DRY-RUN] " if dry_run else ""}Sync volumes terminée'
        ))
        self.stdout.write(f'  ECUE officiels     : {len(official)}')
        self.stdout.write(f'  ECUE en base       : {len(courses)}')
        self.stdout.write(f'  Mis à jour         : {updated}')
        self.stdout.write(f'  Déjà conformes     : {unchanged}')
        self.stdout.write(f'  Absents du doc     : {missing_in_doc}')
        self.stdout.write(f'  Absents de la base : {missing_in_db}')
        self.stdout.write(f'  Σ CM avant → après : {cm_before} → {cm_after}')
        if cm_zero is not None:
            self.stdout.write(
                f'  ECUE avec CM = 0    : {cm_zero} '
                f'(conforme à la maquette pour les APS pratiques)'
            )

        if changes:
            self.stdout.write('')
            self.stdout.write('Écarts corrigés (extrait) :')
            for code, fields in changes[:40]:
                detail = ', '.join(f'{name}: {old}→{new}' for name, old, new in fields)
                self.stdout.write(f'  {code}: {detail}')
            if len(changes) > 40:
                self.stdout.write(f'  … +{len(changes) - 40} autres')
        else:
            self.stdout.write(self.style.SUCCESS(
                'Tous les volumes CM (et TD/TP si demandé) sont déjà alignés sur la maquette officielle.'
            ))
