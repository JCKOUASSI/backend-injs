# Audit général — `JCKOUASSI/backend-injs`

**Date** : 2026-09-21 · **Branche auditée** : `arena/01a0c45d-backend-injs` @ `f09d671`
**Méthode** : toutes les valeurs de ce rapport sont des **mesures exécutées ce jour** dans le
dépôt (commandes citées), pas des estimations. Les deux seules données externes sont le
calendrier de support Django (djangoproject.com/download) et l'état des runs GitHub Actions
(API GitHub). Ce qui n'a **pas** pu être vérifié depuis le bac à sable est dit explicitement.

---

## 1. Verdict synthétique

| Dimension | Note | En une ligne |
|---|---|---|
| Tests | 🟢 **Bon** | 3 461 tests exécutés ce jour, 0 échec ; une seule app sans test |
| Hygiène de dépôt | 🟢 **Bon** | `check_repo_hygiene` CONFORME, 0 `print()` runtime, 0 secret commité |
| Sécurité applicative | 🟢 **Bon** | `check --deploy` : 1 seul avertissement, volontaire et documenté |
| **Cadre d'exécution** | 🔴 **Critique** | **Django 5.1.4 est EOL depuis le 3 décembre 2025** — plus de correctifs de sécurité |
| **CI / déploiement** | 🔴 **Bloqué** | CI à l'arrêt pour cause de **facturation GitHub** (4 jobs, 0 étape) |
| **Poids du dépôt** | 🟠 **À traiter** | **46 % du dépôt est une copie dupliquée** (`workspace/`, 26 Mo) poussée en prod par défaut |
| Dette de taille de fichiers | 🟠 **À traiter** | 9 fichiers front > 800 lignes, `formations/api_views.py` à 5 044 lignes |
| Documentation d'API | 🟡 **Perfectible** | 420 endpoints sans schéma (`drf_spectacular.W002`) |
| Documentation projet | 🟢 **Bon** | 89 fichiers / 2,6 Mo sous `docs/`, 6 ADR, BASELINE et audits datés |

**Le projet est sain dans son code et très bien testé. Ses deux vrais problèmes ne sont pas
dans le code** : un cadre d'exécution en fin de vie, et une chaîne de déploiement arrêtée par
un problème de facturation.

---

## 2. Périmètre mesuré

`arena/probe.sh` et comptages directs :

| Piste | Mesure |
|---|---|
| Applications Django | **23** |
| Modèles (`models.Model`) | **151** |
| Migrations | **219** |
| Fichiers de test backend (`test_*.py`, `tests.py`) | **130** |
| Lignes Python (`backend/`) | **128 263** |
| Commandes de gestion | **60** |
| Frontend — fichiers `.jsx/.js` sous `src/` | **268** · **79 170 lignes** · **89 fichiers de test** |
| Mobile — fichiers Dart | **43** · **8 021 lignes** |
| Dépôt suivi par Git | **3 073 fichiers · 56 Mo** |
| Lignes Python suivies **au total** | **305 617**, dont **134 900 dans `workspace/`** (cf. §6) |

Versions réellement installées : Django **5.1.4**, DRF **3.15.2**, SimpleJWT **5.4.0**,
drf-spectacular **0.28.0**, Python **3.11.2** (le projet vise 3.12), Node **v22.22.3**.

---

## 3. Tests — 🟢 le point fort

Exécutés ce jour :

| Suite | Résultat | Durée |
|---|---|---|
| Backend (`manage.py test`, SQLite de secours, `--parallel 1`) | **`Ran 1714 tests` — OK**, 5 sautés | 701 s |
| Frontend (Vitest) | **89 fichiers · 1 747 tests OK** | 144 s |
| **Total** | **3 461 tests, 0 échec** | — |

Contrôles associés, tous verts ce jour :

- `makemigrations --check --dry-run` → **No changes detected** ;
- `check_repo_hygiene` → **CONFORME** (3 073 fichiers suivis, 0 donnée nominative, 0 `print()` runtime) ;
- `export_api_contract --check` → **contrat conforme au snapshot** ;
- `scripts/sync-injs-app.sh --self-test` → **53 PASS / 0 FAIL** ;
- gate `arena/feux-verts.sh` → **PASSÉE** (6 contrôles verts, 0 rouge).

