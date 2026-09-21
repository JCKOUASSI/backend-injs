# Fix Production Login - injs.badge-qr-code.pro

Date: 2026-09-21
URL: https://injs.badge-qr-code.pro/login
Problème: Impossible de se connecter avec admin/admin123 au frontend et à l'API en production

## Diagnostic rapide (à exécuter sur le VPS 152.228.233.123)

```bash
cd /path/to/backend-injs  # ou /path/to/app-injslmd2026demo
# 1. État des conteneurs
docker compose ps
docker compose logs backend --tail=100

# 2. L'API répond-elle en local (sans passer par Nginx) ?
docker compose exec backend python manage.py check --deploy
curl -s http://localhost:8001/api/health/ || docker compose exec backend curl -s http://localhost:8001/api/health/

# 3. La base contient-elle l'utilisateur admin ?
docker compose exec backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User=get_user_model()
print('Users:', User.objects.count())
print('admin exists:', User.objects.filter(username='admin').exists())
if User.objects.filter(username='admin').exists():
    u=User.objects.get(username='admin')
    print('admin is_superuser:', u.is_superuser, 'is_staff:', u.is_staff, 'is_active:', u.is_active, 'role:', u.role)
"

# 4. Test login direct via API (sans frontend)
curl -s -X POST http://localhost:8001/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq .

# 5. Test via Nginx (même domaine que le frontend)
curl -s -X POST http://localhost/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq .

# 6. Test HTTPS externe (depuis votre poste, pas le VPS)
curl -k -s https://injs.badge-qr-code.pro/api/health/ | jq .
curl -k -s -X POST https://injs.badge-qr-code.pro/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq .
```

## Causes probables et solutions

### Cause 1: Aucun superutilisateur dans la base de production (la plus probable)

**Symptôme**: `admin exists: False` ou `Users: 0`

**Explication**: 
- En dev, `seed_data.py` crée admin/admin123
- En prod, le code `authentication/apps.py:create_superuser_from_env()` crée le superuser **uniquement si** les variables `DJANGO_SUPERUSER_USERNAME`, `EMAIL`, `PASSWORD` sont définies
- Si `.env` ne contient pas ces 3 vars, aucun admin n'est créé → login impossible

**Solution**:

```bash
# Dans .env sur le VPS, ajouter:
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@injs.local
DJANGO_SUPERUSER_PASSWORD=admin123

# Puis redémarrer backend pour déclencher post_migrate
docker compose up -d backend
docker compose logs backend -f | grep -i super

# OU créer manuellement:
docker compose exec backend python manage.py createsuperuser --noinput \
  --username admin --email admin@injs.local
# Puis définir le mot de passe:
docker compose exec backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User=get_user_model()
u=User.objects.get(username='admin')
u.set_password('admin123')
u.is_superuser=True
u.is_staff=True
u.role='ADMIN'
u.save()
print('Password reset to admin123')
"

# OU utiliser le script fourni:
docker compose exec backend python manage.py shell < scripts/create_admin_prod.py
```

### Cause 2: Variables d'environnement incompatibles (DEBUG, SECRET_KEY, DB)

**Symptôme**: Backend crash au démarrage, `SECRET_KEY not set`, ou `connection to server at "localhost" failed`

**Explication**:
- `backend/config/settings.py` lisait uniquement `DEBUG` et `SECRET_KEY`, mais `.env.example` racine utilisait `DJANGO_DEBUG` et `DJANGO_SECRET_KEY`
- De même pour la DB: backend lit `POSTGRES_*`, mais `.env` racine utilisait `DB_*`
- Résultat: en prod, DEBUG=True par défaut (insecure), SECRET_KEY manquant, DB connectée à mauvaise base

**Solution appliquée dans ce commit**:
- `settings.py` supporte maintenant les deux conventions:
  - `DEBUG` OU `DJANGO_DEBUG` (0/1, true/false)
  - `SECRET_KEY` OU `DJANGO_SECRET_KEY`
  - `POSTGRES_DB` OU `DB_NAME`, `POSTGRES_USER` OU `DB_USER`, etc.
- `.env.example` racine mis à jour avec toutes les vars nécessaires
- `docker-compose.yml` simplifié: 3 services (db, backend:8001, frontend:80) avec healthcheck

**À faire sur le VPS**:
```bash
# Mettre à jour le code
git pull origin arena/01a0c5f9-backend-injs
# OU si dépôt injs-app:
# git pull origin main

# Recréer .env à partir du nouveau .env.example
cp .env.example .env
# Éditer .env avec vrais secrets:
nano .env  # DB_PASSWORD, DJANGO_SECRET_KEY fort, DJANGO_SUPERUSER_*

# Rebuild
docker compose up -d --build
docker compose logs -f backend
```

### Cause 3: Nginx ne proxy pas /api vers backend

**Symptôme**: `curl http://localhost/api/health/` → 404 ou empty reply, mais `curl http://localhost:8001/api/health/` → OK

**Explication**:
- Ancien `frontend/nginx.conf` ne faisait que SPA fallback, pas de proxy API
- Ancien `docker-compose.yml` avait un service nginx séparé avec volume `frontend_build` jamais rempli

**Solution appliquée**:
- `frontend/nginx.conf` et `docker/nginx/default.conf` mis à jour avec:
  ```nginx
  upstream backend { server backend:8001; }
  location /api/ { proxy_pass http://backend; ... }
  location /admin/ { proxy_pass http://backend; ... }
  ```
