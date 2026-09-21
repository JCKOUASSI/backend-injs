"""Tests de la commande ``diagnostic_admin`` (workflow « Fix production admin »).

Le diagnostic était auparavant du Python embarqué dans le YAML du workflow, à
la colonne 1 d'un bloc ``run: |`` : le fichier échouait à l'analyse et aucune
étape ne s'exécutait. Passé en commande de gestion, il devient testable — ces
tests couvrent les fonctions pures, la sortie ``CLE=valeur`` et les codes de
retour de ``--strict``.
"""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from authentication.management.commands.diagnostic_admin import (
    etat_admin,
    peut_administrer,
    pour_affichage,
)


class EtatAdminTests(TestCase):
    """Les fonctions pures, sans base de données."""

    def test_compte_absent(self):
        etat = etat_admin(None, superutilisateurs=[])
        self.assertFalse(etat['ADMIN_EXISTS'])
        self.assertEqual(0, etat['SUPERUSER_COUNT'])
        self.assertFalse(peut_administrer(etat))

    def test_compte_absent_mais_autres_superutilisateurs(self):
        etat = etat_admin(None, superutilisateurs=['racine', 'admin'])
        self.assertFalse(etat['ADMIN_EXISTS'])
        self.assertEqual(2, etat['SUPERUSER_COUNT'])
        # Les noms sont triés : la sortie ne dépend pas de l'ordre de la requête.
        self.assertEqual(['admin', 'racine'], etat['SUPERUSER_USERNAMES'])

    def test_un_compte_non_staff_ne_peut_pas_administrer(self):
        Utilisateur = get_user_model()
        compte = Utilisateur(username='invite', is_active=True, is_staff=False)
        self.assertFalse(peut_administrer(etat_admin(compte, [])))

    def test_un_compte_staff_inactif_ne_peut_pas_administrer(self):
        Utilisateur = get_user_model()
        compte = Utilisateur(username='admin', is_active=False, is_staff=True)
        self.assertFalse(peut_administrer(etat_admin(compte, [])))

    def test_un_compte_staff_actif_peut_administrer(self):
        Utilisateur = get_user_model()
        compte = Utilisateur(username='admin', is_active=True, is_staff=True)
        self.assertTrue(peut_administrer(etat_admin(compte, [])))

    def test_formatage_des_valeurs(self):
        self.assertEqual('True', pour_affichage(True))
        self.assertEqual('False', pour_affichage(False))
        self.assertEqual('None', pour_affichage(None))
        self.assertEqual('None', pour_affichage([]))
        self.assertEqual('a,b', pour_affichage(['a', 'b']))


class CommandeDiagnosticAdminTests(TestCase):
    def setUp(self):
        self.Utilisateur = get_user_model()

    def _sortie(self, *arguments):
        sortie = StringIO()
        call_command('diagnostic_admin', *arguments, stdout=sortie)
        return sortie.getvalue()

    def test_aucun_compte(self):
        texte = self._sortie()
        self.assertIn('ADMIN_EXISTS=False', texte)
        self.assertIn('SUPERUSER_COUNT=0', texte)
        self.assertIn("ne peut PAS ouvrir", texte)
        self.assertIn('Aucun compte superutilisateur', texte)

    def test_admin_sain(self):
        self.Utilisateur.objects.create_superuser(
            'admin', 'admin@example.com', 'motdepasse')
        texte = self._sortie()
        self.assertIn('ADMIN_EXISTS=True', texte)
        self.assertIn('ADMIN_ACTIVE=True', texte)
        self.assertIn('ADMIN_STAFF=True', texte)
        self.assertIn('ADMIN_SUPERUSER=True', texte)
        self.assertIn('peut ouvrir une session', texte)

    def test_compte_ordinaire_non_staff(self):
        self.Utilisateur.objects.create_superuser(
            'admin', 'admin@example.com', 'motdepasse')
        self.Utilisateur.objects.create_user(
            'auditeur', 'a@example.com', 'motdepasse')
        texte = self._sortie('--username', 'auditeur')
        self.assertIn('ADMIN_EXISTS=True', texte)
        self.assertIn('ADMIN_STAFF=False', texte)
        # Le compte visé n'est pas admin, mais un superutilisateur existe :
        # le diagnostic doit le dire plutôt que conclure à un dépôt cassé.
        self.assertIn('SUPERUSER_COUNT=1', texte)
        self.assertIn("D'autres comptes superutilisateurs existent", texte)

    def test_compte_vise_par_defaut(self):
        self.assertIn('ADMIN_EXISTS=False', self._sortie())

    def test_strict_sort_en_1_si_le_compte_ne_peut_pas_administrer(self):
        with self.assertRaises(SystemExit) as contexte:
            self._sortie('--strict')
        self.assertEqual(1, contexte.exception.code)

    def test_strict_sort_en_0_sur_un_admin_sain(self):
        self.Utilisateur.objects.create_superuser(
            'admin', 'admin@example.com', 'motdepasse')
        sortie = StringIO()
        # Ne doit lever ni SystemExit ni aucune autre exception.
        call_command('diagnostic_admin', '--strict', stdout=sortie)
        self.assertIn('ADMIN_STAFF=True', sortie.getvalue())
