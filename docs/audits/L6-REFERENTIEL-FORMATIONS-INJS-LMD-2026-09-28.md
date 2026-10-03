# L6 — Référentiel officiel INJS-LMD

| | |
|---|---|
| Date | 2026-09-28 |
| Tâche | L6 |
| Dépôt | `/Users/jckouassi/projets/injs/backend-injs` |
| Branche | `main` |
| HEAD avant / après | `a54f473aef0d78747cc743b9b3e217c8b9f1c251` (inchangé — §26) |
| Source métier | `docs/audits/A-4.5-DOSSIER-VALIDATION-METIER-INJS-LMD-2026-09-27.md` §2 |
| Sauvegarde | `~/Backups/INJS-LMD/database/injs_lmd_current_2026-09-28_04-23-40.dump` |

> L6 ne constitue pas une validation institutionnelle. Le commanditaire INJS
> n'a pas encore visé les 8 filières. L6 met en œuvre la source documentaire
> existante et rend la traçabilité explicite.

## 1. Diagnostic — d'où venait l'affichage CPFAE

```
formations_formation (8 lignes)      ← 3 CPFAE + 5 DEBUG FORM, ref_formation_id = NULL
      ↓
GET /api/formations/referentiels/    ← formations_reelles = Formation.objects.order_by('formation')
      ↓
hooks/useReferentiels.js             ← cache React Query 10 min
      ↓
pages/Modules.jsx
      ↓
menu/arborescence.js  « Formations LMD » → /formations → <Navigate to="/modules" />
```

Le menu **Formations LMD** redirigeait vers l'écran d'exploitation des modules,
alimenté par `formations_formation` — dont la totalité du contenu est CPFAE ou
DEBUG. La fuite **était** la route du menu, pas un endpoint mal filtré.

Côté `RefFormation`, 16 lignes coexistaient sans distinction de nature : 12
cycles INJS et 4 cycles « professorat / maître » (corpus O6, A-4.3ter §5.3) qui
ne figurent pas parmi les 8 filières validées (A-4.5 §2).

## 2. Modèle — aucun nouveau modèle (L6 §4)

Migration `formations/0096_l6_referentiel_injs.py` : **3 `AddField`, 0 suppression,
0 renommage, 0 migration de données**.

| Champ | Rôle |
|---|---|
| `RefFormation.perimetre` | `INJS` / `LEGACY` / `NON_DETERMINE` (défaut : non déterminé) |
| `RefFormation.filiere_code` | code stable de filière `F01`…`F08` (A-4.5 §2) |
| `RefFormation.source` | référence de la source ayant attesté la ligne |

Le défaut `NON_DETERMINE` est délibéré : aucune ligne n'est présumée INJS.

## 3. Source de vérité applicative

`backend/formations/referentiel_injs_l6.py` porte la nomenclature et :

* `formations_injs()` — `perimetre = INJS` **et** exclusion des marqueurs
  `CPFAE` / `Sygepcpfae` / `DEBUG` (défense en profondeur : une ligne mal
  qualifiée en base ne peut pas fuir) ;
* `signaler_ecarts()` — contrôle d'intégrité (8 filières, 0 étranger, compte legacy).

## 4. Les 8 filières INJS (A-4.5 §2)

| Code | Sigle | Filière | École | Diplômes attestés |
|---|---|---|---|---|
| F01 | EM | Éducation et Motricité | ENSEPS | Licence, Master |
| F02 | APA | Activités Physiques Adaptées | ENSEPS | Licence, Master |

## 5. API

`GET /api/formations/lmd/formations/` — nouveau, **additif** :

```
FORMATIONS INJS → PARCOURS → NIVEAUX (+SEMESTRES) → MAQUETTES → UE → ECUE
```

Réponse : `source`, `credits_par_semestre` (30), `credits_par_niveau` (60),
`nb_filieres_attendues` / `nb_filieres_chargees`, `filieres[]`, `integrite`.

Le filtrage est **serveur** (L6 §11) : le frontend n'applique aucun filtre métier.

## 6. Import

`python manage.py qualifier_referentiel_injs_l6 [--dry-run]`

SOURCE MÉTIER → NORMALISATION → VALIDATION (8/8) → IMPORT → CONTRÔLE.

Idempotent vérifié : 1er passage `QUALIFIE=12 | LEGACY=4`, 2e passage
`QUALIFIE=0 | DEJA=16`. Non destructif : aucune suppression. Ne crée ni
parcours, ni UE, ni ECUE, ni code officiel, ni crédits ventilés (L6 §12/§13).

## 7. Données legacy (L6 §9)

Rien n'est supprimé. `formations_formation` conserve ses 8 lignes CPFAE/DEBUG et
les 4 cycles « professorat » sont conservés en base, marqués `LEGACY`. Ils sont
simplement **hors du périmètre fonctionnel INJS** : ils n'apparaissent ni dans
l'API L6, ni dans l'écran Formations LMD.

Les anciens liens d'exploitation pointent vers `/formations/operational`
(session d'exploitation : modules, notes, présences) — distinct de
`/formations` (référentiel INJS). Aucune fonctionnalité L1→L5 n'est retirée.

## 8. Tests

`backend/formations/tests/test_referentiel_injs_l6.py` — 23 tests, A→F :

* **A** — API limitée aux cycles `perimetre=INJS` ; 401 sans authentification ;
* **B** — aucun CPFAE/DEBUG ; une ligne marquée INJS mais étrangère est rejetée ;
* **C** — 8/8 filières, libellés issus de la source, 30/60 ECTS, S1→S10 ;
* **D** — rattachement aux parcours, parcours legacy non exposé ;
* **E** — rattachement aux maquettes → UE → ECUE, maquette legacy non exposée,
  aucune UE artificielle créée ;
* **F** — chaîne `AffectationPedagogique → AffectationCreneau → Séance → Présence`
  pilotée par la FK, contrat API Cours intact, données legacy non supprimées ;
* plus : idempotence, `--dry-run` non écrit, contrôle d'intégrité sans écart.

| F03 | ES | Entraînement Sportif | ENSEPS | Licence, Master |
| F04 | MS | Management du Sport | ENSEPS | Licence, Master |
| F05 | AND | Andragogie | ENSEP | Licence (à confirmer) |
| F06 | LOI | Loisir | ENSEP | Licence (à confirmer) |
| F07 | ECJP | Entrepreneuriat Jeunesse et Conduite de Projets | ENSEP | Licence (à confirmer) |
| F08 | GER | Gérontologie | ENSEP | Licence (à confirmer) |

Ces 8 filières sont portées par **12 cycles `RefFormation`** : F01→F04 sont
documentés « Licence + Master » (A-4.5 §3, D8) et donnent donc 2 cycles chacun ;
F05→F08 ne sont pas documentés avec un découpage licence/master et donnent
**une seule** coquille. Le compte « 8 » est donc porté par `filiere_code`, pas
par le nombre de lignes — c'est le seul comptage qui ne déforme pas la source.
