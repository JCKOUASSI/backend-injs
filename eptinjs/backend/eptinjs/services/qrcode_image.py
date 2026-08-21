"""Rendu du QR de séance en PNG base64.

L'image est produite côté serveur — comme pour les QR étudiants d'INJS — afin
de ne rien ajouter aux dépendances du frontend.
"""
from __future__ import annotations

import base64
import io

import qrcode
from django.conf import settings

COULEUR_INJS = getattr(settings, 'INJS_PRIMARY_COLOR', '#0D47A1')


def origines_de_confiance() -> set[str]:
    """Origines déjà déclarées comme légitimes par le déploiement."""
    origines = set()
    for reglage in ('CORS_ALLOWED_ORIGINS', 'CSRF_TRUSTED_ORIGINS'):
        for origine in getattr(settings, reglage, None) or []:
            origine = (origine or '').strip().rstrip('/')
            if origine and '*' not in origine:
                origines.add(origine)
    return origines


def base_badgeage(request=None) -> str:
    """Origine du SPA, qu'ouvrira le téléphone en scannant le QR.

    L'API et le SPA peuvent être servis par deux hôtes distincts : l'origine
    utile est alors celle annoncée par le navigateur, pas celle de la requête.
    Elle n'est retenue que si le déploiement la déclare déjà de confiance, pour
    qu'un en-tête forgé ne puisse pas détourner le QR vers un site tiers.
    """
    base = (getattr(settings, 'EPTINJS_BADGE_BASE_URL', '') or '').rstrip('/')
    if base:
        return base
    if request is None:
        return ''
    origine = (request.headers.get('Origin') or '').strip().rstrip('/')
    if origine and origine in origines_de_confiance():
        return origine
    return request.build_absolute_uri('/').rstrip('/')


def url_badgeage(token_value, request=None) -> str:
    """URL encodée dans le QR, ouverte par le téléphone de l'étudiant."""
    return f'{base_badgeage(request)}/etudiant/presences?ept_token={token_value}'


def image_base64(contenu: str, *, taille: int = 10) -> str:
    qr = qrcode.QRCode(version=None, box_size=taille, border=3)
    qr.add_data(contenu)
    qr.make(fit=True)
    image = qr.make_image(fill_color=COULEUR_INJS, back_color='white')
    tampon = io.BytesIO()
    image.save(tampon, format='PNG')
    return base64.b64encode(tampon.getvalue()).decode('ascii')


def payload_qr(token, request=None) -> dict:
    """Bloc QR complet prêt à afficher (image, URL, contexte de séance)."""
    seance = token.seance
    url = url_badgeage(token.token, request)
    return {
        'token': str(token.token),
        'payload': str(token.token),
        'badge_url': url,
        'qr_image_base64': image_base64(url),
        'expires_at': token.expires_at.isoformat(),
        'is_active': token.is_active,
        'seance': str(seance.id),
        'course_code': seance.course.code,
        'course_name': seance.course.name,
        'promotion_name': seance.promotion.name,
        'groupe_code': seance.groupe.code if seance.groupe_id else None,
        'date': seance.date.isoformat(),
        'day_display': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'][
            seance.date.weekday()
        ],
        'start_time': seance.heure_debut.strftime('%H:%M'),
        'end_time': seance.heure_fin.strftime('%H:%M'),
        'room_code': seance.room.code if seance.room_id else None,
        'room_name': seance.room.name if seance.room_id else None,
        'statut': seance.statut,
    }
