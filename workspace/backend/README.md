# QR Badge — Système de gestion des présences par QR code

**DFRC** — Direction de la Formation et du Renforcement des Compétences

## Architecture

Ce projet est séparé en deux parties :
- **Backend** : Django 5.x + Django REST Framework (API), base **PostgreSQL**
- **Frontend** : React 18 + Vite (Dashboard web)

```
qr-badge/
├── config/              # Django configuration
├── authentication/       # Auth app (users, JWT)
├── formations/           # Formations, participants, formateurs
├── presences/           # Pointages, scans QR
├── exports/             # PDF/Excel exports
├── dashboard/           # Django templates (legacy web UI)
├── frontend/            # React frontend (NOUVEAU)
│   ├── src/
│   │   ├── pages/       # React components
│   │   ├── context/     # Auth context
│   │   └── services/    # API service
│   └── package.json
├── qr_badge_mobile/     # Flutter mobile app
└── requirements.txt
```

## Stack technique

- **Backend** : Django 5.1 + Django REST Framework + PostgreSQL (`POSTGRES_*` dans `.env`)
- **Frontend** : React 18 + Vite + React Router
- **Auth** : JWT (djangorestframework-simplejwt)
- **Exports** : reportlab (PDF) + openpyxl (Excel)

## Installation rapide (Backend + Frontend)

```bash
# 1. Backend Django
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed_data.py
python manage.py runserver 0.0.0.0:8001  # Accessible sur le réseau local

# 2. Frontend React (dans un autre terminal)
cd frontend
npm install
npm run dev
```

Le frontend sera disponible sur `http://localhost:3000` et communiquera avec le backend Django via l'API.

## Comptes de démonstration

| Rôle | Username | Mot de passe |
|------|----------|-------------|
| Administrateur | `admin` | `admin123` |
| CPFAE Admin | `dfrc` | `dfrc123` |
| Chef CPFAE Admin | `jckouassi` | `JckPcm@123` |
| INJS Admin | `injs` | `injs123` |
| Secrétariat | `secretariat` | `sec123` |
| Encadrant 1 | `superviseur1` | `sup123` |
| Encadrant 2 | `superviseur2` | `sup123` |

Participants : numéros `P001` à `P010` (pas besoin de compte pour scanner)

## API Endpoints

### Authentification
- `POST /api/auth/login/` — Connexion (retourne JWT)
- `POST /api/auth/token/refresh/` — Rafraîchir le token
- `GET /api/auth/me/` — Profil utilisateur connecté

### DFRC (web)
- `GET/POST /api/formations/` — Lister / créer des formations
- `GET/PUT/DELETE /api/formations/{id}/` — Détail formation
- `POST /api/formations/{id}/assign-superviseur/` — Assigner superviseur
- `POST /api/formations/{id}/participants/add/` — Inscrire participant
- `DELETE /api/formations/{id}/participants/{pid}/remove/` — Retirer participant
- `GET/POST /api/formations/participants/` — CRUD participants
- `GET /api/formations/{id}/dashboard/` — Dashboard temps réel
- `GET /api/formations/{id}/presences/` — Liste présences
- `POST /api/formations/{id}/force-pointage/` — Pointage forcé
- `GET /api/exports/formation/{id}/pdf/` — Export PDF
- `GET /api/exports/formation/{id}/excel/` — Export Excel

### Superviseur (tablette)
- `GET /api/formations/superviseur/` — Mes formations
- `GET /api/formations/superviseur/{id}/` — Détail formation
- `POST /api/formations/superviseur/{id}/generate-qr/` — Générer QR
- `GET /api/formations/superviseur/{id}/qr/` — QR actif

### Participant (mobile)
- `POST /api/scan/` — Scanner QR (entrée OU sortie) — endpoint public
- `POST /api/scan/secure/` — Scanner QR sécurisé (anti-fraude, auth JWT requise)
- `GET /api/me/historique/` — Historique personnel du user connecté
- `GET /api/participant/{id}/historique/` — Historique personnel (ancien)
- `GET /api/participant/lookup/?numero=P001` — Recherche par numéro

## Logique du scan (`POST /api/scan/`)

```json
{ "token_qr": "uuid", "numero_participant": "P001", "device_id": "device-123" }
```

1. Vérifie token QR valide (non expiré, actif)
2. Vérifie participant existant + inscrit à la formation
3. 1er scan → **ENTREE** | 2e scan → **SORTIE** (durée calculée serveur)

## Scan sécurisé — anti-fraude (`POST /api/scan/secure/`)

```json
{ "token_qr": "uuid", "device_id": "MOBILE_ANDROID" }
```

- **Auth JWT requise** — le participant doit être connecté
- Le numéro est **automatiquement déduit** du profil lié au compte
- Impossible de badger pour quelqu'un d'autre

---

## App Mobile Flutter (`qr_badge_mobile/`)

Application Flutter pour participants et formateurs. Anti-fraude : le badgeage est lié au compte connecté.

### Installation

```bash
cd qr_badge_mobile
flutter pub get
```

### Lancer sur un appareil/émulateur

```bash
# 1. Démarrer le serveur Django (accessible sur le réseau local)
python manage.py runserver 0.0.0.0:8001

# 2. Créer les comptes mobile (si pas encore fait)
python manage.py shell < scripts/seed_mobile_users.py

# 3. Lancer l'app Flutter
cd qr_badge_mobile
flutter run
```

### Comptes mobile de démonstration

| Rôle | Username | Mot de passe | Nom |
|------|----------|-------------|-----|
| Participant | `p001` à `p010` | même valeur que l'identifiant | Participants P001 à P010 |
| Formateur | `f001` à `f003` | même valeur que l'identifiant | Formateurs F001 à F003 |

### Configuration serveur

Au login, cliquer « Configurer le serveur » pour saisir l'IP LAN du serveur Django (ex: `http://192.168.1.x:8001`).

### Fonctionnalités

- **Login** — authentification JWT
- **Scanner QR** — caméra arrière, détection automatique
- **Anti-fraude** — le numéro est lié au compte, pas de badgeage par procuration
- **Historique** — liste des pointages par jour avec durées
