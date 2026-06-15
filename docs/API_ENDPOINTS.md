# API Backend SYGEPCPFAE — Référence des endpoints

> **Dernière mise à jour :** juin 2026  
> **Base URL (dev) :** `http://localhost:8001`  
> **Préfixe API :** `/api/`

Documentation interactive générée automatiquement :

| Endpoint | Description |
|----------|-------------|
| `GET /api/schema/` | Schéma OpenAPI (JSON) |
| `GET /api/docs/` | Interface Swagger UI |

---

## Authentification

La plupart des endpoints exigent un **JWT Bearer** :

```http
Authorization: Bearer <access_token>
```

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/auth/login/` | POST | Connexion — retourne `access` + `refresh` |
| `/api/auth/token/refresh/` | POST | Rafraîchir le token d'accès |
| `/api/auth/me/` | GET, PATCH | Profil de l'utilisateur connecté |
| `/api/auth/roles/` | GET | Hiérarchie et périmètre des rôles |
| `/api/auth/me/change-password/` | POST | Changer son mot de passe |
| `/api/auth/users/` | GET, POST | Liste / création d'utilisateurs |
| `/api/auth/users/<pk>/` | GET, PUT, PATCH, DELETE | Détail / modification / suppression |

**Synchronisation inter-plateformes (SVEVCPFAE) :**

```http
Authorization: Api-Key <INTER_PLATFORM_API_KEY>
```

---

## Vocabulaire métier

| Terme API | Modèle | Signification |
|-----------|--------|---------------|
| **Formation** | `Formation` | Cycle de formation (ex. « FORMATION EN ADMINISTRATION DE BASE ») |
| **Module / cours** | `Module` | Cours rattaché à un cycle (ce que l'interface appelle « module ») |
| **Séance / session** | `SessionModule` | Séance planifiée ou en cours d'un module |
| **Référentiel** | `RefFormation`, `RefModule`, … | Catalogue prédéfini pour les listes déroulantes |

---

## 1. Formations & modules — `/api/formations/`

### 1.1 Cycles de formation (CRUD)

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/` | GET, POST | Liste / création de cycles |
| `/api/formations/<pk>/` | GET, PUT, PATCH, DELETE | Détail / modification / suppression |
| `/api/formations/<pk>/assign-superviseur/` | POST | Assigner un encadrant |
| `/api/formations/<pk>/participants/add/` | POST | Inscrire un auditeur (requiert `module_id`) |
| `/api/formations/<pk>/participants/<participant_id>/remove/` | DELETE | Retirer un auditeur |
| `/api/formations/<pk>/formateurs/` | GET | Formateurs assignés au cycle |
| `/api/formations/<pk>/formateurs/add/` | POST | Assigner un formateur (requiert `module_id`) |
| `/api/formations/<pk>/formateurs/<formateur_id>/remove/` | DELETE | Retirer un formateur |

### 1.2 Cours / modules (instances)

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/list/` | GET | Liste paginée des **modules** (1 ligne = 1 cours). Filtres : `statut`, `search`, `grade`, `groupe`, `vague`, `secretariat`, `actives`, `page`, `page_size`, … |
| `/api/formations/<pk>/detail/` | GET | Détail d'un cours (frontend React) |
| `/api/formations/<formation_pk>/modules/` | GET, POST | Liste / création de cours dans un cycle |
| `/api/formations/<formation_pk>/modules/<module_pk>/` | GET, PUT, PATCH, DELETE | Détail / modification / suppression |
| `/api/formations/<formation_pk>/modules/<module_pk>/full/` | GET | Détail complet (séances, participants, formateurs, stats) |
| `/api/formations/<formation_pk>/modules/<module_pk>/participants/add/` | POST | Inscrire un auditeur au module |
| `/api/formations/<formation_pk>/modules/<module_pk>/participants/<participant_id>/remove/` | DELETE | Retirer un auditeur |
| `/api/formations/<formation_pk>/modules/<module_pk>/formateurs/add/` | POST | Assigner un formateur |
| `/api/formations/<formation_pk>/modules/<module_pk>/formateurs/<formateur_id>/remove/` | DELETE | Retirer un formateur |
| `/api/formations/<formation_pk>/modules/<module_pk>/assign-superviseur/` | POST | Assigner / retirer l'encadrant du module |

### 1.3 Séances

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/<formation_pk>/sessions/` | GET | Liste des séances (option `?module_id=`) |
| `/api/formations/<formation_pk>/modules/<module_pk>/sessions/new/` | POST | Créer une séance |
| `/api/formations/<formation_pk>/sessions/<session_pk>/start/` | POST | Démarrer une séance |
| `/api/formations/<formation_pk>/sessions/<session_pk>/stop/` | POST | Terminer une séance |
| `/api/formations/<formation_pk>/sessions/<session_pk>/update/` | PATCH | Modifier une séance |
| `/api/formations/<formation_pk>/sessions/<session_pk>/delete/` | DELETE | Supprimer une séance |

