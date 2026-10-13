"""Suppression d'un compte ayant des événements au journal (tous moteurs).

Les clés étrangères du journal passent à NULL ; l'identité reste lisible dans
``acteur_label``. Le journal refuse toujours toute modification de contenu.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from habilitations.models import JournalHabilitation
from habilitations.services.journalisation import journaliser


class SuppressionCompteAvecJournalTests(TestCase):
    def setUp(self):
        self.utilisateur = get_user_model().objects.create_user(
            username='journal_del_user', password='Mot#2026x')
        journaliser('CONNEXION', acteur=self.utilisateur, motif='trace suppression')

    def test_01_suppression_conserve_les_traces(self):
        self.utilisateur.delete()
        evenement = JournalHabilitation.objects.get(motif='trace suppression')
        self.assertIsNone(evenement.acteur_id)
        self.assertEqual(evenement.acteur_label, 'journal_del_user')

    def test_02_modification_du_motif_refusee_orm(self):
        evenement = JournalHabilitation.objects.get(motif='trace suppression')
        evenement.motif = 'altéré'
        with self.assertRaises(Exception):
            evenement.save()
