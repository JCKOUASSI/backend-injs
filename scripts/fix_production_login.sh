#!/usr/bin/env bash
# =============================================================================
# FIX PRODUCTION LOGIN - injs.badge-qr-code.pro
# À exécuter SUR LE VPS 152.228.233.123 en tant que root ou user docker
# =============================================================================
set -euo pipefail

echo "======================================================================"
echo " FIX PRODUCTION - injs.badge-qr-code.pro"
echo " $(date)"
echo "======================================================================"

# Détection du répertoire du projet
PROJECT_DIR=""
for dir in /opt/injs /home/*/backend-injs /home/*/app-injslmd2026demo /root/backend-injs .; do
  if [ -f "$dir/docker-compose.yml" ] || [ -f "$dir/compose.yml" ]; then
    PROJECT_DIR="$dir"
    break
  fi
done

if [ -z "$PROJECT_DIR" ]; then
  echo "❌ docker-compose.yml introuvable. Placez-vous dans le répertoire du projet"
  echo "   ou définissez PROJECT_DIR=/chemin/vers/projet"
  exit 1
fi

cd "$PROJECT_DIR"
echo "📁 Projet: $PROJECT_DIR"
echo ""

# 1. Vérif .env
echo "=== 1. Vérification .env ==="
if [ ! -f .env ]; then
  echo "❌ .env manquant, création depuis .env.example"
  cp .env.example .env
  echo "⚠️  Éditez .env avec vos secrets puis relancez ce script"
  exit 1
fi

echo "Contenu .env (sans secrets):"
grep -v PASSWORD .env | grep -v SECRET | head -n 30
echo ""

# Vérif vars critiques
for var in DB_PASSWORD DJANGO_SECRET_KEY DJANGO_SUPERUSER_USERNAME DJANGO_SUPERUSER_PASSWORD; do
  if ! grep -q "^$var=" .env; then
    echo "❌ $var manquant dans .env"
  else
    echo "✅ $var présent"
  fi
done
echo ""

# 2. Git pull
echo "=== 2. Mise à jour code ==="
if [ -d .git ]; then
  git fetch origin
  echo "Branche actuelle: $(git branch --show-current)"
  echo "Dernier commit local: $(git log --oneline -1)"
  echo "Dernier commit distant arena/01a0c5f9-backend-injs: $(git log --oneline origin/arena/01a0c5f9-backend-injs -1 2>/dev/null || echo 'branche non trouvée')"
  # Si on est sur arena/01a0c5f9-backend-injs, pull
  if git branch --show-current | grep -q "arena/01a0c5f9"; then
    git pull origin $(git branch --show-current)
  else
    echo "⚠️  Vous n'êtes pas sur arena/01a0c5f9-backend-injs, pull manuel nécessaire"
    echo "   git checkout arena/01a0c5f9-backend-injs && git pull"
  fi
else
  echo "⚠️  Pas un dépôt git, skip pull"
fi
echo ""

# 3. Docker ps avant
echo "=== 3. État avant rebuild ==="
docker compose ps || docker-compose ps
echo ""

# 4. Rebuild
echo "=== 4. Rebuild et relance ==="
echo "docker compose down && up --build"
docker compose down || docker-compose down
docker compose up -d --build || docker-compose up -d --build
echo ""
echo "Attente 20s pour démarrage..."
sleep 20
docker compose ps || docker-compose ps
echo ""

# 5. Logs backend
echo "=== 5. Logs backend (50 dernières lignes) ==="
docker compose logs backend --tail=50 || docker-compose logs backend --tail=50
echo ""

# 6. Migrations
echo "=== 6. Migrations ==="
docker compose exec -T backend python manage.py migrate --noinput || docker-compose exec -T backend python manage.py migrate --noinput
echo ""

