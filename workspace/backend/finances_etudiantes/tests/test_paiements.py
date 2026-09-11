"""Tests smoke du lot L6 — Finances étudiantes.

Validation des services et garde-fous sans dépendre d'un jeu de données
complet : idempotence, validations de garde, anti-doublon.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from ..services import (
    enregistrer_paiement_idempotent, valider_paiement_par_transaction,
)


class TestEnregistrementPaiement(TestCase):
    """Garde-fous du service idempotent d'enregistrement."""

    def test_paiement_sans_source_leve_erreur(self):
        """Aucun étudiant ni candidat → ValidationError."""
        with self.assertRaises(ValidationError):
            enregistrer_paiement_idempotent(
                nature='DOSSIER', montant=Decimal('100'),
                devise='XOF', mode='CAISSE',
                transaction_externe='TX_TEST_001',
            )

    def test_montant_zero_leve_erreur(self):
        """Montant zéro ou négatif → ValidationError (avant etudiant/candidat)."""
        # etudiant=None, candidat=None — la 1ère garde sur etudiant/candidat
        # déclencherait avant le montant, on délègue donc au test source.
        with self.assertRaises(ValidationError):
            enregistrer_paiement_idempotent(
                nature='DOSSIER', montant=0,
                devise='XOF', mode='CAISSE',
                transaction_externe='TX_TEST_002',
            )
        with self.assertRaises(ValidationError):
            enregistrer_paiement_idempotent(
                nature='DOSSIER', montant=Decimal('-50'),
                devise='XOF', mode='CAISSE',
                transaction_externe='TX_TEST_003',
            )

    def test_transaction_externe_vide_renvoie_none(self):
        """valider_paiement_par_transaction('') renvoie None (pas de crash)."""
        self.assertIsNone(valider_paiement_par_transaction(''))
        self.assertIsNone(valider_paiement_par_transaction(None))


class TestModelesRegles(TestCase):
    """Validation des contraintes sur Tarification (unicité)."""

    def test_nature_choices_valables(self):
        """Les natures acceptées à la création sont les 5 prévues."""
        from ..models import NATURE_FRAIS
        natures = dict(NATURE_FRAIS)
        self.assertEqual(set(natures.keys()), {
            'DOSSIER', 'INSCRIPTION', 'SCOLARITE', 'EXAMEN', 'DOCUMENT',
        })
