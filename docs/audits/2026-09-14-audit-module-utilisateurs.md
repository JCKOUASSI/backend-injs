# Phase 0 — Audit du module Utilisateurs / Comptes / Rôles / Permissions / Périmètres

> **Date** : 2026-09-14 · **Périmètre** : dépôt `JCKOUASSI/app-injslmd2026demo` (commit `a885bfc`)
> **Méthode** : inspection intégrale du code (backend 20 apps, frontend React/Vite, middlewares,
> migrations, tests, fixtures, docs). **Aucune modification de code** n'a été effectuée.
> **Conventions** : les chiffres sont mesurés sur le dépôt réel ; les documents CURP
> (`docs/curp/`) sont cités comme références.

---

## 1. Constat principal

**Le module « Utilisateurs / Comptes / Rôles / Permissions / Périmètres » existe déjà et est
très avancé.** Il a été construit en unités U0→U5 par le chantier **CURP-INJS**
(Comptes Utilisateurs et Référentiels de Permissions). Deux systèmes coexistent :

| Système | Nature | Statut |
|---|---|---|
| **Legacy** : `authentication.User.role` (12 rôles) + groupes Django `ROLE_*` + `ROLE_POLICY` + permissions Django (10 custom) | RBAC « à l'ancienne », source de vérité en vigueur sur les vues métier | **En production** — c'est lui qui applique les contrôles DRF aujourd'hui |
| **CURP** (app `habilitations`) : `CompteUtilisateur` + `RoleMetier` (35) + `PermissionMetier` (1 155) + `Perimetre` + `AttributionRole` + `PermissionAttribuee` + `DelegationHabilitation` + journal immuable chaîné + moteur `est_autorise()` | RBAC cible, complète en données et en écrans | **Construit, alimenté, écrané — mais le moteur est ÉTEINT par défaut** (mode OFF) et `ExigePermission` n'est branché sur **aucune** vue métier (0 usage) |

Le chantier est documenté unité par unité (`docs/curp/U0→U5`) avec une suite prévue :
**U6** (MFA réel, verrouillage réel, sessions/appareils), **U7** (campagnes de revue,
tableau de bord), **U8** (migration des comptes legacy et bascule du moteur en APPLICATION).

> **Conséquence pour la demande** : la phase « construire un module IAM central » est
> largement faite. Le travail utile consiste à (a) combler les écarts résiduels du modèle
> (organisation hiérarchique, photo, MFA, verrouillage effectif), (b) compléter les écrans
> manquant, (c) documenter et tester les refus d'accès, et (d) préparer la bascule
> (U8). Créer un deuxième système parallèle serait un doublon fonctionnel interdit par
> la règle d'audit (§1 du prompt maître).

---

## 2. Architecture actuelle

### 2.1 Chaîne d'identité (deux couches superposées)

```
User (authentication.User, AbstractUser)          ← identité d'authentification
 ├─ role: CharField 12 valeurs (dénorm. du rôle principal)
 ├─ matricule, telephone, organisation, grade, secretariat FK (formations.Secretariat)
 ├─ must_change_password
 ├─ groupes Django ROLE_*  ← source de vérité legacy des rôles (synchronisés par signaux)
 └─ 10 permissions Django custom (User.Meta.permissions : access_web, mutate_users,
    finance_module, global_scope, list_participants, manage_notes, …)

Personne (habilitations.Personne)                  ← identité physique
CompteUtilisateur (habilitations.CompteUtilisateur) ← profil d'habilitation (1:1 User)
 ├─ statut : INVITE | ACTIF | SUSPENDU | DESACTIVE | VERROUILLE | EXPIRE   (machine A5)
 ├─ canal : WEB | MOBILE | LES_DEUX
 ├─ date_expiration, date_verrouillage, echecs_consecutifs, mfa_actif (flag, non implémenté)
 ├─ attributions → AttributionRole (rôle + niveau effectif N0–N4 + périmètres + date_debut/fin + motif)
 ├─ permission_attribuees → PermissionAttribuee (permissions explicites/exceptionnelles)
 └─ délégations, dérogations, notifications, propositions (file humaine U5)

RoleMetier (35 codes, catalogue A1) × PermissionMetier (1 155 codes A3,
    convention <module>.<ressource>.<action>, 13 verbes canoniques)
    reliés par la matrice niveaux A2 (6 962 liaisons) + 5 couples d'incompatibilité
    (séparation des tâches)
Perimetre : type polymorphe (ContentType) — 12 types : INJS_ENTIER, DIRECTION, SERVICE,
    SECRETARIAT, SITE, FORMATION, PARCOURS, NIVEAU, GROUPE, MODULE_ECUE, ETUDIANT, PROPRE_COMPTE
```

