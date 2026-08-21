"""Origine encodée dans les QR de séance.

Le téléphone qui scanne doit atterrir sur le SPA, y compris lorsque celui-ci
est servi par un autre hôte que l'API.
"""
from django.test import RequestFactory, SimpleTestCase, override_settings

from eptinjs.services.qrcode_image import base_badgeage, url_badgeage

SPA = 'https://injs.badge-qr-code.pro'
API = 'inj.badge-qr-code.pro'


class BaseBadgeageTests(SimpleTestCase):
    def setUp(self):
        self.fabrique = RequestFactory()

    def requete(self, **kwargs):
        return self.fabrique.get(
            '/api/v1/eptinjs/seances/x/qr/', SERVER_NAME=API, secure=True, **kwargs,
        )

    @override_settings(EPTINJS_BADGE_BASE_URL='', CORS_ALLOWED_ORIGINS=[SPA], CSRF_TRUSTED_ORIGINS=[])
    def test_deux_hotes_utilise_l_origine_du_spa(self):
        base = base_badgeage(self.requete(HTTP_ORIGIN=SPA))
        self.assertEqual(base, SPA)

    @override_settings(EPTINJS_BADGE_BASE_URL='', CORS_ALLOWED_ORIGINS=[SPA], CSRF_TRUSTED_ORIGINS=[])
    def test_origine_non_declaree_est_ignoree(self):
        base = base_badgeage(self.requete(HTTP_ORIGIN='https://pirate.example'))
        self.assertEqual(base, f'https://{API}')

    @override_settings(EPTINJS_BADGE_BASE_URL='', CORS_ALLOWED_ORIGINS=[SPA], CSRF_TRUSTED_ORIGINS=[])
    def test_hote_unique_retombe_sur_la_requete(self):
        base = base_badgeage(self.requete())
        self.assertEqual(base, f'https://{API}')

    @override_settings(EPTINJS_BADGE_BASE_URL='https://force.example', CORS_ALLOWED_ORIGINS=[SPA])
    def test_reglage_explicite_prioritaire(self):
        base = base_badgeage(self.requete(HTTP_ORIGIN=SPA))
        self.assertEqual(base, 'https://force.example')

    @override_settings(EPTINJS_BADGE_BASE_URL='', CORS_ALLOWED_ORIGINS=[SPA], CSRF_TRUSTED_ORIGINS=[])
    def test_url_complete_porte_le_jeton(self):
        url = url_badgeage('jeton-123', self.requete(HTTP_ORIGIN=SPA))
        self.assertEqual(url, f'{SPA}/etudiant/presences?ept_token=jeton-123')

    @override_settings(EPTINJS_BADGE_BASE_URL='', CORS_ALLOWED_ORIGINS=['*'], CSRF_TRUSTED_ORIGINS=[])
    def test_joker_n_autorise_pas_tout(self):
        base = base_badgeage(self.requete(HTTP_ORIGIN='https://pirate.example'))
        self.assertEqual(base, f'https://{API}')
