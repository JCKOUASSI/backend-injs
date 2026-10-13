"""Protection BASE de l'immuabilité, spécifique PostgreSQL (prod / CI).

Les déclencheurs ``BEFORE UPDATE/DELETE`` sont posés par la migration
``0002_triggers_immuabilite``. Ce fichier ne s'exécute que sur PostgreSQL ;
sur SQLite (développement), l'immuabilité est garantie et testée au niveau
ORM dans ``test_journal``.

``TransactionTestCase`` est requis : une exception levée par un déclencheur
annulerait la transaction englobante d'un ``TestCase`` classique.
"""
import unittest

from django.db import connection, transaction
from django.test import TransactionTestCase

from habilitations.services.journalisation import journaliser


@unittest.skipUnless(
    connection.vendor == 'postgresql',
    "Les déclencheurs d'immuabilité base ne sont posés que sur PostgreSQL.",
)
class DeclencheursImmuabiliteTests(TransactionTestCase):
    def setUp(self):
        journaliser('CONNEXION', motif='test trigger')

    def test_update_brut_en_sql_est_bloque_par_la_base(self):
        with connection.cursor() as curseur, self.assertRaises(Exception):
            curseur.execute(
                "UPDATE habilitations_journalhabilitation "
                "SET motif = 'altéré' WHERE numero = 1"
            )

    def test_delete_brut_en_sql_est_bloque_par_la_base(self):
        with connection.cursor() as curseur, self.assertRaises(Exception):
            curseur.execute(
                "DELETE FROM habilitations_journalhabilitation WHERE numero = 1"
            )


@unittest.skipUnless(
    connection.vendor == 'postgresql',
    "Les déclencheurs d'immuabilité base ne sont posés que sur PostgreSQL.",
)
class SuppressionCompteAvecJournalTests(TransactionTestCase):
    """Régression : la suppression d'un compte ayant des événements au journal."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.utilisateur = get_user_model().objects.create_user(
            username='pg_journal_user', password='Mot#2026x')
        journaliser('CONNEXION', acteur=self.utilisateur, motif='trace avant suppression')

    def test_suppression_utilisateur_autorisee_et_identite_conservee(self):
        from habilitations.models import JournalHabilitation
        self.utilisateur.delete()
        evenement = JournalHabilitation.objects.get(motif='trace avant suppression')
        self.assertIsNone(evenement.acteur_id)
        self.assertEqual(evenement.acteur_label, 'pg_journal_user')

    def test_redirection_d_une_cle_etrangere_refusee(self):
        from django.contrib.auth import get_user_model
        from habilitations.models import JournalHabilitation
        autre = get_user_model().objects.create_user(
            username='pg_journal_autre', password='Mot#2026x')
        evenement = JournalHabilitation.objects.get(motif='trace avant suppression')
        with self.assertRaises(Exception):
            with transaction.atomic():
                JournalHabilitation.objects.filter(pk=evenement.pk).update(acteur_id=autre.pk)

    def test_modification_du_contenu_refusee_meme_apres_suppression(self):
        from habilitations.models import JournalHabilitation
        self.utilisateur.delete()
        with self.assertRaises(Exception):
            with transaction.atomic(), connection.cursor() as curseur:
                curseur.execute(
                    "UPDATE habilitations_journalhabilitation "
                    "SET motif = 'altéré' WHERE motif = 'trace avant suppression'")
        self.assertTrue(JournalHabilitation.objects.filter(
            motif='trace avant suppression').exists())
