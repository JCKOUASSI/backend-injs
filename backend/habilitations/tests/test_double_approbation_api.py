"""Double approbation des délégations sensibles — niveau API.

Parcours exigé : la première validation laisse la délégation « PROPOSEE » avec
la mention « 1re validation » ; seule une seconde validation par une autre
personne l'active. Le délégant ne peut valider à aucune étape.
"""
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from habilitations.models import DelegationHabilitation, RoleMetier
from habilitations.tests import _u5_fixtures as fx
from parametres.flags import invalidate_flags_cache
from parametres.models import Parametre

FLAG_CLE = 'flag.curp_ui_admin'


class DoubleApprobationApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fx.referentiel_charge()

    def setUp(self):
        Parametre.objects.update_or_create(
            cle=FLAG_CLE,
            defaults={'libelle': 'Console CURP', 'categorie': 'flags',
                      'type': 'bool', 'valeur': 'true', 'valeur_defaut': 'false',
                      'actif': True})
        invalidate_flags_cache()
        self.admin1 = fx.admin('dblapi_admin1')
        self.admin2 = fx.admin('dblapi_admin2')
        role = RoleMetier.objects.get(code='RESPONSABLE_PEDAGOGIQUE')
        role.sensible = True
        role.save(update_fields=['sensible'])
        self.delegant = fx.compte_curp('dblapi_chef', role.code, role_legacy='PERSONNEL')
        self.delegataire = fx.compte_curp('dblapi_rempl', role_code=None,
                                          role_legacy='PERSONNEL')
        self.delegation = DelegationHabilitation.objects.create(
            delegant=self.delegant, delegataire=self.delegataire,
            date_fin=timezone.localdate() + timedelta(days=30),
            motif='Absence du responsable.',
            statut=DelegationHabilitation.Statut.PROPOSEE)
        self.delegation.roles.set([role])
        self.url = f'/api/habilitations/delegations/{self.delegation.pk}/activer/'

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def _activer(self, user, motif='Contrôle effectué.'):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(self.url, {'motif': motif}, format='json')

    def test_01_premiere_validation_reste_proposee_avec_mention(self):
        reponse = self._activer(self.admin1)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data['statut'], 'PROPOSEE')
        self.assertTrue(reponse.data['sensible'])
        self.assertEqual(reponse.data['premiere_validation_par'], 'dblapi_admin1')
        self.assertIsNotNone(reponse.data['premiere_validation_le'])
        self.assertFalse(reponse.data['active'])

    def test_02_meme_personne_ne_valide_pas_deux_fois(self):
        self._activer(self.admin1)
        reponse = self._activer(self.admin1)
        self.assertEqual(reponse.status_code, 403)
        self.delegation.refresh_from_db()
        self.assertEqual(self.delegation.statut, DelegationHabilitation.Statut.PROPOSEE)

    def test_03_seconde_validation_par_autre_personne_active(self):
        self._activer(self.admin1)
        reponse = self._activer(self.admin2)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.data['statut'], 'ACTIVE')
        self.assertTrue(reponse.data['active'])
        self.assertEqual(reponse.data['premiere_validation_par'], 'dblapi_admin1')

    def test_04_delegant_refuse_a_chaque_etape(self):
        client = APIClient()
        client.force_authenticate(user=self.delegant.user)
        self.assertEqual(client.post(self.url, {'motif': 'auto'}, format='json').status_code, 403)
        self._activer(self.admin1)
        self.assertEqual(client.post(self.url, {'motif': 'auto'}, format='json').status_code, 403)
        self.delegation.refresh_from_db()
        self.assertEqual(self.delegation.statut, DelegationHabilitation.Statut.PROPOSEE)
