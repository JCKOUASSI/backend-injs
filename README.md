# INJS-LMD 2026 — Système de Gestion Académique LMD

Plateforme institutionnelle pour l'**Institut National de la Jeunesse et des Sports (INJS)** — Côte d'Ivoire.

## Architecture

- **Backend**: Django 5 + DRF + PostgreSQL (prod) / SQLite (dev) + Redis + Celery + RabbitMQ
- **API**: REST `/api/v1/` + Swagger `/api/v1/docs/`
- **Port API**: **8001** (Docker) — en local, `runserver 8002` si le port 8001 est occupé

## Démarrage rapide (Docker)

```bash
docker-compose up --build
```

Services:
- API: http://localhost:8001
- Swagger: http://localhost:8001/api/v1/docs/
- Admin: http://localhost:8001/admin/
- Nginx: http://localhost

## Démarrage local

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# SQLite par défaut — aucune base externe requise
python manage.py migrate
python manage.py seed_injs_demo
python manage.py runserver 8001
```

Le seed importe automatiquement la **maquette STAPS 2026** et la **nomenclature emplois** depuis `elements/`.

### Import manuel des référentiels métier

```bash
python manage.py import_maquette_staps2026 --replace
python manage.py import_nomenclature_staps --replace
```

### Tests

```bash
python manage.py test_injs          # suite complète
python manage.py test_injs apps.faculty.tests  # module EDT / présences
```

## Comptes démo

**Mot de passe**: `Demo@INJS2026!`

| Email | Profil |
|-------|--------|
| admin@demo.injs.ci | Super Admin |
| dga@demo.injs.ci | Directeur Général Adjoint |
| dg@demo.injs.ci | Directeur Général |
| scolarite@demo.injs.ci | Responsable Scolarité |
| prof.martin@demo.injs.ci | Enseignant |
| etudiant1@demo.injs.ci | Étudiant (L1 STAPS PL, spécialité APA) |

## Modules

1. Auth & RBAC (groupes Django natifs, 5 niveaux, MFA, OAuth2)
2. Gestion étudiants (QR, inscriptions, parcours emploi)
3. Gestion enseignants & emploi du temps (EDT daté, cours, présences, badgeages)
4. LMD STAPS (UE/ECUE, spécialités TC/EM/ES/MS/APA, crédits ECTS)
5. Notes & délibérations (moteur LMD officiel INJS)
6. Finance (Orange/MTN/Moov/Wave/Visa)
7. Documents, messagerie, bibliothèque
8. Rapports PDF/Excel/Word + relevé de notes officiel

## Moteur LMD (règles INJS)

Configuré via `.env` : `LMD_CC_WEIGHT`, `LMD_CT_WEIGHT`, `LMD_COMPENSATION_FLOOR`, `LMD_MENTION_*`

- ECUE : CC 40 % + CT 60 %, validé si ≥ 10/20
- UE : validation directe ou compensation (aucun ECUE < 8/20)
- Semestre : validation directe ou compensation inter-UE (moyenne ≥ 10)
- Mentions : Très bien / Bien / Assez bien / Passable / Ajourné

## API principales

```
POST /api/v1/auth/login/
POST /api/v1/auth/refresh/
GET  /api/v1/auth/me/
GET  /api/v1/auth/groups/
GET  /api/v1/students/
GET  /api/v1/students/{id}/card/
GET  /api/v1/students/{id}/career_path/
GET  /api/v1/academics/formation-periods/
GET  /api/v1/academics/specializations/
GET  /api/v1/faculty/seances/
POST /api/v1/faculty/seances/generate/
POST /api/v1/faculty/seances/publish/
GET  /api/v1/faculty/badge-events/
GET  /api/v1/academics/job-nomenclatures/
GET  /api/v1/exams/grades/
POST /api/v1/exams/deliberations/{id}/run/
POST /api/v1/finance/payments/initiate/
GET  /api/v1/reports/analytics/
GET  /api/v1/reports/transcript/{student_id}/pdf/?semester=1&academic_year=2025-2026
GET  /api/v1/reports/transcript/{student_id}/summary/
```

## Structure

```
backend/          # Django API
elements/         # Documents métier (maquette, validation LMD, relevé, nomenclature)
docker/           # Nginx, K8s
docs/             # Architecture, schéma DB, exemples API
k8s/              # Kubernetes manifests
.github/          # CI/CD
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Schéma DB](docs/DATABASE_SCHEMA.md)
- [API Examples](docs/API_EXAMPLES.md)
- [EDT, cours, présences, badgeages](docs/EDT.md)
