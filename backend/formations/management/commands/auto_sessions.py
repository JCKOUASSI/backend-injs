"""
Management command: auto_sessions
Auto-start and auto-close SessionFormation based on heure_debut_prevue / heure_fin_prevue.

Usage (run every minute via cron):
    * * * * * /path/to/venv/bin/python manage.py auto_sessions

Crontab example:
    */5 * * * * cd /path/to/project && venv/bin/python manage.py auto_sessions >> /tmp/auto_sessions.log 2>&1
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from formations.models import Formation, SessionFormation


class Command(BaseCommand):
    help = 'Auto-start and auto-close sessions based on scheduled times'

    def handle(self, *args, **options):
        now = timezone.now()
        local_now = timezone.localtime(now)
        today = local_now.date()
        current_time = local_now.time()

        started = 0
        closed = 0

        # Auto-start: sessions with auto_demarrage=True, not yet started, time reached
        to_start = SessionFormation.objects.filter(
            auto_demarrage=True,
            demarree_le__isnull=True,
            heure_debut_prevue__isnull=False,
            date_journee=today,
            heure_debut_prevue__lte=current_time,
        ).select_related('formation')

        for session in to_start:
            session.demarree_le = now
            session.save(update_fields=['demarree_le'])
            started += 1

            formation = session.formation
            if formation.statut == 'PLANIFIEE':
                formation.statut = 'EN_COURS'
                formation.session_demarree_le = now
                formation.save(update_fields=['statut', 'session_demarree_le'])

            self.stdout.write(f'  ▶ Démarrée: {session}')

        # Auto-close: sessions started, not closed, end time passed
        to_close = SessionFormation.objects.filter(
            demarree_le__isnull=False,
            terminee_le__isnull=True,
            heure_fin_prevue__isnull=False,
        ).select_related('formation')

        for session in to_close:
            if (
                session.date_journee < today
                or (session.date_journee == today and session.heure_fin_prevue <= current_time)
            ):
                session.terminee_le = now
                session.save(update_fields=['terminee_le'])
                closed += 1
                self.stdout.write(f'  ■ Terminée: {session}')

                # Check if all sessions of the formation are now terminated
                formation = session.formation
                if (
                    formation.statut != 'TERMINEE'
                    and not SessionFormation.objects.filter(
                        formation=formation,
                        terminee_le__isnull=True,
                    ).exclude(pk=session.pk).exists()
                ):
                    formation.statut = 'TERMINEE'
                    formation.session_terminee_le = now
                    formation.save(update_fields=['statut', 'session_terminee_le'])
                    self.stdout.write(f'  ✓ Formation terminée: {formation.formation}')

        self.stdout.write(
            self.style.SUCCESS(
                f'[{local_now.strftime("%Y-%m-%d %H:%M")}] '
                f'{started} séance(s) démarrée(s), {closed} séance(s) terminée(s).'
            )
        )
