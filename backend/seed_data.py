"""
Script de seed pour créer des données de démonstration.
Usage: source venv/bin/activate && python manage.py shell < seed_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from formations.models import Formation, Participant, ModuleParticipant, QRToken
FormationParticipant = ModuleParticipant

User = get_user_model()

print("=" * 60)
print("  CRÉATION DES DONNÉES DE DÉMONSTRATION")
print("=" * 60)

# ──────────────────────────────────────────────
# 1. UTILISATEURS
# ──────────────────────────────────────────────

# Admin / Superuser DFRC
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@dfrc.gouv.fr',
        'first_name': 'Admin',
        'last_name': 'DFRC',
        'role': 'DFRC',
        'is_staff': True,
        'is_superuser': True,
    }
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print("✓ Admin DFRC créé (admin / admin123)")
else:
    print("→ Admin DFRC existe déjà")

# Utilisateur DFRC standard
dfrc_user, created = User.objects.get_or_create(
    username='dfrc',
    defaults={
        'email': 'direction@dfrc.gouv.fr',
        'first_name': 'Marie',
        'last_name': 'DUPONT',
        'role': 'DFRC',
        'is_staff': True,
    }
)
if created:
    dfrc_user.set_password('dfrc123')
    dfrc_user.save()
    print("✓ DFRC Marie DUPONT créée (dfrc / dfrc123)")
else:
    print("→ DFRC Marie DUPONT existe déjà")

# Superviseurs
superviseurs_data = [
    {'username': 'superviseur1', 'first_name': 'Jean', 'last_name': 'MARTIN',
     'email': 'jean.martin@dfrc.gouv.fr', 'telephone': '+33612345678'},
    {'username': 'superviseur2', 'first_name': 'Sophie', 'last_name': 'BERNARD',
     'email': 'sophie.bernard@dfrc.gouv.fr', 'telephone': '+33623456789'},
]

superviseurs = []
for s_data in superviseurs_data:
    sup, created = User.objects.get_or_create(
        username=s_data['username'],
        defaults={
            **s_data,
            'role': 'SUPERVISEUR',
        }
    )
    if created:
        sup.set_password('sup123')
        sup.save()
        print(f"✓ Superviseur {sup.get_full_name()} créé ({s_data['username']} / sup123)")
    else:
        print(f"→ Superviseur {sup.get_full_name()} existe déjà")
    superviseurs.append(sup)


# ──────────────────────────────────────────────
# 2. PARTICIPANTS
# ──────────────────────────────────────────────

participants_data = [
    {'matricule': 'P001', 'nom': 'DIALLO', 'prenom': 'Amadou', 'email': 'amadou@example.com', 'organisation': 'Ministère des Finances'},
    {'matricule': 'P002', 'nom': 'TRAORE', 'prenom': 'Fatou', 'email': 'fatou@example.com', 'organisation': 'Ministère de la Santé'},
    {'matricule': 'P003', 'nom': 'COULIBALY', 'prenom': 'Ibrahim', 'email': 'ibrahim@example.com', 'organisation': 'Ministère de l\'Éducation'},
    {'matricule': 'P004', 'nom': 'KEITA', 'prenom': 'Aminata', 'email': 'aminata@example.com', 'organisation': 'Ministère des Finances'},
    {'matricule': 'P005', 'nom': 'SYLLA', 'prenom': 'Moussa', 'email': 'moussa@example.com', 'organisation': 'Ministère de l\'Agriculture'},
    {'matricule': 'P006', 'nom': 'CAMARA', 'prenom': 'Mariama', 'email': 'mariama@example.com', 'organisation': 'Ministère de la Justice'},
    {'matricule': 'P007', 'nom': 'BARRY', 'prenom': 'Ousmane', 'email': 'ousmane@example.com', 'organisation': 'Ministère de la Santé'},
    {'matricule': 'P008', 'nom': 'SOW', 'prenom': 'Aissatou', 'email': 'aissatou@example.com', 'organisation': 'Ministère des Finances'},
    {'matricule': 'P009', 'nom': 'BALDE', 'prenom': 'Mamadou', 'email': 'mamadou@example.com', 'organisation': 'Ministère de l\'Éducation'},
    {'matricule': 'P010', 'nom': 'CONDE', 'prenom': 'Kadiatou', 'email': 'kadiatou@example.com', 'organisation': 'Ministère de l\'Agriculture'},
]

participants = []
for p_data in participants_data:
    part, created = Participant.objects.get_or_create(
        matricule=p_data['matricule'],
        defaults=p_data,
    )
    if created:
        print(f"✓ Participant {part.nom} {part.prenom} ({part.matricule}) créé")
    else:
        print(f"→ Participant {part.nom} {part.prenom} existe déjà")
    participants.append(part)


# ──────────────────────────────────────────────
# 3. FORMATIONS
# ──────────────────────────────────────────────

now = timezone.now()

formation1, created = Formation.objects.get_or_create(
    formation='Gestion de projet agile',
    defaults={
        'date_debut': now,
        'date_fin': now + timedelta(days=3),
        'statut': 'EN_COURS',
        'creee_par': dfrc_user,
        'superviseur': superviseurs[0],
        'superviseur_assigne_le': now,
        'categorie': 'A',
        'grade': 'A1',
    }
)
if created:
    print(f"\n✓ Formation '{formation1.formation}' créée")
else:
    print(f"→ Formation '{formation1.formation}' existe déjà")

formation2, created = Formation.objects.get_or_create(
    formation='Transformation digitale',
    defaults={
        'date_debut': now + timedelta(days=7),
        'date_fin': now + timedelta(days=9),
        'statut': 'PLANIFIEE',
        'creee_par': dfrc_user,
        'superviseur': superviseurs[1],
        'superviseur_assigne_le': now,
        'categorie': 'B',
        'grade': 'B1',
    }
)
if created:
    print(f"✓ Formation '{formation2.formation}' créée")
else:
    print(f"→ Formation '{formation2.formation}' existe déjà")

formation3, created = Formation.objects.get_or_create(
    formation='Leadership et management',
    defaults={
        'date_debut': now - timedelta(days=5),
        'date_fin': now - timedelta(days=3),
        'statut': 'TERMINEE',
        'creee_par': admin_user,
        'superviseur': superviseurs[0],
        'superviseur_assigne_le': now - timedelta(days=6),
        'categorie': 'A',
        'grade': 'A2',
    }
)
if created:
    print(f"✓ Formation '{formation3.formation}' créée")
else:
    print(f"→ Formation '{formation3.formation}' existe déjà")


# ──────────────────────────────────────────────
# 4. INSCRIPTIONS (participants attendus)
# ──────────────────────────────────────────────

# Formation 1 : tous les 10 participants
_mod1 = formation1.modules.order_by('ordre').first()
if _mod1:
    for p in participants:
        ModuleParticipant.objects.get_or_create(module=_mod1, participant=p)

# Formation 2 : 5 premiers
_mod2 = formation2.modules.order_by('ordre').first()
if _mod2:
    for p in participants[:5]:
        ModuleParticipant.objects.get_or_create(module=_mod2, participant=p)

# Formation 3 : 7 premiers
_mod3 = formation3.modules.order_by('ordre').first()
if _mod3:
    for p in participants[:7]:
        ModuleParticipant.objects.get_or_create(module=_mod3, participant=p)

print("\n✓ Inscriptions des participants aux formations effectuées")


# ──────────────────────────────────────────────
# 5. SESSION + QR TOKEN pour formation 1 (en cours)
# ──────────────────────────────────────────────
from formations.models import SessionFormation
_mod1 = formation1.modules.order_by('ordre').first()
seance1, _ = SessionFormation.objects.get_or_create(
    module=_mod1,
    date_journee=now.date(),
    numero=1,
    defaults={
        'demarree_le': now - timedelta(hours=3),
        'demarree_par': superviseurs[0],
    }
)
print(f"✓ Séance créée pour '{formation1.formation}'")

qr_token, created = QRToken.objects.get_or_create(
    session=seance1,
    actif=True,
    defaults={
        'genere_par': superviseurs[0],
        'expire_at': now + timedelta(hours=24),
    }
)
if created:
    print(f"✓ QR Token généré pour '{formation1.formation}': {qr_token.token}")
else:
    print(f"→ QR Token actif existe déjà: {qr_token.token}")


# ──────────────────────────────────────────────
# 6. QUELQUES POINTAGES pour la formation 1
# ──────────────────────────────────────────────

from presences.models import Pointage

# P001 : entré et sorti (TERMINE)
pt1, created = Pointage.objects.get_or_create(
    participant=participants[0],
    session=seance1,
    defaults={
        'timestamp_entree': now - timedelta(hours=3),
        'timestamp_sortie': now - timedelta(hours=0, minutes=30),
        'statut': 'TERMINE',
        'device_id': 'demo-device-001',
    }
)
if created:
    pt1.calculer_duree()
    pt1.save()
    print(f"✓ Pointage TERMINE pour {participants[0]} (durée: {pt1.duree_presence_minutes} min)")

# P002 : en salle (EN_COURS)
pt2, created = Pointage.objects.get_or_create(
    participant=participants[1],
    session=seance1,
    defaults={
        'timestamp_entree': now - timedelta(hours=1),
        'statut': 'EN_COURS',
        'device_id': 'demo-device-002',
    }
)
if created:
    print(f"✓ Pointage EN_COURS pour {participants[1]}")

# P003 : en salle (EN_COURS)
pt3, created = Pointage.objects.get_or_create(
    participant=participants[2],
    session=seance1,
    defaults={
        'timestamp_entree': now - timedelta(minutes=45),
        'statut': 'EN_COURS',
        'device_id': 'demo-device-003',
    }
)
if created:
    print(f"✓ Pointage EN_COURS pour {participants[2]}")

# P004-P010 : absents (pas de pointage)

print("\n" + "=" * 60)
print("  DONNÉES DE DÉMONSTRATION CRÉÉES AVEC SUCCÈS")
print("=" * 60)
print(f"""
COMPTES DE CONNEXION :
  DFRC Admin    : admin / admin123
  DFRC Standard : dfrc / dfrc123
  Superviseur 1 : superviseur1 / sup123
  Superviseur 2 : superviseur2 / sup123

FORMATION EN COURS : '{formation1.titre}'
  QR Token : {qr_token.token}
  Participants : 10 attendus, 3 pointés (1 terminé, 2 en salle)
  Numéros participants : P001 à P010

API ENDPOINTS PRINCIPAUX :
  POST /api/auth/login/
  GET  /api/formations/
  POST /api/scan/
  GET  /api/formations/<id>/dashboard/
""")
