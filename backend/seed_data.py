"""
Script de seed — données de démonstration SYGEP-CPFAE.
Usage: python seed_data.py  (depuis backend/ avec venv activé)
"""
import os
import django
from datetime import timedelta, date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from formations.models import (
    Formation, Module, Participant, Formateur,
    ModuleParticipant, SessionModule,
)
from presences.models import Pointage

from statistiques.models import ConfigAlerteSeuil

User = get_user_model()
now  = timezone.now()

print("=" * 60)
print("  CRÉATION DES DONNÉES DE DÉMONSTRATION")
print("=" * 60)

# ── 1. Utilisateurs ──────────────────────────────────────────
admin_user, c = User.objects.get_or_create(username='admin', defaults={
    'email': 'admin@cpfae.gouv.ci', 'first_name': 'Admin', 'last_name': 'CPFAE',
    'role': 'ADMIN', 'is_staff': True, 'is_superuser': True,
})
if c: admin_user.set_password('admin123'); admin_user.save()
print(f"{'✓' if c else '→'} admin")

jck, c = User.objects.get_or_create(username='jckouassi', defaults={
    'email': 'jck@cpfae.gouv.ci', 'first_name': 'Jean-Claude', 'last_name': 'Kouassi',
    'role': 'CHEF_CPFAE_ADMIN', 'is_staff': True, 'is_superuser': True,
})
if c: jck.set_password('JckPcm@123'); jck.save()
print(f"{'✓' if c else '→'} jckouassi")

dfrc_user, c = User.objects.get_or_create(username='dfrc', defaults={
    'email': 'dfrc@cpfae.gouv.ci', 'first_name': 'Marie', 'last_name': 'DUPONT',
    'role': 'CPFAE_ADMIN', 'is_staff': True,
})
if c: dfrc_user.set_password('dfrc123'); dfrc_user.save()
print(f"{'✓' if c else '→'} dfrc")

superviseurs = []
for d in [
    {'username': 'superviseur1', 'first_name': 'Jean',   'last_name': 'MARTIN',  'email': 'jean.martin@cpfae.gouv.ci'},
    {'username': 'superviseur2', 'first_name': 'Sophie', 'last_name': 'BERNARD', 'email': 'sophie.bernard@cpfae.gouv.ci'},
]:
    u, c = User.objects.get_or_create(username=d['username'], defaults={**d, 'role': 'ENCADRANT'})
    if c: u.set_password('sup123'); u.save()
    print(f"{'✓' if c else '→'} {d['username']}")
    superviseurs.append(u)

# ── 2. Participants ───────────────────────────────────────────
participants_data = [
    {'matricule': 'P001', 'nom': 'DIALLO',    'prenom': 'Amadou',   'sexe': 'MASCULIN', 'categorie': 'A', 'grade': 'A1', 'vague': 'PREMIERE VAGUE',  'type_concours': 'Concours direct'},
    {'matricule': 'P002', 'nom': 'TRAORE',    'prenom': 'Fatou',    'sexe': 'FEMININ',  'categorie': 'B', 'grade': 'B2', 'vague': 'PREMIERE VAGUE',  'type_concours': 'Concours direct'},
    {'matricule': 'P003', 'nom': 'COULIBALY', 'prenom': 'Ibrahim',  'sexe': 'MASCULIN', 'categorie': 'A', 'grade': 'A2', 'vague': 'DEUXIEME VAGUE',  'type_concours': 'Concours professionnel'},
    {'matricule': 'P004', 'nom': 'KEITA',     'prenom': 'Aminata',  'sexe': 'FEMININ',  'categorie': 'C', 'grade': 'C1', 'vague': 'PREMIERE VAGUE',  'type_concours': 'Concours direct'},
    {'matricule': 'P005', 'nom': 'SYLLA',     'prenom': 'Moussa',   'sexe': 'MASCULIN', 'categorie': 'B', 'grade': 'B1', 'vague': 'DEUXIEME VAGUE',  'type_concours': 'Concours professionnel'},
    {'matricule': 'P006', 'nom': 'CAMARA',    'prenom': 'Mariama',  'sexe': 'FEMININ',  'categorie': 'A', 'grade': 'A3', 'vague': 'TROISIEME VAGUE', 'type_concours': 'Examen professionnel'},
    {'matricule': 'P007', 'nom': 'BARRY',     'prenom': 'Ousmane',  'sexe': 'MASCULIN', 'categorie': 'C', 'grade': 'C2', 'vague': 'PREMIERE VAGUE',  'type_concours': 'Concours direct'},
    {'matricule': 'P008', 'nom': 'SOW',       'prenom': 'Aissatou', 'sexe': 'FEMININ',  'categorie': 'B', 'grade': 'B3', 'vague': 'DEUXIEME VAGUE',  'type_concours': 'Examen professionnel'},
    {'matricule': 'P009', 'nom': 'BALDE',     'prenom': 'Mamadou',  'sexe': 'MASCULIN', 'categorie': 'A', 'grade': 'A1', 'vague': 'TROISIEME VAGUE', 'type_concours': 'Concours professionnel'},
    {'matricule': 'P010', 'nom': 'CONDE',     'prenom': 'Kadiatou', 'sexe': 'FEMININ',  'categorie': 'C', 'grade': 'C1', 'vague': 'PREMIERE VAGUE',  'type_concours': 'Concours direct'},
]
participants = []
for d in participants_data:
    p, c = Participant.objects.get_or_create(matricule=d['matricule'], defaults=d)
    if c: print(f"  ✓ Participant {p.nom} {p.prenom}")
    participants.append(p)

