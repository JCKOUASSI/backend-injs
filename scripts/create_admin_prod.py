#!/usr/bin/env python
"""
Crée ou réinitialise le compte admin en production
Usage:
  - En local dev: python manage.py shell < scripts/create_admin_prod.py
  - En prod Docker: docker compose exec backend python manage.py shell < scripts/create_admin_prod.py
  - Ou: docker compose exec backend python scripts/create_admin_prod.py

Variables d'env utilisées si présentes:
  DJANGO_SUPERUSER_USERNAME (défaut: admin)
  DJANGO_SUPERUSER_EMAIL (défaut: admin@injs.local)
  DJANGO_SUPERUSER_PASSWORD (défaut: admin123)

Ce script est idempotent: il crée l'admin s'il n'existe pas, sinon réinitialise son mot de passe
et ses droits.
"""
import os
import sys
import django

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_BACKEND = os.path.join(_ROOT, 'backend')
for p in (_ROOT, _BACKEND):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@injs.local')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

print("=== Création / réinitialisation admin prod ===")
print(f"Username: {username}")
print(f"Email: {email}")
print(f"Password: {'*' * len(password)} (longueur {len(password)})")

existing = User.objects.filter(username=username).first()
if existing:
    print(f"Utilisateur {username} existe déjà (id={existing.id})")
    print(f"  is_superuser: {existing.is_superuser}")
    print(f"  is_staff: {existing.is_staff}")
    print(f"  is_active: {existing.is_active}")
    print(f"  role: {existing.role}")
    print("  -> Réinitialisation mot de passe et droits...")
    existing.set_password(password)
    existing.email = email
    existing.is_superuser = True
    existing.is_staff = True
    existing.is_active = True
    if hasattr(existing, 'role'):
        existing.role = getattr(User.Role, 'ADMIN', 'ADMIN')
    existing.save()
    print(f"✅ Admin {username} réinitialisé avec mot de passe {password}")
else:
    print(f"Utilisateur {username} n'existe pas, création...")
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role=getattr(User.Role, 'ADMIN', 'ADMIN') if hasattr(User, 'Role') else None
        )
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        print(f"✅ Superutilisateur {username} créé avec succès")
    except Exception as e:
        print(f"❌ Erreur création superuser: {e}")
        try:
            User.objects.filter(username=username).delete()
            user = User(
                username=username,
                email=email,
                is_superuser=True,
                is_staff=True,
                is_active=True,
            )
            if hasattr(user, 'role'):
                user.role = getattr(User.Role, 'ADMIN', 'ADMIN')
            user.set_password(password)
            user.save()
            print(f"✅ Superutilisateur {username} créé via fallback")
        except Exception as e2:
            print(f"❌ Fallback échoué: {e2}")
            sys.exit(1)

u = User.objects.get(username=username)
print("\n=== Vérification finale ===")
print(f"Username: {u.username}")
print(f"Email: {u.email}")
print(f"is_superuser: {u.is_superuser}")
print(f"is_staff: {u.is_staff}")
print(f"is_active: {u.is_active}")
if hasattr(u, 'role'):
    print(f"role: {u.role}")
print(f"Peut se connecter au web: {u.is_active and u.is_staff}")

from django.contrib.auth import authenticate
auth_user = authenticate(username=username, password=password)
if auth_user:
    print(f"✅ Authentification réussie pour {username}/{password}")
else:
    print(f"❌ Authentification échouée pour {username}/{password}")

print(f"\n=== Total utilisateurs: {User.objects.count()} ===")
for user in User.objects.all()[:10]:
    print(f"  - {user.username} ({user.email}) superuser={user.is_superuser} staff={user.is_staff} role={getattr(user, 'role', 'N/A')}")

print("\n✅ Script terminé.")