**Seule lacune mesurée** : sur 23 apps, **une seule n'a aucun test** — `referentiel_injs`.
C'est un très bon ratio. À noter : **0 `TODO`/`FIXME`/`HACK` dans `backend/` et
`frontend/src/`**. Sur l'ensemble du code suivi, `git grep` en trouve 47, mais **44 sont dans
`qr_badge_mobile/app_review/_pydeps/PIL/`** — le code source de Pillow embarqué, pas du code
du projet. Les 3 restants sont dans des gabarits générés par l'outillage Flutter
(`android/app/build.gradle.kts`, `linux/flutter/CMakeLists.txt`,
`windows/flutter/CMakeLists.txt`), tous des `TODO` d'origine du modèle Flutter. Le code écrit
par le projet ne porte donc **aucune** dette marquée.

**Limite assumée** : le feu 3 (Flutter, `flutter analyze`) est **non levable** dans le bac à
sable — `flutter` n'y est pas installé. Il doit être passé sur un poste équipé.

---

## 4. 🔴 Critique — Django 5.1 est en fin de vie

`backend/requirements.txt` épingle **`Django==5.1.4`**.

Selon le calendrier officiel (djangoproject.com/download), la série 5.1 a atteint sa
**fin de support étendu le 3 décembre 2025**, dernier correctif publié **5.1.15**.
Nous sommes le 2026-09-21 : le cadre d'exécution tourne donc depuis **≈ 9,5 mois sans
aucun correctif de sécurité**, et avec **11 versions de correctifs** de retard sur sa
propre série.

| Élément | Valeur |
|---|---|
| Version du dépôt | `Django==5.1.4` |
| Fin de support étendu de la série 5.1 | **3 décembre 2025** (dépassée) |
| Dernier 5.1.x publié | 5.1.15 |
| Cible recommandée | **Django 5.2 LTS** — supporté jusqu'en **avril 2028**, Python 3.10 → 3.13 |

**Conséquence** : toute vulnérabilité Django divulguée depuis décembre 2025 reste non corrigée
sur cette application, qui traite des données nominatives d'étudiants et des paiements.

**Recommandation P0** : migration vers **5.2 LTS**. Deux étapes, dans cet ordre :
1. `Django==5.1.15` (correctifs de la série courante, risque quasi nul) ;
2. `Django==5.2.x` LTS, en s'appuyant sur la suite de 1 714 tests comme filet.
   PostgreSQL 15/16 utilisé ici est compatible (Django 5.2 abandonne PostgreSQL 13).

*Non vérifiable ici* : l'existence de CVE précises touchant 5.1.4 — aucun outil d'audit de
dépendances Python n'est installé dans le bac à sable et je n'ai pas ajouté de dépendance
pour ce seul audit. Le constat de fin de support, lui, est établi.

---

## 5. 🔴 Bloquant — la CI est à l'arrêt pour cause de facturation

Les 3 derniers runs de `ci.yml` sont en échec. Mesure via l'API GitHub :

```
Backend (Django)          : failure | 0 étapes
Frontend (Vite / React)   : failure | 0 étapes
Frontend tests (Vitest)   : failure | 0 étapes
Mobile (Flutter)          : failure | 0 étapes
```

**0 étape** signifie que les jobs ne démarrent pas. Annotation GitHub relevée sur le run :
« The job was not started because recent account payments have failed or your spending limit
needs to be increased. »

Ce **n'est pas un défaut de code** : les mêmes vérifications, exécutées localement, sont
vertes (§3). Mais `docs/DEPLOIEMENT_INJS.md` §2 fait d'une **CI verte le prérequis pour armer
la sync de production**. Tant que la facturation n'est pas réglée :

- aucune image n'est validée par la CI ;
- `SYNC_DRY_RUN` doit rester absent (mode sec), ce qui est le comportement par défaut — le
  workflow est correctement sécurisé sur ce point ;
- le déploiement sur `injs.badge-qr-code.pro` ne peut pas être engagé proprement.

**Recommandation P0** : régler GitHub → *Billing & plans*, puis relancer la CI et confirmer
les 4 jobs au vert avant toute sync.

*Note* : `mobile` échouait déjà avant cet arrêt pour une raison distincte (`flutter analyze`,
risque R6 du rapport de base) — à traiter après le rétablissement de la facturation.

---

## 6. 🟠 `workspace/` : 46 % du dépôt est une copie dupliquée, poussée en prod

Mesures :

