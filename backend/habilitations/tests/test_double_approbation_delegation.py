"""Double approbation des délégations sensibles.

Une délégation portant un rôle sensible (ou une permission critique) n'est
activée qu'à la SECONDE validation, faite par une personne distincte de la
première, et jamais par le délégant ou le délégataire. Une délégation non
sensible reste activée en une seule validation (non-régression).
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from habilitations.models import DelegationHabilitation, JournalHabilitation, RoleMetier
from habilitations.services.delegations_u5 import ErreurConsole, activer_delegation
from habilitations.tests import _u5_fixtures as fx


class DoubleApprobationDelegationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fx.referentiel_charge()

    def setUp(self):
        self.admin1 = fx.admin('dbl_admin1')
        self.admin2 = fx.admin('dbl_admin2')
        self.role = RoleMetier.objects.get(code='RESPONSABLE_PEDAGOGIQUE')
        self.role.sensible = True
        self.role.save(update_fields=['sensible'])
        self.delegant = fx.compte_curp(
            'dbl_chef', self.role.code, role_legacy='PERSONNEL')
        self.delegataire = fx.compte_curp(
            'dbl_rempl', role_code=None, role_legacy='PERSONNEL')
        self.delegation = DelegationHabilitation.objects.create(
            delegant=self.delegant, delegataire=self.delegataire,
            date_fin=timezone.localdate() + timedelta(days=30),
            motif='Absence du responsable.',
            statut=DelegationHabilitation.Statut.PROPOSEE)
        self.delegation.roles.set([self.role])

    def _recharger(self):
        return DelegationHabilitation.objects.get(pk=self.delegation.pk)

    def _refus_journalises(self):
        return JournalHabilitation.objects.filter(
            type_evenement=JournalHabilitation.TypeEvenement.ACCES_REFUSE).count()

    def test_01_delegation_sensible_detectee(self):
        self.assertTrue(self._recharger().est_sensible())

    def test_02_premiere_validation_n_active_pas(self):
        resultat = activer_delegation(self.delegation, self.admin1, 'Contrôle 1.', {})
        self.assertEqual(resultat.statut, DelegationHabilitation.Statut.PROPOSEE)
        self.assertEqual(self._recharger().premiere_validation_par, self.admin1)
        self.assertIsNotNone(self._recharger().premiere_validation_le)
        self.assertTrue(JournalHabilitation.objects.filter(
            type_evenement=JournalHabilitation.TypeEvenement.DELEGATION_PREMIERE_VALIDATION,
        ).exists())

    def test_03_meme_acteur_ne_peut_pas_valider_deux_fois(self):
        activer_delegation(self.delegation, self.admin1, 'Contrôle 1.', {})
        avant = self._refus_journalises()
        with self.assertRaises(ErreurConsole) as ctx:
            activer_delegation(self.delegation, self.admin1, 'Contrôle 2.', {})
        self.assertEqual(ctx.exception.code, 'DOUBLE_VALIDATION_MEME_ACTEUR')
        self.assertEqual(ctx.exception.statut, 403)
        self.assertEqual(self._recharger().statut, DelegationHabilitation.Statut.PROPOSEE)
        self.assertEqual(self._refus_journalises(), avant + 1)

    def test_04_second_valideur_distinct_active(self):
        activer_delegation(self.delegation, self.admin1, 'Contrôle 1.', {})
        activee = activer_delegation(self.delegation, self.admin2, 'Contrôle 2.', {})
        self.assertEqual(activee.statut, DelegationHabilitation.Statut.ACTIVE)
        self.assertEqual(activee.valide_par, self.admin2)
        self.assertEqual(activee.premiere_validation_par, self.admin1)

    def test_05_delegant_ne_peut_pas_etre_second_valideur(self):
        activer_delegation(self.delegation, self.admin1, 'Contrôle 1.', {})
        with self.assertRaises(ErreurConsole) as ctx:
            activer_delegation(self.delegation, self.delegant.user, 'auto', {})
        self.assertEqual(ctx.exception.code, 'DELEGATION_AUTO_VALIDATION')
        self.assertEqual(self._recharger().statut, DelegationHabilitation.Statut.PROPOSEE)

    def test_06_delegation_non_sensible_activee_en_une_validation(self):
        self.role.sensible = False
        self.role.save(update_fields=['sensible'])
        activee = activer_delegation(self.delegation, self.admin1, 'Contrôle.', {})
        self.assertEqual(activee.statut, DelegationHabilitation.Statut.ACTIVE)
        self.assertIsNone(activee.premiere_validation_par)
