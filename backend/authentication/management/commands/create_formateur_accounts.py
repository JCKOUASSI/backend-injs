"""
Crée (ou met à jour) les comptes utilisateurs pour les formateurs assignés à au moins un module.

Usage typique:
  python manage.py create_formateur_accounts --dry-run
  python manage.py create_formateur_accounts --password OPHIR2025

Le username est le numéro de badge du formateur (ex. F0042).
Le mot de passe par défaut est OPHIR2025. Le formateur devra le changer à la première connexion.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from formations.models import Formateur, ModuleFormateur

User = get_user_model()

DEFAULT_PASSWORD = 'OPHIR2025'


class Command(BaseCommand):
    help = "Crée des comptes User (rôle FORMATEUR) pour les formateurs assignés à au moins un module."

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=DEFAULT_PASSWORD,
            help=f'Mot de passe à appliquer (défaut: {DEFAULT_PASSWORD}).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les actions sans écrire en base.',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Ne pas modifier les utilisateurs déjà liés au formateur.',
        )
        parser.add_argument(
            '--formation-id',
            type=int,
            default=None,
            help='Limiter aux assignations dont le module appartient à cette formation.',
        )

    def handle(self, *args, **options):
        password = options['password']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']
        formation_id = options['formation_id']

        qs = ModuleFormateur.objects.select_related('formateur', 'module__formation').order_by('formateur_id')
        if formation_id is not None:
            qs = qs.filter(module__formation_id=formation_id)

        formateur_ids = qs.values_list('formateur_id', flat=True).distinct()
        formateurs = (
            Formateur.objects.filter(pk__in=formateur_ids)
            .select_related('user')
            .order_by('nom', 'prenom', 'numerobadge')
        )

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for formateur in formateurs:
            try:
                action = self._process_formateur(
                    formateur=formateur,
                    password=password,
                    dry_run=dry_run,
                    skip_existing=skip_existing,
                )
                if action == 'created':
                    created += 1
                elif action == 'updated':
                    updated += 1
                else:
                    skipped += 1
            except Exception as exc:  # pragma: no cover - diagnostic CLI
                errors += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"ERREUR {formateur.numerobadge} {formateur.nom} {formateur.prenom}: {exc}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Terminé — créés: {created}, mis à jour: {updated}, ignorés: {skipped}, erreurs: {errors}"
                + (" (dry-run)" if dry_run else "")
            )
        )

    def _process_formateur(
        self,
        *,
        formateur: Formateur,
        password: str,
        dry_run: bool,
        skip_existing: bool,
    ) -> str:
        username = formateur.numerobadge

        if formateur.user_id and skip_existing:
            self.stdout.write(
                f"[SKIP] {username} — compte déjà lié (user_id={formateur.user_id})"
            )
            return 'skipped'

        if dry_run:
            self.stdout.write(
                f"[DRY-RUN] {username} → {formateur.prenom} {formateur.nom}"
            )
            return 'skipped'

        with transaction.atomic():
            user = formateur.user
            if user is None:
                user = User(
                    username=username,
                    email=formateur.email or '',
                    first_name=formateur.prenom[:150],
                    last_name=formateur.nom[:150],
                    role=User.Role.FORMATEUR,
                    matricule=formateur.numerobadge,
                    is_active=True,
                    must_change_password=True,
                )
                user.set_password(password)
                user.save()
                formateur.user = user
                formateur.save(update_fields=['user'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[CREATE] {username} ({formateur.prenom} {formateur.nom})"
                    )
                )
                return 'created'

            changed_fields = []
            if user.username != username:
                user.username = username
                changed_fields.append('username')
            if user.email != (formateur.email or ''):
                user.email = formateur.email or ''
                changed_fields.append('email')
            if user.first_name != formateur.prenom:
                user.first_name = formateur.prenom[:150]
                changed_fields.append('first_name')
            if user.last_name != formateur.nom:
                user.last_name = formateur.nom[:150]
                changed_fields.append('last_name')
            if user.role != User.Role.FORMATEUR:
                user.role = User.Role.FORMATEUR
                changed_fields.append('role')
            if user.matricule != formateur.numerobadge:
                user.matricule = formateur.numerobadge
                changed_fields.append('matricule')

            user.set_password(password)
            user.is_active = True
            if not getattr(user, 'must_change_password', False):
                user.must_change_password = True
                changed_fields.append('must_change_password')

            user.save()
            self.stdout.write(
                self.style.WARNING(
                    f"[UPDATE] {username} ({formateur.prenom} {formateur.nom}) "
                    f"(champs: {', '.join(sorted(set(changed_fields)))})"
                )
            )
            return 'updated'
