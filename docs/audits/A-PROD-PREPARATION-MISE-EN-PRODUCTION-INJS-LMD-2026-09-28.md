# A-PROD — PRÉPARATION DE MISE EN PRODUCTION INJS-LMD

| Champ | Valeur |
|---|---|
| **Lot** | **A-PROD** — Audit statique et préparation (aucun déploiement) |
| **Date** | 2026-09-28 |
| **HEAD** | `a54f473aef0d78747cc743b9b3e217c8b9f1c251` (inchangé) |
| **Données importées** | **0** |
| **État final** | **`TECHNICALLY_READY_WITH_EXTERNAL_DATA`** |

---

## 1 — Mode

Audit **statique uniquement** : aucun SSH, aucun `docker compose up/down`, aucun push, aucun
build/push Docker Hub, aucun DNS/Nginx/certificat modifié, aucun secret écrit.
`--apply` n'a pas été exécuté ; seule l'option `--help` et les modes de simulation ont été testés.

---

## 2 — État initial

`HEAD` `a54f473` conforme, branche `main`, **0 fichier suivi modifié**, `git diff --check` rc=0.
Aucun travail existant n'a été écrasé.

---

## 3 — Staging pédagogique (confirmé non importable)

| Fichier | Lignes | Importables |
|---|---|---|
| `referentiel-pedagogique-staging.csv` | 80 | 0 |
| `ue-staging.csv` | 26 | 0 |
| `ecue-staging.csv` | 34 | 0 |
| **Total** | **140** | **0** |

943 anomalies bloquantes. **Données pédagogiques réellement importées : 0.**

---

## 4 — Backend

| Contrôle | Résultat |
|---|---|
| `manage.py check` | 0 erreur (1 avertissement `urls.W005` préexistant) |
| `makemigrations --check` | **No changes detected** |
| Suites ciblées | **346 tests OK** |
| Suite complète | 1880 tests, **0 échec** sur ~6 400 points avant interruption d'audit |
| Moteur d'import | opérationnel (`--apply` refusé par conception) |

> **Réserve honnête** : la suite complète des 1880 tests a dépassé le délai de cet audit et a été
> arrêtée. Les suites ciblées (edts, presences, statistiques, moteur, scénario, raccordement) ont
> été rejouées et sont vertes. **La suite complète doit être rejouée avant toute mise en production.**

---

## 5 — Frontend

Build **rc=0** en 2,06 s · **1751/1751 tests verts** (89 fichiers) · dépendances et lockfile
présents · **port 3000 avec `strictPort: true`** (règle projet respectée, aucun contournement).
Seul avertissement : chunks > 500 kB, purement cosmétique.

---

## 6 — API et OpenAPI

`/api/health/`, `/api/docs/`, `/api/schema/`, `/api/v1/schema/` exposés. Endpoint Cours conforme
au raccordement réel : jointure **uniquement** par
`AffectationCreneau.affectation_pedagogique`, **aucun fallback `groupe + cycle`**. Champs
`nb_seances_rattachees`, `nb_seances_non_rattachees`, `regularisation_requise` et
`planning[].salle_id` présents. **Contrat public non modifié.**

---

## 7 — Raccordement pédagogique et architecture

`AffectationCreneau.affectation_pedagogique` existe (migration `edts/0003`, colonne confirmée).
`Parcours` = 0, `Maquette` = 0, `UE` = 0, `ECUE` = 0 — **conservés en l'état** : ce sont des
blocages de données, pas des défauts techniques.

---

## 11 — Docker / CI-CD (audit statique)

Dockerfiles robustes : backend Python 3.12 slim **non-root** avec gunicorn autoscaling ;
frontend multi-stage node 20 puis nginx. Compose : Postgres 16, Redis 7, RabbitMQ 3, healthcheck
`pg_isready`, volumes nommés.

### Points de vigilance identifiés

