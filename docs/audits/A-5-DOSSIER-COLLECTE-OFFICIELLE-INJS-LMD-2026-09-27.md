# RAPPORT A-5 — DOSSIER DE COLLECTE OFFICIELLE ET VALIDATION DES DONNÉES PÉDAGOGIQUES INJS-LMD

| Champ | Valeur |
|---|---|
| Lot | **A-5** — Dossier de collecte officielle INJS-LMD |
| Date | 2026-09-27 |
| Branche / commit | `main` / `a54f473aef0d78747cc743b9b3e217c8b9f1c251` |
| Nature | **Audit documentaire et préparation — aucun import** |
| Base de données | `injs_lmd_current` — **0 écriture** |
| Décision d'import | **NO-GO maintenue** (inchangée) |
| Décision A-5 | **`A5_PRET_POUR_COLLECTE`** |
| Artefacts | 8 CSV + 3 modèles + 1 README dans `workspace/26092026/a5-collecte/` |

---

## 1. OBJET

Construire le **DOSSIER DE COLLECTE OFFICIELLE INJS-LMD 2026**, c'est-à-dire l'ensemble des
dispositifs permettant de **demander, réceptionner, contrôler, tracer et valider** les
documents pédagogiques actuellement absents du référentiel INJS-LMD.

**A-5 ne fabrique pas de maquettes.** Il produit :

1. la liste exacte des données manquantes ;
2. les documents officiels à demander ;
3. les critères d'acceptation ;
4. une matrice de collecte ;
5. une matrice de traçabilité des preuves ;
6. un modèle de demande officielle ;
7. un modèle de fiche de réception ;
8. un protocole de contrôle ;
9. un format d'import futur ;
10. une décision claire sur les conditions de passage de `NO-GO` à `GO`.

---

## 2. CONTEXTE

Les audits **A-4.1 à A-4.12** ont exploré de manière exhaustive le corpus documentaire local.
Le lot **A-4.12** a établi un **plafond documentaire** : les données disponibles ne permettent
pas de poursuivre honnêtement la reconstruction des maquettes.

**A-5 ne contourne pas cette conclusion.** A-5 la transforme en **dossier professionnel de
collecte des preuves officielles**, prêt à être transmis à l'INJS et à recevoir les documents
manquants.

| A-4.1 → A-4.12 | A-5 |
|---|---|
| Audit **négatif** : ce qui manque | Dossier **positif** : ce qu'il faut demander |
| Extraction depuis des sources existantes | Réception de sources officielles |
| Production de constats | Production de **procédures** |
| `NO-GO` comme fin | `A5_PRET_POUR_COLLECTE` comme fin |

---

## 3. REFERENTIEL VALIDE

### 3.1 Périmètre — 8 filières

| École | Filière | Code |
|---|---|---|
| **ENSEPS** | Éducation et Motricité | EM |
| **ENSEPS** | Management du Sport | MS |
| **ENSEPS** | Entraînement Sportif | ES |
| **ENSEPS** | Activités Physiques Adaptées | APA |
| **ENSEP** | Andragogie | — |
| **ENSEP** | Loisir | — |
| **ENSEP** | Entrepreneuriat, Jeunesse et Conduite de Projets | ECJP |
| **ENSEP** | Gérontologie | — |

### 3.2 Cycle LMD

| Paramètre | Valeur | Source |
|---|---|---|
| Licence | S1 → S6 (3 ans) | cadre LMD, validé A-4.5 |
| Master | S7 → S10 (2 ans supplémentaires) | cadre LMD, validé |
| Total | 5 ans | A-4.10 / A-4.12 |
| Crédits | **30 ECTS / semestre** | cadre LMD |
| Niveau | **60 ECTS / niveau** | cadre LMD + S-16 (« Crédits Prog : 180 ») |
| Licence | 180 ECTS | S-16 |
| Master | 120 ECTS | cadre LMD |
| Cycle complet | 300 ECTS | cadre LMD |

### 3.3 État en base (inchangé)

`Niveau` = 5 · `Semestre` = 10 · `Parcours` = 0 · `Maquette` = 0 · `UE` = 0 · `ECUE` = 0

---

## 4. RESULTATS A-4.12 REPRIS COMME ETAT INITIAL

| Indicateur | Valeur A-4.12 | Repris par A-5 |
|---|---|---|
| Corpus inventorié | 426 fichiers | ✔ |
| Corpus exploitable | 403 documents | ✔ |
| Sources `P1` | **1** (S-16) | ✔ |
| Copies bit-identiques de S-16 | 6 | ✔ |
| Cellules totales | 80 (8 filières × 10 semestres) | ✔ |
| Cellules complètes | **0** | ✔ |
| Cellules partielles | **4** (EM/S1, ES/S1, ES/S7, APA/S5) | ✔ |
| Cellules absentes | **76** | ✔ |
| Cellules importables | **0** | ✔ |
| UE confirmées | 9 | ✔ |
| ECUE confirmés | 25 | ✔ |
| Codes officiellement observés | 9 | ✔ |
| Coefficients | **0** | ✔ |
| CM / TD / TP | **0** | ✔ |
| `CONTRA-A411-01` | **`RESOLUE_A`** | ✔ |
| Base de données | inchangée | ✔ |
| Commit / push / déploiement | aucun | ✔ |

### 4.1 Répartition des sources par niveau de preuve

