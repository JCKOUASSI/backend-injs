from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.faculty.services.session_qr import ensure_sessions_for_date


class Command(BaseCommand):
    help = 'Ouvre automatiquement les séances de badgeage du jour selon l\'emploi du temps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date ISO (YYYY-MM-DD). Par défaut : aujourd\'hui.',
        )

    def handle(self, *args, **options):
        if options.get('date'):
            session_date = date.fromisoformat(options['date'])
        else:
            session_date = timezone.localdate()

        sessions = ensure_sessions_for_date(session_date)
        self.stdout.write(self.style.SUCCESS(
            f'{len(sessions)} séance(s) active(s) pour le {session_date.isoformat()}',
        ))
