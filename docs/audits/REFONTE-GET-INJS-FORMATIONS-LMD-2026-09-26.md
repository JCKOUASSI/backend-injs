# REFONTE MÉTIER — GET-INJS + FORMATIONS LMD

**INJS-LMD — INJS Marcory** · Document d'audit préalable à toute modification
Date : **26/09/2026** · Dépôt : `backend-injs` · Branche : `main` · Commit : `89a1097a`

> **État : AUDIT TERMINÉ — AUCUNE MODIFICATION DE MODÈLE EFFECTUÉE À CE JOUR.**
> Ce document est la cartographie exigée par la consigne (§2). Les corrections
> structurelles proposées au § 6 n'ont **pas** été appliquées : elles attendent la
> validation des arbitrages du § 8.

---

## 0. RÉPONSE EXECUTIVE À LA CONSIGNE

La consigne demande une refonte d'envergure. **L'audit montre que 80 % du modèle métier
cible existe déjà et est cohérent.** Le hiatus réel est plus étroit et plus grave qu'un
problème de périmètre : **la séance EDT — l'objet pivot exigé au § 13 — n'a aucun lien
avec le modèle pédagogique**, alors que ce dernier est riche et complet.

| Attendu par la consigne | État réel | Verdict |
| :--- | :--- | :--- |
| Année académique | `scolarite.AnneeAcademique` | ✅ **existe** |
| Formation | `formations.Formation` + `RefFormation` | ✅ **existe** (double objet, cf. § 4.3) |
| Parcours | `scolarite.Parcours` (FK `ref_formation` + `type_formation`) | ✅ **existe** |
| Spécialité | ❌ **aucun modèle** — seulement un `CharField` libre sur `ModuleParticipant` | ⚠️ **lacune** |
| Promotion | ❌ **aucun modèle** — mais le rôle est **déjà tenu** par `Maquette` et `AffectationPedagogique` | ⚠️ **à arbitrer** |
| Groupe | `scolarite.Groupe` + `AffectationGroupe` | ✅ **existe** |
| Maquette | `scolarite.Maquette` (année + `ref_formation` + `parcours` + `niveau`, version, statut) | ✅ **existe** |
| UE | `scolarite.UE` (FK `maquette` + `semestre`, crédits, caractère, ordre) | ✅ **existe** |
| ECUE | `scolarite.ECUE` (FK `ue`, crédits, coefficient, volumes CM/TD/TP) | ✅ **existe** |
| Enseignant contextualisé | `scolarite.AffectationPedagogique` (**FK `enseignant` + `ue` + `ecue` + `groupe` + `semestre`**) | ✅ **existe, très riche** |
| **Séance = pivot** | `edts.AffectationCreneau` : **ni `ecue`, ni FK salle, ni FK enseignant** | 🔴 **LACUNE STRUCTURANTE** |
| Présence rattachée à la séance | `presences.Pointage.seance_edt` (FK) — **fait** | ✅ **existe** |

> **Conclusion** : il ne faut **pas** créer un modèle parallèle. Il faut **relier** l'EDT
> au modèle pédagogique déjà présent. C'est une correction d'une seule foreign key.

---

## 1. ÉTAT INITIAL (§27)

```
branche : main
commit  : 89a1097a fix(ci): use GitHub-hosted runners
git diff --check : (vide — conforme)
```

| État | Détail |
| :--- | :--- |
| Modifications **appliquées par ce chantier** (session précédente) | `backend/presences/{geofence.py,seances_edt_services.py,views.py,test_seances_edt.py}`, `backend/statistiques/{seances_edt_stats.py,tests/…}`, `backend/formations/management/commands/{set_geofence_site.py,seed_lot1_1_injs.py,seed_lot2_1_edts.py}`, `backend/tests_e2e_injs_2026_2027.py` |
| Modifications **préexistantes de l'utilisateur** (8 fichiers CSS/JSX) | `Layout.jsx`, `index.css`, `main.jsx`, `habilitations.css`, `dashboardEngine.css`, `login.css`, `scolariteDashboard.css`, `sidebar.css` |
| Non suivis | `.venv-ci/`, `docs/audits/…`, `workspace/26092026/`, `optimisation-ci-…prompt.md`, `frontend/src/styles/harmonisation.css` |

⚠️ **Les 8 fichiers CSS/JSX sont hors périmètre de la présente refonte et n'ont pas été touchés.**

### 1.1 Chemins demandés vs chemins réels

La consigne liste `apps/`, `modules/`, `GET-INJS/`, `Formations/`, `LMD/`, `etudiants/`,
`enseignants/`. **Aucun de ces répertoires n'existe** (attention : le système de fichiers est
sensible à la casse, `backend/Formations` renvoye `backend/formations`).

| Chemin demandé | État | Équivalent réel |
| :--- | :--- | :--- |
| `apps/`, `modules/`, `GET-INJS/`, `LMD/` | ❌ inexistant | apps Django à la racine de `backend/` ; GET-INJS = section de menu `get_injs` |
| `Formations/` | ⚠️ collision de casse | `backend/formations/` |
| `etudiants/`, `enseignants/` | ❌ inexistant | `backend/scolarite/` (dossiers) et `backend/formations/` (formateurs) |
| `EDT/` | ❌ | `backend/edts/` |
| `presences/`, `scolarite/`, `statistiques/` | ✅ | identiques |

**Apps réelles (26)** : `administrations`, `admissions`, `authentication`, `config`, `core`,
`dashboard`, `docs`, `edts`, `equivalences`, `exports`, `finances_etudiantes`, `formations`,
`graduation`, `habilitations`, `jurys`, `logs`, `media`, `nginx`, `parametres`, `patrimoine`,
`presences`, `referentiel_injs` *(résiduel, non déclaré)*, `referentiels`,
`ressources_humaines`, `scolarite`, `scripts`, `statistiques`, `suiviEvaluation`.

---

## 2. CARTOGRAPHIE INTERNE (§2)

### 2.1 Modèles — le socle LMD

`backend/scolarite/models.py` — **21 modèles**, c'est le cœur du modèle métier INJS-LMD :