| Niveau | Effectif | Utilisable pour l'import ? |
|---|---|---|
| **P1** — source officielle directe | **1** | OUI (bloquée par H et I) |
| **P2** — source institutionnelle | **0** | — |
| **P3** — source secondaire | **7** | NON |
| **P4** — source tertiaire | **1** | NON |
| **P5** — hypothèse / artefact | 394 | NON |

> **1 document `P1` sur 403.** C'est le cœur du problème : l'essentiel de l'information
> pédagogique n'existe pas localement sous une forme opposable.

---

## 5. PLAFOND DOCUMENTAIRE

### 5.1 Ce qui a été épuisé

| Axe | Résultat |
|---|---|
| Corpus local complet | 426 documents inventoriés |
| S-16 (table 0 + hors table 0) | exhaustivement extrait |
| Relevés / bulletins | **1 seul** bulletin exploitable |
| Codes `[A-Z]{3}8[0-9]{3}` | **9 codes**, tous issus de S-16 |
| Recherche web ciblée | index seul, contenu inaccessible |
| Recherche par filière | **1 filière** documentée sur 8 |
| Recherche par niveau | **L1 seul** |
| Recherche par semestre | S1, S5, S7 ; **7 semestres vides** |

### 5.2 Ce qui bloque de façon structurelle

| Donnée | Cellules | Pièce qui la lèverait |
|---|---|---|
| Coefficient / M3C | **80 / 80** | **P13** |
| Volume CM / TD / TP | **80 / 80** | **P14** |

Ces deux dimensions sont absentes de **tous** les documents, y compris de la source `P1`.

### 5.3 Conséquence

> **Aucune nouvelle recherche locale n'est rationnelle.** La seule voie est la demande
> formelle des pièces officielles.

---

## 6. LISTE DES PIECES MANQUANTES

Artefact : `liste_documents_manquants.csv` — **18 lignes × 10 colonnes**.

> Les 18 entrées sont **reprises mot pour mot** de `a412-documents-a-obtenir.csv`
> (A-4.12, §15), conformément au mandat §10.

| ID | Rang | Pièce | Priorité |
|---|---|---|---|
| P01 | 1 | Maquettes officielles EM — Licence S1-S6 | **P0** |
| P02 | 2 | Maquettes officielles EM — Master S7-S10 | **P0** |
| P03 | 3 | Maquettes officielles ES — Licence S1-S6 | **P0** |
| P04 | 4 | Maquettes officielles ES — Master S7-S10 | **P0** |
| P05 | 5 | Maquettes officielles MS — Licence S1-S6 | **P0** |
| P06 | 6 | Maquettes officielles MS — Master S7-S10 | **P0** |
| P07 | 7 | Maquettes officielles APA — Licence S1-S6 | **P0** |
| P08 | 8 | Maquettes officielles APA — Master S7-S10 | **P0** |
| P09 | 9 | Maquettes officielles Andragogie | **P0** |
| P10 | 10 | Maquettes officielles Loisir | **P0** |
| P11 | 11 | Maquettes officielles ECJP | **P0** |
| P12 | 12 | Maquettes officielles Gerontologie | **P0** |
| P13 | 13 | M3C / coefficients par UE et ECUE | **P0** |
| P14 | 14 | Volumes horaires CM / TD / TP (avec TPE, stage, total) | **P0** |
| P15 | 15 | Codes officiels UE et ECUE | **P1** |
| P16 | 16 | Repartition officielle des CECT (ventilation UE et ECUE) | **P0** |
| P17 | 17 | Modele de releve de notes vierge (template officiel) | **P1** |
| P18 | 18 | Exemplaires de releves couvrant S2 (validation du format de code) | **P2** |

### 6.1 Statut documentaire

> **Aucune de ces 18 pièces n'est prouvée comme existante.** La colonne `existe_t_on` porte
> `INCONNU` pour les pièces 1 à 16 et 18, et `A VERIFIER` pour la pièce 17. Il s'agit d'une
> **demande**, jamais d'un constat d'absence avérée.

---

## 7. MATRICE DE COLLECTE

Artefact : `matrice_collecte_officielle.csv` — **98 lignes × 21 colonnes**.

| Niveau de granularité | Lignes | Contenu |
|---|---|---|
| **Pièce** | 18 | une ligne par document demandé (P01 → P18) |
| **Cellule** | 80 | une ligne par `Formation × Niveau × Semestre` |

### 7.1 Colonnes

`ID` · `Priorite` · `Formation` · `Niveau` · `Semestre` · `Type_Document` · `Donnee_Attendue` ·
`Description` · `Source_Attendue` · `Statut` · `Date_Demande` · `Date_Reception` · `Format` ·
`Nom_Fichier` · `SHA256` · `Page` · `Preuve` · `Niveau_Confiance` · `Controle` ·
`Bloquant_Import` · `Observation`

### 7.2 Document unique, correspondances semester par semestre

Conformément au mandat §4, lorsqu'un document regroupe plusieurs semestres il est enregistré
comme **document unique** (une ligne `P01`…`P12`), mais les **correspondances semestre par
semestre** sont établies dans les **80 lignes `CELL-<FILIERE>-<SEMESTRE>`**, chacune portant
les `ID_PIECE` à l'origine de la donnée.

### 7.3 Valeurs de `Statut`

`A_DEMANDER` → `DEMANDE` → `RECU` → `EN_CONTROLE` → `VALIDE` | `REJETE` | `INCOMPLET` |
`NON_DISPONIBLE`

**État actuel : les 98 lignes sont à `A_DEMANDER`.**

---

## 8. PRIORISATION P0 / P1 / P2

