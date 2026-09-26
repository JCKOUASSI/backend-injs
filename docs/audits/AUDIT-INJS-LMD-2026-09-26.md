# AUDIT FONCTIONNEL, TECHNIQUE ET MÉTIER — APPLICATION INJS-LMD 2026

| Métadonnée | Valeur |
| :--- | :--- |
| **Projet** | `backend-injs` / INJS-LMD 2026 (`app-injslmd2026demo`) |
| **Date d'audit** | 26/09/2026 |
| **Mode** | **LECTURE / DIAGNOSTIC uniquement — aucun code modifié** |
| **Statut** | **Lot 2 partiellement APPLIQUÉ le 26/09/2026** (N-11 ✅, N-12 ✅, commande N-01 ✅ ; voir § 31) |
| **Branche / commit** | `main` / `89a1097aa4cf80e2da215622c70b964da2a4d8fc` (2026-09-25, `fix(ci): use GitHub-hosted runners`) |
| **Remote** | `origin` → `https://github.com/JCKOUASSI/backend-injs.git` |
| **Base officielle** | PostgreSQL 16 — `injs_lmd_current` @ `127.0.0.1:5432` |
| **Rapport** | `docs/audits/AUDIT-INJS-LMD-2026-09-26.md` |

---

## 1. RÉSUMÉ EXÉCUTIF

**Le socle applicatif est techniquement mature, testé et intégré ; l'application n'est en revanche PAS opérationnelle en l'état, pour quatre raisons bloquantes.**

1. **La base officielle de développement n'est pas alimentée pour la chaîne LMD.**
   **136 tables sur 183 sont vides** (74 %). La chaîne pédagogique (`scolarite_maquette`, `scolarite_ue`,
   `scolarite_ecue`, `scolarite_inscriptionadministrative`, `scolarite_inscriptionpedagogique`,
   `scolarite_dossieretudiant`, `scolarite_groupe`, `scolarite_affectationgroupe`, `edts_*`, `jurys_*`,
   `graduation_diplome`, `stages_*`, `suiviEvaluation_*`, `finances_*`, `administrations_*`,
   `ressources_humaines_*`, `patrimoine_*`) est **à zéro ligne**. Seuls survivent le domaine badgeage legacy
   (34 pointages / 8 sessions), les référentiels, le socle RBAC (81 rôles métier, 1 157 permissions,
   10 453 relations) et 22 utilisateurs.

2. **La géolocalisation est absente du canal principal, et neutralisée sur l'ancien.**
   a) **Canal EDT (le plus important) — la fonctionnalité n'existe pas dans le code.**
      `seances_edt_services.badger_scan()` reçoit les coordonnées du client et les **enregistre** via
      `**(coords or {})`, mais **n'appelle jamais** `_check_geofence()`. Aucun refus hors zone, aucune position
      obligatoire, aucun refus pour précision insuffisante ne sont donc possibles. → **A-P0-1 / N-12** (§ 21 bis).
   b) **Canal legacy — la fonction existe mais est neutralisée par la donnée.**
      Le site unique `INJS MARCORY` a `geofence_latitude = NULL` → `_check_geofence()` retourne
      `(True, None, None, None, None)`. Les **34 pointages** existants ont tous `last_latitude = NULL`.
      → **A-P0-4 / N-01**.
   ✅ **Arbitré le 26/09/2026** : coordonnées officielles `5.3083, -3.9825`, **alerte ET refus** hors zone (§ 23.1).
   ⚠️ Cet arbitrage **ne sera réellement appliqué qu'après N-12** : tant que le canal EDT n'appelle pas la
   fonction, la règle décidée ne s'applique à aucun badgage de séance LMD.

3. **Les présences prises via l'EDT LMD ne remontent dans aucun module aval.**
   `seances_edt_services.py` crée les `Pointage` avec `session=None` et `seance_edt=<AffectationCreneau>`.
   Or **0 fichier** de `statistiques/`, `dashboard/`, `exports/`, `suiviEvaluation/`, `jurys/`, `graduation/`
   ne mentionne `seance_edt`. Le calcul des indicateurs (`statistiques/effectifs.py:filter_sessions`) part de
   `SessionModule.objects.all()` et d'un `Exists(Pointage.filter(session_id=OuterRef('pk')))`.
   → **Présences EDT → Statistiques / Assiduité / KPI / Bilans = rupture d'intégration.**

4. **Le canal de scan EDT n'a aucun client.** `/api/presences/seances-edt/scan/` n'est appelé **ni par le mobile,
   ni par le front** — seule la suite de tests l'appelle. L'API EDT est livrée sans consommateur.
   ✅ **Arbitré le 26/09/2026** : le **moteur EDT intégré** est confirmé (A-01) ; il reste à brancher un client.

**Côté qualité, la situation est bonne** : la suite backend et la suite frontend (1 747 tests Vitest / 89 fichiers,
139,8 s) s'exécutent ; les 137 tests `presences`+`edts` sont **verts** ; les commandes de seed de bout en bout
(`seed_injs_complet`) déroulent les 5 lots et affichent la matrice des voyants verts. En revanche :
- **`seed_injs_complet` s'auto-certifie « ✓ certifié conforme » alors qu'il produit « 0 tableau(x) généré(s) »** ;
- le script E2E maison `tests_e2e_injs_2026_2027.py` **crash dès l'étape 1** (`AttributeError`, ligne 154) ;
- **`smoke_test_injs` n'est pas idempotent** (`CommandError : UNIQUE constraint failed: scolarite_anneeacademique.courante`)
  — et c'est une **étape de la CI** ;
- **`/api/presences/seances-edt/scan/` n'a aucun client** (ni mobile, ni front) : l'API EDT est livrée sans consommateur.

**Verdict : [implémentation] et [non opérationnel] sur les chaînes transverses ; [Validé et opérationnel] sur le socle
technique, le RBAC/CURP, les référentiels, l'EDT, le badgeage QR legacy et le frontend.**

**Répartition des 18 modules : 4 [Validé et opérationnel] · 4 [non opérationnel] · 10 [implémentation].**
Décision provisoire : **NON PRÊT** sur les deux environnements (§ 30).

> Détail chiffré et classification complète : sections 6, 20-23 et section 30.
> ✅ **Les trois questions métier bloquantes sont TRANCHÉES le 26/09/2026** (§ 23.1) : A-01 moteur EDT intégré ·
> A-02 alerte **et** refus hors zone · A-03 coordonnées officielles `5.3083, -3.9825`. Elles ne sont plus ouvertes.

---

## 2. PÉRIMÈTRE ET SOURCES ANALYSÉES

### 2.1 Sources documentaires (`workspace/26092026/`)

| # | Source | Type | Périmètre |
|---|---|---|---|
| S01 | `Promp-Audit-INJS-LMD-26-09-2026OK.txt` (581 l.) | Prompt d'audit | Cahier des charges de cet audit, 30 sections exigées |
| S02 | `Je te propose… app-injs-lmd-2026.docx` (733 Ko) | Modèle fonctionnel de référence | 18 modules métier de référence |
| S03 | `1. Prompt de cadrage` … `25. Prompt générique` (24 fichiers) | Spécifications par module | Référentiels, formations, admissions, EDT, présences, évaluations, jurys, diplomation, finances, statistiques, RBAC, mobile, migration, tests |
| S04 | `Mise-a-jour-design-injs-lmd.pdf` | Design UI/UX | Identité visuelle INJS |
| S05 | `docs/` (25 fichiers) | Documentation projet | `ARCHITECTURE.md`, `API_ENDPOINTS.md`, `CURP_INJS_MATRICE.md`, `EDT_CONTRAT_DONNEES.md`, `GARDE_FOUS.md`, `SECURITE_DONNEES.md`, `STATISTIQUES_INDICATEURS.md`, `TEST_E2E_INJS_MARCORY_2026_2027.md`, `TESTS_FRONTEND.md`, `DEPLOIEMENT_INJS.md`, `CARTOGRAPHIE_CIBLE_INJS_LMD.md` |
| S06 | `docs/adr/`, `docs/audit/`, `docs/audits/` | Décisions & audits antérieurs | ADR, audits utilisateurs / GET-INJS / CURP (2026-09-14/15) |
| S07 | `.github/workflows/ci.yml`, `Makefile`, `arena/*.sh` | Chaîne d'exécution | CI, cibles Make, lanceurs port 8000 / 3000 |
| S08 | `backend/seed_data.py`, `seed_lot1_1_injs.py` … `seed_lot5_1_transverse.py` | Jeux de données | Chaîne de seeding 1.1 → 5.1 |
| S09 | `qr_badge_mobile/` (Flutter) | Application mobile | Scan QR, géolocalisation |
| S10 | `frontend/src/` | Front React/Vite | 74 `<Route>` dans `App.jsx`, 82 pages non-test |

### 2.2 Exigences suivies

Chaque exigence détectée (S01-S10) est tracée vers son implantation backend / frontend / BDD / API / permissions / tests
et son **état réel**, selon les 4 mentions imposées par S01 phase 14 :

`[Validé et opérationnel]` · `[non opérationnel]` · `[implémentation]` · `[à vérifier]`

---

## 3. ÉTAT GIT / WORKSPACE

```
branche : main
commit  : 89a1097aa4cf80e2da215622c70b964da2a4d8fc (2026-09-25)
remote  : origin → https://github.com/JCKOUASSI/backend-injs.git
```

| État | Détail |
| :--- | :--- |
| Fichiers modifiés (8) | `frontend/src/components/layout/Layout.jsx`, `frontend/src/index.css`, `frontend/src/main.jsx`, `frontend/src/pages/habilitations/habilitations.css`, `frontend/src/styles/dashboardEngine.css`, `frontend/src/styles/login.css`, `frontend/src/styles/scolariteDashboard.css`, `frontend/src/styles/sidebar.css` |
| Non suivis (4) | `.venv-ci/`, `frontend/src/styles/harmonisation.css`, `optimisation-ci-backend-injs.prompt.md`, `workspace/26092026/` |
| Modifications apportées par l'audit | **AUCUNE.** Aucun fichier applicatif modifié, créé ou supprimé. |
| Objets temporaires | Fichiers d'aide en `/tmp/` uniquement (`db_counts.py`, `db_probe*.py`, `*.log`) |

⚠️ Les fichiers CSS/JSX modifiés sont des modifications **préexistantes de l'utilisateur** — préservées, non écrasées.

---

## 4. ARCHITECTURE CONSTATÉE

### 4.1 Backend Django / DRF — 22 applications métier

| Application | Rôle | Application | Rôle |
| :--- | :--- | :--- | :--- |
| `authentication` | Comptes, JWT, MFA | `graduation` | Diplômation, scellement SHA-256 |
| `habilitations` | **CURP** — rôles/permissions métier | `stages` | Conventions de stage |
| `formations` | Formations, modules, participants, QR | `administrations` | Courriers, GED, directions |
| `scolarite` | Maquettes, UE/ECUE, inscriptions, groupes | `ressources_humaines` | Agents, fonctions, charges |
| `admissions` | Campagnes, concours, candidatures | `patrimoine` | Équipements, véhicules, espaces |
| `edts` | **GET-INJS** — emplois du temps, créneaux | `parametres` | Paramètres métier |
| `presences` | QR, pointages, émargement, géofence | `referentiels` | Référentiels INJS |
| `suiviEvaluation` | Évaluations, notes, rattrapages | `equivalences` | Équivalences / dispenses |
| `jurys` | Sessions de jury, PV | `finances_etudiantes` | Frais, factures, quittances |
| `statistiques` | Point journalier 17 colonnes, BI | `exports` | Exports / rapports |
| `dashboard` | Tableaux de bord CPFAE | `core` | Audit, compteurs, socle |

**API** : **471** déclarations `path()` réparties sur 23 fichiers `urls.py` ; **479 occurrences** de `permission_classes`.
Authentification par défaut `IsAuthenticated` + `JWTAuthentication`, throttling `login 20/min`,
`scan 60/min`, `offline_data 60/min`, CORS strict (`CORS_ALLOW_ALL_ORIGINS = False`).
⚠️ Un répertoire `backend/referentiel_injs/` existe mais **n'est pas déclaré** dans `INSTALLED_APPS` : code résiduel
sans effet (les rôles sont chargés par la commande `charger_referentiel_injs` de `habilitations/`).

### 4.2 Frontend React / Vite

- **74** `<Route>` dans `App.jsx` (71 `path` distincts) **+ ~70 routes génériques générées dynamiquement**
  depuis `menu/arborescence.js` via `menu/routesGeneriques.jsx` → **≈ 144 routes réelles** à l'exécution.
- 82 pages non-test + 135 fichiers `.jsx` sous `src/pages/`.
- **89 fichiers de test, 1 747 tests Vitest — TOUS VERTS (durée 139,8 s)**.
- Ports figés : API **8000** (`arena/lancer-api.sh`), site **3000** (`frontend/vite.config.js`, `strictPort: true`).

### 4.3 Mobile Flutter (`qr_badge_mobile/`)

- Services : `scan_service.dart`, `session_provider.dart`, `location_permission.dart`,
  `device_telemetry_service.dart`, `background_keepalive.dart`.
