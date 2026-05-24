from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Couleurs alignées sur frontend/src/index.css (:root --ci-*, --text-*)
_CI_ORANGE = '#F57C00'
_CI_ORANGE_DARK = '#E65100'
_CI_GREEN = '#43A047'
_CI_GREEN_DARK = '#388E3C'
_CI_LIGHT = '#FFF8F0'
_TEXT_PRIMARY = '#1e293b'
_TEXT_SECONDARY = '#64748b'
_BORDER = '#e2e8f0'
_CARD_BG = '#ffffff'
_FONT = "'Segoe UI', system-ui, -apple-system, sans-serif"

ROLE_LABELS = {
    'ADMIN': 'Administrateur',
    'DIRECTION': 'Direction',
    'CHEF_CPFAE_ADMIN': 'Chef CPFAE Admin',
    'CPFAE_ADMIN': 'CPFAE Admin',
    'CHEF_SECRETARIAT': 'Chef Secrétariat',
    'SECRETARIAT': 'Secrétariat',
    'FINANCE': 'Finance',
    'ENCADRANT': 'Encadrant',
    'AUDITEUR': 'Auditeur',
}


def _html_email_shell(*, title: str, subtitle: str, inner: str) -> str:
    """Enveloppe HTML commune (charte SYGEP-CPFAE / frontend)."""
    return f"""
<!DOCTYPE html>
<html lang="fr">
<body style="margin:0; padding:24px 12px; background:{_CI_LIGHT}; font-family:{_FONT}; color:{_TEXT_PRIMARY};">
  <div style="max-width:600px; margin:0 auto;">
    <div style="background:linear-gradient(180deg, {_CI_GREEN_DARK} 0%, {_CI_GREEN} 100%); background-color:{_CI_GREEN_DARK}; padding:24px; border-radius:12px 12px 0 0; text-align:center; border-bottom:3px solid {_CI_ORANGE};">
      <h1 style="color:#fff; margin:0; font-size:1.35rem; font-weight:700;">{title}</h1>
      <p style="color:rgba(255,255,255,0.88); margin:8px 0 0; font-size:0.9rem;">{subtitle}</p>
    </div>
    <div style="background:{_CARD_BG}; padding:28px; border:1px solid {_BORDER}; border-top:none; border-radius:0 0 12px 12px; box-shadow:0 4px 24px rgba(0,0,0,0.06);">
      {inner}
    </div>
  </div>
</body>
</html>
"""


def _html_cta_button(href: str, label: str) -> str:
    return (
        f"<div style='text-align:center; margin:24px 0;'>"
        f"<a href='{href}' style='display:inline-block; background:{_CI_ORANGE}; color:#fff; "
        f"padding:12px 28px; border-radius:10px; text-decoration:none; font-weight:600; "
        f"font-size:1rem; border:1px solid {_CI_ORANGE_DARK};'>"
        f"{label}</a></div>"
    )