| Priorité | Définition | Pièces | Nombre |
|---|---|---|---|
| **P0** | **BLOQUANTE** — nécessaire pour rendre une cellule importable | P01 → P14, P16 | **15** |
| **P1** | **IMPORTANTE** — validation administrative et traçabilité | P15, P17 | **2** |
| **P2** | **COMPLÉMENTAIRE** — utile mais non bloquante | P18 | **1** |

### 8.1 Pièces les plus critiques

| Pièce | Why critique |
|---|---|
| **P13** — M3C / coefficients | seule pièce qui peut lever le critère **H**, en échec sur **80/80 cellules** |
| **P14** — Volumes CM/TD/TP | seule pièce qui peut lever le critère **I**, en échec sur **80/80 cellules** |
| **P16** — Répartition CECT | lève le critère **G** pour l'APA S5 (14/30, `CONTRA-12`) |
| **P01/P02** — EM | l'unique filière disposant déjà d'une preuve `P1` |

### 8.2 Justification du classement de P15 (codes) en `P1`

Les codes ne figurent dans **aucun** des 10 critères A → J : leur absence n'interdit donc pas,
à elle seule, le statut `IMPORTABLE`. Ils restent néanmoins indispensables à la **codification
officielle** du référentiel, d'où `P1` (important) et non `P0` (bloquant).

---

## 9. CRITERES D'AUTHENTICITE

| Niveau | Définition | Exemples | Importable ? |
|---|---|---|---|
| **P1** | **Source officielle directe** | document signé · document cacheté · document émis par l'INJS · note de service · maquette administrative · règlement officiel · document institutionnel identifiable | **OUI** |
| **P2** | **Source institutionnelle** | document institutionnel non signé, copie institutionnelle identifiable | **OUI** (à justifier) |
| **P3** | **Source secondaire** | page web, extraction, transcription, document de travail, audit | **NON** |
| **P4** | **Source tertiaire** | document externe, source non institutionnelle | **NON** |

> **Un `P3` ou `P4` n'est jamais l'équivalent automatique d'une maquette `P1`.**
> Les 7 sources `P3` du dossier actuel (S-13, S-14, S-17, S-18a/b/c, S-19) restent non
> importables.

### 9.1 Cas particulier du relevé de notes

Un code observé dans un **relevé de notes** (cas de S-16) doit être **distingué** d'un code
provenant directement d'une **maquette officielle**. S-16 est un relevé : ses 9 codes sont
observés, mais la **règle de construction** et la **nomenclature complète** restent inconnues
→ pièce **P15**.

---

## 10. CRITERES D'ACCEPTATION

Un document reçu sera accepté pour paramétrage si et seulement si :

| # | Critère |
|---|---|
| 1 | il est émis par l'INJS ou par une instance academicement compétente |
| 2 | il porte une identification de l'émetteur, une date et une période de validité |
| 3 | il mentionne explicitement la formation, le niveau et le semestre |
| 4 | il est lisible intégralement (pas de scan tronqué) |
| 5 | il permet de reconstituer les relations UE → ECUE sans interprétation |
| 6 | il fournit les CECT |
| 7 | il fournit les coefficients (P13) |
| 8 | il fournit les volumes horaires (P14) |
| 9 | il ne présente aucune contradiction avec une autre pièce officielle reçue |

**À défaut** : `REJETE` ou `INCOMPLET`, et le document ne peut pas servir au paramétrage.

---

## 11. CRITERES D'IMPORTABILITE

Artefact : `critere_importabilite.csv` — **80 lignes × 17 colonnes**.

| | Critère | Exigence |
|---|---|---|
| **A** | Formation identifiée | obligatoire |
| **B** | Niveau identifié | obligatoire |
| **C** | Semestre identifié | obligatoire |
| **D** | UE officiellement documentées | obligatoire |
| **E** | ECUE officiellement documentées | obligatoire |
| **F** | Relation UE → ECUE certaine | obligatoire |
| **G** | CECT documentés | obligatoire |
| **H** | Coefficients documentés | obligatoire |
| **I** | CM / TD / TP documentés lorsque requis | obligatoire |
| **J** | Aucune contradiction documentaire non résolue | obligatoire |

> **Sinon : `NON_IMPORTABLE` ou `PARTIELLE`, mais jamais `IMPORTABLE`.**

### 11.1 Application au dossier actuel

| Cellule | A | B | C | D | E | F | G | H | I | J | Statut | Pièces requises |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **EM / S1** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | PASS | `PARTIEL` | P01, P13, P14 |
| **ES / S1** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | PASS | `PARTIEL` | P03, P13, P14, P15 |
| **ES / S7** | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | PASS | **FAIL** | **FAIL** | PASS | `NON_IMPORTABLE` | P04, P13, P14, P15 |
| **APA / S5** | PASS | PASS | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** | `NON_IMPORTABLE` | P07, P13, P14, P16 |
| **76 autres** | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | `NON_IMPORTABLE` | TOUTES |

> ### **0 cellule satisfait A → J à 100 %** — l'état est **inchangé** par rapport à A-4.12.

---

## 12. MATRICE DES PREUVES

Artefact : `matrice_preuves.csv` — **11 lignes × 22 colonnes**.

`ID_PIECE` · `Fichier` · `SHA256` · `Source` · `Nature_Source` · `Formation` · `Niveau` ·
`Semestre` · `UE` · `ECUE` · `Code` · `CECT` · `Coefficient` · `CM` · `TD` · `TP` · `Page` ·
`Extrait_Preuve` · `Statut` · `Validateur` · `Date_Validation` · `Observation`

