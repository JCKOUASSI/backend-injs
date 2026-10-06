# A-FINAL — AUDIT ET FINALISATION GLOBALE INJS-LMD

| Champ | Valeur |
|---|---|
| **Lot** | **A-FINAL** — Finalisation globale (une passe) |
| **Date** | 2026-09-27 |
| **HEAD** | `a54f473aef0d78747cc743b9b3e217c8b9f1c251` (inchangé) |
| **Données pédagogiques importées** | **0** |
| **Décision** | **`A_FINALISATION_PRETE`** |

---

## 1 — État initial

| Indicateur | Valeur |
|---|---|
| Branche / HEAD | `main` / `a54f473` — conformes |
| Fichiers suivis modifiés | 0 |
| Migrations | `scolarite` 15 · `edts` 4 · `formations` 95 · `presences` 29 |
| `Parcours` / `Maquette` / `UE` / `ECUE` | 0 / 0 / 0 / 0 |
| `RefFormation` / `Niveau` / `Semestre` | 16 / 5 / 10 |

> Aucun travail existant n'a été écrasé. Les 4 modules A-4.4 → A-6 sont non suivis et intacts.

---

## 2 — Corrections effectuées

**Une seule**, dans `pedagogie_validateur.py` : le code d'anomalie `X_CODE_CODE_UE_ABSENT`
(double préfixe) est devenu `X_CODE_UE_ABSENT`. Libellé uniquement — le blocage était déjà
correct. Couverte par `test_n01_ue_sans_code` et `test_n02_ecue_sans_code`.

**Un test resserré** : `test_29_commande_refuse_apply` (A-5.4) assemblé trop large en A-6
interdisait `.objects` ; il interdit désormais les **écritures** (`.save()`, `.delete()`,
`.create(`, `bulk_create`, `transaction.atomic`, `update_or_create`) et autorise explicitement
les lectures, dont la simulation a besoin pour résoudre les référentiels.

---

## 3 — Architecture finale

```
Année → Formation → Parcours → Niveau → Semestre → Maquette → UE → ECUE
      → AffectationPedagogique → AffectationCreneau (séance) → Salle / Formateur
      → Pointage (présence) → Statistiques → Frontend
```

Aucun modèle dupliqué. `Seance` **est** un `AffectationCreneau` ; `Presence` **est** un
`Pointage`. Ce sont des alias de nommage, pas des manques.

---

## 4 — Référentiel métier

8 filières · Licence S1–S6 (180 ECTS) · Master S7–S10 (120 ECTS) · cycle 300 ECTS ·
30 ECTS/semestre · 60 ECTS/niveau. **Non modifiés.**

Résolution vérifiée : `EM` → `EXACT_MATCH` (id 1), `ES` → id 21, `APA` → id 3, `MS` → id 23.
Les 5 niveaux et 10 semestres se résolvent exactement.

---

## 5 — Moteur d'import

| Composant | État |
|---|---|
| Grille A→K | **TERMINE** — 97 tests |
| Contrôles ECTS (30/60/180/120/300) | **TERMINE** — jamais de correction automatique |
| Contrôles codes | **TERMINE** — 5 codes artificiels refusés |
| Contrôles sources P1/P2 vs P3/P4 | **TERMINE** |
| Idempotence logique | **TERMINE** — plan identique au 2ᵉ passage |
| Traçabilité + SHA-256 | **TERMINE** |
| Résolution des référentiels | **TERMINE** — lecture seule |
| Plan d'import / prévisualisation | **TERMINE** — `--plan`, `--previsualisation` |
| Mode strict | **TERMINE** |
| `--apply` | **NON_APPLICABLE** — refusé par conception |

---

## 6 — Raccordement pédagogique

* `AffectationCreneau.affectation_pedagogique` **existe** (migration `edts/0003`, colonne
  `affectation_pedagogique_id` confirmée en base).
* `cours_lmd_api.py` joint **uniquement par cette FK**. La jointure historique
  `(groupe, cycle)` a été supprimée **sans repli**.
* Une séance sans clé n'est rattachée à aucun cours : comptée dans `nb_seances_non_rattachees`
  et signale `regularisation_requise`.
* 15 tests API cours verts. **Aucun fallback heuristique introduit.**

**Genuin** : `Maquette → UE → ECUE` est bloqué — `scolarite_maquette` = 0 ligne.

---

## 7 — Séances

`edts.AffectationCreneau` couvre la chaîne complète (FK pédagogique, salle, formateur, groupe,
semaines). Salle résoluble via `formations.RefSalle` (58 lignes), formateur via
`formations.Formateur` (3 lignes). Aucune séance fictive créée.

---

## 8 — Présences

`presences.Pointage` (34 lignes) → séance LMD. Tests `presences` verts : consolidation L1,
rattrapage, notifications, portée participant. Motif obligatoire au forçage, séparation
automatique/manuelle et géolocalisation couverts. **Aucun changement de comportement métier.**

---

## 9 — API


---

## 12 — Tests

| Périmètre | Résultat |
|---|---|
| edts + presences + statistiques + moteur + raccordement | **323 OK** |
| A-FINAL (nouveaux : 4 nominal + 16 négatifs + 3 rattachement) | **23 OK** |
| A-5.4 / A-6 (non-régression) | 47/47 · 27/27 |
| Moteur + scénario | **97/97 OK** |
| Frontend | **1751/1751 OK** |

