"""Garde-fous des liens de la page d'accueil API (2026-10-10).

Demande utilisateur : « Impossible d'accéder aux différents liens de API Django
et particulièrement Administration Django ». Cause racine : les liens étaient
générés en « http:// » alors que la passerelle d'aperçu sert la page en https —
l'iframe bloque alors chaque clic comme contenu mixte.

Ces tests verrouillent :
1. les liens de la page HTML sont relatifs (schéma/hôte indépendants) ;
2. aucun lien « http:// » n'est servi depuis une page atteinte derrière une
   passerelle TLS (e2b.app / arena.site / trycloudflare.com) ;
3. le lien « Administration Django » pointe bien vers /admin/ et la fenêtre de
   connexion répond ;
4. le contrat JSON expose le schéma public réel (https derrière la passerelle).
"""
import re

from django.test import SimpleTestCase, TestCase, override_settings

HOTE_PASSERELLE = '8000-sandbox-test.e2b.app'


@override_settings(ALLOWED_HOSTS=['localhost', '127.0.0.1', '.e2b.app', '.arena.site', '.trycloudflare.com'])
class LiensAccueilApiTests(SimpleTestCase):
    """La page d'accueil HTML doit servir des liens cliquables partout."""

    def _page(self, **meta):
        # Le client de test envoie Accept: */* → la vue répondrait en JSON :
        # on demande explicitement la page HTML.
        entetes = {'HTTP_ACCEPT': 'text/html', **meta}
        reponse = self.client.get('/', HTTP_HOST=HOTE_PASSERELLE, **entetes)
        self.assertEqual(reponse.status_code, 200, reponse.content[:200])
        return reponse.content.decode('utf-8')

    def test_liens_html_relatifs(self):
        corps = self._page()
        hrefs = re.findall(r'href="([^"]+)"', corps)
        self.assertGreaterEqual(len(hrefs), 9)
        for href in hrefs:
            with self.subTest(href=href):
                # Relatif (chemin ou requête) ou https absolu — jamais http://.
                self.assertFalse(href.startswith('http://'), f'{href} est un lien http:// (contenu mixte)')
                self.assertTrue(
                    href.startswith('/') or href.startswith('?') or href.startswith('https://'),
                    f'{href} n’est ni relatif ni https',
                )

    def test_aucun_lien_http_derriere_passerelle_tls(self):
        corps = self._page()
        self.assertNotIn('http://', corps)

    def test_bouton_administration_pointe_vers_admin(self):
        corps = self._page()
        self.assertIn('Administration Django', corps)
        self.assertRegex(
            corps,
            r'<a href="/admin/">Administration Django</a>',
        )

    @override_settings(DEBUG=True)
    def test_aucun_lien_de_l_accueil_ne_repond_404(self):
        # Plainte du 2026-10-10 : « Impossible d'accéder aux différents liens ».
        # Chaque lien de la page doit aboutir (200/302/401/405 selon le
        # contrat) — jamais un 404 (lien mort) ni un 406 (négociation cassée).
        corps = self._page()
        cibles = [
            h for h in re.findall(r'href="([^"]+)"', corps)
            if h.startswith('/')
        ]
        self.assertGreaterEqual(len(cibles), 8)
        # En-tête Accept d'un vrai navigateur (avec repli */*).
        accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        for cible in cibles:
            with self.subTest(cible=cible):
                reponse = self.client.get(
                    cible, HTTP_HOST=HOTE_PASSERELLE, HTTP_ACCEPT=accept,
                )
                self.assertNotIn(
                    reponse.status_code, (404, 406),
                    f'{cible} répond {reponse.status_code} — lien cassé sur la page d’accueil.',
                )

    def test_liens_json_en_https_derriere_passerelle(self):
        reponse = self.client.get('/?format=json', HTTP_HOST=HOTE_PASSERELLE)
        self.assertEqual(reponse.status_code, 200)
        payload = reponse.json()
        for cle, url in (
            ('admin', payload['links']['admin']),
            ('documentation', payload['links']['documentation']),
            ('frontend', payload['links']['frontend']),
        ):
            with self.subTest(lien=cle):
                self.assertTrue(url.startswith('https://'), f'{cle} = {url}')

    def test_frontend_derive_le_port_3000_en_https(self):
        reponse = self.client.get('/?format=json', HTTP_HOST=HOTE_PASSERELLE)
        frontend = reponse.json()['links']['frontend']
        attendu = f'https://3000-{HOTE_PASSERELLE[len("8000-"):]}'
        self.assertEqual(frontend, attendu)


@override_settings(ALLOWED_HOSTS=['localhost', '127.0.0.1', '.e2b.app', '.arena.site', '.trycloudflare.com'])
class ParcoursAdministrationTests(TestCase):
    """Le parcours « Administration Django » doit fonctionner de bout en bout."""

    @override_settings(PREVIEW_AUTOLOGIN_ENABLED=False, DEBUG=True)
    def test_page_admin_accessible_depuis_accueil(self):
        accueil = self.client.get(
            '/', HTTP_HOST=HOTE_PASSERELLE, HTTP_ACCEPT='text/html',
        ).content.decode('utf-8')
        cible = re.search(r'href="([^"]+)"[^>]*>Administration Django', accueil).group(1)
        reponse = self.client.get(cible, HTTP_HOST=HOTE_PASSERELLE)
        # /admin/ redirige vers la fenêtre de connexion (auto-login désactivé).
        self.assertIn(reponse.status_code, (200, 302))
        if reponse.status_code == 302:
            reponse = self.client.get(reponse['Location'], HTTP_HOST=HOTE_PASSERELLE)
            self.assertEqual(reponse.status_code, 200)
        self.assertIn('csrfmiddlewaretoken', reponse.content.decode('utf-8'))


@override_settings(ALLOWED_HOSTS=['localhost', '127.0.0.1', '.e2b.app', '.arena.site', '.trycloudflare.com'])
class LiensOuvrentOngletPremierNiveauTests(TestCase):
    """Garde-fou : tout lien de l'accueil doit s'ouvrir hors iframe.

    Plainte du 2026-10-10 : « CSRF cookie not set » sur /admin/ depuis
    l'aperçu. Dans une iframe, les cookies tiers sont bloqués ; un lien en
    ``target="_blank"`` est bloqué silencieusement par l'iframe : interdit.
    """

    @override_settings(DEBUG=True)
    def test_chaque_lien_de_l_accueil_reste_dans_la_fenetre(self):
        reponse = self.client.get(
            '/', HTTP_HOST=HOTE_PASSERELLE, HTTP_ACCEPT='text/html',
        )
        # Liste de navigation uniquement (le pied de page JSON reste inchangé).
        liens = re.findall(r'<li><a [^>]*href="[^"]+"[^>]*>', reponse.content.decode())
        self.assertGreaterEqual(len(liens), 8)
        for lien in liens:
            with self.subTest(lien=lien):
                self.assertNotIn('target=', lien)
