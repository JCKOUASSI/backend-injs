# Architecture INJS-LMD 2026

## Vue d'ensemble

Plateforme nationale de gestion académique LMD pour l'INJS Côte d'Ivoire, conçue pour gérer plusieurs institutions (approche ministère).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLIENTS (API REST / Swagger / Admin Django)          │
│   Applications tierces │ Portail web │ Intégrations institutionnelles   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS / TLS 1.3
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Istio Service Mesh + WAF + Rate Limit                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Nginx (reverse proxy, static, SSL termination)             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│         Django 5 + DRF + Gunicorn (API /api/v1/)                        │
│  accounts │ students │ academics │ faculty │ exams │ finance │ ...      │
└───┬─────────┬─────────┬──────────┬──────────┬────────────────────────────┘
    │         │         │          │          │
    ▼         ▼         ▼          ▼          ▼
 PostgreSQL  Redis   RabbitMQ  Elasticsearch  MinIO
 (OLTP)     (cache)  (Celery)  (search)      (files)
```

## Modules Backend

| App | Responsabilité |
|-----|----------------|
| `core` | Modèles de base, mixins, permissions, utilitaires export |
| `accounts` | User, RBAC 5 niveaux, JWT, MFA, OAuth2/OIDC, audit |
| `academics` | Institutions, départements, filières, UE/ECUE, spécialités STAPS, nomenclature emplois |
| `students` | Étudiants, inscriptions, dossiers, carte QR |
| `faculty` | Enseignants, affectations, emploi du temps, absences |
| `exams` | Examens, notes, délibérations, jurys, soutenances |
| `admissions` | Préinscriptions, admissions, campagnes |
| `finance` | Frais, paiements (Orange/MTN/Moov/Wave/Visa) |
| `notifications` | Email, push, WebSocket |
| `reports` | PDF, Word, Excel, analytics |
| `documents` | GED, signature électronique, archivage |
| `messaging` | Messagerie interne |
| `library` | Bibliothèque numérique |

## RBAC - 5 Niveaux (groupes Django natifs)

```
N0: super_admin
N1: directeur_general, directeur_academique, directeur_financier
N2: chef_departement, responsable_filiere, responsable_scolarite
N3: enseignant, jury, examinateur
N4: etudiant
```

Chaque groupe possède un `GroupProfile` (code, level). Permissions métier : `{module}.{action}` ex. `students.view`, `grades.create`, `finance.export_pdf`.

API groupes : `GET /api/v1/auth/groups/`

## Flux Auth JWT

```
POST /api/v1/auth/login/ → access + refresh tokens
POST /api/v1/auth/refresh/ → new access token
POST /api/v1/auth/mfa/verify/ → après login si MFA activé
GET  /api/v1/auth/me/ → profil + permissions
```

## Calcul LMD (moteur officiel INJS)

Règles issues de `elements/CONDITIONS DE VALIDATION.docx` — implémentées dans `apps/exams/services/lmd_engine.py` :

- ECUE : CC 40 % + CT 60 %, validé si ≥ 10/20
- UE : validation directe ou compensation (aucun ECUE < 8/20)
- Semestre : validation directe ou compensation inter-UE (moyenne ≥ 10)
- Année : 60 crédits + règle 80 %
- Mentions : Très bien / Bien / Assez bien / Passable / Ajourné

## Référentiels métier (elements/)

| Document | Commande / Service |
|----------|-------------------|
| Maquette STAPS 2026 | `import_maquette_staps2026` |
| Nomenclature emplois | `import_nomenclature_staps` |
| Relevé de notes | `reports/services/transcript.py` |

## Paiements (finance/providers/)

Abstraction `PaymentProvider` avec implémentations:
- `OrangeMoneyProvider`, `MTNMoMoProvider`, `MoovMoneyProvider`, `WaveProvider`, `StripeCardProvider`

## Déploiement

- **Dev**: `docker-compose up` (PostgreSQL, Redis, RabbitMQ, MinIO, API:8001)
- **Prod**: Kubernetes + Helm + ArgoCD + Prometheus/Grafana/Loki/Tempo

## API Versioning

Toutes les routes sous `/api/v1/`. Documentation Swagger: `/api/v1/docs/`
