"""Phase 5 — accès effectifs d'un compte (refonte « Utilisateurs & Accès »).

Invariants vérifiés :
- une seule source de vérité : chaque décision affichée = ``est_autorise()`` ;
- un compte suspendu ne dispose d'aucun accès effectif, mais ses permissions
  restent visibles avec le motif de refus ;
- un rôle hors période (expiré) n'ouvre plus de droits ;
- l'endpoint est réservé à l'administration et tracé par les gardes existantes.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from habilitations.models import (
    AttributionRole,
    CompteUtilisateur,
    PermissionMetier,
    RoleMetier,
)
from habilitations.services.acces_effectifs import acces_effectifs
from habilitations.services.moteur import est_autorise
from habilitations.tests import _u5_fixtures as fx


def _role_avec_permissions():
    for role in RoleMetier.objects.filter(disponible=True).order_by('code'):
        if PermissionMetier.objects.filter(roles_octroyants=role).exists():
            return role
    raise AssertionError('Aucun rôle avec permissions dans le référentiel.')


class AccesEffectifsTests(TestCase):
    def setUp(self):
        fx.referentiel_charge()
        fx.ouvrir(fx.F_UI)
        self.role = _role_avec_permissions()
        self.codes_role = set(
            PermissionMetier.objects.filter(
                roles_octroyants=self.role,
            ).values_list('code', flat=True)
        )

    def test_01_candidats_issus_du_role(self):
        compte = fx.compte_curp('ae_actif', role_code=self.role.code)
        resultat = acces_effectifs(compte)
        codes = {p['code'] for p in resultat['permissions']}
        self.assertEqual(codes, self.codes_role)
        self.assertEqual(resultat['roles_actifs'][0]['code'], self.role.code)

    def test_02_source_unique_le_moteur_decide(self):
        compte = fx.compte_curp('ae_coherent', role_code=self.role.code)
        resultat = acces_effectifs(compte)
        for entree in resultat['permissions']:
            decision = est_autorise(compte.user, entree['code'], canal='WEB')
            self.assertEqual(entree['autorise'], bool(decision.autorise),
                             f"divergence sur {entree['code']}")
            self.assertEqual(entree['motifs'], list(decision.motifs))

    def test_025_compte_actif_obtient_des_acces_effectifs(self):
        # Garde-fou : la vue n'est pas trivialement fermée pour un compte actif.
        compte = fx.compte_curp('ae_actif_ok', role_code=self.role.code)
        resultat = acces_effectifs(compte)
        self.assertGreater(resultat['synthese']['autorisees'], 0,
                           f"motifs : {[p['motifs'] for p in resultat['permissions']][:5]}")

    def test_03_compte_suspendu_sans_acces_effectif(self):
        compte = fx.compte_curp(
            'ae_suspendu', role_code=self.role.code,
            statut=CompteUtilisateur.Statut.SUSPENDU,
        )
        resultat = acces_effectifs(compte)
        self.assertEqual(resultat['statut_compte'], CompteUtilisateur.Statut.SUSPENDU)
        self.assertEqual(resultat['synthese']['autorisees'], 0)
        self.assertGreater(resultat['synthese']['refusees'], 0)
        self.assertEqual(resultat['modules_accessibles'], [])

    def test_04_role_expire_n_ouvre_plus_de_droits(self):
        compte = fx.compte_curp('ae_expire', role_code=self.role.code)
        attribution = AttributionRole.objects.get(compte=compte, role=self.role)
        attribution.date_debut = timezone.localdate() - timedelta(days=30)
        attribution.date_fin = timezone.localdate() - timedelta(days=1)
        attribution.save()
        resultat = acces_effectifs(compte)
        self.assertEqual(resultat['roles_actifs'], [])
        self.assertEqual(
            [r['code'] for r in resultat['roles_hors_periode']], [self.role.code])
        self.assertEqual(resultat['permissions'], [])
        self.assertEqual(resultat['synthese']['autorisees'], 0)

    def test_05_module_accessible_derive_des_autorisations(self):
        compte = fx.compte_curp('ae_modules', role_code=self.role.code)
        resultat = acces_effectifs(compte)
        modules_autorises = {p['module'] for p in resultat['permissions'] if p['autorise']}
        self.assertEqual(set(resultat['modules_accessibles']), modules_autorises)


class AccesEffectifsApiTests(TestCase):
    def setUp(self):
        fx.referentiel_charge()
        fx.ouvrir(fx.F_UI)
        self.role = _role_avec_permissions()
        self.admin = fx.admin('adm_ae', role='ADMIN')
        self.client = APIClient()

    def test_01_admin_obtient_la_vue(self):
        compte = fx.compte_curp('ae_api', role_code=self.role.code)
        self.client.force_authenticate(self.admin)
        reponse = self.client.get(f'/api/habilitations/comptes/{compte.pk}/acces-effectifs/')
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('permissions', reponse.data)
        self.assertIn('modules_accessibles', reponse.data)

    def test_02_utilisateur_non_admin_refuse(self):
        compte = fx.compte_curp('ae_refus', role_code=self.role.code)
        non_admin = fx.admin('ae_secretariat', role='SECRETARIAT')
        self.client.force_authenticate(non_admin)
        reponse = self.client.get(f'/api/habilitations/comptes/{compte.pk}/acces-effectifs/')
        self.assertEqual(reponse.status_code, 403)

    def test_03_compte_inconnu_404(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.get('/api/habilitations/comptes/999999/acces-effectifs/')
        self.assertEqual(reponse.status_code, 404)

    def test_04_non_authentifie_refuse(self):
        compte = fx.compte_curp('ae_anonyme', role_code=self.role.code)
        reponse = self.client.get(f'/api/habilitations/comptes/{compte.pk}/acces-effectifs/')
        self.assertIn(reponse.status_code, (401, 403))


class ImpactUtilisateurCoherenceTests(TestCase):
    """impact_utilisateur (écran Accès effectifs) doit refléter la décision backend."""

    def setUp(self):
        fx.referentiel_charge()
        fx.ouvrir(fx.F_UI)
        self.role = _role_avec_permissions()

    def test_01_impact_suit_acces_effectifs(self):
        from habilitations.services import impact
        compte = fx.compte_curp('imp_actif', role_code=self.role.code)
        attendu = {p['code'] for p in acces_effectifs(compte)['permissions'] if p['autorise']}
        donnees = impact.impact_utilisateur(compte.user_id)
        self.assertEqual(donnees['total_effectives'], len(attendu))
        self.assertEqual(
            {c for r in donnees['roles'] for c in r['permissions']}, attendu)

    def test_02_compte_suspendu_sans_effectif_dans_impact(self):
        from habilitations.services import impact
        compte = fx.compte_curp(
            'imp_suspendu', role_code=self.role.code,
            statut=CompteUtilisateur.Statut.SUSPENDU,
        )
        donnees = impact.impact_utilisateur(compte.user_id)
        self.assertEqual(donnees['total_effectives'], 0)
        self.assertEqual(donnees['modules_effectifs'], [])
        self.assertEqual(
            [c for r in donnees['roles'] for c in r['permissions']], [])
