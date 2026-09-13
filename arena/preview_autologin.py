"""Aperçu Arena : auto-connexion démo pour l'admin en vignette.

UNIQUEMENT pour l'overlay d'aperçu bac-à-sable (``arena/settings_sandbox.py``) —
ce module n'est jamais référencé par ``config/settings.py`` de production.

Contexte : la passerelle d'aperçu Arena filtre les en-têtes ``Cookie`` entre
son point d'entrée (*.arena.site) et le bac à sable (*.e2b.app). Aucune
authentification Django par cookie (session + jeton CSRF) ne peut donc y
fonctionner dans les vignettes, ce qui se manifeste par un éternel
« 403 CSRF cookie not set » ou une page de login qui reboucle.

Ce middleware (process_request exécuté APRÈS AuthenticationMiddleware, car
ajouté en fin de pile) authentifie à chaque requête les chemins ``/admin/``
comme compte démo ``admin`` — sans aucun cookie, donc insensible au filtrage
de la passerelle. Chaque requête est ainsi traitée comme une session neuve
automatisée ; la redirection depuis ``/admin/login/`` évite le formulaire de
connexion condamné.

Limite connue : les actions admin d'écriture soumises par formulaire restent
soumises à la vérification CSRF cookie (elles échoueraient pareillement sans
celui-ci) ; l'aperçu admin est donc fonctionnel en consultation et sur les
écrans de démo prévus, pas pour des modifications via l'admin Django.
"""
import logging

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

logger = logging.getLogger("arena.preview_autologin")


class AutoLoginApercuMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._utilisateur = None  # cache par processus du compte démo

    def _compte_demo(self):
        if self._utilisateur is None:
            nom = getattr(settings, "PREVIEW_AUTOLOGIN_USERNAME", "admin")
            try:
                self._utilisateur = get_user_model().objects.get(username=nom)
            except get_user_model().DoesNotExist:
                logger.warning("Auto-connexion aperçu : compte démo %r absent", nom)
                self._utilisateur = False
        return self._utilisateur or None

    def __call__(self, request):
        if request.path.startswith("/admin"):
            utilisateur = self._compte_demo()
            if utilisateur is not None and not request.user.is_authenticated:
                login(request, utilisateur,
                      backend="django.contrib.auth.backends.ModelBackend")
            if request.path.startswith("/admin/login"):
                return redirect("/admin/")
        return self.get_response(request)
