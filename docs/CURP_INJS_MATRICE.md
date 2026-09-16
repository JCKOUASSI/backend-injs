# CURP-INJS — Matrice des rôles et permissions (document de travail J2)

> Généré par `python manage.py generer_matrice_habilitations` le 2026-09-14.
> **Statut : PROVISOIRE, en attente de la validation ligne à ligne de l'expert
> fonctionnel (jalon J2).** Les cases suivies d'une astérisque (`*`) portent sur
> des modules absents de l'annexe A2 ; elles sont proposées par l'équipe de
> réalisation et doivent être confirmées en atelier.
>
> Lecture du tableau des niveaux : **N0** consultation très limitée ·
> **N1** consultation · **N2** saisie et traitement · **N3** validation ·
> **N4** administration et décision. Un tiret signifie aucun accès. Les
> limitations « à ses ECUE » ou « à son propre dossier » sont portées par le
> périmètre du rôle, pas par le niveau.

## 1. Matrice rôle × module (annexe A2 + cases provisoires)

| Rôle | administration | candidatures | scolarite | pedagogie | enseignants | evaluations | jurys | diplomation | finances_etud | stages | rh | patrimoine | edt | presences | statistiques | administrations | finances_form | exports | parametres | referentiels |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ADMIN_SYSTEME | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4 | N4* | N4* | N4* | N4* | N4* |
| DIRECTION_GENERALE | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N3 | N1 | N1 | N1 | N1 | N1 | N1 | N4 | N1* | N1* | N1* | — | N1* |
| DIRECTION_ETUDES | N1 | N1 | N3 | N3 | N1 | N3 | N3 | N3 | — | N1 | — | — | N3 | N1 | N3 | N1* | — | N1* | — | N1* |
| SCOLARITE | N1 | N2 | N3 | N2 | N1 | N2 | N1 | N2 | N1 | N1 | — | — | N2 | N2 | N1 | N1* | — | N1* | — | N2* |
| RESPONSABLE_PEDAGOGIQUE | — | N1 | N1 | N3 | N2 | N2 | N2 | N1 | — | N2 | — | — | N3 | N2 | N1 | — | — | N1* | — | N2* |
| AGENT_CANDIDATURE | — | N2 | N1 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | N1* |
| AGENT_CONTROLE_DOSSIERS | — | N2 | N1 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | N1* |
| RESPONSABLE_CONCOURS | — | N4 | N2 | N1 | N1 | N2 | — | — | — | — | — | — | N1 | N1 | N1 | — | — | N1* | — | N1* |
| AGENT_ADMISSIONS | — | N2 | N2 | N1 | — | — | — | — | N1 | — | — | — | — | — | — | — | — | — | — | N1* |
| AGENT_INSCRIPTIONS | — | N1 | N2 | N1 | — | — | — | — | N1 | — | — | — | — | — | — | — | — | — | — | N1* |
| GESTIONNAIRE_ETUDIANTS | — | N1 | N2 | N1 | — | N1 | — | N1 | N1 | N1 | — | — | N1 | N1 | N1 | — | — | N1* | — | N1* |
| RESPONSABLE_FORMATION | — | N1 | N1 | N3 | N2 | N2 | N2 | N1 | — | N2 | — | — | N2 | N1 | N1 | — | — | N1* | — | N2* |
| GESTIONNAIRE_GROUPES | — | — | N1 | N2 | N1 | — | — | — | — | — | — | — | N2 | N1 | — | — | — | — | — | N1* |
| GESTIONNAIRE_COURS | — | — | N1 | N2 | N1 | N1 | — | — | — | — | — | N1 | N2 | N1 | — | — | — | — | — | N1* |
| GESTIONNAIRE_MAQUETTES | — | — | N1 | N3 | N1 | N1 | — | — | — | — | — | — | N1 | — | — | — | — | — | — | N2* |
| ENSEIGNANT | — | — | — | N1 | N1 | N2 | — | — | — | N1 | — | — | N1 | N2 | — | — | — | — | — | N1* |
| RESPONSABLE_UE_ECUE | — | — | — | N2 | N2 | N3 | N1 | — | — | N1 | — | — | N2 | N2 | N1 | — | — | N1* | — | N1* |
| GESTIONNAIRE_CHARGES | — | — | — | N2 | N2 | — | — | N1 | — | N1 | — | N1 | N2 | N1 | N1 | — | N1* | N1* | — | N1* |
| GESTIONNAIRE_NOTES | — | — | N1 | N1 | N1 | N2 | N1 | — | — | — | — | — | — | N1 | N1 | — | — | N1* | — | N1* |
| MEMBRE_JURY | — | — | N1 | N1 | — | N1 | N2 | N1 | — | — | — | — | — | N1 | N1 | — | — | N1* | — | N1* |
| RESPONSABLE_JURY | — | — | N1 | N1 | — | N3 | N4 | N2 | — | — | — | — | — | N1 | N1 | — | — | N1* | — | N1* |
| RESPONSABLE_GRADUATION | — | — | N1 | N1 | — | N1 | N1 | N3 | — | — | — | — | — | — | N1 | — | — | N1* | — | N1* |
| RESPONSABLE_DIPLOMATION | — | — | N1 | N1 | — | N1 | N1 | N4 | — | — | — | — | — | — | N1 | — | — | N1* | — | N1* |
| GESTIONNAIRE_FINANCES_ETUD | — | N1 | N1 | — | — | — | — | N1 | N2 | — | — | — | — | — | N1 | — | — | N1* | — | N1* |
| VALIDATEUR_FINANCIER | — | — | N1 | — | — | — | — | N1 | N3 | — | — | N1 | — | — | N1 | — | N3* | N1* | — | N1* |
| GESTIONNAIRE_VACATIONS | — | — | — | N1 | N2 | — | — | — | N2 | — | N1 | — | N1 | N1 | N1 | — | N2* | N1* | — | N1* |
| GESTIONNAIRE_STAGES | — | — | N1 | N1 | N1 | N1 | — | — | N1 | N2 | — | — | N1 | N1 | N1 | — | — | N1* | — | N1* |
| GESTIONNAIRE_RH | — | — | — | — | N1 | — | — | — | N1 | — | N3 | N1 | N1 | N1 | N1 | — | — | N1* | — | N1* |
| GESTIONNAIRE_PATRIMOINE | — | — | — | — | — | — | — | — | N1 | — | N1 | N2 | N1 | — | N1 | — | — | N1* | — | N1* |
| GESTIONNAIRE_ESPACES | — | — | — | N1 | — | — | — | — | — | — | — | N2 | N2 | N1 | N1 | — | — | N1* | — | N1* |
| GESTIONNAIRE_COURRIERS | N2 | — | N1 | — | — | — | — | N1 | — | — | N1 | N1 | — | — | — | N2* | — | — | — | N1* |
| ARCHIVISTE | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1 | N1* | — | N1* | — | N1* |
| ETUDIANT | — | — | N1 | N1 | — | N1 | N0 | N1 | N1 | N1 | — | — | N1 | N1 | — | — | — | — | — | — |
| CANDIDAT | — | N1 | — | — | — | — | — | N0 | — | — | — | — | — | — | — | — | — | — | — | — |
| CONSULTATION | — | N0 | N0 | N0 | N0 | N0 | — | N0 | — | N0 | — | N0 | N0 | N0 | N1 | — | — | N1* | — | — |

