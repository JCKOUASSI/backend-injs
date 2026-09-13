"""Aperçu Arena : cookies Partitioned (CHIPS) pour l'admin en iframe tierce.

Django 5.1 ne sait pas encore émettre l'attribut ``Partitioned``
(``SESSION_COOKIE_PARTITIONED`` / ``CSRF_COOKIE_PARTITIONED`` arrivent en
Django 5.2) et Python 3.11 ne connaît pas non plus cet attribut Morsel. Ce
middleware d'APERÇU (jamais utilisé en production) :

1. enregistre une fois ``partitioned`` comme attribut de cookie de type
   drapeau auprès de ``http.cookies.Morsel`` ;
2. ajoute ``Partitioned`` aux cookies de session et CSRF émis par Django,
   afin que le navigateur les stocke dans la partition de la page Arena
   intégratrice (*.arena.site) et les renvoie dans les requêtes de l'iframe
   (*.e2b.app). Sans Partitioned, les cookies sont stockés mais jamais
   renvoyés (« 403 CSRF cookie not set »).
"""
from http.cookies import Morsel

if "partitioned" not in Morsel._reserved:
    Morsel._reserved["partitioned"] = "Partitioned"
if "partitioned" not in Morsel._flags:
    Morsel._flags.add("partitioned")

# Noms définis par l'overlay (CSRF_COOKIE_NAME / SESSION_COOKIE_NAME).
_PARTITIONNABLES = {"injs_csrftoken", "injs_sessionid", "refresh_token"}


class PartitionedCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for nom, morsel in getattr(response, "cookies", {}).items():
            if nom in _PARTITIONNABLES:
                morsel["partitioned"] = True
        return response