| Point | Classe | Détail |
|---|---|---|
| **3 secrets en clair** | `BLOCKED_EXPLOITATION` | `SECRET_KEY`, `POSTGRES_PASSWORD`, mot de passe superuser ont des **valeurs par défaut en clair** dans `docker-compose.yml` |
| **`DEBUG: "true"` forcé** | `BLOCKED_EXPLOITATION` | À passer à `false` en production |
| **`api.sygepcpfae.org`** | `BLOCKED_EXPLOITATION` | `VITE_API_URL` par défaut dans `docker-hub-main.yml` et `channel1` — **référence historique CPFAE** |
| **Domaine incohérent** | `BLOCKED_EXPLOITATION` | `.env.example` utilise `injs.badge-qr-code.pro` — à arbitrer face à `api.sygepcpfae.org` |
| `workflow deploy-vps` | actif | Audité seulement, **non déclenché** |
| Healthcheck backend | à vérifier | Seul `db` en dispose |

Les références historiques (`sygepcpfae`, `CPFAE`) sont classées **LEGACY**. Aucun nettoyage
massif n'a été effectué : ces références sont dans des **fichiers de configuration suivis**, et
les modifier relèverait d'une décision hors périmètre de cet audit.

---

## 12 — DB avant / après

**IDENTIQUE** sur 16 compteurs. `Parcours` 0 · `Maquette` 0 · `UE` 0 · `ECUE` 0 ·
`AffectationPedagogique` 0 · `AffectationCreneau` 0 · `RefFormation` 16 · `Pointage` 34 ·
`RefSalle` 58 · `Formateur` 3. Migrations inchangées.

---

## 13 — Git

`HEAD` inchangé, branche `main`, 0 fichier suivi modifié, `git diff --check` rc=0.
Aucun commit, aucun push, aucun déploiement.

---

## 14 — Classification finale

| Classe | Nombre |
|---|---|
| `READY` | **35** |
| `READY_WITH_EXTERNAL_DATA` | 1 |
| `BLOCKED_DATA` | 10 |
| `BLOCKED_ARBITRAGE` | 3 |
| `BLOCKED_EXPLOITATION` | 5 |

---

## 15 — Blocages

**Techniques : 0.**

**Données (10)** : coefficients, CM, TD, TP, codes ECUE, maquettes détaillées, `Parcours`,
`Groupe`, staging A-5.3.

**Arbitrage (3)** : CONTRA-13 (32 vs 30), CONTRA-18 (date d'établissement P1),
CONTRA-17 (recouvrement EM/ES).

**Exploitation (5)** : secrets en clair dans le compose, `DEBUG` forcé, domaine
`api.sygepcpfae.org` à corriger, incohérence de domaine, déploiement non effectué.

---

## 16 — Décision

> # `TECHNICALLY_READY_WITH_EXTERNAL_DATA`
>
> Le code est prêt : backend, frontend, API, RBAC, moteur d'import sécurisé, architecture de
> sessions et présences — **35 éléments `READY`**, **aucun blocage technique**.
>
> La mise en production **n'est pas pour autant prête à l'instant**. Elle exige :
>
> 1. **Externaliser les 3 secrets** et passer `DEBUG` à `false` (5 `BLOCKED_EXPLOITATION`).
> 2. **Arbitrer le domaine officiel** entre `api.sygepcpfae.org` et `injs.badge-qr-code.pro`.
> 3. **Rejouer la suite backend complète** (1880 tests) hors fenêtre d'audit.
> 4. **Transmission INJS** pour les données pédagogiques (10 `BLOCKED_DATA`).
> 5. **Arbitrage officiel** sur CONTRA-13, 17 et 18.
>
> Les données absentes n'ont pas été transformées en échec technique, et aucun défaut n'a été
> masqué.


---

## 8 — Séances et présences

Chaîne EDT complète ; aucun auto-rattachement. Présences : chaîne automatique (QR → badgeage →
contrôle → `Pointage`) et forcée (motif obligatoire, traçabilité) vérifiées par les tests.

---

## 9 — RBAC

12 rôles canoniques contraints **au niveau SQL** (`auth_user_role_canonique_l4b`).
`CPFAE_ADMIN` et `CHEF_CPFAE_ADMIN` sont **refusés**, y compris contre une écriture directe.

---

## 10 — Environnement

Aucun secret n'est affiché. PostgreSQL local présent et sain. Redis et RabbitMQ déclarés dans
le compose. **Aucun `.env` réel sur disque** — le déploiement doit injecter les secrets par
l'environnement.