| Mesure | Valeur |
|---|---|
| Poids suivi sous `workspace/` | **26 Mo sur 56 Mo** (≈ 46 %) |
| Fichiers suivis sous `workspace/` | **1 365** |
| Contenu | `backend/`, `frontend/`, `qr_badge_mobile/`, `docs/`, `scripts/`, `arena/`, `uploads/`, `prompts/` — **une seconde copie de l'application** |
| Lignes Python dupliquées | **134 900 lignes Python sous `workspace/` sur 305 617 lignes `.py` suivies au total — soit 44 % du Python du dépôt** |
| `.gitignore` | n'exclut que `workspace/.pycache/` (ligne 73) — le reste est suivi |
| `SYNC_EXCLUDE_PATHS` | **vide par défaut** — `scripts/sync-injs-app.sh:37` : « défaut : aucun, pour ne surprendre personne » |

**Conséquence directe sur le déploiement** : la sync vers `Tobi-nw/injs-app` pousserait ces
26 Mo de code périmé dans le dépôt de production. Les images Docker n'en seraient pas
cassées (elles construisent depuis `backend/` et `frontend/` de la racine), mais le dépôt de
prod se retrouve avec deux arbres `backend/` divergents — source d'erreur humaine garantie.

**Recommandation P1** : poser `SYNC_EXCLUDE_PATHS=workspace` (au minimum) avant le premier
push réel, et décider du sort de `workspace/` dans le dépôt de dev : soit l'archiver hors de
Git, soit la réduire à ses documents utiles. Le script sait faire — `--suggest-keep` et
`--exclude` existent et sont testés (cas 13 et 14 du harnais).

Autres poids mesurés, du même ordre d'idée :

- **21 Mo de `.dylib`** (36 fichiers) sous `qr_badge_mobile/app_review/_pydeps/PIL/.dylibs/` —
  bibliothèques natives Pillow embarquées dans Git ;
- **121 `.png`** suivis ;
- **5 fichiers `.txt` de prompts** à la racine (145 Ko au total), dont
  `REALISATION-MAJ-INJS-LMD-2026.txt` (68 Ko) — livrables de travail, pas documentation.

---

## 7. Sécurité applicative — 🟢 bon état

`manage.py check --deploy` avec les valeurs de production du domaine cible
(`DEBUG=False`, `DJANGO_ALLOWED_HOSTS=injs.badge-qr-code.pro`, `CSRF_TRUSTED_ORIGINS` et
`CORS_ALLOWED_ORIGINS` alignés, clé de 50+ caractères) :

```
System check identified 1 issue (0 silenced).
?: (security.W008) SECURE_SSL_REDIRECT is not set to True.
```

**Un seul avertissement, et il est volontaire** : `config/settings.py` documente que la
redirection HTTP→HTTPS est assurée par Nginx, pas par Django. Il n'a pas été ajouté à
`SILENCED_SYSTEM_CHECKS` — un contrôle de sécurité masqué est un contrôle oublié.

Autres vérifications :

| Contrôle | Résultat |
|---|---|
| Secrets commités (`git grep` sur motifs `SECRET_KEY`/`PASSWORD`/`TOKEN`/`API_KEY` + valeur longue) | **aucun** |
| Fichiers `.env` suivis par Git | **aucun** — uniquement des `.env.example` |
| Données nominatives / artefacts de build suivis | **aucun** (`check_repo_hygiene` CONFORME) |
| Épinglage des dépendances Python | **31 dépendances, 31 épinglées en `==`** (100 %) |

### Vulnérabilités npm — à relativiser

`npm audit` : **15 vulnérabilités (2 critiques, 6 hautes, 5 modérées, 2 basses)**, toutes
`fixAvailable`. Mais la localisation change complètement la lecture :

| Paquet | Sévérité | Où |
|---|---|---|
| `vitest`, `@vitest/coverage-v8` | critique | **devDependencies** |
| `vite` | haute | **devDependencies** |
| `postcss`, `js-yaml`, `nanoid`, `browserslist`, `brace-expansion` | haute | **transitives** |
| `react`, `react-dom` (`^18.2.0`) | — | **dependencies** · **non affectés** |

**Aucune dépendance d'exécution du front n'est touchée** : le risque porte sur l'environnement
de build et de test, pas sur l'artifact servi aux utilisateurs. `npm audit fix` est disponible
mais modifie `package-lock.json` — à faire sur une branche dédiée, validée par les 1 747 tests
Vitest, pas en passant.

---

## 8. API — contrat solide, documentation perfectible

