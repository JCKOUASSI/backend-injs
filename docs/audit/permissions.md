# Audit des permissions — module Utilisateurs (LOT 4)

> **Rapport d'audit consolidé** · Date : 2026-09-14 · Branche :
> `arena/01a0a19d-app-injslmd2026demo`
> **Portée** : vérification par tests que les droits sont **correctement bornés**
> (refus croisés du prompt §34) et que la chaîne d'administration fonctionne de
> bout en bout (scénario §35), puis consolidation documentaire.
> **Précédents** : [`docs/audits/2026-09-14-audit-module-utilisateurs.md`](../audits/2026-09-14-audit-module-utilisateurs.md)
> (phase 0, §11/§12 = plan LOT 4), [`docs/curp/05-architecture-completion-module-utilisateurs.md`](../curp/05-architecture-completion-module-utilisateurs.md) §5.
> **Lectures complémentaires** : [`IAM.md`](../architecture/IAM.md),
> [`RBAC.md`](../security/RBAC.md),
> [`administration/utilisateurs.md`](../administration/utilisateurs.md).

---

## 1. Méthode

1. **Lecture du référentiel** avant tout test : catalogues
   (`catalogue_roles.py`, `catalogue_matrice.py`, `catalogue_modules.py`),
   chargement (`charger_referentiel`), puis mesures chiffrées en `dry_run`
   (aucune écriture).
2. **Caractérisation par tests, jamais par modification** : chaque comportement
   observé est figé par un test nommé d'après le fait, y compris lorsqu'il
   s'agit d'un écart (le test documente l'état livré, il ne « corrige » pas le
   produit).
3. **Moteur en mode APPLICATION sur une base de test uniquement**
   (`@override_settings(HABILITATIONS_OBSERVATION=True,
   HABILITATIONS_APPLICATION=True)`), base jetable Django — le dépôt livré reste
   `APPLICATION=false`, donc aucun refus ne peut atteindre l'environnement
   démarré.
4. **Refus d'abord** : aucun geste n'est déclaré « terminé » sans son test de
   refus correspondant (règle du chantier). Les tests d'autorisation sont
   toujours accompagnés de leur symétrique interdit.
5. **Preuve de journalisation** : chaque refus appliqué est vérifié dans le
   journal chaîné (`ACCES_REFUSE`), et l'intégrité de la chaîne est contrôlée
   (`verifier_chaine() == []`).
6. **Garde-fous vérifiés** : abstention sur compte non gouverné, no-op total en
   mode OFF, inertie du défaut livré, fermeture de la console par drapeau même
   pour un super-utilisateur.
7. **Additif uniquement** : deux nouveaux fichiers de tests, quatre nouveaux
   documents, index mis à jour. **Aucun fichier de production modifié**, aucune
   migration, aucun `flush`/`drop`/`truncate`.

### 1.1 Outillage utilisé

| Outil | Usage |
|---|---|
| `charger_referentiel(dry_run=True)` | volumes et anomalies du référentiel sans écrire |
| `habilitations.services.moteur.est_autorise()` | décision motivée, appelée directement (pur) |
| `habilitations.permissions.ExigePermission.pour(code)` | refus DRF journalisé, exercé via `has_permission()` |
| `habilitations.services.journalisation.verifier_chaine()` | intégrité de la piste d'audit |
| `habilitations.services.observation.remettre_a_zero()` | isolation des compteurs entre tests |
| DRF `APIClient` + `force_authenticate` / `credentials` | appels authentifiés, rebasculement d'identité |
| `cache.clear()` | neutralisation du throttle de connexion entre tests |
| `manage.py inventaire_habilitation --comptes`, `habilitations_diag`, `observations_habilitations` | inventaires d'état |

Piège consigné : avec **DRF `APIClient`**, `post(chemin, dict,
content_type='application/json')` envoie le dictionnaire brut (→ 400 *JSON parse
error*). Il faut `format='json'`. Le client Django de `TestCase` tolère
l'ancienne forme, ce qui masque l'erreur.

---

## 2. Volumes mesurés (référentiel, 2026-09-14)

| Objet | Valeur |
|---|---|
| Rôles | **81** (35 A1 + 46 cibles J2), dont **22 sensibles** |
| Permissions atomiques | **1 155** sur **20 modules** |
| Liaisons matrice (rôle × permission) | **10 440** |
| Permissions critiques (double validation) | **15** |
| Verbes | 13 canoniques → **31 actions** au modèle |
| Types de périmètre | **12** |
| Statuts de compte / canaux | **6** / 3 |
| Types d'événements du journal | **37** |
| Couples d'incompatibilité | **5** |
| Cases matrice | A2 = 35 lignes ; J2 = 46 rôles cibles + 12 lignes provisoires |
| Anomalies de chargement | **0** (rôle sans permission, permission orpheline, rôle indisponible) ; rechargement idempotent |

