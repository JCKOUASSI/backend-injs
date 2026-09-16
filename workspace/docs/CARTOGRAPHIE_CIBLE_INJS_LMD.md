# CARTOGRAPHIE CIBLE — SYSTÈME INJS-LMD

**Base** : audit du 09/06/2026 + vérifications code au 06/09/2026 (branche `restauration-INJS-LMD-2026-08-29`, commit `8c157f5`).
**Nature du document** : livrable d'analyse — aucun code modifié par sa production.
**Légende** : ✅ = modèle/endpoint/écran existant vérifié · 🆕 = à créer · ⚠️ = double représentation signalée.

---

## 0. SOCLE TRANSVERSE (transversal à tous les modules)

- **Objectif** : identité, authentification, paramétrage global, journalisation.
- **Acteurs** : ADMIN, DIRECTION, tous rôles métier.
- **Entités existantes** : ✅ `authentication.User` (rôles TextChoices : ADMIN, DIRECTION, CHEF_CPFAE_ADMIN, CPFAE_ADMIN, CHEF_SECRETARIAT, SECRETARIAT, FINANCE, ARCHIVE, ENCADRANT, SUPERVISEUR, FORMATEUR, AUDITEUR — `backend/authentication/models.py`), ✅ `parametres.Parametre`, ✅ `parametres.ParametreHistorique` (piste d'audit du paramétrage).
- **Endpoints réels** : `/api/auth/` (login, token/refresh, me, me/change-password, roles, users), `/api/parametres/` (ViewSet `ParametreViewSet`).
- **Écrans réels** : React `Login.jsx`, `Profile.jsx`, `Users.jsx`, `Parametres.jsx` (non versionné) · Flutter `login_page.dart`, `profile_fiche_page.dart`, `change_password_page.dart`.
- **Permissions à réutiliser** : toutes les classes de `backend/authentication/permissions.py` (`HasFormationsPerm`, `CanManageParticipant`, `CanManageModuleParticipant`, `IsDFRC`, `IsDFRCOrEncadrant`, `IsParticipantOrReadOnly`, `IsSecretariat`, `IsEncadrant`, `IsSecretariatOrEncadrant`, `IsSecretariatOrDFRC`, `IsUserMutationAllowed`, `IsSecretariatOrEncadrantOrDFRC`).
- **Dépendances** : JWT SimpleJWT, throttling DRF (login/scan), `must_change_password` (déjà en place).

---

## 1. RÉFÉRENTIELS ✅ (socle existant, source de vérité)

- **Objectif** : nomenclatures stables alimentant tous les modules LMD et formation continue.
- **Acteurs** : Secrétariat, Admin.
- **Sous-modules** : formations de référence, modules de référence (+ volumes horaires), sites/bâtiments/salles, catégories, grades, vagues, types de secrétariat.
- **Entités** : ✅ `formations.RefFormation`, `RefModule`, `RefModuleVolumeHoraire`, `RefSite`, `RefBatiment`, `RefSalle`, `RefCategorie`, `RefGrade`, `RefVague`, `RefTypeSecretariat` — toutes les Ref* sont **à préserver**.
- **Endpoints réels** : `/api/formations/ref/formations/`, `ref/modules/`, `ref/sites/`, `ref/batiments/`, `ref/salles/`, `ref/categories/`, `ref/grades/`, `ref/types-secretariat/`, `ref/vagues/` + import/export Excel `ref/excel/<kind>/` · côté scolarité : `/api/scolarite/ref/<ressource>/` (niveaux, parcours, semestres, régimes…).
- **Écrans réels** : `Referentiels.jsx`, `ImportExcel.jsx`, `Secretariats.jsx`.
- **Documents** : exports Excel par référentiel.
- **Notifications** : aucune requise.
- **Tests requis** : 🆕 unicité codes/libellés, garde de suppression si référencé.
- **Dépendances** : aucune (socle).
- **⚠️ Incohérence à traiter** : les champs texte legacy de `Participant` (categorie, grade, vague, site, salle, type_concours, libelle_concours — L383-401 `formations/models.py`) dupliquent les Ref* → plan de migration vers FK (cf. synthèse D2).

## 2. ADMISSIONS / CONCOURS ✅ socle — 🆕 extensions concours

- **Objectif** : chaîne Candidat → Candidature → Admission, puis conversion en Inscription.
- **Acteurs** : Secrétariat, DIRECTION, Candidat (déposant).
- **Sous-modules** : candidats, candidatures, pièces, décisions d'admission ; 🆕 épreuves de concours.
- **Entités** : ✅ `admissions.Candidat`, `Candidature`, `PieceCandidature`, `Admission` (OneToOne → Candidature), `TypeCandidature`, `VoieAcces`, `TypePiece`, `ReglePiece`. 🆕 Épreuves de concours, jurys de sélection, listes d'admissibilité/admission.
- **Relations** : ✅ `Admission.candidature` OneToOne ; conversion explicite uniquement via `/api/scolarite/inscriptions/depuis-admission/`.
- **Workflows réels** : transition d'états explicite de la candidature (`/transition/`), décision d'admission (`/decision/`, `/annuler/`), vérification des pièces (`/deposer/`, `/verifier/`).
- **Statuts réels vérifiés** (`backend/admissions/models.py`) :
  - `Candidature.Statut` (L148) : BROUILLON, SOUMISE, EN_ATTENTE_DE_VERIFICATION, PIECES_INCOMPLETES, PIECES_VALIDEES, EN_ETUDE, ADMISSIBLE, ADMIS…
  - `PieceCandidature.Statut` (L272) : MANQUANTE, FOURNIE, EN_VERIFICATION, VALIDEE, REFUSEE, EXPIREE.
  - `Admission.Decision` (L317) : ADMIS, ADMIS_SOUS_RESERVE, EN_ATTENTE, REFUSEE, ANNULEE.
- **Endpoints réels** : `/api/admissions/candidats/`, `candidatures/` (+stats, transition, pieces), `admissions/` (+decision, annuler), `pieces/<id>/deposer|verifier|fichier`, `ref/<ressource>/`.
- **Écrans réels** : `pages/scolarite/Candidatures.jsx`, `Admissions.jsx`, `ImportExcel.jsx`.
- **Documents générés** : pièces justificatives (MEDIA_ROOT non servi publiquement — accès par vue authentifiée).
- **Notifications** : 🆕 à formaliser (aucun modèle Notification* dans admissions).
- **Permissions** : réutiliser `IsSecretariat`, `IsSecretariatOrDFRC` ; 🆕 rôle jury.
- **Tests réels** : `admissions/tests/test_admissions.py`, `test_candidatures.py` ; 🆕 tests épreuves concours.
- **Dépendances** : §1 (référentiels), §3 (passerelle vers inscription).


---

## 3. SCOLARITÉ ✅ (cœur LMD existant)

- **Objectif** : inscription administrative, dossier étudiant, groupes, événements, année académique.
- **Acteurs** : Secrétariat, DIRECTION, FINANCE (blocage impayés), étudiant (consultation).
- **Sous-modules** : année académique, dossier étudiant, inscriptions administratives, réinscriptions, groupes, événements, journal.
- **Entités** : ✅ `scolarite.AnneeAcademique` (année courante unique — test `test_une_seule_annee_courante`), `DossierEtudiant` (OneToOne → `formations.Participant`), `InscriptionAdministrative`, `AffectationGroupe`, `EvenementScolarite`, `JournalScolarite`, `Groupe`, référentiels LMD (`TypeFormation`, `Niveau`, `Parcours`, `Semestre`, `RegimeEtudes`, `StatutEtudiant` avec `bloque_inscription`).
- **Sources de vérité à préserver** : `formations.Participant.matricule` (unique) = identité étudiante ; `AnneeAcademique` courante unique ; `Maquette/UE/ECUE` (§4).
- **Statuts réels vérifiés** : `InscriptionAdministrative.Statut` (L361) : BROUILLON, EN_ATTENTE, A_VALIDER, VALIDEE, REJETEE, ANNULEE, SUSPENDUE, TERMINEE · `InscriptionPedagogique.Statut` (L555) : PREVUE, VALIDEE, ABANDONNEE, DISPENSEE — Origine (L561) : AUTOMATIQUE (générée depuis maquette) / MANUELLE.
- **Endpoints réels** : `/api/scolarite/annee-courante/`, `etudiants/` (+detail, evenements), `inscriptions/` (+stats, `depuis-admission/`, transition, affectations, retirer-groupe), `reinscriptions/`, `groupes/effectifs|repartition/`, `inscriptions/<pk>/passerelle/` (+analyser, lot).
- **Écrans réels** : `pages/scolarite/ScolariteDashboard.jsx`, `Inscriptions.jsx`, `FicheEtudiant.jsx`, `Groupes.jsx`.
- **Documents générés** : liste de classe PDF/Excel (`/api/exports/participants/liste-classe/...`).
- **Notifications** : via `JournalScolarite` (traçabilité) ; 🆕 notifications métier à définir.
- **Permissions** : `IsSecretariat`, `IsSecretariatOrDFRC`.
- **Tests réels** : `test_inscriptions.py`, `test_parcours_complet.py`, `test_core.py`, `test_groupes.py`, `test_participant_matricule.py`, `test_session_reactivation.py`.
- **⚠️ Double représentation groupes** : ✅ `scolarite.Groupe` + `AffectationGroupe` (LMD) vs ⚠️ `Participant.groupe` (texte L400) et `Module.groupe` (texte L609) — cf. synthèse D1.

## 4. PÉDAGOGIE ✅ (maquettes + inscriptions pédagogiques)

- **Objectif** : maquettes LMD versionnées, inscriptions pédagogiques (IP), passerelle ECUE↔RefModule.
- **Acteurs** : DIRECTION/DFRC (validation), Secrétariat, ENCADRANT.
- **Sous-modules** : maquettes versionnées, UE/ECUE, IP, passerelle.
- **Entités** : ✅ `scolarite.Maquette` (versionnée, `ref_formation`+`niveau`, Statut BROUILLON/ACTIVE/ARCHIVEE), `UE` (Caractere, rattachée à un Semestre), `ECUE` (passerelle possible vers `RefModule`), `InscriptionPedagogique`.
- **Endpoints réels** : `/api/scolarite/maquettes/` (+ ecues par semestre), `inscriptions/<pk>/pedagogie/` (+generer, ajouter), `pedagogie/<ligne_id>/`.
- **Écrans réels** : intégrés à `FicheEtudiant.jsx`/`Inscriptions.jsx` ; 🆕 écran dédié Maquettes si besoin.
- **Règles métier** : ⚠️ pas encore de garde-fou de modification d'une maquette ACTIVE (audit) ; 🆕 verrouillage proposé ; cohérence parcours↔formation contrôlée (L302, L448 `scolarite/models.py`).
- **Notifications** : 🆕.
- **Permissions** : `IsDFRC`, `IsSecretariatOrDFRC`.
- **Tests réels** : `test_referentiels.py` (MaquetteTests, MaquetteAPITests), `test_import_maquette.py` ; 🆕 test anti-modification d'ACTIVE.

## 5. ENSEIGNANTS / FORMATEURS ✅

- **Objectif** : gestion des formateurs, affectation aux modules, supervision.
- **Acteurs** : FORMATEUR, ENCADRANT, SUPERVISEUR, Secrétariat.
- **Entités** : ✅ `formations.Formateur`, `ModuleFormateur`, `Secretariat` (membres via `User.secretariat`), rôles ENCADRANT/SUPERVISEUR/FORMATEUR.
- **Endpoints réels** : `/api/formations/formateurs/` (+list, donnees-sensibles, finance-report), `<pk>/formateurs/` par formation, `superviseur/` (+generate-qr, qr).
- **Écrans réels** : `Formateurs.jsx`, `FicheFormateur.jsx`, `FinanceEncadrants.jsx` · Flutter : `profile_fiche_page.dart`.
- **Documents générés** : export formateur PDF/Excel (`/api/exports/formateur/...`).
- **Notifications** : 🆕 affectation module.
- **Permissions** : `IsEncadrant`, `IsSecretariatOrEncadrant`, `IsSecretariatOrEncadrantOrDFRC`, `CanManageModuleParticipant`.
- **Tests requis** : 🆕 chevauchement d'affectations (dépend EDT §6).

## 6. EDT — INTERFACE (décision actée : non intégré)

- **Objectif** : alimenter l'application externe `app-ept-injs-lmd 2026` par un **contrat de données lecture seule**. À cartographier comme **interface, pas comme module à construire**.
- **Entités** : aucune nouvelle ; le contrat lit `Groupe`, `Module`, `SessionModule`, `AffectationGroupe`, `InscriptionPedagogique`.
- **Endpoints réels** : `/api/scolarite/edt/` (contrat), `edt/groupes/`, `edt/enseignements/`, `edt/etudiants/` (`backend/scolarite/urls.py` L52-55).
- **Paramètre lié** : ✅ seed `edt_source_externe` (`parametres` 0003, modifiable=False).
- **Sens retour** : import manuel Excel des EDT produits → Cours/Séances (via `ImportExcel.jsx`).
- **Tests réels** : `scolarite/tests/test_edt_export.py`.

## 7. PRÉSENCES ✅ (badgeage QR)

- **Objectif** : pointage séances (web public désactivable, mobile sécurisé), rattrapages, audit anti-fraude.
- **Acteurs** : AUDITEUR/étudiant, FORMATEUR, Secrétariat.
- **Entités** : ✅ `presences.Pointage`, `AuditLog`, `DeviceBinding`, `Rattrapage` ; ✅ `formations.SessionModule`, `QRToken`.
- **Endpoints réels** : `/api/scan/` (public, gardé par `PUBLIC_QR_SCAN_ENABLED`), `/api/scan/secure/` (+heartbeat, check-status), `offline-data`, `mobile/config`, `me/historique|fiche`, `rattrapages/…`, `formations/<pk>/dashboard|presences|force-pointage|close-session/`, `devices/` (+unbind), `audit-logs/`, `participant/<pk>/notes-fiche/` (+export).
- **Écrans réels** : React `Rattrapages.jsx`, page serveur `badge.html` (gated) · Flutter `scan_page.dart`, `home_page.dart`, `history_page.dart`, `home_dashboard_page.dart`.
- **Statuts/règles** : heartbeat + géofence paramétrables (MOBILE_* dans settings.py), marquage ABSENT_NON_BADGE via `AUTO_ABSENT_DELAI_MINUTES`.
- **Notifications** : 🆕.
- **Permissions** : `IsParticipantOrReadOnly`, JWT pour /scan/secure/, throttling scan.
- **Tests réels** : `presences/tests.py` (ScanModuleExclusivityTest, PublicScanDisabledTest, ScanFormateurBadgeNormalizationTest…).

## 8. NOTES ✅ socle — 🆕 rattachement ECUE + verrouillage

- **Objectif** : saisie et synthèse des notes par module ; évolution vers le calcul ECTS par UE.
- **Acteurs** : FORMATEUR (saisie), Secrétariat/DIRECTION (validation), étudiant (consultation fiche).
- **Entités** : ✅ `formations.NoteModule`, `NoteModuleColonne`, `NoteModuleSynthese` (Mention), `NotificationModificationNote`. 🆕 Lien NoteModule→ECUE, verrouillage immuable.
- **Endpoints réels** : saisie notes module (`formations/urls.py`), `/api/presences/participant/<pk>/notes-fiche/` (+export fmt).
- **Écrans réels** : `NotesModule.jsx`, `ModuleDetail.jsx`.
- **⚠️ Incohérence actée** : `NoteModule` **non rattaché à l'ECUE** (0 référence ECUE dans `formations/models.py`) → rattachement à créer pour la validation LMD (cf. synthèse D4).
- **Règles métier (audit)** : ⚠️ ni verrouillage ni piste d'audit immuable — patterns à réutiliser : `AuditLog` (presences), `JournalScolarite`, `ParametreHistorique`.
- **Notifications réelles** : `NotificationModificationNote` (✅).
- **Permissions** : `IsEncadrant` / `IsSecretariatOrEncadrantOrDFRC`.
- **Tests réels** : `test_notes_fiche_export.py`, `test_note_notifications.py` ; 🆕 test immutabilité post-verrou.


## 9. JURYS 🆕 (à créer)

- **Objectif** : instances de délibération semestrielles/annuelles LMD et PV officiels.
- **Acteurs** : DIRECTION (président de jury), Secrétariat (secrétariat du jury), FORMATEUR (avis), SUPERVISEUR (consultation).
- **Sous-modules** : sessions de jury, composition, délibération, PV, décisions compensées.
- **Entités** : 🆕 `SessionJury`, `MembreJury`, `DecisionJury`, `PVJury` — socle à réutiliser : ✅ `suiviEvaluation.DecisionPedagogique` (décision par module/étudiant), ✅ `scolarite.InscriptionPedagogique.Statut`, ✅ `scolarite.StatutEtudiant.bloque_inscription`.
- **Relations proposées** : `DecisionJury` → `DossierEtudiant` + `AnneeAcademique` + `Semestre` ; `PVJury` → `SessionJury` + `SignatureRapport` (pattern existant ✅ `statistiques.SignatureRapport`).
- **Workflows** : 🆕 ouverture session → saisie propositions → délibération → validation PV → application des décisions (via `JournalScolarite`).
- **Statuts** : 🆕 CONVOQUEE / EN_DELIBERATION / VALIDEE / PV_EMIS.
- **Règles métier** : compensation d'UE (paramètres réutilisables : seed `seuil_validation_ue`, `credits_ects_ue` ✅ parametres 0003) ; verrou des notes exigé avant délibération (dépend §8).
- **Endpoints proposés** : `/api/jurys/sessions/`, `/api/jurys/sessions/<pk>/membres/`, `/api/jurys/sessions/<pk>/deliberer/`, `/api/jurys/sessions/<pk>/pv/`.
- **Écrans proposés** : React `pages/jurys/JurySessions.jsx`, `JuryDeliberation.jsx`, `PVJury.jsx` — Flutter : consultation décision via `profile_fiche_page.dart` (existant).
- **Documents générés** : 🆕 PV de jury PDF (moteur `exports/` existant).
- **Notifications** : 🆕 (pattern `NotificationRapport` ✅ statistiques).
- **Permissions** : 🆕 `IsDirection` — modèle : `IsDFRC` (✅ authentication/permissions.py L106).
- **Tests requis** : 🆕 impossibilité de délibérer avec notes non verrouillées ; unicité décision par étudiant/semestre.
- **Dépendances** : §8 (notes verrouillées), §4 (maquettes), §3 (inscriptions).

## 10. DIPLÔMES 🆕 (à créer)

- **Objectif** : délivrance et traçabilité des diplômes LMD (Licence/Master).
- **Acteurs** : DIRECTION, Secrétariat, ARCHIVE (rôle existant ✅).
- **Entités** : 🆕 `Diplome`, `DiplomeDelivre` — sources de vérité à préserver : `Participant.matricule`, `AnneeAcademique`, `Parcours`, décision de jury finale (§9).
- **Endpoints proposés** : `/api/diplomes/demandes/`, `/api/diplomes/delivrances/`, `/api/diplomes/<pk>/attestation/`.
- **Écrans proposés** : React `pages/diplomes/Diplomes.jsx`, `AttestationDetail.jsx`.
- **Documents générés** : 🆕 diplôme PDF, attestation de réussite, relevé de notes définitif (moteur `exports/`).
- **Notifications** : 🆕 (pattern `NotificationFinanceAjustement` réutilisable).
- **Permissions** : 🆕 combinaison `IsSecretariatOrDFRC` + rôle ARCHIVE pour consultation des émis.
- **Tests requis** : 🆕 délivrance impossible sans décision jury VALIDEE ; unicité du numéro d'émission.
- **Dépendances** : §9 (jurys), §3 (DossierEtudiant), §8 (synthèse de notes).

## 11. STAGES 🆕 (à créer)

- **Objectif** : gestion des stages et conventions (volet LMD).
- **Acteurs** : ENCADRANT (tuteur), Secrétariat, étudiant (AUDITEUR), organisme externe.
- **Entités** : 🆕 `ConventionStage`, `OrganismeAccueil`, `TuteurExterne`, `EvaluationStage` — rattachés à `DossierEtudiant` (✅) et `AnneeAcademique` (✅).
- **Endpoints proposés** : `/api/stages/conventions/`, `/api/stages/conventions/<pk>/validation/`, `/api/stages/evaluations/`.
- **Écrans proposés** : React `pages/stages/Stages.jsx`, `ConventionDetail.jsx`.
- **Statuts proposés** : 🆕 BROUILLON / SOUMISE / SIGNEE / EN_COURS / SOUTENUE / VALIDEE (aligner sur le pattern `Candidature.Statut` ✅ admissions).
- **Documents générés** : 🆕 convention PDF, attestation de stage.
- **Notifications** : 🆕 échéances de remise de rapport.
- **Permissions** : réutiliser `IsSecretariatOrEncadrant` (✅).
- **Dépendances** : §3, §9 (validation pédagogique finale).


## 12. FINANCES ÉTUDIANTES ⚠️ double socle — 🆕 frais de scolarité LMD

- **Objectif** : distinguer le volet **financement formateurs** (existant) du volet **frais de scolarité étudiant LMD** (à créer).
- **Existant (formateurs)** : ✅ `formations.FinanceSettings`, `FinanceAjustement` (workflow valider/rejeter ✅ endpoints), `NotificationFinanceAjustement` ; endpoints `/api/formations/finance/dashboard|settings|encadrants|ajustements|notifications/` ; écrans `FinanceDashboard.jsx`, `FinanceAjustements.jsx`, `FinanceParametrage.jsx`, `FinanceEncadrants.jsx` ; exports `/api/exports/finance/...`.
- **À créer (étudiants)** : 🆕 `EcheancierPaiement`, `Paiement`, `RecuPaiement` rattachés à `InscriptionAdministrative` (✅) — module « Frais de scolarité » absent de l'existant, **double représentation volontaire** : deux domaines de finance distincts (cf. synthèse D5).
- **Endpoints proposés** : `/api/scolarite/finances/echeanciers/`, `/finances/paiements/`, `/finances/recus/<pk>/`.
- **Écrans proposés** : React `pages/scolarite/FinancesEtudiant.jsx` (⚠️ ne pas fusionner avec `FinanceDashboard.jsx` existant).
- **Règles métier** : blocage d'inscription si impayés — coupler à `StatutEtudiant.bloque_inscription` (✅ L243 `scolarite/models.py`).
- **Permissions** : rôle FINANCE (existant ✅) + `IsSecretariat`.
- **Tests requis** : 🆕 cohérence échéancier/paiements, déclenchement/levée du blocage.
- **Dépendances** : §3 (inscriptions), §10 (attestation solde pour diplôme).

## 13. ADMINISTRATION / PATRIMOINE 🆕 (à créer)

- **Objectif** : inventaire, affectation des salles/équipements, gestion documentaire.
- **Existant partiel** : ✅ `RefSite`, `RefBatiment`, `RefSalle` (référentiels lieux) ; ✅ rôle ARCHIVE ; écrans `archives/` existants mais dédiés aux **documents pédagogiques** (`ArchiveCahiersAppel.jsx`, `ArchiveListesNotes.jsx`, `ArchivesDashboard.jsx`) — ⚠️ signalé : ne pas confondre « archives pédagogiques » (existantes) et « patrimoine » (à créer).
- **Entités à créer** : 🆕 `Equipement`, `Inventaire`, `AffectationSalle`, `DocumentPatrimoine`.
- **Endpoints proposés** : `/api/patrimoine/equipements/`, `/api/patrimoine/affectations/`.
- **Écrans proposés** : React `pages/patrimoine/Inventaire.jsx`.
- **Documents générés** : 🆕 états d'inventaire PDF.
- **Notifications** : 🆕.
- **Permissions** : 🆕 rôle dédié ou ARCHIVE + ADMIN.
- **Dépendances** : §1 (référentiels lieux — à étendre sans dupliquer RefSalle).

## 14. STATISTIQUES ✅ (socle existant, à étendre LMD)

- **Objectif** : pilotage, alertes de seuils, rapports signés, bilans.
- **Acteurs** : DIRECTION, Secrétariat, superviseurs.
- **Entités** : ✅ `statistiques.ConfigAlerteSeuil`, `Rapport` (workflow ✅ endpoint `rapports/<id>/workflow/`), `ObservationQualitative`, `SignatureRapport`, `NotificationRapport`.
- **Endpoints réels** : `/api/statistiques/secretariats/`, `alertes/seuils/`, `rapports/…`, `point-journalier/` (+export), `bilans/` (+export), `bilan-fac/` (+périmètre, export).
- **Écrans réels** : `Statistiques.jsx`, `AnalyseQualitative.jsx` ; Flutter `home_dashboard_page.dart`.
- **Documents générés** : exports point journalier, bilans, bilan-fac (réels).
- **Notifications réelles** : `NotificationRapport` (✅).
- **Extension à créer** : 🆕 indicateurs LMD (taux de réussite par UE, effectifs par niveau/parcours) alimentés par §3/§4/§9 — sans modifier les endpoints existants.
- **Permissions** : à recadrer par rôle DIRECTION/Secrétariat.
- **Tests réels** : à vérifier (`statistiques/tests.py`).

## 15. SÉCURITÉ ✅ (socle existant, à durcir par module)

- **Objectif** : authentification, liaison device, audit, conformité données sensibles.
- **Existant** : ✅ JWT SimpleJWT, `DeviceBinding` + endpoint `devices/<id>/unbind/`, `AuditLog` presences (`audit-logs/`), endpoint `formateurs/<pk>/donnees-sensibles/` (droit RGPD-like), `must_change_password`, throttling login/scan, `guarded_logout.dart` côté mobile.
- **À créer** : 🆕 piste d'audit immuable des notes et maquettes (réutiliser le pattern `AuditLog`/`ParametreHistorique`), permissions par module LMD (jurys, diplômes, finances étudiantes).
- **Tests requis** : 🆕 tests d'accès croisés par rôle sur chaque nouveau domaine (pattern des tests `test_api_access.py` existants).


---

## 📌 SYNTHÈSE DES DOUBLES REPRÉSENTATIONS SIGNALÉES (à traiter, pas à implémenter ici)

| # | Double représentation | Existant vérifié | Cible recommandée |
|---|----------------------|------------------|-------------------|
| D1 | Groupes | ✅ `scolarite.Groupe` + `AffectationGroupe` (LMD) **vs** ⚠️ `Participant.groupe` (texte, L400) + `Module.groupe` (texte, L609) | Groupe LMD = source de vérité ; champs texte conservés comme legacy lecture seule pour le socle formation continue |
| D2 | Catégorisation participant | ⚠️ champs texte legacy `categorie/grade/vague/site/salle/type_concours/libelle_concours` (Participant) **vs** ✅ `RefCategorie`, `RefGrade`, `RefVague`, `RefSite`, `RefSalle` | Migration progressive texte → FK Ref*, affichage dual le temps de la transition |
| D3 | Formation | ⚠️ `formations.Formation` **sans FK vers `RefFormation`** (grep confirmé : 0 occurrence) **vs** ✅ `RefFormation` référentiel ; ✅ `Maquette.ref_formation` et ✅ `Groupe.ref_formation` existent déjà côté scolarite | Ajout futur d'une FK `Formation.ref_formation` (nullable) comme pont — à étudier, non implémenté |
| D4 | Notes / ECUE | ⚠️ `NoteModule` (formations) **non rattaché à l'ECUE** (0 référence ECUE dans formations/models.py) **vs** ✅ `scolarite.ECUE` (passerelle vers `RefModule` déjà prévue en docstring) | Rattachement NoteModule→ECUE à créer pour la validation ECTS |
| D5 | Finances | ⚠️ finance **formateurs** (✅ FinanceSettings/FinanceAjustement) **vs** 🆕 finance **étudiante** (frais de scolarité) | Deux sous-modules distincts, jamais fusionnés dans un même modèle |

## 📌 Modules absents de l'existant — récapitulatif « à créer »

**Concours** (épreuves/validations — au-delà de la chaîne admissions existante), **Jurys**, **Diplômes**, **Stages**, **Frais de scolarité**, **Documents officiels/diplômes délivrés**, **Validation ECTS** (calcul par UE), **Patrimoine**. Positionnés en §2, §9, §10, §11, §12, §13 avec dépendances.

## 📌 Interfaces (non modules)

- **EDT externe** : contrat lecture seule `/api/scolarite/edt/` (contrat, groupes, enseignements, etudiants) → `app-ept-injs-lmd 2026` ; retour par import Excel manuel (`ImportExcel.jsx`). Paramètre `edt_source_externe` verrouillé en seed (modifiable=False).

---

## Points de vigilance hérités de l'audit (rappel)

1. `backend/parametres/` et `backend/formations/referentiels_excel.py` **non versionnés dans Git** (audit 09/06/2026) — à committer avant tout nouveau développement (risque critique).
2. Maquettes ACTIVE modifiables sans garde-fou — à traiter en §4 avant le module Jurys (§9).
3. Notes sans verrouillage/audit immuable — prérequis du module Jurys (§9).
