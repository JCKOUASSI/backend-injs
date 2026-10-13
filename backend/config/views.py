import os
import re

from django.http import HttpResponse, JsonResponse

# Passerelles TLS de l'aperçu : le trafic y est TOUJOURS en https, même quand
# X-Forwarded-Proto n'est pas (ou est mal) propagé.
_HOTE_PASSERELLE = re.compile(r'\.(e2b\.app|arena\.site|trycloudflare\.com)$', re.I)


def _scheme(request):
    """Schéma public réel (https derrière les passerelles de l'aperçu).

    Garde-fou (2026-10-10) : les liens générés en « http:// » depuis une page
    servie en https sont bloqués comme contenu mixte par l'iframe d'aperçu —
    « impossible d'accéder aux liens de l'API, en particulier Administration
    Django ». Verrouillé par config/tests/test_liens_accueil_api.py.
    """
    if request.is_secure():
        return 'https'
    proto = request.headers.get('X-Forwarded-Proto', '').split(',')[0].strip().lower()
    if proto == 'https':
        return 'https'
    hote = (request.headers.get('X-Forwarded-Host') or request.get_host()).split(':')[0]
    return 'https' if _HOTE_PASSERELLE.search(hote) else 'http'


def _hote(request):
    return request.headers.get('X-Forwarded-Host') or request.get_host()


def _frontend_url(request):
    """URL du frontend canonique (port 3000, figé pour le projet).

    Priorité : variable ``FRONTEND_URL`` si elle est posée (production /
    Docker). Sinon on dérive l'hôte de la requête (ou de l'en-tête
    ``X-Forwarded-Host`` posé par le proxy d'aperçu) en remplaçant le port de
    l'API (8000) par celui du front (3000) — sans aucun identifiant codé en dur.
    """
    explicite = os.environ.get('FRONTEND_URL')
    if explicite:
        return explicite.rstrip('/')
    host = _hote(request)
    if host.startswith('8000-'):
        host = f'3000-{host[len("8000-"):]}'
    elif ':' in host:
        host = f'{host.split(":", 1)[0]}:3000'
    return f'{_scheme(request)}://{host}'


def _api_links(request):
    # Liens RELATIFS pour la page HTML : ils résolvent toujours, quel que soit
    # le schéma/hôte public de la passerelle (pas de contenu mixte en iframe).
    # Le contrat JSON reste en absolu mais avec le schéma public réel.
    base = f'{_scheme(request)}://{_hote(request)}'
    return {
        'application': 'INJS LMD API',
        'organisation': 'INJS — Institut National de la Jeunesse et des Sports',
        'version': '1.0',
        'links': {
            'frontend': _frontend_url(request),
            'documentation': f'{base}/api/v1/docs/',
            'schema': f'{base}/api/schema/',
            'admin': f'{base}/admin/',
            'dashboard': f'{base}/dashboard/',
            'auth': {
                'login': f'{base}/api/auth/login/',
                'me': f'{base}/api/auth/me/',
                'token_refresh': f'{base}/api/auth/token/refresh/',
            },
            'formations': f'{base}/api/formations/',
            'scolarite': f'{base}/api/scolarite/',
            'admissions': f'{base}/api/admissions/',
            'presences': f'{base}/api/scan/',
            'exports': f'{base}/api/exports/',
        },
        # Cibles relatives servies telles quelles par la page HTML.
        'routes': {
            'documentation': '/api/v1/docs/',
            'schema': '/api/schema/',
            'admin': '/admin/',
            'dashboard': '/dashboard/',
            'login': '/api/auth/login/',
            'formations': '/api/formations/',
            'presences': '/api/scan/',
            'exports': '/api/exports/',
        },
    }


def api_root(request):
    """Page d'accueil de l'API (JSON ou HTML selon Accept)."""
    payload = _api_links(request)
    accept = request.headers.get('Accept', '')
    wants_html = (
        'text/html' in accept
        and 'application/json' not in accept.split(',')[0].strip()
    ) or request.GET.get('format') == 'html'

    if not wants_html:
        return JsonResponse(payload)

    routes = payload['routes']
    rows = [
        ('Application web (React)', payload['links']['frontend']),
        ('Documentation API (Swagger)', routes['documentation']),
        ('Schéma OpenAPI', routes['schema']),
        ('Administration Django', routes['admin']),
        ('Dashboard Direction', routes['dashboard']),
        ('Connexion API', routes['login']),
        ('Formations', routes['formations']),
        ('Badgeage (scan QR)', routes['presences']),
        ('Exports PDF / Excel', routes['exports']),
    ]
    # Navigation dans la même fenêtre : dans l'aperçu (iframe), une nouvelle
    # fenêtre (target=_blank) est bloquée silencieusement, donc le lien ne
    # faisait rien. Les pages Django admin acceptent l'affichage dans l'aperçu.
    list_items = '\n'.join(
        f'        <li><a href="{url}">{label}</a></li>' for label, url in rows
    )
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{payload['application']}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
    p.sub {{ color: #555; margin-top: 0; }}
    ul {{ line-height: 1.8; padding-left: 1.25rem; }}
    a {{ color: #0b5cab; }}
    footer {{ margin-top: 2rem; font-size: 0.875rem; color: #666; }}
    code {{ background: #f4f4f4; padding: 0.1em 0.35em; border-radius: 3px; }}
  </style>
</head>
<body>
  <h1>{payload['application']}</h1>
  <p class="sub">{payload['organisation']}</p>
  <p>API REST — utilisez les liens ci-dessous ou l’application web pour vous connecter.</p>
  <ul>
{list_items}
  </ul>
  <footer>
    Réponse JSON : <code><a href="?format=json">{_scheme(request)}://{_hote(request)}/?format=json</a></code>
  </footer>
</body>
</html>"""
    return HttpResponse(html)