### 12.1 État de la matrice

| Statut | Lignes | Détail |
|---|---|---|
| `EN_CONTROLE` | 2 | S-16 (P1) — EM/S1, 2 entrées (structure + codes) |
| `REJETE_POUR_IMPORT` | 6 | S-13, S-14, S-17, S-18a, S-19, P-11 — tous `P3`/`P4` |
| `NON_DISPONIBLE` | 3 | P13, P14, P16 — **non reçues** |

### 12.2 Ce que la matrice montre

| Champ | Valeur consolidée |
|---|---|
| Preuves `P1` exploitables | **1** (S-16, EM/S1) |
| Preuves `P3` exploitables pour l'import | **0** |
| UE documentées par une source `P1` | **9** |
| ECUE documentés par une source `P1` | **13** |
| Codes documentés par une source `P1` | **9** |
| CECT documentés par une source `P1` | **30** (EM/S1) |
| **Coefficients** | **`A_OBTENIR` (P13)** |
| **CM / TD / TP** | **`A_OBTENIR` (P14)** |

### 12.3 Règle appliquée

`Coefficient`, `CM`, `TD`, `TP` portent **`NON_DOCUMENTE`** dans toutes les lignes.
**Aucune absence n'est convertie en `0`.** La colonne `Observation` rappelle systématiquement
que l'information provient d'une source non officielle.

---

## 13. PROTOCOLE DE RECEPTION

Modèle : `FICHE_RECEPTION_DOCUMENT.md` (10 sections).

| # | Étape | Livrable |
|---|---|---|
| 1 | Déposer le fichier dans `a5-collecte/received/` | fichier déposé, non renommé |
| 2 | Calculer le **SHA-256** | empreinte 64 hex |
| 3 | Renseigner la fiche de réception | fiche `FICHE_RECEPTION_<PIECE>_<date>.md` |
| 4 | Identifier émetteur, date, période, formation, niveau, semestre | champs §1 et §2 |
| 5 | Recenser le contenu obtenu | checklist §5 (18 éléments) |
| 6 | Qualifier le niveau de confiance | `P1` / `P2` / `P3` / `P4` |
| 7 | Lancer le protocole de contrôle (§14) | 20 contrôles |
| 8 | Décider : `VALIDE` / `REJETE` / `INCOMPLET` / `NON_DISPONIBLE` | §8 de la fiche |
| 9 | Identifier les cellules débloquées | liste `Formation × Niveau × Semestre` |
| 10 | Mettre à jour `matrice_collecte_officielle.csv` et `matrice_preuves.csv` | lignes mises à jour |

### 13.1 Règles de la réception

* **ne rien renommer** un document reçu ;
* **ne rien écraser** ;
* un document **illisible** est classé `INCOMPLET`, jamais `VALIDE` ;
* un document sans **identification de l'émetteur** est classé `REJETE` ;
* une copie **bit-identique** à un document déjà reçu est consignée et **non comptabilisée** comme
  nouvelle pièce.

---

## 14. PROTOCOLE DE CONTROLE

Les **20 étapes** à appliquer à chaque document reçu :

| # | Étape | Résultat attendu |
|---|---|---|
| 1 | Calculer le SHA-256 | empreinte unique |
| 2 | Détecter les doublons | aucun ou hash déjà connu |
| 3 | Vérifier le contenu | lisible, non tronqué |
| 4 | Vérifier les pages | nombre de pages annoncé / réel |
| 5 | Identifier l'émetteur | organisme + service |
| 6 | Identifier la date | date de document |
| 7 | Identifier la période | année académique de validité |
| 8 | Identifier la formation | 1 des 8 filières |
| 9 | Identifier le niveau | L1, L2, L3, M1, M2 |
| 10 | Identifier le semestre | S1 → S10 |
| 11 | Extraire les UE | code, intitulé, CECT, statut |
| 12 | Extraire les ECUE | code, intitulé, UE parent, CECT, statut |
| 13 | Extraire les codes | UE, ECUE, enseignements |
| 14 | Extraire les CECT | UE, ECUE |
| 15 | Extraire les coefficients | UE, ECUE, type d'évaluation |
| 16 | Extraire CM / TD / TP | par ECUE |
| 17 | Vérifier les relations UE → ECUE | chaque ECUE rattachée à une UE existante |
| 18 | Vérifier les totaux | Σ semestre = 30 |
| 19 | Identifier les contradictions | avec les autres pièces reçues |
| 20 | Attribuer le niveau de confiance | `P1` / `P2` / `P3` / `P4` |

### 14.1 Règles de non-invention au contrôle

> * un champ absent reste **`NON_DOCUMENTE`**, jamais `0` ;
> * un champ absent ne doit **jamais** être rempli par déduction (CECT recopiée de l'UE vers
>   l'ECUE, coefficient déduit des crédits, volume déduit d'un autre semestre) ;
> * une valeur lue dans une source `P3` reste `P3` même si elle est cohérente.

---

## 15. CONTROLE DES DOUBLONS

Artefact : `registre_doublons.csv` — **8 lignes × 10 colonnes**.

| ID | Fichier | Classe | Action |
|---|---|---|---|
| DUP-01 → DUP-06 | `MODELE DE RELEVE DE NOTES.docx` | `COPIE_IDENTIQUE` | conservation — **ne constitue pas une nouvelle preuve** |
| DUP-07 | `MODELE_DE_RELEVE_DE_NOTES.docx.txt` | `DERIVE_TEXTE` | conservation — dérivé de S-16 |
| DUP-08 | fichier à nom différent, hash inconnu | `A_VERIFIER` | à qualifier à la réception |

