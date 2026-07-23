from django.core.management.base import BaseCommand

from apps.academics.models import Institution
from apps.faculty.models import Room, EquipmentAsset, MaintenanceTicket, RoomReservation
from django.utils import timezone
from datetime import timedelta


DEMO_EQUIPMENT = [
    ('EQ-PROJ-001', 'Vidéoprojecteur Epson', 'Audiovisuel', 'AMP-001', ['projecteur', 'sono'], 1),
    ('EQ-PC-001', 'Parc PC salle info', 'Informatique', 'INF-001', ['pc', 'wifi'], 40),
    ('EQ-ERGO-001', 'Ergomètre CNMS', 'Médecine', 'MED-002', ['ergomètre', 'spiromètre'], 2),
    ('EQ-VR-001', 'Casques VR', 'Numérique', 'INF-014', ['casques_vr'], 8),
    ('EQ-FORCE-001', 'Plateforme de force', 'Biomécanique', 'LAB-001', ['capteurs', 'plateforme_force'], 1),
]


class Command(BaseCommand):
    help = 'Seed équipements / ticket / réservation démo campus INJS'

    def handle(self, *args, **options):
        inst = Institution.objects.first()
        if not inst:
            self.stderr.write('Aucune institution')
            return

        created = 0
        for code, name, category, room_code, tags, qty in DEMO_EQUIPMENT:
            room = Room.objects.filter(institution=inst, code=room_code).first()
            _, was = EquipmentAsset.objects.get_or_create(
                institution=inst,
                code=code,
                defaults={
                    'name': name,
                    'category': category,
                    'room': room,
                    'quantity': qty,
                    'capability_tags': tags,
                    'status': 'in_use' if room else 'available',
                },
            )
            if was:
                created += 1

        room = Room.objects.filter(institution=inst, code='SC-101').first()
        if room:
            MaintenanceTicket.objects.get_or_create(
                room=room,
                title='Climatisation défaillante',
                defaults={
                    'description': 'Ticket démo — climatisation salle SC-101',
                    'priority': 'medium',
                    'status': 'open',
                },
            )
            start = timezone.now() + timedelta(days=2)
            start = start.replace(hour=14, minute=0, second=0, microsecond=0)
            RoomReservation.objects.get_or_create(
                room=room,
                title='Séminaire partenaires sport',
                start_datetime=start,
                defaults={
                    'end_datetime': start + timedelta(hours=2),
                    'purpose': 'Réservation démo',
                    'attendees_count': 40,
                    'required_equipment': ['projecteur'],
                    'status': 'pending',
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f'Campus ops seed OK — {created} équipements créés '
            f'(total assets={EquipmentAsset.objects.filter(institution=inst).count()})'
        ))