### 2.2 Authentification

- **JWT (SimpleJWT)** : `POST /api/auth/login/` (throttlé `LoginRateThrottle`),
  refresh en cookie HttpOnly + rotation, `FlexibleJWTAuthentication` (Bearer → X-JWT-Access → `?access_token=`).
- **Session Django** en complément (admin, `SessionAuthentication` DRF).
- **Contrôles login** : partition web/mobile (`ALLOWED_WEB_ROLES` / `MOBILE_ONLY_ROLES`),
  verrouillage **d'appareil** (device binding) pour AUDITEUR/FORMATEUR,
  `must_change_password` → écran forcé (`/forced-password-change`).
- **Middlewares de sécurité** : Security, CSRF, XFrameOptions, CORS, WhiteNoise,
  + middlewares démo d'aperçu (`DemoAdminAutoLoginMiddleware`, overlay `arena/*` sandbox uniquement).
- **Politique de sécurité** : `PolitiqueSecurite` (singleton) porte longueur/min MDP,
  historique, `nombre_echecs_avant_verrouillage=5`, `duree_verrouillage_minutes=15`,
  inactivité session/suspension, durée max dérogation… — **stockée et historisée, mais
  non appliquée à la connexion** (U6 prévue) : **pas de verrouillage de compte réel**,
  **pas de MFA réel** (`mfa_actif` est un flag dormant), **`last_login` non alimenté**
  par les connexions JWT (écart E11).

### 2.3 Autorisation

- **En vigueur (legacy)** : `ROLE_POLICY` (`authentication/role_groups.py`, ~530 lignes)
  mappe chaque rôle → permissions Django ; DRF via classes (`IsDFRC`, `IsEncadrant`,
  `IsSecretariatOrDFRC`, `CanListParticipants`…) posées vue par vue. Backend seul
  autorité ; `IsAuthenticated` par défaut (settings `REST_FRAMEWORK`).
- **Cible (CURP)** : moteur `habilitations.services.moteur.est_autorise(user,
  code_permission, canal, cible, contexte)` — pure, journalisable, évaluant
  rôles/niveaux/périmètres/dérogations/délégations. Mode piloté par variables
  `HABILITATIONS_OBSERVATION` / `HABILITATIONS_APPLICATION` (défaut **OFF**).
  Permission DRF `ExigePermission.pour('module.ressource.action')` prête à l'emploi —
  **0 vue métier l'utilise actuellement**.
- **Projection frontend** : `GET /api/auth/capabilities/` (`compute_capabilities`)
  renvoie `{module: [actions]}` ; le menu React est **déjà dynamique** (`peut(user,
  module, action)`), les routes sont gardées par `ProtectedRoute capacite={...}`.

---

## 3. Modèles actuels (inventaire)

