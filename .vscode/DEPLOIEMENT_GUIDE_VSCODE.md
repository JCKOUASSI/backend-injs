# Guide Déploiement INJS-LMD via VS Code - jusqu'à https://injs.badge-qr-code.pro

> **Objectif**: Déployer `backend-injs` sur `injs.badge-qr-code.pro` en passant par `injs-app`
> **Chaîne**: `backend-injs` (dev) → sync → `Tobi-nw/injs-app` (ou `JCKOUASSI/app-injslmd2026demo`) → Docker Hub → VPS 152.228.233.123 → https://injs.badge-qr-code.pro

## Prérequis VS Code

- Extensions: Python, ESLint, Docker, GitHub Actions
- Outils: `gh` CLI authentifié (`gh auth login`), Docker Desktop, Python 3.12, Node 22
- Ouvrir le dossier `backend-injs` dans VS Code: `code .`

## Phase 1: Développement local (VS Code Tasks)

Ouvrir la palette: `Ctrl+Shift+P` → `Tasks: Run Task`

### 1. Préparer l'environnement
```
INJS 0 · Vérifier l'environnement
INJS 1 · Bootstrap (préparer l'environnement)
```
- Crée `backend/.venv`, installe `requirements.txt`, `frontend/node_modules`, écrit `arena/settings_sandbox.py`

### 2. Base de données et admin
```
INJS 2 · Migrations (sandbox SQLite)
INJS 3 · Créer admin local (admin/admin123)
```
- Vérifie: `backend/db_sandbox.sqlite3` créé, admin existe

### 3. Lancer les serveurs (3 terminaux dédiés)
```
INJS 4 · API Django :8000 (sandbox SQLite)
INJS 5 · Site web :3000 (Vite + proxy /api)
INJS 6 · Mobile Sim :5000 (PWA INJS bleu)
```
OU tout en un:
```
INJS 7 · Stack complète (API 8000 + Front 3000 + Mobile 5000)
```
- Previews: 
  - API: http://localhost:8000/api/ → https://8000-<sandbox>.e2b.app
  - Front: http://localhost:3000/ → https://3000-<sandbox>.e2b.app
  - Mobile: http://localhost:5000/ → https://5000-<sandbox>.e2b.app (bleu nuit #0B1F3A + bleu clair #1E62D0)

### 4. Vérifier les couleurs INJS
```
INJS · Fix mobile couleurs INJS bleu foncé/clair
```
- Doit afficher `✅ Aucun vert, déjà en bleu INJS` si déjà corrigé
- Sinon, le thème a été corrigé dans `qr_badge_theme.dart` et `mobile-sim/style.css`

### 5. Tests et qualité
```
INJS · Tests backend (checks + migrations)
INJS · Lint frontend
INJS · Build frontend
INJS · Tests frontend (Vitest)
INJS · Hygiène du dépôt (P00-02/P00-05)
INJS · Smoke INJS-LMD (23 étapes)
INJS · Sonde sandbox (feux verts)
```
- Tous doivent être verts (lint: 0 errors, build: ✓ built)

## Phase 2: Commit, Push et Sync vers injs-app

### 6. Commit et Push
```
Git · Commit toutes les modifications
Git · Push vers origin arena/01a0c5f9-backend-injs
PR · État et vérifications
```
- Ou manuellement:
```bash
git add -A
git commit -m "feat: ma fonctionnalité"
git push origin arena/01a0c5f9-backend-injs
```

### 7. Sync vers injs-app (dépôt de production)

**IMPORTANT**: Vérifiez d'abord la facturation GitHub (cause des échecs CI actuels):
```
Déploiement 13 · Vérifier CI GitHub (billing)
```
- Si `The job was not started because recent account payments have failed` → régler `Billing & plans` avant de sync

**Dry-run (simulation, sans push)**:
```
Déploiement 3 · Sync dry-run vers injs-app (simulation)
```
- Va sur GitHub → Actions → Sync → lit le rapport: fichiers `+a / ~m / -d`, vérifie `SYNC_KEEP_PATHS`

**Push réel (arme le déploiement)**:
```
Déploiement 4 · Sync push réel vers injs-app (ARME)
```
- ⚠️ Ne faire qu'après dry-run vert
- Pousse `main` → `Tobi-nw/injs-app@main` → déclenche build Docker Hub `ophirdesire/qr-badge-*`

**Suivi**:
```
Déploiement 5 · Suivre les exécutions du sync
```
- `gh run list --workflow=sync-injs-app.yml --limit 5`
- Attendre que le run soit vert, puis vérifier Docker Hub et VPS

## Phase 3: Déploiement sur VPS 152.228.233.123 (injs.badge-qr-code.pro)

### 8. Préparer le VPS (à exécuter SUR LE VPS)

**Via VS Code SSH** (si Remote-SSH configuré) ou terminal local:
```
Déploiement 12 · SSH vers VPS prod (152.228.233.123)
```
- Ou manuellement: `ssh root@152.228.233.123` ou `ssh ubuntu@152.228.233.123`