---

## 3. Résultats — tests de refus croisés (prompt §34)

**Fichier** : `backend/habilitations/tests/test_lot4_refus_croises.py`
**Résultat** : **51 tests, 51 OK** (mode APPLICATION sur base de test).

### 3.1 Enseignant (N2, MODULE_ECUE, canal MOBILE) — 8 tests

| Fait vérifié | Test |
|---|---|
| Autorisé sur **son** module/ECUE | `test_01` |
| **Refusé** sur le module d'un collègue (cible hors périmètre) | `test_02`, symétrie `test_03` |
| N'administre pas la fiche d'un collègue | `test_04` |
| Ne valide pas les notes (`evaluations.note.valider`) | `test_05` |
| Canal MOBILE imposé par le rôle → web refusé (`CANAL_IMPOSE_PAR_ROLE`) | `test_06` |
| Refus fonctionnel **tracé au journal** `ACCES_REFUSE` | `test_07` |
| Un accès autorisé ne produit **aucun** refus journalisé | `test_08` |

### 3.2 Chef de département (N3, périmètre DIRECTION) — 8 tests

| Fait vérifié | Test |
|---|---|
| Autorisé dans sa direction | `test_01` |
| Refusé dans la direction d'un autre chef | `test_02`, symétrie `test_04` |
| Refusé sur un département d'une autre direction | `test_03` |
| Couverture hiérarchique **par résolveur injecté** (département rattaché à la direction) | `test_05` |
| Ne valide pas un jury (`jurys.pv.signer`) | `test_06` |
| Ne crée pas de rôle (`administration.role.creer`) | `test_07` |
| Refus tracé au journal pour le compte concerné | `test_08` |

### 3.3 Étudiant (N1, PROPRE_COMPTE, canal MOBILE) — 8 tests

| Fait vérifié | Test |
|---|---|
| Consulte **son** dossier | `test_01` |
| Ne consulte pas le dossier d'un autre étudiant | `test_02`, symétrie `test_03` |
| Ne modifie pas son dossier | `test_04` |
| Ne force aucun émargement (`presences.emargement.forcer`) | `test_05` |
| Peut déposer un justificatif sur son propre compte | `test_06` |
| Un périmètre `PROPRE_COMPTE` **seul** ne couvre aucune cible nommée (sémantique documentée) | `test_07` |
| Canal WEB refusé à un compte mobile | `test_08` |

### 3.4 Agent de scolarité vs administrateur de rôles — 9 tests

| Fait vérifié | Test |
|---|---|
| Ne crée pas de rôle, ne valide pas d'attribution, n'administre pas la politique | `test_01`–`test_03` |
| Frontière en **lecture seule** sur le module `administration` | `test_04` |
| Garde son périmètre de scolarité ; **refusé hors de son secrétariat** | `test_05`, `test_06` |
| Console des comptes **refusée même drapeau ouvert** (`ExigeDrapeauAdmin`) | `test_07` |
| Un administrateur accède à la console dans le même contexte (contrôle croisé) | `test_08` |
| Refus produit par la **permission DRF** sur un acte d'administration | `test_09` |

### 3.5 Administrateur SI ≠ actes métier sensibles — 8 tests

| Fait vérifié | Test |
|---|---|
| Les 6 rôles du domaine TECHNIQUE (`SYSADMIN`, `DB_ADMIN`, `NETWORK_ADMIN`, `SECURITY_ADMIN`, `API_MANAGER`, `SUPPORT_IT`) ne portent **aucune** permission critique au catalogue | `test_01` |
| Ces rôles sont **hors de tout module métier** (candidatures, scolarité, évaluations, jurys, diplomation, finances…) | `test_02` |
| `SYSADMIN` refusé sur un paiement ; garde la main sur `parametres` | `test_03`, `test_04` |
| Rôle sensible sans seconde signature → refus ; sans MFA actif → refus | `test_05`, `test_06` |
| `DB_ADMIN` ne touche pas aux dossiers étudiants | `test_07` |
| **Écart J2-1 caractérisé** : la ligne A2 d'`ADMIN_SYSTEME` (`N4` sur les 15 modules) lui confère des actes métier critiques — contenu par les contrepoids (rôle sensible, MFA, double validation, motif, journal), **à arbitrer en atelier** | `test_08` |

### 3.6 Écart de couverture « objet métier » — 4 tests