| App | Modèles | Migrations | Fichiers de test |
|---|---:|---:|---:|
| authentication | User (custom) + DeviceBinding + autres | — | — |
| **habilitations** | **13** : Personne, CompteUtilisateur, RoleMetier, PermissionMetier, Periméré, AttributionRole, PermissionAttribuee, DelegationHabilitation, PropositionProvisionnement, ExecutionImport, NotificationHabilitation, PolitiqueSecurite, JournalHabilitation | 8 | 18 |
| formations | 27 (dont **Secretariat**, RefTypeSecretariat, **RefSite**) | 92 | 27 |
| scolarite | 21 | 14 | 13 |
| administrations | 5 | 1 | 1 |
| admissions | 15 | 2 | 3 |
| ressources_humaines | 6 (dont **Service**, Agent) | 1 | 1 |
| jurys | 6 (SessionJury, MembreJury…) | 2 | 2 |
| parametres | 2 (Parametre = feature flags) | 7 | 3 |
| presences | 5 (dont **AuditLog** générique) | 26 | 4 |
| statistiques / patrimoine / presences / graduation / stages / finances_etudiantes / edts / equivalences / suiviEvaluation / referentiels / core | 2–9 chacun | 1–12 | 0–11 |

**Total** : 20 apps, 133 modèles, ~190 migrations, 114 fichiers de test backend
(≈ 943 méthodes), **70 fichiers de test frontend** (Vitest).

### Relations utilisateur ↔ entités métier (FK vers `AUTH_USER_MODEL`)

formations (17 — superviseur/encadrant/formateur), jurys (7 — MembreJury,
creee_par…), administrations (7), statistiques (6), presences (6), patrimoine (6),
graduation (6), scolarite (3), edts (3), equivalences (3), suiviEvaluation (2),
parametres (3), stages, referentiels, core… **Aucune FK directe User→Département ni
User→Service** : le rattachement organisationnel existant est `User.secretariat`
(1:1 secrétariat) ; les autres rattachements passent par les entités métier
(`Formateur`, `Agent`, `Participant`, `DossierEtudiant`, `MembreJury`).

---

## 4. Rôles actuels

### 4.1 Legacy (12, en vigueur)

`ADMIN, DIRECTION, CHEF_CPFAE_ADMIN, CPFAE_ADMIN, CHEF_SECRETARIAT, SECRETARIAT,
FINANCE, ARCHIVE, ENCADRANT, SUPERVISEUR, FORMATEUR (mobile-only), AUDITEUR (mobile-only)`.
10 rôles web + 2 mobile-only (partition sans recouvrement) ; 5 combinaisons
multi-rôles autorisées. Chacun a un groupe Django `ROLE_*` + permissions `ROLE_POLICY`.

### 4.2 Cible (35, chargés en base — catalogue A1, idempotent `charger_referentiel`)

`ADMIN_SYSTEME, DIRECTION_GENERALE, DIRECTION_ETUDES, SCOLARITE, RESPONSABLE_PEDAGOGIQUE,
AGENT_CANDIDATURE, AGENT_CONTROLE_DOSSIERS, RESPONSABLE_CONCOURS, AGENT_ADMISSIONS,
AGENT_INSCRIPTIONS, GESTIONNAIRE_ETUDIANTS, RESPONSABLE_FORMATION, GESTIONNAIRE_GROUPES,
GESTIONNAIRE_COURS, GESTIONNAIRE_MAQUETTES, ENSEIGNANT, RESPONSABLE_UE_ECUE,
GESTIONNAIRE_CHARGES, GESTIONNAIRE_NOTES, MEMBRE_JURY, RESPONSABLE_JURY,
RESPONSABLE_GRADUATION, RESPONSABLE_DIPLOMATION, GESTIONNAIRE_FINANCES_ETUD,
VALIDATEUR_FINANCIER, GESTIONNAIRE_VACATIONS, GESTIONNAIRE_STAGES, GESTIONNAIRE_RH,
GESTIONNAIRE_PATRIMOINE, GESTIONNAIRE_ESPACES, GESTIONNAIRE_COURRIERS, ARCHIVISTE,
ETUDIANT, CANDIDAT, CONSULTATION`.

