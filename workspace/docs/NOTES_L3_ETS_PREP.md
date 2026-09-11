# Préparation lot L3 — Remontée des notes vers les ECUE et crédits ECTS

> **Périmètre** : document de **conception/preparation** rédigé dans le cadre du
> Prompt 12 (lot L1 « Sécurisation des notes »). L'implémentation des points
> de décision ci-dessous est planifiée avec le **Prompt 13**.
>
> Règle de conception absolue : **ne pas dupliquer les règles de calcul des
> notes/moyennes/validations dans React ou Flutter**. Le backend reste la seule
> source de vérité ; les écrans consomment des API en lecture qui exposent les
> résultats calculés.

---

## 1. État constaté après le lot L1

- `formations.NoteModule` : note / colonne / participant + workflow de
  validation **BROUILLON → SOUMISE → VALIDEE** (`statut_validation`,
  `verrouillee`, `validation_par`, `validation_le`).
- `formations.CorrectionNoteModule` : historique **append-only** des
  corrections (motif obligatoire), exposé par `GET …/notes/historique/`.
- `formations.Module.ref_module` → `formations.RefModule` (nomenclature unifiée).
- `scolarite.ECUE` : `credits` (ECTS), `coefficient`, et `ref_module` →
  `formations.RefModule` (« Module opérationnel correspondant »).
- `scolarite.InscriptionPedagogique` : ligne d'enseignement réellement suivi
  (ECUE + semestre + groupe), rattachée à `InscriptionAdministrative`
  (étudiant, année, formation, parcours, niveau).

## 2. Cible : chaîne de remontée

```
NoteModule (formation.Module.ref_module)
    │  ← passerelle référentielle : mêmes RefModule
    ▼
scolarite.ECUE (écue.ref_module == module.ref_module)
    │  ← inscription pédagogique : inscriptions_pedagogiques (ecue)
    ▼
scolarite.InscriptionPedagogique
    │  (inscription.etudiant == étudiant LMD)
    ▼
scolarite.InscriptionAdministrative / DossierEtudiant
    ▼
Validation par crédits ECTS
```

Deux passerelles doivent être stabilisées (décisions au Prompt 13) :

1. **Passerelle référentielle** : `formations.Module.ref_module` ↔
   `ECUE.ref_module` (même `RefModule`). Elle est déjà en place sur les
   modèles ; il reste à définir le comportement quand plusieurs modules
   opérationnels pointent vers le même `RefModule` (moyenne ? choix du module
   de référence par période/cohorte ?) et quand la note est saisie à une
   sous-colonne (CC1, CC2…) : agrégation vers l'ECUE par coefficients de
   colonne à définir.

2. **Passerelle personne** : identifier comment `formations.Participant`
   (porteur des notes) est rattaché au `DossierEtudiant` LMD (matricule
   unique, UUID de synchro, ou FK dédiée à ajouter par migration additive).
   C'est le prérequis pour relier `NoteModule.participant` à
   `InscriptionPedagogique.inscription.etudiant`.

## 3. Flux cible (tous calculs backend)

1. `NoteModule` **VALIDEE** et verrouillée (lot L1) → devient éligible.
2. Service backend (nouveau, ex. `scolarite/validation_ects_services.py`) :
   - agrège les notes par colonne (coefficients de `NoteModuleColonne`),
   - map le module → ECUE via `RefModule`,
   - applique seuils (`ParametresEvaluation` de la formation, déjà central),
   - calcule la **validation de l'ECUE** et les **crédits ECTS acquis**
     (pondération `coefficient` de l'ECUE, règles d'UE à définir au P13).
3. Résultat persisté (ex. `ValidationECUE` append-only) avec lien vers
   `InscriptionPedagogique` + référence à l'historique de validation des notes.
4. API **lecture seule** : tableaux de bord (RSU/relevés) consomment ces
   résultats ; aucune règle recomputée côté affichage.

## 4. Réutilisation du lot L1 (zéro duplication)

- Le workflow **BROUILLON/SOUMISE/VALIDEE** et le **verrouillage** deviennent
  le garde-fou d'entrée de la remontée : une note non validée n'entre pas dans
  le calcul ECTS.
- Les **corrections auditées** (`CorrectionNoteModule` + `JournalScolarite`)
  laissent une trace unique qui alimente aussi le « pourquoi » d'une
  revalidation partielle éventuelle d'une ECUE.

## 5. Points de décision à trancher au Prompt 13

- [ ] Périmètre de la synchronisation `Module.ref_module ↔ ECUE.ref_module`
      (1:1 / 1:n, période de référence).
- [ ] Passerelle `Participant` ↔ `DossierEtudiant` (matricule/FK additive).
- [ ] Agrégation multi-colonnes (CC1/CC2/examen) vers une note d'ECUE unique +
      coefficients.
- [ ] Règle de validation d'ECUE (seuil /20, note éliminatoire éventuelle) et
      report des crédits ECTS.
- [ ] Règle de validation d'UE (somme des ECUE, compensation) — réutilisation
      ou non de `suiviEvaluation.DecisionPedagogique`.
- [ ] Nouveaux modèles append-only (`ValidationECUE`, `ValidationUE`) vs
      extension de `MoyenneModule`/`DecisionPedagogique`.
- [ ] Reciblage de `formations.NoteModuleSynthese` (mention calculée côté
      opérationnel) vers la mention LMD calculée côté ECTS.

## 6. Non-régression garantie par le lot L1

- Migration `formations 0091` **additive** : aucun champ existant modifié,
  aucune donnée supprimée.
- Comportement de saisie historique conservé : les notes existantes restent en
  `BROUILLON` (verrouillage uniquement si l'utilisateur lance `valider`).
- Noeud de contrôle : `module_notes_list_api` expose `statut_validation` /
  `verrouillee` sans casser le contrat des écrans (champs ajoutés uniquement).