| Mesure | Valeur |
|---|---|
| Routes figées au contrat (`docs/api/contract.snapshot.json`) | **667** |
| Répartition | GET 299 · POST 242 · PATCH 60 · DELETE 42 · PUT 24 |
| `export_api_contract --check` | **conforme** |
| Collisions d'`operationId` | **0** (corrigées le 2026-09-21, 39 → 0) |
| Avertissements `drf_spectacular.W002` | **420** (mesuré sur la stderr de `manage.py spectacular`) |

Les 420 avertissements « unable to guess serializer » concernent des `APIView` sans
`serializer_class` : ces endpoints apparaissent **sans schéma de requête ni de réponse** dans
la documentation OpenAPI (`/api/docs/`). Le contrat figé n'est pas cassé — il enregistre déjà
ces réponses comme non spécifiées — mais un consommateur d'API ne peut pas savoir ce que ces
endpoints renvoient.

Les corriger exige d'annoter les vues, ce qui **modifie les `responses` du contrat figé** et
donc impose de régénérer le snapshot via `export_api_contract`. C'est une décision de
gouvernance (P00-08), pas une correction automatique : d'où son classement en P2.

---

## 9. Dette de taille de fichiers

**Backend** — les 5 plus gros fichiers Python (hors migrations) :

| Fichier | Lignes |
|---|---|
| `formations/api_views.py` | **5 044** |
| `exports/views.py` | 3 455 |
| `presences/views.py` | 3 368 |
| `statistiques/views.py` | 2 084 |
| `dashboard/views_legacy.py` | 1 951 |

**Frontend** — 9 fichiers sources > 800 lignes (cible du garde-fou G.1 : **0**), décompte hors
fichiers `.test.` :

`Statistiques.jsx` 2 419 · `ModuleDetail.jsx` 1 944 · `FormationDetail.jsx` 1 825 ·
`menu/ecrans.js` 1 779 · `menu/arborescence.js` 1 578 · `DashboardEngineView.jsx` 1 054 ·
`ParticipantDetailModal.jsx` 1 012 · `Dashboard.jsx` 822 · `Modules.jsx` 811.

`Statistiques.jsx` a été réduit de **5 498 à 2 419 lignes** le 2026-09-21 (13 modules extraits
sous `pages/statistiques/`), mais **le compteur G.1 n'a pas bougé** : sur ces 9 fichiers, 6 sont
un seul composant massif — les faire passer sous le seuil impose de découper des composants
porteurs d'état, pas de déplacer des utilitaires.

---

## 10. Chaîne de déploiement — état maillon par maillon

Chaîne documentée : `backend-injs` → `Tobi-nw/injs-app` → Docker Hub → VPS →
`https://injs.badge-qr-code.pro/`.

| Maillon | État mesuré | Preuve |
|---|---|---|
| 1 — sync de l'arbre | 🟢 **sain** | harnais `--self-test` : **53 PASS / 0 FAIL** ; `SYNC_DRY_RUN` sécurisé par défaut |
| 1 — workflows | 🟢 **valides** | les **5 workflows** du dépôt s'analysent sans erreur YAML |
| 1 — diagnostic admin prod | 🟢 **réparé** | `fix-production-admin.yml` échouait à l'analyse YAML ; le diagnostic est devenu `manage.py diagnostic_admin` (12 tests) |
| 2 — build & push images | 🔴 **hors de portée** | `Tobi-nw/injs-app` renvoie 404 avec le compte du bac à sable (privé) |
| 3 — déploiement VPS | 🔴 **hors de portée** | VPS non joignable, Docker absent du bac à sable |
| 4 — service | 🔴 **non vérifiable** | TLS sortant filtré |
| Transverse — CI | 🔴 **à l'arrêt** | facturation GitHub (§5) |

**Deux décisions d'exploitant restent ouvertes** (déjà documentées, toujours d'actualité) :

1. **URL de l'API** — `frontend/nginx.conf` ne proxifie **pas** `/api` (fallback SPA seul), donc
   `VITE_API_URL` doit être absolue. `injs.badge-qr-code.pro` et `api.badge-qr-code.pro` ne
   résolvent pas vers le même serveur : la valeur est à trancher, puis à figer au **build**.
2. **Noms d'images** — ce dépôt construit `jckouassi/injs-be` / `jckouassi/injs-fe`, alors que
   la documentation annonce `ophirdesire/qrcode-badge` / `ophirdesire/qr-badge-frontend`. À
   confirmer sur le dépôt cible, qui construit ses propres images ; le VPS doit épingler le bon
   couple dépôt/tag.

---

## 11. Recommandations priorisées