# ── 3. Formateurs ─────────────────────────────────────────────
formateurs_data = [
    {'numerobadge': 'F001', 'nom': 'KONÉ',    'prenom': 'Seydou',  'specialite': 'Management public'},
    {'numerobadge': 'F002', 'nom': 'OUÉDRAOGO','prenom': 'Alima',  'specialite': 'Finances publiques'},
    {'numerobadge': 'F003', 'nom': 'NDIAYE',  'prenom': 'Ibrahima','specialite': 'Droit administratif'},
]
formateurs = []
for d in formateurs_data:
    f, c = Formateur.objects.get_or_create(numerobadge=d['numerobadge'], defaults=d)
    if c: print(f"  ✓ Formateur {f.nom} {f.prenom}")
    formateurs.append(f)

# ── 4. Formations + Modules ───────────────────────────────────
formations_data = [
    {'formation': 'Formation en Administration de Base (FAB) — Vague 1', 'numero_formation': 1},
    {'formation': 'Formation en Administration Complémentaire (FAC) — Vague 2', 'numero_formation': 2},
    {'formation': 'Formation en Finances Publiques', 'numero_formation': 3},
]
formations = []
for d in formations_data:
    f, c = Formation.objects.get_or_create(formation=d['formation'], defaults=d)
    if c: print(f"\n  ✓ Formation '{f.formation}'")
    formations.append(f)

# Modules pour chaque formation
modules_par_formation = [
    [
        {'intitule': 'Déontologie de la Fonction Publique', 'ordre': 1, 'grade': 'A1', 'groupe': 'GROUPE 1', 'vague': 'PREMIERE VAGUE', 'duree_prevue_heures': 20, 'statut': 'TERMINEE'},
        {'intitule': 'Droit Administratif Général',         'ordre': 2, 'grade': 'A2', 'groupe': 'GROUPE 2', 'vague': 'PREMIERE VAGUE', 'duree_prevue_heures': 30, 'statut': 'EN_COURS'},
        {'intitule': 'Gestion des Ressources Humaines',     'ordre': 3, 'grade': 'B1', 'groupe': 'GROUPE 3', 'vague': 'DEUXIEME VAGUE', 'duree_prevue_heures': 25, 'statut': 'PLANIFIEE'},
    ],
    [
        {'intitule': 'Leadership et management public',     'ordre': 1, 'grade': 'A1', 'groupe': 'GROUPE 1', 'vague': 'DEUXIEME VAGUE', 'duree_prevue_heures': 15, 'statut': 'TERMINEE'},
        {'intitule': 'Communication institutionnelle',      'ordre': 2, 'grade': 'B2', 'groupe': 'GROUPE 2', 'vague': 'DEUXIEME VAGUE', 'duree_prevue_heures': 18, 'statut': 'EN_COURS'},
    ],
    [
        {'intitule': 'Comptabilité publique',               'ordre': 1, 'grade': 'C1', 'groupe': 'GROUPE 1', 'vague': 'PREMIERE VAGUE', 'duree_prevue_heures': 35, 'statut': 'PLANIFIEE'},
    ],
]

