# Rapport — Refonte Organisation / Cours-Formations / Présences QR (lots A, C, B)

**Date :** 2026-09-15 · **Branches/commits :** `7520d7e` (lot A), `4c04dbb` (lot C), `86ceb57` (lot B)
**Plan :** `docs/audits/2026-09-15-plan-refonte-organisation-cours-presences.md`
**Référentiels appliqués :** Modèle fonctionnel INJS-LMD 2026 (MODULES 04, 08, 13),
rapport de mise en œuvre (zéro régression, D1-D5), audit du 11/09.

---

## 1. « Secrétariats » → « Directions / Départements / Services » (lot A — modèle 13)

- **Structure enrichie, pas remplacée** : `administrations.Direction`/`Departement` et
  `ressources_humaines.Service` gagnent les champs du modèle 13.3 (code, responsable,
  adjoint, téléphone, e-mail, localisation) — migrations purement additives.
- **Le secrétariat devient un service de support rattaché** (§15) :
  `formations.Secretariat.direction` / `.departement` (nullables, **au plus un**,
  CheckConstraint `secretariat_rattache_au_plus_un`) + adjoint/contact/localisation/`actif`.
- **API unifiée** `/api/administrations/organigramme/` : arbre hiérarchique
  (directions → départements → services → secrétariats rattachés, orphelins inclus),
  CRUD des quatre entités, `DELETE` = **désactivation** (jamais de purge), effectifs
  calculés depuis les rattachements CURP `CompteUtilisateur.departements/services` et
  `User.secretariat` (§13.8 « effectifs = comptes ayant accès ») ; écriture réservée à la
  direction (DFRC), lecture à tout compte authentifié ; chaque geste journalisé dans la
  chaîne immuable `journaliser` (actions `ORGANISATION_CREEE/MODIFIEE/DESACTIVEE`).
- **Console CURP** : les trois écrans `organisation_*` exposent désormais les nouveaux
  champs (lecture) ; leurs routes sont inchangées.
- **Unités feuilles typées et imbriquables (13.4)** : un service porte un
  `type_unite` (SERVICE / BUREAU / UNITÉ / CELLULE / AUTRE) et peut être rattaché à un
  autre service (`parent`, garde anti-cycle, 30 niveaux max) — l'organisation réelle
  de l'INJS se modélise sans coder de profondeur en dur ; l'arbre de l'écran greffe
  récursivement les sous-unités sous leur parent.
- **Frontend** : nouvel écran `/organisation` à quatre onglets (liste + arbre, CRUD
  modal incluant type et unité rattachante, réactivation des unités inactives). L'entrée de menu **« Secrétariats » est
  remplacée** par « Directions / Départements / Services » ; `/secretariats` redirige
  vers l'onglet secrétariats et l'écran historique reste monté sur
  `/secretariats/historique` (pont de rétrocompatibilité). Catalogue CURP : codes
  `administrations.organigramme.consulter/gerer` (+ fixtures menu régénérées : 1157 codes).

## 2. Présences par QR — automatique ET manuelle à motif (lot C — modèle 08)

L'existant (badgeage legacy `SessionModule`, geofence, heartbeats, rattrapages) est
**conservé tel quel** ; la chaîne 08 est **empilée** sur les séances LMD de l'EDT :

- `formations.QRToken` accepte une séance EDT (`seance_edt`, `session` assouplie
  nullable) ; `presences.Pointage` gagne `seance_edt`. Les pointages LMD sans séance
  legacy sont **protégés partout** : heartbeat sanctions et `auto_close_pointages`
  filtrés, aggégations de stats et colonnes d'admin gardées sur `None`.
- **Scan automatique** `POST /api/presences/seances-edt/scan/` : identité déduite du
  compte (anti-fraude), `device_id` requis pour auditeurs, fenêtre temporelle
  (ouverture anticipée / retard / clôture — tolérances paramétrables via
  `Parametre` : `presences.edt.*`), **réservé aux inscrits du groupe** (règle 1),
  1 entrée + 1 sortie par séance, retard automatique au-delà de la tolérance,
  tout scanné audité (`SCAN_SECURE_ENTREE/SORTIE`, canal `EDT_LMD`).
