from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

ROLE_LABELS = {
    'ADMIN': 'Administrateur',
    'DIRECTION': 'Direction',
    'CHEF_CPFAE_ADMIN': 'Chef CPFAE Admin',
    'CPFAE_ADMIN': 'CPFAE Admin',
    'CHEF_SECRETARIAT': 'Chef Secrétariat',
    'SECRETARIAT': 'Secrétariat',
    'ENCADRANT': 'Encadrant',
    'AUDITEUR': 'Auditeur',
}


def send_welcome_email(user, plain_password):
    """Envoie un email de bienvenue à l'utilisateur avec ses identifiants initiaux.
    Ne fait rien si l'utilisateur n'a pas d'adresse email renseignée."""
    if not user.email:
        return

    full_name = user.get_full_name() or user.username
    role_label = ROLE_LABELS.get(user.role, user.role)
    frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else ''

    subject = "Bienvenue sur QR Badge — Vos identifiants de connexion"

    message = f"""Bonjour {full_name},

Votre compte sur la plateforme QR Badge a été créé.

Voici vos identifiants de connexion :

  Identifiant : {user.username}
  Mot de passe : {plain_password}
  Rôle         : {role_label}

{"URL de connexion : " + frontend_url + "/login" if frontend_url else ""}

Pour des raisons de sécurité, veuillez changer votre mot de passe dès votre première connexion
(Menu → Changer mon mot de passe).

Cordialement,
L'équipe DFRC — QR Badge
"""

    html_message = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #1a3a5c; padding: 24px; border-radius: 8px 8px 0 0; text-align: center;">
    <h1 style="color: #fff; margin: 0; font-size: 1.4rem;">QR Badge — DFRC</h1>
    <p style="color: #cde; margin: 4px 0 0;">Gestion des présences</p>
  </div>
  <div style="background: #f9f9f9; padding: 28px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px;">
    <p>Bonjour <strong>{full_name}</strong>,</p>
    <p>Votre compte sur la plateforme <strong>QR Badge</strong> a été créé avec succès.</p>

    <div style="background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 20px; margin: 20px 0;">
      <h3 style="margin-top: 0; color: #1a3a5c;">Vos identifiants</h3>
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="padding: 8px 0; color: #666; width: 40%;">Identifiant</td>
          <td style="padding: 8px 0; font-weight: bold; font-family: monospace; font-size: 1.05rem;">{user.username}</td>
        </tr>
        <tr style="border-top: 1px solid #f0f0f0;">
          <td style="padding: 8px 0; color: #666;">Mot de passe</td>
          <td style="padding: 8px 0; font-weight: bold; font-family: monospace; font-size: 1.05rem;">{plain_password}</td>
        </tr>
        <tr style="border-top: 1px solid #f0f0f0;">
          <td style="padding: 8px 0; color: #666;">Rôle</td>
          <td style="padding: 8px 0;">{role_label}</td>
        </tr>
      </table>
    </div>

    {"<div style='text-align:center; margin: 24px 0;'><a href='" + frontend_url + "/login' style='background:#1a3a5c; color:#fff; padding:12px 28px; border-radius:6px; text-decoration:none; font-weight:bold;'>Se connecter</a></div>" if frontend_url else ""}

    <div style="background: #fff8e1; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 4px; margin-top: 16px;">
      <strong>⚠️ Sécurité</strong><br>
      Changez votre mot de passe dès votre première connexion via <em>Menu → Changer mon mot de passe</em>.
    </div>

    <p style="margin-top: 24px; color: #666; font-size: 0.9rem;">
      Cordialement,<br>
      <strong>L'équipe DFRC — QR Badge</strong>
    </p>
  </div>
</body>
</html>
"""

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
