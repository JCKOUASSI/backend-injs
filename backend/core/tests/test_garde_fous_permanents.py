"""Garde-fous permanents — admin Django joignable depuis la passerelle (2026-10-10).

Cités par ``frontend/src/pages/Login.jsx`` (commentaire COMPTES_DEMO) et par
``arena/settings_sandbox.py``. Ils empêchent la régression des deux pannes
validées par l'utilisateur le 2026-10-10 :

1. « Le bouton Administration ne fonctionne pas » : /admin doit être joignable
   avec l'hôte public de la passerelle (ALLOWED_HOSTS), sans être avalé par le
   fallback SPA ;
2. « Impossible de se connecter à la fenêtre de connexion de l'admin Django » :
   la vraie fenêtre doit s'afficher (PREVIEW_AUTOLOGIN_ENABLED = False) et le
   POST ``admin/admin123`` doit passer la vérification CSRF depuis l'origine
   publique (CSRF_TRUSTED_ORIGINS).

Le profil d'aperçu est recopié par ``arena/bootstrap.sh`` après chaque
réinitialisation du sandbox : les deux fichiers sont donc verrouillés en
lockstep (convention déjà en place dans
``config/tests/test_apercu_hardening.py``).
"""
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

REPO = settings.BASE_DIR.parent
OVERLAY = REPO / 'arena' / 'settings_sandbox.py'
BOOTSTRAP = REPO / 'arena' / 'bootstrap.sh'

HOTE_PASSERELLE = 'sbx-demo.arena.site'
ORIGINE_PASSERELLE = f'https://{HOTE_PASSERELLE}'


def _lire(chemin):
    return chemin.read_text(encoding='utf-8')


class PasserelleApercuTests(SimpleTestCase):
    """Listes hôtes/origines du profil d'aperçu et de son générateur."""

    SUFFIXES_HOTE = ('.e2b.app', '.arena.site', '.trycloudflare.com')
    ORIGINES = ('https://*.e2b.app', 'https://*.arena.site', 'https://*.trycloudflare.com')

    def test_hotes_passerelle_autorises(self):
        from arena import settings_sandbox as sbx
        for suffixe in self.SUFFIXES_HOTE:
            with self.subTest(suffixe=suffixe):
                self.assertIn(suffixe, sbx.ALLOWED_HOSTS)

    def test_origines_passerelle_dans_csrf_trusted(self):
        from arena import settings_sandbox as sbx
        for origine in self.ORIGINES:
            with self.subTest(origine=origine):
                self.assertIn(origine, sbx.CSRF_TRUSTED_ORIGINS)

    def test_hotes_et_origines_lockstep_avec_le_generateur(self):
        # bootstrap.sh recopie le profil après chaque reset : sans lockstep,
        # les correctifs disparaissent silencieusement.
        contenu = _lire(BOOTSTRAP)
        for suffixe in self.SUFFIXES_HOTE:
            with self.subTest(suffixe=suffixe):
                self.assertIn(f'"{suffixe}"', contenu)
        for origine in self.ORIGINES:
            with self.subTest(origine=origine):
                self.assertIn(f'"{origine}"', contenu)

    def test_vraie_fenetre_connexion_admin(self):
        # L'auto-connexion d'aperçu court-circuite la fenêtre de connexion :
        # elle doit rester désactivée dans le profil ET son générateur.
        from arena import settings_sandbox as sbx
        self.assertIs(sbx.PREVIEW_AUTOLOGIN_ENABLED, False)
        for profil in (OVERLAY, BOOTSTRAP):
            with self.subTest(profil=profil.name):
                self.assertIn('PREVIEW_AUTOLOGIN_ENABLED = False', _lire(profil))


