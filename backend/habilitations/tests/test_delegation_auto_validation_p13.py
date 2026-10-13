"""Phase 13 — une délégation ne peut pas être validée par ses propres parties.

Garanties : ni le délégant ni le délégataire ne peuvent activer la délégation ;
un tiers habilité (administrateur) le peut ; l'état reste PROPOSÉE en cas de refus.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from habilitations.models import DelegationHabilitation, JournalHabilitation, RoleMetier
from habilitations.services.delegations_u5 import ErreurConsole, activer_delegation
from habilitations.tests import _u5_fixtures as fx


class AutoValidationDelegationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fx.referentiel_charge()

    def setUp(self):
        self.admin = fx.admin()
        self.role_rp = RoleMetier.objects.get(code='RESPONSABLE_PEDAGOGIQUE')
        self.fin = timezone.localdate() + timedelta(days=30)
        self.delegant = fx.compte_curp(
            'p13_chef', self.role_rp.code, role_legacy='PERSONNEL')
        self.delegataire = fx.compte_curp(
            'p13_rempl', role_code=None, role_legacy='PERSONNEL')
        self.delegation = DelegationHabilitation.objects.create(
            delegant=self.delegant, delegataire=self.delegataire,
            date_fin=self.fin, motif='Absence du responsable.',
            statut=DelegationHabilitation.Statut.PROPOSEE)
        self.delegation.roles.set([self.role_rp])

    def _recharger(self):
        return DelegationHabilitation.objects.get(pk=self.delegation.pk)

    def test_01_delegant_ne_peut_pas_valider_sa_delegation(self):
        with self.assertRaises(ErreurConsole) as ctx:
            activer_delegation(self.delegation, self.delegant.user, 'auto', {})
        self.assertEqual(ctx.exception.code, 'DELEGATION_AUTO_VALIDATION')
        self.assertEqual(self._recharger().statut, DelegationHabilitation.Statut.PROPOSEE)

    def test_02_delegataire_ne_peut_pas_valider_sa_delegation(self):
        with self.assertRaises(ErreurConsole) as ctx:
            activer_delegation(self.delegation, self.delegataire.user, 'auto', {})
        self.assertEqual(ctx.exception.code, 'DELEGATION_AUTO_VALIDATION')
        self.assertEqual(self._recharger().statut, DelegationHabilitation.Statut.PROPOSEE)

    def test_03_tiers_habilite_peut_valider(self):
        activee = activer_delegation(self.delegation, self.admin, 'Contrôle fait.', {})
        self.assertEqual(activee.statut, DelegationHabilitation.Statut.ACTIVE)
        self.assertEqual(activee.valide_par, self.admin)

    def test_04_refus_auto_validation_journalise(self):
        avant = JournalHabilitation.objects.filter(
            type_evenement=JournalHabilitation.TypeEvenement.ACCES_REFUSE).count()
        with self.assertRaises(ErreurConsole):
            activer_delegation(self.delegation, self.delegant.user, 'auto', {})
        apres = JournalHabilitation.objects.filter(
            type_evenement=JournalHabilitation.TypeEvenement.ACCES_REFUSE)
        self.assertEqual(apres.count(), avant + 1)
        self.assertEqual(apres.last().nouvelle_valeur.get('code'), 'DELEGATION_AUTO_VALIDATION')