### 1.4 QR codes

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/<formation_pk>/generate-qr/` | POST | Générer un QR (frontend) |
| `/api/formations/<formation_pk>/sessions/<session_pk>/generate-qr/` | POST | Générer un QR pour une séance |
| `/api/formations/<pk>/qr-image/` | GET | Image PNG du QR (API) |
| `/api/formations/<pk>/sessions/<session_pk>/qr-image/` | GET | Image PNG du QR séance |
| `/formations/<pk>/qr-image/` | GET | Image PNG du QR (**public**, hors `/api/`) |
| `/formations/<pk>/sessions/<session_pk>/qr-image/` | GET | Idem séance (**public**) |
| `/api/formations/superviseur/<pk>/generate-qr/` | POST | Générer QR (vue superviseur) |
| `/api/formations/superviseur/<pk>/qr/` | GET | QR actif (vue superviseur) |

### 1.5 Auditeurs (participants)

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/participants/` | GET, POST | CRUD liste / création |
| `/api/formations/participants/<pk>/` | GET, PUT, PATCH, DELETE | Détail / modification / suppression |
| `/api/formations/participants/list/` | GET | Liste paginée (frontend React) |
| `/api/formations/participants/<pk>/formations/` | GET | Formations/modules d'un auditeur |

### 1.6 Formateurs

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/formateurs/` | GET, POST | CRUD liste / création |
| `/api/formations/formateurs/<pk>/` | GET, PUT, PATCH, DELETE | Détail / modification / suppression |
| `/api/formations/formateurs/list/` | GET | Liste paginée (frontend) |
| `/api/formations/formateurs/finance-report/` | GET | Rapport financier formateurs |
| `/api/formations/formateurs/<pk>/donnees-sensibles/` | GET, PATCH | Données sensibles (RIB, etc.) |

### 1.7 Secrétariats

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/secretariats/` | GET, POST | Liste / création |
| `/api/formations/secretariats/<pk>/` | GET, PUT, PATCH, DELETE | Détail / modification / suppression |
| `/api/formations/secretariats/<pk>/participants/` | GET | Auditeurs du secrétariat |

### 1.8 Superviseur (encadrant)

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/superviseur/` | GET | Mes cycles assignés |
| `/api/formations/superviseur/<pk>/` | GET | Détail d'un cycle assigné |

### 1.9 Dashboard & statistiques opérationnelles

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/stats/` | GET | Statistiques tableau de bord (modules, séances, présences…) |

### 1.10 Finance

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/finance/dashboard/` | GET | Tableau de bord finance |
| `/api/formations/finance/settings/` | GET, PATCH | Paramètres (taux horaire, etc.) |
| `/api/formations/finance/encadrants/` | GET | Suivi encadrants |
| `/api/formations/finance/ajustements/` | GET, POST | Liste / création d'ajustements |
| `/api/formations/finance/ajustements/<pk>/valider/` | POST | Valider un ajustement |
| `/api/formations/finance/ajustements/<pk>/rejeter/` | POST | Rejeter un ajustement |

### 1.11 Référentiels

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/referentiels/` | GET | Données pour listes déroulantes (entrées **actives** + groupes, grades modules…) |
| `/api/formations/referentiels/gestion/` | GET | Toutes les tables référentielles (actifs + inactifs) — page admin |

**CRUD par entité** — pour chaque ressource : **GET, POST** sur la liste · **PUT, DELETE** sur `<pk>/`

