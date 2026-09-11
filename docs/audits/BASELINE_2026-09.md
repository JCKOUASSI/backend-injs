# BASELINE DE NON-RÉGRESSION — APPLICATION INJS-LMD 2026 (`app-injslmd2026demo`)

> **Prompt : P00-01 — Ré-audit à chaud et baseline de non-régression (LOT 0, lecture seule).**
> Date du relevé : **2026-09-11** · Branche : `arena/01a08d49-app-injslmd2026demo` · Tête : **`1ec2515`** (« Retrait workflow/fichier temporaires de diagnostic Flutter »), commit de référence cité par P00-01.
> Environnement de relevé : sandbox Arena (Python 3.11.2, Node v22.22.3, npm 10, Git 2.39.5, SQLite 3.40 module) ; **PostgreSQL, Docker, Redis, Flutter et le client `sqlite3` sont absents du sandbox**.
> Outillage : scripts `arena/bootstrap.sh`, `arena/probe.sh`, `arena/feux-verts.sh` livrés par le mode opératoire Arena ; overlay `arena/settings_sandbox.py` (SQLite mémoire pour les tests, courriel en mémoire, pas de broker).
> Rapports bruts conservés : `arena/probe-20260911-1644.txt` (baseline probe officielle), `arena/p00-01-test-run-nopar.log` (suite Django complète), `arena/feux-verts.log`.

**Règle J.8** : l'audit détaillé [S1] du 11/09/2026 fait foi pour l'état du code ; les écarts chiffrés ci-dessous sont des **faits mesurés** à proposer au pilote, pas des corrections automatiques.

---

## A. Architecture réelle

Monorepo trois pistes sous une racine unique :

```
app-injslmd2026demo/
├── backend/            Django 5.1.4 + DRF 3.15.2 (config.settings, 20 applications métier à plat)
├── frontend/           React 18.2 + Vite 7 (npm ; vite build vérifié ✓)
├── qr_badge_mobile/    Flutter (piste mobile ; Flutter absent du sandbox, validée en CI/poste)
├── docs/               documentation, transcripts, audits
└── scripts/            utilitaires (sauvegarde, démarrage, génération PDF)
```

Versions réellement installées/vérifiées (sources citées) :

| Brique | Version réelle | Source de vérité |
|---|---|---|
| Django | **5.1.4** | `backend/requirements.txt:5`, import runtime |
| DRF | **3.15.2** | `backend/requirements.txt:7` |
| SimpleJWT | 5.4.0 | requirements + runtime |
| psycopg2-binary | 2.9.10 (installé ; aucun serveur PG dans le sandbox) | requirements:19 |
| Redis client | 5.2.1 (serveur absent) | requirements:30 |
| Python | 3.11.2 dans le sandbox (**projet cible 3.12** ; CI = 3.12) | `python3 --version` |
| React | 18.2 | `frontend/package.json` |
| Vite | 7 | `frontend/package.json` |
| Node / npm | v22.22.3 / 10 | runtime (CI Node 22) |
| Flutter | **absent du sandbox**, CI épinglée 3.41.7 | `.github/workflows/ci.yml` |
| drf-spectacular | présent (Swagger + OpenAPI 3.0.3) | `/api/docs/` et `/api/schema/` répondent 200 |

- Base par défaut : **PostgreSQL** (`config/settings.py`, bloc `DATABASES`), bascule SQLite de développement par `USE_SQLITE=1` / `SQLITE_PATH`.
- Cache : LocMem si `DEBUG`, Redis si `REDIS_URL`, sinon FileBasedCache (`config/settings.py:220-245`).
- Pas de `pytest` : le runner est celui de Django (`manage.py test`). Scripts npm : `dev`, `build`, `preview`, `lint` (**pas encore de script `test` — E11, corrigé par P00-04**).

---

## B. Backend (apps, modèles, migrations, routes, admin)