## 2. Référentiel des rôles (annexe A1)

| Code | Libellé | Domaine | Niv. | Périmètre | Module requis | Sensible | Canal |
|---|---|---|---|---|---|---|---|
| `ADMIN_SYSTEME` | Administrateur système | ADMINISTRATION | N4 | INJS_ENTIER | — | oui | web/mobile |
| `DIRECTION_GENERALE` | Direction générale | ADMINISTRATION | N4 | INJS_ENTIER | — | oui | web/mobile |
| `DIRECTION_ETUDES` | Direction des études | ADMINISTRATION | N4 | INJS_ENTIER | — | oui | web/mobile |
| `SCOLARITE` | Scolarité | ADMINISTRATION | N3 | SECRETARIAT | scolarite | non | web/mobile |
| `RESPONSABLE_PEDAGOGIQUE` | Responsable pédagogique | ADMINISTRATION | N3 | FORMATION | scolarite | non | web/mobile |
| `AGENT_CANDIDATURE` | Agent de candidature | CANDIDATURES | N2 | INJS_ENTIER | admissions | non | web/mobile |
| `AGENT_CONTROLE_DOSSIERS` | Agent de contrôle des dossiers | CANDIDATURES | N2 | INJS_ENTIER | admissions | non | web/mobile |
| `RESPONSABLE_CONCOURS` | Responsable concours et sélection | CANDIDATURES | N3 | INJS_ENTIER | admissions | oui | web/mobile |
| `AGENT_ADMISSIONS` | Agent admissions | SCOLARITE | N2 | SECRETARIAT | admissions | non | web/mobile |
| `AGENT_INSCRIPTIONS` | Agent inscriptions | SCOLARITE | N2 | SECRETARIAT | scolarite | non | web/mobile |
| `GESTIONNAIRE_ETUDIANTS` | Gestionnaire étudiants | SCOLARITE | N2 | SECRETARIAT | scolarite | non | web/mobile |
| `RESPONSABLE_FORMATION` | Responsable de formation | PEDAGOGIE | N3 | FORMATION | scolarite | non | web/mobile |
| `GESTIONNAIRE_GROUPES` | Gestionnaire des groupes | PEDAGOGIE | N2 | FORMATION | scolarite | non | web/mobile |
| `GESTIONNAIRE_COURS` | Gestionnaire des cours | PEDAGOGIE | N2 | FORMATION | scolarite | non | web/mobile |
| `GESTIONNAIRE_MAQUETTES` | Gestionnaire des maquettes | PEDAGOGIE | N3 | FORMATION | scolarite | non | web/mobile |
| `ENSEIGNANT` | Enseignant | ENSEIGNANTS | N2 | MODULE_ECUE | scolarite | non | MOBILE |
| `RESPONSABLE_UE_ECUE` | Responsable UE / ECUE | ENSEIGNANTS | N3 | MODULE_ECUE | scolarite | non | web/mobile |
| `GESTIONNAIRE_CHARGES` | Gestionnaire des charges enseignantes | ENSEIGNANTS | N2 | FORMATION | scolarite | non | web/mobile |
| `GESTIONNAIRE_NOTES` | Gestionnaire des notes | EVALUATIONS | N2 | FORMATION | suiviEvaluation | non | web/mobile |
| `MEMBRE_JURY` | Membre de jury | EVALUATIONS | N2 | FORMATION | jurys | non | web/mobile |
| `RESPONSABLE_JURY` | Responsable de jury | EVALUATIONS | N4 | FORMATION | jurys | oui | web/mobile |
| `RESPONSABLE_GRADUATION` | Responsable graduation | DIPLOMATION | N3 | INJS_ENTIER | graduation | oui | web/mobile |
| `RESPONSABLE_DIPLOMATION` | Responsable diplômation | DIPLOMATION | N4 | INJS_ENTIER | graduation | oui | web/mobile |
| `GESTIONNAIRE_FINANCES_ETUD` | Gestionnaire finances étudiantes | FINANCE | N2 | INJS_ENTIER | finances_etudiantes | oui | web/mobile |
| `VALIDATEUR_FINANCIER` | Validateur financier | FINANCE | N3 | INJS_ENTIER | finances_etudiantes | oui | web/mobile |
| `GESTIONNAIRE_VACATIONS` | Gestionnaire vacations formateurs | FINANCE | N2 | INJS_ENTIER | formations | oui | web/mobile |
| `GESTIONNAIRE_STAGES` | Gestionnaire des stages | STAGES | N2 | FORMATION | stages | non | web/mobile |
| `GESTIONNAIRE_RH` | Gestionnaire ressources humaines | RH | N3 | INJS_ENTIER | ressources_humaines | oui | web/mobile |
| `GESTIONNAIRE_PATRIMOINE` | Gestionnaire du patrimoine | PATRIMOINE | N2 | SITE | patrimoine | non | web/mobile |
| `GESTIONNAIRE_ESPACES` | Gestionnaire des espaces | PATRIMOINE | N2 | SITE | patrimoine | non | web/mobile |
| `GESTIONNAIRE_COURRIERS` | Gestionnaire courriers et documents | ADMINISTRATION_GENERALE | N2 | SERVICE | administrations | non | web/mobile |
| `ARCHIVISTE` | Archiviste | ADMINISTRATION_GENERALE | N2 | INJS_ENTIER | — | non | web/mobile |
| `ETUDIANT` | Étudiant / auditeur | DESTINATAIRES | N1 | PROPRE_COMPTE | presences | non | MOBILE |
| `CANDIDAT` | Candidat | DESTINATAIRES | N0 | PROPRE_COMPTE | admissions | non | web/mobile |
| `CONSULTATION` | Consultation restreinte | DESTINATAIRES | N1 | INJS_ENTIER | — | non | web/mobile |