### 15.1 Leçon du dossier

> Les 6 copies de S-16 ne constituent **qu'une seule source**. Le comptage de doublons a été
> appliqué de manière systématique à A-4.11 : c'est ce qui a permis de conclure qu'un seul
> bulletin existe réellement dans tout le corpus.

**Règle pour la suite** : une pièce reçue dont le SHA-256 est identique à une pièce déjà
enregistrée est **consignée** mais **ne débloque aucune cellule supplémentaire**.

---

## 16. CONTROLE SHA-256

Artefact : `controle_integrite_sha256.csv` — **13 lignes × 10 colonnes**.

### 16.1 Méthode

```bash
shasum -a 256 "fichier"
```

ou

```bash
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" fichier
```

### 16.2 Règles

| Règle | Description |
|---|---|
| **R1** | Tout document reçu doit avoir une empreinte SHA-256 calculée et consignée |
| **R2** | Une empreinte déjà connue dans `registre_doublons.csv` ⇒ pièce **dupliquée** |
| **R3** | Une pièce dupliquée est consignée mais **ne débloque aucune cellule** |
| **R4** | Toute modification d'une pièce reçue impose un **nouveau** SHA-256 et une **nouvelle** fiche |
| **R5** | L'empreinte est la **clé d'identité** de la pièce : jamais de renommage de fichier |

### 16.3 Contrôle effectué sur le dossier actuel

| Contrôle | Résultat |
|---|---|
| Copies de S-16 vérifiées | **6 / 6** |
| SHA-256 conforme à `da64afadda888cff…bbe78` | **6 / 6 — CONFORME** |
| Pièces officielles reçues | **0** — aucune empreinte à contrôler |

---

## 17. CONTROLE DE COHERENCE LMD

### 17.1 Règles de contrôle

| Niveau | Règle | Seuil |
|---|---|---|
| **Semestre** | Σ CECT du semestre | **= 30** |
| **Année** | Σ CECT de l'année | = 60 |
| **Licence** | Σ CECT des 6 semestres de Licence | **= 180** |
| **Master** | Σ CECT des 4 semestres de Master | **= 120** |
| **Cycle** | Licence + Master | **= 300** |

> ### Ces contrôles ne s'appliquent **que** lorsque les données officielles nécessaires sont
> effectivement disponibles.
> Tant qu'un semestre n'est pas documenté, son total reste **`NON_DOCUMENTE`** et **non** forcé
> à 30.

### 17.2 Application à l'état actuel

| Périmètre | Contrôle | Résultat |
|---|---|---|
| EM / S1 | Σ = 30 | **30 ✔ CONFORME** (source `P1`) |
| EM / S1..S6 | Σ = 180 | **NON CALCULABLE** — 5 semestres sans donnée |
| ES / S1 | Σ = 30 | 30 (source `P3` — non opposable) |
| ES / S1..S6 | Σ = 180 | **NON CALCULABLE** |
| APA / S5 | Σ = 30 | **14 ✗ NON CONFORME** (`CONTRA-12`, 16 CECT manquants) |
| Tous les autres | — | **NON DOCUMENTÉ** |

### 17.3 Point d'attention sur APA S5

Les 16 CECT manquants correspondent à 3 UE mentionnées « inclus UE » **sans valeur chiffrée**.
**Aucune répartition n'a été déduite.** Cette anomalie est levée uniquement par la pièce
**P16** (et/ou **P07**).

---

## 18. MODELE DE DEMANDE OFFICIELLE

Fichier : `DEMANDE_DOCUMENTS_OFFICIELS_INJS_LMD.md` (style administratif professionnel).

| Section | Contenu |
|---|---|
| En-tête | objet, référence dossier, date, demandeur, contact |
| §1 | destinataires (DG INJS, scolarité, ENSEPS, ENSEP, commission pédagogique) |
| §2 | objet et contexte (audit 426 / 403, absence de paramétrage) |
| §3 | motif de la demande |
| §4 | périmètre concerné (8 filières, cycle LMD) |
| §5 | **documents demandés** — 18 pièces |
| §6 | contenu attendu par pièce (UE, ECUE, coefficients, CM/TD/TP, M3C, CECT, codes) |
| §7 | critères d'acceptation |
| §8 | modalités de transmission (format, nommage, accusé de réception) |
| §9 | formule de clôture et bloc signature |

### 18.1 Formulation du motif (§19 du mandat)

Le modèle indique explicitement que les documents sont nécessaires pour :

> **« assurer la fidélité du paramétrage du référentiel pédagogique INJS-LMD et éviter toute
> reconstruction ou interprétation non validée. »**

### 18.2 Points de vigilance intégrés au modèle

* demander explicitement les **autres volumes officiellement définis** (TPE, stage, projet) ;
* demander d'**indiquer explicitement** les volumes « non définis » plutôt que de laisser des
  cellules vides ;
* demander de **distinguer** les codes issus d'un relevé des codes issus d'une maquette ;
* demander la **règle de construction des codes** ;
* prévoir la gestion d'un **document unique regroupant plusieurs semestres**.

---

## 19. ETAT DES PIECES RECUES

> ### **Aucune pièce officielle n'a été reçue à ce jour.**

| Statut | Nombre | Détail |
|---|---|---|
| `RECU` | **0** | — |
| `EN_CONTROLE` | **0** | — |
| `VALIDE` | **0** | — |
| `REJETE` | **0** | — |
| `INCOMPLET` | **0** | — |
| `NON_DISPONIBLE` | **0** | — |