# 7. Vérif admin
echo "=== 7. Vérification utilisateur admin ==="
docker compose exec -T backend python manage.py shell <<'PY' || docker-compose exec -T backend python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
User=get_user_model()
print(f"Total users: {User.objects.count()}")
for u in User.objects.all()[:20]:
    print(f"  - {u.username} email={u.email} superuser={u.is_superuser} staff={u.is_staff} active={u.is_active} role={getattr(u, 'role', 'N/A')}")
print(f"admin exists: {User.objects.filter(username='admin').exists()}")
PY
echo ""

# 8. Création admin si manquant
echo "=== 8. Création / réinit admin ==="
if [ -f scripts/create_admin_prod.py ]; then
  docker compose exec -T backend python manage.py shell < scripts/create_admin_prod.py || docker-compose exec -T backend python manage.py shell < scripts/create_admin_prod.py
else
  echo "scripts/create_admin_prod.py manquant, création manuelle"
  docker compose exec -T backend python manage.py shell <<'PY' || docker-compose exec -T backend python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
User=get_user_model()
username='admin'
email='admin@injs.local'
password='admin123'
u, created = User.objects.get_or_create(username=username, defaults={'email': email, 'is_superuser': True, 'is_staff': True})
u.set_password(password)
u.email=email
u.is_superuser=True
u.is_staff=True
u.is_active=True
if hasattr(u, 'role'):
    u.role='ADMIN'
u.save()
print(f"{'Created' if created else 'Updated'} admin with password {password}")
from django.contrib.auth import authenticate
print(f"Auth test: {authenticate(username=username, password=password) is not None}")
PY
fi
echo ""

# 9. Test API locale
echo "=== 9. Test API locale (sans Nginx) ==="
echo "curl http://localhost:8001/api/health/"
docker compose exec -T backend curl -s http://localhost:8001/api/health/ || curl -s http://localhost:8001/api/health/ || echo "❌ backend:8001/api/health/ échoué"
echo ""
echo "curl http://localhost:8001/api/auth/login/ admin/admin123"
docker compose exec -T backend curl -s -X POST http://localhost:8001/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | head -c 500 || curl -s -X POST http://localhost:8001/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | head -c 500
echo ""
echo ""

# 10. Test via Nginx
echo "=== 10. Test via Nginx (http://localhost/api/) ==="
curl -s http://localhost/api/health/ | head -c 500 || echo "❌ http://localhost/api/health/ échoué"
echo ""
curl -s -X POST http://localhost/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | head -c 500 || echo "❌ http://localhost/api/auth/login/ échoué"
echo ""
echo ""

# 11. Test HTTPS externe (si possible)
echo "=== 11. Test HTTPS externe ==="
curl -k -s https://injs.badge-qr-code.pro/api/health/ | head -c 500 || echo "❌ https://injs.badge-qr-code.pro/api/health/ échoué (normal si firewall)"
echo ""

# 12. Logs finaux
echo "=== 12. Logs finaux backend ==="
docker compose logs backend --tail=30 || docker-compose logs backend --tail=30
echo ""
echo "=== 13. Logs frontend ==="
docker compose logs frontend --tail=30 || docker-compose logs frontend --tail=30
echo ""

echo "======================================================================"
echo " FIN DU DIAGNOSTIC"
echo " Si admin existe et curl http://localhost/api/auth/login/ renvoie access token,"
echo " alors le backend est OK. Le problème restant est Nginx / TLS / DNS."
echo ""
echo " Prochaines étapes:"
echo "  - Vérifier que https://injs.badge-qr-code.pro pointe bien vers ce VPS"
echo "  - Vérifier que le port 80 est ouvert et Nginx écoute"
echo "  - Vérifier les logs: docker compose logs -f"
echo "  - Dans navigateur: F12 -> Console -> essayer login admin/admin123"
echo "  - Si 'Compte verrouillé' -> attendre 15 min ou déverrouiller:"
echo "    docker compose exec backend python manage.py shell -c \"from authentication import connexion_sure; connexion_sure.reinitialiser_compteur('admin')\" 2>/dev/null || echo 'Pas de CURP'"
echo "======================================================================"