class ConnexionAdminDepuisPasserelleTests(TestCase):
    """Comportement réel : GET /api, GET /admin/login/, POST admin/admin123."""

    def setUp(self):
        User = get_user_model()
        # Patron de authentication/apps.py (création du compte admin).
        User.objects.create_superuser(
            username='admin', email='admin@injs.ci', password='admin123',
            role=User.Role.ADMIN,
        )

    def _client_csrf(self):
        return Client(enforce_csrf_checks=True)

    # DEBUG=True : convention de config/tests/test_apercu_hardening.py (le
    # stockage staticfiles manifest des tests ne sert pas les assets admin).

    @override_settings(PREVIEW_AUTOLOGIN_ENABLED=False, DEBUG=True)
    def test_api_accessible_avec_hote_passerelle(self):
        reponse = self.client.get(
            '/api/',
            HTTP_HOST=HOTE_PASSERELLE,
            HTTP_X_FORWARDED_PROTO='https',
        )
        self.assertEqual(reponse.status_code, 200, reponse.content[:200])

    @override_settings(PREVIEW_AUTOLOGIN_ENABLED=False, DEBUG=True)
    def test_admin_login_affiche_le_vrai_formulaire(self):
        reponse = self.client.get(
            '/admin/login/',
            HTTP_HOST=HOTE_PASSERELLE,
            HTTP_X_FORWARDED_PROTO='https',
        )
        self.assertEqual(reponse.status_code, 200, reponse.content[:200])
        corps = reponse.content.decode('utf-8')
        self.assertIn('csrfmiddlewaretoken', corps)
        self.assertIn('INJS', corps)
        # Le fallback SPA (React #root) ne doit jamais servir /admin/…
        self.assertNotIn('id="root"', corps)

    @override_settings(PREVIEW_AUTOLOGIN_ENABLED=False, DEBUG=True)
    def test_connexion_admin_123_depuis_origine_passerelle(self):
        client = self._client_csrf()
        page = client.get(
            '/admin/login/',
            HTTP_HOST=HOTE_PASSERELLE,
            HTTP_X_FORWARDED_PROTO='https',
            HTTP_ORIGIN=ORIGINE_PASSERELLE,
        )
        self.assertEqual(page.status_code, 200)
        jeton = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', page.content.decode('utf-8'),
        ).group(1)

        reponse = client.post(
            '/admin/login/',
            {
                'username': 'admin',
                'password': 'admin123',
                'next': '/admin/',
                'csrfmiddlewaretoken': jeton,
            },
            HTTP_HOST=HOTE_PASSERELLE,
            HTTP_X_FORWARDED_PROTO='https',
            HTTP_ORIGIN=ORIGINE_PASSERELLE,
        )
        self.assertEqual(reponse.status_code, 302, reponse.content[:200])
        # Connexion réellement établie : la page d'accueil admin s'ouvre.
        suite = client.get(
            '/admin/',
            HTTP_HOST=HOTE_PASSERELLE,
            HTTP_X_FORWARDED_PROTO='https',
        )
        self.assertEqual(suite.status_code, 200)
        self.assertIn('INJS LMD', suite.content.decode('utf-8'))

    @override_settings(PREVIEW_AUTOLOGIN_ENABLED=False, DEBUG=True)
    def test_connexion_admin_passe_le_csrf_via_proxy_vite(self):
        # Trajet réel derrière le proxy vite : Django reçoit Host 127.0.0.1:8000
        # (changeOrigin) mais l'origine du navigateur est la passerelle publique.
        # C'est CSRF_TRUSTED_ORIGINS (wildcard) qui doit absorber l'écart.
        client = self._client_csrf()
        page = client.get(
            '/admin/login/',
            HTTP_HOST='127.0.0.1:8000',
            HTTP_X_FORWARDED_PROTO='https',
        )
        self.assertEqual(page.status_code, 200)
        jeton = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', page.content.decode('utf-8'),
        ).group(1)

        reponse = client.post(
            '/admin/login/',
            {
                'username': 'admin',
                'password': 'admin123',
                'next': '/admin/',
                'csrfmiddlewaretoken': jeton,
            },
            HTTP_HOST='127.0.0.1:8000',
            HTTP_X_FORWARDED_PROTO='https',
            HTTP_ORIGIN=ORIGINE_PASSERELLE,
        )
        self.assertEqual(
            reponse.status_code, 302,
            f'CSRF refusé depuis la passerelle ? body={reponse.content[:200]!r}',
        )
