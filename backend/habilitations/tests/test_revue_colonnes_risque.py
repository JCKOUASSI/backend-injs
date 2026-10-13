"""Revue des habilitations : colonnes, regroupement et signalement du risque.

La revue est consultative : elle ne modifie aucun compte et signale les
comptes détenant un rôle sensible.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from habilitations.models import AttributionRole, CompteUtilisateur, RoleMetier
from habilitations.tests import _u5_fixtures as fx
from parametres.flags import invalidate_flags_cache
from parametres.models import Parametre

FLAG_CLE = 'flag.curp_ui_admin'


class RevueColonnesRisqueTests(TestCase):
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
        self.admin = fx.admin('revue_admin')
        self.role_sensible = RoleMetier.objects.get(code='RESPONSABLE_PEDAGOGIQUE')
        self.role_sensible.sensible = True
        self.role_sensible.save(update_fields=['sensible'])
        self.compte_sensible = fx.compte_curp(
            'revue_sensible', self.role_sensible.code, role_legacy='PERSONNEL')
        self.compte_simple = fx.compte_curp('revue_simple', role_code=None,
                                            role_legacy='PERSONNEL')
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def tearDown(self):
        from django.core.cache import cache
        cache.clear()
        super().tearDown()

    def _lignes(self):
        reponse = self.client.get('/api/habilitations/comptes/revue/')
        self.assertEqual(reponse.status_code, 200)
        lignes = []
        for lignes_groupe in reponse.data['groupes'].values():
            lignes.extend(lignes_groupe)
        return reponse, lignes

    def test_01_colonnes_presentes(self):
        _, lignes = self._lignes()
        self.assertTrue(lignes)
        for ligne in lignes:
            for cle in ('compte', 'username', 'statut', 'roles', 'sensible'):
                self.assertIn(cle, ligne)

    def test_02_compte_a_role_sensible_signale(self):
        _, lignes = self._lignes()
        par_user = {l['username']: l for l in lignes}
        self.assertTrue(par_user['revue_sensible']['sensible'])
        self.assertIn(self.role_sensible.code, par_user['revue_sensible']['roles'])
        self.assertFalse(par_user['revue_simple']['sensible'])

    def test_03_revue_ne_modifie_rien(self):
        avant = list(CompteUtilisateur.objects.values_list('pk', 'statut'))
        attributions_avant = AttributionRole.objects.count()
        self._lignes()
        self.assertEqual(list(CompteUtilisateur.objects.values_list('pk', 'statut')), avant)
        self.assertEqual(AttributionRole.objects.count(), attributions_avant)

    def test_04_role_expire_non_compte(self):
        fin_passee = timezone.localdate() - timedelta(days=1)
        AttributionRole.objects.filter(compte=self.compte_sensible).update(date_fin=fin_passee)
        _, lignes = self._lignes()
        par_user = {l['username']: l for l in lignes}
        self.assertNotIn(self.role_sensible.code, par_user['revue_sensible']['roles'])
        self.assertFalse(par_user['revue_sensible']['sensible'])
