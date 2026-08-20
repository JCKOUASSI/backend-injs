"""Jeu de démonstration : périodes, programmes et emploi du temps généré.

    python manage.py eptinjs_seed_demo --reset --generer
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import AcademicYear, Semester
from apps.faculty.models import Teacher

from eptinjs.models import (
    JourFerie,
    ParametresPlanification,
    PeriodeFormation,
    ProgrammePeriode,
    Seance,
)
from eptinjs.planning import generer_planning
from eptinjs.services.common import paires_ecue_promotion, promotions_filtrees

VOLUMES = {'cm': 'hours_cm', 'td': 'hours_td', 'tp': 'hours_tp'}


class Command(BaseCommand):
    help = 'Crée des périodes de formation, les programmes issus de la maquette et un emploi du temps.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Supprime les données eptinjs existantes.')
        parser.add_argument('--generer', action='store_true', help='Lance le moteur après création.')
        parser.add_argument('--periodes', type=int, default=2, help='Nombre de périodes à créer.')
        parser.add_argument('--promotions', type=int, default=3, help='Nombre de promotions à programmer.')
        parser.add_argument(
            '--ecue-par-promotion', type=int, default=6,
            help='Nombre d’ECUE programmés par promotion et par période.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        year = AcademicYear.objects.filter(is_current=True).order_by('-start_date').first()
        if year is None:
            year = AcademicYear.objects.order_by('-start_date').first()
        if year is None:
            self.stderr.write(self.style.ERROR(
                'Aucune année académique. Lancez d’abord « manage.py seed_injs_demo ».',
            ))
            return

        if options['reset']:
            Seance.objects.all().delete()
            ProgrammePeriode.objects.all().delete()
            PeriodeFormation.objects.all().delete()
            self.stdout.write('Données eptinjs réinitialisées.')

        ParametresPlanification.resolve(None)

        periodes = self._creer_periodes(year, options['periodes'])
        self.stdout.write(self.style.SUCCESS(f'{len(periodes)} période(s) de formation prête(s).'))

        self._creer_jours_feries(year)

        promotions = promotions_filtrees()[:options['promotions']]
        if not promotions:
            self.stderr.write(self.style.WARNING('Aucune promotion active : programmes non créés.'))
            return

        total = 0
        for index, periode in enumerate(periodes):
            semestre = periode.semester.number if periode.semester else None
            paires = paires_ecue_promotion(promotions, semester_number=semestre)
            total += self._creer_programmes(
                periode, paires,
                ecue_par_promotion=options['ecue_par_promotion'],
                decalage=index,
            )
        self.stdout.write(self.style.SUCCESS(f'{total} programme(s) de période créé(s).'))

        if options['generer']:
            for periode in periodes:
                resultat = generer_planning(periode, mode='best_effort', remplacer=True)
                synthese = resultat.synthese
                self.stdout.write(
                    f'  {periode.code} : {synthese["seances"]} séances, '
                    f'{synthese["heures_placees"]} h placées '
                    f'({synthese["taux_couverture"]} % de couverture, {synthese["echecs"]} échec(s)).',
                )

    def _creer_periodes(self, year, nombre):
        """Découpe l'année académique en fenêtres contiguës.

        Les dates des semestres de démonstration sont souvent trop courtes pour
        absorber une maquette complète : on découpe donc l'année, le semestre ne
        servant qu'à rattacher la période au calendrier LMD.
        """
        semestres = list(Semester.objects.filter(academic_year=year).order_by('number'))
        periodes = []
        duree = max((year.end_date - year.start_date).days // max(nombre, 1), 30)

        for index in range(nombre):
            debut = year.start_date + timedelta(days=index * duree)
            fin = min(debut + timedelta(days=duree - 1), year.end_date)
            if debut >= year.end_date:
                break
            periode, _ = PeriodeFormation.objects.update_or_create(
                academic_year=year,
                code=f'P{index + 1}',
                defaults={
                    'libelle': f'Période {index + 1} — {year.label}',
                    'semester': semestres[index] if index < len(semestres) else None,
                    'date_debut': debut,
                    'date_fin': fin,
                    'ordre': index + 1,
                    'rythme_mensuel': '4',
                    'statut': 'ouverte',
                    'is_active': True,
                },
            )
            periodes.append(periode)
        return periodes

    def _creer_jours_feries(self, year):
        feries = [
            (f'{year.start_date.year}-12-25', 'Noël'),
            (f'{year.end_date.year}-01-01', 'Jour de l’An'),
            (f'{year.end_date.year}-05-01', 'Fête du Travail'),
            (f'{year.end_date.year}-08-07', 'Fête de l’Indépendance'),
        ]
        for date_iso, libelle in feries:
            annee, mois, jour = (int(part) for part in date_iso.split('-'))
            from datetime import date as date_cls
            valeur = date_cls(annee, mois, jour)
            if year.start_date <= valeur <= year.end_date:
                JourFerie.objects.get_or_create(
                    institution=year.institution, date=valeur,
                    defaults={'libelle': libelle},
                )

    def _creer_programmes(self, periode, paires, *, ecue_par_promotion, decalage=0):
        """Programme un échantillon d'ECUE par promotion, calibré sur la période."""
        par_promotion: dict = {}
        for course, promotion in paires:
            par_promotion.setdefault(promotion.id, []).append((course, promotion))

        enseignants = list(Teacher.objects.filter(is_active=True).select_related('user'))
        rotation = 0
        crees = 0

        for lot in par_promotion.values():
            # Le décalage évite de reprogrammer les mêmes ECUE d'une période à l'autre.
            debut = (decalage * ecue_par_promotion) % max(len(lot), 1)
            selection = (lot + lot)[debut:debut + ecue_par_promotion]
            for course, promotion in selection:
                for nature, champ in VOLUMES.items():
                    heures = getattr(course, champ, 0) or 0
                    if heures <= 0:
                        continue
                    titulaire = enseignants[rotation % len(enseignants)] if enseignants else None
                    rotation += 1
                    _, created = ProgrammePeriode.objects.get_or_create(
                        periode=periode, course=course, promotion=promotion, session_kind=nature,
                        defaults={
                            'volume_horaire_minutes': heures * 60,
                            'creneau_mode': 'matin_et_soir' if nature == 'cm' else 'soir',
                            'teacher': titulaire,
                        },
                    )
                    crees += int(created)
        return crees