- `docker-compose.yml` simplifié: frontend est le nginx qui sert le build + proxy backend
- Backend expose 8001 (Gunicorn bind 0.0.0.0:8001), frontend proxy vers backend:8001

**À faire sur le VPS**:
```bash
docker compose up -d --build frontend
docker compose logs frontend
curl -s http://localhost/api/health/
```

### Cause 4: CORS / CSRF

**Symptôme**: Frontend affiche "Erreur réseau" ou "CORS error" dans console navigateur

**Explication**:
- Si `VITE_API_URL` est absolu `https://injs.badge-qr-code.pro/api` et frontend est sur même domaine, pas de CORS (same origin)
- Mais si `CORS_ALLOWED_ORIGINS` ou `CSRF_TRUSTED_ORIGINS` ne contient pas `https://injs.badge-qr-code.pro`, les requêtes POST avec cookies peuvent échouer

**Solution**:
- `.env` doit contenir:
  ```
  CSRF_TRUSTED_ORIGINS=https://injs.badge-qr-code.pro
  CORS_ALLOWED_ORIGINS=https://injs.badge-qr-code.pro
  DJANGO_ALLOWED_HOSTS=injs.badge-qr-code.pro,localhost,127.0.0.1
  ```
- Déjà dans le nouveau `.env.example`

### Cause 5: Cookie Secure / SameSite

**Symptôme**: Login réussit (200) mais refresh token non posé, déconnexion immédiate

**Explication**:
- En prod DEBUG=False, cookies sont `Secure=True`, `SameSite=Lax`
- Si frontend et API sont sur même domaine https, OK
- Si API est sur sous-domaine différent (ex: api.badge-qr-code.pro), cookie SameSite=Lax ne sera pas envoyé cross-site
- Solution: même domaine pour front et API (recommandé), ou SameSite=None + Secure

**Solution**:
- Garder front et API sur même domaine `injs.badge-qr-code.pro` (front `/`, API `/api/`)
- Déjà le cas avec `VITE_API_URL=https://injs.badge-qr-code.pro/api`
- Si besoin cross-domain, ajouter dans .env:
  ```
  JWT_COOKIE_SAMESITE=None
  JWT_COOKIE_SECURE=1
  COOKIE_SAMESITE=None
  ```

## Procédure complète de remise en service prod

```bash
# Sur VPS 152.228.233.123
cd /opt/injs  # ou votre chemin
git pull

# 1. Mettre à jour .env
cp .env.example .env
# Éditer:
# - DB_PASSWORD fort
# - DJANGO_SECRET_KEY fort (générer: python3 -c "import secrets; print(secrets.token_urlsafe(50))")
# - DJANGO_SUPERUSER_* = admin / admin@injs.local / admin123
# - Vérifier DJANGO_ALLOWED_HOSTS, CSRF, CORS

# 2. Rebuild et relance
docker compose down
docker compose up -d --build
docker compose ps
docker compose logs backend --tail=50
docker compose logs frontend --tail=50

# 3. Vérifier API locale
sleep 10
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); print('admin exists:', User.objects.filter(username='admin').exists())"
curl -s http://localhost:8001/api/health/
curl -s http://localhost/api/health/

# 4. Créer admin si manquant
docker compose exec backend python manage.py createsuperuser --noinput --username admin --email admin@injs.local || true
docker compose exec backend python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
User=get_user_model()
u, created = User.objects.get_or_create(username='admin', defaults={'email':'admin@injs.local', 'is_superuser':True, 'is_staff':True, 'role':'ADMIN'})
u.set_password('admin123')
u.is_superuser=True
u.is_staff=True
u.is_active=True
u.role='ADMIN'
u.save()
print(f"Admin {'created' if created else 'updated'}: {u.username}")
PY

# 5. Test login
curl -s -X POST http://localhost/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | jq .

# 6. Test HTTPS externe
curl -k https://injs.badge-qr-code.pro/api/health/
# Dans navigateur: https://injs.badge-qr-code.pro/login -> admin/admin123 -> devrait marcher

# 7. Logs si échec
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
```

## Checklist prod

- [ ] `.env` contient `DB_PASSWORD`, `DJANGO_SECRET_KEY` fort, `DJANGO_SUPERUSER_*`
- [ ] `DJANGO_DEBUG=0`, `DEBUG=0`
- [ ] `DJANGO_ALLOWED_HOSTS` inclut `injs.badge-qr-code.pro`
- [ ] `CSRF_TRUSTED_ORIGINS` = `https://injs.badge-qr-code.pro`
- [ ] `CORS_ALLOWED_ORIGINS` = `https://injs.badge-qr-code.pro`
- [ ] `VITE_API_URL` = `https://injs.badge-qr-code.pro/api` (absolu, pas relatif)
- [ ] `docker compose up -d --build` vert, `docker compose ps` tous healthy
- [ ] `curl http://localhost:8001/api/health/` → `{"status":"ok"}`
- [ ] `curl http://localhost/api/health/` → `{"status":"ok"}` (via nginx)
- [ ] Admin existe et login OK via curl et via navigateur
- [ ] Console navigateur sans erreur CORS

## Références

- `backend/config/settings.py` - supporte maintenant DB_* et POSTGRES_*, DEBUG et DJANGO_DEBUG
- `docker-compose.yml` - simplifié 3 services, backend 8001, frontend 80 avec proxy API
- `frontend/nginx.conf` et `docker/nginx/default.conf` - proxy /api, /admin, /static, /media vers backend:8001
- `.env.example` - exemple complet production
- `scripts/create_admin_prod.py` - script création admin prod