| Modèle | Rôle | Statut |
| :--- | :--- | :--- |
| `AnneeAcademique` | année + `courante` (contrainte d'unicité) | ✅ |
| `TypeFormation`, `Niveau` | référentiels d'entrée | ✅ |
| `RegleValidationLMD` | règles LMD (crédits, volumes) | ✅ |
| `Parcours` | FK `ref_formation` + `type_formation`, code/intitulé/actif | ✅ |
| `Semestre`, `RegimeEtudes`, `StatutEtudiant` | référentiels de période et statut | ✅ |
| **`Groupe`** | unité d'exécution, FK `annee_academique` + `niveau` + `ref_formation` | ✅ |
| `DossierEtudiant`, `InscriptionAdministrative`, `InscriptionPedagogique` | scolarité | ✅ |
| `AffectationGroupe` | inscription d'un étudiant à un groupe (actif/période) | ✅ |
| **`Maquette`** | FK `annee_academique` + `ref_formation` + `parcours` + `niveau`, version, statut | ✅ |
| **`UE`** | FK `maquette` + `semestre`, code, crédits, caractère, ordre | ✅ |
| **`ECUE`** | FK `ue`, code, crédits, coefficient, volumes CM/TD/TP | ✅ |
| `MaquetteJournal` | journal de validation | ✅ |
| **`AffectationPedagogique`** | **FK `annee_academique`, `ref_formation`, `parcours`, `niveau`, `semestre`, `ue`, `ecue`, `groupe`, `enseignant`** + volume + statut | ✅ **le modèle cible complet** |
| `IndisponibiliteEnseignant` | contraintes EDT | ✅ |

### 2.2 La chaîne cible est DÉJÀ complète… sauf le dernier maillon

```
AffectationPedagogique
   annee_academique → ref_formation → parcours → niveau → semestre
                    → UE → ECUE
                    → GROUPE
                    → ENSEIGNANT (FK formations.Formateur)
```

**C'est exactement la chaîne exigée au § 3 de la consigne.** Elle est déjà codée, testée
(`scolarite/tests/test_pedagogie.py`, `test_parcours_complet.py`), et elle n'est pas utilisée
par l'EDT.

### 2.3 L'EDT — l'objet séance

`backend/edts/models.py` — `AffectationCreneau` (l'objet « séance planifiée ») :

| Champ | Type | Conformité § 10-13 |
| :--- | :--- | :--- |
| `emploi_du_temps` | FK | ✅ |
| `creneau_template` | FK (jour, heures) | ✅ |
| `semaine_debut` / `semaine_fin` | entier | ✅ |
| **`formation`** | FK → `RefFormation` (**catalogue**, pas l'instance) | ⚠️ |
| **`groupe`** | FK → `scolarite.Groupe` | ✅ |
| **`salle_nom`** | **`CharField`** | 🔴 « Évite toute relation ambiguë fondée uniquement sur un intitulé texte » (§ 10) |
| **`enseignant_id`** | **`PositiveIntegerField`** | 🔴 pas de FK — unenforceable, non contraint |
| `enseignant_nom` | `CharField` | 🔴 dénormalisé |
| `intitule` | `CharField` | 🔴 l'ECUE est deviné par un texte |
| **ECUE** | **absent** | 🔴 **impossible de répondre « Quel ECUE ? »** |
| `nature` | choix (COURS, TP…) | ✅ |

### 2.4 Présences

`presences.Pointage` porte **déjà** les deux canaux : `session` (legacy) **et**
`seance_edt` (FK `AffectationCreneau`). Le § 14-15 de la consigne est donc **satisfait** :
la présence EST rattachée à la séance, pas à « étudiant + date ».

Le badgeage automatique (`presences/seances_edt_services.badger_scan`) applique déjà :
identité, QR de séance validable, fenêtre horaire, appartenance au groupe, géolocalisation
(corrigée le 26/09), anti-doublon, traçabilité `AuditLog`. Le forcé impose un motif **en
correction** (règle 08.14).

### 2.5 API, frontend, menu

| Élément | Constat |
| :--- | :--- |
| Routes | 471 `path()` sur 23 `urls.py` ; **aucune route CPFAE** dans `config/urls.py` (seul un commentaire) |
| Menu | `frontend/src/menu/arborescence.js` — 4 sections : `scolarite`, `formations`, `get_injs`, `evaluations` |
| **GET-INJS** | **existe déjà** (`get_injs`, libellé « GET-INJS ») avec 10 entrées : EDT, création, présences séance, cours, salles, disponibilités, enseignants, conflits, rattrapages, export |
| Formations LMD | entrées `formations.lmd`, `formations.filieres`, `formations.parcours`, `formations.niveaux`, `formations.semestres`, `formations.ue_ecue`, `formations.cours_lmd` |
| ⚠️ **`formations.cours`** | libellé **« Cours & modules (CPFAE — héritage) »**, chemin `/modules` → **cible de la suppression (§ 28)** |
| Écrans génériques | `menu/ecrans.js` + `routesGeneriques.jsx` (≈ 70 écrans dérivés de l'arborescence) |
| Frontend CPFAE | 98 occurrences, quasi toutes dans `utils/roles.js`, `PointJournalierCPFAE.jsx`, `Statistiques.jsx` |

### 2.6 Données réelles (base officielle `injs_lmd_current`)

| Table | Lignes | Lecture |
| :--- | --: | :--- |
| `formations_formation` | 8 | offre de formation |
| **`formations_module`** | **10** | ⚠️ **seul objet pédagogique peuplé — c'est l'héritage CPFAE** |
| `scolarite_maquette` | **0** | chaîne LMD vide |
| `scolarite_ue` | **0** | |
| `scolarite_ecue` | **0** | |
| `scolarite_affectationpedagogique` | **0** | |
| `edts_affectationcreneau` | **0** | aucune séance planifiée |
| `scolarite_groupe` | **0** | |
| `presences_pointage` | 34 | **tous sur le canal legacy** (`seance_edt` = 0) |

> **Conséquence majeure** : le modèle pédagogique LMD est **vide**, et le seul modèle
> peuplé est l'objet `Module` hérité du CPFAE. Toute correction structurelle proposée est donc
> **sans impact sur des données existantes** — le risque de migration est nul.

---

## 3. DÉPENDANCES CPFAE / SYGEPCPFAE (§22)

**371 occurrences** backend + **98** frontend. Elles ne sont pas de même nature, et la
consigne interdit de traiter uniformément. Classification par **nature technique** :

### 3.1 [À CONSERVER] — identité technique, aucun impact métier

| Élément | Occ. | Nature | Pourquoi conserver |
| :--- | --: | :--- | :--- |
| `PUBLIC_APP_URL` = `app.sygepcpfae.org` | 1 | défaut d'env | corriger l'URL de production n'est pas une refonte métier |
| Commentaire « Web dashboard CPFAE » | 1 | commentaire | cosmétique |
| Libellés d'interface « CPFAE » | ~30 | texte affiché | renommage sans incidence technique |

### 3.2 [À ADAPTER] — des noms, pas des logiques

| Élément | Occ. | Nature | Risque d'un renommage |
| :--- | --: | :--- | :--- |
| **Rôle `CPFAE_ADMIN` / `CHEF_CPFAE_ADMIN`** | **202** | `User.Role` + groupes Django + permissions CURP + données | 🔴 **Élevé** : identité, RBAC, comptes, front, tests. **Ne pas renommer ici** — créer un alias |
| `PointJournalierCPFAE` (front) | ~20 | composant + API | 🟡 adossé au `Module` CPFAE — voir § 5 |
| `statistiques/point_journalier.py` | 8 | **logique** | 🟡 voir § 5.2 |
| Emails `authentication/emails.py` | 17 | textes d'e-mail | 🟢 faible |

### 3.3 [À ISOLER] — logique héritée à ne pas propager

| Élément | Fichiers | Nature | Décision |
| :--- | :--- | :--- | :--- |
| **`formations.Module`** | `formations/{models,api_views,views,notes_fiche_api}.py`, `dashboard/services.py`, `suiviEvaluation/services.py` | objet pédagogique **hérité**, **seul modèle peuplé (10 lignes)** | **Isoler** : plus de rattachement depuis l'EDT, plus d'injection dans les statistiques. Ne pas supprimer |
| **« point journalier CPFAE »** | `statistiques/point_journalier*.py`, `PointJournalierCPFAE.jsx` | tableau de bord **Module**-centré | **Isoler** : ne pas l'étendre, ne pas le réintroduire (§ 18) |
| Routes `/modules`, `/formations/:id/modules/:id` | `App.jsx`, menu | écrans | **Isoler** : retirer du menu (§ 28), conserver les routes en transition |

### 3.4 [OBSOLESCENTE] — vérifié inutilisé

| Élément | Preuve | Action |
| :--- | :--- | :--- |
| `backend/referentiel_injs/` | app **non déclarée** dans `INSTALLED_APPS` ; référentiels chargés par `habilitations` | documenter puis supprimer |
| `scripts/generate_real_import.py` (32 occ.) | générateur de fixtures, hors chaîne | documenter puis supprimer |

### 3.5 [À SUPPRIMER APRÈS VALIDATION]

| Élément | Prérequis |
| :--- | :--- |
| Libellé de menu « Cours & modules (CPFAE — héritage) » | le retrait casse `menu/arborescence.test.js:313` (assert `/modules`). Mise à jour **simultanée** obligatoire |
| 10 lignes `formations_module` | après bascule complète sur la chaîne LMD — **pas aujourd'hui** |

### 3.6 Récapitulatif

| Classe | Élément principal | Décision |
| :--- | :--- | :--- |
| [À CONSERVER] | URLs, commentaires, libellés | garder / renommer l'URL de prod |
| [À ADAPTER] | Rôle `CPFAE_ADMIN` (202 occ.) | **alias**, pas renommage |
| [À ISOLER] | `Module`, point journalier, `/modules` | geler l'usage, ne pas propager |
| [OBSOLESCENTE] | `referentiel_injs`, générateurs | documenter → supprimer |
| [À SUPPRIMER APRÈS VALIDATION] | entrée de menu `/modules` | + test à corriger |

---

## 4. MODÈLE MÉTTIER CIBLE — CONFRONTÉ AU CODE

### 4.1 Chaîne demandée, état réel

| # | Exigence | État | Modèle réel |
| :-- | :--- | :-- | :--- |
| 1 | Année académique | ✅ | `scolarite.AnneeAcademique` |
| 2 | Formation | ✅ | `formations.Formation` (+ `RefFormation` catalogue) |
| 3 | Parcours | ✅ | `scolarite.Parcours` |
| 4 | Spécialité | 🔴 | **absente** — `ModuleParticipant.specialite` est un texte libre |
| 5 | Promotion | ⚠️ | **absente comme modèle** ; rôle porté par `(annee_academique, ref_formation, parcours, niveau)` dans `Maquette` et `AffectationPedagogique` |
| 6 | Groupe | ✅ | `scolarite.Groupe` + `AffectationGroupe` |
| 7 | Maquette | ✅ | `scolarite.Maquette` (version, statut, validation) |
| 8 | UE | ✅ | `scolarite.UE` |
| 9 | ECUE | ✅ | `scolarite.ECUE` (crédits, coefficient, volumes CM/TD/TP) |
| 10 | Enseignant contextualisé | ✅ | `scolarite.AffectationPedagogique.enseignant` |
| 11 | **Séance pivot** | 🔴 | `edts.AffectationCreneau` **sans lien avec l'ECUE** |

### 4.2 Le seul maillon manquant

```
AffectationPedagogique ──✗── AffectationCreneau
   (UE, ECUE, enseignant,        (séance : jour, heure, salle, groupe)
    groupe, semestre, parcours)
```

**C'est LA correction à faire.** Une seule FK nullable
`AffectationCreneau.affectation_pedagogique → AffectationPedagogique`
rend la séance capable de répondre à **toutes** les questions du § 13 :
ECUE ? UE ? formation ? parcours ? groupe ? enseignant ? salle ? moment ?

### 4.3 Le doublon `Formation` / `RefFormation`

`RefFormation` (catalogue) et `Formation` (instance d'exécution) coexistent. C'est **cohérent**
et conforme : le § 5 demande de réutiliser l'existant plutôt que dupliquer.
**Aucun correctif proposé** — documenté pour éviter toute confusion.

### 4.4 Pourquoi ne pas créer `Promotion` ni `Spécialité` maintenant

| Modèle demandé | Décision | Motif |
| :--- | :--- | :--- |
| `Promotion` | **Ne pas créer** | le rôle est **déjà tenu** par le tuple `(annee_academique, ref_formation, parcours, niveau)` de `Maquette` et `AffectationPedagogique`. Le § 9 interdit une structure parallèle : créer `Promotion` serait une **troisième** façon de dire la même chose |
| `Spécialité` | **ARBITRAGE REQUIS** | aujourd'hui `Parcours` n'a pas d'enfant « spécialité ». Le modèle est possible, mais les **règles de rattachement sont métier** (§ 25) |

---

## 5. LE POINT JOURNALIER CPFAE (§ 5, § 18, § 28)

### 5.1 Ce qu'il est

`statistiques/point_journalier.py` (645 lignes) + `PointJournalierCPFAE.jsx` : tableau
jour × créneau × groupe, **centré sur `Module`**. Il consomme `filter_sessions()` qui ne lit
que `SessionModule` et **ignore** les présences `seance_edt` (constaté le 26/09 ; corrigé par
une couche dédiée `statistiques/seances_edt_stats.py`, non réinjectée ici).

### 5.2 Position retenue

| Règle de la consigne | Application |
| :--- | :--- |
| « Ne reproduis pas le point journalier CPFAE » | **Aucune reproduction.** Le composant n'est ni étendu, ni réinjecté, ni utilisé comme modèle |
| « Ne réintroduis pas de point journalier CPFAE » (§ 18) | les statistiques LMD passent par `seances_edt_stats` (formation / groupe / séance), pas par le point journalier |
| « Évite le rattachement artificiel RefFormation CPFAE → Module CPFAE » | **C'est le piège évité** : la liaison sera `AffectationCreneau → AffectationPedagogique → ECUE`, **jamais** vers `Module` |

> Le composant `PointJournalierCPFAE.jsx` et son API sont **conservés** (non supprimés) : ils
> servent encore le canal legacy peuplé (34 pointages, 8 sessions). Les **isoler** sans les
> casser ; leur retrait définitif relève de la bascule de canal.

---

## 6. CORRECTIONS PROPOSÉES — **NON APPLIQUÉES**

### C1 — Rendre la séance pivot 🔴 P0 — **1 seule FK**

```python
# edts/models.py — AffectationCreneau
affectation_pedagogique = models.ForeignKey(
    'scolarite.AffectationPedagogique',
    on_delete=models.PROTECT,
    null=True, blank=True,
    related_name='seances_edt',
    help_text="Contexte pédagogique de la séance (UE, ECUE, enseignant, groupe, semestre).",
)
```

| | |
| :--- | :--- |
| **Valeur** | rend possible `Séance → ECUE → UE → Maquette → Formation/Parcours` et `Séance → Enseignant / Groupe` (§ 10, § 13) |
| **Migration** | 1 champ `null=True` — **aucune donnée existante touchée** (`edts_affectationcreneau` = 0 ligne) |
| **Régression** | **nulle** — champ optionnel, aucun code existant modifié |
| **Test** | « une séance liée expose UE, ECUE, enseignant, groupe, semestre » |

### C2 — FK salle (au lieu d'un texte) 🟡 P1 — **1 FK**

`salle_nom` (`CharField`) → `salle` (FK `RefSalle`, nullable), `salle_nom` **conservé en
lecture**. Supprime l'ambiguïté « intitulé texte » exigée au § 10. L'écran
`Salles & espaces` existe déjà au menu GET-INJS : la donnée est là, seule la FK manque.

### C3 — FK enseignant (au lieu d'un entier) 🟡 P1 — **1 FK**

`enseignant_id` (`PositiveIntegerField`, **non contraint**) → `enseignant` (FK
`User`, nullable). `enseignant_id` / `enseignant_nom` **conservés en lecture** pour la
transition.

> ⚠️ **Correction du 26/09 (constatée pendant le lot L1).** L'arbitrage A-6/C3 ci-dessus
> avait été rédigé en supposant que l'enseignant était rattaché à `User`. **C'est faux :
> la cible réelle est `formations.Formateur`.** `AffectationPedagogique.enseignant` pointe
> vers `formations.Formateur` (et non vers `AUTH_USER_MODEL`). Deux conséquences :
> 1. **L2/C3 doit cibler `formations.Formateur`**, pas `User` — à revalider avant
>    d'implémenter L2.
> 2. Le rapprochement enseignant EDT ↔ enseignant LMD se fait via `Formateur`
>    (`numerobadge` est la clé métier naturelle).
> `AffectationCreneau` possède **déjà** un `formateur` FK vers `formations.Formateur`
> (migration `edts.0002`) : L2/C3 devra donc arbitrer entre ce FK existant et un FK
> vers `User`, et non créer un doublon.

> **C1, C2, C3 sont les seules corrections de modèle proposées.** Elles couvrent § 10, § 11 et
> § 13. **Aucune donnée, aucune migration existante, aucune suppression.**

### C4 — Retirer l'entrée de menu « Cours & modules (CPFAE — héritage) » 🟢 P2

Retrait de `formations.cours` dans `arborescence.js` **+ mise à jour de
`arborescence.test.js:313`** (même lot, sinon build rouge). Les **routes** `/modules` et
`/formations/:id/modules/:id` sont **conservées** : une URL peut être liée ou mise en favori.
`Modules.jsx` et son API ne sont **pas supprimés** → [À ISOLER].

### C5 — Alias de rôle `CPFAE_ADMIN` 🟢 P2

Rôle `DIRECTION_PEDAGOGIQUE` **(nom à arbitrer)** aliasé sur le rôle existant, pour
désolidariser progressivement **sans** migration de 202 occurrences ni de comptes.
**Nom non inventé ici** (§ 25).

### C6 — Chaîne LMD devoidée sur la base officielle 🟡 P1

`maquette` / `ue` / `ecue` / `affectationpedagogique` / `groupe` / `affectationcreneau` sont
**à zéro**. Sans données, aucun parcours n'est démontrable. → **Nécessite l'arbitrage des
maquettes officielles** (§ 8, A-2/A-3) ; ce n'est pas un correctif de code. Le seed
`seed_injs_complet` existe et fonctionne.

---

## 7. CE QUI EST DÉJÀ CONFORME (à ne pas refaire)

| Exigence | Constat |
| :--- | :--- |
| § 14 présence rattachée à la séance | `Pointage.seance_edt` FK ✅ |
| § 15 badgeage automatique | identité · QR de séance · fenêtre · groupe · géolocalisation · anti-doublon · `AuditLog` ✅ |
| § 16 badgeage forcé | motif obligatoire **en correction** (règle 08.14) + `FORCE_DFRC` + auteur tracé ✅ |
| § 17 géolocalisation configurable | module partagé `presences/geofence.py`, 2 canaux, refus activable **sans réécrire la chaîne** ✅ |
| § 4 GET-INJS | section existante, 10 entrées opérationnelles ✅ |
| § 9 maquette | `Maquette → UE → ECUE` avec versioning et validation ✅ |
| § 12 types de séance | `AffectationCreneau.nature` (COURS, TP, …) ✅ |
| § 21 migrations | 236 migrations appliquées, **aucune suppression** ✅ |

---

## 8. ARBITRAGES MÉTIERS REQUIS (§25)

**Aucune règle n'a été inventée.** Chacune est documentée avec ses options et son impact.

### A-1 — Rattachement d'une séance EDT à son ECUE

| | |
| :--- | :--- |
| **Code actuel** | `AffectationCreneau.intitule` (texte libre) ; aucun ECUE |
| **Ce qui manque** | la règle de rattachement |
| **Option 1 — recommandée** | FK `affectation_pedagogique` choisie **manuellement** à la planification : zéro inférence, zéro risque |
| **Option 2** | déduction automatique par `(groupe, enseignant, créneau)` — **ambiguë** si un enseignant tient 2 ECUE le même jour |
| **Impact** | Option 1 : saisie un peu plus longue, données fiables. Option 2 : gain de saisie, **risque de rattachement erroné** |

### A-2 — Promotion : faut-il un modèle ?

| | |
| :--- | :--- |
| **Code actuel** | pas de modèle ; le rôle est porté par `(annee_academique, ref_formation, parcours, niveau)` |
| **Option 1 — recommandée** | **aucun modèle** ; la documentation rend le tuple explicite |
| **Option 2** | modèle `Promotion` FK (année, formation, parcours, niveau) — plus lisible, mais **structure parallèle** proscrite par le § 9 |
| **Impact** | Option 1 : risque nul. Option 2 : 1 modèle + migration + refonte de `Maquette` et `AffectationPedagogique` |

### A-3 — Spécialité : modèle ou attribut de `Parcours` ?

| | |
| :--- | :--- |
| **Code actuel** | `Parcours` sans spécialité ; `ModuleParticipant.specialite` = texte libre (non fiable) |
| **Option 1** | `Specialite` FK sur `Parcours` — respecte FORMATION → PARCOURS → SPÉCIALITÉ |
| **Option 2** | champ `specialite` sur `Parcours` — plus simple, non référentielle |
| **Impact** | dans les deux cas, **la liste des spécialités est une donnée métier** |

### A-4 — Noms officiels (formations, parcours, ECUE)

Le dépôt ne contient **aucune nomenclature validée**. Le seed propose des libellés de
démonstration. **ARBITRAGE REQUIS** — aucun nom n'a été inventé.

### A-5 — Politique GPS (§ 17)

La consigne demande de conserver les deux modes : c'est fait (`--rayon`, `--desactiver`).
Le défaut retenu le 26/09 est **refus + alerte**. **Confirmer** si le refus doit devenir
configurable par site.

### A-6 — `on_delete` de la FK C1

`PROTECT` (une affectation pédagogique ne doit pas disparaître sous une séance) ou
`SET_NULL` (la séance survit, perd son contexte). **Choix métier.**

---

## 9. MATRICE DE TRAÇABILITÉ (livrable B)

| # | Exigence métier | Modèle | API | Frontend | Test | Statut |
| :-- | :--- | :--- | :--- | :-- | :-- | :-- |
| 1 | Année académique | `scolarite.AnneeAcademique` | ✅ | ✅ | ✅ | **Conforme** |
| 2 | Formation | `formations.Formation` + `RefFormation` | ✅ `/formations/` | ✅ | ✅ | **Conforme** |
| 3 | Parcours | `scolarite.Parcours` | ✅ `/scolarite/ref/parcours/` | ✅ | ✅ `test_parcours_complet` | **Conforme** |
| 4 | **Spécialité** | ❌ | ❌ | ❌ | ❌ | 🔴 **Absent** (A-3) |
| 5 | **Promotion** | ⚠️ implicite | ❌ | ❌ | ❌ | ⚠️ **À arbitrer** (A-2) |
| 6 | Groupe | `scolarite.Groupe` + `AffectationGroupe` | ✅ | ✅ | ✅ `test_groupes` | **Conforme** |
| 7 | Maquette | `scolarite.Maquette` | ✅ | ✅ « Maquettes LMD » | ✅ | **Conforme** |
| 8 | UE | `scolarite.UE` | ✅ | ✅ « UE / ECUE » | ✅ | **Conforme** |
| 9 | ECUE | `scolarite.ECUE` | ✅ | ✅ | ✅ | **Conforme** |
| 10 | Enseignant contextualisé | `AffectationPedagogique.enseignant` | ✅ | ✅ | ✅ `test_pedagogie` | **Conforme** |
| 11 | **Séance = pivot pédagogique** | 🔴 **lien absent** | ❌ | ❌ | ❌ | 🔴 **Lacune (C1)** |
| 12 | Séance : salle identifiée | 🔴 `salle_nom` texte | ❌ | ⚠️ écran existe | ❌ | 🔴 **Lacune (C2)** |
| 13 | Séance : enseignant identifié | 🔴 `enseignant_id` entier | ❌ | ⚠️ écran existe | ❌ | 🔴 **Lacune (C3)** |
| 14 | Présence rattachée à la séance | `Pointage.seance_edt` | ✅ | ✅ | ✅ 13 tests | **Conforme** |
| 15 | Badgeage automatique | `badger_scan()` | ✅ | mobile | ✅ | **Conforme** |
| 16 | Badgeage forcé + motif | `emarger()` | ✅ | ✅ | ✅ | **Conforme** |
| 17 | Géolocalisation paramétrable | `presences/geofence.py` | ✅ | mobile | ✅ 8 tests | **Conforme** (A-5) |
| 18 | Statistiques LMD | `seances_edt_stats.py` | ❌ non exposée | ❌ | ✅ 13 tests | 🟡 **Couche prête, non exposée** |
| 19 | GET-INJS fonctionnel | — | — | ✅ 10 entrées | ✅ | **Conforme** |
| 20 | **Sous-module CPFAE supprimé** | `Module` (10 lignes) | `/formations/` | ⚠️ `/modules` | ⚠️ test menu | 🟡 **Menu à retirer** (C4) |
| 21 | Chaîne LMD en données | 6 tables à **0** | — | ❌ écrans vides | — | 🔴 **Données absentes** (A-4) |

**Légende** : ✅ conforme · 🟡 à finaliser · 🔴 lacune

---

## 10. PLAN D'EXÉCUTION PROPOSÉ

| Lot | Contenu | Modèle | Migration | Test requis | Dépend |
| :-- | :--- | :-- | :-- | :-- | :-- |
| **L1** | **C1** — FK `affectation_pedagogique` + test « la séance expose son ECUE » | 1 champ | 1 `AddField` null | 1 test | **A-1, A-6** |
| **L2** | **C2** + **C3** — FK salle et enseignant, champs texte conservés | 2 champs | 1 `AddField` null | 2 tests | L1 — **⚠️ C3 à revalider (§ 15)** |
| **L3** | **C4** — retrait du menu CPFAE + mise à jour du test | — | — | menu + build | — |
| **L4** | **C5** — alias de rôle (nom arbitré) | `User.Role` | 1 `AlterField` | RBAC | — |
| **L5** | Exposition API des statistiques LMD (§ 18, § 20) | — | — | API | — |
| **L6** | Navigation front GET-INJS → LMD (§ 19) | — | — | Vitest | L1 |

> ✅ **L1, L2 et L3 RÉALISÉS le 26/09/2026** — détail aux § 15, § 16 et § 17. L4 à L6 non démarrés.
> L1 et L2 sont **purement structurels** et réversibles (suppression du champ). L3 est
> réversible (rétablissement d'une entrée de menu).

---

## 11. RISQUES

| Risque | Probabilité | Impact | Parade |
| :--- | :-- | :-- | :-- |
| FK C1 mal remplie (séances sans contexte) | Moyenne | Élevé | champ **optionnel** ; rapport des séances non contextualisées ; aucun blocage de saisie |
| Rattachement auto erroné (option 2 de A-1) | Élevée | **Élevé** | **option 1 recommandée** : choix manuel |
| Retrait du menu cassant des liens externes | Faible | Moyen | **routes conservées** |
| Renommage du rôle `CPFAE_ADMIN` | — | **Critique** | **alias**, jamais renommé |
| Création d'un modèle `Promotion` | Moyenne | Moyen | une **3ᵉ** représentation du même concept |
| Confusion `Module` (CPFAE) ↔ `ECUE` (LMD) | Élevée | Moyen | documentée ; `Module` isolé, jamais rattaché à l'EDT |
| Migration sur base peuplée | **Nulle** | — | `edts_affectationcreneau` = 0 ligne |

---

## 12. RÉSUMÉ FINAL (livrable C)

### FICHIERS MODIFIÉS
**Aucun** pour cette refonte. *(Les fichiers listés en § 1 proviennent du chantier
« géolocalisation + statistiques LMD » du 26/09, déjà validé.)*

### FICHIERS CRÉÉS
**Aucun** pour cette refonte. Seul le présent rapport.

### MIGRATIONS
**Aucune.** Proposée : 1 `AddField` nullable (C1), 1 pour C2+C3.

### API
**Aucune modification.** 471 routes ; contrat `docs/api/contract.snapshot.json` conforme.
À venir (L5) : exposition des statistiques LMD — **sans nouvelle route** si un endpoint
`statistiques` existant est réutilisé.

### TESTS
Aucun test ajouté. Référence avant refonte : **1 716 tests backend OK** (0 échec),
**1 747 tests frontend** (0 échec).

### CPFAE À TRAITER

| Classe | Élément | Action |
| :--- | :--- | :--- |
| [À CONSERVER] | URL de production, libellés | renommer l'URL ; libellés libres |
| [À ADAPTER] | rôle `CPFAE_ADMIN` (202 occ.) | **alias** (L4) |
| [À ISOLER] | `formations.Module`, point journalier, `/modules` | geler l'usage ; menu à retirer (L3) |
| [OBSOLESCENTE] | `referentiel_injs/`, générateurs de fixtures | documenter → supprimer |
| [À SUPPRIMER APRÈS VALIDATION] | 10 lignes `formations_module` | après bascule LMD |

### ARBITRAGES
**2 tranchés** : A-1 (rattachement ECUE → **manuel, explicite**) · A-6 (`on_delete` → **PROTECT**).
**4 ouverts** : A-2 (modèle Promotion) · A-3 (Spécialité) · A-4 (nomenclature officielle) ·
A-5 (défaut GPS).

### RISQUES
Détail au § 11. **Le plus critique** : un rattachement automatique ECUE erroné.
**Parade retenue** : choix manuel (A-1 option 1).

---

## 15. LOT L1 / C1 — RÉALISÉ LE 26/09/2026 ✅

### 15.1 État initial

| | |
| :--- | :--- |
| **Modèle** | `edts.AffectationCreneau` — **aucune FK vers `AffectationPedagogique`** |
| **Contexte accessible depuis une séance** | aucun UE, aucun ECUE, aucun enseignant LMD ; seulement `intitule` (texte libre) |
| **Base `injs_lmd_current`** | `edts_affectationcreneau` = **0 ligne** ✅ condition § 2 respectée |
| **Vérification préalable** | branche `main`, commit `89a1097a`, `git diff --check` propre |

### 15.2 Modification — 1 seul champ

`backend/edts/models.py` (+12 lignes) :

```python
affectation_pedagogique = models.ForeignKey(
    'scolarite.AffectationPedagogique',
    on_delete=models.PROTECT,      # A-6 : conforme aux conventions du projet
    null=True, blank=True,         # aucune donnée existante à renseigner
    related_name='seances_edt',
    help_text="Contexte pédagogique de la séance (...). Rattachement MANUEL "
              "et explicite : aucune déduction automatique n'est effectuée.",
)
```

**Aucun autre champ ajouté.** Aucun modèle parallèle créé. Aucune modification de
`AffectationPedagogique`, `UE`, `ECUE`, `Maquette`, `Groupe`, `Formateur`.

**Rattachement MANUEL (A-1) :** aucune logique de déduction (titre, date, enseignant,
groupe, UE, ECUE, salle, heuristique) n'a été introduite. Le `help_text` l'inscrit
explicitement dans le modèle. Une séance sans rattachement est parfaitement valide.

### 15.3 Migration

**`edts/migrations/0003_affectationcreneau_affectation_pedagogique.py`**

```python
dependencies = [('edts', '0002_...'), ('scolarite', '0015_...')]
operations = [migrations.AddField(
    model_name='affectationcreneau', name='affectation_pedagogique',
    field=models.ForeignKey(blank=True, null=True,
        on_delete=django.db.models.deletion.PROTECT,
        related_name='seances_edt', to='scolarite.affectationpedagogique'))]
```

**Un seul `AddField`.** Aucune suppression, aucun `AlterField`, aucun `RunPython`,
aucune donnée touchée. Migration **non destructive et réversible**.

Structure vérifiée en base après application :

```
affectation_pedagogique_id bigint  NULL   + index
FK → scolarite_affectationpedagogique(id)   [PROTECT au niveau Django]
```

### 15.4 Tests

**Fichier créé : `backend/edts/tests/test_raccordement_pedagogique.py`** (9 tests)

| Test | Exigence couverte | Résultat |
| :--- | :--- | :--- |
| `test_la_seance_retrouve_son_ecue` | **§ 9 — séance → ECUE** | ✅ |
| `test_la_chaine_complete_est_atteignable` | § 9 — ECUE → UE → Maquette + Formation/Parcours/Niveau/Semestre/Groupe/Enseignant | ✅ |
| `test_la_seance_expose_encore_son_groupe_et_son_horaire` | non-régression de l'identité opérationnelle | ✅ |
| `test_une_seance_sans_rattachement_reste_valide` | **§ 3 — aucune déduction automatique** | ✅ |
| `test_le_rattachement_est_explicite_et_modifiable` | § 3 — rattachement/détachement manuels | ✅ |
| `test_une_seance_partage_l_affectation_pedagogique` | § 5 — plusieurs séances (CM/TD/TP) par ECUE | ✅ |
| `test_supprimer_l_affectation_utilisee_est_protge` | **§ 9 — comportement PROTECT** | ✅ |
| `test_supprimer_une_affectation_inutilisee_est_autorise` | § 4 — converse du PROTECT | ✅ |
| `test_le_protect_est_bien_le_on_delete_du_modele` | § 4 — garde-fou de convention | ✅ |

**Suites exécutées**

| Commande | Résultat |
| :--- | :--- |
| `manage.py test edts.tests.test_raccordement_pedagogique` | **9/9 OK** |
| `manage.py test edts scolarite formations presences` | **660 tests OK** (2 skipped préexistants) |
| `manage.py check` | ✅ (1 warning `urls.W005` **préexistant**, hors périmètre) |
| `manage.py makemigrations --check --dry-run` | ✅ **No changes detected** |
| `git diff --check` | ✅ propre |

### 15.5 Base — données intactes

| Table | Avant migration | Après migration |
| :--- | :-- | :-- |
| `edts_affectationcreneau` | **0** | **0** ✅ |
| `scolarite_affectationpedagogique` | 0 | 0 |
| `scolarite_ue` / `scolarite_ecue` / `scolarite_maquette` | 0 / 0 / 0 | 0 / 0 / 0 |
| `formations_module` (hérité CPFAE) | 10 | 10 |
| `presences_pointage` | 34 | 34 |
| `authentication_user` | 22 | 22 |

Aucune donnée existante modifiée. **Aucun `DROP`, `TRUNCATE`, `DELETE`, `flush` exécuté.**

### 15.6 Git

| | |
| :--- | :--- |
| **Modifié** | `backend/edts/models.py` (+12) — **seul fichier de code touché** |
| **Créé (migration)** | `backend/edts/migrations/0003_affectationcreneau_affectation_pedagogique.py` |
| **Créé (test)** | `backend/edts/tests/test_raccordement_pedagogique.py` |
| **Modifié (doc)** | ce rapport |
| **`git diff --check`** | ✅ propre |
| **`git diff --stat`** | `backend/edts/models.py \| 12 ++++++++++++` |
| **Modifications utilisateur antérieures** | ✅ préservées (8 fichiers CSS/JSX, 6 fichiers backend, docs) |
| **Commit** | **non effectué** — en attente de validation |

### 15.7 Risques et découvertes

| # | Constat | Impact | Traitement |
| :-- | :--- | :--- | :--- |
| 1 | **`AffectationPedagogique.enseignant` pointe vers `formations.Formateur`, pas `User`** | 🔴 Le rapport supposait `User` — **erreur de cadrage** | **Corrigé § 2.2 et § 7/C3.** L2/C3 doit cibler `Formateur` |
| 2 | `AffectationCreneau` possède **déjà** `formateur` (FK `Formateur`, migration `edts.0002`) | 🟡 L2/C3 créerait un doublon | **Arbitrage requis avant L2** |
| 3 | `salle_nom` et `enseignant_id` restent des champs texte/entier libre | 🟡 Prévisible | **L2 — non traité ici (hors périmètre)** |
| 4 | `edts_affectationcreneau` = 0 ligne et `presences_pointage` = 34 lignes sur le canal **legacy** | 🟡 La chaîne LMD reste non peuplée | **Aucun rattachement artificiel inventé** (§ 3) |
| 5 | Une **maquette `ACTIVE` est immuable** (`ValidationError` à l'écriture d'UE) | ℹ️ Test uniquement | Maquette laissée en `BROUILLON` dans le test |
| 6 | `urls.W005` (namespace `dashboard_api` non unique) | ℹ️ Préexistant | **Non corrigé — hors périmètre** |

**Aucun risque de données.** L1 est purement structurel et entièrement réversible.

### 15.8 Conditions nécessaires avant L2

1. **Arbitrer C3** : la cible est `formations.Formateur` et non `User` (§ 15.7 #1 et #2).
   Faut-il exploiter le `formateur` **existant**, ou créer un FK distinct ?
2. **C2 est confirmé** : `formations.RefSalle` existe bien (modèle + admin + API
   `test_core.RefSalleAPITest`). Il reste à vérifier son unicité par nom avant d'écrire
   la FK `salle`, et à décider si `salle_nom` est conservé en lecture.
3. **Aucun rattachement automatique** : L2 ne doit introduire aucune déduction.
4. Migrer L1 en recette avant toute nouvelle édition de schéma.

---

## 16. LOT L2 — CONSOLIDATION DE LA SÉANCE LMD — RÉALISÉ LE 26/09/2026 ✅

**Principe** : consolider l'existant, ne rien reconstruire.
`EXISTANT > NOUVEAU` · `SOURCE UNIQUE > DOUBLON` · `RELATION EXPLICITE > AUTOMATISME`.

### 16.1 Modèle avant / après

| | Avant L1 | Après L1 | Après L2 |
| :--- | :--- | :--- | :--- |
| `formateur` → `Formateur` | ✅ *(existant)* | ✅ | ✅ **réutilisé tel quel** |
| `enseignant_id` (entier libre) | ⚠️ | ⚠️ | ⚠️ **inchangé** |
| `affectation_pedagogique` | ❌ | ✅ (L1) | ✅ |
| `salle_nom` (texte) | ✅ | ✅ | ✅ **conservé** |
| `salle` → `RefSalle` | ❌ | ❌ | ✅ **ajouté (L2)** |

**Un seul champ ajouté en L2 : `salle`.** `salle_nom` est conservé : il alimente la
détection de conflits de `edts/services.py`, l'API EDT, les présences, les statistiques
et la géolocalisation. Sa suppression est hors périmètre.

### 16.2 C3 — Formateur : relation existante réutilisée

| | |
| :--- | :--- |
| **Décision** | **Réutiliser `AffectationCreneau.formateur`** (FK `formations.Formateur`, `PROTECT`, nullable) |
| **Aucun doublon** | ✅ aucune FK `enseignant` créée, aucun champ ajouté ni renommé |
| **Champs laissés intacts** | `formateur` (FK), `enseignant_id` (entier), `enseignant_nom` (texte) |
| **Preuve** | `test_il_n_existe_qu_un_seul_champ_vers_le_formateur` : une seule FK vers `Formateur` dans le modèle |

### 16.3 C2 — Salle : analyse puis décision

| Critère | Constat |
| :--- | :--- |
| **Modèle `RefSalle`** | `formations.RefSalle` — `site` (CASCADE), `batiment` (SET_NULL), `nom` (100) |
| **Contrainte d'unicité** | `unique_together = ('site', 'batiment', 'nom')` |
| **Doublons réels en base** | **0** — 58 salles, aucun nom répété |
| **Usages de `salle_nom`** | `edts/services.py` (conflits, `_ressources_occupees`), `edts/api.py` (l. 246, 723, 769, 1016), `scolarite/cours_lmd_api.py` (l. 114), `presences/seances_edt_services.py`, `presences/geofence.py`, `statistiques/seances_edt_stats.py`, 2 seeds, 5 tests |
| **Décision** | **FK nullable `salle` ajoutée, `salle_nom` conservé** — transition progressive, sans perte |

```python
salle = models.ForeignKey(
    'formations.RefSalle', on_delete=models.PROTECT,
    null=True, blank=True, related_name='seances_edt', ...)
```

`on_delete=PROTECT` : une salle utilisée par une séance ne peut pas disparaître
(cf. la règle d'indisponibilité portée par `RefSalle.indisponible_du/au`).

### 16.4 Cohérence — aucun arbitrage deviné

**§ 7 — `seance.formateur` vs `affectation_pedagogique.enseignant`** : la règle métier
(*un remplaçant est-il autorisé ? la sous-traitance ?*) **n'est pas tranchée par le
dépôt**. `AffectationCreneau.clean()` ne contrôle que les semaines et la nature.
→ **Aucune contrainte introduite.** Les deux relations restent indépendantes, seul
comportement non inventé. Test `test_le_formateur_est_independant_de_l_affectation`.

**§ 8 — Année / Formation / Groupe** : `seance.formation` et `seance.groupe` sont des
FK **historiques**, antérieures à `AffectationPedagogique`. Les rendre obligatoires ou
identiques serait inventer une règle. → **Aucun couplage ajouté** ; le groupe reste
joignable via `affectation_pedagogique.groupe`. Test
`test_les_relations_independantes_restent_admissibles`.

### 16.5 Migration

**`edts/migrations/0004_affectationcreneau_salle.py`** — 1 `AddField` :

```sql
ALTER TABLE "edts_affectationcreneau"
  ADD COLUMN "salle_id" bigint NULL REFERENCES "formations_refsalle" ("id") ...;
CREATE INDEX "edts_affectationcreneau_salle_id_c44ddfc2" ON ... ("salle_id");
```

**SQL inspecté avant application** : aucun `DROP`, `DELETE`, `UPDATE`, ni `ALTER` de
donnée. Migration minimale, non destructive, réversible. **Appliquée** et vérifiée :
`salle_id bigint NULL` + FK vers `formations_refsalle(id)`, `salle_nom` intact (`not null`).

### 16.6 Tests

**Fichier étendu : `backend/edts/tests/test_raccordement_pedagogique.py`**
(9 tests L1 conservés + 21 tests L2, classe `ConsolidationSeanceLMDTests`)

| Test | Exigence | Résultat |
| :--- | :--- | :--- |
| `test_la_seance_retrouve_son_ecue` + 8 autres | **Test 5 — régression L1** (séance → ECUE, PROTECT) | ✅ |
| `test_le_formateur_utilise_la_fk_existante` | **Test 2 — formateur** | ✅ |
| `test_il_n_existe_qu_un_seul_champ_vers_le_formateur` | Test 2 — anti-doublon | ✅ |
| `test_le_formateur_est_independant_de_l_affectation` | Test 4 — § 7 sans règle inventée | ✅ |
| `test_la_seance_reference_la_salle_du_referentiel` | **Test 3 — `RefSalle`** | ✅ |
| `test_salle_nom_est_conserve_avec_la_fk` | Test 3 — transition | ✅ |
| `test_la_salle_est_optionnelle` | Test 3 — nullable | ✅ |
| `test_supprimer_une_salle_utilisee_est_protge` | Test 3 — PROTECT | ✅ |
| `test_une_salle_de_referentiel_n_expose_les_seances` | Test 3 — related_name | ✅ |
| `test_la_detection_de_conflit_de_salle_sert_toujours` | Test 4 — non-régression `services.py` | ✅ |
| `test_la_seance_expose_les_cotes_coherentes_de_la_chaine_lmd` | Test 4 — cohérence | ✅ |
| `test_les_relations_independantes_restent_admissibles` | Test 4 — § 8 | ✅ |
| `test_la_chaine_lmd_complete_est_atteignable` | **Architecture cible § 5** | ✅ |

| Suite | Résultat |
| :--- | :--- |
| `test edts.tests.test_raccordement_pedagogique` | **30/30 OK** |
| `test edts` | **56 OK** |
| `test formations` | **247 OK** (2 skipped préexistants) |
| `test presences statistiques scolarite` | **452 OK** |
| `manage.py check` | ✅ (warning `urls.W005` préexistant) |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `git diff --check` | ✅ propre |

**API (§ 19)** : `edts/api.py` **non modifié** — le contrat expose toujours `salle_nom`.
Exposer `salle` relève d'un lot API, pas de L2. `edts.tests.test_api` (14 tests) reste
vert : aucune régression de contrat.

### 16.7 Base — compteurs avant / après

| Objet | Avant | Après | Différence |
| :--- | :-- | :-- | :-- |
| `edts_affectationcreneau` | 0 | 0 | **0** |
| `scolarite_affectationpedagogique` | 0 | 0 | 0 |
| `scolarite_ue` / `ecue` / `maquette` | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| `formations_module` | 10 | 10 | 0 |
| `presences_pointage` | 34 | 34 | 0 |
| `authentication_user` | 22 | 22 | 0 |
| `formations_formateur` | 3 | 3 | 0 |
| `formations_refsalle` | 58 | 58 | 0 |

Aucune perte. Aucun `DROP`/`TRUNCATE`/`DELETE`/`flush`.

### 16.8 Git

| | |
| :--- | :--- |
| **Branche** | `main` (HEAD `89a1097a`) |
| **Modifié** | `backend/edts/models.py` (+24 : 12 L1 + 12 L2) — **seul fichier de code** |
| **Créé (migration)** | `backend/edts/migrations/0004_affectationcreneau_salle.py` |
| **Étendu (tests)** | `backend/edts/tests/test_raccordement_pedagogique.py` |
| **Modifié (doc)** | ce rapport |
| **`git diff --check`** | ✅ propre |
| **Commit** | **aucun** (conforme § 26) |

### 16.9 Arbitrages restant ouverts

| # | Question | Pourquoi L2 ne tranche pas |
| :-- | :--- | :--- |
| 1 | `seance.formateur` doit-il être **égal** à `affectation_pedagogique.enseignant` ? | Remplaçant / sous-traitance non tranchés — § 24 |
| 2 | `seance.groupe` doit-il être égal à `affectation_pedagogique.groupe` ? | FK historiques non dépréciées — § 24 |
| 3 | Faut-il exposer `salle` et `affectation_pedagogique` dans l'API EDT ? | Lot API dédié, pas L2 |
| 4 | Quand supprimer `salle_nom` ? | Après bascule des consommateurs de `services.py` |
| 5 | Faut-il déprécier `enseignant_id` / `enseignant_nom` ? | Hors périmètre L2 |

### 16.10 Périmètre explicitement NON traité

CPFAE / `Sygepcpfae` / `formations.Module` / `/modules` / point journalier ·
QR / badgeage / géolocalisation / présences / statistiques / pointage ·
`Promotion` / `Spécialité` / nomenclature officielle · frontend / GET-INJS ·
API EDT · `referentiel_injs/` · arbitrages A-2 à A-5.

---

## 17. LOT L3 — C4, RETRAIT DU MENU CPFAE — RÉALISÉ LE 26/09/2026 ✅

**Portée strictement navigationnelle.** Aucun modèle, aucune API, aucune donnée,
aucun rôle touchés.

### 17.1 Modification

`frontend/src/menu/arborescence.js` (**−9 lignes**) — retrait de l'entrée :

```js
- {
-   id: 'formations.cours',
-   libelle: 'Cours & modules (CPFAE — héritage)',
-   chemin: '/modules',
-   droit: { curp: [...], legacy: [['web', 'operationnel']] },
- },
```

**Remplacée par** `formations.cours_lmd` — « Cours (LMD) » → `/cours`, qui porte
déjà la chaîne Année → Formation → Parcours → UE → ECUE → Séance. Aucune
nouvelle entrée n'est créée : l'entrée LMD existait déjà juste au-dessus.

### 17.2 Ce qui est conservé (transition)

| Élément | Statut | Raison |
| :--- | :--- | :--- |
| **Route `/modules`** (`App.jsx` l. 220) | ✅ **conservée** | Retrait navigationnel, pas fonctionnel |
| **Page `<Modules />`** | ✅ conservée | Idem |
| `formations.Module`, `SessionModule` | ✅ conservés | § 10 : données supprimées seulement après bascule LMD |
| Rôles `CPFAE_ADMIN` / `CHEF_CPFAE_ADMIN` | ✅ inchangés | ~202 occurrences, hors périmètre |
| Point journalier CPFAE, `referentiel_injs/` | ✅ inchangés | hors périmètre |

### 17.3 Tests

`frontend/src/menu/arborescence.test.js` : `/modules` retiré de la liste de
non-régression (il ne doit plus être **une entrée de menu**, mais reste une route),
+ une suite `L3` de 5 tests :

| Test | Verrou |
| :--- | :--- |
| `l'entrée CPFAE « Cours & modules » a disparu du menu` | id `formations.cours` absent |
| `aucune entrée de menu ne pointe plus vers /modules` | plus de `chemin === '/modules'` |
| `aucun libellé CPFAE ne subsiste dans le menu` | plus de `/CPFAE/` dans les libellés |
| `l'entrée LMD de remplacement est bien présente` | `formations.cours_lmd` + `/cours` |
| `la route /modules reste déclarée dans App.jsx` | **garantit la conservation de la route** |

| Suite | Avant L3 | Après L3 |
| :--- | :-- | :-- |
| `arborescence.test.js` | 58 | **63** ✅ |
| Suite frontend complète | 1747 | **1751** ✅ (89 fichiers) |
| `npm run build` | — | ✅ **succès** (9,66 s) |

**Zéro régression** : le +4 correspond exactement aux 4 nouveaux tests L3.

### 17.4 Contrôles techniques

| Contrôle | Résultat |
| :--- | :--- |
| `npm run build` | ✅ |
| Suite frontend | ✅ 1751 / 1751 |
| `manage.py check` | ✅ (warning `urls.W005` préexistant) |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `git diff --check` | ✅ propre |
| Base | ✅ inchangée (creneau 0, module 10, pointage 34, users 22) |

### 17.5 Git

| | |
| :--- | :--- |
| **Modifié** | `frontend/src/menu/arborescence.js` (−9) · `arborescence.test.js` (+48) |
| **Base de données** | aucune |
| **Migrations** | aucune |
| **`git diff --check`** | ✅ propre |
| **Commit** | **aucun** |

### 17.6 Point d'attention

Le retrait porte sur **le menu uniquement**. Un utilisateur disposant d'un lien
direct, d'un favori ou d'une URL mémorisée `/modules` **continuer d'accéder à
l'écran CPFAE**. C'est voulu (§ 10 : bascule progressive), mais cela signifie que
l'héritage reste techniquement accessible : son retrait définitif suppose d'avoir
arbitré la **suppression de `formations.Module` et de ses 10 lignes**, donc le lot
L4+ et un arbitrage métier explicite.

---

---

## 18. LOT L4a — MIGRATION CONTRÔLÉE DU RBAC INJS-LMD — RÉALISÉ LE 26/09/2026 ✅

### 18.1 Origine historique et décision

`CPFAE_ADMIN` et `CHEF_CPFAE_ADMIN` étaient des identifiants hérités de
**Sygepcpfae**, l'application dont INJS-LMD est historiquement issu. Constat
important : **les libellés affichés étaient déjà en terminologie INJS**
(« INJS Admin », « Chef INJS Admin ») — seuls les **codes** portaient CPFAE.

L4a bascule les deux codes sur leurs identifiants INJS, **sans toucher à aucun
droit métier** :

| Ancien rôle | Nouveau rôle (canonique) | Libellé (inchangé) |
| :--- | :--- | :--- |
| `CPFAE_ADMIN` | `INJS_ADMIN` | « INJS Admin » |
| `CHEF_CPFAE_ADMIN` | `CHEF_INJS_ADMIN` | « Chef INJS Admin » |

### 18.2 Référentiel : 12 rôles, pas 14

La consigne L4a demandait « 14 rôles canoniques ». **Le dépôt en compte 12**, et
un renommage n'en crée aucun. Un document de ce nombre n'existe nulle part dans
le dépôt. **Arbitrage du commanditaire (26/09) : 12 → 12**, aucun rôle inventé.

`ADMIN · DIRECTION · CHEF_INJS_ADMIN · INJS_ADMIN · CHEF_SECRETARIAT ·
SECRETARIAT · FINANCE · ARCHIVE · ENCADRANT · SUPERVISEUR · FORMATEUR · AUDITEUR`

Toute évolution 12 → 14 exigera un lot distinct avec définition métier validée.

### 18.3 Compatibilité legacy (§ 7)

Architecture appliquée — **entrée legacy → normalisation → canonique**,
et non « 14 rôles actifs » :

```python
ROLES_LEGACY = {
    'CHEF_CPFAE_ADMIN': User.Role.CHEF_INJS_ADMIN,
    'CPFAE_ADMIN':      User.Role.INJS_ADMIN,
}
def normalize_role(valeur): ...
```

Les clés sont **ordonnées de la plus longue à la plus courte** : sans cela,
`ROLE_CHEF_CPFAE_ADMIN` se normaliserait à tort en `INJS_ADMIN` (piège du
suffixe). Ce bug a été détecté et corrigé avant migration.

### 18.4 Migrations appliquées (4)

| Migration | Rôle |
| :--- | :--- |
| `authentication.0021_alter_user_role` | `AlterField` des `choices` (12 rôles INJS) |
| `authentication.0022_migration_roles_injs` | `RunPython` : `User.role` + renommage des groupes |
| `authentication.0023_converger_groupes_roles_injs` | convergence des groupes (cf. § 18.5) |
| `parametres.0009` + `parametres.0010` | `AlterField` + migration des 40 listes JSON de rôles |

**Découverte majeure :** 40 paramètres stockaient `["ADMIN","CHEF_CPFAE_ADMIN",
"CPFAE_ADMIN", …]`. Sans migration de ces données, un compte `INJS_ADMIN`
aurait **perdu ses droits** sur les 40 paramètres. La migration `0010` convertit
les listes JSON en préservant l'ordre et les autres rôles.

### 18.5 Incident de migration — corrigé et documenté

Le renommage des groupes s'est d'abord mal exécuté : le filtre portait
`name='CPFAE_ADMIN'` alors que le nom stocké est `ROLE_CPFAE_ADMIN`. Pire, le
signal `post_migrate` → `ensure_role_groups()` recrée les groupes canoniques via
`get_or_create`, **produisant un doublon** (legacy + canonique, mêmes droits en
double).

L'annulation a été tentée puis **refusée par PostgreSQL** (unicité du nom de
groupe), ce qui a protégé les données sans aucune perte. La correction a été
apportée par la migration de convergence `0023` (fusion par `add()`, jamais
`set()`), idempotente.

**État final vérifié : 2 groupes, 141 permissions chacun, 2 et 1 utilisateurs.**

### 18.6 Garanties vérifiées par empreintes (§ 11)

| Groupe | Avant | Après |
| :--- | :--- | :--- |
| `ROLE_CPFAE_ADMIN` | 141 perms · md5 `448a0df9…` | `ROLE_INJS_ADMIN` : 141 · **md5 `448a0df9…`** |
| `ROLE_CHEF_CPFAE_ADMIN` | 141 perms · md5 `448a0df9…` | `ROLE_CHEF_INJS_ADMIN` : 141 · **md5 `448a0df9…`** |

Empreintes **strictement identiques** → aucune permission perdue, aucune ajoutée.
Comptage global identique : `users=22 · groups=12 · group_perms=1148 ·
user_groups=23`.

### 18.7 Tests

| Suite | Résultat |
| :--- | :--- |
| `test authentication` (incl. 19 tests L4a) | **226 OK** |
| `test roles.test.js` (frontend) | **202 OK** |
| Suite frontend complète | **1751 OK** (89 fichiers) |
| `manage.py check` | ✅ (warning `urls.W005` préexistant) |
| `makemigrations --check --dry-run` | ✅ **No changes detected** |
| `git diff --check` | ✅ propre |

Le test de caractérisation `test_01_referentiel_roles.py` reste **strict**
(égalité stricte des 12 rôles). `test_roles_injs_l4a.py` ajoute les 7 tests de
sécurité exigés, dont la vérification qu'aucun groupe canonique n'est vide et
que les deux groupes admin ont un périmètre identique.

### 18.8 Vestiges CPFAE conservés (§ 22)

| Emplacement | Catégorie | Pourquoi conservé |
| :--- | :--- | :--- |
| `role_groups.ROLES_LEGACY` | **LEGACY COMPATIBILITY** | normalisation d'entrée ; à retirer en L4b |
| 18 migrations historiques | **MIGRATION** | historiques non modifiables (interdiction explicite) |
| `test_roles_injs_l4a.py` | **TEST** | verrouille l'absence de régression du legacy |
| Ce rapport | **DOCUMENTATION** | traçabilité de la décision |

Aucune référence CPFAE ne subsiste dans le code métier, le frontend ou la base.

---

## 19. LOT L4b — VERROUILLAGE DU RBAC, FIN DE LA COMPATIBILITÉ CPFAE — 26/09/2026 ✅

### 19.1 Ce qui a été supprimé

| Élément | Sort |
| :--- | :--- |
| `role_groups.ROLES_LEGACY` | **supprimé** |
| `role_groups.normalize_role()` | **supprimé** |
| `ROLES_LEGACY_ADMIN` | **renommé** `ROLES_ADMIN_SYSTEME` (contenu identique) |

L'audit a établi que `normalize_role()` n'était appelé par **aucun code de
production** : la compatibilité était un contrat avec personne.

### 19.2 Découverte majeure — deux référentiels de rôles se chevauchaient

La contrainte DB a révélé un **défaut de conception préexistant** : des rôles
métier CURP (`PERSONNEL`, `AGENT_INSCRIPTIONS`, `DFRC`) étaient écrits dans
`User.role`, qui est le champ du **RBAC**.

```
User.role          ≠  AttributionRole
RBAC INJS-LMD         CURP / habilitations
12 rôles, OBLIGATOIRE rôles métier
```

**Le code de production était déjà protégé** (`comptes_admin.py:307` :
`if role_legacy not in User.Role.values: erreur ROLE_LEGACY_INCONNU`). Seules
des **fixtures de test** contournaient cette garde. Corrigées : `PERSONNEL` →
`SECRETARIAT` dans `_u5_fixtures.py` ; `DFRC` → `INJS_ADMIN` dans
`test_access.py` (l'alias `ROLE_ALIASES` de `statistiques.access` reste le
mécanisme de compatibilité **en lecture**).

### 19.3 Verrou en base

Migration **`authentication.0024_contrainte_role_canonique.py`** :

```sql
ALTER TABLE "authentication_user"
ADD CONSTRAINT "auth_user_role_canonique_l4b"
CHECK ("role" IN ('ADMIN','DIRECTION','CHEF_INJS_ADMIN','INJS_ADMIN',
  'CHEF_SECRETARIAT','SECRETARIAT','FINANCE','ARCHIVE','ENCADRANT',
  'SUPERVISEUR','FORMATEUR','AUDITEUR'));
```

> **Choix technique : `RunSQL` et non `AddConstraint`.** Sur SQLite, Django
> traduit `AddConstraint` en reconstruction de table (`CREATE TABLE new__… ;
> INSERT…SELECT ; DROP TABLE ; ALTER RENAME`) — un `DROP TABLE` déguisé sur
> `authentication_user`. Le `RunSQL` émet un simple DDL sur toutes les bases.

**`User.role = ''` est désormais refusé** : la chaîne vide n'est pas un rôle
RBAC. Deux tests de caractérisation qui documentaient cet état ont été réécrits
pour protéger le nouveau contrat.

### 19.4 Preuves (contrainte réellement active, testée hors ORM)

| Écriture SQL directe | Résultat |
| :--- | :--- |
| `role='CPFAE_ADMIN'` | `ERROR: violates check constraint` |
| `role='UNKNOWN_ROLE'` | `ERROR: violates check constraint` |
| `role=''` | `ERROR: violates check constraint` |
| `role='INJS_ADMIN'` (canonique) | acceptée |

Aucune ligne créée par les tentatives échouées (`0` vérifié).

### 19.5 Résultat

| Contrôle | Résultat |
| :--- | :--- |
| Tests L4a + contrainte DB | **21 PASS** |
| `test authentication`, `habilitations`, `statistiques` | ✅ |
| Suite backend complète | **1769 PASS** |
| Suite frontend (`roles` + `menu`) | **265 PASS** |
| `manage.py check` | ✅ |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| `git diff --check` | ✅ propre |

**Base** : `users=22 · groups=12 · group_perms=1148 · legacy=0 · role_vide=0`
— strictement identique à l'état d'avant L4b.

**Vestiges CPFAE restants** : 18 migrations historiques (non modifiables) et la
présente documentation. **Zéro** occurrence active dans modèles, services,
serializers, views, permissions, capabilities, frontend et configuration.

---

*Rapport initial produit le 26/09/2026 — audit préalable.*
*Lots **L1/L2/L3/L4a/L4b** réalisés le 26/09/2026 (§ 15 à § 19). Lots L5 et L6 non démarrés.*
*Créer une nomenclature, un rattachement automatique ou un modèle `Promotion` supplémentaire*
*exige toujours un arbitrage métier explicite (§ 25).*







