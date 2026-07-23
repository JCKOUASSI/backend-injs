from django.core.management.base import BaseCommand

from apps.academics.models import Institution
from apps.faculty.models import Room
from apps.faculty.data.campus_rooms import room_dicts


class Command(BaseCommand):
    help = 'Charge le catalogue campus INJS (~250 espaces pédagogiques) dans faculty.Room'

    def add_arguments(self, parser):
        parser.add_argument(
            '--institution',
            type=str,
            default='',
            help='UUID ou code institution (défaut: première institution)',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Met à jour les salles existantes (même code)',
        )

    def handle(self, *args, **options):
        inst_arg = options.get('institution') or ''
        if inst_arg:
            inst = Institution.objects.filter(id=inst_arg).first() or Institution.objects.filter(code=inst_arg).first()
        else:
            inst = Institution.objects.first()

        if not inst:
            self.stderr.write(self.style.ERROR('Aucune institution trouvée. Créez-en une avant.'))
            return

        created = updated = skipped = 0
        for data in room_dicts():
            defaults = {k: v for k, v in data.items() if k != 'code'}
            obj, was_created = Room.objects.get_or_create(
                institution=inst,
                code=data['code'],
                defaults=defaults,
            )
            if was_created:
                created += 1
            elif options['update']:
                for key, value in defaults.items():
                    setattr(obj, key, value)
                obj.is_active = True
                obj.save()
                updated += 1
            else:
                skipped += 1

        total = Room.objects.filter(institution=inst, is_active=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'Campus INJS — institution={inst.code or inst.name}: '
            f'+{created} créées, {updated} mises à jour, {skipped} inchangées '
            f'(total actif: {total})'
        ))
