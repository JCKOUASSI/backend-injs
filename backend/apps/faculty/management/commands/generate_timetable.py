from django.core.management.base import BaseCommand

from apps.academics.models import AcademicYear, Promotion
from apps.faculty.services.planning import generate_for_promotion, generate_for_academic_year, PlanningError


class Command(BaseCommand):
    help = "Génère automatiquement l'emploi du temps (affectations, salles, séances de présence)"

    def add_arguments(self, parser):
        parser.add_argument('--year', type=str, help='UUID ou libellé année (ex. 2025-2026)')
        parser.add_argument('--promotion', type=str, help='UUID promotion (sinon toutes si --all)')
        parser.add_argument('--all', action='store_true', help='Toutes les promotions actives')
        parser.add_argument('--replace', action='store_true', help='Remplacer l’EDT existant')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--max-per-day', type=int, default=3)

    def handle(self, *args, **options):
        year = None
        if options.get('year'):
            raw = options['year']
            year = AcademicYear.objects.filter(pk=raw).first() or AcademicYear.objects.filter(label=raw).first()
        if not year:
            year = AcademicYear.objects.filter(is_current=True).first()
        if not year:
            self.stderr.write('Aucune année académique courante.')
            return

        kwargs = {
            'replace_existing': options['replace'],
            'dry_run': options['dry_run'],
            'max_sessions_per_day': options['max_per_day'],
            'auto_assign_teachers': True,
            'auto_seed_roster': True,
            'open_sessions': True,
        }

        try:
            if options['all'] or not options.get('promotion'):
                result = generate_for_academic_year(year, **kwargs)
                self.stdout.write(self.style.SUCCESS(
                    f"{result['created']} créneau(x) — {result['promotions']} promotion(s)"
                ))
                return
            promo = Promotion.objects.filter(pk=options['promotion']).first()
            if not promo:
                self.stderr.write('Promotion introuvable')
                return
            result = generate_for_promotion(promotion=promo, academic_year=year, **kwargs)
            self.stdout.write(self.style.SUCCESS(
                f"{result['created']} créneau(x) pour {result['promotion']}"
            ))
        except PlanningError as exc:
            self.stderr.write(str(exc))