Mesuré en base : **35 rôles · 1 155 permissions · 6 962 liaisons matrice · 5 couples
d'incompatibilité** (séparation des tâches) · 0 permission orpheline · 0 rôle sans permission.
Matrice de travail `docs/CURP_INJS_MATRICE.md` (rôle × 20 modules, niveaux N0–N4),
statut provisoire en attente de validation J2.

**Correspondance avec la liste cible du prompt maître (§7)** : la plupart des rôles
demandés existent sous code INJS (`JURY_MEMBER`→`MEMBRE_JURY`, `JURY_PRESIDENT`→
`RESPONSABLE_JURY`, `SCOLARITY_MANAGER`→`SCOLARITE`, `ETUDIANT_MANAGER`→
`GESTIONNAIRE_ETUDIANTS`, `GROUPE_MANAGER`→`GESTIONNAIRE_GROUPES`, `NOTE_MANAGER`→
`GESTIONNAIRE_NOTES`, `JURY_SECRETARY`≈`MEMBRE_JURY`+fonction `SECRETAIRE` de
`MembreJury.fonction`…). **Absents du catalogue** : `VACATAIRE`, `CONCOURS_CORRECTEUR`,
`CONCOURS_SURVEILLANT`, `TUTEUR_ENTREPRISE`, `CHERCHEUR`, `RECHERCHE_MANAGER`,
`BOURSE_MANAGER`, `COMPTABLE`, `CAISSIER`, `RECOUVREMENT`, `CONTROLEUR_FINANCIER`,
`PAIE_MANAGER`, `ACHATS_MANAGER`, `LOGISTICIEN`, `MAINTENANCE`, `GED_MANAGER`,
`COMMUNICATION_MANAGER`, `SUPPORT_IT`, `SYSADMIN`, `NETWORK_ADMIN`, `DB_ADMIN`,
`SECURITY_ADMIN`, `DATA_ANALYST`, `API_MANAGER`, `LECTEUR`, `AUDIT_READONLY`,
`SIGNATAIRE`, `SECRETARIAT_GENERAL`, `QUALITE_MANAGER`, `PLANIFICATION_MANAGER`,
`STATISTICIEN`, `CHEF_DEPARTEMENT`, `RESPONSABLE_PARCOURS`. → Les rôles manquants se
travaillent **en données du référentiel** (catalogue + matrice), pas en code.

---

## 5. Permissions actuelles

Trois couches distinctes (ne pas confondre) :

1. **Permissions Django** (10 custom sur `User.Meta` + permissions modèles) — portées
   par les groupes `ROLE_*`, contrôlées par `has_perm` et les classes DRF legacy.
2. **Permissions métier CURP** (`PermissionMetier`, 1 155) — convention
   `<module>.<ressource>.<action>` conforme à la demande (`formations.formation.consulter`,
   `evaluations.note.valider`…) ; 13 verbes canoniques + verbes métier (31 valeurs
   `PermissionMetier.Action`) ; niveaux minima par verbe (N0 consultation → N4
   administration) ; critique par permission (surcharge `NIVEAU_PERMISSION_SURCHARGE`).
3. **Permissions explicites et restrictions** (`PermissionAttribuee`) + **dérogations**
   (durée bornée, révocables) + **délégations** (bornées, sans re-délégation, action
   tracée) — le calcul « rôles + explicites − restrictions » est dans le moteur.

**Endpoints de calcul des droits** : `GET /api/auth/capabilities/` (projection menu),
`GET /api/habilitations/mes-acces/`, `POST /api/habilitations/evaluer/`.

---

## 6. Écrans frontend actuels

### 6.1 Parc « Utilisateurs » legacy (en ligne)

- `frontend/src/pages/Users.jsx` : tableau (nom, identifiant, matricule, email,
  rôle/secrétariat, téléphone, actif, actions) + recherche/filtres/pagination +
  création/modification ; API `GET/POST /api/auth/users/`, `GET/PATCH/DELETE
  /api/auth/users/{id}/` (permis `IsSecretariatOrDFRC`, hiérarchie de création
  `get_creatable_roles`).