def send_welcome_email(user, plain_password):
    """Envoie un email de bienvenue à l'utilisateur avec ses identifiants initiaux.
    Ne fait rien si l'utilisateur n'a pas d'adresse email renseignée."""
    if not user.email:
        return

    full_name = user.get_full_name() or user.username
    role_label = ROLE_LABELS.get(user.role, user.role)
    frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else ''

    subject = "Bienvenue sur SYGEP-CPFAE — Vos identifiants de connexion"

    message = f"""Bonjour {full_name},

Votre compte sur la plateforme SYGEP-CPFAE a été créé.

Voici vos identifiants de connexion :

  Identifiant : {user.username}
  Mot de passe : {plain_password}
  Rôle         : {role_label}

{"URL de connexion : " + frontend_url + "/login" if frontend_url else ""}

Pour des raisons de sécurité, veuillez changer votre mot de passe dès votre première connexion
(Menu → Changer mon mot de passe).

Cordialement,
L'équipe DFRC — SYGEP-CPFAE
"""

    cta = _html_cta_button(frontend_url + '/login', 'Se connecter') if frontend_url else ''

    inner = f"""
    <p style="margin:0 0 12px; line-height:1.6;">Bonjour <strong>{full_name}</strong>,</p>
    <p style="margin:0 0 20px; color:{_TEXT_SECONDARY}; line-height:1.6;">Votre compte sur la plateforme <strong style="color:{_TEXT_PRIMARY};">SYGEP-CPFAE</strong> a été créé avec succès.</p>

    <div style="background:{_CI_LIGHT}; border:1px solid {_BORDER}; border-radius:10px; padding:20px; margin:20px 0;">
      <h3 style="margin:0 0 16px; color:{_CI_GREEN_DARK}; font-size:1.05rem;">Vos identifiants</h3>
      <table style="width:100%; border-collapse:collapse;">
        <tr>
          <td style="padding:10px 0; color:{_TEXT_SECONDARY}; width:40%;">Identifiant</td>
          <td style="padding:10px 0; font-weight:700; font-family:ui-monospace,monospace; font-size:1.02rem; color:{_TEXT_PRIMARY};">{user.username}</td>
        </tr>
        <tr style="border-top:1px solid {_BORDER};">
          <td style="padding:10px 0; color:{_TEXT_SECONDARY};">Mot de passe</td>
          <td style="padding:10px 0; font-weight:700; font-family:ui-monospace,monospace; font-size:1.02rem; color:{_TEXT_PRIMARY};">{plain_password}</td>
        </tr>
        <tr style="border-top:1px solid {_BORDER};">
          <td style="padding:10px 0; color:{_TEXT_SECONDARY};">Rôle</td>
          <td style="padding:10px 0; color:{_TEXT_PRIMARY};">{role_label}</td>
        </tr>
      </table>
    </div>

    {cta}

    <div style="background:#FFF3E0; border-left:4px solid {_CI_ORANGE_DARK}; padding:14px 18px; border-radius:8px; margin-top:8px;">
      <strong style="color:{_CI_ORANGE_DARK};">Sécurité</strong><br>
      <span style="color:{_TEXT_PRIMARY}; font-size:0.95rem; line-height:1.5;">Changez votre mot de passe dès votre première connexion via <em>Menu → Changer mon mot de passe</em>.</span>
    </div>

    <p style="margin-top:28px; color:{_TEXT_SECONDARY}; font-size:0.9rem; line-height:1.5;">
      Cordialement,<br>
      <strong style="color:{_TEXT_PRIMARY};">L'équipe DFRC — SYGEP-CPFAE</strong>
    </p>
    """

    html_message = _html_email_shell(
        title='SYGEP-CPFAE — DFRC',
        subtitle='Gestion des présences',
        inner=inner,
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Email de bienvenue envoyé à %s (%s)", user.email, user.username)
    except Exception as exc:
        logger.error("Échec envoi email à %s : %s", user.email, exc)


def send_suspect_heartbeat_email(encadrant, personne_nom, personne_numero, formation_titre, module_intitule, seance_label, silence_minutes):
    """Notifie l'encadrant d'un module qu'un auditeur n'envoie plus de signal de présence
    depuis `silence_minutes` minutes et est passé en statut HORS_LIGNE_SUSPECT."""
    if not encadrant or not encadrant.email:
        return

    encadrant_nom = encadrant.get_full_name() or encadrant.username
    frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else ''

    subject = f"[SYGEP-CPFAE] Alerte présence — {personne_nom} hors ligne ({silence_minutes} min)"

    message = f"""Bonjour {encadrant_nom},

Une alerte de présence nécessite votre vérification.

L'auditeur suivant n'a plus envoyé de signal depuis {silence_minutes} minutes :

  Nom      : {personne_nom}
  Badge N° : {personne_numero}
  Module   : {module_intitule}
  Séance   : {seance_label}

Son statut est passé à « Hors ligne — suspect ». Veuillez vérifier sa présence physique en salle.

{"Tableau de bord : " + frontend_url if frontend_url else ""}

Cordialement,
L'équipe DFRC — SYGEP-CPFAE
"""

    cta = _html_cta_button(frontend_url, 'Accéder au tableau de bord') if frontend_url else ''

    inner = f"""
    <p style="margin:0 0 16px; line-height:1.6;">Bonjour <strong>{encadrant_nom}</strong>,</p>

    <div style="background:#FFF3E0; border-left:4px solid {_CI_ORANGE_DARK}; padding:16px 20px; border-radius:8px; margin-bottom:22px;">
      <strong style="font-size:1.05rem; color:{_CI_ORANGE_DARK};">Auditeur hors ligne depuis {silence_minutes} minutes</strong>
    </div>

    <div style="background:{_CI_LIGHT}; border:1px solid {_BORDER}; border-radius:10px; padding:20px; margin:20px 0;">
      <h3 style="margin:0 0 16px; color:{_CI_GREEN_DARK}; font-size:1.05rem;">Informations</h3>
      <table style="width:100%; border-collapse:collapse;">
        <tr>
          <td style="padding:10px 0; color:{_TEXT_SECONDARY}; width:40%;">Auditeur</td>
          <td style="padding:10px 0; font-weight:700; color:{_TEXT_PRIMARY};">{personne_nom}</td>
        </tr>
        <tr style="border-top:1px solid {_BORDER};">
          <td style="padding:10px 0; color:{_TEXT_SECONDARY};">Badge N°</td>
          <td style="padding:10px 0; font-family:ui-monospace,monospace; color:{_TEXT_PRIMARY};">{personne_numero}</td>
        </tr>
        <tr style="border-top:1px solid {_BORDER};">
          <td style="padding:10px 0; color:{_TEXT_SECONDARY};">Module</td>
          <td style="padding:10px 0; color:{_TEXT_PRIMARY};">{module_intitule}</td>
        </tr>
        <tr style="border-top:1px solid {_BORDER};">
          <td style="padding:10px 0; color:{_TEXT_SECONDARY};">Séance</td>
          <td style="padding:10px 0; color:{_TEXT_PRIMARY};">{seance_label}</td>
        </tr>
        <tr style="border-top:1px solid {_BORDER};">
          <td style="padding:10px 0; color:{_TEXT_SECONDARY};">Silence</td>
          <td style="padding:10px 0; color:{_CI_ORANGE_DARK}; font-weight:700;">{silence_minutes} minutes sans signal</td>
        </tr>
      </table>
    </div>

    <p style="margin:0 0 8px; color:{_TEXT_PRIMARY}; line-height:1.6;">Veuillez vérifier la présence physique de cet auditeur en salle.</p>

    {cta}

    <p style="margin-top:28px; color:{_TEXT_SECONDARY}; font-size:0.9rem; line-height:1.5;">
      Cordialement,<br>
      <strong style="color:{_TEXT_PRIMARY};">L'équipe DFRC — SYGEP-CPFAE</strong>
    </p>
    """

    html_message = _html_email_shell(
        title='SYGEP-CPFAE — DFRC',
        subtitle='Alerte de présence',
        inner=inner,
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[encadrant.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(
            "Alerte heartbeat envoyée à l'encadrant %s pour %s",
            encadrant.email, personne_nom,
        )
    except Exception as exc:
        logger.error("Échec envoi alerte heartbeat à %s : %s", encadrant.email, exc)