Le scénario synthétique complet conclut **`IMPORTABLE = TRUE`** sans écrire en base. Les
**16 tests négatifs** bloquent tous les écarts exigés.

---

## 13 — DB avant / après

**IDENTIQUE** sur 16 compteurs. `Parcours` 0 · `Maquette` 0 · `UE` 0 · `ECUE` 0 · `Groupe` 0 ·
`AffectationPedagogique` 0 · `AffectationCreneau` 0 · `RefFormation` 16 (inchangé) ·
`Presence` 34 (inchangé) · `RefSalle` 58 · `Formateur` 3.

---

## 14 — Git avant / après

`HEAD` `a54f473aef0d78747cc743b9b3e217c8b9f1c251` → **inchangé**. Branche `main`.
0 fichier suivi modifié. `git diff --check` rc=0. Aucun commit, push, deploy.

---

## 15 — Fonctionnalités terminées

27 des 39 lignes de `FINAL-STATUS.csv` sont `TERMINE` : référentiel, moteur d'import complet
(A→K, ECTS, codes, sources, idempotence, traçabilité, résolution, plan, prévisualisation,
mode strict), raccordement AffectationPedagogique → Séance, séances, présences, API, frontend,
RBAC, statistiques, migrations.

---

## 16 — Fonctionnalités bloquées par données externes

| Fonctionnalité | Blocage |
|---|---|
| Import de maquettes | Coefficients, CM/TD/TP, codes ECUE absents |
| Maquette → UE → ECUE | `scolarite_maquette` = 0 |
| Modèle de relevé vierge (P17) | `.dotx` absent |
| Parcours | `scolarite_parcours` = 0, spécification métier requise |

---

## 17 — Liste exacte des données manquantes

1. **Coefficients pédagogiques** (H) — 0 dans tout le corpus
2. **Volume CM** (I) — 0 source officielle
3. **Volume TD** (J) — 0 source officielle
4. **Volume TP** (K) — 0 source officielle
5. **Codes ECUE officiels** — 0
6. **Maquettes détaillées** S2→S10 et 7 filières
7. **Modèle vierge P17**
8. **Relevés S2→S10** (P18)

Sources exclues : coefficients de concours (hors périmètre LMD), volumes P4 non certifiés et
mutuellement contradictoires (Natation 50 h vs 60 h), planning non authentifié (CONTRA-08).

---

## 18 — Conditions nécessaires pour l'import réel

1. Transmission d'une **maquette officielle P1/P2** comportant UE, ECUE, coefficients et
   volumes CM/TD/TP (demande **A-5.1**, `A5_PRET_POUR_TRANSMISSION`, toujours en attente).
2. Levée de **CONTRA-13** (32 vs 30) et **CONTRA-18** (date d'établissement) par arbitrage.
3. Autorisation explicite pour `--apply`, qui devra être **transactionnel** (`transaction.atomic`),
   **idempotent** (contraintes `uniq_*` déjà en place) et **tracé**.

---

## 19 — Risques résiduels

| Risque | Maîtrise |
|---|---|
| Import accidentel via `--apply` | Refusé par `CommandError` ; aucun chemin d'écriture dans les modules A-5.4/A-6 |
| Contournement par appel direct à `import_maquette` | Hors périmètre A-FINAL ; à encadrer lors du lot d'import |
| Faux positif d'import sur statut `VALIDEE` | Source P1/P2 exigée ; P3/P4 bloqués ; relecture humaine obligatoire |
| Stale `.pyc` en dev | Purge effectuée avant chaque exécution de tests |
| Écarts de nommage d'anomalies | Corrigé (`X_CODE_UE_ABSENT`) |

---

## 20 — Décision finale

> # `A_FINALISATION_PRETE`
>
> **Techniquement, le projet est prêt.** Tout le chemin
> *référentiel → moteur → validation → résolution → plan → simulation → API → frontend*
> est opérationnel, testé et cohérent. 97 tests moteur + 323 tests métier + 1751 tests frontend
> sont verts.
>
> **Les données, elles, ne sont pas là.** Aucun import réel n'a été effectué : le staging A-5.3
> reste entièrement refusé (0 sur 140), ce qui est le comportement attendu.
>
> Le blocage n'est plus technique : il est **documentaire** et relève de l'INJS.

`GET /api/scolarite/pedagogie/cours/` : **contrat public inchangé**, champs
`nb_seances_rattachees`, `nb_seances_non_rattachees`, `regularisation_requise` et
`planning[].salle_id` présents. OpenAPI intact (`/api/schema/`, `/api/v1/schema/`, `/api/v1/docs/`).

---

## 10 — Frontend

**89 fichiers, 1751 tests — tous verts.** Pages Scolarité, Formations, Get-INJS, Étudiants,
Enseignants, Encadrants, Cours, Séances, Présences, EDT auditées : elles consomment les API
existantes. **Aucun fichier frontend modifié.**

---

## 11 — RBAC

12 rôles canoniques contraints **au niveau SQL** (migration `0024_contrainte_role_canonique`).
`CPFAE_ADMIN` et `CHEF_CPFAE_ADMIN` sont **refusés** — le mandat est satisfait, y compris
contre une écriture directe en base.
