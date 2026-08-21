from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.faculty.services.attendance_eval import close_overdue_for_date


class Command(BaseCommand):
    help = (
        'Clôture les présences ouvertes (sortie bornée à la fin prévue, auto-absence). '
        'À planifier en cron, par exemple toutes les 15 minutes.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date ISO (YYYY-MM-DD). Par défaut : aujourd’hui et la veille.',
        )
        parser.add_argument(
            '--today-only',
            action='store_true',
            help='Ne traiter que la date du jour (ou --date).',
        )

    def handle(self, *args, **options):
        if options.get('date'):
            days = [date.fromisoformat(options['date'])]
        elif options.get('today_only'):
            days = [timezone.localdate()]
        else:
            today = timezone.localdate()
            days = [today - timedelta(days=1), today]

        for session_date in days:
            result = close_overdue_for_date(session_date)
            self.stdout.write(self.style.SUCCESS(
                f'{session_date.isoformat()} : {result["sessions"]} séance(s), '
                f'{result["closed"]} sortie(s) auto, {result["absents"]} absence(s)'
            ))