- **QR de séance** `GET/POST …/seances-edt/<id>/qr/` : jeton unique par séance et par
  jour (régénération désactive l'ancien), ouvert à l'enseignant de l'affectation, au
  secrétariat et à la direction.
- **Émargement manuel de masse** `POST …/emargement/` : les « cases de l'enseignant »
  du modèle 08.2 (badger tout le groupe, puis exceptions) ; statuts PRÉSENT/RETARD/
  ABSENT/ABSENCE_JUSTIFIÉE/EXCUSÉ ; **motif obligatoire dès qu'un badgeage existant est
  corrigé** (08.14 « forçage contrôlé »), avec avant/après et auteur journalisés ;
  participants hors groupe refusés (403).
- **Clôture automatique** `POST …/autoclore/` : ouvertures refermées à la fin de
  séance (`SORTIE_AUTO`), inscrits sans aucun badge marqués absents
  (`ABSENT_NON_BADGE`), QR désactivé, bilan audité (`CLOSE_SESSION`) — la commande
  planifiée legacy reste opérationnelle.
- **Écran `/edt/presences`** : séances du jour (filtrées par périmètre), modal QR
  (bibliothèque `qrcode` déjà au contrat), liste nominative cochable, bouton
  « Tous présents », motif global, clôture auto. Entrée de menu dédiée dans la
  console GET-INJS.
- Pilotes CURP branchés en observation : `presences.qr.generer`,
  `presences.emargement.saisir/consulter`, `presences.seance_emargement.cloturer`.

## 3. Cours & Formations alignés sur la chaîne LMD (lot B — modèle 04, D3)

- **`RefFormation` = descripteur de cycle** (04.4) : code (unique, normalisé), type de
  diplôme (LICENCE/MASTER/DOCTORAT/DUT/PROFESSIONNALISANT/AUTRE), domaine, mention,
  durée (années), nb semestres, crédits ECTS visés, description ; API référentiel
  exposant les champs, PUT à sémantique douce, **suppression protégée** (409) dès
  qu'une session s'appuie sur le cycle.
- **Dien D3 résolu par lien, pas par fusion** : `formations.Formation.ref_formation`
  (FK nullable, SET_NULL) exposée en écriture/lecture (`ref_formation_intitule`) ; la
  création de formation depuis l'écran Modules **rattache automatiquement le cycle**
  quand l'intitulé provient du référentiel ; la règle L1 des présences
  (`maquette_active_pour_session`) repose désormais sur le vrai lien.
- **Réconciliation des données** : `manage.py reconcilier_formations_cycles`
  (idempotente, `--dry-run`, option `--creer-cycles-manquants` qui crée le cycle
  nettoyé avant rattachement). Appliquée en dev : 3 cycles créés, 3 sessions reliées,
  aucune perte ; les intitulés ambigus restent non rattachés (rapport).
- **Vue « Cours » LMD** : `GET /api/scolarite/pedagogie/cours/` = affectation
  pédagogique × planning EDT publié × effectif (affectations de groupe actives) ×
  séances réalisées (pointages lot C) ; filtres année (courante par défaut), cycle,
  niveau, semestre, groupe, enseignant, type, statut, recherche.
- **Écran `/cours`** : table filtrable + détail (cursus, position, volume, séances
  planifiées avec lien direct « Présences » vers `/edt/presences?seance=`) ; menu :
  nouvelle entrée « Cours (LMD) », l'entrée CPFAE devient « Cours & modules
  (CPFAE — héritage) » (chemin `/modules` inchangé), l'entrée GET-INJS « Cours »
  pointe vers la vue LMD ; le référentiel cycles (écran générique) affiche les
  nouveaux champs.

## 4. Zéro régression — preuve

| Contrôle | Résultat |
|---|---|
| Suite backend complète (feux verts, SQLite parallel=1) | **1672 tests, OK (skipped=5)** — baseline ~1623 préservée, +49 tests |
| Suite frontend Vitest | **85 fichiers / 1725 tests, OK** |
| Lint ESLint + build Vite | OK (0 erreur) |
| `manage.py check` / migrations | additives seules ; `makemigrations --check` propre |
| Contrat d'API (`docs/api/contract.snapshot.json`) | 634 → **665 routes, additif uniquement**, changelog justifié (P00-08) |
| Catalogue CURP | +2 codes, 0 retiré ; fixtures menu régénérées (1157 codes) |
| Garde spécifique du nombre de codes (console U4) | mise à jour assumée **dans le lot** (1157) |
| Feu 3 (Flutter) | non levable dans le sandbox — à valider hors Arena (convention héritée) |

## 5. Écarts assumés / suite

1. **Enseignant non badgeable sur séance LMD** : le scan EDT est réservé aux auditeurs
   inscrits ; la présence de l'enseignant continue de passer par le flux SessionModule
   (paie) — à réunifier au prompt « heures réalisées » si le besoin apparaît.
2. ~~`NotificationAbsence` et les alertes restent branchés sur le flux legacy~~ —
   **résolu par le lot suivant** (`90325c1+` : alerte à la clôture) :
   `auto_clore` vérifie le cumul d'absences de chaque absent de la séance contre les
   seuils `ConfigAlerteSeuil` (les mêmes que l'agrégat global) et notifie
   immédiatement Direction/Secrétariat ; idempotence garantie par contrainte
   d'unicité (destinataire, étudiant, séance, niveau) ; désactivable par le
   paramètre `presences.edt.notifier_a_cloture`. La **cloche** de l'application
   (`AppNotificationsBell`) gagne une source « Présences » (`GET/PATCH
   /api/stats/notifications/recues/`, contrat `tout`+`ids`) — 7 tests backend,
   4 tests vitest.
3. La gouvernance complète des cycles (formulaire de création du référentiel dans la
   console) s'appuie sur l'API durcie (`/formations/ref/formations/`) ; l'écran
   générique reste en lecture — l'ajout d'un formulaire CURP dédié est un lot à part.
4. Les dates de séances sont dérivées (année académique + n° de semaine + jour) ; si
   l'EDT adopte plus tard un calendrier par occurrence (séance datée en dur), le
   service `seances_edt_services.est_seance_du_jour` est le point d'adaptation unique.
