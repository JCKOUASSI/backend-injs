"""Importe la maquette STAPS 2026 INJS dans la base académique."""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.maquette_parser import (
    DEFAULT_MAQUETTE_PATH,
    SPECIALIZATION_LABELS,
    parse_maquette_docx,
)
from apps.academics.models import (
    Course, Department, Institution, Program, ProgramCourse,
    Specialization, TeachingUnit,
)


class Command(BaseCommand):
    help = 'Importe UE/ECUE officiels depuis la maquette STAPS 2026 (elements/)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(DEFAULT_MAQUETTE_PATH),
            help='Chemin vers le docx maquette',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Supprime les UE/ECUE existants du département STAPS avant import',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = options['file']
        self.stdout.write(f'Parsing maquette: {path}')
        ues = parse_maquette_docx(path)
        if not ues:
            self.stdout.write(self.style.ERROR('Aucune UE extraite du document'))
            return

        inst, _ = Institution.objects.get_or_create(
            code='INJS',
            defaults={
                'name': 'Institut National de la Jeunesse et des Sports',
                'acronym': 'INJS',
                'city': 'Abidjan',
            },
        )
        dept, _ = Department.objects.get_or_create(
            institution=inst,
            code='STAPS',
            defaults={'name': 'Sciences et Techniques des Activités Physiques et Sportives'},
        )

        specs = {}
        for code, (name, is_tc) in SPECIALIZATION_LABELS.items():
            spec, _ = Specialization.objects.update_or_create(
                code=code,
                defaults={'name': name, 'is_tronc_commun': is_tc, 'track': 'BOTH'},
            )
            specs[code] = spec

        programs = {}
        for track_code, track_label in [('PL', 'Professeur de Lycée'), ('PC', 'Professeur de Collège')]:
            prog, _ = Program.objects.update_or_create(
                department=dept,
                code=f'L-STAPS-{track_code}',
                defaults={
                    'name': f'Licence STAPS — {track_label}',
                    'degree_type': 'L',
                    'track': track_code,
                    'duration_semesters': 6,
                    'total_credits': 180,
                    'description': 'Maquette STAPS 2026 INJS/UFHB',
                    'is_active': True,
                },
            )
            programs[track_code] = prog

        if options['replace']:
            ProgramCourse.objects.filter(program__in=programs.values()).delete()
            Course.objects.filter(teaching_unit__department=dept).delete()
            TeachingUnit.objects.filter(department=dept).delete()
            self.stdout.write('Ancien référentiel STAPS supprimé.')

        ue_count = ecue_count = link_count = 0
        for ue_data in ues:
            if ue_data.credits_ects <= 0:
                ue_data.credits_ects = sum(e.credits_ects for e in ue_data.ecues) or 3

            teaching_unit, _ = TeachingUnit.objects.update_or_create(
                code=ue_data.code,
                defaults={
                    'name': ue_data.name[:255],
                    'credits_ects': ue_data.credits_ects,
                    'semester_number': ue_data.semester,
                    'department': dept,
                    'description': ue_data.category[:500] if ue_data.category else '',
                },
            )
            ue_count += 1

            for ecue in ue_data.ecues:
                Course.objects.update_or_create(
                    teaching_unit=teaching_unit,
                    code=ecue.code,
                    defaults={
                        'name': ecue.name[:255],
                        'hours_cm': ecue.hours_cm,
                        'hours_td': ecue.hours_td,
                        'hours_tp': ecue.hours_tp,
                    },
                )
                ecue_count += 1

            spec = specs.get(ue_data.specialization_code, specs['TC'])
            target_programs = []
            if ue_data.track == 'PL':
                target_programs = [programs['PL']]
            elif ue_data.track == 'PC':
                target_programs = [programs['PC']]
            else:
                target_programs = list(programs.values())

            for program in target_programs:
                _, created = ProgramCourse.objects.update_or_create(
                    program=program,
                    teaching_unit=teaching_unit,
                    specialization=spec,
                    defaults={
                        'semester_number': ue_data.semester,
                        'is_mandatory': True,
                        'credits_override': ue_data.credits_ects,
                    },
                )
                if created:
                    link_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import terminé: {ue_count} UE, {ecue_count} ECUE, {link_count} nouvelles liaisons filière'
        ))
        for code, prog in programs.items():
            total = ProgramCourse.objects.filter(program=prog).count()
            self.stdout.write(f'  {prog.code}: {total} UE rattachées')