| Fait vérifié | Test |
|---|---|
| Une cible **dict** `{type, object_id}` est couverte ; la **même cible en objet** ne l'est pas | `test_01` |
| Cause racine : `_decrire_perimetre()` n'expose pas `content_type_id` | `test_02` |
| Le refus sur objet est **quand même tracé** au journal | `test_03` |
| Un **résolveur injecté** par le contexte lève l'écart **sans correctif de production** | `test_04` |

### 3.7 Garde-fous — 6 tests

Compte non gouverné → **abstention** (pas un refus) ; compte suspendu → refus ;
anonyme → refus ; mode OFF → **no-op total** ; les refus ci-dessus sont bien
produits en mode APPLICATION (contrôle de non-régression du mode) ; **le défaut
livré est inerte**.

---

## 4. Résultats — scénario de bout en bout (prompt §35)

**Fichier** : `backend/habilitations/tests/test_lot4_e2e_scenario.py`
**Résultat** : **9 tests, 9 OK** (~7 s).

### 4.1 `test_01_scenario_complet_du_prompt_35` — 11 étapes chaînées

| # | Étape | Vérification |
|---|---|---|
| 1 | Création d'un compte par la console | `POST /comptes/` → 201, personne + compte + attribution, matricule `PERS-…`, journal `COMPTE_CREE` |
| 2 | Attribution du rôle `CHEF_DEPARTEMENT` (N3) | rôle actif, niveau effectif, `ROLE_ATTRIBUE` au journal |
| 3 | Création de l'organisation | Direction « DG » (+ « DAE »), département rattaché |
| 4 | Pose du périmètre DIRECTION | périmètre polymorphe lié à l'attribution |
| 5 | Connexion du nouveau compte | JWT + cookie refresh, `last_login` **et** `derniere_connexion` alimentés, `AuditLog USER_LOGIN` |
| 6 | Menu et capacités projetées | `GET /api/auth/capabilities/` → `habilitations.gouverne=true`, clé `habilitations` purement descriptive |
| 7 | **Accès autorisé** | `scolarite.groupe.modifier` sur la direction DG → autorisé |
| 8 | **Accès interdit** | même code sur une **autre** direction → refus `CIBLE_HORS_PERIMETRE` ; `jurys.pv.signer` → refus (niveau) |
| 9 | Refus par la permission DRF | `ExigePermission` → 403 motivé + `ACCES_REFUSE` journalisé |
| 10 | Modification du rôle + différentiel | simulation (gagnées/perdues/conservées) → `PATCH /modifier/` avec `differentiel_accepte` + `motif` |
| 11 | Recalcul + audit | perte de `scolarite.groupe.modifier`, conservation de `scolarite.dossier_etudiant.consulter` ; `verifier_chaine() == []` |

### 4.2 Étapes isolées (rejouables séparément)

| Test | Fait |
|---|---|
| `test_02` | Menu et projections pour le compte connecté |
| `test_03` | Recalcul après révocation du rôle |
| `test_04` | Piste d'audit complète **et intègre** (chaîne SHA-256) |
| `test_05` | Journal filtrable par compte et par type d'événement |
| `test_06` | Console fermée par drapeau, **même pour l'administrateur** |
| `test_07` | Création refusée sans motif ou avec rôle inconnu — **atomicité** : aucun `User` fantôme |
| `test_08` | Doublon d'identifiant → 409 `IDENTIFIANT_EXISTANT` |
| `test_09` | Suspension du compte → `is_active=False`, accès coupés (`COMPTE_SUSPENDU`) |

---

## 5. Écarts numérotés