Le recueil titre « 33 rôles » ; le tableau A1 comporte 35 lignes, dont trois
destinataires du service (`ETUDIANT`, `CANDIDAT`, `CONSULTATION`). Les 35
lignes sont chargées par sécurité additive.

## 3. Incompatibilités de séparation des tâches (J5)

- `GESTIONNAIRE_NOTES` est incompatible avec `RESPONSABLE_JURY` (et réciproquement).
- `AGENT_INSCRIPTIONS` est incompatible avec `GESTIONNAIRE_FINANCES_ETUD` (et réciproquement).
- `GESTIONNAIRE_FINANCES_ETUD` est incompatible avec `VALIDATEUR_FINANCIER` (et réciproquement).
- `AGENT_CANDIDATURE` est incompatible avec `AGENT_CONTROLE_DOSSIERS` (et réciproquement).
- `RESPONSABLE_GRADUATION` est incompatible avec `GESTIONNAIRE_NOTES` (et réciproquement).

## 4. Permissions critiques (motif obligatoire, double validation, journalisation renforcée)

- `administration.attribution.valider`
- `administration.compte.modifier`
- `administration.role.creer`
- `administration.role.modifier`
- `diplomation.diplome.revoquer`
- `diplomation.diplome.valider`
- `edt.emploi_du_temps.publier`
- `evaluations.note.verrouiller`
- `exports.export_sensible.generer`
- `finances_etud.paiement.valider`
- `finances_etud.remboursement.valider`
- `jurys.pv.signer`
- `jurys.resultat.publier`
- `parametres.parametre.administrer`
- `presences.emargement.forcer`