Le dossier `a5-collecte/received/` est **vide et prêt à recevoir les documents**.

### 19.1 Sources antérieures (non des pièces reçues)

Les 14 sources du `registre_sources.csv` sont des documents **trouvés localement** avant A-5, et
non des pièces transmises par l'INJS dans le cadre de cette démarche. Aucune n'est `P1` hormis
S-16, qui est un **relevé de notes** et non une maquette.

---

## 20. ETAT DES PIECES MANQUANTES

| Priorité | Pièces | Statut | Cellules bloquées |
|---|---|---|---|
| **P0** | **15** | `A_DEMANDER` | **80 / 80** |
| **P1** | 2 | `A_DEMANDER` | 0 (traçabilité) |
| **P2** | 1 | `A_DEMANDER` | 0 (confort) |
| **Total** | **18** | `A_DEMANDER` | **80 / 80** |

### 20.1 Historique du statut

| Date | Événement | Pièces touchées |
|---|---|---|
| 2026-09-27 | Création du dossier de collecte | 18 pièces créées en `A_DEMANDER` |
| — | Demande à émettre | — |
| — | Réception attendue | — |

**La date de demande sera renseignée dans `matrice_collecte_officielle.csv` (colonne
`Date_Demande`) au moment de l'envoi effectif du modèle.**

---

## 21. CONDITIONS DE PASSAGE A A-6 / IMPORT

### 21.1 Chaîne complète imposée

```text
A-5
 ↓
Réception des documents officiels
 ↓
Contrôle P1/P2
 ↓
Extraction structurée
 ↓
Validation UE/ECUE
 ↓
Validation CECT
 ↓
Validation coefficients
 ↓
Validation CM/TD/TP
 ↓
Contrôle 30 ECTS / semestre
 ↓
Contrôle 180 ECTS Licence
 ↓
Contrôle 120 ECTS Master
 ↓
Contrôle absence de contradiction
 ↓
GO documentaire
 ↓
Import dry-run
 ↓
Validation dry-run
 ↓
Import réel autorisé séparément
```

### 21.2 Conditions à réunir par cellule

| # | Condition | Pièce | Bloquante ? |
|---|---|---|---|
| 1 | Le demandeur a transmis le modèle de demande | — | administrative |
| 2 | L'INJS a accusé réception | — | administrative |
| 3 | La maquette de la filière est reçue | P01 → P12 | **OUI** |
| 4 | Le document est `P1` ou `P2` | — | **OUI** |
| 5 | La M3C / les coefficients sont reçus | P13 | **OUI** (critère H) |
| 6 | Les volumes CM/TD/TP sont reçus | P14 | **OUI** (critère I) |
| 7 | La répartition des CECT est reçue | P16 | **OUI** (critère G) |
| 8 | Le code officiel est reçu | P15 | non bloquant (§8.2) |
| 9 | La fiche de réception est renseignée | — | **OUI** |
| 10 | Le contrôle 20 étapes est passé | — | **OUI** |
| 11 | Aucune contradiction non résolue | — | **OUI** (critère J) |
| 12 | La grille A → J est à 100 % pour la cellule | — | **OUI** |

### 21.3 Séquence minimale réaliste

Pour rendre **une seule cellule** importable, il faut au minimum :

* la maquette de la filière concernée (**P01** à **P12**) ;
* la M3C / les coefficients (**P13**) ;
* les volumes horaires (**P14**).

> **C'est ce trio — maquette + coefficients + volumes — qui définit le seuil minimal d'un `GO`.**

### 21.4 Ce qui reste hors de portée de A-5

| Élément | Nature |
|---|---|
| Existence des 18 pièces | **INCONNUE** — A-5 ne prouve pas leur existence |
| Obtention effective | hors périmètre documentaire |
| Contrôle de contenu | impossible sans pièce |
| Toute écriture en base | **interdite** |

---

## 22. DECISION FINALE A-5

### 22.1 Réponse aux 10 livrables attendus

| # | Livrable | État |
|---|---|---|
| 1 | Liste exacte des données manquantes | ✅ `matrice_collecte_officielle.csv` (98 lignes) |
| 2 | Documents officiels à demander | ✅ `liste_documents_manquants.csv` (18 pièces) |
| 3 | Critères d'acceptation | ✅ §10 + §7 du modèle de demande |
| 4 | Matrice de collecte | ✅ `matrice_collecte_officielle.csv` |
| 5 | Matrice de traçabilité des preuves | ✅ `matrice_preuves.csv` |
| 6 | Modèle de demande officielle | ✅ `DEMANDE_DOCUMENTS_OFFICIELS_INJS_LMD.md` |
| 7 | Modèle de fiche de réception | ✅ `FICHE_RECEPTION_DOCUMENT.md` |
| 8 | Protocole de contrôle | ✅ §14 (20 étapes) |
| 9 | Format d'import futur | ✅ `format_import_futur.csv` (22 champs) |
| 10 | Décision sur les conditions `NO-GO` → `GO` | ✅ §21 |

### 22.2 Décision

| Option | Applicable ? | Motif |
|---|---|---|
| `A5_BLOQUE` | ❌ non | Le registre a été **correctement construit** : 18 pièces, 80 cellules, 8 CSV, 3 modèles, tous validés. |
| `A5_COLLECTE_EN_COURS` | ❌ non | **Aucune pièce n'a été reçue** : la collecte n'a pas commencé. |
| **`A5_PRET_POUR_COLLECTE`** | ✅ **retenu** | Le dossier de collecte est **complet et opérationnel**. |

