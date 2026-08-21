"""Reprise de l'ancien emploi du temps ``faculty.Schedule``.

Les créneaux hebdomadaires récurrents sont déroulés en séances datées sur la
fenêtre d'une période de formation, pour ne rien perdre de l'existant.

    python manage.py eptinjs_import_schedules --periode P1
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.faculty.models import Schedule

from eptinjs.models import JourFerie, PeriodeFormation, ProgrammePeriode, Seance
from eptinjs.models import minutes_between


class Command(BaseCommand):
    help = 'Convertit les créneaux faculty.Schedule en séances datées eptinjs.'

    def add_arguments(self, parser):
        parser.add_argument('--periode', required=True, help='Code de la période de formation cible.')
        parser.add_argument('--dry-run', action='store_true', help='Simule sans écrire.')

    @transaction.atomic
    def handle(self, *args, **options):
        periode = PeriodeFormation.objects.filter(code=options['periode']).first()
        if periode is None:
            self.stderr.write(self.style.ERROR(f'Période « {options["periode"]} » introuvable.'))
            return

        feries = set(
            JourFerie.objects
            .filter(institution_id=periode.academic_year.institution_id, is_active=True)
            .values_list('date', flat=True)
        )

        schedules = Schedule.objects.filter(is_active=True).select_related(
            'assignment', 'assignment__course', 'assignment__promotion',
            'assignment__teacher', 'supervisor', 'room',
        )
        if not schedules:
            self.stdout.write(self.style.WARNING('Aucun créneau actif à reprendre.'))
            return

        programmes_crees, seances_creees = 0, 0

        for schedule in schedules:
            assignment = schedule.assignment
            programme, created = ProgrammePeriode.objects.get_or_create(
                periode=periode,
                course=assignment.course,
                promotion=assignment.promotion,
                session_kind=schedule.session_kind,
                defaults={
                    'teacher': assignment.teacher,
                    'supervisor': schedule.resolved_supervisor(),
                    'salle_preferee': schedule.room,
                    'volume_horaire_minutes': 0,
                },
            )
            programmes_crees += int(created)

            dates = self._occurrences(periode, schedule.day_of_week, feries)
            duree = minutes_between(schedule.start_time, schedule.end_time)

            for numero, jour in enumerate(dates, start=1):
                existe = Seance.objects.filter(
                    programme=programme, date=jour, heure_debut=schedule.start_time,
                ).exists()
                if existe:
                    continue
                if options['dry_run']:
                    seances_creees += 1
                    continue
                Seance.objects.create(
                    programme=programme,
                    periode=periode,
                    course=assignment.course,
                    promotion=assignment.promotion,
                    teacher=assignment.teacher,
                    supervisor=schedule.resolved_supervisor(),
                    room=schedule.room,
                    session_kind=schedule.session_kind,
                    numero=numero,
                    intitule=f'{assignment.course.name} — séance {numero}',
                    date=jour,
                    heure_debut=schedule.start_time,
                    heure_fin=schedule.end_time,
                    duree_minutes=duree,
                    statut='planifiee',
                    origine='import',
                )
                seances_creees += 1

            if not options['dry_run']:
                programme.volume_horaire_minutes = programme.minutes_planifiees()
                programme.save(update_fields=['volume_horaire_minutes', 'updated_at'])

        prefixe = ''
        if options['dry_run']:
            # get_or_create des programmes a déjà écrit : on annule tout.
            transaction.set_rollback(True)
            prefixe = '[simulation] '
        self.stdout.write(self.style.SUCCESS(
            f'{prefixe}{programmes_crees} programme(s) et {seances_creees} séance(s) depuis '
            f'{len(schedules)} créneau(x) hebdomadaire(s).',
        ))

    def _occurrences(self, periode, jour_semaine, feries):
        """Toutes les dates de la période tombant le bon jour de la semaine."""
        dates = []
        courant = periode.date_debut
        while courant <= periode.date_fin:
            if (
                courant.weekday() == jour_semaine
                and courant not in feries
                and periode.semaine_autorisee(courant)
            ):
                dates.append(courant)
            courant += timedelta(days=1)
        return dates