**Sur le VPS**:
```bash
cd /opt/injs  # ou /home/.../backend-injs
git checkout arena/01a0c5f9-backend-injs
git pull origin arena/01a0c5f9-backend-injs

# Préparer .env production
cp .env.example .env
nano .env
# Renseigner:
# DB_PASSWORD=...
# DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
# DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_EMAIL=admin@injs.local
# DJANGO_SUPERUSER_PASSWORD=admin123
# DJANGO_ALLOWED_HOSTS=injs.badge-qr-code.pro,localhost
# CSRF_TRUSTED_ORIGINS=https://injs.badge-qr-code.pro
# CORS_ALLOWED_ORIGINS=https://injs.badge-qr-code.pro
# VITE_API_URL=https://injs.badge-qr-code.pro/api
```

**Tâche VS Code locale pour générer .env**:
```
Déploiement 1 · Préparer .env production
```

### 9. Build et lancement prod

**Sur VPS**:
```bash
docker compose down
docker compose up -d --build
docker compose ps  # tous healthy
docker compose logs backend --tail=100 | grep -i super
```

**Via VS Code (si Docker context distant configuré)**:
```
Déploiement 2 · Build Docker local (test)
Déploiement 9 · Logs prod backend
Déploiement 10 · Logs prod frontend
```

### 10. Créer admin et vérifier login

**Sur VPS**:
```bash
docker compose exec backend python manage.py migrate --noinput
bash scripts/fix_production_login.sh  # diagnostic complet
# OU
docker compose exec backend python scripts/create_admin_prod.py
# OU manuel:
docker compose exec backend python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
User=get_user_model()
u,_=User.objects.get_or_create(username='admin', defaults={'email':'admin@injs.local','is_superuser':True,'is_staff':True})
u.set_password('admin123'); u.is_superuser=True; u.is_staff=True; u.is_active=True; u.role='ADMIN'; u.save()
PY

# Test API locale
curl -s http://localhost:8001/api/health/
curl -s -X POST http://localhost:8001/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | jq .
curl -s http://localhost/api/health/
curl -s -X POST http://localhost/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | jq .

# Si compte verrouillé après 5 échecs (CURP):
# Déverrouiller
```

**Via VS Code Tasks (local si conteneurs prod tournent localement)**:
```
Déploiement 8 · Créer admin prod (local Docker)
Déploiement 11 · Déverrouiller compte admin prod
Déploiement 6 · Vérifier santé prod https://injs.badge-qr-code.pro
Déploiement 7 · Fix production login (admin/admin123)
```

### 11. Vérification finale prod

**Dans navigateur**:
- https://injs.badge-qr-code.pro/ → doit afficher frontend React (pas page blanche)
- F12 → Console → aucune erreur CORS
- https://injs.badge-qr-code.pro/login → admin/admin123 → doit rediriger vers `/`
- https://injs.badge-qr-code.pro/api/docs/ → Swagger UI
- https://injs.badge-qr-code.pro/admin/ → admin Django

**Si échec**:
- `docker compose logs backend --tail=100`
- `docker compose logs frontend --tail=100`
- Vérifier `VITE_API_URL` dans build: `docker compose exec frontend cat /usr/share/nginx/html/index.html | grep -o 'VITE_API_URL[^<]*'`
- Vérifier `.env` sur VPS: `grep -v PASSWORD .env`

## Phase 4: Pipeline complet en une commande

```
Déploiement FULL · Pipeline complet jusqu'à prod
```
- Exécute bootstrap → migrations → admin → checks → lint+build → affiche instructions déploiement

## Raccourcis VS Code

- `Ctrl+Shift+P` → `Tasks: Run Task` → choisir tâche
- `Ctrl+`` → terminal intégré
- `F5` → lance `Stack INJS complète (API + Front)` (via launch.json compound)
- `Ctrl+Shift+D` → Debug → choisir `API Django :8000 (sandbox SQLite)`

## Fichiers importants

- `.env.example` - exemple complet prod (DB, SECRET_KEY, SUPERUSER, CORS/CSRF)
- `docker-compose.yml` - 3 services prod (db, backend:8001, frontend:80 avec proxy API)
- `frontend/nginx.conf` + `docker/nginx/default.conf` - proxy /api, /admin vers backend:8001
- `backend/config/settings.py` - supporte DB_* et POSTGRES_*, DEBUG et DJANGO_DEBUG
- `scripts/create_admin_prod.py` - création admin prod idempotent
- `scripts/fix_production_login.sh` - diagnostic complet prod
- `docs/PRODUCTION_LOGIN_FIX.md` - runbook détaillé
- `mobile-sim/` - PWA simulation Flutter mobile (port 5000, couleurs INJS #0B1F3A + #1E62D0)

## Déploiement via injs-app (chaîne officielle)

1. Dev local → commit → push `arena/01a0c5f9-backend-injs`
2. Merge vers `main` (PR)
3. Sync `main` → `Tobi-nw/injs-app@main` (dry-run puis réel)
4. `injs-app` → build Docker Hub `ophirdesire/qr-badge-frontend` + `backend`
5. VPS `injs.badge-qr-code.pro` → `docker compose pull && up -d` (ou watchtower)
6. Vérif santé + login admin

Voir `docs/DEPLOIEMENT_INJS.md` pour la chaîne complète avec preuves de déploiement (commit dev → commit sync → digest image → HTTP 200).