> # # `A5_PRET_POUR_COLLECTE`
>
> Le dossier A-5 est prêt à être transmis à l'INJS et à recevoir les documents manquants.
>
> **A-5 ne transforme pas le `NO-GO` d'import.** La décision d'import reste **`NO-GO`**, avec
> **0 cellule importable** sur 80. Conformément au mandat §26, la décision A-5 **ne transforme
> jamais automatiquement** A-5 en `GO` d'import.

### 22.3 État du dossier à la clôture

| Indicateur | Valeur |
|---|---|
| Pièces construites | **18** |
| Pièces demandées | **18** |
| Pièces reçues | **0** |
| Pièces validées | **0** |
| Pièces rejetées | **0** |
| Pièces incomplètes | **0** |
| Pièces manquantes | **18** |
| Cellules importables | **0** |
| Cellules partielles | **4** |
| Cellules non importables | **76** |
| Artefacts produits | **8 CSV + 3 modèles + 1 README + 1 dossier `received/`** |
| Écritures en base | **0** |
| Fichiers applicatifs modifiés | **0** |
| Migrations | **0** |
| Commit / push / déploiement | **0** |

### 22.4 Ce que ce lot a produit

Le dossier A-5 ne modifie **aucune** donnée pédagogique. Il produit la **chaîne procédurale**
permettant de sortir du `NO-GO` :

1. un **modèle de demande** prêt à envoyer ;
2. un **protocole de réception** (10 étapes) ;
3. un **protocole de contrôle** (20 étapes) ;
4. une **classification d'authenticité** (`P1`→`P4`) ;
5. une **grille d'importabilité** objective (A → J) ;
6. un **format d'import** cible (22 champs) ;
7. des **registres de traçabilité** (matrices, sources, doublons, empreintes).

### 22.5 Règle de non-invention — rappel final

> Aucun UE, ECUE, code, coefficient, CECT, CM, TD ou TP n'a été inventé, déduit d'une autre
> filière ou déduit d'une note observée. Toute donnée absente porte le statut `ABSENTE`,
> `A_OBTENIR` ou `NON_DOCUMENTE`. **Aucune absence n'a été convertie en `0`.**

---

## 23. ARTEFACTS PRODUITS

| Fichier | Lignes × colonnes |
|---|---|
| `a5-collecte/matrice_collecte_officielle.csv` | 98 × 21 |
| `a5-collecte/matrice_preuves.csv` | 11 × 22 |
| `a5-collecte/liste_documents_manquants.csv` | 18 × 10 |
| `a5-collecte/registre_sources.csv` | 14 × 10 |
| `a5-collecte/registre_doublons.csv` | 8 × 10 |
| `a5-collecte/controle_integrite_sha256.csv` | 13 × 10 |
| `a5-collecte/critere_importabilite.csv` | 80 × 17 |
| `a5-collecte/format_import_futur.csv` | 22 × 8 |
| `a5-collecte/FICHE_RECEPTION_DOCUMENT.md` | modèle 10 sections |
| `a5-collecte/DEMANDE_DOCUMENTS_OFFICIELS_INJS_LMD.md` | modèle 9 sections |
| `a5-collecte/README.md` | mode d'emploi 10 sections |
| `a5-collecte/received/` | dossier vide, prêt à recevoir |
| `docs/audits/A-5-DOSSIER-COLLECTE-OFFICIELLE-INJS-LMD-2026-09-27.md` | le présent rapport |

---

## A-5.1 — Finalisation de la demande officielle

> **Lot documentaire et administratif uniquement.** Aucun import, aucune écriture en base,
> aucune modification de code applicatif.

### A-5.1.1 État initial

| Élément | Valeur au démarrage de A-5.1 |
|---|---|
| Branche | `main` |
| HEAD | `a54f473aef0d78747cc743b9b3e217c8b9f1c251` |
| Décision A-5 | `A5_PRET_POUR_COLLECTE` |
| Décision d'import | `NO-GO` — **inchangée** |
| Pièces listées | 18 (15 `P0`, 2 `P1`, 1 `P2`) |
| Pièces transmises | **0** |
| Pièces reçues | **0** |
| Pièces validées | **0** |
| `received/` | vide |
| Base de données | `injs_lmd_current` — **0 écriture** |

### A-5.1.2 Contrôle des 18 pièces

Source de vérité : `a412-resolution/a412-documents-a-obtenir.csv`.

> ⚠️ **Écart de chemin constaté** : le mandat §4 désigne
> `workspace/26092026/a5-collecte/a412-documents-a-obtenir.csv`. Ce fichier **n'existe pas** dans
> le dossier A-5 : la source de vérité réelle est
> `workspace/26092026/a412-resolution/a412-documents-a-obtenir.csv`. La vérification a été
> conduite sur ce fichier, **sans duplication de source**.

| Contrôle | Résultat |
|---|---|
| Pièces dans la source de vérité | **18** |
| Pièces dans `liste_documents_manquants.csv` | **18** |
| Pièces dans `matrice_collecte_officielle.csv` (niveau pièce) | **18** |
| Pièces dans `registre_suivi_demandes.csv` | **18** |
| Pièces dans la demande détaillée | **18** |
| Identifiants `P01` → `P18` identiques dans les 4 fichiers | **OUI** |
| Répartition des priorités | **15 `P0` · 2 `P1` · 1 `P2`** — conforme |
| Ajout / suppression / invention | **0 / 0 / 0** |