- **20 applications Django** (vérifié, égal à l'audit) :
  `administrations, admissions, authentication, dashboard, edts, equivalences, exports, finances_etudiantes, formations, graduation, jurys, parametres, patrimoine, presences, referentiels, ressources_humaines, scolarite, stages, statistiques, suiviEvaluation` (+ package projet `config`, non applicatif ; 30 entrées `INSTALLED_APPS` au total).
- **133 classes de modèles** (`models.Model`) — égal à l'audit (J.1 : le rapport [S3] annonçait 138, l'écart de 5 n'est pas confirmé sur le code).
- **184 migrations** — égal à l'audit. `makemigrations --check --dry-run` → **« No changes detected »** (aucune migration manquante, code retour 0). `manage.py check` → **0 problème**.
- **Commandes de gestion : 32** (audit 31, +1).
- Lignes Python : **96 557** (audit 88 068) dont 8 489 de migrations et 16 234 de tests ; hors migrations et tests : 71 834.
- Déclarations d'URL : **387** `path()/re_path()` dans les `urls.py` des applications ; 26 inclusions racines dans `config/urls.py` (dont `admin/`, `dashboard/`, `sw.js`).

Routes par application (déclarations dans les `urls.py`) :

| App | Routes | App | Routes | App | Routes |
|---|---:|---|---:|---|---:|
| formations | 89 | presences | 31 | admissions | 29 |
| scolarite | 49 | suiviEvaluation | 16 | statistiques | 15 |
| exports | 14 | stages | 13 | edts | 11 |
| finances_etudiantes | 13 | graduation | 12 | administrations | 10 |
| equivalences | 9 | patrimoine | 8 | authentication | 8 |
| jurys | 7 | ressources_humaines | 7 | dashboard | 5 |
| referentiels | 1 | parametres | 1 | | |

- Endpoints de contrôle : `/api/health/` → **200** `{"status":"ok","database":"ok"}` ; `/api/docs/` → **200** (Swagger « INJS API ») ; `/api/schema/` → **200** (OpenAPI 3.0.3).
- **27 fichiers de tests backend ont un résultat vert isolément dans les autres apps ; voir section J pour les non-verts.** Fichiers de tests : **80** (audit 76, +4). Méthodes `test_*` : **943** (égal à l'audit, plancher de non-régression).
- Administration Django enrichie (`admin_mixins.py`, `admin_forms.py`, provisioning de comptes badge).

Répartition des méthodes de test par application :

| App | Fichiers | Méthodes | Lignes | App | Fichiers | Méthodes | Lignes |
|---|---:|---:|---:|---|---:|---:|---:|
| scolarite | 12 | 247 | 3 356 | formations | 27 | 238 | 4 462 |
| presences | 4 | 85 | 1 653 | admissions | 3 | 80 | 928 |
| statistiques | 11 | 61 | 1 313 | authentication | 3 | 68 | 1 083 |
| config | 5 | 24 | 279 | referentiels | 2 | 19 | 189 |
| parametres | 1 | 18 | 237 | jurys | 2 | 17 | 614 |
| exports | 1 | 24 | 408 | administrations | 1 | 10 | 99 |
| patrimoine | 1 | 9 | 97 | equivalences | 1 | 10 | 203 |
| ressources_humaines | 1 | 7 | 74 | suiviEvaluation | 1 | 6 | 142 |
| stages | 1 | 5 | 90 | finances_etudiantes | 1 | 4 | 60 |
| graduation | 1 | 4 | 43 | dashboard | 1 | 7 | 48 |
| **edts** | **0** | **0** | **0** | | | | |

---

## C. Frontend (pages, routes, services, hooks, CSS)

- **106 fichiers `.js/.jsx`**, **35 549 lignes** (audit 105 / 35 495). **0 fichier de test, 0 framework de test** (E11).
- `src/pages/` : **54 pages** ; composants : 27 ; contextes : 11 ; services : 2 (`api.js`, etc.) ; feuilles CSS : 2.
- Routes React dans `App.jsx` : **52 éléments `<Route >` réels** (l'audit annonçait 53 ; le 53ᵉ décompte incluait probablement la balise englobante `<Routes>` — **écart à arbitrer**).
- Navigation : menu latéral avec filtrage par rôle aligné sur `role_groups.py` (`frontend/src/utils/roles.js`, en-tête « Aligné sur backend/authentication/role_groups.py »).
- **ESLint : 89 avertissements, 0 erreur** (égal à l'audit) ; **build Vite : succès** (3,4 s ; seul avertissement de chunk > 500 kB).
- Script `npm run test` **inexistant** → feu 2 « test » rouge jusqu'à P00-04 (exception documentée par le mode opératoire).
- Fichiers de plus de 650 lignes : **12** (audit 9) ; fichiers de plus de 800 lignes (cible G.1 = 0) : **5** :
  `Statistiques.jsx` **5 508**, `ModuleDetail.jsx` 1 937, `FormationDetail.jsx` 1 818, `components/ParticipantDetailModal.jsx` 1 134, `pages/Dashboard.jsx` 806.
- Point d'attention aperçu : `services/api.js:1` porte un repli codé en dur `http://127.0.0.1:8000/api` si `VITE_API_URL` est absent (à neutraliser en preview par `.env`/proxy ; le code navigateur ne doit jamais joindre localhost).

---

## D. Mobile (`qr_badge_mobile/`)

- **43 fichiers Dart, 8 021 lignes** (audit 40 / 7 818) ; **3 fichiers de tests** (`test/open_session_recovery_test.dart`, `session_provider_heartbeat_test.dart`, `user_facing_error_test.dart`).
- Assets : `assets/app_icon.png` ; `.env.example` présent (l'asset `app.env` reste le point connu de sensibilité CI, risque R6 — à ne pas modifier).
- Flutter absent du sandbox : **`flutter analyze` est NON LEVABLE ici**, à exécuter en CI ou sur poste équipé.
- Côté backend, rôles mobile : `MOBILE_ENCADRANT_ROLES = {ENCADRANT, SUPERVISEUR}` (SUPERVISEUR explicitement qualifié de legacy dans `role_groups.py`).

---

## E. Base de données (moteur, migrations appliquées)

- Production/défaut : PostgreSQL (nom de base par défaut hérité `qr_badge`, variable `POSTGRES_DB` — **nom legacy à renommer documentairement**, R5 ; les procédures parlent de `injs_lmd_current`).
- `USE_SQLITE=1` fournit un chemin de développement SQLite déjà présent dans les réglages ; le projet n'active **pas** `django.contrib.postgres` (0 occurrence) et n'utilise ni `SearchVector`, ni `ArrayField`, ni opérateurs PG ; 37 `JSONField` (portables sur SQLite moderne) → la compatibilité de la suite avec SQLite est globalement bonne, sous réserve du point J1 ci-dessous.
- Migration complète testée sur base jetable `/tmp` (jamais sur une base du dépôt) : toutes les migrations s'appliquent, mais le **schéma physique SQLite obtenu est incomplet sur `formations_refsalle`** (voir J1, défaut du chemin de secours SQLite de la migration `0086`).
- Aucune migration non appliquée ne manque (`makemigrations --check` propre).

---

## F. Authentification et permissions N0–N4 (matrice réelle)

- Les **12 rôles métier existent exactement** (`authentication/models.py`, `User.Role`) :
  `ADMIN, DIRECTION, CHEF_CPFAE_ADMIN, CPFAE_ADMIN, CHEF_SECRETARIAT, SECRETARIAT, FINANCE, ARCHIVE, ENCADRANT, SUPERVISEUR, FORMATEUR, AUDITEUR`.
  *Note : le libellé du rôle `AUDITEUR` est encore « Étudiant » dans le modèle — reliquat à corriger (R5).*
- Groupes effectifs codés dans `authentication/role_groups.py` : `ADMIN_LEVEL_ROLES / DUAL_ACCESS_ROLES` (ADMIN, CHEF_CPFAE_ADMIN, CPFAE_ADMIN), `ALLOWED_WEB_ROLES` (11 rôles web), `OPERATIONAL_WEB_ROLES` (web hors FINANCE), `SECRETARIAT_ROLES`, `GLOBAL_ACCESS_ROLES`, `DASHBOARD_SECRETARIAT_FILTER_ROLES`, `MOBILE_ENCADRANT_ROLES`.
- Autres mécanismes présents : JWT SimpleJWT + `FlexibleJWTAuthentication`, throttling (`THROTTLE_LOGIN_RATE`, `THROTTLE_SCAN_RATE`, `THROTTLE_OFFLINE_DATA_RATE`), `DeviceBinding`, permissions DRF dédiées, synchronisation de profil, middleware de preview/démo (**`DEMO_ADMIN_AUTOLOGIN` inactif par défaut, gardé hors production**).
- **Écart confirmé vis-à-vis de DA-05 : le formalisme N0–N4 (niveau × permission × module × périmètre × état) n'existe encore ni côté backend ni dans `utils/roles.js`.** Seule une logique de rôles/groupes existe. Le mapping des 12 rôles vers N0–N4 reste donc à construire (P01-05) et à faire valider par le commanditaire (point de synchro avant P01-05, gate humaine G2). Les périmètres actuels dérivent surtout du secrétariat rattaché (`secretariat_id`) et de `user_has_stats_access(...)`.

---

## G. API (index des routes par domaine)

- Préfixes racines principaux : `api/administrations/, api/admissions/, api/auth/, api/edts/, api/enseignants/, api/equivalences/, api/evaluations/, api/exports/, api/finances-etudiantes/, api/formations/, api/graduation/, api/juries/, api/parametres/, api/patrimoine/, api/referentiels/, api/rh/, api/scolarite/, api/stages/, api/statistiques/` + `api/health/`, `api/docs/`, `api/schema/`.
- Le frontend ne parle qu'à Django/DRF (règle 7 respectée ; aucun accès direct base).
- Génération OpenAPI : **nombreux avertissements drf-spectacular** (vues fonctionnelles sans `serializer_class` déductible, `FlexibleJWTAuthentication` sans extension OpenAPI, collisions d'`operationId` liste/détail sur une trentaine de routes, notamment admissions, edts, finances, scolarite, stages, statistiques) — aucun n'empêche le schéma de répondre, mais la doc OpenAPI est à compléter (à rattacher aux prompts de socle/documentation).
- Contrat externe : `api/scolarite/edt/` (planificateur externe, DA-09) existe ; vérifier son marquage lecture seule dans le prompt dédié.

---

## H. Modules déjà présents (table de maturité 0→3 par domaine)

État dérivé de [S1]/PARTIE D, reconfirmé par les comptages du jour (maturité approximative : 0=absent, 1=API partielle, 2=API complète et/ou UI partielle, 3=complet) :

| Module réf. | Domaine | App(s) | Backend | UI web | Maturité |
|---|---|---|---|---|---|
| 01 | Référentiels | formations/scolarite/referentiels/parametres | partiel+app commune `referentiels` | partielle | 2 |
| 02 | Candidatures/admissions | admissions (15 modèles) | complet | partiel | 2 |
| 03 | Étudiants | scolarite (+formations.Participant) | complet | partiel | 2 |
| 04 | Formations/pédagogie | scolarite + formations | complet (maquettes versionnées) | partiel | 2 |
| 05 | Enseignants | formations.Formateur / ressources_humaines | complet | partiel | 2 |
| 06 | EDT | edts (+SessionModule) | partiel, **0 test** | partiel | 1 |
| 07 | Campus/patrimoine | patrimoine + RefSite/Salle/Batiment | partiel | **absent (0 écran)** | 1 |
| 08 | Présences | presences | complet (QR, heartbeat, DeviceBinding, geofence) | partiel | 2 |
| 09 | Notes/évaluations | formations (NoteModule…) + suiviEvaluation | complet | complet | 3 |
| 10 | Jurys/diplômation | jurys, graduation, equivalences | complet | partiel | 2 |
| 11 | Finances étudiantes | finances_etudiantes (9 modèles) | complet | **~25 % (4 appels UI)** | 1 |
| 12 | Direction financière/compta. | formations.FinanceSettings (formateurs seuls) | **absent pour la comptabilité** | absent | 0 |
| 13 | Administration & RH | administrations, ressources_humaines, stages | API présentes | **absent (0 écran)** | 1 |
| 14 | Documents/courriers/archives | administrations | partiel | **absent (0 écran)** | 1 |
| 15 | Notifications | dispersé (presences, jurys, finances) | épars | épars | 1 |
| 16 | Rapports/BI | statistiques, dashboard, exports | complet (cache, PDF/Excel) | complet | 2 |
| 17 | Portails/services en ligne | frontend React, Flutter/PWA, `views_legacy.py` | partiel | partiel | 1 |
| 18 | Administration système/sécurité | authentication, parametres, presences.AuditLog | complet (JWT, throttling, RBAC rôles) | partielle | 2 |

---

## I. Écrans déjà présents (liste + nombre d'appels API par domaine)

Appels API du frontend par domaine (chemins relatifs utilisés via `services/api.js`) :

`formations` 94 · `scolarite` 54 · `evaluations` 42 · `admissions` 27 · `statistiques` 20 · `auth` 14 · `edts` 9 · `rattrapages` 7 · `equivalences` 5 · `enseignants` 5 · `graduation` 4 · `finances-etudiantes` 4 · `parametres` 3 · `participant` 3 · `juries` 2 · `formateurs` 1 · `scan` 1.

- **Les 4 domaines orphelins d'écran (E1) sont confirmés à 0 appel API et 0 écran React** : `stages`, `patrimoine`, RH (`rh`/`ressources_humaines`), `administrations` (courriers).
- Finances étudiantes : seuls 4 appels UI → taux de couverture ~25 % confirmé (E2).
- États des 5 très gros écrans listés en section C ; les modules 11/13/14 sont les principaux absents d'écrans.

---

## J. Problèmes détectés (ordre de criticité pour l'exécution du LOT 0)

**J1 — CRITIQUE pour le sandbox : migration `formations/0086_refsalle_type_lieu_fields` cassée sur SQLite.**
La migration utilise `SeparateDatabaseAndState` : DDL PostgreSQL en dur (branche `postgresql`) et une fonction `apply_salle_columns()` qui ajoute les colonnes via `schema_editor.add_field()` sur SQLite. Avec Django 5.1.4, l'éditeur SQLite **reconstruit la table** pour tout champ non-null ou avec défaut (et ne peut pas faire `ALTER TABLE ADD COLUMN` avec `DROP DEFAULT`) ; à la 3ᵉ colonne (`equipements`), la table est recréée à partir de l'état du modèle à 0085, ce qui **supprime physiquement `type_lieu` et `capacite`**. Résultat mesuré : après migration complète, `formations_refsalle` possède bien `equipements, indisponible_du, indisponible_au, type_espace_id` mais **pas `type_lieu` ni `capacite`**. Conséquence : **19 erreurs de tests** dans le sandbox (`admissions` concours/classement, `scolarite` EDT/charges, `formations` RefSalle, `patrimoine` réservations) toutes avec `OperationalError: table formations_refsalle has no column named type_lieu`. Sur PostgreSQL (chemin `RunSQL`), la CI backend est verte.
→ **Ne pas modifier la migration 0086** (règle 5 / migrations existantes intouchables). Correctif propre à livrer : une **nouvelle migration** qui, sur SQLite, ajoute les colonnes manquantes en SQL natif (ou rend le modèle cohérent avec `type_espace` introduit en 0090) ; décision à prendre en P00-02/P01-01. **Tant qu'elle n'est pas tranchée, le feu 1 ne peut pas être vert dans le sandbox.**

**J2 — 6 échecs de tests (hors migrations) sous l'overlay SQLite, qualifiés :**
1. `config.tests.test_socle.ProductionHardeningTests.test_settings_allow_no_wildcard_literal` : attend `ALLOWED_HOSTS` sans `'*'` ; l'overlay sandbox impose délibérément `ALLOWED_HOSTS=['*']` pour la preview → **échec induit par l'overlay, sans objet en conditions réelles** (les réglages filtrent `'*'` hors DEBUG ; CI verte).
2. `referentiels.tests.test_api.ReferentielsAPIAccessTests.test_regle4_doublon_libelle_casse_rejete` : le rejet d'un douillon de libellé à casse/accent différent (`Épreuve écrite` vs `épreuve ÉCRITE`) repose sur `UniqueConstraint(Lower('libelle'))` ; le `LOWER()` de SQLite ne replie pas les caractères accentués (ASCII) alors que PostgreSQL oui → **écart de moteur** (PostgreSQL vert en CI).
3–6. Quatre tests de cache statistiques (`statistiques/tests/test_dashboard_cache.py`) : **défaut d'isolation inter-tests** — `LocMemCache` conserve ses données au niveau module par `LOCATION` (`django/core/cache/backends/locmem.py:11,21`) et les tests n'appellent pas `cache.clear()` en `setUp` ; ils passent isolés (un cas testé seul : OK) mais échouent en classe/module (le plus tôt pollue le suivant : `1 != 2`, `0 != 1`). Le mécanisme est indépendant du moteur ; la CI backend PostgreSQL à `1ec2515` est néanmoins rapportée **verte** (logs GitHub momentanément indisponibles lors du relevé — incident de stockage Azure —, ce point est donc **à reconfirmer en recette PG** ; un `cache.clear()` défensif en `setUp` reste recommandé).

**Bilan suite backend dans le sandbox : 943 tests détectés, 902 exécutés (41 non exécutés : classes en échec `setUpClass`), 877 réussites, 19 erreurs, 6 échecs (249 s, 1 processus).**
Le mode `--parallel 2` du script `feux-verts.sh` échoue en outre par `TypeError: cannot pickle 'traceback' object` quand un worker lève une erreur au montage ; le relevé fiable s'est fait sans parallélisme.

**J3 — CI (branche `1ec2515`) : 2 jobs verts sur 3, comme à l'audit.** Backend PostgreSQL (Python 3.12) : **vert** ; Frontend (lint+build) : **vert** ; Mobile (Flutter analyze) : **échec (R6)**. Attention : la tête de `main` (`99fd5e9`, qui ajoute uniquement les documents de pilotage) montre quant à elle les 3 jobs en échec — son arbre de code racine n'est pas celui de cette branche (les deux lignes divergent : 1 commit propre à `main`, 81 à cette branche ; `formations/api_cache.py`, `statistiques/tests/test_dashboard_cache.py` n'existent pas sur `main`). La refonte s'appuie sur la branche `1ec2515`.

**J4 — Reliquats legacy (R5/R12), quantifiés :** SYGEP/sygep dans 18+13 fichiers ; `CPFAE` dans 103 fichiers ; `QR Badge`/`qr-badge`/`qr_badge` dans 14/7/24 fichiers ; `MEMFPMA` dans 3 ; `DFRC` dans 80 ; CDN `html5-qrcode` dans 4 ; Bootstrap 5.3 CDN dans 9 ; `logo-sygepcpfae` dans 2.
Présents physiquement : `backend/static/sw.js` et `backend/staticfiles/sw.js` (« qr-badge-v3 »), `backend/dashboard/views_legacy.py` (1 951 lignes), images `backend/static/img/logo-sygepcpfae.png` et `logo-mfpma.jpeg` (+ copies collectées dans `staticfiles/`). Les courriels transactionnels (`authentication/emails.py') sont encore entièrement estampillés SYGEP-CPFAE/DFRC (sujets, signatures, logo en data URI). Cohérent avec DA-12 : retrait en dernier, derrière flag et fenêtre d'observation.

**J5 — Hygiène de dépôt (R4/R5).** `backend/staticfiles/` (**18 Mo**) est versionné ; des données binaires/nominatives sont versionnées dans `backend/` : `import_formateurs.xlsx`, `import_formations.xlsx`, `import_participants.{csv,xlsx}`, `import_seances.xlsx`, `importverif/*.xlsx`, `modele_*.csv`, `test_import_formations_seances.xlsx`, et `LISTE DES FORMATEURS FAB 2026 - 19-04-2026.numbers` (878 Ko) — à sortir du dépôt en P00-02. Fichiers géants backend confirmés : `formations/api_views.py` 4 980, `exports/views.py` 3 455, `presences/views.py` 3 368, `statistiques/views.py` 2 084, `dashboard/views_legacy.py` 1 951, `formations/management/commands/import_excel.py` 1 747, `formations/models.py` 1 366, `scolarite/models.py` 1 279.

**J6 — Qualité OpenAPI/observabilité.** Avertissements spectacular (section G) ; **271 `print()` runtime** (audit 288) et absence de Sentry/APM (E12/R7) ; `select_related/prefetch_related` : 363 occurrences (audit 359).

**J7 — En-têtes de migrations « Generated by Django 6.0.3 »** (migrations 0001 à 000x, datées de mars 2026) : simples commentaires historiques de génération, aucune dépendance à Django 6 n'est requise (J.3 : requirements = 5.1.4). À laisser tels quels, à mentionner dans P00-03.

**J8 — Origine des écarts de comptage.** Les comptages du jour sont identiques sur l'arbre `1ec2515` et sur la copie figée `workspace/backend@99fd5e9` (à ±350 lignes près) : les écarts vs [S1] (lignes Python +8 489, fichiers de tests +4, lignes Dart +203, fichiers front +1, etc.) ne viennent **pas** d'une dérive récente mais vraisemblablement d'un périmètre de comptage différent lors de l'audit. Ils sont sans impact fonctionnel et à acter dans l'onglet « Écarts E ».

---

## K. Risques (rappel R1→R12, état vérifié ce jour)

- **R1 — domaines sans UI** : confirmé (4 domaines à 0 écran ; finances étudiantes ~25 %).
- **R2 — aucun test frontend** : confirmé (0 framework, pas de script `npm test`).
- **R3 — doubles représentations D1–D5** : non revérifiées une à une dans P00-01 (objet des prompts dédiés P01/P02/P04/P05).
- **R4 — fichiers géants** : confirmé (5 écrans >800 lignes côté front ; 8 fichiers Python >1 200 lignes).
- **R5 — identité/hygiène dépôt** : confirmé (J4, J5 ; nom de base PG `qr_badge` ; libellé `AUDITEUR`=« Étudiant »).
- **R6 — CI mobile instable** : confirmé, job Mobile rouge à `1ec2515` (asset `app.env`).
- **R7 — observabilité** : confirmée (271 print, pas de Sentry).
- **R8 — maquettes actives/notes** : mécanismes partiels présents (verrous objets corrections dans les apps métiers) ; couverture complète attendue LOT 2.
- **R9 — concours partiellement écrantés** : confirmé côté UI ; backend présent mais non testable dans le sandbox du fait de J1.
- **R10 — staging/CD/sauvegarde restauration** : workflows Docker Hub présents mais en échec sur `main` ; exercice de restauration non réalisé.
- **R11 — e-mail Gmail / SMS absents** : confirmé (`EMAIL_HOST=smtp.gmail.com` par défaut, `EMAIL_HOST_USER` vide ; pas de passerelle SMS).
- **R12 — socle HTML/CDN/PWA legacy** : confirmé (J4).

---

## L. Éléments manquants par rapport au modèle fonctionnel de référence

Les 17 écarts nets E1→E17 de la PARTIE E restent valides dans leur principe ; confirmations du jour : E1 (4 orphelins), E2 (4 appels finances), E11 (0 test front), E12 (271 print, pas de Sentry), E15 (**edts : 0 test** ; exports 24 méthodes, dashboard 7 — partiellement couverts), E17 (fichiers géants aux dimensions annoncées). Le module 12 comptabilité demeure **totalement absent** (E3) ; le hub notifications (E6), les portails public/candidat (E7), la GED (E10), le moteur d'EDT automatique (E4) et la hiérarchie campus complète (E5, `type_espace` amorcé en migration 0090) restent à construire selon le plan.

---

## M. BASELINE CHIFFRÉE (à mettre à jour après chaque lot — jam ais à la baisse pour les tests)

| Indicateur | Relevé 2026-09-11 | Audit [S1] | Écart | Objectif / sens |
|---|---:|---:|---|---|
| Applications Django | 20 | 20 | 0 | stable (DA-01) |
| Modèles Django | 133 | 133 | 0 | n/a |
| Migrations | 184 | 184 | 0 | additions réversibles seules |
| Migration manquante (`makemigrations --check`) | 0 | — | — | rester à 0 |
| Lignes Python (totale probe) | 96 557 | 88 068 | +8 489 | information |
| Fichiers de tests backend | 80 | 76 | +4 | ↑ |
| **Méthodes de test backend (plancher)** | **943** | **943** | **0** | **jamais de baisse** |
| Tests verts dans le sandbox SQLite | 877 / 902 exécutés (943 détectés) | — | 19 err + 6 éch (voir J) | 100 % après arbitrage J1/J2 |
| Backend CI PostgreSQL (3.12) | **vert à `1ec2515`** | — | — | rester vert |
| `print()` runtime | 271 | 288 | −17 | **→ 0 (P00-05)** |
| `select_related`/`prefetch_related` | 363 | 359 | +4 | ↑ |
| Commandes de gestion | 32 | 31 | +1 | information |
| Fichiers `.js/.jsx` | 106 | 105 | +1 | information |
| Lignes frontend | 35 549 | 35 495 | +54 | information |
| Fichiers de tests frontend | 0 | 0 | 0 | framework en P00-04, puis ↑ |
| Script `npm run test` | absent | absent | — | ajouté P00-04 |
| ESLint (erreurs / avertissements) | **0 / 89** | 0 / 89 | 0 | 0 erreur maintenu |
| Build Vite | succès | — | — | rester vert |
| Fichiers front > 650 / **> 800 lignes** | 12 / **5** | 9 / 9 (seuil 650) | +3 / — | **0 > 800 (G.1)** |
| Fichiers Dart / lignes | 43 / 8 021 | 40 / 7 818 | +3 / +203 | information |
| Tests Dart | 3 fichiers | — | — | `flutter analyze` hors sandbox |
| Routes `<Route>` React | 52 | 53 | −1 (à confirmer) | inventaire figé |
| Déclarations d'URL DRF | 387 | — | — | contrat d'API stable |
| Domaines backend sans écran UI | **4** (stages, patrimoine, RH, administrations) | 4 | 0 | **→ 0 (P06-06/P10)** |
| Couverture UI finances étudiantes | ~25 % (4 appels) | 25 % | 0 | **→ 100 % (P09-01→04)** |
| Tests edts / exports / dashboard | 0 / 24 / 7 méthodes | 0 / 0 / 0 | — | P06-05, P06-09 |
| CI (jobs verts à `1ec2515`) | 2 / 3 (mobile rouge R6) | 2 / 3 | 0 | 3 / 3 |
| Feu 3 Flutter dans Arena | **NON LEVABLE** | — | — | obligatoire hors sandbox à chaque gate |
| `staticfiles/` versionné | 18 Mo | — | — | sortir du dépôt (P00-02) |

---

## N. Recommandation pour la prochaine étape

**Une seule prochaine étape recommandée : ouvrir P00-02 (« Hygiène du dépôt ») APRÈS arbitrage explicite du pilote sur les trois points suivants,** qui conditionnent les feux verts du sandbox :

1. **J1 — défaut SQLite de la migration 0086** : approuver le principe d'une *nouvelle* migration additive (sans toucher 0086) pour créer `type_lieu`/`capacite` sur SQLite (ou aligner le modèle sur `type_espace`), ce qui rendra le feu 1 vert dans Arena ; revalider obligatoirement LOT 9 et LOT 11 sur PostgreSQL réel avant leurs gates.
2. **J2 — 6 échecs sandbox** : enregistrer l'échec `ALLOWED_HOSTS` comme écart d'overlay sans action code ; confirmer le comportement PostgreSQL de `test_regle4` et des 4 tests de cache en recette (CI verte), et planifier un `cache.clear()` défensif en `setUp`.
3. **J3/J4/J5** : confirmer que la refonte s'appuie bien sur la branche `1ec2515` (et non sur la tête de `main`), puis faire sortir de P00-02 les binaires/données nominatives et `staticfiles/`.

Aucune modification automatique n'a été réalisée par ce prompt. Les seuls artefacts ajoutés en dehors du présent rapport sont les outils de pilotage Arena (`arena/`, issus des préalables validés par le commanditaire), le dossier généré `frontend/dist/` (construction hors dépôt, ignoré) et les journaux cités en en-tête.

### Vérification des 10 incohérences J.1→J.10 (DoD P00-01)

| Incohérence | Vérification du jour |
|---|---|
| **J.1** nombre de modèles (133 vs 138) | **133 confirmé par comptage des `models.Model`** → [S1] retenu |
| **J.2** nombre de tests (943 vs 890) | **943 méthodes détectées par le runner** (« Found 943 test(s) ») → [S1] retenu ; CI PG verte, sandbox 25 non-verts expliqués (J1/J2) |
| **J.3** version Django (« 5.1/6 ») | **Django 5.1.4** réel ; seules des en-têtes de migrations citent « 6.0.3 » (commentaires historiques) → P00-03 documentera |
| **J.4** arborescence cible vs réelle | 20 apps à plat nomenclature française confirmées → DA-01 (conserver, créer seulement core/comptabilite/notifications/portails) |
| **J.5** règles comptables module 12 | rien dans le code ; décision humaine toujours requise avant P09-08 (J.5 du livrable) |
| **J.6** e-mail/SMS | SMTP Gmail par défaut, SMS absent, couche d'abstraction à livrer P11-01/02, choix prestataire humain |
| **J.7** 12 rôles vs liste [S2] | les 12 rôles existent à l'identique ; N0–N4 non modélisés (DA-05, synchro avant P01-05) |
| **J.8** statut du rapport [S3] | les constats [S1] (UI 25 %, 0 écran orphelin, 0 test edts, fichiers géants) sont confirmés par le code → [S1] fait foi |
| **J.9** périmètre UFR vs INJS global | multi-périmètre présent (sites, secrétariats, `secretariat_id`) ; aucune hypothèse mono-site codée en dur constatée |
| **J.10** nom de fichier de l'audit | fichier « Audit complet et détaillé de app-injs-lmd2026demo.txt » bien identifié comme source [S1] |

---

*Fin du rapport P00-01 (phase de relevé initial). Conformément au prompt : aucune correction n'avait été appliquée durant la phase de relevé, aucune migration lancée sur une base du projet, aucun commit effectué.*

---

## ADDITIF DU 2026-09-11 — CORRECTIFS DE STABILISATION APRÈS ARBITRAGE DU COMMANDITAIRE

Sur décision explicite du commanditaire, trois correctifs de stabilisation (hors fonctionnel métier) ont été appliqués pour rendre le filet de tests exploitable dans le sandbox :

1. **J1 — migration additive `formations/0092_refsalle_sqlite_columns.py`.** Crée physiquement `type_lieu` et `capacite` sur **SQLite uniquement** (SQL natif `ALTER TABLE`, idempotent), no-op sur PostgreSQL (où 0086 est correct), marche arrière à vide. Les migrations 0086 et suivantes n'ont **pas** été modifiées (règle 5). Après cette migration, le schéma SQLite de `formations_refsalle` est complet (`…, equipements, indisponible_du, indisponible_au, type_espace_id, type_lieu, capacite`) et `makemigrations --check` reste propre.
2. **J2 — isolation des tests de cache statistiques.** Ajout de `cache.clear()` dans le `setUp` des 3 classes de `statistiques/tests/test_dashboard_cache.py` (LocMemCache partagée par `LOCATION`) ; correctif uniquement dans les tests.
3. **J2 — outillage Arena durci.** L'overlay généré par `arena/bootstrap.sh` ne pose plus `ALLOWED_HOSTS=['*']` mais `['testserver','localhost','127.0.0.1','.e2b.app']` (la preview Arena reste joignable via `.e2b.app`), ce qui rend le test de durcissement applicable. `arena/feux-verts.sh` utilise par défaut un exécution mono-processus (`FEUX_VERTS_PARALLEL`, défaut 1) car `--parallel 2` fait remonter « cannot pickle 'traceback' object » dans ce sandbox et masque le résultat (export `FEUX_VERTS_PARALLEL=2` sur CI/poste).

**Résultat après correctifs (mono-processus, overlay SQLite) :**

| Avant | Après |
|---|---|
| 902 exécutés / 943 détectés, **19 erreurs + 6 échecs** | **943 exécutés, 942 verts, 1 échec** |
| feu 1 bloqué par le schéma | feu 1 bloqué par un **unique écart moteur documenté** |

Le seul échec restant est `referentiels.tests.test_api.ReferentielsAPIAccessTests.test_regle4_doublon_libelle_casse_rejete` : différence de pliage Unicode entre SQLite (`LOWER()` ASCII) et PostgreSQL (plie les accents), verte en CI PostgreSQL. Il fait l'objet de l'**[ADR-006 `docs/ADR/ADR-006-unicite-libelles-insensible-casse.md`](../ADR/ADR-006-unicite-libelles-insensible-casse.md)** et sera corrigé fonctionnellement en **LOT 1 (référentiels P01-02/P01-03)** ; aucun test n'est marqué ignoré pour contournement.

État des feux après correctifs : **feu 1** = migrations/checks verts, tests 942/943 (1 écart moteur fléché LOT 1) · **feu 2** = ESLint 0 erreur et build Vite verts, tests Vitest indisponibles jusqu'à P00-04 (exception documentée) · **feu 3** = Flutter NON LEVABLE dans le sandbox (poste/CI).

*Aucune donnée de démonstration n'a été modifiée ou supprimée ; aucune base de projet n'a été migrée (toutes les migrations de diagnostic l'ont été sur des bases jetables `/tmp`).*
