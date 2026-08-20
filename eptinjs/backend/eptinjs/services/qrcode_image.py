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


def url_badgeage(token_value, request=None) -> str:
    """URL encodée dans le QR, ouverte par le téléphone de l'étudiant."""
    base = getattr(settings, 'EPTINJS_BADGE_BASE_URL', '') or ''
    if not base and request is not None:
        base = request.build_absolute_uri('/').rstrip('/')
    return f'{base}/etudiant/presences?ept_token={token_value}'


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
