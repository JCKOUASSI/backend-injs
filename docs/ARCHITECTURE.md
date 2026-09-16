# Architecture de l'application INJS-LMD 2026

> Document de référence de l'architecture **réelle** du dépôt. Il ne décrit pas une cible
> idéale : il explique ce qui existe, comment les 18 modules de référence s'appuient sur
> les applications Django effectives, et fige les douze décisions d'architecture (DA-01 →
> DA-12) qui s'imposent à tous les développements.
>
> Voir aussi : [README racine](../README.md), [registre des ADR](ADR/README.md),
> [cartographie cible](CARTOGRAPHIE_CIBLE_INJS_LMD.md),
> [baseline d'audit](audits/BASELINE_2026-09.md).

Date de référence : septembre 2026. États : **[OK]** existe et est exploitable ·
**[PART]** partiel · **[CRÉER]** à construire.

---

## 1. Vue d'ensemble

L'application de l'**INJS Marcory** (Abidjan, Côte d'Ivoire) couvre la gestion LMD « de A
à Z » : référentiels, admissions/concours, scolarité et pédagogie, enseignants, emplois du
temps, présences par QR, notes, jurys et diplômation, finances étudiantes, administration
et patrimoine, statistiques/BI et portails.

Trois clients consomment **uniquement** l'API Django/DRF (jamais la base directement) :

```
                           ┌──────────────────────────────────────────────┐
                           │                BACKEND  Django 5.1.4 / DRF     │
                           │            (backend/, 20 applications à plat)  │
                           │                                                │
   ┌───────────────┐  HTTPS│  config/settings.py                           │      ┌──────────────┐
   │  FRONTEND WEB │──────▶│  REST / JWT (SimpleJWT)  ── drf-spectacular    │◀────▶│ PostgreSQL   │
   │ React 18/Vite │  /api │  WhiteNoise (statiques) · Gunicorn             │  SQL │ 16 (prod/CI) │
   └───────────────┘       │                                                │      └──────────────┘
   - tableau de bord       │  authentication · referentiels · parametres    │
   - écrans métier         │  formations · presences · exports · dashboard  │      ┌──────────────┐
   - servi par Nginx en    │  statistiques · suiviEvaluation · scolarite    │◀────▶│  Redis 7     │
     prod (ou par Django   │  admissions · equivalences · jurys · graduation│ cache│ (cache partagé│
     en mode PREVIEW_SPA)  │  finances_etudiantes · stages · administrations│      │  multi-instances)│
                           │  ressources_humaines · patrimoine · edts        │      └──────────────┘
   ┌───────────────┐       │                                                │
   │ MOBILE FLUTTER│──────▶│  /api/scan/secure/ · heartbeats · géofence      │      ┌──────────────┐
   │ + PWA web     │  /api │  services planifiés (cron) :                    │      │  Stockage    │
   │ (qr_badge_    │       │   process_mobile_heartbeats ·                   │      │  media/ +    │
   │  mobile/)     │       │   auto_close_pointages · auto_sessions          │      │ staticfiles/ │
   └───────────────┘       └──────────────────────────────────────────────┘      └──────────────┘
                                   ▲                                      ▲
        ┌──────────────────────────┴───────────────┐        ┌────────────┴────────────┐
        │  Emploi du temps : planificateur EXTERNE  │        │  Emails SMTP (transactionnel)│
        │  app-ept-injs-lmd — contrat LECTURE SEULE │        │  (optionnel, sinon console)  │
        │  GET /api/scolarite/edt/...  (DA-09)      │        └──────────────────────────┘
        └───────────────────────────────────────────┘
```

- Le frontend web et l'API sont séparés en développement (Vite 3000 / Django 8001) ; en
  production le frontend est construit puis servi par Nginx (image Docker), et Django ne
  fournit que l'API et l'administration. Un mode « SPA servie par Django »
  (`PREVIEW_SPA=1`, une seule origine) existe pour les démonstrations.
- Le client mobile natif (Flutter) et la PWA utilisent le parcours de badgeage authentifié
  `/api/scan/secure/` ; le parcours public `/api/scan/` est désactivé en production
  (`PUBLIC_QR_SCAN_ENABLED=False`).
- En mise à l'échelle horizontale, les réplicas applicatifs partagent le cache Redis et
  le volume `media/` (voir `backend/compose.scale.yml`, Nginx en tête).

---

## 2. Découpage : 18 modules de référence ↔ applications Django

La table officielle de correspondance (extrait des règles du projet). Les applications
sont disposées à plat (DA-01 / ADR-005) : on ne crée pas de sous-dossier `apps/`.

| # | Module de référence | Application(s) Django réelle(s) | État | UI web |
|---|---------------------|----------------------------------|------|--------|
| 01 | Référentiels | `formations` (les `Ref*`), `scolarite` (année académique, type de formation, niveau, parcours, semestre, régime, statut étudiant), `referentiels` (`RefSocle`, journal), `parametres` | PART | PART |
| 02 | Candidatures & admissions | `admissions` (candidats, candidatures, pièces, campagnes, épreuves, surveillances, convocations, notes, classements) | OK | PART |
| 03 | Étudiants | `scolarite` (dossier étudiant, inscriptions administrative/pédagogique, `Groupe`, `AffectationGroupe`, `AffectationPedagogique`, journal), `formations.Participant` | OK | PART |
| 04 | Formations & pédagogie | `scolarite` (maquettes/UE/ECUE versionnées), `formations` (`Formation`, `Module`, `SessionModule`) | OK | PART |
| 05 | Enseignants | `formations.Formateur`, `ressources_humaines.Agent`, `scolarite.AffectationPedagogique` | OK | PART |
| 06 | Emplois du temps | `edts` (`CreneauTemplate`, `EmploiDuTemps`, `AffectationCreneau`, `ConflitCreneau`), `formations.SessionModule`, contrat lecture seule `scolarite/edt_export.py` | PART | PART |
| 07 | Campus & patrimoine | `patrimoine` (équipements, véhicules, inventaire, maintenance, réservations, mouvements), lieux `Ref*` dans `formations` | PART | CRÉER |
| 08 | Présences | `presences` (`Pointage`, `AuditLog`, `DeviceBinding`, `Rattrapage`, `NotificationAbsence`) | OK | PART |
| 09 | Évaluations & notes | `formations` (`NoteModule`, colonnes, `CorrectionNoteModule`), `suiviEvaluation` | OK | OK |
| 10 | Jurys & diplômation | `jurys` (sessions, membres, propositions, décisions, PV), `graduation` (diplômes, rééditions, registre, modèles de documents), `equivalences` | OK | PART |
| 11 | Finances étudiantes | `finances_etudiantes` (tarification, échéanciers/lignes, factures, paiements, quittances, remboursements, relances, rapprochements) | OK | PART (~25 %) |
| 12 | Direction financière & comptabilité | `formations.FinanceSettings/FinanceAjustement` (rémunération des formateurs uniquement) ; la comptabilité générale n'existe pas encore (future app `comptabilite`) | CRÉER | PART |
| 13 | Administration & RH | `administrations` (courriers, documents officiels, versions, réunions de commission, missions), `ressources_humaines` (services, fonctions, agents, affectations, disponibilités, documents RH), `stages` | PART | CRÉER |
| 14 | Documents, courriers & archives | `administrations` (courrier, document officiel, versions) | PART | CRÉER |
| 15 | Notifications & communication | dispersé (`presences.NotificationAbsence`, notifications de jurys, relances financières) ; future app `notifications` | CRÉER | CRÉER |
| 16 | Rapports, statistiques & BI | `statistiques` (config d'alertes/seuils, rapports, observations, signatures, notifications), `dashboard`, `exports` (routes PDF/Excel) — **lecture seule**, DA-10 | OK | OK |
| 17 | Portails & services en ligne | frontend React (routes), Flutter/PWA, `dashboard/views_legacy.py` ; future app `portails` (aucun nouveau métier, DA-11) | PART | PART |
| 18 | Administration système & sécurité | `authentication` (12 rôles, JWT, appairage de device, limitation de débit, permissions, groupes), `parametres` (`Parametre` + historique), `presences.AuditLog`, **`core` (P01-01 : journal d'audit unifié append-only, codes atomiques, `/api/core/audit/`)** | OK | PART |

Le tableau ci-dessus couvre les **20 applications métier** répertoriées dans
`INSTALLED_APPS` (`referentiels` y est inclus, au titre du module 01) ; `config` n'est pas
une application mais le package de réglages Django. Les applications créées pendant la
restauration de la branche 2026-09 sont `graduation`, `finances_etudiantes`, `stages`,
`administrations`, `ressources_humaines`, `patrimoine`, `edts`. L'application **`core`**
est créée par P01-01 (journal d'audit unifié, derrière `flag.lot01_socle_referentiels_rbac`).
Les applications manquantes à créer plus tard selon la même nomenclature à plat sont
`comptabilite`, `notifications` et `portails` (DA-01).

---

## 3. Les douze décisions d'architecture (DA-01 → DA-12)

Ces décisions tranchent les tensions entre l'architecture cible idéale et l'état réel du
dépôt ; elles s'imposent à toutes les évolutions.

### DA-01 — Conservation de l'arborescence Django existante
On **ne renomme pas et on ne déplace pas** les applications existantes (risque sur les
migrations, les imports et les tests). Les applications manquantes sont créées en
respectant la nomenclature française à plat : `core`, `comptabilite`, `notifications`,
`portails`. → [ADR-005](ADR/ADR-005-conservation-arborescence-django-a-plat.md).

### DA-02 — Une seule source de vérité par objet
Aucun doublon de référentiel : une formation de référence unique, un espace unique, un
groupe unique (`scolarite.Groupe`), un module/ECUE unique. Les doubles représentations
historiques D1–D5 convergent par ponts additifs, sans suppression brutale.
→ [ADR-001](ADR/ADR-001-doubles-representations-D1-D5.md), [ADR-006](ADR/ADR-006-unicite-libelles-insensible-casse.md).

### DA-03 — Soft delete et historisation
Aucune suppression physique sur les données académiques, financières et documentaires :
`is_active` / `deleted_at` + journal (ancienne/nouvelle valeur, utilisateur, date, motif).
Les notes corrigées passent par un objet de correction traçable ; les opérations
financières validées sont annulées/régularisées/remboursées, jamais supprimées.

### DA-04 — Année académique obligatoire
Toute donnée académique temporelle est rattachée à une année académique ; une seule année
active à la fois (contrainte déjà testée) ; une année clôturée interdit la modification des
résultats définitifs.

### DA-05 — RBAC = niveau × rôle × permission × module × périmètre × état
L'autorisation ne dépend jamais d'un simple nom de rôle. Exemple : *formateur + N2 +
NOTES.MODIFIER + SES GROUPES + NOTE NON VALIDÉE* → autorisé ; *+ AUTRE FORMATION* → refusé.

- Périmètres : `INJS_ENTIER, DIRECTION, SERVICE, FORMATION, PARCOURS, NIVEAU, GROUPE,
  MODULE, ETUDIANT, PROPRE_COMPTE`.
- Actions : `CONSULTER, CRÉER, MODIFIER, SOUMETTRE, VALIDER, REJETER, PUBLIER, ANNULER,
  EXPORTER, IMPRIMER, ARCHIVER, SUPPRIMER, ADMINISTRER`.
- Les **12 rôles existants sont conservés** et cartographiés sur les niveaux N0–N4 ; les
  rôles additionnels cibles (comptabilité, documentation, patrimoine, jury, candidat,
  consultation) sont ajoutés, jamais substitués.
- La matrice UI (`frontend/src/utils/roles.js`) reste alignée sur
  `authentication/role_groups.py`, puis dérive d'un endpoint de capacités backend.
- **État réel :** les 12 rôles et groupes Django existent ; le formalisme N0–N4 n'est pas
  encore implémenté (la matrice du README racine est la cible à faire valider, tâche
  P01-05).

### DA-06 — Feux de bascule (feature flags) pour tout changement de comportement
Tout changement d'un comportement existant est livré derrière un paramètre backend
(`parametres.Parametre`) **et** une variable d'environnement, activable par rôle et par
domaine, désactivable en une minute sans redéploiement de code.

### DA-07 — Deux finances, jamais fusionnées (D5)
`finances_etudiantes` (frais de scolarité) et `formations.Finance*` (rémunération
horaire des formateurs) restent deux sous-systèmes autonomes (modèles, écrans, droits,
exports). Le seul lien est analytique (remontée vers le module 12).
→ [ADR-002](ADR/ADR-002-deux-finances-jamais-fusionnees.md).

### DA-08 — Gabarit d'écrans unique pour les domaines orphelins
Stages, patrimoine, RH et administrations sont livrés avec un seul gabarit React
réutilisable : liste filtrable + pagination serveur + détail + timeline de statut +
pièces jointes + exports.

### DA-09 — Contrat EDT v1.1 conservé
Le contrat lecture seule `/api/scolarite/edt/` vers le planificateur externe est conservé
et versionné. Le moteur natif (lot EDT) produit des **brouillons validables** ; l'ingestion
externe produit les séances actives.
→ [ADR-003](ADR/ADR-003-edt-externe-et-moteur-natif-complementaires.md).

### DA-10 — Le module 16 (BI) est en lecture seule
Rapports et BI ne modifient aucune donnée métier : ils agrègent. Les agrégats lourds
passent par des tables de synthèse incrémentales et le cache Redis, jamais par des requêtes
lourdes en ligne.

### DA-11 — Le module 17 (portails) ne recrée aucun métier
Les portails exposent les API existantes selon les droits ; aucun modèle métier dans la
couche portail (navigation + tableaux de bord + accès aux API filtrées).

### DA-12 — Le retrait du legacy est le dernier geste
Le socle HTML legacy (`dashboard/views_legacy.py`, templates de badgeage,
`backend/static/sw.js`, CDN html5-qrcode / Bootstrap 5.3, courriels et logos d'ancienne
identité) n'est retiré **qu'après** bascule vérifiée, derrière feu de bascule, avec une
fenêtre d'observation. → [ADR-005](ADR/ADR-005-conservation-arborescence-django-a-plat.md),
[ADR-004](ADR/ADR-004-middlewares-demo-iframe-gardes-debug.md).

---

## 4. Authentification et permissions (réel)

- Utilisateur personnalisé dans `authentication/models.py` : 12 rôles `TextChoices`
  (ADMIN, DIRECTION, CHEF_CPFAE_ADMIN, CPFAE_ADMIN, CHEF_SECRETARIAT, SECRETARIAT, FINANCE,
  ARCHIVE, ENCADRANT, SUPERVISEUR, FORMATEUR, AUDITEUR). Chaque rôle est synchronisé vers
  un groupe Django `ROLE_*` (`role_groups.py`).
- Une `ROLE_HIERARCHY` ordonne les rôles du plus au moins élevé ; des ensembles figés
  définissent les accès (`DUAL_ACCESS_ROLES`, `MOBILE_ONLY_ROLES`, `ALLOWED_WEB_ROLES`,
  `FINANCE_MODULE_ROLES`, …) et des combinaisons multi-rôles sont autorisées pendant la
  transition.
- Permissions DRF dans `authentication/permissions.py` (certains noms de classes portent un
  sigle hérité, par ex. `IsDFRC` pour la direction — voir §6).
- JWT par SimpleJWT (jetons aussi posés en cookies selon la configuration), limitation de
  débit DRF (`THROTTLE_LOGIN_RATE`, `THROTTLE_SCAN_RATE`), appairage de device mobile
  (`DeviceBinding`) et journal d'audit (`presences.AuditLog`).

## 5. Données, cache et traitements planifiés

- **Base** PostgreSQL en production/CI ; SQLite est pris en charge pour les bacs à sable
  légers (`USE_SQLITE=1`, `SQLITE_PATH`), avec une différence connue de pliage des accents
  documentée dans l'[ADR-006](ADR/ADR-006-unicite-libelles-insensible-casse.md).
- **Cache** : Redis si `REDIS_URL` est défini (production multi-instances), sinon cache
  fichier (`CACHE_DIR`) ou cache mémoire/local.
- **Tâches planifiées** (service `cron` du Compose ou `scripts/start_dev.sh cron`) :
  `process_mobile_heartbeats`, `auto_close_pointages --skip-heartbeat`, `auto_sessions`
  toutes les 5 minutes.
- **Statiques** : WhiteNoise avec `CompressedManifestStaticFilesStorage` ; le manifeste est
  régénéré par `collectstatic` (le dossier `staticfiles/` n'est pas versionné).

## 6. Surface legacy résiduelle en code/infrastructure (non modifiable en P00-03)

La documentation et les libellés visibles basculent immédiatement en terminologie INJS-LMD.
Restent **dans le code ou l'infrastructure** des identifiants techniques hérités que la
seule phase documentaire ne peut renommer (ils relèvent de lots ultérieurs, derrière feux
de bascule, conformément à DA-12) :

| Surface | Exemples | Lot de bascule indicatif |
|---|---|---|
| Noms de dossiers / artefacts | dossier `qr_badge_mobile/`, images et conteneurs Docker `qr-badge-*`, image de CI `sygep-backend-ci`, nom de base par défaut `qr_badge` | avec les changements d'infra / de publication |
| Identifiants de code | classes `IsDFRC`, `IsSecretariatOrDFRC`… ; `Pointage.Statut.FORCE_DFRC` ; clés de rôles `CPFAE_ADMIN`, `CHEF_CPFAE_ADMIN` (figées par DA-05) ; routes légales `/dashboard/legal/...qr-badge...` | LOT 1+ (permissions/RBAC) |
| Socle HTML / assets legacy | `dashboard/views_legacy.py`, templates de badgeage, `static/sw.js`, feuilles CSS d'administration, CDN html5-qrcode | DA-12, après bascule des écrans |
| Courriels transactionnels | sujets/signatures/logo de l'ancien nom dans `authentication/emails.py` | LOT retrait legacy, derrière feu de bascule |
| Magasins d'applications & pages légales | URL GitHub Pages hébergée et noms de fichiers `docs/legal/*qr-badge*`, textes déjà publiés | lors du rebranding des fiches stores |
| Documents d'audit | citations des anciens sigles dans `docs/audits/` (constats nécessaires à l'exactitude) | non modifiés (pièces factuelles) |

Les documents d'époque sont regroupés dans [docs/archives/](archives/README.md) et portent
un bandeau « Document d'archive — ne pas utiliser ».
