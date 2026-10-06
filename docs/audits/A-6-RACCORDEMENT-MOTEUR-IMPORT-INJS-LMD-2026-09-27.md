# A-6 — RACCORDEMENT SÉCURISÉ DU MOTEUR D'IMPORT

| Champ | Valeur |
|---|---|
| **Lot** | **A-6** — Raccordement du moteur au référentiel métier |
| **Date** | 2026-09-27 |
| **Mode** | **DÉVELOPPEMENT CONTRÔLÉ — AUCUN IMPORT RÉEL** |
| **HEAD** | `a54f473aef0d78747cc743b9b3e217c8b9f1c251` (inchangé) |
| **Décision** | **`A6_RACCORDEMENT_PRET`** |

---

## 1 — Architecture existante : ce qui a été réutilisé

| Module | Lot | Réutilisé tel quel ? |
|---|---|---|
| `pedagogie_validateur.py` | A-5.4 | ✅ **Intégralement** — grille A→K, ECTS, codes, sources |
| `import_referentiel_pedagogique.py` | A-5.4 | ✅ Étendu (`--plan`, `--rapport-plan`) |
| `import_maquette.py` | préexistant | ✅ ** inchangé** — reste le seul chemin d'écriture |
| `import_referentiel_injs_lmd.py` | A-4.x | ✅ inchangé — référentiel structurel |

> **Aucun troisième importer n'a été créé.** A-6 ajoute un **module de résolution** qui
> produit un verdict ; l'écriture reste à `import_maquette`, intacte.

---

## 2 — Architecture du pipeline

```
SOURCE → VALIDATION → RÉSOLUTION → PLAN → SIMULATION
```

| Étape | Module | Écriture |
|---|---|---|
| Normalisation + grille A→K | `pedagogie_validateur.py` | non |
| Résolution référentiels | `pedagogie_raccordement.py` (A-6) | **non — lecture seule** |
| Plan + verdict | `ImportPlan` / `ActionPlan` | **non — simulation** |
| Application | `import_maquette.py` | **jamais appelé en A-6** |

---

## 3 — Modèles réellement raccordables

`scolarite.AnneeAcademique` → `formations.RefFormation` → `scolarite.Parcours` →
`scolarite.Niveau` → `scolarite.Semestre` → `scolarite.Maquette` → `scolarite.UE` →
`scolarite.ECUE` → `scolarite.AffectationPedagogique` → `edts.AffectationCreneau` →
`formations.RefSalle` / `formations.Formateur` → `presences.Pointage`.

**Règle L1/L2/L5 vérifiée** : `AffectationCreneau.affectation_pedagogique` **existe déjà**
(migration `edts/0003`, colonne `affectation_pedagogique_id`). Le chemin
AffectationPedagogique → Séance est **opérationnel**, et A-6 n'a créé aucune association.

> Deux modèles du mandat n'existent pas : il n'y a pas de `Seance` (la séance **est** un
> `AffectationCreneau`) ni de `Presence` (la présence **est** un `Pointage`). Documenté, non contourné.

---

## 4 — Modèles manquants / gaps réels

| Gap | Impact | Traitement |
|---|---|---|
| `scolarite_maquette` = **0 ligne** | Aucun UE/ECUE rattachable → `PRETE_A_IMPORTER` inatteignable | **Documenté** |
| `scolarite_parcours` = 0 | Pas de filtre de parcours | Résolution sans parcours |
| AND / LOI / ECJP / GER : cycle unique | Résolution `CONFLICT` → blocage | **Documenté** |
| Codes `RefFormation` vides | Résolution par intitulé normalisé, pas par code | Documenté |

> **Aucune migration créée ni appliquée.** Aucun gap n'a été contourné.

---

## 5 — Tests

| Suite | Lot | Résultat |
|---|---|---|
| `test_moteur_import_pedagogique` | A-5.4 | **47/47** (aucune régression) |
| `test_raccordement_import` | A-6 | **27/27** |
| **Total** | | **74/74 OK** |

Points de contrôle : non-écriture DB, rejet du staging, idempotence logique, hash source,
traçabilité, Master ES non arbitré.

---

## 6 — Résultat staging A-5.3

| Fichier | Lignes | Importables | Rejetées |
|---|---|---|---|
| `referentiel-pedagogique-staging.csv` | 80 | **0** | 80 |
| `ue-staging.csv` | 26 | **0** | 26 |
| `ecue-staging.csv` | 34 | **0** | 34 |
| **Total** | **140** | **0** | **140** |

943 anomalies bloquantes. Le staging reste **entièrement refusé**, comme exigé.

---

## 7 — Données synthétiques

| Mesure | Valeur |
|---|---|
| Cas simulés | **10** |
| Éligibles au plan (grille A→K franchie) | 7 |
| `PRETE_A_IMPORTER` | **0** (aucune maquette en base) |
| **Écritures réelles** | **0** |

Le rejet des 7 lignes éligibles porte la cause racine : *« ECUE sans UE certaine — cause : aucune
maquette existante »*. Le pipeline est donc correct ; c'est l'absence de maquette qui bloque.

---

## 8 — DB

**DB AVANT = DB APRÈS** sur les 16 compteurs : `Maquette` 0 · `UE` 0 · `ECUE` 0 · `Parcours` 0 ·
`AffectationPedagogique` 0 · `AffectationCreneau` 0 · `RefFormation` 16 · `Niveau` 5 ·
`Semestre` 10 · `RefSalle` 58 · `Formateur` 3 · `Pointage` 34.

Migrations inchangées : `scolarite` 15 (`0015`), `edts` 4 (`0004`), `formations` 95 (`0095`),
`presences` 29 (`0029`).

---

## 9 — Git

`HEAD` = `a54f473aef0d78747cc743b9b3e217c8b9f1c251` — **inchangé**.
Branche `main`. `git diff --check` rc=0. **0 fichier suivi modifié.** Aucun commit, push, deploy.

---

## 10 — Décision

> # `A6_RACCORDEMENT_PRET`
>
> Le chemin technique **source → validation → résolution → plan → simulation** est
> opérationnel et vérifié, y compris jusqu'à `AffectationPedagogique`.
>
> **Aucun import réel n'a été effectué ni autorisé.** Le moteur A-5.4 a été réutilisé sans
> duplication, les 47 tests A-5.4 sont conservés, et le staging A-5.3 reste entièrement refusé.
>
> Le blocage n'est plus technique mais **documentaire** : sans maquette officielle signée
> (UE, ECUE, coefficients, volumes), `PRETE_A_IMPORTER` ne peut pas être atteint.