| Ressource | Liste | Détail |
|-----------|-------|--------|
| Formations ref | `/api/formations/ref/formations/` | `…/<pk>/` |
| Modules ref (cours prédéfinis) | `/api/formations/ref/modules/` | `…/<pk>/` |
| Sites | `/api/formations/ref/sites/` | `…/<pk>/` |
| Bâtiments | `/api/formations/ref/batiments/` | `…/<pk>/` |
| Salles | `/api/formations/ref/salles/` | `…/<pk>/` |
| Catégories | `/api/formations/ref/categories/` | `…/<pk>/` |
| Grades | `/api/formations/ref/grades/` | `…/<pk>/` |
| Types secrétariat | `/api/formations/ref/types-secretariat/` | `…/<pk>/` |
| Vagues | `/api/formations/ref/vagues/` | `…/<pk>/` |

### 1.12 Import & synchronisation

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/import-excel/` | POST | Import Excel (multipart) |
| `/api/formations/sync/participants/` | GET | Sync auditeurs → SVEVCPFAE (Api-Key) |
| `/api/formations/sync/formateurs/` | GET | Sync formateurs |
| `/api/formations/sync/sessions/` | GET | Sync séances |
| `/api/formations/sync/presences/` | GET | Sync présences |

---

## 2. Présences & badgeage — `/api/`

### 2.1 Scan QR

| Endpoint | Méthodes | Auth | Description |
|----------|----------|------|-------------|
| `/api/scan/` | POST | Public* | Scan QR classique (entrée / sortie) |
| `/api/scan/check-status/` | GET | Public* | Statut badgeage avant confirmation |
| `/api/scan/secure/` | POST | JWT | Scan sécurisé app mobile (anti-fraude) |
| `/api/scan/secure/heartbeat/` | POST | JWT | Heartbeat pendant séance ouverte |
| `/api/scan/secure/check-status/` | GET | JWT | Statut badgeage (utilisateur authentifié) |

\* Désactivé en production sauf `PUBLIC_QR_SCAN_ENABLED=True`.

### 2.2 Espace personnel (mobile)

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/me/historique/` | GET | Historique de badgeage de l'utilisateur connecté |
| `/api/me/fiche/` | GET, PATCH | Fiche personnelle (PATCH réservé aux formateurs) |

### 2.3 Gestion des présences (staff)

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/formations/<pk>/dashboard/` | GET | Dashboard présences d'un cycle |
| `/api/formations/<pk>/presences/` | GET | Liste des pointages |
| `/api/formations/<pk>/force-pointage/` | POST | Forcer entrée ou sortie |
| `/api/formations/<pk>/force-badgeage-auditeurs-bulk/` | POST | Badgeage bulk aléatoire auditeurs absents |
| `/api/formations/<pk>/close-session/` | POST | Clôturer une séance |
| `/api/formations/<uuid:token>/offline-data/` | GET | Données hors-ligne (token QR, public*) |

### 2.4 Auditeurs

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/participant/<pk>/historique/` | GET | Historique (rôle AUDITEUR, son propre profil) |
| `/api/participant/<pk>/fiche-admin/` | GET | Fiche admin d'un auditeur |
| `/api/participant/lookup/` | GET | Recherche par numéro / matricule |

