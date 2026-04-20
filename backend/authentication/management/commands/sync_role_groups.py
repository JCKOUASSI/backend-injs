from django.core.management.base import BaseCommand

from authentication.role_groups import ensure_role_groups, sync_all_users_role_groups


class Command(BaseCommand):
    help = "Crée/met à jour les groupes par rôle et resynchronise tous les utilisateurs."

    def handle(self, *args, **options):
        ensure_role_groups()
        sync_all_users_role_groups()
        self.stdout.write(
            self.style.SUCCESS("Groupes de rôles synchronisés avec succès.")
        )
