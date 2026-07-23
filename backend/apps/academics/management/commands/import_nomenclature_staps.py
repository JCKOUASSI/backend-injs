"""Importe la nomenclature officielle des emplois STAPS INJS."""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import Specialization, StapsJobNomenclature
from apps.academics.nomenclature_parser import DEFAULT_NOMENCLATURE_PATH, parse_nomenclature_xlsx


class Command(BaseCommand):
    help = 'Importe la nomenclature emplois STAPS (grades A3/A4, CAPS/CAPEPS) depuis elements/'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(DEFAULT_NOMENCLATURE_PATH),
            help='Chemin vers le fichier xlsx',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Supprime les entrées existantes avant import',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = options['file']
        self.stdout.write(f'Parsing nomenclature: {path}')
        rows = parse_nomenclature_xlsx(path)
        if not rows:
            self.stdout.write(self.style.ERROR('Aucune ligne extraite du fichier'))
            return

        if options['replace']:
            deleted, _ = StapsJobNomenclature.objects.all().delete()
            self.stdout.write(f'{deleted} entrée(s) supprimée(s).')

        created = updated = skipped = 0
        for row in rows:
            try:
                spec = Specialization.objects.get(code=row.specialization_code)
            except Specialization.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Spécialité {row.specialization_code} absente — ligne ignorée'
                ))
                skipped += 1
                continue

            if not row.diploma_code:
                self.stdout.write(self.style.WARNING(
                    f'Diplôme non reconnu pour {row.specialization_code}/{row.degree_type}'
                ))
                skipped += 1
                continue

            _, was_created = StapsJobNomenclature.objects.update_or_create(
                degree_type=row.degree_type,
                specialization=spec,
                defaults={
                    'civil_service_grade': row.civil_service_grade,
                    'track': row.track,
                    'job_title': row.job_title[:255],
                    'duration_years': row.duration_years,
                    'competencies': row.competencies,
                    'career_outcomes': row.career_outcomes,
                    'diploma_code': row.diploma_code,
                    'diploma_label': row.diploma_label[:255],
                    'employers': row.employers,
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import terminé: {created} créées, {updated} mises à jour, {skipped} ignorées'
        ))
        for degree in ('L', 'M'):
            count = StapsJobNomenclature.objects.filter(degree_type=degree).count()
            label = 'Licence' if degree == 'L' else 'Master'
            self.stdout.write(f'  {label}: {count} emplois')
