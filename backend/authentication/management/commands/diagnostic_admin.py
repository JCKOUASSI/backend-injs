"""Diagnostic du compte administrateur (workflow « Fix production admin »).

Ce diagnostic vivait à l'origine en Python embarqué dans
`.github/workflows/fix-production-admin.yml`, à l'intérieur d'un bloc
`run: |` et d'une commande `ssh` : les lignes de code y étaient à la colonne 1,
ce qui fermait le bloc scalaire et faisait échouer le workflow dès l'analyse
YAML (« could not find expected ':' »). Le diagnostic est maintenant une
commande de gestion : elle fait partie de l'image Docker, s'exécute en
production par `docker exec injs-be python manage.py diagnostic_admin`, et se
teste localement comme n'importe quelle commande.

La sortie est en `CLE=valeur` : lisible directement dans le journal d'Actions,
et consommable par un script (`grep`/`cut`) sans dépendre d'un formatage
fragile. Les quatre premières clés sont celles que produisait le script
d'origine, pour ne casser aucun traitement existant.

Commande volontairement en **lecture seule** et à code de retour 0 : c'est un
diagnostic, pas une correction. `--strict` fait sortir en code 1 quand le
compte ne peut pas ouvrir une session d'administration, pour brancher la
commande dans un contrôle automatisé.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

#: Clés de sortie, dans l'ordre d'affichage.
CLES_ETAT = (
    'ADMIN_EXISTS',
    'ADMIN_ACTIVE',
    'ADMIN_STAFF',
    'ADMIN_SUPERUSER',
    'ADMIN_LAST_LOGIN',
    'SUPERUSER_COUNT',
    'SUPERUSER_USERNAMES',
)


def etat_admin(utilisateur, superutilisateurs=()):
    """Construit l'état d'un compte (``None`` accepté) — fonction pure.

    ``superutilisateurs`` est la liste des noms de comptes disposant de
    ``is_superuser`` : elle sert à distinguer « le compte `admin` n'existe pas »
    de « aucun compte ne peut ouvrir l'administration ».
    """
    noms = sorted(superutilisateurs)
    if utilisateur is None:
        return {
            'ADMIN_EXISTS': False,
            'ADMIN_ACTIVE': False,
            'ADMIN_STAFF': False,
            'ADMIN_SUPERUSER': False,
            'ADMIN_LAST_LOGIN': None,
            'SUPERUSER_COUNT': len(noms),
            'SUPERUSER_USERNAMES': noms,
        }
    return {
        'ADMIN_EXISTS': True,
        'ADMIN_ACTIVE': bool(utilisateur.is_active),
        'ADMIN_STAFF': bool(utilisateur.is_staff),
        'ADMIN_SUPERUSER': bool(utilisateur.is_superuser),
        'ADMIN_LAST_LOGIN': utilisateur.last_login,
        'SUPERUSER_COUNT': len(noms),
        'SUPERUSER_USERNAMES': noms,
    }


def pour_affichage(valeur):
    """Formate une valeur d'état pour la sortie ``CLE=valeur``."""
    if isinstance(valeur, bool):
        return str(valeur)
    if valeur is None:
        return 'None'
    if isinstance(valeur, (list, tuple)):
        return ','.join(valeur) if valeur else 'None'
    return str(valeur)


def peut_administrer(etat):
    """Un compte ouvre l'administration s'il existe, est actif et ``staff``."""
    return bool(
        etat['ADMIN_EXISTS'] and etat['ADMIN_ACTIVE'] and etat['ADMIN_STAFF']
    )


class Command(BaseCommand):
    help = (
        "Diagnostic en lecture seule du compte administrateur : existence, "
        "état actif, staff, superutilisateur, dernière connexion."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='admin',
            help="Nom du compte à diagnostiquer (défaut : admin).",
        )
        parser.add_argument(
            '--strict',
            action='store_true',
            help=(
                "Sortir en code 1 si le compte ne peut pas ouvrir une session "
                "d'administration."
            ),
        )

    def handle(self, *args, **options):
        utilisateur_model = get_user_model()
        nom = options['username']
        utilisateur = utilisateur_model.objects.filter(username=nom).first()
        superutilisateurs = utilisateur_model.objects.filter(
            is_superuser=True
        ).values_list('username', flat=True)

        etat = etat_admin(utilisateur, superutilisateurs)
        for cle in CLES_ETAT:
            self.stdout.write(f'{cle}={pour_affichage(etat[cle])}')

        if peut_administrer(etat):
            self.stdout.write(
                self.style.SUCCESS(
                    f'Le compte « {nom} » peut ouvrir une session '
                    "d'administration."
                )
            )
        else:
            message = (
                f"Le compte « {nom} » ne peut PAS ouvrir une session "
                "d'administration."
            )
            if etat['SUPERUSER_COUNT']:
                message += (
                    " D'autres comptes superutilisateurs existent : "
                    f"{pour_affichage(etat['SUPERUSER_USERNAMES'])}."
                )
            else:
                message += " Aucun compte superutilisateur n'existe."
            self.stdout.write(self.style.WARNING(message))

        if options['strict'] and not peut_administrer(etat):
            raise SystemExit(1)
