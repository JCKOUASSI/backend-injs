"""Phase 3 — ExigePermission posée sur les vues de la console (refonte « Utilisateurs & Accès »).

Garanties vérifiées :
- chaque code de permission exigé par la console existe dans le référentiel
  (sinon le moteur serait aveugle sur cette vue) ;
- mode OFF et mode OBSERVATION : aucune réponse modifiée, aucun refus ;
- mode APPLICATION : un refus moteur devient 403 et est tracé ACCES_REFUSE.
Le mode APPLICATION n'est jamais activé par défaut : il est forcé ici, dans le
seul cadre d'un test, par ``override_settings``.
"""
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from habilitations.models import JournalHabilitation, PermissionMetier
from habilitations.permissions import ExigePermissionParMethode
from habilitations.services.moteur import DecisionAutorisation
from habilitations.tests import _u5_fixtures as fx

CODES_CONSOLE = {
    'administration.compte.consulter', 'administration.compte.creer',
    'administration.compte.modifier', 'administration.personne.consulter',
    'administration.role.consulter', 'administration.permission.consulter',
    'administration.journal.consulter', 'administration.attribution.consulter',
    'administration.attribution.valider', 'administration.attribution.creer',
    'administration.revue.consulter', 'administration.revue.modifier',
    'administration.delegation.creer',
    # Phase 4 : workflow et organisation.
    'administration.derogation.consulter', 'administration.derogation.creer',
    'administration.derogation.modifier', 'administration.delegation.consulter',
    'administration.delegation.modifier', 'administration.politique.consulter',
    'administration.politique.creer', 'administration.politique.modifier',
}


def _decision_refus(permission):
    return DecisionAutorisation(
        permission=permission, canal='WEB', mode='APPLICATION',
        gouverne=True, autorise=False, motifs=['TEST_REFUS_P3'],
    )


class CodesConsoleTests(TestCase):
    def test_01_codes_de_la_console_existent_au_referentiel(self):
        fx.referentiel_charge()
        existants = set(PermissionMetier.objects.filter(
            code__in=CODES_CONSOLE).values_list('code', flat=True))
        manquants = CODES_CONSOLE - existants
        self.assertEqual(manquants, set(), f'codes absents du référentiel : {manquants}')

    def test_02_methode_non_mappee_s_abstient(self):
        perm = ExigePermissionParMethode({'GET': 'administration.compte.consulter'})
        requete = mock.Mock(method='DELETE')
        self.assertTrue(perm.has_permission(requete, None))


@override_settings(HABILITATIONS_APPLICATION=False, HABILITATIONS_OBSERVATION=False)
class ModeOffTests(TestCase):
    def setUp(self):
        fx.referentiel_charge()
        fx.ouvrir(fx.F_UI)
        self.admin = fx.admin('adm_p3_off', role='ADMIN')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_01_mode_off_ne_refuse_jamais(self):
        with mock.patch('habilitations.permissions.est_autorise',
                        return_value=_decision_refus('administration.compte.consulter')):
            reponse = self.client.get('/api/habilitations/comptes/')
        self.assertEqual(reponse.status_code, 200)


@override_settings(HABILITATIONS_APPLICATION=False, HABILITATIONS_OBSERVATION=True)
class ModeObservationTests(TestCase):
    def setUp(self):
        fx.referentiel_charge()
        fx.ouvrir(fx.F_UI)
        self.admin = fx.admin('adm_p3_obs', role='ADMIN')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_01_observation_ne_modifie_pas_la_reponse(self):
        with mock.patch('habilitations.permissions.est_autorise',
                        return_value=_decision_refus('administration.compte.consulter')):
            reponse = self.client.get('/api/habilitations/comptes/')
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(JournalHabilitation.objects.filter(
            type_evenement=JournalHabilitation.TypeEvenement.ACCES_REFUSE).exists())


@override_settings(HABILITATIONS_APPLICATION=True, HABILITATIONS_OBSERVATION=False)
class ModeApplicationTests(TestCase):
    def setUp(self):
        fx.referentiel_charge()
        fx.ouvrir(fx.F_UI)
        self.admin = fx.admin('adm_p3_app', role='ADMIN')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_01_refus_moteur_devient_403_trace(self):
        with mock.patch('habilitations.permissions.est_autorise',
                        return_value=_decision_refus('administration.compte.consulter')):
            reponse = self.client.get('/api/habilitations/comptes/')
        self.assertEqual(reponse.status_code, 403)
        trace = JournalHabilitation.objects.filter(
            type_evenement=JournalHabilitation.TypeEvenement.ACCES_REFUSE).first()
        self.assertIsNotNone(trace)
        self.assertEqual(
            trace.nouvelle_valeur.get('permission'), 'administration.compte.consulter')

    def test_02_decision_autorisee_passe(self):
        autorisee = DecisionAutorisation(
            permission='administration.compte.consulter', canal='WEB',
            mode='APPLICATION', gouverne=True, autorise=True)
        with mock.patch('habilitations.permissions.est_autorise', return_value=autorisee):
            reponse = self.client.get('/api/habilitations/comptes/')
        self.assertEqual(reponse.status_code, 200)

    def test_03_methode_verbe_distinct_porte_son_propre_code(self):
        # GET et POST n'exigent pas la même permission : le code vient de la méthode.
        vus = []

        def espion(user, code, **kwargs):
            vus.append(code)
            return DecisionAutorisation(permission=code, canal='WEB', mode='APPLICATION',
                                        gouverne=False, autorise=True)
        with mock.patch('habilitations.permissions.est_autorise', side_effect=espion):
            self.client.get('/api/habilitations/comptes/')
        self.assertEqual(vus, ['administration.compte.consulter'])