- `Login.jsx`, `ForcedPasswordChange.jsx`, `Profile` (`/profile`), `MonEspace`
  (`/mon-espace`, canal étudiant/enseignant).

### 6.2 Parc CURP (écranés U4/U5, sous `/administration/comptes*`, garde
`habilitations_admin.gerer` + drapeau `flag.curp_ui_admin`)

| Écran | Fichier | Couvre la demande |
|---|---|---|
| Tableau comptes | `habilitations/ListeComptes.jsx` | §19 tableau principal (recherche, filtres, tri, pagination, créer, modifier, désactiver, réactiver, verrouiller, déverrouiller) |
| Fiche compte | `habilitations/FicheCompte.jsx` + `ModifierCompte.jsx` + `DifferentialPanel.jsx` | §20 fiche complète (identité, compte, rôles, permissions effectives, périmètres, journal) + différentiel avant écriture |
| Assistant création | `habilitations/AssistantCreation.jsx` | §2 (rôles multiples, périmètres, validité, statut) |
| Rôles | `habilitations/GestionRoles.jsx` | §21 (liste, détail, duplication via API `roles/{code}/`) |
| Matrice | `habilitations/MatricePermissions.jsx` | §22–23 (organisation module→ressource→action + matrice rôle×permission) |
| Journal | `habilitations/JournalHabilitations.jsx` | §25 (append-only, chaîne SHA-256, endpoint d'intégrité `journal/integrite/`) |
| Dérogations / Délégations | `Derogations.jsx`, `Delegations.jsx` | §14/18 (exceptions bornées, séparations des tâches) |
| File de provisionnement | `FileProvisionnement.jsx` | §2 (6 sondes métier, approbation humaine) |
| Import masse / opérations | `OperationsMasse.jsx` | §27 (imports réversibles `IMP-AAAAMMJJ-NNNN`) |
| Revue / Notifications | `RevueHabilitations.jsx`, `NotificationsHabilitation.jsx` | §25 (préavis, échéances, alertes) |

**Garde-fous front** : `ProtectedRoute capacite={module, action}` ; menu construit par
`peut(user, module, action)` sur `capabilities` — le §31 (menu dynamique) est **déjà
implémenté**. Les contrôles front ne remplacent jamais le backend (projections en
lecture seule, l'API reste l'autorité).

### 6.3 Écrans manquants vis-à-vis du prompt

- **Organisation** : aucun écran Départements/Services (§24) — les entités
  `Département`/`Direction` n'existent pas non plus (voir §9).
- **Permissions effectives dédiées** : `mes-acces` existe, mais pas d'écran
  `GET /users/{id}/effective-permissions/` par compte tiers (la fiche compte le
  projette pour l'admin).
- **Comptes démo identifiés** : 14 comptes témoins `temoin_*` + `admin` (U0) — §36
  partiellement couvert (parc de démo clair, jamais injecté en prod).

---

## 7. API actuelles (extraits pertinents)

```
POST   /api/auth/login/            GET  /api/auth/me/            PATCH /api/auth/me/
POST   /api/auth/token/refresh/    POST /api/auth/logout/        GET  /api/auth/roles/
GET    /api/auth/capabilities/     POST /api/auth/me/change-password/
GET    /api/auth/users/            POST /api/auth/users/
GET    /api/auth/users/{id}/       PATCH /api/auth/users/{id}/   DELETE /api/auth/users/{id}/

GET    /api/habilitations/comptes/            POST (création assistée)
GET    /api/habilitations/comptes/{id}/       POST .../simuler-modification/
POST   /api/habilitations/comptes/{id}/modifier/      POST .../statut/
POST   /api/habilitations/comptes/import-simuler/   POST .../imports/  (exécution, drapeau)
GET    /api/habilitations/comptes/imports/{ref}/     POST .../annuler/
GET    /api/habilitations/roles/            GET /api/habilitations/roles/{code}/
GET    /api/habilitations/permissions/      GET /api/habilitations/matrice/
GET    /api/habilitations/journal/          GET /api/habilitations/journal/integrite/
POST   /api/habilitations/derogations/      POST .../revoquer/
POST   /api/habilitations/delegations/      POST .../terminer/  .../activer/  .../action/
GET    /api/habilitations/propositions/     POST .../approuver/  .../rejeter/
POST   /api/habilitations/provisions/scanner/
GET    /api/habilitations/notifications/    .../lire/  .../tout-lire/
GET    /api/habilitations/mes-acces/        POST /api/habilitations/evaluer/
GET    /api/formations/secretariats/        (CRUD organisation partielle)
```

**Absents** : `DELETE /api/users/{id}/roles/{role_id}/` explicite (les rôles passent
par le différentiel `simuler-modification`→`modifier`), `GET /users/{id}/scopes/`
dédié, `GET /api/audit-logs/` générique (le journal CURP existe :
`/api/habilitations/journal/`).

---

## 8. Sécurité — ce qui est fait / ce qui manque

**Fait** : backend seul autorité ; défaut `IsAuthenticated` ; throttlage login ;
partition web/mobile ; device binding ; `must_change_password` ; journal
**immuable** (ORM + déclencheurs PostgreSQL) et **chaîné SHA-256** avec vérification
d'intégrité ; séparation des tâches (5 incompatibilités appliquées par le moteur et
les contrôles d'attribution) ; motif obligatoire sur chaque geste sensible ;
révocation de sessions/délégations ; file d'approbation humaine (aucune écriture
automatique) ; drapeaux de sécu livrés éteints ; politiques paramétrées.

**Manque (écarts mesurés, registre `docs/curp/01-etat-des-droits.md` E1–E11)** :

| Écart | Constat | Unité prévue |
|---|---|---|
| **Moteur OFF** | `HABILITATIONS_APPLICATION`/`OBSERVATION` éteints ; les vues métier appliquent le legacy seul ; `ExigePermission` = 0 usage | U8 (bascule après observation) |
| **Verrouillage compte** | `echecs_consecutifs`/`date_verrouillage`/`nombre_echecs_avant_verrouillage` existent mais **la connexion ne les applique pas** | U6 |
| **MFA** | flag `mfa_actif` seulement ; aucun TOTP/SMS | U6 |
| **last_login** | non alimenté par les logins JWT (E11) → comptes dormants invisibles | U4/U8 |
| **Repli permissif** | `participants_queryset_for_user` renvoie tout pour les rôles sans branche (E5) ; défense en aval uniquement | U2 (observation) |
| **Double source finance** (E2/E4) | `FINANCE_MODULE_ROLES` vs permission `finance_module` ; ADMIN non superuser sans finance | U2/U3 |
| **Asymétrie scolarité** (E3) | secrétariats sans `add_participant` mais avec `delete_participant` | U2 |
| **Rôles non retirés** (E1) | `user.save()` ajoute le groupe sans retirer l'ancien | U1/U2 |
| **Double API utilisateurs** | `/api/auth/users/` (legacy) + `/api/habilitations/comptes/` (CURP) coexistent | U8 |
| **Front `utils/roles.js`** | 411 lignes de logique serveur dupliquées (E7) | retrait après bascule |
| **Deux journaux** | `presences.AuditLog` (générique badgeage/formations) + `habilitations.JournalHabilitation` (IAM) — périmètres distincts, pas de doublon mais à clarifier en doc | — |

---

## 9. Organisation hiérarchique (§4, §15 du prompt) — état réel

La cible « Établissement → Direction → Département → Service → Formation → Parcours →
Groupe → Cours/ECUE » **n'existe que partiellement** :

| Niveau | Entité existante | État |
|---|---|---|
| Établissement | — (l'INJS est singleton dans le SI) | n/a (mono-établissement) |
| Direction | **aucun modèle** (`Perimetre.Type.DIRECTION` existe sans entité porteuse) | à créer ou à cartographier sur `Secretariat` |
| Département | **aucun modèle** | à créer (ou cartographier sur domaines/secteurs) |
| Service | `ressources_humaines.Service` (+ `formations.Secretariat`, `RefTypeSecretariat`, `RefSite`) | exists, non hiérarchisé entre eux |
| Formation / Parcours / Niveau / Groupe | `formations.RefFormation`, `scolarite.Parcours`, `Niveau`, `Groupe` | exists |
| Cours / ECUE / UE | `formations.Module`, `scolarite.ECUE`/`UE` | exists |

`User` est rattaché à **un seul secrétariat** (`User.secretariat` 1:1) ; il n'y a
ni `User.département` ni `User.service` (M2M) au sens du prompt. Les périmètres
`DIRECTION`/`SERVICE`/`SITE` du modèle CURP sont **prêts à porter** ces niveaux
dès que les entités existent — le modèle CURP n'a pas à changer pour ça.

---

## 10. Données de démonstration & compatibilité

- **Parc démo** : 15 comptes (14 témoins `temoin_*` couvrant les 12 rôles legacy +
  `admin`), ensemencement idempotent documenté (U0) ; jamais injecté en prod.
- **Comptes métier réels** : `Participant`/`Formateur`/`Agent`/`DossierEtudiant`
  reliés à `User` (17 FK formations, 7 jurys, 7 administrations, 6 presences, 6
  patrimoine, 6 statistiques, 6 graduation…) — **aucune de ces relations n'est à
  toucher** : la bascule U8 doit rattacher ces comptes existants au profil CURP sans
  suppression (règle S5 : jamais de suppression physique).
- **Migrations** : 8 dans `habilitations` (0001→0008, toutes réversibles, vérifiées
  aller/retour), 7 dans `parametres` (flags), 92 dans `formations`… État propre
  (`makemigrations --check` : aucune migration manquante).
- **Base** : production/CI = PostgreSQL (déclencheurs d'immutabilité du journal) ;
  sandbox = SQLite (l'ORM assure l'immutabilité).

## 11. Tests

- **Backend** : 114 fichiers / ≈ 943 méthodes ; `habilitations` : **349 tests**
  (U0 : 110 caractérisation, U1–U5 : cycle de vie A5, file idempotente, approbation,
  plafonds, imports réversibles, délégations, expirations, intégrité journal).
- **Frontend** : 70 fichiers Vitest (dont `habilitations/*` : listes, fiche,
  différentiel, matrice, U5 cycle de vie, flags).
- **Refus d'accès** : couverts pour le legacy (403 vérifiés par tests caractérisation
  E5/E8) ; **pas encore de tests de refus sur le moteur CURP en mode APPLICATION**
  (impossible tant que le mode est OFF) — à construire en U8 avec les scénarios
  §33/§34/§35 du prompt (enseignant A ≠ B, chef dépt A ≠ B, étudiant A ≠ B, agent
  scolarité ≠ admin rôles, admin SI ≠ droits métier sensibles).

---

## 12. Synthèse des écarts vs prompt maître

| § prompt | Existant | Écart à combler |
|---|---|---|
| 2/5 Modèle données | Personne/Compte/Role/Permission/Attribution/Perimetre/Delegation/Journal/Politique | Équivalent complet — à enrichir (département/service sur le compte, photo) |
| 6 Compte (champs) | email, nom/prénom, matricule, téléphone, grade, organisation, statut (6), verrouillage (champ), expiration (champ), MFA (flag) | **photo**, verrouillage **effectif** (connexion), MFA réel |
| 7 Rôles | 35 catalogués + 12 legacy | ~30 rôles cible manquants (travaux de **données** : catalogue + matrice) |
| 8/9/10/11/12/13 Permissions | 1 155 `<module>.<ressource>.<action>` + 31 verbes | RAS (couverture A3 complète pour les 20 modules) ; cartes §10–13 à vérifier case par case en J2 |
| 14/15/16 Périmètres | 12 types polymorphes + résolveurs de couverture + moteur | Entités **Direction/Département** ; hiérarchisation Service→Département ; périmètre `ETABLISSEMENT` inutile (mono-site) |
| 17 Super admin | `ADMIN_SYSTEME` (N4 global) + superuser Django | Politique « ne pas contourner les validations métier » : à formaliser (rôles sensibles N4 + audit renforcé) |
| 18 Séparation des tâches | 5 incompatibilités + contrôles d'attribution + délégation bornée | Étendre les couples au besoin (données) |
| 19/20/21/22/23 Écrans | 15 écrans CURP + Users legacy | **Écran Organisation** (départements/services) ; endpoint/effectives-permissions par compte |
| 25 Audit | Journal immuable chaîné + AuditLog générique + `_log_audit` | Clarifier la doc ; endpoint `/audit-logs/` si demandé |
| 26/27/28 Sécurité/API/Backend | En place (backend seul autorité) | Branchement `ExigePermission` en U8 (mode observation d'abord, règle R3) |
| 29/31 Front | Menu dynamique + ProtectedRoute + contrôles par capacité | RAS |
| 32/33 Étudiant/Enseignant | Rôles `ETUDIANT`/`CANDIDAT`/`ENSEIGNANT` + périmètres `PROPRE_COMPTE`/`MODULE_ECUE` + canal mobile | Tests de refus croisés (§34) |
| 34/35 Tests | 349 habilitations + 70 front | Scénarios E2E §35 + refus §34 (mode APPLICATION) |
| 36 Démo | 14 témoins identifiés | RAS (étendre aux nouveaux rôles si ajouté) |
| 37/39 Compatibilité | Relations métier préservées, S5 (jamais de suppression) | Discipline U8 : rattachement additif uniquement |
| 40 Documentation | `docs/curp/*` (U0–U5, matrice, ADR) | Créer `docs/architecture/IAM.md` + `docs/security/RBAC.md` + `docs/administration/utilisateurs.md` + `docs/audit/permissions.md` (consolider l'existant) |

---

## 13. Recommandation (saisie pour la Phase 1)

**Ne pas reconstruire.** Le socle CURP est exactement le module demandé. La Phase 1
doit donc :

1. **Périmètre 1 — Modèle & données** : entités `Direction`/`Département` (ou
   cartographie explicite sur `Secretariat`), lien compte↔organisation (M2M),
   `photo` sur `Personne`, rôles manquants du prompt ajoutés au **catalogue**
   (migration de données idempotente, réversible) + extensions de la matrice
   marquées « provisoires J2 ».
2. **Périmètre 2 — Sécurité effective (U6 avancée)** : verrouillage de compte
   appliqué à la connexion (échecs → verrouillage → déverrouillage admin), MFA
   (TOTP, flag `mfa_actif`), alimentation `last_login`/`derniere_connexion` sur les
   logins JWT, sessions bornées.
3. **Périmètre 3 — Écrans** : Organisation (départements/services + utilisateurs),
   permissions effectives par compte (endpoint + bloc fiche), matrice complétée
   (recherche/filtres).
4. **Périmètre 4 — Tests & doc** : refus d'accès (§34), E2E (§35), consolidation
   `docs/architecture/IAM.md` etc.
5. **Périmètre 5 — Bascule (U8, ultérieure et optionnelle)** : rattachement des
   comptes legacy au profil CURP, mode OBSERVATION → APPLICATION du moteur,
   `ExigePermission` sur les vues critiques, retrait du legacy. **À ne lancer qu'après
   feu vert explicite** (impact production).

**Contraintes permanentes** : additif uniquement, migrations réversibles, aucun
`flush/drop/truncate`, tests de refus obligatoires avant tout « terminé », journal
pour chaque geste sensible, frontend jamais source d'autorisation.
