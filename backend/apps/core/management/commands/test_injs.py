"""Lance toute la suite de tests INJS (apps/*/tests/)."""
from django.core.management import call_command
from django.core.management.base import BaseCommand

INJS_TEST_PACKAGES = [
    'apps.accounts.tests',
    'apps.students.tests',
    'apps.finance.tests',
    'apps.exams.tests',
    'apps.academics.tests',
    'apps.reports.tests',
    'apps.core.tests',
    'apps.faculty.tests',
]


class Command(BaseCommand):
    help = 'Exécute tous les tests automatisés INJS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keepdb', action='store_true',
            help='Conserve la base de test entre les exécutions',
        )
        parser.add_argument(
            'pytest_args', nargs='*',
            help='Arguments transmis à manage.py test (ex. apps.finance.tests)',
        )

    def handle(self, *args, **options):
        labels = options['pytest_args'] or INJS_TEST_PACKAGES
        kwargs = {'verbosity': options.get('verbosity', 1)}
        if options['keepdb']:
            kwargs['keepdb'] = True
        call_command('test', *labels, **kwargs)
