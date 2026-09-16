"""Aperçu Arena : auto-connexion démo pour l'admin en vignette."""
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
        # Redirection de la racine vers l'admin pour ouvrir directement le tableau de bord
        if request.path == "/":
            return redirect("/admin/")

        # Permettre l'accès direct et l'affichage fidèle de la page de connexion
        if request.path.startswith("/admin/login"):
            setattr(request, "_dont_enforce_csrf_checks", True)
            if request.method == "POST":
                utilisateur = self._compte_demo()
                if utilisateur is not None:
                    if hasattr(request, "session"):
                        login(request, utilisateur, backend="django.contrib.auth.backends.ModelBackend")
                        next_url = request.POST.get("next") or request.GET.get("next") or "/admin/"
                        return redirect(next_url)
            return self.get_response(request)

        if request.path.startswith("/admin"):
            utilisateur = self._compte_demo()
            user = getattr(request, "user", None)
            if utilisateur is not None and (user is None or not user.is_authenticated):
                if hasattr(request, "session"):
                    login(request, utilisateur,
                          backend="django.contrib.auth.backends.ModelBackend")
        return self.get_response(request)