### 2.5 Appareils & audit

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/devices/` | GET | Liaisons appareil ↔ compte |
| `/api/devices/<device_id>/unbind/` | DELETE | Délier un appareil |
| `/api/audit-logs/` | GET | Journal d'audit |

---

## 3. Exports — `/api/exports/`

Tous en **GET** (fichiers PDF ou Excel).

| Endpoint | Description |
|----------|-------------|
| `/api/exports/formation/<pk>/pdf/` | Export cycle complet (PDF) |
| `/api/exports/formation/<pk>/excel/` | Export cycle complet (Excel) |
| `/api/exports/module/<module_pk>/pdf/` | Export module / cours (PDF) |
| `/api/exports/module/<module_pk>/excel/` | Export module / cours (Excel) |
| `/api/exports/session/<session_pk>/pdf/` | Export séance (PDF) |
| `/api/exports/session/<session_pk>/excel/` | Export séance (Excel) |
| `/api/exports/formateur/<formateur_pk>/pdf/` | Rapport finance formateur (PDF) |
| `/api/exports/formateur/<formateur_pk>/excel/` | Rapport finance formateur (Excel) |
| `/api/exports/finance/synthese/pdf/` | Synthèse finance globale (PDF) |
| `/api/exports/finance/synthese/excel/` | Synthèse finance globale (Excel) |
| `/api/exports/finance/encadrants/pdf/` | Finance encadrants (PDF) |
| `/api/exports/finance/encadrants/excel/` | Finance encadrants (Excel) |

---

## 4. Statistiques — `/api/statistiques/`

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/api/statistiques/` | GET | Dashboard statistiques (`?formation_id=`, `?secretariat_id=`, période…) |
| `/api/statistiques/secretariats/` | GET | KPIs par secrétariat |
| `/api/statistiques/alertes/seuils/` | GET, POST, PUT | Seuils d'alerte et indicateurs |
| `/api/statistiques/rapports/` | GET, POST | Liste / génération de rapports |
| `/api/statistiques/rapports/notifications/` | GET, PATCH | Notifications rapports |
| `/api/statistiques/rapports/<rapport_id>/` | GET, PATCH, DELETE | Détail / modification / suppression |
| `/api/statistiques/rapports/<rapport_id>/workflow/` | POST | Workflow (`soumettre`, `valider`, `publier`, `rejeter`) |
| `/api/statistiques/rapports/<rapport_id>/observations/` | GET, POST | Observations sur un rapport |
| `/api/statistiques/point-journalier/` | GET | Point journalier (export inline via `?export=xlsx\|pdf\|docx`) |
| `/api/statistiques/point-journalier-export/` | GET | Export point journalier (fichier binaire) |
| `/api/statistiques/bilans/` | GET | Bilans (`?dimension=module\|categorie\|formation`, période…) |
| `/api/statistiques/bilans-export/` | GET | Export bilans (fichier binaire) |

**Traçabilité des indicateurs** (sources, formules, filtres) : voir [`STATISTIQUES_INDICATEURS.md`](STATISTIQUES_INDICATEURS.md).

---

## 5. Dashboard web (pages HTML) — `/dashboard/`

Routes legacy / pages statiques. La plupart redirigent vers le frontend React.

| Endpoint | Méthodes | Description |
|----------|----------|-------------|
| `/dashboard/badge/` | GET | Page badge QR |
| `/dashboard/legal/confidentialite-qr-badge/` | GET | Politique confidentialité app mobile |
| `/dashboard/legal/support-qr-badge/` | GET | Page support app mobile |
| `/dashboard/login/` | GET, POST | Connexion web (legacy) |
| `/dashboard/logout/` | GET | Déconnexion |
| `/dashboard/` | GET | Redirection → frontend React |
| `/dashboard/formations/*` | GET | Redirection → frontend |
| `/dashboard/participants/*` | GET | Redirection → frontend |
| `/dashboard/formateurs/*` | GET | Redirection → frontend |
| `/dashboard/users/*` | GET | Redirection → frontend |
| `/dashboard/import/` | GET | Redirection → frontend |

---

## 6. Administration Django

| Endpoint | Description |
|----------|-------------|
| `/admin/` | Interface d'administration Django |

---

## Rôles et périmètres d'accès (résumé)

| Permission DRF | Rôles typiques |
|----------------|----------------|
| `IsOperationalWebStaff` | Personnel web sauf FINANCE — dashboard, listes, référentiels dropdown |
| `IsWebStaff` | Tout personnel web y compris FINANCE — endpoints finance |
| `IsDFRC` | ADMIN, CPFAE_ADMIN, CHEF_CPFAE_ADMIN (+ DIRECTION lecture seule) — référentiels CRUD |
| `IsSecretariatOrDFRC` | Secrétariat + admins — création modules, import |
| `IsSecretariatOrEncadrantOrDFRC` | + encadrants — séances, présences, QR |
| `IsInterPlatformServiceAccount` | Sync SVEVCPFAE (Api-Key) |

Le rôle **FINANCE** n'a accès qu'aux endpoints `/api/formations/finance/*`, exports finance et statistiques — pas aux endpoints opérationnels (`/list/`, `/stats/`, `/referentiels/`, etc.).

---

## Fichiers sources

Les routes sont déclarées dans :

- `backend/config/urls.py` — routage principal
- `backend/authentication/urls.py`
- `backend/formations/urls.py`
- `backend/formations/qr_urls.py`
- `backend/presences/urls.py`
- `backend/exports/urls.py`
- `backend/statistiques/urls.py`
- `backend/dashboard/urls.py`

Pour le détail des payloads et schémas de réponse, préférer **`/api/docs/`** (Swagger) qui reste synchronisé avec le code.