| ID | Gravité | Écart | Preuve | Traitement |
|---|---|---|---|---|
| **L4-01** | **P0 (bloquant LOT 5)** | `moteur._decrire_perimetre()` omet `content_type_id` → une cible **objet métier** n'est jamais couverte au contrôle 9 (`CIBLE_HORS_PERIMETRE`). Seuls dict, `INJS_ENTIER`, la règle `SECRETARIAT` et un résolveur injecté fonctionnent. Conséquence : `has_object_permission` (donc tout branchement sur `get_object()`) refuserait tout en mode APPLICATION. | `test_lot4_refus_croises.py::CouvertureObjetEcartTests` (4 tests) | Correctif **additif d'une ligne** (exposer `content_type_id`) + tests de non-régression, **au LOT 5 sur feu vert**. Contournement déjà démontré : résolveur injecté (`contexte={'couverture': …}`). |
| **L4-02** | P1 | La console ne pose que des périmètres `SECRETARIAT` (`perimetres_secretariats`) ; tout autre type passe par l'admin Django. | `test_lot4_e2e_scenario.py` étape 4 (périmètre posé par ORM) | Ouvrir le sélecteur de périmètre dans l'assistant (LOT 5), additif. |
| **L4-03** | P2 | Une connexion réussie trace `presences.AuditLog` (`USER_LOGIN`) et les horodatages, mais n'émet pas d'événement `CONNEXION` au journal d'habilitation (type prévu au modèle, jamais émis). | `test_lot4_e2e_scenario.py::test_04` | Arbitrer : double piste assumée ou émission additive de `CONNEXION`. |
| **L4-04** | P2 | `journalisation._resoudre_cible()` exige une **instance** de modèle et lève sur un dict : un refus portant une cible dict n'est pas journalisé avec sa cible. | observations LOT 4 ; les tests de journal utilisent des instances | Rendre `_resoudre_cible` tolérant au format dict du contrat d'API (additif). |
| **J2-1** | Décision humaine | Ligne A2 d'`ADMIN_SYSTEME` = `N4` sur les 15 modules ⇒ actes métier critiques (`jurys.pv.signer`, `diplomation.diplome.valider`, `finances_etud.paiement.valider`) alors que le catalogue dit « sans intervenir sur les décisions métier ». | `test_lot4_refus_croises.py::AdminSiTests::test_08` | **Atelier J2** : restreindre la ligne ou formaliser la politique de contournement. Contenus aujourd'hui par rôle sensible + MFA + double validation + motif + journal. |
| **J2-2** | Décision humaine | `CHEF_DEPARTEMENT` reçoit `administration: N2` ⇒ création/modification de comptes et d'attributions **dans son périmètre**. | `…::ChefDepartementCroiseTests::test_07` | Atelier J2 : confirmer ou abaisser à N1. |
| **J2-3** | Décision humaine | Rôles SI portant un niveau minimal sur `parametres` (placeholder documenté). 0 acte métier sensible, 0 module métier — vérifié. | `…::AdminSiTests::test_01/02` | Atelier J2 : valider le périmètre technique. |
| **J2-4** | Décision humaine | Aucun type de périmètre `DEPARTEMENT` ; `DIRECTION` sert de périmètre par défaut aux rôles de département. Résolveurs hiérarchiques non livrés. | `…::ChefDepartementCroiseTests::test_05` | LOT 5 : ajouter le type + résolveurs (additif), ou assumer `DIRECTION`. |
| **L4-05** | Environnement | Suite backend complète : **1 556 tests, 4 erreurs, 5 ignorés**. Les 4 erreurs sont toutes `dashboard.tests.PublicBadgePage{Enabled,Disabled}Test` et proviennent du `CompressedManifestStaticFilesStorage` sans manifeste (`Missing staticfiles manifest entry for 'img/logo-injs.png'`) — `collectstatic` n'avait pas été joué dans le bac à sable. **Après `collectstatic`, ces 4 tests passent (OK)** : cause d'environnement, sans lien avec le LOT 4. Les 5 ignorés comprennent les 2 tests de déclencheurs d'immuabilité PostgreSQL. | `/tmp/tests_backend_lot4.log` (525 s) ; rejeu ciblé `manage.py test dashboard.tests.PublicBadgePage*` → OK après `collectstatic` | Ajouter `collectstatic` au préalable d'exécution de la suite (CI déjà pourvue) ; rejouer sous PostgreSQL en intégration ; **jamais** masquer l'écart. |
| **L4-06** | Documentation | Homonymie : `flag.lot01_…lot12_…` (lots de construction du produit) ≠ « LOT 1 → LOT 5 » (lots du module Utilisateurs). | seed `parametres/flags.py` vs plan CURP §7 | Clarifié dans [`IAM.md`](../architecture/IAM.md) §13 ; renommage **non** proposé (additif, risque de casse). |

---

## 6. Couverture de la suite

| Suite | Tests | État |
|---|---|---|
| `habilitations` (module complet, U1–U5 + LOT 1–3 + **LOT 4**) | **374** (2 ignorés : déclencheurs PostgreSQL) | **OK** (~240 s) |
| — dont `test_lot4_refus_croises.py` | **51** | OK |
| — dont `test_lot4_e2e_scenario.py` | **9** | OK |
| `authentication` (caractérisation U0 + LOT 2 + socle/capacités/throttles) | **207** | **OK** (92 s) |
| **Suite backend complète** (20 apps) | **1 556** | 4 erreurs d'environnement (manifeste `staticfiles` absent) → **OK après `collectstatic`** ; 5 ignorés (dont déclencheurs PostgreSQL) — 525 s |