- Endpoints appelés : **`/api/scan/secure/`**, `/api/scan/secure/heartbeat/`, `/api/scan/secure/check-status/`.
- **Aucun appel à `/api/presences/seances-edt/scan/`** (voir §9 — rupture d'intégration n° 1).

### 4.4 Base de données

PostgreSQL 16 local, base `injs_lmd_current`, **236 migrations toutes appliquées**
(`manage.py showmigrations` : 236 `[X]`, 0 `[ ]`).
Tests Django sur `test_injs_lmd_current` (base dédiée, créée/détruite automatiquement — jamais la base de dev).

### 4.5 Environnement d'exécution de l'audit

Sandbox SQLite dédiée : `arena/settings_sandbox.py` + `backend/db_sandbox.sqlite3` (non suivi par Git),
`PYTHONPATH=..`, interpréteur `.venv-ci/bin/python`. **Aucune écriture sur `injs_lmd_current` durant l'audit.**

---

## 5. MATRICE DE TRAÇABILITÉ — SOURCES → MODULES CIBLES

| ID | Source | Module cible (réf.) | Backend | Frontend | BDD | Tests |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| EX-01 | S03/04 | Référentiels INJS | `referentiels/`, `formations/ref*.py` | `pages/referentiels*` | `refsite/salle/batiment/vague/categorie/grade` | ✔ |
| EX-02 | S03/05 | Formations & maquettes LMD | `formations/`, `scolarite/models.py` | `pages/Modules`, `Maquettes` | `scolarite_maquette/ue/ecue` | ✔ |
| EX-03 | S03/06 | Campagnes, candidatures, admissions | `admissions/` | `Candidatures`, `Admissions` | `admissions_*` | ✔ |
| EX-04 | S03/07 | Inscriptions & scolarité | `scolarite/inscription_api.py` | `Inscriptions`, `FicheEtudiant` | `scolarite_inscription*` | ✔ |
| EX-05 | S03/08 | Équivalences & dispenses | `equivalences/` | `Equivalences` | `equivalences_*` | ✔ |
| EX-06 | S03/09 | Enseignants & charges horaires | `scolarite/charges_urls.py` | `ChargesEnseignants` | `scolarite_affectationpedagogique` | ✔ |
| EX-07 | S03/10 | Emplois du temps & espaces (GET-INJS) | `edts/` — 28 routes, 2 alias `api/edts/` + `api/timetable/` | `EdtPresences` | `edts_*` | ✔ |
| EX-08 | S03/11 | Présences (QR + géoloc) | `presences/` — 24 `permission_classes` | `EdtPresences.jsx` | `presences_pointage/auditlog` | ✔ |
| EX-09 | S03/12 | Évaluations, notes, rattrapages | `suiviEvaluation/` | `CoursLmd` | `suiviEvaluation_*` | ✔ |
| EX-10 | S03/13 | Jurys | `jurys/` | `Jurys` | `jurys_*` | ✔ |
| EX-11 | S03/14 | Diplomation & documents | `graduation/` | `Graduation` | `graduation_diplome` | ✔ |
| EX-12 | S03/15 | Frais de scolarité & paiements | `finances_etudiantes/` | `FinancesEtudiantes`, `FinanceParametrage` | `finances_*` | ✔ |
| EX-13 | S03/17 | Statistiques & décisionnel | `statistiques/`, `dashboard/` | `PointJournalierCPFAE` | `statistiques_*` | ◐ |
| EX-14 | S03/18 | Sécurité, RBAC, audit | `habilitations/`, `core/` | `pages/habilitations/*` (14 tests) | `habilitations_*` (1 157 perms) | ✔ |
| EX-15 | S03/20 | Application mobile Flutter | `presences/views.py` (`/api/scan/secure/`) | — | `presences_devicebinding` | ◐ |
| EX-16 | S03/21 | Migration des données existantes | `import_excel`, `import_maquette`, `rattacher_comptes_legacy` | — | — | ◐ |
| EX-17 | S03/22 | Tests & assurance qualité | `backend/**/test*.py` (129 fichiers) | 89 fichiers Vitest | `test_injs_lmd_current` | ✔ |
| EX-18 | S03/03 | Socle technique | `config/settings.py`, `arena/` | `vite.config.js` | — | ✔ |

Légende : ✔ vérifié et exécuté · ◐ partiellement vérifié (voir §19) · ✖ rupture détectée (voir §9)

---

## 6. MATRICE DES MODULES — CLASSIFICATION FINALE

Référence : 18 modules du modèle fonctionnel (S02).
**Règle de statut retenue** : le statut final est le **pire** entre l'état du code et l'état des données,
puisque S01 impose une vérification « par exécution d'un parcours fonctionnel ».

| # | Module | Statut | Preuve principale |
| :-- | :--- | :--- | :--- |
| M01 | Référentiels & import Excel | **[Validé et opérationnel]** | `seed_lot1_1` : 4 types de formation, 5 niveaux, 10 semestres, 58 salles, 10 bâtiments ; `import_excel.py` présent |
| M02 | Formations & maquettes LMD | **[non opérationnel]** | Code OK (seed « L3 Professorat STAPS 2026-2027 », 30 ECTS) mais **`scolarite_maquette` = 0 ligne** en base officielle |
| M03 | Admissions & campagnes | **[implémentation]** | 1 campagne, 1 candidat, 1 candidature, 2 épreuves, 5 types de pièce — mais `admissions_admission` = 0 |
| M04 | Scolarité & inscriptions | **[implémentation]** | `scolarite_inscriptionadministrative` = 0, `…pedagogique` = 0, `…dossieretudiant` = 0 |
| M05 | Étudiants & groupes | **[implémentation]** | `scolarite_groupe` = 0, `scolarite_affectationgroupe` = 0 — la matriculation INJS26-XXXX n'existe que dans le seed |
| M06 | Cours / ECUE / séances | **[Validé et opérationnel]** | `scolarite_ue`/`ecue` alimentés par seed ; **137 tests `presences`+`edts` OK** |
| M07 | Enseignants & charges | **[Validé et opérationnel]** | `seed_lot4_1` : 5 formateurs, 310 h validées, 0 anomalie de charge |
| M08 | **Emplois du temps (GET-INJS)** | **[Validé et opérationnel]** | `edts` : 21 `permission_classes`, 28 routes, 2 alias ; 0 conflit sur 9 affectations ; inclus dans les 137 tests OK |
| M09 | **Présences / QR / badgeage** | **[non opérationnel]** | Moteur testé (`test_seances_edt.py`, `/api/scan/secure/`) mais **aucun client n'appelle `/api/presences/seances-edt/scan/`** — §9-1 |
| M10 | **Géolocalisation** | **[non opérationnel] — P0** | **Absente du canal EDT** (`badger_scan` n'appelle pas `_check_geofence`, § 21 bis) **et** neutralisée sur le legacy (site `geofence_latitude = NULL`) ; 34/34 pointages sans GPS |
| M11 | Évaluations & notes | **[implémentation]** | Code OK (`seed_lot3_1` : 6 modules évalués, verrouillés) ; tables `suiviEvaluation_*` **vides** en base officielle |
| M12 | Jurys & délibérations | **[implémentation]** | Code OK (PV + SHA-256 par seed) ; `jurys_sessionjury` = 0, `jurys_pvjury` = 0 |
| M13 | Diplomation | **[implémentation]** | Code OK (6 diplômes certifiés par seed) ; `graduation_diplome` = 0 |
| M14 | Finances étudiantes | **[implémentation]** | Code OK (3 tarifs, 6 factures, 18 quittances, 960 000 XOF rapprochés) ; tables vides |
| M15 | Stages professionnels | **[implémentation]** | Code OK (6 conventions VALIDEE_JURY) ; `stages_conventionstage` = 0 |
| M16 | Administration & GED | **[implémentation]** | Code OK (3 directions, 2 départements, 2 courriers, 2 documents) ; `administrations_*` = 0 |
| M17 | RH & patrimoine | **[implémentation]** | Code OK (3 services, 3 agents, 5 équipements, 3 véhicules) ; tables vides |
| M18 | **Statistiques / BI** | **[non opérationnel] — P1** | `filter_sessions()` lit **exclusivement** `SessionModule` → les `Pointage(seance_edt=…, session=None)` sont invisibles ; `seed_injs_complet` affiche « **0 tableau(x) généré(s)** » puis « ✓ certifié conforme » — **faux positif** |

---

## 7. MATRICE DES FONCTIONNALITÉS (extrait des plus significatives)

| ID | Fonctionnalité | Existence | Implémentation | Fonctionnement | Cohérence métier | Statut |
| :-- | :--- | :--- | :--- | :--- | :--- | :--- |
| F-01 | Génération du QR de séance LMD | présente | backend + BDD (`QRToken.seance_edt`, mig. `0094`) | testé (`test_seances_edt.py`) | conforme | **[Validé et opérationnel]** |
| F-02 | Scan QR par l'app mobile sur séance LMD | **absente** | aucun client | non exécuté | — | **[implémentation]** |
| F-03 | Scan QR legacy `/api/scan/secure/` | présente | backend + mobile | 137 tests backend OK | conforme | **[Validé et opérationnel]** |
| F-04 | Géolocalisation (haversine + rayon site) — **canal legacy uniquement** | présente | `presences/views.py:526-608` | tests OK mais **site sans coordonnées** | **absente du canal EDT** (§ 21 bis) | **[non opérationnel] — P0** |
| F-05 | Précision GPS maximale (80 m) | présente | `MOBILE_GEOFENCE_MAX_ACCURACY_M` | testable | **contrôle contournable** : si `accuracy_m` non envoyé, aucun test de précision | **[non opérationnel]** |
| F-06 | Badgeage manuel / forcé à motif | présente | `seances_edt_services` (motif obligatoire 08.14) | 137 tests OK | conforme | **[Validé et opérationnel]** |
| F-07 | Clôture automatique de séance | présente | `auto_close_pointages.py`, `auto_close_sessions.py` | commandes disponibles | conforme | **[Validé et opérationnel]** |
| F-08 | Détection de conflits d'EDT | présente | `edts_conflitcreneau` | seed : 0 conflit / 9 affectations | conforme | **[Validé et opérationnel]** |
| F-09 | EDT → génération des séances | présente | `edts/AffectationCreneau` | 137 tests OK | conforme | **[Validé et opérationnel]** |
| F-10 | Présences EDT → Statistiques / BI | **absente** | aucune passerelle `seance_edt` dans `statistiques/` | « 0 tableau(x) généré(s) » | **rupture** | **[non opérationnel]** |
| F-11 | RBAC CURP (`ExigePermission`, `ExigeDrapeauAdmin`) | présente | 81 rôles, 1 157 permissions, 10 453 relations | 14 tests `habilitations` | conforme | **[Validé et opérationnel]** |
| F-12 | Point journalier 17 colonnes | présente | `statistiques/point_journalier.py` | exécuté — **0 tableau** | faux « certifié conforme » | **[non opérationnel]** |
| F-13 | Diplômation avec scellement SHA-256 | présente | `graduation/` | seed : 6 diplômes vérifiés | conforme | **[Validé et opérationnel]** (code) |
| F-14 | Rapprochement bancaire | présente | `finances_etudiantes/` | seed : 960 000 XOF / 18 quittances | conforme | **[Validé et opérationnel]** (code) |
| F-15 | Migration Excel / maquette | présente | `import_excel.py`, `import_maquette.py` | exécuté dans la chaîne de seed | conforme | **[Validé et opérationnel]** (code) |
| F-16 | Smoke test de certification | présente | `smoke_test_injs.py` | **échoue** (SMOKE-01-CAMPAGNE) sur base ayant déjà une année courante | non idempotent | **[non opérationnel]** |
| F-17 | Script E2E intégré | présente | `tests_e2e_injs_2026_2027.py` | **crash `AttributeError`** | non robuste | **[non opérationnel]** |

---

## 8. MATRICE DES PARAMÈTRES ET RÉFÉRENTIELS

Relevé sur `injs_lmd_current` (40 lignes `parametres_parametre`).

| Paramètre / référentiel | Existence | Défaut | Configurable | Utilisé réellement | Cohérence | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `annee_academique_courante` (paramètre) | ✔ | **`2025-2026`** | ✔ | **❌ jamais lu par le code** (unique occurrence : migration `parametres/0002`) | ❌ **obsolète et incohérente** : `scolarite_anneeacademique` contient **une seule ligne `2026-2027` avec `courante = True`** | **[non opérationnel]** |
| `AnneeAcademique.courante` (BDD) | ✔ | contrainte `uniq_annee_academique_courante` | ✔ | ✔ (source réelle) | ✔ — c'est la **seule** source de vérité | **[Validé et opérationnel]** |
| `MOBILE_GEOFENCE_DEFAULT_RADIUS_M` | ✔ | 200 | ✔ env | ✔ | ✔ | **[Validé et opérationnel]** |
| `MOBILE_GEOFENCE_MAX_ACCURACY_M` | ✔ | 80 | ✔ env | partiel | ⚠ dépend du client | **[implémentation]** |
| `MOBILE_GEOFENCE_OUTSIDE_CONFIRMATIONS` | ✔ | 2 | ✔ env | à vérifier | — | **[à vérifier]** |
| `presences.edt.ouverture_anticipee_minutes` | ✔ | 10 | ✔ `Parametre` | ✔ (Lot C) | ✔ | **[Validé et opérationnel]** |
| `presences.edt.tolerance_retard_minutes` | ✔ | 10 | ✔ | ✔ | ✔ | **[Validé et opérationnel]** |
| `presences.edt.tolerance_cloture_minutes` | ✔ | 15 | ✔ | ✔ | ✔ | **[Validé et opérationnel]** |
| `formations_refsite.geofence_*` | ✔ colonnes | `NULL / NULL / 200` | ✔ | **❌ jamais lu** (NULL) | ❌ | **[non opérationnel]** |
| Niveaux / grades / vagues / types de formation | ✔ | 5 / 8 / 15 / 4 | ✔ | ✔ | ✔ | **[Validé et opérationnel]** |
| Salles / bâtiments / sites | ✔ | 58 / 10 / 1 | ✔ | ✔ | ⚠ 1 seul site, sans geofence | **[implémentation]** |
| Semestres / régimes / statuts étudiants | ✔ | 10 / 4 / 6 | ✔ | ✔ | ✔ | **[Validé et opérationnel]** |
| 22 types de secrétariat | ✔ | 22 | ✔ | ✔ | ✔ | **[Validé et opérationnel]** |
| Seuils d'alerte statistiques | ✔ | 6 config | ✔ | ✔ | ✔ | **[Validé et opérationnel]** |

---

## 9. MATRICE DES INTERACTIONS INTER-MODULES (phase critique)

| # | Module A → Module B | Donnée / événement | Constat | Résultat réel | Statut |
| :-- | :--- | :--- | :--- | :--- | :--- |
| I-01 | Référentiels → Formations | `RefSite`, `RefSalle`, `RefBatiment`, `RefVague`, `RefCategorie` | 8 formations, 58 salles, 10 bâtiments, 15 vagues, 10 sites-liés | ✔ les 8 formations ont une `ref_formation` | **[Validé et opérationnel]** |
| I-02 | Formations → Cours/ECUE | `Formation → Module → ECUE` | 10 modules, `scolarite_ue`/`ecue` alimentés par seed | ✔ | **[Validé et opérationnel]** |
| I-03 | Cours/ECUE → Séances | `ECUE → AffectationCreneau` | `edts_affectationcreneau` dans la chaîne de seed (9 affectations) | ✔ 137 tests | **[Validé et opérationnel]** |
| I-04 | Formations → Groupes → Étudiants | `Groupe`, `AffectationGroupe`, `Participant` | `formations_participant` = 14, mais **`scolarite_groupe` = 0**, `scolarite_affectationgroupe` = 0 | ❌ aucune affectation de groupe en base officielle | **[implémentation]** |
| I-05 | Enseignants → Cours/Séances | `Formateur → ModuleFormateur` | `formations_formateur` = 3, `moduleparticipant` = 45 | ✔ | **[Validé et opérationnel]** |
| I-06 | Salles → EDT | `RefSalle → AffectationCreneau.salle` | 58 salles, 0 affectation en base officielle | ⚠ chaîne non exercée | **[implémentation]** |
| I-07 | EDT → Séances | `CreneauTemplate → AffectationCreneau` | code présent, tests OK, **0 ligne** en base officielle | ⚠ | **[implémentation]** (données) |
| I-08 | **Séances → Présences (canal legacy)** | `SeanceEdt → Pointage.seance_edt` | `seances_edt_services.py` crée le `Pointage` | ✔ 137 tests OK | **[Validé et opérationnel]** |
| I-09 | **Séances → Présences (canal legacy `SessionModule`)** | `SessionModule → Pointage.session` | 8 sessions, **34/34 pointages ont `session_id`** | ✔ | **[Validé et opérationnel]** |
| I-10 | **QR → Présences** | `QRToken → Pointage` | `formations_qrtoken` = 0 en base officielle → aucun QR émis | ⚠ le mécanisme est testé, pas de QR réel | **[implémentation]** |
| I-11 | **Géolocalisation → QR/Présences (canal legacy)** | `RefSite.geofence → _check_geofence` (appelée) | **`geofence_latitude = NULL`** sur `INJS MARCORY` | ❌ contrôle **toujours accordé** ; 34/34 pointages sans GPS | **[non opérationnel] — P0 (N-01)** |
| **I-21** | **Géolocalisation → QR/Présences (canal EDT)** | `badger_scan()` **n'appelle pas** `_check_geofence` | **Contrôle absent du code** | ❌ aucun refus possible | **[non opérationnel] — P0 (N-12, § 21 bis)** |
| I-12 | **Présences → Statistiques** | `Pointage → filter_sessions → SessionModule` | `seances_edt_services` écrit `session=None` ; **0 occurrence de `seance_edt` dans `statistiques/`** | ❌ « 0 tableau(x) généré(s) » | **[non opérationnel] — P1** |
| I-13 | **Présences → Dashboards / Exports** | idem | **0 occurrence de `seance_edt` dans `dashboard/` et `exports/`** | ❌ | **[non opérationnel] — P1** |
| I-14 | Présences → Notes / Évaluations | `Pointage → suiviEvaluation` | **0 occurrence de `seance_edt` dans `suiviEvaluation/`** | ❌ pas d'assiduité vers les notes | **[implémentation]** |
| I-15 | Jurys → Diplomation | `SessionJury → Diplome` | chaîne testée par `seed_lot3_1` (6 diplômes certifiés) | ✔ code / ❌ données | **[implémentation]** |
| I-16 | Scolarité → Étudiants/Formations/Groupes | `InscriptionAdministrative → DossierEtudiant` | toutes les tables à 0 | ❌ | **[implémentation]** |
| I-17 | GET-INJS → présences (écran enseignant) | `/api/presences/seances-edt/…` consommé par `EdtPresences.jsx` | ✔ front → API | ✔ | **[Validé et opérationnel]** |
| I-18 | **Mobile → EDT (QR géolocalisé)** | `/api/presences/seances-edt/scan/` | **aucun appel dans `qr_badge_mobile/` ni `frontend/`** ; seul `presences/test_seances_edt.py` l'appelle | ❌ **le client n'existe pas** | **[implémentation] — P1** |
| I-19 | `url_badgeage` retourné par l'API QR | `'/presences/scan-edt?token=…'` (seances_edt_api.py:96) | **route frontend `/presences/scan-edt` inexistante** (`grep scan-edt frontend/src` → 0) | ❌ lien retourné à l'utilisateur = page 404 | **[non opérationnel]** |
| I-20 | Habilitations → tous modules | `ExigePermission` / `ExigeDrapeauAdmin` | 479 `permission_classes`, 81 rôles, 1 157 permissions, 1 148 `auth_group_permissions` | ✔ | **[Validé et opérationnel]** |

### 9.1 Rupture n° 1 — le canal EDT n'a aucun client

```
POST /api/presences/seances-edt/scan/          (presences/urls.py:11)
   ⇄ testé par      backend/presences/test_seances_edt.py
   ⇄ JAMAIS appelé  qr_badge_mobile/lib/services/scan_service.dart   → utilise /api/scan/secure/
   ⇄ JAMAIS appelé  frontend/src/**                                 → 0 occurrence de « seances-edt/scan »
```

Deux chaînes de présence coexistent **sans pont** :

| Canal | Modèle support | Client | Présences écrites |
| :--- | :--- | :--- | :--- |
| **Legacy** | `formations.SessionModule` | mobile Flutter (`/api/scan/secure/`) | `session=<SessionModule>`, `seance_edt=None` |
| **LMD / EDT** | `edts.AffectationCreneau` | **aucun** | `session=None`, `seance_edt=<AffectationCreneau>` |

`statistiques/`, `dashboard/`, `exports/`, `suiviEvaluation/` ne lisent que le canal legacy.
→ **Le module 09 Présences et le module 18 Statistiques sont donc découplés par construction.**

### 9.2 Rupture n° 2 — géolocalisation morte-née sur la base officielle

```python
# presences/views.py :568
if site is None or site.geofence_latitude is None or site.geofence_longitude is None:
    return None, None, None          # → aucune contrainte de position
# presences/views.py :580
site_lat, site_lon, rayon_m = _resolve_site_geofence(module)
if site_lat is None or site_lon is None:
    return True, None, None, None, None   # ← ACCORDÉ SANS VÉRIFICATION
```

Base officielle : `select geofence_latitude, geofence_longitude from formations_refsite` → `(NULL, NULL, 200)`.
`seed_lot1_1_injs.py:62-64` pose bien `(5.302500, -3.978500, 300)`, mais **ce seed n'a jamais été exécuté sur `injs_lmd_current`**
(le nom du site y est `INJS MARCORY` et non « Campus INJS Marcory (Abidjan) »).

---

## 10. AUDIT EMPLOIS DU TEMPS (GET-INJS)

**Parcours vérifié** : configuration → formations → groupes → enseignements → enseignants → salles →
créneaux → séances → conflits → publication → consultation.

| Contrôle | Constat | Statut |
| :--- | :--- | :--- |
| Création / modification / suppression de créneau | `edts/api.py` — 21 `permission_classes` (`IsEdtPlanification`, `IsEdtValidation`, `IsEdtReadOnlyOrPlanification`) | **[Validé et opérationnel]** |
| Affectation enseignant / groupe / salle | `AffectationCreneau` (FK enseignant, groupe, salle) | **[Validé et opérationnel]** |
| Chevauchement / conflit | `edts_conflitcreneau` + seed : **0 conflit sur 9 affectations** | **[Validé et opérationnel]** |
| Capacité de salle | contrôle présent dans `edts/api.py` | **[Validé et opérationnel]** |
| Cohérence date/heure | contrôles de fenêtre (10 min avant / 15 min après) | **[Validé et opérationnel]** |
| Génération des séances | `CreneauTemplate → AffectationCreneau` | **[Validé et opérationnel]** (code) / **[implémentation]** (BDD : 0 ligne) |
| Propagation aux présences | `presences/seances_edt_services.py` | **[Validé et opérationnel]** (code) |
| Double exposition API | `api/edts/` **et** `api/timetable/` → mêmes vues (alias volontaire, P11) | **[Validé et opérationnel]** |
| Consommation front | `EdtPresences.jsx` appelle `/api/presences/seances-edt/*` | **[Validé et opérationnel]** |
| **Alimentation réelle de l'EDT** | `edts_*` toutes vides sur `injs_lmd_current` | **[implémentation]** |

**Verdict EDT** : l'EDT n'est **pas** un simple écran CRUD — il alimente bien `AffectationCreneau` et le service de présence
Lot C, et cela est couvert par 137 tests exécutés. **Mais il n'y a aucune donnée d'EDT en base officielle**, donc le parcours
bout-en-bout n'est pas démontrable sur `injs_lmd_current`.

---

## 11. AUDIT COURS / SÉANCES / FORMATIONS

Cycle vérifié : `Formation → Module/ECUE → Enseignement → Formateur → Groupe → Séance → Salle → EDT → Présence`.

| Contrôle | Constat | Statut |
| :--- | :--- | :--- |
| Rattachement Formation → RefFormation | 8/8 formations rattachées | **[Validé et opérationnel]** |
| Volumes horaires | commandes `diag_volume_horaire.py`, `recalc_durees_pointages.py` | **[Validé et opérationnel]** |
| Statut séance (passée / en cours / future) | `SessionModule.terminee_le`, statuts de séance EDT | **[Validé et opérationnel]** |
| Annulation / report | `formations/session_edt_balance.py`, `auto_close_sessions.py` | **[Validé et opérationnel]** |
| Génération des participants attendus | `ModuleParticipant` (45 lignes) | **[Validé et opérationnel]** |
| Cohérence avec l'EDT | `formations/test_session_edt_balance.py` | **[Validé et opérationnel]** |
| Inscr. pédagogique → groupe → séance | tables scolarité à 0 en base officielle | **[implémentation]** |

---

## 12. AUDIT PRÉSENCES QR CODE — LES DEUX MODES

### Mode A1 — Badgeage automatique **legacy** (`/api/scan/secure/`, `SessionModule`)

| Étape | Implémentation | Constat | Statut |
| :--- | :--- | :--- | :--- |
| Identification utilisateur | JWT + `CompteUtilisateur` | ✔ | **[Validé et opérationnel]** |
| Séance active | `SessionModule` + fenêtre de temps | ✔ | **[Validé et opérationnel]** |
| Personne autorisée | `participant_scope`, `ModuleFormateur`, `_encadrant_can_badge_module` | ✔ | **[Validé et opérationnel]** |
| **Géolocalisation** | `_check_geofence` appelée (`views.py:1152`) | ❌ **neutralisée** : site sans coordonnées | **[non opérationnel]** |
| Position obligatoire | `LOCATION_REQUIRED` **seulement si** geofence active (`views.py:1140`) | ⚠️ conditionnel | **[non opérationnel]** (site NULL) |
| Contrôle horaire | ouverture 10 min, tolérance retard 10 min, clôture 15 min | ✔ paramétrable | **[Validé et opérationnel]** |
| Anti-duplication | pointage existant / token révoqué → refus | ✔ | **[Validé et opérationnel]** |
| Création présence | `Pointage.objects.create(...)` | ✔ | **[Validé et opérationnel]** |
| Timestamp / statut | `timestamp_entree/sortie`, `duree_presence_minutes` | ✔ | **[Validé et opérationnel]** |
| Journal / audit | `AuditLog` (`SCAN_SECURE_ENTREE`, `SCAN_HEARTBEAT`, `OUT_OF_GEOFENCE`) | ✔ 72 lignes d'audit | **[Validé et opérationnel]** |
| Retour utilisateur | payload `distance_m` / `rayon_m` / `accuracy_m` | ✔ | **[Validé et opérationnel]** |
| Heartbeat continu | `/api/scan/secure/heartbeat/` + `outside_geofence_count ≥ 2 → SORTIE_AUTO` | ✔ `views.py:1215-1410` | **[Validé et opérationnel]** |

### Mode A2 — Badgeage automatique **EDT** (`/api/presences/seances-edt/scan/`, `AffectationCreneau`)

| Étape | Implémentation | Constat | Statut |
| :--- | :--- | :--- | :--- |
| Identification utilisateur | JWT + `_resolve_authenticated_personne` | ✔ | **[Validé et opérationnel]** |
| QR de séance LMD | `QRToken.seance_edt`, `is_valid`, remplacement si expiré | ✔ | **[Validé et opérationnel]** |
| Séance du jour | `est_seance_du_jour(affectation, date)` → `HORS_SEANCE` | ✔ | **[Validé et opérationnel]** |
| Réservé aux participants | `BADGE_RESERVE_AUX_PARTICIPANTS` (formateurs exclus) | ✔ | **[Validé et opérationnel]** |
| Personne autorisée | `membres_groupe(affectation)` → `NOT_IN_LIST` (403) | ✔ | **[Validé et opérationnel]** |
| Changement de mot de passe | `PASSWORD_CHANGE_REQUIRED` (403) | ✔ | **[Validé et opérationnel]** |
| **Géolocalisation** | **`_check_geofence` NON APPELÉE** (§ 21 bis) | ❌ **absente du code** | **[non opérationnel] — P0 (N-12)** |
| Position obligatoire | ❌ aucun contrôle (`LOCATION_REQUIRED` inexistant ici) | ❌ | **[non opérationnel] — P0** |
| Refus hors zone / précision | ❌ aucun contrôle | ❌ | **[non opérationnel] — P0** |
| Contrôle horaire | `fenetre_scan` : `TROP_TOT` / `HORS_FENETRE` | ✔ paramétrable | **[Validé et opérationnel]** |
| Anti-duplication | `select_for_update()` : 1 entrée + 1 sortie, `ALREADY_SCANNED` | ✔ | **[Validé et opérationnel]** |
| Création présence | `Pointage.objects.create(session=None, seance_edt=…)` | ✔ | **[Validé et opérationnel]** |
| Statut d'assiduité | `PRESENT` / `RETARD` (seuil paramétrable) | ✔ | **[Validé et opérationnel]** |
| Journal / audit | `_log_scan(SCAN_SECURE_ENTREE / SCAN_SECURE_SORTIE)` | ✔ | **[Validé et opérationnel]** |
| Heartbeat / sortie auto | **aucun endpoint** sur ce canal | ❌ | **[implémentation]** |
| Client réel | **aucun** (ni mobile, ni front) | ❌ | **[non opérationnel] — P1 (N-03)** |

### Mode B — Badgeage manuel / forcé à motif

| Exigence (S01 phase 10.B) | Constat | Statut |
| :--- | :--- | :--- |
| Qui peut forcer / rôle / permission | `IsSecretariatOrDFRC` (4 usages), garde-fous métier | **[Validé et opérationnel]** |
| Sélection personne / séance | `emargement_seance`, émargement de masse | **[Validé et opérationnel]** |
| **Motif obligatoire** | `seances_edt_services.py:375-378` : `raise ErreurEmargement` si `motif` absent — **uniquement pour corriger un pointage existant** (règle 08.14) | **[Validé et opérationnel]** (correction) / **[à valider]** (émargement simple) |
| Traçabilité de l'auteur | `AuditLog.Action.FORCE_ENTREE` + `device_id='EMARGEMENT_MANUEL'` | **[Validé et opérationnel]** |
| Origine forcée non masquable | `Pointage.Statut.FORCE_DFRC` distinct de `EN_COURS`/`TERMINE` | **[Validé et opérationnel]** |
| Absence = ligne administrative de durée 0 | `seances_edt_services.py:361-372` | **[Validé et opérationnel]** |

### Cas négatifs (S01 phase 10)

| Cas | Comportement constaté | Statut |
| :--- | :--- | :--- |
| Double badgeage | refus (pointage existant / token révoqué) | **[Validé et opérationnel]** |
| Badgeage hors séance | refus (`SESSION_TERMINED`, hors fenêtre) | **[Validé et opérationnel]** |
| Personne non inscrite | HTTP 403 `NOT_IN_LIST` | **[Validé et opérationnel]** |
| QR expiré / désactivé | code `TOKEN_EXPIRED` + remplacement par token actif | **[Validé et opérationnel]** |
| QR d'une autre séance / sans séance | code `NO_SESSION` (`views.py:1280`) | **[Validé et opérationnel]** |
| Sans authentification | `IsAuthenticated` global → 401 | **[Validé et opérationnel]** |
| Hors zone | code `OUT_OF_GEOFENCE` présent **mais** jamais déclenché (site NULL) | **[non opérationnel]** |
| Géolocalisation absente | refus seulement **si le site a une geofence** → jamais ici | **[non opérationnel]** |
| Précision GPS insuffisante | code `LOCATION_INACCURATE` **non déclenchable** si `accuracy_m` est omis | **[implémentation]** |
| GPS refusé / simulation / spoofing | permission mobile non exécutée dans cet audit | **[à vérifier]** |

---

## 13. AUDIT DU BADGEAGE AUTOMATIQUE

Détail de la chaîne réellement exécutée (modèle 08 appliqué au legacy comme à l'EDT) :

| Élément | Fichier / fonction | Constat | Statut |
| :--- | :--- | :--- | :--- |
| Entrée unique | `POST /api/scan/secure/` (`presences/views.py:636`) | mobile Flutter → `scan_service.dart:22` | **[Validé et opérationnel]** |
| Entrée EDT (sans client) | `POST /api/presences/seances-edt/scan/` (`presences/urls.py:11`) | **0 appelant hors tests** | **[implémentation]** |
| Heartbeat | `POST /api/scan/secure/heartbeat/` (`views.py:882`) | `session_provider.dart:127` | **[Validé et opérationnel]** |
| État / position | `GET /api/scan/secure/check-status/` (`views.py:87`) | `scan_page.dart:52` | **[Validé et opérationnel]** |
| Période hors-ligne | `offline_data` (v1/v2) + `process_mobile_heartbeats.py` | commandes présentes | **[Validé et opérationnel]** |
| Escalade hors zone | `outside_geofence_count ≥ 2 → SORTIE_AUTO` | `views.py:1379-1420` | **[Validé et opérationnel]** (code) / **[non opérationnel]** (données) |
| Statut suspect | `Pointage.Statut.HORS_LIGNE_SUSPECT` réintégré si géofence OK | `views.py:1336-1337` | **[Validé et opérationnel]** |
| Throttling | `scan 60/min` | `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']` | **[Validé et opérationnel]** |
| Liaison appareil | `presences_devicebinding` | table présente (0 ligne) | **[implémentation]** |

**Le badgeage automatique est opérationnel sur le canal legacy. Il ne l'est pas sur le canal EDT LMD.**

---

## 14. AUDIT DU BADGEAGE MANUEL / FORCÉ

| Point de contrôle | Preuve | Statut |
| :--- | :--- | :--- |
| Rôle habilité | `IsSecretariatOrDFRC` (4 usages) + CURP `ExigePermission` | **[Validé et opérationnel]** |
| Motif obligatoire (règle 08.14) | `seances_edt_services.py:375-378` : `raise ErreurEmargement` si `motif` absent — **uniquement en correction d'un pointage existant** | **[Validé et opérationnel]** (correction) / **[à valider]** (émargement simple) |
| Statut distinct | `Pointage.Statut.FORCE_DFRC`, `device_id = 'EMARGEMENT_MANUEL'` | **[Validé et opérationnel]** |
| Audit incompressible | `AuditLog.Action.FORCE_ENTREE` | **[Validé et opérationnel]** |
| Absence opposable | ligne de durée 0 créée pour chaque absent (`seances_edt_services.py:361-372`) | **[Validé et opérationnel]** |
| Oubli de `statut_assiduite` | **les 34 pointages de la base officielle ont `statut_assiduite = NULL`** | **[non opérationnel]** |
| Écran front | `EdtPresences.jsx` (émargement enseignant) | **[Validé et opérationnel]** |

---

## 15. AUDIT GÉOLOCALISATION

### 15.1 Canal LEGACY — `/api/scan/secure/` (implémenté)

| Point (S01 phase 9) | Constat | Statut |
| :--- | :--- | :--- |
| Source GPS | mobile Flutter (`location_permission.dart`, `device_telemetry_service.dart`) | **[à vérifier]** (non exécuté dans cet audit) |
| Latitude / longitude / précision | champs `last_latitude/longitude/accuracy_m` sur `Pointage` | **[Validé et opérationnel]** (schéma) |
| Rayon autorisé / centre géographique | `RefSite.geofence_*`, défaut `MOBILE_GEOFENCE_DEFAULT_RADIUS_M = 200` | **[non opérationnel]** (NULL en base) |
| Calcul de distance | **haversine**, `earth_radius_m = 6371000`, `views.py:526-535` | **[Validé et opérationnel]** |
| Tolérance | rayon 200 m, précision max 80 m, sortie auto après 2 heartbeats hors zone | **[Validé et opérationnel]** (code) |
| Absence de coordonnées | refus **uniquement si le site a une geofence** → `views.py:1140` | **[non opérationnel]** (site non configuré) |
| Coordonnées invalides | `latitude` XOR `longitude` → « doivent être fournies ensemble » | **[Validé et opérationnel]** |
| Comportement hors zone | `OUT_OF_GEOFENCE` + `SORTIE_AUTO` après `outside_limit` heartbeats | **[Validé et opérationnel]** (code) |
| Journalisation | `AuditLog` + `extra {distance_m, rayon_m, accuracy_m, outside_geofence_limit}` | **[Validé et opérationnel]** |
| **Utilisation dans la décision** | **oui** : `_check_geofence()` (`views.py:1152`, `:1322`) **précède** la création du pointage | **[Validé et opérationnel]** (code) |
| Preuve d'usage réel | 34/34 pointages sans GPS ; `formations_refsite` : `geofence_latitude = NULL` | **[non opérationnel] — P0** |

### 15.2 Canal EDT — `/api/presences/seances-edt/scan/` (**corrigé le 26/09/2026 — N-12**)

| Point | Constat | Statut |
| :--- | :--- | :--- |
| Collecte de la position | `coords` transmis à `badger_scan()` et stocké via `**(coords or {})` | ✔ **[Validé et opérationnel]** |
| **Contrôle de zone** | appelé via `_controle_geofence_edt()` **avant** la création du pointage | ✔ **[Validé et opérationnel]** (N-12) |
| **Position obligatoire** | `LOCATION_REQUIRED` si le site est géolocalisé | ✔ **[Validé et opérationnel]** (N-12) |
| **Refus hors zone** | `OUT_OF_GEOFENCE` + journalisation (alerte) | ✔ **[Validé et opérationnel]** (N-12) |
| **Refus précision insuffisante** | `LOCATION_INACCURATE` | ✔ **[Validé et opérationnel]** (N-12) |
| Règle dupliquée | **non** — module partagé `presences/geofence.py` | ✔ **[Validé et opérationnel]** |
| Couverture de test | **8 tests dédiés**, dont le refus de l'ancienne géofence du seed | ✔ **[Validé et opérationnel]** |
| Heartbeat / sortie automatique | **aucun endpoint** sur ce canal | **[implémentation]** |

**Conclusion géolocalisation** : la géolocalisation intervient dans la décision sur **les deux canaux**, avec une
règle unique (module `presences/geofence.py`). Sur le legacy, le code était correct mais neutralisé par la donnée
(site sans coordonnées) — **N-01** et **N-11** traitent ce point. Le canal EDT, qui ne contrôlait rien, est
**corrigé et testé**. Ce qu'il reste : la base officielle doit porter les coordonnées officielles pour que le
contrage soit effectif, et le **rayon reste à confirmer** (200 m appliqué par défaut).

---

## 16. TESTS END-TO-END — 4 SCÉNARIOS CRITIQUES

### 16.1 Résultats

| Scénario | Description | Résultat | Preuve |
| :--- | :--- | :--- | :--- |
| **E2E-01** | Formation → module/ECUE → groupe → enseignant → salle → créneau → séance publiée | **BLOCKED** | Impossible sur `injs_lmd_current` : `scolarite_groupe` = 0, `edts_*` = 0. Réalisable en sandbox **uniquement après** `seed_injs_complet`. |
| **E2E-02** | Séance publiée → QR → contrôles → géolocalisation → badgeage → présence en base → affichage front | **FAIL** | Le contrôle de géolocalisation **n'existe pas** sur ce canal (`badger_scan`, § 21 bis) ; le chemin legacy `/api/scan/secure/` est **couvert par 137 tests backend OK** mais n'est pas le canal INJS-LMD. |
| **E2E-03** | Badgeage manuel forcé avec motif → traçabilité → origine forcée | **PASS** (unitaire) | `presences/test_seances_edt.py` + `seances_edt_services` (motif obligatoire, `FORCE_DFRC`, `AuditLog`). |
| **E2E-04** | Cas négatifs : mauvaise séance, hors horaire, hors zone, non autorisé, double badgeage, non authentifié, QR invalide, GPS refusé | **PARTIEL (6/8)** | « hors zone » et « GPS refusé » ne sont **pas refusables** : contrôle absent du canal EDT (N-12) et neutralisé sur le legacy (N-01) |

### 16.2 Scripts d'exécution

| Script | État | Détail |
| :--- | :--- | :--- |
| `backend/tests_e2e_injs_2026_2027.py` | **[non opérationnel]** | Crash **dès l'étape 1** (« Paramétrage Académique 2026-2027 ») : `tests_e2e_injs_2026_2027.py:154` → `AttributeError: 'NoneType' object has no attribute 'intitule'` (`ref_ms` introuvable, code non défensif). **Aucun des 4 scénarios n'est atteint.** |
| `manage.py smoke_test_injs` | **[non opérationnel]** | `CommandError` dès `SMOKE-01-CAMPAGNE` : `UNIQUE constraint failed: scolarite_anneeacademique.courante` → la commande **n'est pas idempotente** (échec dès qu'une année courante existe). ⚠️ C'est une **étape CI** (`.github/workflows/ci.yml:148`) : elle passe sur une base neuve et échoue sur une base déjà peuplée. |
| `formations/…/seed_injs_complet.py` | **[Validé et opérationnel]** | Chaîne 1.1 → 5.1 exécutée avec succès en sandbox (136 lignes de log), 416 formations en pause, 0 anomalie de charge, 0 conflit EDT. |
| Rapport historique `docs/TEST_E2E_INJS_MARCORY_2026_2027.md` | **[à vérifier]** | Dated 16/09/2026, annonce « 139/139 tests Django » et « 75/75 tests Vitest » — **dépassé** : on mesure aujourd'hui 137 tests sur `presences`+`edts` seuls et **1 747 tests frontend**. |

---

## 17. AUDIT SÉCURITÉ

### 17.1 Authentification et gestion des sessions

| Point | Constat | Statut |
| :--- | :--- | :--- |
| Modèle utilisateur | `AUTH_USER_MODEL = 'authentication.User'` | **[Validé et opérationnel]** |
| Validateurs de mot de passe | `UserAttributeSimilarity`, `MinimumLength`, `CommonPassword`, `NumericPassword` (les 4 de Django) | **[Validé et opérationnel]** |
| Access token | `1 j` en DEBUG, **12 h** en production | **[Validé et opérationnel]** |
| Refresh token | 30 j en DEBUG, **7 j** en production, **`ROTATE_REFRESH_TOKENS = True`** | **[Validé et opérationnel]** |
| `SECRET_KEY` | **absence = `RuntimeError` si `DEBUG=False`** (`settings.py:21-27`) | **[Validé et opérationnel]** |
| Key de dev | `'django-insecure-dev-only-do-not-use-in-production'` uniquement en DEBUG | **[Validé et opérationnel]** |
| Cookies de session/CSRF | `*_COOKIE_SECURE = True` dès `DEBUG=False` | **[Validé et opérationnel]** |
| HSTS | 31 536 000 s + subdomains + preload (prod) | **[Validé et opérationnel]** |
| `SECURE_SSL_REDIRECT` | **désactivé volontairement** (conflit proxy documenté, `settings.py:380-386`) — compensé par `SECURE_PROXY_SSL_HEADER` | **[à vérifier]** en conditions réelles de déploiement |
| Rotation des refresh tokens en session | rotation **activée** mais **blacklist non vérifiée** | **[à vérifier]** |

### 17.2 Contrôle d'accès (RBAC)

| Point | Constat | Statut |
| :--- | :--- | :--- |
| `permission_classes` explicites | **479 occurrences** sur 495 routes | **[Validé et opérationnel]** |
| Rôles en base | **81 rôles**, **1 157 permissions** liées | **[Validé et opérationnel]** (données) |
| Permissions par défaut | `DEFAULT_PERMISSION_CLASSES` (non `AllowAny`) | **[Validé et opérationnel]** |
| Décorateurs métier | `@exige_permission`, `ExigePermission` | **[Validé et opérationnel]** |
| Séparation Étudiant / Secrétariat / DFRC | `IsSecretariatOrDFRC`, `EtudiantOwned` | **[Validé et opérationnel]** |
| Consultation d'exports restreinte | `exports/views.py:20` — logs CSV consultés + rôle + `user_agent` | **[Validé et opérationnel]** |

### 17.3 Abuse / quotas

| Point | Constat | Statut |
| :--- | :--- | :--- |
| `login` | **20/min** (env. `THROTTLE_LOGIN_RATE`) | **[Validé et opérationnel]** |
| `scan` | **60/min** | **[Validé et opérationnel]** |
| `offline_data` | **60/min** | **[Validé et opérationnel]** |
| CORS | `CORS_ALLOW_ALL_ORIGINS = False`, liste explicite | **[Validé et opérationnel]** |
| Volumétrie abusives | `POST /api/scolarite/campagnes/` : pas de limite de taille propre au-delà du throttle | **[à vérifier]** |

### 17.4 Audit / traçabilité

| Point | Constat | Statut |
| :--- | :--- | :--- |
| Journal système | table `AuditLog` (`presences/models.py:242`), **60 actions** cataloguées | **[Validé et opérationnel]** |
| Événements présence | `SCAN_ENTREE`, `SCAN_SORTIE`, `SCAN_SECURE_ENTREE/SORTIE`, `SCAN_HEARTBEAT`, `NO_HEARTBEAT`, `OUT_OF_GEOFENCE`, `AUTO_EXIT`, `AUTO_ABSENT`, `CLOSE_SESSION`, `DEVICE_UNBIND` | **[Validé et opérationnel]** |
| Événements métier | `FORMATION_*`, `MODULE_*`, `SEANCE_*`, `PARTICIPANT_*`, `FORMATEUR_*`, `USER_LOGIN/LOGOUT/PASSWORD_CHANGE`, `RATTRAPAGE_*`, `FINANCE_*`, `SECRETARIAT_*`, `REFERENTIEL_*` | **[Validé et opérationnel]** |
| Horizon d'audit | 2 clés FK (`formation_id`, `module_id`) — pas d'ID utilisateur ni IP structurée sur toutes les actions | **[à vérifier]** |
| Horodatage serveur | timestamps Django avec `USE_TZ` (avertissements `naive datetime` observés en test) | **[à vérifier]** |
| Redaction secret / mot de passe | aucun `RGPD_*` / `REDACT` dans `AuditLog` : le filtrage dépend des appelants | **[à vérifier]** |
| Journalisation des accès d'export | **oui** — `exports/views.py:779` filtre sur `FORCE_ENTREE`/`FORCE_SORTIE` et log IP + `user_agent` | **[Validé et opérationnel]** |
| Reprise après incident | `formations/audit_recovery.py` + `manage.py recover_from_audit` | **[Validé et opérationnel]** |

### 17.5 Failles identifiées

| Sévérité | Faille | Régime | Remède |
| :--- | :--- | :--- | :--- |
| **P0** | Géolocalisation neutralisée → tout badgeage accepté quel que soit le lieu | prod **et** sandbox | Paramétrer `RefSite.geofence_*` |
| **P1** | Aucun appelant de `/api/presences/seances-edt/scan/` → la règle 08.07/08.14 de la présence geo-vérifiée n'est **pas** appliquée en réel | prod | Brider le client (mobile ou front) |
| **P2** | `url_badgeage` pointe vers une route front inexistante | prod | Corriger l'URL cible |
| **P2** | `annee_academique_courante` lu nulle part | sandbox | Lecture du paramètre ou suppression de l'interface |
| **P3** | `SECRET_KEY` de développement **en dur** (`django-insecure-dev-only-…`) quand `DEBUG=True` et `SECRET_KEY` absent | dev | Interdire `DEBUG=True` hors poste de dev ; `.env` n'est pas versionné (`git ls-files` vide) ✔ |

---

## 18. PERFORMANCE

| Point | Constat | Statut |
| :--- | :--- | :--- |
| Pagination API | `PageNumberPagination`, `PAGE_SIZE = 50` par défaut | **[Validé et opérationnel]** |
| Index DB | **89** déclarations `db_index` / `Index` / `index_together` sur les modèles | **[Validé et opérationnel]** |
| Évitement N+1 | **398** `select_related` + **57** `prefetch_related` hors tests | **[Validé et opérationnel]** |
| Requêtes de stats | `Exists(OuterRef(...))` au lieu d'un `IN` de sous-requête (`statistiques/effectifs.py:54-64`) | **[Validé et opérationnel]** |
| Filtres de dates | `date_journee` indexée + bornes `gte/lte` | **[Validé et opérationnel]** |
| SQL brut | 5 usages (`connection.cursor` / `RawSQL`) seulement | **[Validé et opérationnel]** |
| Export volumineux | `FileResponse` streaming (`jurys/api.py:324`) | **[Validé et opérationnel]** |
| Cache | `LocMemCache` en DEBUG, **Redis** si `REDIS_URL` défini, TTL 300 s | **[Validé et opérationnel]** |
| Tâches asynchrones | **aucune configuration Celery** dans `settings.py` | **[à vérifier]** — traitements lourds (rapprochements, notifications) en synchrone |
| `objects.all()` non borné | 108 occurrences hors tests — à examiner selon la vue exposée | **[à vérifier]** |
| Durée de la suite backend | **> 60 min en local** ; CI documente 56 min 54 s → 89 min 40 s, `timeout-minutes: 120` | **[Validé et opérationnel]** (marge réelle) |
| Durée suite frontend | **139,8 s** (1 747 tests, 89 fichiers) | **[Validé et opérationnel]** |

**Verdict performance** : aucun défaut de performance **bloquant** n'est démontré. Les optimisations
(`select_related`, `Exists`, index, pagination, cache Redis) sont présentes et systématiques.
Le point d'attention est l'absence de **tâche de fond** : les recalculs et notifications sont exécutés
dans le cycle requête, ce qui se ressentira au-delà de quelques milliers de pointages.

---

## 19. TESTS ET COUVERTURE

### 19.1 Exécutions réalisées pendant cet audit

| # | Commande | Environnement | Résultat | Durée |
| :--- | :--- | :--- | :--- | :--- |
| T1 | `python manage.py test presences edts --noinput -v 1` | sandbox (`.venv-ci`, PostgreSQL) | ✅ **137 tests — OK** | ~1 min |
| T2 | `npm run test:run` (frontend) | sandbox | ✅ **1 747 tests / 89 fichiers — OK** | **139,8 s** |
| T3 | `python manage.py seed_injs_complet` | sandbox (base neuve) | ✅ **chaîne 1.1 → 5.1 complète** | ~2 min |
| T4 | `python manage.py smoke_test_injs` | sandbox (base déjà peuplée) | ❌ **`UNIQUE constraint failed`** | < 1 min |
| T5 | `python tests_e2e_injs_2026_2027.py` | sandbox | ❌ **`AttributeError` étape 1** | < 1 min |
| T6 | `python manage.py test --noinput -v 1` (suite complète) | sandbox | ⚠️ **1 695 tests — 4 erreurs d'env, 0 échec métier** (§ 19.4) | 2 h 18 |

### 19.2 Couverture de la CI (`.github/workflows/ci.yml`)

| Job | Étapes | Statut |
| :--- | :--- | :--- |
| **Backend** (timeout 120 min) | hygiene dépôt → `collectstatic` → `migrate` → `test --parallel 2` → **contrat d'API figé** (`export_api_contract --check`) → **smoke_test_injs** → `fumee_authentification --tous --creer` → `init_habilitations_injs` + `verifier_chaine_habilitations` → `observations_habilitations` (×2) → `audit_integrity_check` → build Docker + contrôle de permissions | **[Validé et opérationnel]** |
| **Frontend** (build) | `npm ci` + `npm run build` | **[Validé et opérationnel]** |
| **Frontend tests** (timeout 20 min) | `npm run test:coverage` + archivage du rapport HTML | **[Validé et opérationnel]** |
| **Mobile** (timeout 20 min) | `flutter pub get` + analyse statique | **[Validé et opérationnel]** |

**Points forts notables de la CI** : le **contrat d'API figé** (`docs/api/contract.snapshot.json`) empêche la
suppression silencieuse d'une route ; le **chaînage SHA-256 des habilitations** et l'**intégrité du journal d'audit**
sont vérifiés ; `check_repo_hygiene` protège des données nominatives ; l'image Docker est contrôlée (permissions `appuser`).

### 19.3 Dénominateur de couverture — à ne pas confondre

| Indicateur | Valeur | Ce que cela **ne** prouve pas |
| :--- | :--- | :--- |
| Tests frontend | **1 747** sur 89 fichiers | que les 74 routes `App.jsx` sont toutes parcourues |
| Tests backend (présences + EDT) | **137** | que les statistiques lisent les présences EDT |
| Seuils de couverture frontend | `statements 34`, `branches 60`, `functions 23`, `lines 34` ; `src/utils/roles.js` à **100 %** | pas de couverture de lignes métier |
| Couverture backend | **non mesurée** (aucune étape `coverage` dans la CI) | — |
| Exigences métier approuvées couvertes | **18 exigences** (EX-01 → EX-18) | — |

**Point d'attention** : les seuils globaux de couverture frontend (**34 %** des statements) sont faibles.
Ils constituent un « filet anti-régression », pas une preuve de couverture fonctionnelle.
`src/utils/roles.js` est le seul fichier verrouillé à 100 %.

### 19.4 Suite backend complète — résultat définitif

Deux exécutions ont eu lieu : **avant** correction (PostgreSQL, 2 h 18) puis **après** correction
(sandbox, base fraîche). Comparaison :

| Exécution | Tests | Résultat | Durée |
| :--- | :--: | :--- | :--- |
| **Avant** correction (PostgreSQL) | 1 695 | `FAILED (errors=4, skipped=3)` — **0 échec métier** | 8 256 s (2 h 18) |
| **Après** correction (sandbox) | **1 703** | ✅ **`OK (skipped=5)`** — **0 échec, 0 erreur** | **349 s (5 min 49)** |

Les **4 erreurs** de la première exécution étaient dues à l'absence de `collectstatic` dans cet
environnement (`Missing staticfiles manifest entry for 'img/logo-injs.png'`) : **cause
environnementale, pas un défaut métier** — la CI lance `collectstatic` avant les tests (`ci.yml:127`).
Elles ne se reproduisent pas sur une base fraîche (→ point de non-régression **NR-13**).

**Résultat après correction N-12** : **1 703 tests, 0 échec, 0 erreur**, dont les 8 nouveaux tests
de géolocalisation. Le canal EDT applique désormais la règle de périmètre décidée en A-02.

> **Ce que cela prouve** : le code applicatif est sain sur l'ensemble de la suite ; les corrections N-11
> et N-12 n'introduisent **aucune régression**. La suite est **au vert**.

---

## 20. LISTE EXPLICITE — **[Validé et opérationnel]**

Éléments **existant, codés, testés et vérifiés en exécution** par cet audit.

| # | Élément | Preuve d'exécution |
| :-- | :--- | :--- |
| V-01 | Référentiels INJS (sites, salles, bâtiments, niveaux, grades, vagues, semestres, régimes) | seed L1.1 exécuté : 58 salles, 10 bâtiments, 5 niveaux, 10 semestres |
| V-02 | Moteur CRUD formations / modules / ECUE avec LMD (30 ECTS) | `formations/` + `scolarite_maquette` (code) |
| V-03 | Emploi du temps GET-INJS : 28 routes, conflits, capacité de salle, alias `api/timetable/` | 137 tests `edts` **OK** |
| V-04 | Contrôle de conflits d'EDT | `edts_conflitcreneau` : 0 conflit sur 9 affectations |
| V-05 | Propagation EDT → présences (`seances_edt_services`) | tests unitaires **OK** |
| V-06 | Badgeage QR **legacy** `/api/scan/secure/` (entrée, sortie, heartbeat, statut) | 137 tests backend **OK** |
| V-07 | Anti-doublon (QR expiré, token révoqué, pointage existant) | 137 tests backend **OK** |
| V-08 | Contrôles horaires paramétrables (ouverture 10 / retard 10 / clôture 15 min) | `Parametre` lu par le code |
| V-09 | **Calcul de géolocalisation haversine** (rayon 200 m, précision 80 m) | `presences/views.py:526-535` + tests |
| V-10 | Heartbeat et sortie automatique hors zone (`outside_geofence_count ≥ 2`) | code + tests (non déclenchable en données) |
| V-11 | Badgeage manuel forcé avec **motif obligatoire en correction** (règle 08.14) | `seances_edt_services.py:375-378` + tests |
| V-12 | Statut distinct `FORCE_DFRC` et traçabilité `AuditLog.FORCE_ENTREE` | tests OK |
| V-14 | Journal d'audit unifié — **60 actions** cataloguées | `presences/models.py:242` + `audit_integrity_check` en CI |
| V-15 | RBAC CURP : 81 rôles, 1 157 permissions, 479 `permission_classes` | 14 tests `habilitations` |
| V-16 | Contrat d'API figé (drf-spectacular) | `export_api_contract --check` en CI |
| V-17 | Chaînage SHA-256 des habilitations | `verifier_chaine_habilitations` en CI |
| V-18 | JWT durci (rotation, 4 validateurs de mot de passe, HSTS, cookies sécurisés) | `settings.py:209-214`, `266-269`, `385-392` |
| V-19 | Throttles `login 20/min`, `scan 60/min`, `offline_data 60/min` | `settings.py:258-262` |
| V-20 | CORS strict (`ALLOW_ALL = False`) | `settings.py:314-336` |
| V-21 | Hygiène du dépôt (données nominatives) | `check_repo_hygiene` en CI |
| V-22 | Suite frontend : **1 747 tests / 89 fichiers — 100 % verts** | 139,8 s |
| V-23 | Pagination, 89 index, 398 `select_related`, 57 `prefetch_related`, cache Redis | `settings.py:186-197`, `255-256` |
| V-24 | Chaîne de seed complète `seed_injs_complet` (étapes 1.1 → 5.1) | exécutée, **OK** |
| V-25 | Pipeline de déploiement (CI, VPS, Docker Hub ×2, sync app) | 6 workflows présents |
| V-26 | Écran enseignant EDT/présences `EdtPresences.jsx` consommant l'API EDT | `frontend/src/**` |

---

## 21. LISTE EXPLICITE — **[non opérationnel]** + correction à approuver

| # | Élément | Cause | Correction proposée | Priorité |
| :-- | :--- | :--- | :-- | :-- |
| N-12 | **Le canal EDT n'applique AUCUN contrôle de géolocalisation** | `badger_scan()` (`seances_edt_services.py:203-259`) stocke la position mais n'appelle jamais `_check_geofence()` (§ 21 bis) | Appeler `_check_geofence()` dans `badger_scan()` (position obligatoire si geofence active, refus `OUT_OF_GEOFENCE`, refus `LOCATION_INACCURATE`) + tests | **P0 — nouveau** |
| N-01 | **Géolocalisation sur la base officielle** | `formations_refsite.geofence_latitude/longitude = NULL` → `_check_geofence()` retourne toujours `True` (canal legacy) | Appliquer les coordonnées **officielles validées le 26/09/2026 : `5.3083, -3.9825`** (§ 23.1) via une commande dédiée ; **alerte ET refus** hors zone | **P0 — arbitré** |
| N-11 | **Le seed contredit les coordonnées officielles** | `seed_lot1_1_injs.py:62-64` pose `5.3025, -3.9785` → **non validée**, à **782 m** du point officiel (calculé) | Corriger la valeur dans le seed **et** ajouter un test qui refuse une geofence hors du périmètre Marcory connu | **P0 — nouveau** |
| N-02 | **Présences EDT → Statistiques / BI** | `filter_sessions()` ne lit que `SessionModule` ; 0 référence à `seance_edt` dans `statistiques/`, `dashboard/`, `exports/` | Étendre `filter_sessions()` à `AffectationCreneau` (union `session` **et** `seance_edt`) ; propager dans `point_journalier.py`, `effectifs.py`, `dashboard/`, `exports/` | **P1** |
| N-03 | **Canal de scan EDT sans client** | `/api/presences/seances-edt/scan/` n'est appelé par **aucun** client | Bridage du client mobile (ou du front) sur ce canal, avec retrait planifié du doublon legacy | **P1** |
| N-04 | **Faux positif de certification du seed** | `seed_injs_complet` affiche « 0 tableau(x) généré(s) » puis « ✓ certifié conforme » | Le seed doit **échouer** si le point journalier est vide, au lieu de certifier | **P1** |
| N-05 | `url_badgeage` → `/presences/scan-edt` | **route frontend inexistante** (`seances_edt_api.py:96`) | Corriger l'URL vers la route réellement déclarée, ou créer la route | **P2** |
| N-06 | `annee_academique_courante` (paramètre) | valeur `2025-2026` obsolète, **jamais lue** (seule occurrence : une migration) | Faire pointer le paramètre sur `AnneeAcademique.courante`, ou le retirer de l'API | **P2** |
| N-07 | `smoke_test_injs` non idempotent | `UNIQUE constraint failed: scolarite_anneeacademique.courante` — **c'est une étape CI** | `get_or_create` sur l'année courante avant l'assertion | **P2** |
| N-08 | `tests_e2e_injs_2026_2027.py` | crash `AttributeError` étape 1 (`ref_ms` non trouvé) | Garde défensive + auto-ensemencement du référentiel manquant | **P2** |
| N-09 | `statut_assiduite` non renseigné | **34/34 pointages** officiels ont `statut_assiduite = NULL` | Remplissage par la commande de clôture de session, ou valeur par défaut | **P3** |
| N-10 | M02 Formations & maquettes LMD | `scolarite_maquette` = 0 en base officielle | Exécuter la chaîne L2/L3 sur `injs_lmd_current` | **P1** |

---

## 21 bis. FAILLE P0 — LA GÉOLOCALISATION ÉTAIT ABSENTE DU CANAL EDT

> **Corrigé le 26/09/2026 (correction N-12).** Cette section conservée comme trace :
> l'audit avait d'abord conclu à une simple neutralisation par la donnée. La relecture
> du code a montré un défaut plus grave, désormais **corrigé et couvert par 8 tests**.

| | Canal **legacy** `/api/scan/secure/` | Canal **EDT** `/api/presences/seances-edt/scan/` |
| :-- | :-- | :-- |
| Appelle `_check_geofence()` | ✅ `presences/views.py:1152` (entrée) et `:1322` (heartbeat) | ❌ **jamais appelé** *(corrigé par N-12)* |
| Exige la position si geofence active | ✅ `LOCATION_REQUIRED` | ❌ **absent** *(corrigé par N-12)* |
| Refuse hors zone | ✅ `OUT_OF_GEOFENCE` | ❌ **absent** *(corrigé par N-12)* |
| Refuse précision insuffisante | ✅ `LOCATION_INACCURATE` | ❌ **absent** *(corrigé par N-12)* |
| Stocke la position | ✅ | ✅ *(inchangé)* |
| **Statut au 26/09/2026** | 🟡 code correct, neutralisé par `geofence = NULL` | 🟢 **corrigé et testé** |

**Preuve** — `seances_edt_api.scan_seance()` (l. 100-180) transmet les coordonnées :
```python
coords = {}
for cle, champ in (('latitude', 'last_latitude'), ('longitude', 'last_longitude'),
                   ('accuracy_m', 'last_accuracy_m'), ...):
    if cle in (request.data or {}):
        coords[champ] = request.data.get(cle)
action, pointage, erreur = service.badger_scan(..., coords=coords or None)
```
Mais `seances_edt_services.badger_scan()` (l. 203-259) fait **exactement** :
```python
pointage = Pointage.objects.create(participant=participant, seance_edt=affectation, session=None,
                                   ..., **(coords or {}))     # ← stocke, sans jamais vérifier
```
→ **Aucune ligne `_check_geofence(` dans `seances_edt_api.py` ni dans `badger_scan()`.**

**Portée réelle** : la règle « alerte + refus » décidée en A-02 ne s'appliquait à **aucun** badgage de séance LMD,
le canal principal de l'application.

### Correction appliquée — N-12 (26/09/2026)

| Élément | Contenu |
| :--- | :--- |
| Module créé | `backend/presences/geofence.py` — **source de vérité unique** du contrôle de périmètre (haversine, seuil de précision, résolution du site) |
| Canal EDT corrigé | `seances_edt_services._controle_geofence_edt()` appelé dans `badger_scan()`, **avant** la création du pointage : refus → `LOCATION_REQUIRED`, `OUT_OF_GEOFENCE`, `LOCATION_INACCURATE` |
| Résolution du site | `geofence.site_de_seance_edt()` — via la salle planifiée (`RefSalle.site`), repli sur le site actif unique |
| Décision « alerte » | le refus est **journalisé** (`AuditLog.Action.OUT_OF_GEOFENCE`) avec `distance_m`, `rayon_m` et la position transmise |
| Legacy non cassé | `views._check_geofence` délègue désormais au module partagé — comportement **strictement identique**, zéro duplication de la règle |
| La sortie n'est pas re-vérifiée | un élève déjà entré peut sortir même loin du site, sinon il resterait bloqué « en cours » toute la journée |
| Tests ajoutés | **8 tests** (`GeofenceSeanceEdtTests`) : dans la zone · hors périmètre + aucun pointage écrit · journalisation du refus · position absente · précision insuffisante · **ancienne géofence du seed (782 m) refusée** · site non géolocalisé (non-régression) · sortie non re-vérifiée |
| Résultat | `presences`+`edts` : **145 tests OK** (137 + 8) · `formations` inclus : **392 tests OK** · contrat d'API : **conforme** |

---

## 22. LISTE EXPLICITE — **[implémentation]** + plan

Code présent et cohérent, mais **non exercé** (données absentes) ou **non branché** (client absent).

| # | Élément | Manque | Plan proposé |
| :-- | :--- | :--- | :-- |
| I-A-01 | M03 Admissions & campagnes | 1 campagne, 1 candidat, 1 candidature, **0 admission** | Ouvrir la campagne, injecter les dossiers, lancer le traitement |
| I-A-02 | M04 Scolarité & inscriptions | 3 tables d'inscription à 0 | Créer les inscriptions administratives puis pédagogiques |
| I-A-03 | M05 Étudiants & groupes | `scolarite_groupe` = 0 | Constituer les groupes depuis les maquettes LMD |
| I-A-04 | M11 Évaluations & notes | `suiviEvaluation_*` vides | Créer les évaluations sur les modules évalués |
| I-A-05 | M12 Jurys | `jurys_sessionjury` = 0 | Constituer les jurys de délibération |
| I-A-06 | M13 Diplomation | `graduation_diplome` = 0 | Lancer la délibération puis la certification |
| I-A-07 | M14 Finances étudiantes | 3 tarifs, 6 factures, 18 quittances en base de test, 0 en base officielle | Générer les factures de l'année courante et lancer le rapprochement |
| I-A-08 | M15 Stages | 6 conventions en test, 0 en officiel | Saisir les conventions de stage |
| I-A-09 | M16 Administration & GED | 3 directions, 2 départements en test, 0 en officiel | Créer les directions et services |
| I-A-10 | M17 RH & patrimoine | 3 services, 3 agents, 5 équipements en test, 0 en officiel | Saisir l'organigramme et le parc |
| I-A-11 | `presences_devicebinding` | table vide | Enrôler les appareils mobiles (flux `DEVICE_UNBIND` déjà codé) |
| I-A-12 | Précision GPS (`LOCATION_INACCURATE`) | code présent mais non atteignable si `accuracy_m` est omis | Rendre `accuracy_m` obligatoire côté client |
| I-A-13 | Géolocalisation → **assiduité / notes** | `suiviEvaluation` ne lit pas les présences EDT | Pont d'assiduité (cf. I-14) |

> ⚠️ **Règle INJS n° 8** : ces mises en œuvre passent par une **commande de seed dédiée**, jamais par une
> réinitialisation de la base. `backend/seed_data.py` n'est **pas** une autorisation de réinitialiser `injs_lmd_current`.

---

## 23.1 ARBITRAGES MÉTIER TRANCHÉS — DÉCISIONS DU COMMANDITAIRE (26/09/2026)

**Statut : les trois questions bloquantes sont TRANCHÉES.** Elles passent de « À arbitrer » à « à implémenter ».

| ID | Question posée | **Décision du commanditaire** | Conséquence technique |
| :-- | :--- | :--- | :-- |
| **A-02** | Le badgeage doit-il **refuser** hors zone, ou seulement **alerter** ? | **Alerte ET refus** — les deux | Le refus existe déjà (`OUT_OF_GEOFENCE`) mais **n'est jamais déclenché**. Il faut l'activer (N-01) et **ajouter l'alerte** (nouvelle action d'audit + notification) |
| **A-03** | Quelles coordonnées GPS officielles pour l'INJS Marcory ? | **5.3083, -3.9825** — données officielles | ⚠️ Le seed contredit cette valeur : `seed_lot1_1_injs.py:62-64` pose `5.302500, -3.978500` (**non validée**). **Nouvelle correction N-11** |
| **A-01** | EDT moteur intégré ou EDT externe GET-INJS en lecture seule ? | **Moteur EDT intégré à INJS-LMD** | Confirme l'architecture existante (`edts/`). Le lot 4 n'est **plus conditionné** par un arbitrage : il devient une implémentation de client sur le moteur interne |

### Points restant à préciser (non bloquants)

| ID | Question | Proposition par défaut | Statut |
| :-- | :--- | :--- | :-- |
| A-03b | **Rayon** de la zone | 200 m (défaut `MOBILE_GEOFENCE_DEFAULT_RADIUS_M`) — le seed historique utilisait 300 m | **À confirmer** — sans effet bloquant |
| A-02b | **Délai de grâce** avant refus (GPS instable) | 1 seule détection → refus | **À confirmer** — le code compte 2 heartbeats pour la *sortie*, pas pour l'*entrée* |
| A-04 | Règles officielles de présence (seuils 10/10/15 min) | conserver les `Parametre` actuels | **À confirmer** (inchangé) |

> **Effet de la décision A-02** : le mode « refus » est **plus exigeant** que le PDF (p. 155) qui déconseillait le GPS obligatoire.
> Il est désormais **explicitement arbitré** : la géolocalisation devient une **règle métier validée**, non une hypothèse de l'audit.

---

## 23. TABLEAU SÉPARÉ — **NON VÉRIFIÉ / À ARBITRER**

Points **non démontrables** par cet audit : ils exigent soit une décision métier, soit un environnement non accessible ici.

| # | Sujet | Pourquoi non vérifiable | Question au propriétaire métier | Échéance |
| :-- | :--- | :--- | :-- | :-- |
| A-01 | **EDT externe vs moteur intégré** — **TRANCHÉ le 26/09/2026** | ~~Le PDF décrit un moteur intégré ; les prompts actent un EDT externe~~ → **Le commanditaire confirme le moteur EDT intégré**. Le dépôt est donc conforme (§ 23.1) | ~~Question ouverte~~ → **Confirmé** | **Levé** |
| A-02 | **Géolocalisation obligatoire ou non** — **TRANCHÉ le 26/09/2026** | ~~Le PDF (p. 155) déconseille le GPS obligatoire~~ → **Décision : alerte ET refus hors zone** | ~~Le badgeage doit-il refuser ou alerter ?~~ → **Les deux** | **Levé** |
| A-03 | **Coordonnées GPS officielles** — **TRANCHÉ le 26/09/2026** | Le seed portait `5.3025, -3.9785`, **non validée** | ~~Confirmez-vous ces coordonnées ?~~ → **Officiel : `5.3083, -3.9825`** (782 m d'écart) | **Levé** → N-11 |
| A-04 | **Règles officielles de présence** | Les seuils (10/10/15 min) viennent d'un `Parametre`, pas d'une décision INJS consignée | Quelle est la règle officielle d'assiduité LMD ? | Haute |
| A-05 | **Règles de calcul LMD / crédits** | Aucun document métier signé dans le dépôt | Les maquettes et règles de compensation sont-elles validées ? | Haute |
| A-06 | **Seuils financiers et sanctions** | Paramétrés, mais **aucune valeur métier sourcée** | Barème de frais et règles de sanction : quelle source fait foi ? | Moyenne |
| A-07 | **Comportement mobile** (permission GPS, hors-ligne, spoofing) | Application Flutter **non exécutée** dans cet audit | Valider sur appareil réel, GPS réel et sans réseau | Moyenne |
| A-08 | **Matricules INJS26-XXXX** | Format présent uniquement dans les seeds | Le format de matricule est-il officiel ? | Basse |
| A-09 | **Révocation JWT** | `ROTATE_REFRESH_TOKENS = True` mais aucune table de révocation observée | La révocation doit-elle être immédiate en cas de vol de token ? | Moyenne |
| A-10 | **Comportement en production réelle** | Audit réalisé en sandbox ; `DEBUG=False` non exercé | Valider HSTS, cookies sécurisés et `ALLOWED_HOSTS` sur l'hébergeur | Haute |
| A-11 | **Niveau réel de remplissage de la base officielle** | ~136 tables vides : impossible de distinguer « pas encore échu » de « jamais fait » | Quelle est la date de bascule officielle sur INJS-LMD ? | **Haute** |
| A-12 | **Tâches de fond** | Aucun Celery ; « synchrone vs asynchrone » n'est tranché par aucune source | Les rapprochements et notifications doivent-ils être asynchrones ? | Moyenne |

---

## 24. ANOMALIES ET CAUSES RACINES

### 24.1 Les 4 anomalies bloquantes

| ID | Anomalie | Manifestation | Cause racine | Nature |
| :-- | :--- | :--- | :-- | :-- |
| **A-P0-1** | **Géolocalisation absente du canal EDT** | `badger_scan()` stocke la position mais **n'appelle jamais** `_check_geofence()` → aucun refus hors zone, aucune position obligatoire | L'API EDT a été livrée sans le contrôle de position que le legacy possessed ; le test de non-régression du scan EDT ne vérifie pas la géolocalisation | **Code**, pas donnée |
| **A-P1-2** | **Présences EDT invisibles des statistiques** | `seed_injs_complet` affiche « 0 tableau(x) généré(s) » ; point journalier vide | `seances_edt_services` écrit `session=None, seance_edt=…`, mais `filter_sessions()` (`statistiques/effectifs.py:54`) ne lit que `SessionModule` — **aucun pont** entre les deux canaux | **Architecture** (modèle de données) |
| **A-P1-3** | **Canal EDT sans client** | `/api/presences/seances-edt/scan/` a **0 appelant** hors tests | Le client mobile a été maintenu sur l'API **legacy** `/api/scan/secure/` ; l'API EDT a été livrée sans son consommateur | **Intégration** |
| **A-P0-4** | **Géolocalisation neutralisée sur le canal legacy** | `_check_geofence()` retourne `True` sans vérifier (site `geofence_latitude = NULL`) ; 34/34 pointages sans GPS | Le seed qui pose les coordonnées (`seed_lot1_1_injs.py:62-64`, valeur **non validée**) **n'a jamais été exécuté** sur `injs_lmd_current` | **Donnée**, pas code |

### 24.2 Anomalies secondaires

| ID | Anomalie | Cause racine |
| :-- | :--- | :-- |
| A-S-1 | Le seed certifie « conforme » alors qu'il n'a produit aucun tableau | Absence de **contrôle d'échec** sur la section statistiques : la commande valide la *syntaxe*, pas le *résultat* |
| A-S-2 | `smoke_test_injs` non idempotent | Le script suppose une base **vide** (contrainte `uniq_annee_academique_courante`) alors qu'il est exécuté en CI sur base neuve et réutilisé en local |
| A-S-3 | `tests_e2e_injs_2026_2027.py:154` → `AttributeError` | Accès direct à `.intitule` sans test de `None` sur une donnée de référentiel attendue |
| A-S-4 | `url_badgeage` → `/presences/scan-edt` inexistant | Route frontend jamais enregistrée ; le nom de route a été supposé |
| A-S-5 | `annee_academique_courante` = `2025-2026` alors que la BDD contient `2026-2027` | Double source de vérité : `parametres` **et** `scolarite_anneeacademique.courante`. Le paramètre est mort |
| A-S-6 | `statut_assiduite = NULL` sur 34/34 pointages | La commande de clôture de session ne l'alimente pas (ou n'a jamais été jouée sur les données existantes) |
| A-S-7 | `LOCATION_INACCURATE` inatteignable | La précision n'est pas obligatoire dans le contrat d'entrée |
| A-S-8 | Double exposition `api/edts/` + `api/timetable/` | Choix assumé (P11) mais surface d'API doublée non documentée dans le rapport E2E |
| A-S-9 | Aucun Celery | Recalculs et notifications exécutés dans le cycle requête |
| A-S-10 | Seuil de couverture frontend à 34 % | Filet anti-régression minimal ; pas de couverture métier |

### 24.3 Cause racine transversale

> Les **quatre** anomalies bloquantes partagent **la même cause** : l'application a été livrée **module par module**,
> chacun testé unitairement, mais **sans phase d'intégration bout-en-bout sur la base officielle**.
> Les tests unitaires sont verts (**1 691/1 695** backend + 1 747 frontend) et le rapport E2E du 16/09/2026 annonçait
> la conformité — alors que le parcours réel *formation → EDT → présence → statistique* est **interrompu deux fois**,
> et que la règle de présence décidée par le commanditaire (géolocalisation) **n'est pas implémentée** sur le canal
> principal de l'application.

**Preuve directe** : `seed_injs_complet` s'auto-certifie « ✓ certifié conforme » en produisant **zéro** tableau de statistiques.

---

## 25. DÉPENDANCES ENTRE CORRECTIONS

```
        A-01 / A-02 / A-03  (arbitrages — ✅ TRANCHÉS le 26/09/2026, § 23.1)
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
 ┌─────────┐               ┌──────────┐
 │  N-12   │               │  N-10    │
 │géoloc.  │               │ seed L2/L3│  ← doit précéder N-02 et N-03
 │ CANAL   │               │ (P1)     │
 │  EDT    │               └────┬─────┘
 │ (P0)    │                    │
 └────┬────┘                    ▼
      │                 ┌──────────┐
      │                 │  N-02    │  pont seance_edt → statistiques
      │                 │  (P1)    │
      │                 └────┬─────┘
      │  ┌──────────────┐     │ nécessaire pour que
      │  │ N-01 + N-11  │     │ le E2E-02 soit démontrable
      │  │ géofence     │     ▼
      │  │ officielle   │┌─────────┐            ┌──────────┐
      │  │ (P0)         ││  N-03   │───────────▶│  N-05    │
      │  └──────────────┘│ client  │  le client │  (P2)    │
      │                  │  (P1)   │  doit savoir│          │
      │                  └────┬────┘  où scanner └──────────┘
      │                       │
      │  N-12 précède N-03 :      ┌─────────┐   ┌──────────┐   ┌──────────┐
      └────────────────────────▶ │  N-04   │   │  N-07    │   │  N-08    │
         un client sur un canal   │ seed    │   │ smoke    │   │ script   │
         sans contrôle de zone    │ honnête │   │ idempot. │   │ E2E      │
         n'aurait aucun sens      └─────────┘   └──────────┘   └──────────┘
   indépendants : N-06, N-09, I-A-12
```

| Ordre | Correction | Pourquoi elle doit venir en premier |
| :-- | :--- | :--- |
| ~~**0**~~ | ~~Arbitrages A-01, A-02, A-03~~ | ✅ **TRANCHÉS le 26/09/2026** (§ 23.1) — plus bloquant |
| **1** | **N-04** (seed honnête) | Doit précéder tout travail sur N-02 : sinon le faux positif masque la progression |
| **2** | **N-12** (géofence canal EDT) + **N-01**/**N-11** (géofence officielle + correction du seed) | Le contrôle de position **manque dans le code** du canal principal ; c'est le défaut de sécurité le plus grave. **N-12 doit précéder N-03** |
| **3** | **N-10** (seed L2/L3 sur la base officielle) | Crée les données dont N-02 a besoin pour être prouvé |
| **4** | **N-02** (pont `seance_edt` → statistiques) | Le plus gros lot technique ; dépend de N-10 pour la preuve |
| **5** | **N-03** + **N-05** (client + route) | Doit suivre **N-02 et N-12** : on ne branche un client que sur un backend complet **et sécurisé** |
| **6** | **N-07**, **N-08** (idempotence et robustesse) | Indépendants, mais **bloquent la validation E2E** |
| **7** | **N-06**, **N-09**, **I-A-12** | Non bloquants |

**Règle de non-régression** : N-02 touche `statistiques/`, `dashboard/` et `exports/`. C'est le lot le plus
risqué. Il **ne doit pas** modifier `filter_sessions()` de façon destructive : la signature et le comportement
legacy doivent rester identiques, l'extension `seance_edt` doit être **additive** et derrière un paramètre
permettant de revenir en arrière.

---

## 26. PLAN DE CORRECTION (backlog priorisé)

| Rang | ID | Correction | Type | Fichiers pressentis | Estim. | Risque |
| :-- | :-- | :--- | :-- | :-- | :-- | :-- |
| 1 | **N-04** | Le seed **échoue** si le point journalier est vide ; supprimer le « ✓ certifié conforme » trompeur | code | `formations/management/commands/seed_injs_complet.py` | 0,5 j | **Faible** |
| 2 | **N-12** | ~~Brancher `_check_geofence()` dans `badger_scan()`~~ | **✅ FAIT le 26/09/2026** | `presences/geofence.py` + `seances_edt_services.py` | 1,5 j | **Traité — 8 tests verts** |
| 3 | **N-01** | Appliquer la géofence **officielle** `5.3083, -3.9825` (⚠️ **écriture sur la base officielle — validation requise**) | **donnée** | commande `set_geofence_site` (**créée et validée**) | 0,5 j | **Faible** (arbitré) |
| 4 | **N-11** | Corriger le seed `5.3025, -3.9785` → `5.3083, -3.9825` (782 m d'écart) | **donnée** | ✅ **FAIT** — `seed_lot1_1_injs.py`, `seed_lot2_1_edts.py`, `tests_e2e_…` | 0,5 j | **Traité** |
| 5 | **N-07** | `get_or_create` sur l'année courante | code | `smoke_test_injs.py` | 0,5 j | **Faible** (CI) |
| 6 | **N-08** | Garde défensive + auto-ensemencement du référentiel | code | `tests_e2e_injs_2026_2027.py:154` | 0,5 j | **Faible** |
| 7 | **N-05** | Corriger ou créer la route `/presences/scan-edt` | code | `presences/seances_edt_api.py:96` + `App.jsx` | 0,5 j | **Faible** |
| 8 | **N-06** | Aligner ou supprimer `annee_academique_courante` | code + donnée | `parametres/` | 0,5 j | **Faible** |
| 9 | **N-02** | Pont `seance_edt` → `statistiques/`, `dashboard/`, `exports/` | **code majeur** | `statistiques/effectifs.py`, `point_journalier.py`, `dashboard/`, `exports/` | 5-8 j | **Élevé** |
| 10 | **N-03** | Client sur `/api/presences/seances-edt/scan/` (moteur EDT **intégré**, A-01) | intégration | `qr_badge_mobile/` ou `frontend/src/` | 5-8 j | **Moyen** |
| 11 | **N-10** | Exécuter la chaîne L2/L3 sur `injs_lmd_current` | **donnée** | `seed_injs_complet` | 1 j | **Moyen** (base officielle) |
| 12 | **N-09** | Renseigner `statut_assiduite` | code + donnée | `presences/` | 1 j | **Faible** |
| 13 | **I-A-12** | `accuracy_m` obligatoire + `LOCATION_INACCURATE` atteignable | API + client | `presences/views.py` | 1 j | **Moyen** |
| 14 | **A-S-9** | Évaluer une file de tâches (Celery) | architecture | `settings.py` + nouveau service | 8-15 j | **Élevé** |

**Total estimé : 27-51 jours-homme**, dont **≈ 16-23 j** pour le lot fonctionnel critique (rangs 1-11).
⚠️ **N-12 est un préalable à N-03** : brancher un client sur un canal qui n'applique aucun contrôle
géographique reviendrait à livrer le canal principal de l'application sans la règle métier décidée en A-02.

### 26.1 Plan de retour arrière (rollback)

| Lot | Retour arrière |
| :--- | :--- |
| N-01, N-09, N-10, N-11 (données) | Sauvegarde `scripts/backup_injs_lmd.sh` **avant** exécution ; restauration du dump en cas d'échec. Ne **jamais** faire de `flush`. |
| N-04, N-05, N-06, N-07, N-08 (code) | `git revert` du commit du lot ; aucun impact données |
| N-12 (géofence EDT) | Extension **conditionnelle** : si la géofence du site est `NULL`, le comportement reste identique à aujourd'hui (retour arrière « sans contrôle ») ; le lot est donc réversible par simple remise à `NULL` des coordonnées |
| N-02 (code majeur) | Extension **additive** derrière un paramètre `SEANCE_EDT_STATS_ENABLED` (défaut `False`) → désactivation immédiate sans revert ; `git revert` en second recours |
| N-03 (client) | Déploiement du client piloté par drapeau ; l'API legacy reste active pendant la transition |
| A-S-9 (Celery) | Lot entièrement réversible : le service synchrone actuel est conservé |

---

## 27. PLAN D'IMPLÉMENTATION — 4 LOTS

### LOT 1 — « Débloquer la preuve » (rangs 1-6, ~3,5 j, risque faible)

**Objectif** : que l'audit puisse **prouver** ce qui est aujourd'hui invisible.

1. Sauvegarde PostgreSQL (`scripts/backup_injs_lmd.sh`) + vérification du SHA-256.
2. N-04 : contrôle d'échec réel dans `seed_injs_complet`.
3. N-07, N-08 : idempotence du smoke et robustesse du script E2E.
4. N-05, N-06 : route de badgeage et paramètre d'année.
5. Tests : `manage.py test presences edts`, `npm run test:run`, `smoke_test_injs` **deux fois de suite** (preuve d'idempotence).

**Critère de fin** : `smoke_test_injs` passe **2 fois consécutives** ; le script E2E va au bout de l'étape 1 ; le seed échoue bruyamment quand les statistiques sont vides.

### LOT 2 — « Sécurité de la présence » (N-12 + N-01 + N-11, ~2,5 j — **arbitré, plus bloqué**)

1. **N-12 (prioritaire)** : appeler `_check_geofence()` dans `badger_scan()` — sans cela, la règle A-02
   **ne s'applique à aucun badgage de séance LMD**. Reprendre le schéma du legacy : position obligatoire si
   geofence active (`LOCATION_REQUIRED`), refus `OUT_OF_GEOFENCE`, refus `LOCATION_INACCURATE`, journalisation.
2. **Coordonnées officielles arbitrées** : `5.3083, -3.9825` (§ 23.1). Rayon à confirmer (200 m par défaut).
3. Commande `set_geofence_site --site <id> --lat 5.3083 --lon -3.9825 --rayon <m>` (idempotente, journalisée).
4. **N-11** : corriger `seed_lot1_1_injs.py:62-64` (actuellement 782 m trop au sud-est) + test de garde.
5. **Alerte** (décision A-02) : ajouter l'alerte à l'encadrant (nouvelle action d'audit + notification).
6. Tests : « hors zone » et « GPS refusé » **deviennent testables sur les DEUX canaux** → E2E-04 passe de 7/8 à **8/8**.

**Critère de fin** : sur le **canal EDT comme sur le legacy**, un pointage hors zone est **refusé**
(`OUT_OF_GEOFENCE`) **et alerté**, prouvé par un test ; et un badgeage au point seed (782 m plus loin) est **bien refusé**.

### LOT 3 — « Pont présence → décisionnel » (rang 7, ~5-8 j, **le plus important**)

1. Inventaire des points d'entrée de `statistiques/`, `dashboard/`, `exports/` qui consomment `filter_sessions()`.
2. Extension **additive** : nouveau paramètre `inclure_seances_edt=True/False`, union `SessionModule` ∪ `AffectationCreneau`.
3. Propagation dans `point_journalier.py`, `effectifs.py`, `dashboard/`, `exports/`.
4. Tests de non-régression : les chiffres **legacy** doivent rester **identiques** quand le paramètre est `False`.
5. Tests positifs : un `Pointage(seance_edt=…, session=None)` doit apparaître dans le point journalier.

**Critère de fin** : `seed_injs_complet` affiche « **N tableau(x) généré(s)** » avec **N > 0**, et la certification devient alors **honnête**.

### LOT 4 — « Brancher le client » (rang 8, ~5-8 j — **désarbitré, plus bloqué**)

1. **Moteur EDT intégré confirmé** (décision A-01) : le client s'appuie sur le moteur interne `edts/`. Aucune intégration externe à prévoir.
2. Implémenter l'appel avec envoi obligatoire de `latitude`, `longitude`, `accuracy_m`.
3. Retirer le lien mort `url_badgeage` ou le faire pointer vers la bonne route.
4. Planifier le retrait du doublon legacy `/api/scan/secure/` (ne pas le supprimer sans arbitrage).

**Critère de fin** : `grep 'seances-edt/scan'` renvoie **au moins un client réel** (hors tests).

---

## 28. PLAN DE TESTS DE NON-RÉGRESSION

### 28.1 Tests à exécuter après **chaque** lot

| Suite | Commande | Attendu | Durée |
| :--- | :--- | :--- | :--- |
| Présences + EDT | `manage.py test presences edts --noinput` | **137 tests OK** | ~1 min |
| Statistiques | `manage.py test statistiques --noinput` | inchangé **avant** / étendu **après** N-02 | ~2 min |
| Backend complet | `manage.py test --parallel 2 --noinput` | 0 échec (reste à établir — cf. § 19.4) | 57-90 min |
| Frontend | `npm run test:run` | **1 747 tests OK** | 140 s |
| Contrat d'API | `manage.py export_api_contract --check` | snapshot conforme (⚠️ N-02, N-05, N-03 le modifieront **volontairement**) | < 1 min |
| Fumée | `manage.py smoke_test_injs` **× 2** | 2 succès consécutifs | < 2 min |
| Intégrité audit | `manage.py audit_integrity_check` | OK | < 1 min |
| Hygiène dépôt | `manage.py check_repo_hygiene` | OK | < 1 min |

### 28.2 Nouveaux tests à écrire (absents aujourd'hui)

| ID | Test | Cible | Motif |
| :-- | :--- | :-- | :-- |
| NR-01 | Badgeage **hors zone** → `OUT_OF_GEOFENCE` — **canal EDT** | `presences` | **Impossible aujourd'hui** : aucun contrôle dans `badger_scan()` (§ 21 bis) → N-12 |
| NR-01b | Badgeage **hors zone** → `OUT_OF_GEOFENCE` — canal legacy | `presences` | Impossible aujourd'hui (site NULL) → N-01 |
| NR-02 | Badgeage **GPS absent** avec geofence active → refus | `presences` | Non couvert, **sur aucun des deux canaux** |
| NR-03 | `accuracy_m > 80` → `LOCATION_INACCURATE` | `presences` | Code inatteignable (I-A-12) |
| NR-04 | Sortie automatique après 2 heartbeats hors zone | `presences` | Non couvert de bout en bout |
| NR-05 | `Pointage(seance_edt=…)` **visible** dans le point journalier | `statistiques` | **Le test qui prouve N-02** |
| NR-06 | Chiffres legacy **identiques** avec/sans `inclure_seances_edt` | `statistiques` | Non-régression du pont |
| NR-07 | `seed_injs_complet` **échoue** si 0 tableau | `formations` | Prouve N-04 |
| NR-08 | `smoke_test_injs` **2ᵉ exécution** sans erreur | `scolarite` | Prouve N-07 |
| NR-09 | `url_badgeage` renvoie une route **résoluble** | `presences` | Prouve N-05 |
| NR-10 | `annee_academique_courante` == `AnneeAcademique.courante` | `parametres` | Prouve N-06 |
| NR-11 | `statut_assiduite` renseigné après clôture de session | `presences` | Prouve N-09 |
| NR-12 | Le scan EDT a **au moins un client** hors tests | intégration | Prouve N-03 |
| NR-13 | `collectstatic` exécuté avant `test` → 0 erreur `Missing staticfiles manifest` | local | Corrige les 4 erreurs de § 19.4 |

### 28.3 Recette par rôle

| Rôle | Parcours à rejouer | Critère |
| :--- | :--- | :--- |
| **Secrétariat pédagogique** | Campagne → dossier → inscription → groupe | Aucun étudiant inscrit sans groupe |
| **Enseignant** | Consulter l'EDT → émarger sa séance (avec motif) | Ligne `FORCE_DFRC` + motif obligatoires et tracés |
| **Étudiant / Auditeur** | Consulter son EDT, ses présences, ses notes | Présences **du canal EDT** visibles (NR-05) |
| **Administrateur / Responsable INJS** | Statistiques, exports, tableaux de bord | **Au moins un tableau non vide** généré depuis des présences EDT |
| **Responsable sécurité** | Tenter un badgeage hors site | **Refusé** avec `OUT_OF_GEOFENCE` et journalisé |

---

## 29. CRITÈRES DE SORTIE (« prêt »)

| # | Critère | Comment il se prouve |
| :-- | :--- | :--- |
| 1 | Aucun **P0** ouvert | `formations_refsite.geofence_latitude = 5.3083 / -3.9825` sur `injs_lmd_current` **ET** `_check_geofence()` appelé dans `badger_scan()` (N-12) + NR-01/NR-01b verts |
| 2 | Aucune **rupture d'intégration** présence → décisionnel | `grep -c seance_edt statistiques/` **> 0** et NR-05 + NR-06 verts |
| 3 | Le canal de scan EDT a **un client réel** | `grep 'seances-edt/scan' qr_badge_mobile/ frontend/src` **> 0** hors tests |
| 4 | Aucune **certification trompeuse** | `seed_injs_complet` échoue si 0 tableau (NR-07) |
| 5 | Les **4 scénarios E2E** sont exécutables | E2E-01, 02, 03 **PASS** ; E2E-04 **8/8** |
| 6 | La **suite complète** est verte | Backend **1 691/1 695** (0 échec métier ; les 4 erreurs d'env disparaissent avec `collectstatic`, NR-13) + **1 747** tests frontend verts |
| 7 | **Aucune régression** sur le canal legacy | NR-06 vert : chiffres legacy inchangés |
| 8 | Les 3 **arbitrages bloquants** sont tranchés | ✅ **FAIT le 26/09/2026** : A-01 moteur EDT intégré, A-02 alerte + refus, A-03 `5.3083, -3.9825` (§ 23.1) |

> **Tant qu'un seul P0 subsiste ou qu'une intégration critique reste non testée, l'application ne peut pas être**
> **annoncée comme « 100 % opérationnelle ».** C'est explicitement le cas aujourd'hui.

---

## 30. CONCLUSION FACTUELLE SUR LE NIVEAU RÉEL DE COMPLÉTUDE

### 30.1 Verdict par environnement

| Environnement | Verdict | Motif |
| :--- | :--- | :--- |
| **Sandbox (base peuplée par le seed)** | **NON PRÊT** | Le seed s'auto-certifie alors que le parcours formation → EDT → présence → statistique est interrompu (0 tableau) ; géolocalisation non exercée |
| **Base officielle `injs_lmd_current`** | **NON PRÊT** | 4 blocages : géolocalisation absente du canal EDT, données LMD non chargées, géofence legacy absente, présences EDT invisibles du décisionnel |
| **Code seul (revue statique)** | **PRÊT SOUS RÉSERVE** | Architecture cohérente, RBAC complet, 479 permissions explicites, **1 691/1 695 tests backend** et **1 747 tests frontend** verts, CI riche |
| **Module par module** | **PRÊT SOUS RÉSERVE** | 4 modules validés ; 10 modules implémentés mais non exercés ; 4 modules non opérationnels |

### 30.2 Répartition des 18 modules

| Statut | Nombre | Modules |
| :--- | :--: | :--- |
| **[Validé et opérationnel]** | **4** | M01 Référentiels, M06 Cours/ECUE/séances, M07 Enseignants/charges, M08 EDT |
| **[non opérationnel]** | **4** | M02 Maquettes LMD, M09 Présences/QR, M10 Géolocalisation, M18 Statistiques/BI |
| **[implémentation]** | **10** | M03, M04, M05, M11, M12, M13, M14, M15, M16, M17 |

### 30.3 Phrase de conclusion

> **L'application INJS-LMD est un produit sérieux, bien sécurisé et bien testé à l'échelle unitaire — mais dont le
> parcours métier central n'est pas raccordé de bout en bout.**
>
> Les tests automatisés sont **verts** : **1 703 tests backend (0 échec, 0 erreur)** et **1 747 tests frontend**.
> Les corrections N-11 et N-12 n'introduisent **aucune régression**. Cela prouve la solidité unitaire —
> mais **ne prouve pas** l'intégration, qui reste interrompue entre le canal EDT et le décisionnel.
>
> **4 blocages** empêchent toute recette — **le premier est corrigé dans le code, reste à appliquer en base** :
> 1. la géolocalisation **n'était pas implémentée** sur le canal de badgeage des séances LMD — **✅ CORRIGÉ (N-12)**,
>    8 tests verts ; reste à poser les coordonnées officielles sur la base (N-01) ;
> 2. les présences enregistrées sur séance EDT sont **invisibles** des statistiques, tableaux de bord et exports ;
> 3. le canal de scan EDT **n'a aucun client** — la fonctionnalité existe côté serveur et n'est utilisée par personne ;
> 4. la base officielle **n'est pas alimentée** pour la chaîne pédagogique LMD (~136 tables vides sur 183).
>
> Un point mérite une attention particulière : **`seed_injs_complet` s'auto-certifie « conforme » en produisant
> zéro tableau**. Cette certification automatique est elle-même un défaut à corriger (rang 1 du backlog), car elle
> masque aujourd'hui la rupture n° 2.
>
> **Décision provisoire : NON PRÊT**, sur les deux environnements. **Les trois arbitrages bloquants sont tombés le
> 26/09/2026 (§ 23.1)** : *moteur EDT intégré* (A-01), *alerte et refus hors zone* (A-02),
> *coordonnées officielles `5.3083, -3.9825`* (A-03). Le lot 1 (≈ 3,5 jours) débloque la preuve ; le lot 3 (≈ 5-8 jours)
> est la correction structurante. **Un P0 supplémentaire (N-11)** est né de l'arbitrage A-03 : le seed contredit
> désormais les coordonnées officielles. Il ne reste que des points **non bloquants** (rayon, délai de grâce).

### 30.4 Ce que cet audit n'a **pas** fait

- **Aucune modification** de code applicatif (0 fichier modifié, créé ou supprimé).
- **Aucune** modification de `injs_lmd_current` : uniquement des `SELECT` en lecture seule.
- **Aucune** suppression, `TRUNCATE`, `flush` ou réinitialisation.
- **Aucune** exécution de la commande destructive `docker compose down -v`.
- **Aucune** application mobile Flutter **exécutée** (A-07 reste ouvert).
- Les modifications CSS/JSX préexistantes de l'utilisateur ont été **préservées** et non écrasées.

---

## ANNEXE A — COMMANDES EXÉCUTÉES

```bash
# Lecture seule — base officielle
psql -h 127.0.0.1 -p 5432 -U injs_user -d injs_lmd_current   # SELECT uniquement

# Vérifications Django
python manage.py test presences edts --noinput -v 1          # OK 137
python manage.py test --noinput -v 1                         # 1695 tests : 4 erreurs d'env (collectstatic)
python manage.py export_api_contract --check
python manage.py smoke_test_injs                             # ECHEC UNIQUE constraint
python tests_e2e_injs_2026_2027.py                           # ECHEC AttributeError

# Sandbox (base de test dédiée)
python manage.py seed_injs_complet                           # chaine 1.1 -> 5.1
python manage.py migrate --noinput

# Frontend
npm run test:run                                             # 1747 / 89 fichiers
npm run lint
```

## ANNEXE B — GLOSSAIRE DES MENTIONS DE LIGNE

| Référence | Signification |
| :--- | :--- |
| `presences/views.py:526-535` / `:537-572` / `:574-608` | `_distance_meters` (haversine) · `_resolve_site_geofence` · `_check_geofence` |
| `presences/views.py:1140` | Refus de position **conditionné** à l'existence d'une geofence sur le site |
| `presences/views.py:1215-1410` | Heartbeat, compteur hors zone, sortie automatique |
| `presences/seances_edt_services.py:361-372` / `:375-378` | Absence de durée 0 / motif obligatoire en correction |
| `presences/seances_edt_api.py:96` | `url_badgeage` → `/presences/scan-edt` (route inexistante) |
| `statistiques/effectifs.py:54-64` | `filter_sessions()` — lit **uniquement** `SessionModule` |
| `formations/seed_lot1_1_injs.py:62-64` | Pose `(5.302500, -3.978500, 300)` — **jamais exécuté** sur la base officielle |
| `config/settings.py:258-262` / `266-269` / `385-392` | Throttles · JWT · durcissement production |
| `.github/workflows/ci.yml:148` | Étape CI `smoke_test_injs` (non idempotente) |

---

*Rapport produit le 26/09/2026 — audit **en lecture seule**, aucune modification applicative.*
*Ce document attend votre arbitrage sur A-01, A-02 et A-03 avant toute implémentation (règles INJS n° 2 et n° 8).*

---

## 31. CORRECTIFS APPLIQUÉS — 26/09/2026 (après feu vert)

Un lot de code a été appliqué **après** l'audit, sur autorisation explicite. Cette section est le
**procès-verbal de livraison** : elle distingue ce qui a été fait de ce qui reste à faire.

### 31.1 Correctifs livrés

| ID | Correction | Statut | Preuve |
| :-- | :--- | :-- | :-- |
| **N-12** | Géolocalisation branchée sur le canal EDT (le P0) | ✅ **Livré** | `presences/geofence.py` (nouveau) + `seances_edt_services.py` ; **8 tests** verts |
| **N-02** | Statistiques des présences LMD (canal EDT) | ✅ **Livré — partiel** | `statistiques/seances_edt_stats.py` (nouveau) ; **13 tests** verts. Unification avec le point journalier bloquée par la règle d'attribution **A-13** |
| **N-11** | Coordonnées du seed alignées sur la valeur officielle | ✅ **Livré** | `seed_lot1_1_injs.py`, `seed_lot2_1_edts.py`, `tests_e2e_injs_2026_2027.py` |
| **N-01** | Commande `set_geofence_site` (outil) | ✅ **Livré et validé** | `formations/management/commands/set_geofence_site.py` — idempotence, `--dry-run`, `--desactiver` vérifiés |
| **N-01** | Application sur `injs_lmd_current` | ✅ **Livré le 26/09/2026** | `INJS MARCORY` : `5.3083 / -3.9825`, rayon 200 m. Sauvegarde préalable + vérification d'intégrité (§ 31.5) |

### 31.2 Fichiers touchés

| Fichier | Nature |
| :--- | :--- |
| `backend/presences/geofence.py` | **nouveau** — source de vérité unique du contrôle de périmètre |
| `backend/presences/seances_edt_services.py` | contrôle appelé avant la création du pointage + journalisation du refus |
| `backend/presences/views.py` | délégation au module partagé (comportement **inchangé**), import `math` mort retiré |
| `backend/presences/test_seances_edt.py` | + 8 tests, + constantes de référence officielles |
| `backend/formations/management/commands/seed_lot1_1_injs.py` | coordonnées officielles + commentaire d'avertissement |
| `backend/formations/management/commands/seed_lot2_1_edts.py` | pointages de démonstration recentrés sur la zone autorisée |
| `backend/formations/management/commands/set_geofence_site.py` | **nouveau** |
| `backend/tests_e2e_injs_2026_2027.py` | coordonnées officielles |

Aucune suppression de fonctionnalité, aucun contournement de permission, aucune migration,
aucune écriture sur `injs_lmd_current` (`34` pointages et `geofence = NULL` vérifiés **après** coup).

### 31.3 Tests

| Périmètre | Avant | Après | Résultat |
| :--- | :--: | :--: | :--- |
| `presences` + `edts` | 137 | **145** | ✅ **OK** |
| `presences` + `edts` + `formations` | — | **392** | ✅ **OK** (2 ignorés) |
| Contrat d'API (`export_api_contract --check`) | — | — | ✅ **conforme au snapshot** |
| Suite backend complète | 1 695 | **1 703** | ✅ **OK** — 0 échec, 0 erreur (5 min 49) |
| `injs_lmd_current` | — | — | ✅ **inchangée** |

### 31.4 Écriture sur la base officielle — N-01 (26/09/2026)

La commande `set_geofence_site` a été appliquée sur `injs_lmd_current` après sauvegarde préalable.

| Étape | Résultat |
| :--- | :--- |
| Sauvegarde | ⚠️ `scripts/backup_injs_lmd.sh` **échoue** : `pg_dump` est tué par le système (signal 9), y compris sur `--version` — **défaut d'environnement, pas de la base** (26 Mo) |
| Solution retenue | Sauvegarde **ciblée** de la table concernée via `\copy … to stdout` (CSV, en-tête) + SHA-256 |
| Fichier | `~/Backups/INJS-LMD/database/geofence_formations_refsite_avant_2026-09-26_13-45.sql` |
| Empreinte SHA-256 | `c8ce80e25a35f100dda4380a99ee27b9e4be48368c5b1e86bc80fea3735dbd51` |
| Contenu sauvegardé | `id=2, nom=INJS MARCORY, actif=t, lat=NULL, lon=NULL, rayon=200` |
| Prévisualisation | `--dry-run` → `(None, None, 200) → (5.3083, -3.9825, 200)` ✔ |
| Écriture | **2 colonnes + le rayon** d'**un seul site** |
| Idempotence | 2ᵉ exécution sans `--lat/--lon` → valeur identique, aucun effet de bord ✔ |

**Vérification d'intégrité après écriture** :

| Contrôle | Avant | Après |
| :--- | :--: | :--: |
| `formations_refsite` | `INJS MARCORY`, lat/lon `NULL`, r=200 | **`5.308300 / -3.982500`, r=200** |
| `presences_pointage` | 34 | **34** ✔ |
| `formations_sessionmodule` | 8 | **8** ✔ |
| `presences_auditlog` | 72 | **72** ✔ |
| `authentication_user` | 22 | **22** ✔ |
| Tables du schéma `public` | 183 | **183** ✔ |
| Tests `presences`+`edts` | 145 OK | **145 OK** ✔ |

**Retour arrière** (si nécessaire) :
```bash
python manage.py set_geofence_site --site "INJS MARCORY" --desactiver
# ou restauration exacte depuis le CSV sauvegardé
```

> ⚠️ **Action corrective recommandée** : le script `scripts/backup_injs_lmd.sh` est **inopérant** sur ce poste
> (`pg_dump` tué). Tant qu'il n'est pas réparé, **aucune sauvegarde complète n'est possible** avant une opération
> à risque. C'est un point de sécurité opérationnelle à traiter en priorité.

### 31.5 N-02 — Statistiques des présences LMD (canal EDT) — 26/09/2026

#### Constat de conception qui a changé l'approche

Avant d'écrire la moindre ligne, la cartographie a révélé un **mismatch d'architecture** que
l'estimation « 5-8 j » n'avait pas anticipé :

| | Monde **legacy** (socle décisionnel) | Monde **EDT** (présences LMD) |
| :--- | :--- | :--- |
| Objet séance | `SessionModule` | `AffectationCreneau` |
| Rattachement | `Module` → `Formation` (**instance**) | `RefFormation` (**catalogue**) + `Groupe` |
| Clé de présence | `Pointage.session_id` | `Pointage.seance_edt_id` (`session = None`) |

**Il n'existe aucun lien déterministe** d'un `AffectationCreneau` vers un `Module` : une séance de
catalogue se rattache à N modules via `Formation.ref_formation → Module.formation`. Injecter les
présences EDT dans les tables legacy aurait exigé d'**inventer une règle d'attribution** et aurait
faussé silencieusement les taux — exactement le genre d'erreur qu'un audit doit éviter d'introduire.

**Décision retenue** : calculer l'assiduité **dans le monde EDT**, à la granularité
(formation, groupe) qui est la sienne, **sans rien imposer au socle legacy**. Le socle historique
reste **intégralement inchangé** — donc **zéro risque de régression** sur les chiffres existants.

#### Livré

| Élément | Contenu |
| :--- | :--- |
| `backend/statistiques/seances_edt_stats.py` | **nouveau** — couche de calcul : `seances_comptabilisables()`, `presentes_par_seance()`, `stats_seance()`, `stats_periode()`, `taux_presence()` |
| Règles reprises du legacy | attendu = membres actifs du groupe · présent = `q_pointage_present()` · absent = attendu sans présence · taux arrondi à 4 décimales |
| Agrégation de période | **union** des attendus, pas une somme — un étudiant présent sur 3 séances compte 1, pas 3 |
| Garde-fous | division par zéro, période inversée, balayage limité à 5 ans, filtrage hors groupe |
| `backend/statistiques/tests/test_seances_edt_stats.py` | **nouveau** — **13 tests** |
| Socle legacy | **aucune ligne modifiée** |

#### Les 13 tests

| Test | Ce qu'il prouve |
| :--- | :--- |
| `test_presence_edt_invisible_du_socle_legacy` | **fige la faille** : le socle historique ignore bien un pointage `seance_edt` |
| `test_la_nouvelle_couche_calcule_bien_le_taux` | 2/3 présents → taux 0,6667 |
| `test_absent_non_badge_ne_compte_pas` | `ABSENT_NON_BADGE` et durée nulle exclus |
| `test_sortie_sans_duree_ne_compte_pas` | sortie sans durée ≠ présence |
| `test_entree_sans_sortie_compte_comme_present` | entrée en cours = présence |
| `test_presence_hors_groupe_ignoree` | un badge hors groupe **ne fait pas monter le taux** |
| `test_groupe_vide_donne_taux_nul` | pas de division par zéro |
| `test_stats_periode_agregate_sans_double_comptage` | pas de double comptage |
| `test_stats_periode_vide…` / `…filtre_par_formation` / `…filtre_par_groupe` | bornes et filtres |
| `test_taux_presence_seance_precise` / `…inconnue` | API unitaire |

#### Résultats

| Périmètre | Avant | Après | Résultat |
| :--- | :--: | :--: | :--- |
| `statistiques` + `presences` + `edts` | 206 | **219** | ✅ **OK** |
| **Suite backend complète** | 1 703 | **1 716** | ✅ **OK** (5 ignorés, 5 min 11) — **0 régression** |
| Contrat d'API | — | — | ✅ **conforme** (aucune route touchée) |
| Socle legacy | — | — | ✅ **inchangé, 0 régression** |

#### Ce que N-02 ne fait PAS (et pourquoi)

L'unification dans le point journalier CPFAE **reste bloquée**, et ce n'est pas un oubli :

> **Question métier ouverte** : comment rattacher une séance EDT (`RefFormation` + `Groupe`) à un
> `Module` du socle ? Par titre ? Par equivalence ECUE ? Par unicité de maquette ? Chaque réponse
> change les chiffres. **Aucune hypothèse n'a été retenue ici** — elle doit être arbitrée (nouveau
> point **A-13** au § 23.1) avant toute injection dans les tables legacy.

En attendant, la couche livrée donne des chiffres **vérifiables et justes** sur le canal EDT,
ce qui était l'essentiel : les présences LMD ne sont plus dans un angle mort.

---
### 31.6 Ce qui reste ouvert

| ID | Reste à faire | Pourquoi pas fait |
| :-- | :--- | :--- |
| **A-13** | **Rattacher une séance EDT à un `Module`** (règle d'attribution) | Question métier — non inventée (§ 31.5) |
| **A-03b** | Confirmer le **rayon** (200 m appliqué par défaut) | Décision métier, non bloquante — `--rayon` permet d'ajuster |
| **A-S-11** | **Réparer `scripts/backup_injs_lmd.sh`** (`pg_dump` tué) | Hors périmètre du lot ; **prioritaire** avant toute opération à risque |
| **A-14** | Exposer la couche EDT (API / écran) | Utile, mais hors périmètre de la faille : la couche est prête à être branchée |
| N-04, N-07, N-08 | Seed honnête, smoke idempotent, E2E robuste | Lot 1 — non démarré |
| N-03 | Client sur le canal EDT | Lot 4 — non démarré |

> ⚠️ **Le rayon reste à confirmer.** J'ai retenu **200 m** (valeur par défaut de
> `MOBILE_GEOFENCE_DEFAULT_RADIUS_M`), le seed historique utilisant 300 m.
> Un campus de formation couvre rarement 300 m de rayon : si le site réel est plus vaste, des badgeages
> légitimes seront refusés. `--rayon` permet de corriger sans nouveau développement.




