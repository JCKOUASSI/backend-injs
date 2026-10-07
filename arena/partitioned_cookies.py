"""Add the CHIPS ``Partitioned`` attribute to sandbox CSRF/session cookies.

Django 5.1 does not expose a cookie setting for this attribute. Python's
``http.cookies.Morsel`` also gained it after the runtime shipped with Django
5.1, so register the RFC attribute only when this sandbox-only middleware is
imported. Production settings never load this module.
"""
from http.cookies import Morsel

from django.conf import settings


# ``Partitioned`` is a boolean cookie flag. Registering the spelling keeps
# SimpleCookie's serializer correct on Python versions that predate CHIPS.
if "partitioned" not in Morsel._reserved:
    Morsel._reserved["partitioned"] = "Partitioned"
Morsel._flags.add("partitioned")


class PartitionedCookieMiddleware:
    """Partition only the dedicated preview session and CSRF cookies."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.cookie_names = {
            getattr(settings, "SESSION_COOKIE_NAME", "sessionid"),
            getattr(settings, "CSRF_COOKIE_NAME", "csrftoken"),
        }

    def __call__(self, request):
        response = self.get_response(request)
        for name in self.cookie_names:
            cookie = response.cookies.get(name)
            if cookie is None:
                continue
            same_site = (cookie["samesite"] or "").lower()
            if same_site == "none" and "secure" in cookie:
                cookie["partitioned"] = True
        return response
