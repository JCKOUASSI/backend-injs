"""Phase 2 — anti-escalade de privilèges (refonte « Utilisateurs & Accès »).

Vérifie, au niveau service (appelé par la console, les imports de masse et
l'API) :
- auto-modification des droits, du canal et du statut refusée ;
- élévation hiérarchique refusée (compte de rang supérieur) ;
- rôle sensible en direct refusé sur soi-même ou sur un pair (rang égal),
  autorisé sur un compte de rang inférieur ;
- chaque refus est tracé dans le journal (ACCES_REFUSE) et n'écrit rien ;
- les attributions non sensibles entre pairs restent autorisées.
"""
from django.test import TestCase

from habilitations.models import (
    AttributionRole,
    CompteUtilisateur,
    JournalHabilitation,
    RoleMetier,
)
from habilitations.services import comptes_admin as service
from habilitations.tests import _u5_fixtures as fx


class AntiEscaladeTests(TestCase):
    def setUp(self):
        fx.referentiel_charge()
        self.role_sensible = RoleMetier.objects.get(code='ADMIN_SYSTEME')
        self.role_banal = RoleMetier.objects.filter(sensible=False).first()
        self.admin = fx.admin('adm_p2', role='ADMIN')            # N4
        self.secretariat = fx.admin('sec_p2', role='SECRETARIAT')  # N2
        self.pair = fx.compte_curp('pair_p2', role_legacy='ADMIN', niveau='N4')
        self.bas = fx.compte_curp('bas_p2', role_legacy='SECRETARIAT', niveau='N2')
        # Profil CURP de l'acteur lui-même (même utilisateur que self.admin).
        self.compte_admin = CompteUtilisateur.objects.create(
            user=self.admin, statut=CompteUtilisateur.Statut.ACTIF,
            canal='WEB',
        )

    def _payload_roles(self, *codes):
        return {
            'roles': [{'role': c, 'niveau': 'N4', 'motif': 'Test P2'} for c in codes],
            'differential_accepte': True,
            'motif': 'Test P2',
        }

    def _nb_attributions(self, compte):
        return AttributionRole.objects.filter(
            compte=compte, statut=AttributionRole.Statut.ACTIVE).count()

    def _nb_refus(self, code):
        return JournalHabilitation.objects.filter(
            type_evenement=JournalHabilitation.TypeEvenement.ACCES_REFUSE,
            nouvelle_valeur__code=code,
        ).count()

    # --- auto-modification ---------------------------------------------------

    def test_01_auto_attribution_de_role_refusee_et_tracee(self):
        avant = self._nb_attributions(self.compte_admin)
        with self.assertRaises(service.ErreurConsole) as cm:
            service.modifier_compte(
                self.compte_admin, self.admin,
                self._payload_roles(self.role_banal.code),
            )
        self.assertEqual(cm.exception.code, 'AUTO_MODIFICATION_INTERDITE')
        self.assertEqual(cm.exception.statut, 403)
        self.assertEqual(self._nb_attributions(self.compte_admin), avant)
        self.assertEqual(self._nb_refus('AUTO_MODIFICATION_INTERDITE'), 1)

    def test_02_auto_changement_de_statut_refuse(self):
        with self.assertRaises(service.ErreurConsole) as cm:
            service.changer_statut(
                self.compte_admin, self.admin, 'suspendre', 'Test P2')
        self.assertEqual(cm.exception.code, 'AUTO_MODIFICATION_INTERDITE')
        self.compte_admin.refresh_from_db()
        self.assertEqual(self.compte_admin.statut, CompteUtilisateur.Statut.ACTIF)

    def test_03_auto_modification_sans_changement_reste_permise(self):
        # Mise à jour des seules notes : pas un droit, pas refusée.
        service.modifier_compte(
            self.compte_admin, self.admin, {'notes': 'RAS'})
        self.compte_admin.refresh_from_db()
        self.assertEqual(self.compte_admin.notes, 'RAS')

    # --- rang hiérarchique -----------------------------------------------------

    def test_04_escalade_hierarchique_refusee(self):
        # Un secrétariat (N2) ne peut pas attribuer un rôle à un administrateur (N4).
        with self.assertRaises(service.ErreurConsole) as cm:
            service.modifier_compte(
                self.pair, self.secretariat,
                self._payload_roles(self.role_banal.code),
            )
        self.assertEqual(cm.exception.code, 'ESCALADE_HIERARCHIQUE')
        self.assertEqual(self._nb_attributions(self.pair), 0)

    def test_05_creation_au_rang_superieur_refusee(self):
        payload = {
            'identifiants': {'username': 'nouveau_p2', 'role_legacy': 'ADMIN',
                             'mot_de_passe': 'Mot#2026x'},
            'roles': [],
        }
        with self.assertRaises(service.ErreurConsole) as cm:
            service.creer_compte(self.secretariat, payload)
        self.assertEqual(cm.exception.code, 'ESCALADE_HIERARCHIQUE')
        self.assertFalse(
            CompteUtilisateur.objects.filter(user__username='nouveau_p2').exists())

    # --- rôle sensible --------------------------------------------------------

    def test_06_role_sensible_direct_sur_pair_refuse(self):
        with self.assertRaises(service.ErreurConsole) as cm:
            service.modifier_compte(
                self.pair, self.admin, self._payload_roles(self.role_sensible.code))
        self.assertEqual(cm.exception.code, 'ROLE_SENSIBLE_DEMANDE_REQUISE')
        self.assertEqual(self._nb_attributions(self.pair), 0)
        self.assertEqual(self._nb_refus('ROLE_SENSIBLE_DEMANDE_REQUISE'), 1)

    def test_07_role_sensible_direct_sur_rang_inferieur_autorise(self):
        service.modifier_compte(
            self.bas, self.admin, self._payload_roles(self.role_sensible.code))
        self.assertEqual(self._nb_attributions(self.bas), 1)

    def test_08_role_non_sensible_entre_pairs_autorise(self):
        service.modifier_compte(
            self.pair, self.admin, self._payload_roles(self.role_banal.code))
        self.assertEqual(self._nb_attributions(self.pair), 1)

    def test_09_creation_role_sensible_pair_refusee(self):
        payload = {
            'identifiants': {'username': 'pair_cree_p2', 'role_legacy': 'ADMIN',
                             'mot_de_passe': 'Mot#2026x'},
            'roles': [{'role': self.role_sensible.code, 'niveau': 'N4',
                       'motif': 'Test P2'}],
        }
        with self.assertRaises(service.ErreurConsole) as cm:
            service.creer_compte(self.admin, payload)
        self.assertEqual(cm.exception.code, 'ROLE_SENSIBLE_DEMANDE_REQUISE')
        self.assertFalse(
            CompteUtilisateur.objects.filter(user__username='pair_cree_p2').exists())

    def test_10_sans_acteur_systeme_pas_de_garde(self):
        # Les sondes et tâches planifiées (acteur None) gardent leur comportement.
        service.modifier_compte(
            self.pair, None, self._payload_roles(self.role_sensible.code))
        self.assertEqual(self._nb_attributions(self.pair), 1)