**Divergences d'intitulé détectées et corrigées** — 4 pièces présentaient un intitulé accentué ou
reformulé par rapport à la source. Elles ont été **remises à la forme verbatim** :

| Pièce | Intitulé A-5 (avant) | Intitulé retenu (verbatim) |
|---|---|---|
| P12 | Maquettes officielles **Gérontologie** | `Maquettes officielles Gerontologie` |
| P16 | **Répartition officielle des CECT** (ventilation UE et ECUE) | `Repartition officielle des CECT (ventilation UE et ECUE)` |
| P17 | **Modèle de relevé de notes vierge** (template officiel) | `Modele de releve de notes vierge (template officiel)` |
| P18 | **Exemplaires de relevés** couvrant S2 (validation du format de code) | `Exemplaires de releves couvrant S2 (validation du format de code)` |

> La correction est **strictement documentaire** : elle porte sur des libellés, jamais sur des
> données applicatives. Les 12 autres pièces étaient déjà concordantes.

**Résultat : 18/18 concordantes — 0 ajout, 0 suppression, 0 renommage, 0 invention.**

### A-5.1.3 Documents produits

| Fichier | Nature |
|---|---|
| `DEMANDE_DOCUMENTS_OFFICIELS_INJS_LMD.md` | demande administrative complète — en-tête, §0 principe, objet, contexte, motif, tableau des 18 pièces, contenu attendu, format, année académique, traçabilité, périmètre, clôture |
| `DEMANDE_OFFICIELLE_INJS_LMD_COURTE.md` | version courte ~1 page |
| `DEMANDE_OFFICIELLE_INJS_LMD_DETAILLEE.md` | version détaillée — tableau des 18 pièces + détail par catégorie |
| `MODELE_EMAIL_DEMANDE_DOCUMENTS_INJS_LMD.md` | modèle d'e-mail réutilisable |
| `MODELE_LETTRE_DEMANDE_DOCUMENTS_INJS_LMD.md` | modèle de lettre administrative |
| `registre_suivi_demandes.csv` | 18 lignes × 15 colonnes — toutes à `À COMPLÉTER` / `NON DEMANDE` |
| `registre_relances.csv` | en-tête seul — **aucune relance inventée** |
| `registre_integrite.csv` | 18 lignes × 8 colonnes — toutes `NON RECU` |
| `PROTOCOLE_RECEPTION_DOCUMENTS.md` | chaîne 10 étapes + 20 contrôles + règles de non-invention |
| `received/README.md` | 9 règles de dépôt — dossier `received/` laissé **vide** |
| `README.md` (A-5) | inventaire mis à jour + §9.1 état de la transmission |

### A-5.1.4 Statut de transmission

| Champ | Valeur |
|---|---|
| Pièces à demander | **18** |
| **Pièces effectivement transmises** | **0** |
| **Documents effectivement reçus** | **0** |
| Pièces validées | **0** |
| Pièces rejetées | **0** |
| Statut des 18 pièces dans le registre | `NON DEMANDE` |
| Date de demande | `À COMPLÉTER` |
| Canal | `À COMPLÉTER` |
| Destinataire | `À COMPLÉTER` |
| Référence de transmission | `À COMPLÉTER` |
| Relances | **0** |
| Fichiers dans `received/` | **0** |

> **Documents effectivement reçus : 0**
>
> Aucune date, aucun numéro de courrier, aucun destinataire, aucune adresse électronique, aucun
> nom de responsable, aucune signature et aucune validation INJS n'ont été inventés. Les
> destinataires listés dans la demande sont explicitement marqués **pressentis, non confirmés**.

### A-5.1.5 Corrections documentaires

| Correction | Détail |
|---|---|
| « 9 CSV » → **« 8 CSV »** | 3 occurrences dans le présent rapport (§0, §22.2, §22.3) — le compte réel est 8 |
| Intitulés verbatim | 4 pièces réalignées sur la source de vérité |
| Terminologie | `MANQUANT` remplacé par `NON REÇU` — l'INJS n'a confirmé l'inexistence d'aucune pièce |
| Destinataires | ne sont plus présentés comme établis — colonne « Destinataire retenu » à compléter |
| Convention de nommage | `A5_<ID_PIECE>_…` → `INJS-LMD_<FORMATION>_<NIVEAU>_<SEMESTRE>_<TYPE>_<ANNEE>.<EXT>` |
| Exemple de nommage | explicitement présenté comme **forme uniquement**, sans fichier correspondant |

### A-5.1.6 Règle de non-invention — rappel

> Aucun UE, ECUE, code, coefficient, CECT, CM, TD ou TP n'a été inventé, déduit d'une autre filière
> ou déduit d'une note observée. **Aucune absence n'a été convertie en `0`.** Aucune donnée
> reçue n'a été importée : aucune pièce n'a été reçue.

### A-5.1.7 Décision

> # `A5_PRET_POUR_TRANSMISSION`
>
> Le dossier administratif est **complet, cohérent et directement transmissible** à l'INJS.
>
> La transmission **n'a pas été effectuée** : elle suppose la désignation du destinataire, le
> choix du canal et la date — autant d'informations qui relèvent du commanditaire.
>
> A-5.1 **ne transforme pas** le `NO-GO` d'import : la décision d'import reste **`NO-GO`**,
> avec **0 cellule importable** sur 80.
>
> **Arrêt à ce stade.** Aucune suite automatique n'est engagée : la prochaine action dépend de la
> **réception réelle** des documents officiels et de l'application du protocole de réception.

---

*Fin du rapport A-5.*
