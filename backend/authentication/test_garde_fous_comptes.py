"""Garde-fous comptes — suppression définitive SygepCPFAE / Responsable CPFAE.

Demande du 2026-10-10 : « supprimer tous les comptes concernant Sygepcpfae ou
Responsable CPFAE (partout) ». Les comptes témoins historiques
``temoin_cpfae_admin`` / ``temoin_chef_cpfae_admin`` ont été renommés
``temoin_injs_admin`` / ``temoin_chef_injs_admin`` ; le compte démo ``dfrc``
(« Responsable CPFAE ») a été supprimé du seed.

Ces tests empêchent toute réintroduction, dans les listes de comptes gérées par
le dépôt :
* les 14 comptes témoins (``creer_comptes_temoins.COMPTES``) ;
* les témoins de fumée (``fumee_authentification.TEMOINS_WEB`` / ``TEMOINS_MOBILE``) ;
* le seed de démonstration (``backend/seed_data.py``).

Le pendant front (plaquettes de la page de connexion) est verrouillé par
``frontend/src/pages/Login.test.jsx`` (« garde-fou : aucune plaquette démo… »).
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from authentication.management.commands.creer_comptes_temoins import COMPTES
from authentication.management.commands.fumee_authentification import TEMOINS_MOBILE, TEMOINS_WEB

INTERDITS = re.compile(r'sygep|cpfae|dfrc', re.IGNORECASE)


class ComptesTemoinsTests(SimpleTestCase):
    """Aucun compte témoin ne porte la marque CPFAE/Sygep/dfrc."""

    def test_comptes_temoins_sans_marque_interdite(self):
        noms = [c[0] for c in COMPTES]
        for nom in noms:
            with self.subTest(compte=nom):
                self.assertIsNone(INTERDITS.search(nom))

    def test_temoins_fumee_sans_marque_interdite(self):
        noms = [t[0] for t in TEMOINS_WEB] + [t[0] for t in TEMOINS_MOBILE]
        for nom in noms:
            with self.subTest(compte=nom):
                self.assertIsNone(INTERDITS.search(nom))

    def test_couverture_smoke_conservee(self):
        # La refonte a renommé, pas supprimé : la couverture des rôles admin
        # doit rester complète dans les deux listes.
        roles = {t[1] for t in TEMOINS_WEB}
        self.assertIn('CHEF_INJS_ADMIN', roles)
        self.assertIn('INJS_ADMIN', roles)


class SeedDemonstrationTests(SimpleTestCase):
    """Aucun compte du seed ne recrée un profil CPFAE/Sygep/dfrc."""

    # Un compte = username / email / first_name / last_name du seed. Les
    # mentions non comptables (statut métier « FORCE_DFRC », classes CSS
    # badge-dfrc, composant legacy PointJournalierCPFAE) ne sont PAS des
    # comptes et restent hors périmètre de suppression.
    IDENTIFIANTS = re.compile(
        r"username\s*=\s*['\"]([^'\"]*)['\"]"
        r"|email\s*=\s*['\"]([^'\"]*)['\"]"
        r"|first_name\s*=\s*['\"]([^'\"]*)['\"]"
        r"|last_name\s*=\s*['\"]([^'\"]*)['\"]"
        r"|reset_demo_user\(\s*['\"]([^'\"]*)['\"]",
    )

    def test_seed_data_sans_compte_interdit(self):
        source = (Path(settings.BASE_DIR) / 'seed_data.py').read_text(encoding='utf-8')
        for m in self.IDENTIFIANTS.finditer(source):
            for valeur in m.groups():
                if not valeur:
                    continue
                with self.subTest(identifiant=valeur):
                    self.assertIsNone(
                        INTERDITS.search(valeur),
                        f'backend/seed_data.py recrée un compte interdit : {valeur!r}.',
                    )