Rejeu :

```bash
cd backend
./.venv/bin/python manage.py collectstatic --noinput                      # préalable à la suite complète (L4-05)
./.venv/bin/python manage.py test habilitations -v 1                      # 374 tests (~240 s)
./.venv/bin/python manage.py test habilitations.tests.test_lot4_refus_croises -v 2   # 51
./.venv/bin/python manage.py test habilitations.tests.test_lot4_e2e_scenario -v 2    #  9
./.venv/bin/python manage.py test authentication -v 1                     # 207 tests
./.venv/bin/python manage.py test -v 1                                    # 1 556 tests (~525 s)
```

Environnement de mesure : Python 3.11, Django 5.1.4, SQLite (`USE_SQLITE=1`),
bac à sable sans PostgreSQL ni Redis. Les tests de déclencheurs d'immuabilité du
journal sont **ignorés** dans cet environnement et doivent être rejoués sous
PostgreSQL en intégration.

---

## 7. Constat global

**Le bornage des droits est vérifié et tient** : aucun des accès croisés du
prompt §34 n'est accordé (enseignant ↔ enseignant, chef ↔ chef, étudiant ↔
étudiant, agent scolarité ↔ administration des rôles, administrateur SI ↔ actes
métier sensibles), les refus sont motivés par des **codes stables**, journalisés
et produits **uniquement** en mode APPLICATION ; en mode OFF ou avec le défaut
livré, le dispositif est strictement inerte. La chaîne d'administration de bout
en bout (création → rôles → organisation → périmètre → connexion → projection →
accès → modification → recalcul → audit) fonctionne et laisse une piste
d'audit **intègre**.

**Le dispositif n'est pas encore branché sur les vues métier** : `ExigePermission`
n'est posée sur aucune vue (0 usage), conformément à la règle « observation
avant refus ». L'autorisation réellement appliquée reste le dispositif legacy
(`ROLE_POLICY` + classes DRF), inchangé.

**Un préalable technique unique** conditionne le branchement : la résolution des
cibles objet (**L4-01**), correctif additif d'une ligne, plus les résolveurs
hiérarchiques (J2-4).

---

## 8. Plan de remédiation (LOT 5) — propositions, aucune exécution sans feu vert

| Ordre | Action | Type | Prérequis |
|---|---|---|---|
| 1 | Exposer `content_type_id` dans `_decrire_perimetre` + tests de non-régression (L4-01) | additif, 1 ligne | — |
| 2 | Rendre `_resoudre_cible` tolérant aux cibles dict (L4-04) | additif | — |
| 3 | Résolveurs hiérarchiques Direction→Département→Service, Formation→Parcours→Groupe→ECUE, injectables par contexte (J2-4) | additif | 1 |
| 4 | Sélecteur de périmètre complet dans l'assistant de création/modification (L4-02) | additif (UI + API) | 3 |
| 5 | Atelier J2 : arbitrer J2-1, J2-2, J2-3 et le type `DEPARTEMENT` | décision humaine | — |
| 6 | Rattachement additif des comptes legacy à un profil CURP (`CORRESPONDANCE_LEGACY`) | additif | 5 |
| 7 | Mode OBSERVATION mesuré sur les vues réelles, synthèse des écarts | mesure | 6 |
| 8 | Branchement `ExigePermission` vue par vue, puis APPLICATION progressive avec repli immédiat | bascule | 7 |
| 9 | Émission de l'événement `CONNEXION` au journal d'habilitation (L4-03) | additif | arbitrage |
| 10 | Rejeu complet sous PostgreSQL (déclencheurs d'immuabilité, baseline référentiels — L4-05) | environnement | — |

---

## 9. Traçabilité de cet audit

| Élément | Emplacement |
|---|---|
| Tests de refus croisés (§34) | `backend/habilitations/tests/test_lot4_refus_croises.py` |
| Tests de bout en bout (§35) | `backend/habilitations/tests/test_lot4_e2e_scenario.py` |
| Socle de fixtures partagé | `backend/habilitations/tests/_u5_fixtures.py` |
| Architecture consolidée | `docs/architecture/IAM.md` |
| Règles de droits consolidées | `docs/security/RBAC.md` |
| Guide d'exploitation | `docs/administration/utilisateurs.md` |
| Audit de phase 0 (antérieur) | `docs/audits/2026-09-14-audit-module-utilisateurs.md` |
| Plan du chantier | `docs/curp/05-architecture-completion-module-utilisateurs.md` |
| Notes de conception | `docs/curp/00-…05-*.md`, `docs/curp/U1…U6-note-conception.md` |
