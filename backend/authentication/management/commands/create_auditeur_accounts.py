"""
Crée (ou met à jour) les comptes utilisateurs pour tous les auditeurs inscrits à au moins un module.

Usage typique:
  python manage.py create_auditeur_accounts --dry-run
  python manage.py create_auditeur_accounts --password OPHIR2025

Le username est le numéro d'inscription (matricule) de l'auditeur.
Le mot de passe par défaut est OPHIR2025. L'auditeur devra le changer à la première connexion.
Le mot de passe est réinitialisé pour les comptes ciblés (sauf si --skip-existing est passé).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from formations.models import ModuleParticipant, Participant

User = get_user_model()

DEFAULT_PASSWORD = 'OPHIR2025'


class Command(BaseCommand):
    help = "Crée des comptes User (rôle AUDITEUR) pour les auditeurs inscrits à au moins un module."

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
            help='Ne pas modifier les utilisateurs déjà liés au participant.',
        )
        parser.add_argument(
            '--formation-id',
            type=int,
            default=None,
            help='Limiter aux inscriptions dont le module appartient à cette formation.',
        )

    def handle(self, *args, **options):
        password = options['password']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']
        formation_id = options['formation_id']

        qs = (
            ModuleParticipant.objects.select_related('participant', 'module__formation')
            .order_by('participant_id')
        )
        if formation_id is not None:
            qs = qs.filter(module__formation_id=formation_id)

        participant_ids = qs.values_list('participant_id', flat=True).distinct()
        participants = (
            Participant.objects.filter(pk__in=participant_ids)
            .select_related('user', 'secretariat')
            .order_by('nom', 'prenom', 'matricule')
        )

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for participant in participants:
            try:
                action = self._process_participant(
                    participant=participant,
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
                        f"ERREUR {participant.matricule} {participant.nom} {participant.prenom}: {exc}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Terminé — créés: {created}, mis à jour: {updated}, ignorés: {skipped}, erreurs: {errors}"
                + (" (dry-run)" if dry_run else "")
            )
        )

    def _process_participant(
        self,
        *,
        participant: Participant,
        password: str,
        dry_run: bool,
        skip_existing: bool,
    ) -> str:
        username = participant.matricule

        if participant.user_id and skip_existing:
            self.stdout.write(
                f"[SKIP] {username} — compte déjà lié (user_id={participant.user_id})"
            )
            return 'skipped'

        if dry_run:
            self.stdout.write(
                f"[DRY-RUN] {username} → {participant.prenom} {participant.nom}"
            )
            return 'skipped'

        with transaction.atomic():
            user = participant.user
            if user is None:
                user = User(
                    username=username,
                    email=participant.email or '',
                    first_name=participant.prenom[:150],
                    last_name=participant.nom[:150],
                    role=User.Role.AUDITEUR,
                    matricule=participant.matricule,
                    secretariat=participant.secretariat,
                    is_active=True,
                    must_change_password=True,
                )
                user.set_password(password)
                user.save()
                participant.user = user
                participant.save(update_fields=['user'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[CREATE] {username} ({participant.prenom} {participant.nom})"
                    )
                )
                return 'created'

            # Compte existant lié : aligner les champs et réinitialiser le mot de passe
            changed_fields = []
            if user.username != username:
                user.username = username
                changed_fields.append('username')
            if user.email != (participant.email or ''):
                user.email = participant.email or ''
                changed_fields.append('email')
            if user.first_name != participant.prenom:
                user.first_name = participant.prenom[:150]
                changed_fields.append('first_name')
            if user.last_name != participant.nom:
                user.last_name = participant.nom[:150]
                changed_fields.append('last_name')
            if user.role != User.Role.AUDITEUR:
                user.role = User.Role.AUDITEUR
                changed_fields.append('role')
            if user.matricule != participant.matricule:
                user.matricule = participant.matricule
                changed_fields.append('matricule')
            if user.secretariat_id != getattr(participant.secretariat, 'pk', None):
                user.secretariat = participant.secretariat
                changed_fields.append('secretariat')

            user.set_password(password)
            user.is_active = True
            if not getattr(user, 'must_change_password', False):
                user.must_change_password = True
                changed_fields.append('must_change_password')

            user.save()
            self.stdout.write(
                self.style.WARNING(
                    f"[UPDATE] {username} ({participant.prenom} {participant.nom}) "
                    f"(champs: {', '.join(sorted(set(changed_fields)))})"
                )
            )
            return 'updated'