## 5. Correspondance avec les 12 rôles existants (annexe A6, appliquée en U8)

| Rôle existant | Rôles métier CURP |
|---|---|
| `ADMIN` | `ADMIN_SYSTEME` |
| `CHEF_CPFAE_ADMIN` | `ADMIN_SYSTEME`, `DIRECTION_ETUDES` |
| `CPFAE_ADMIN` | `SCOLARITE`, `GESTIONNAIRE_COURS` |
| `DIRECTION` | `DIRECTION_GENERALE` |
| `CHEF_SECRETARIAT` | `SCOLARITE`, `AGENT_INSCRIPTIONS`, `AGENT_ADMISSIONS`, `GESTIONNAIRE_ETUDIANTS` |
| `SECRETARIAT` | `AGENT_INSCRIPTIONS`, `AGENT_ADMISSIONS`, `GESTIONNAIRE_ETUDIANTS` |
| `FINANCE` | `GESTIONNAIRE_FINANCES_ETUD`, `GESTIONNAIRE_VACATIONS` |
| `ARCHIVE` | `ARCHIVISTE` |
| `ENCADRANT` | `ENSEIGNANT`, `GESTIONNAIRE_GROUPES` |
| `SUPERVISEUR` | `RESPONSABLE_PEDAGOGIQUE` |
| `FORMATEUR` | `ENSEIGNANT` |
| `AUDITEUR` | `ETUDIANT` |

## 6. Modules du catalogue (annexe A3) et activation conditionnelle

- `administration` — Administration des habilitations (application Django : `habilitations`).
- `candidatures` — Candidatures et concours (application Django : `admissions`).
- `scolarite` — Scolarité (application Django : `scolarite`).
- `pedagogie` — Pédagogie, maquettes et UE/ECUE (application Django : `scolarite`).
- `enseignants` — Enseignants et charges (application Django : `scolarite`).
- `evaluations` — Évaluations et notes (application Django : `suiviEvaluation`).
- `jurys` — Jurys et délibérations (application Django : `jurys`).
- `diplomation` — Graduation et diplômation (application Django : `graduation`).
- `finances_etud` — Finances étudiantes (application Django : `finances_etudiantes`, conditionnel MOA).
- `finances_form` — Rémunération et vacations des formateurs (application Django : `formations`).
- `stages` — Stages et conventions (application Django : `stages`, conditionnel MOA).
- `rh` — Ressources humaines (application Django : `ressources_humaines`, conditionnel MOA).
- `patrimoine` — Patrimoine, espaces et réservations (application Django : `patrimoine`, conditionnel MOA).
- `edt` — Emplois du temps (application Django : `edts`).
- `presences` — Présences et émargements (application Django : `presences`).
- `administrations` — Courriers et documents administratifs (application Django : `administrations`, conditionnel MOA).
- `statistiques` — Statistiques et rapports (application Django : `statistiques`).
- `exports` — Exports de données (application Django : `exports`).
- `parametres` — Paramètres généraux (application Django : `parametres`).
- `referentiels` — Référentiels (application Django : `referentiels`).