| Priorité | Action | Effort | Bénéfice |
|---|---|---|---|
| **P0** | Régler la **facturation GitHub**, relancer la CI, obtenir 4 jobs verts | faible (hors code) | Débloque toute la chaîne de déploiement |
| **P0** | **Django 5.1.4 → 5.1.15 puis 5.2 LTS** | moyen | Sort d'un cadre **sans correctifs de sécurité depuis 9,5 mois** ; support jusqu'en avril 2028 |
| **P1** | Poser **`SYNC_EXCLUDE_PATHS=workspace`** avant le premier push réel, puis statuer sur `workspace/` (26 Mo) | faible | Évite de pousser 46 % de code dupliqué dans le dépôt de production |
| **P1** | Trancher l'**URL de l'API** et les **noms d'images**, puis poser les secrets (`INJS_APP_SYNC_TOKEN`, `DOCKERHUB_*`, `VPS_*`) | faible (décisions) | Rend le déploiement exécutable et non ambigu |
| **P2** | `npm audit fix` sur une branche dédiée, validée par les 1 747 tests Vitest | faible | Solde 15 vulnérabilités d'outillage de build/test |
| **P2** | Retirer de Git les **21 Mo de `.dylib`** (`qr_badge_mobile/app_review/_pydeps/`) | faible | Allège le dépôt de 37 % |
| **P2** | Annoter les **420 endpoints** sans schéma + régénérer le snapshot d'API | **élevé** | Documentation OpenAPI exploitable par les consommateurs |
| **P3** | Découper les **9 fichiers front > 800 lignes** (composants porteurs d'état) | élevé | Atteint la cible G.1 = 0 |
| **P3** | Ajouter des tests à **`referentiel_injs`**, seule app sans test | faible | Couvre la dernière zone non testée |
| **P3** | Réduire `formations/api_views.py` (5 044 lignes) | élevé | Maintenabilité du plus gros fichier backend |

---

## 12. Ce qui n'a pas pu être vérifié depuis le bac à sable

Par honnêteté sur la portée de cet audit :

- **`Tobi-nw/injs-app`** : 404 avec le compte disponible — dépôt privé. Ses workflows, ses
  secrets et ses noms d'images n'ont pas pu être lus.
- **Le VPS et `https://injs.badge-qr-code.pro/`** : non joignables (TLS sortant filtré). Aucun
  contrôle de service (§6.4 du document de déploiement) n'a été fait.
- **Docker** : absent du bac à sable. Aucun build d'image ni `docker compose config` n'a pu
  être exécuté ; la conformité des Dockerfile n'est donc pas démontrée par l'exécution.
- **Flutter** : absent. `flutter analyze` (feu 3) non passé — à faire sur un poste équipé.
- **PostgreSQL** : absent. Les tests ont tourné sur **SQLite de secours** ; les comportements
  spécifiques PostgreSQL (déclencheurs, types) restent à revalider en recette.
- **Audit de vulnérabilités Python** : aucun outil installé ; je n'ai pas ajouté de dépendance
  au projet pour ce seul audit. Le constat de fin de support Django (§4) est indépendant de
  cet outillage et reste établi.

---

## 13. Reproduction des mesures

```bash
# Structure et versions
bash arena/probe.sh

# Tests et garde-fous
cd backend && source .venv/bin/activate
python manage.py test --settings=arena.settings_sandbox --parallel 1      # 1 714 OK
python manage.py makemigrations --check --dry-run --settings=arena.settings_sandbox
python manage.py check_repo_hygiene --settings=arena.settings_sandbox
python manage.py export_api_contract --check --settings=arena.settings_sandbox
cd ../frontend && npm run test -- --run                                   # 1 747 OK

# Sécurité de déploiement
DEBUG=False SECRET_KEY=<clé 50+ caractères> \
  DJANGO_ALLOWED_HOSTS=injs.badge-qr-code.pro \
  CSRF_TRUSTED_ORIGINS=https://injs.badge-qr-code.pro \
  CORS_ALLOWED_ORIGINS=https://injs.badge-qr-code.pro \
  python manage.py check --deploy --settings=config.settings               # 1 problème

# Chaîne de déploiement
bash scripts/sync-injs-app.sh --self-test                                  # 53 PASS
gh run list -R JCKOUASSI/backend-injs -L 3                                 # CI à l'arrêt

# Poids et doublons
git ls-files -z workspace | du -ch --files0-from=- | tail -1               # 26 Mo
git ls-files | grep -c '\.dylib$'                                          # 36
bash arena/feux-verts.sh audit-2026-09-21                                  # GATE PASSÉE
```