all_modules = []
for i, formation in enumerate(formations):
    for md in modules_par_formation[i]:
        module, c = Module.objects.get_or_create(
            formation=formation, intitule=md['intitule'],
            defaults={
                **md,
                'formateur': formateurs[i % len(formateurs)],
                'superviseur': superviseurs[i % len(superviseurs)],
                'creee_par': dfrc_user,
                'date_debut': (now - timedelta(days=10)).date() if md['statut'] in ('TERMINEE','EN_COURS') else (now + timedelta(days=5)).date(),
                'date_fin':   (now - timedelta(days=2)).date()  if md['statut'] == 'TERMINEE' else (now + timedelta(days=10)).date(),
            }
        )
        if c: print(f"    ✓ Module '{module.intitule}'")
        all_modules.append(module)

# ── 5. Inscriptions ───────────────────────────────────────────
print("\n  Inscriptions participants → modules…")
for i, module in enumerate(all_modules):
    # Inscrire un sous-ensemble de participants par module
    subset = participants[: max(3, 10 - i)]
    for p in subset:
        ModuleParticipant.objects.get_or_create(module=module, participant=p)

# ── 6. Sessions ───────────────────────────────────────────────
print("  Création des séances…")
sessions = []
for i, module in enumerate(all_modules[:4]):  # 4 premiers modules
    jour = (now - timedelta(days=3 - i)).date() if module.statut in ('TERMINEE', 'EN_COURS') else now.date()
    session, c = SessionModule.objects.get_or_create(
        module=module, date_journee=jour, numero=1,
        defaults={
            'intitule': 'Matin',
            'heure_debut_prevue': None,
            'demarree_le':  (now - timedelta(days=3-i, hours=3)) if module.statut in ('TERMINEE','EN_COURS') else None,
            'terminee_le':  (now - timedelta(days=3-i, hours=1)) if module.statut == 'TERMINEE' else None,
            'demarree_par': superviseurs[0],
        }
    )
    if c: print(f"    ✓ Séance — {module.intitule} ({jour})")
    sessions.append(session)

# ── 7. Pointages ─────────────────────────────────────────────
print("  Création des pointages…")
STATUTS_DEMO = ['TERMINE', 'TERMINE', 'TERMINE', 'EN_COURS', 'ABSENT_NON_BADGE', 'TERMINE', 'SORTIE_AUTO', 'TERMINE', 'EN_COURS', 'ABSENT_NON_BADGE']
for i, session in enumerate(sessions):
    inscrits = list(ModuleParticipant.objects.filter(module=session.module).select_related('participant'))
    for j, mp in enumerate(inscrits[:8]):
        statut = STATUTS_DEMO[(i + j) % len(STATUTS_DEMO)]
        entree = session.demarree_le or (now - timedelta(hours=3))
        sortie = (entree + timedelta(hours=2)) if statut in ('TERMINE', 'SORTIE_AUTO', 'FORCE_DFRC') else None
        pt, c = Pointage.objects.get_or_create(
            participant=mp.participant, session=session,
            defaults={
                'timestamp_entree': entree + timedelta(minutes=j*5),
                'timestamp_sortie': sortie,
                'statut': statut,
                'device_id': f'demo-device-{j+1:03d}',
                'duree_presence_minutes': 120 if sortie else None,
            }
        )
        if c: print(f"    ✓ Pointage {statut} — {mp.participant.nom}")

# ── 8. Seuils d'alertes Statistiques ───────────────────────────
print("  Configuration des seuils d'alertes…")
SEUILS_DEMO = {
    'taux_presence':        {'seuil_avertissement': 75, 'seuil_critique': 60},
    'taux_absence':         {'seuil_avertissement': 20, 'seuil_critique': 35},
    'taux_abandon':         {'seuil_avertissement': 10, 'seuil_critique': 20},
    'taux_execution_vh':    {'seuil_avertissement': 70, 'seuil_critique': 50},
    'nb_absences_notoires': {'seuil_avertissement': 50, 'seuil_critique': 100},
    'saturation_groupe':    {'seuil_avertissement': 80, 'seuil_critique': 95},
}
for code, vals in SEUILS_DEMO.items():
    _, c = ConfigAlerteSeuil.objects.get_or_create(indicateur=code, defaults={**vals, 'actif': True})
    if c: print(f"    ✓ Seuil {code}")

print("\n" + "=" * 60)
print("  SEED TERMINÉ avec succès !")
print("=" * 60)
