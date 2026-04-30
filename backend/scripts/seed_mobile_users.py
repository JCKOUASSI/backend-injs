"""
Crée des comptes utilisateur pour les participants et formateurs de démo.
Génère des mots de passe aléatoires uniques (anti-fraude).
Usage: source venv/bin/activate && python manage.py shell < scripts/seed_mobile_users.py
"""
import os
import sys
import string
import random
import django

# Ajouter le dossier racine du projet au path (nécessaire en exécution directe)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from formations.models import Participant, Formateur

User = get_user_model()


def _gen_password(username, length=6):
    """Génère un mot de passe numérique déterministe basé sur le username.
    Le même username donne toujours le même mot de passe."""
    rng = random.Random(f'qrbadge-2025-{username}')
    return ''.join(rng.choices(string.digits, k=length))


print("=" * 60)
print("  CRÉATION DES COMPTES MOBILE (mots de passe aléatoires)")
print("=" * 60)

credentials = []

# ── Comptes pour les participants ──
for p in Participant.objects.all():
    username = p.numero.lower()
    password = _gen_password(username)

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': p.prenom,
            'last_name': p.nom,
            'email': p.email or '',
            'role': User.Role.AUDITEUR,
        }
    )

    # Toujours réinitialiser le mot de passe (force un nouveau à chaque run)
    user.set_password(password)
    user.save()

    if p.user != user:
        p.user = user
        p.save(update_fields=['user'])

    label = "créé" if created else "màj"
    print(f"  ✓ {p.prenom} {p.nom} ({username} / {password}) — {label}")
    credentials.append({
        'type': 'Participant',
        'nom': f'{p.prenom} {p.nom}',
        'username': username,
        'password': password,
    })

# ── Comptes pour les formateurs ──
for f in Formateur.objects.all():
    username = f.numerobadge.lower()
    password = _gen_password(username)

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': f.prenom,
            'last_name': f.nom,
            'email': f.email or '',
            'role': User.Role.AUDITEUR,
        }
    )

    user.set_password(password)
    user.save()

    if f.user != user:
        f.user = user
        f.save(update_fields=['user'])

    label = "créé" if created else "màj"
    print(f"  ✓ {f.prenom} {f.nom} ({username} / {password}) — {label}")
    credentials.append({
        'type': 'Formateur',
        'nom': f'{f.prenom} {f.nom}',
        'username': username,
        'password': password,
    })

# ── Fichier imprimable pour distribution ──
creds_file = os.path.join(os.environ.get('PWD', os.getcwd()), 'credentials_mobile.txt')
with open(creds_file, 'w') as fh:
    fh.write("=" * 50 + "\n")
    fh.write("  IDENTIFIANTS APP MOBILE QR BADGE\n")
    fh.write("  Code superviseur déconnexion : 2025\n")
    fh.write("=" * 50 + "\n\n")
    for c in credentials:
        fh.write(f"  {c['type']:12s} | {c['nom']:30s} | {c['username']:20s} | {c['password']}\n")
    fh.write("\n" + "=" * 50 + "\n")
    fh.write("  NE PAS PARTAGER — chaque code est personnel.\n")
    fh.write("=" * 50 + "\n")

print("\n" + "=" * 60)
print("  COMPTES MOBILE CRÉÉS — mots de passe aléatoires")
print("=" * 60)
print(f"\n  Fichier d'identifiants : {creds_file}")
print("  Imprimez ce fichier et distribuez chaque ligne au participant concerné.")
print("  Code superviseur pour déconnexion : 2025")
print()
