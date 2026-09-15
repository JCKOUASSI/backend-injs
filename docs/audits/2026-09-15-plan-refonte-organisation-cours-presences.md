# Plan — refonte Organisation / Cours-Formations / Présences QR (d'après le Modèle fonctionnel de référence)

**Date :** 2026-09-15 · **Statut :** TROIS LOTS LIVRÉS (A `7520d7e`, C `4c04dbb`, B `86ceb57`) —
gate feux verts passée (backend 1672 OK, frontend 1725 OK + lint + build) ;
rapport détaillé : `docs/audits/2026-09-15-rapport-refonte-organisation-cours-presences.md`.
**Source :** `workspace/uploads/` — *Audit complet détaillé* (11/09/2026),
*Modèle fonctionnel de référence INJS-LMD 2026* (MODULES 04, 08, 13 ; §§ 15, 17-18, 35),
*Rapport de mise en œuvre* (gap analysis, D1-D5, phases 1-10).
**Méthode :** zéro régression — additif, réversible, nothing-but-bridge ; les notions
« à remplacer » restent accessibles (redirections, champs conservés) ; tests + feux verts à
chaque lot. S'inscrit dans la continuité des LOT 4-6 (CURP) et du lot L8 (GET-INJS).

---

## Lot A — « Secrétariats » → « Directions / Départements / Services » (modèle 13)

Le modèle cible (13.3-13.6) : hiérarchie configurable `INJS → Directions → Départements →
Services (→ Bureaux/Unités)` ; la structure porte responsable, adjoint, contact, localisation ;
« un secrétariat est rattaché à une structure » (§15) — il **devient un service de support
rattaché**, plus l'entité racine de l'application.

| Action | Détail | Régression |
|---|---|---|
| Champs additifs Direction/Departement | responsable, adjoint (FK User), téléphone, email, localisation | aucune (nullables) |
| Champs additifs Service RH | code, responsable, adjoint, téléphone, email, localisation | aucune |
| Pont Secrétariat → structure | `Secretariat.direction` + `Secretariat.departement` (nullables, au plus un, CheckConstraint) | ancienne table intacte |
| API unifiée `/api/organisation/` | arbre (directions→départements→services→secrétariats rattachés, effectifs via CURP `CompteUtilisateur.departements/services` et `User.secretariat`) ; CRUD quatre entités ; écriture = DFRC ; suppression = désactivation ; audit `core` (ORGANISATION_*) | nouvelles routes uniquement |
| Console CURP | champs exposés en lecture dans les écrans organisation_* (déjà posés LOT 4/5) | additif |
| Frontend | écran « Directions / Départements / Services » (`/organisation`, quatre onglets, CRUD modaux) ; le menu « Secrétariats » est **remplacé** par cette entrée ; `/secretariats` redirige vers l'onglet secrétariats ; l'écran legacy reste monté (compatibilité URL directe) | aucune page supprimée |
| Alignement habilitations | périmètres SECRETARIAT/DIRECTION/DEPARTEMENT/SERVICE + résolveurs hiérarchiques : déjà livrés au LOT 5 — l'organigramme posé ici les alimente | — |

## Lot C — Présences par QR : séance LMD automatique + émargement manuel à motif (modèle 08)

Le socle QR existe pour le legacy (formation → SessionModule → scan/heartbeat/geofence/rattrapage,
`séance` au sens `formations.SessionModule`) — **rien de neuf côté LMD** : le modèle 08 et le
rapport §4 exigent la chaîne `EDT → SÉANCE → ÉMARGEMENT → JUSTIFICATION → STATS`, l'écart
« disponibilité immédiate de la séance pour la génération de QR » n'étant pas branché sur
`edts.Creneau`.

| Action | Détail |
|---|---|
| Modèle | `Pointage.creneau` (FK nullable → edts.Creneau) ; `QrTokenSeance` (uuid, validité = début −10 min → fin +15 min, tolérances paramétrables via Parametre, usage unique par participant) |
| QR séance | `POST /api/presences/seances-edt/<creneau>/qr/` (générer/rafraîchir) — garde : séance planifiée et non clôturée |
| Scan auto | `POST /api/presences/seances-edt/scan/` — vérifs serveur du modèle 08.6 : compte authentifié, token valide, fenêtre, **inscrit au groupe de la séance**, doublon (2e scan = sortie) ; géo/device best effort (champs déjà là) |
| Émargement manuel | `GET …/<creneau>/presences/` (liste nominative du groupe, statuts présence/retard/absent/non-badgé) ; `POST …/<creneau>/emargement/` — entrées [{participant, statut, motif}] : **motif obligatoire** pour forcer/corriger un pointage existant (modèle 08.14 « forçage contrôlé »), chaque ligne auditée (avant/après), auteur + horodatage ; droits : enseignant de l'affectation, encadrant responsable, secrétariat, DFRC |
| Clôture automatique | `POST …/<creneau>/autoclore/` (entrées sans sortie → sortie = fin de séance, RETARD/ABSENT selon seuils ; non-badgés → ABSENT) + commande `auto_close_pointages` existante conservée |
| Frontend | écran `/edt/presences` : choisir une séance (creneaux de la semaine filtrés groupe/enseignant), afficher le QR (lib `qrcode` déjà présente), liste d'émargement cochable + motif, clôture auto ; bouton d'accès depuis la fiche séance EDT |
| CURP | codes `presences.*` du catalogue ; nouvelles vues branchées `ExigePermission` **en OBSERVATION** (règle LOT 5) + gating legacy |

## Lot B — Cours & Formations alignés sur la chaîne LMD (modèle 04 ; double représentations D3)

| Action | Détail |
|---|---|
| D3 réel | `formations.Formation.ref_formation` (FK nullable → RefFormation, SET_NULL) — la « formation opérationnelle » est rattachée au « cycle » du référentiel ; sérialiseurs + écran Formations (select cycle) ; backfill idempotent en commande (matching par intitulé, non résolus comptés, **aucune perte**) |
| RefFormation enrichi | code, type_diplome, domaine, mention, duree_annees, nb_semestres, nb_credites, description (modèle 04.4) — additif ; exposé API `/formations/ref/formations/` |
| Vue « Cours » | `GET /api/pedagogie/cours/` : la « ligne de cours » du modèle 17 = affectation pédagogique (ECUE × groupe × enseignant × type CM/TD/TP × volume) **jonchée** au planning EDT (jour, horaire, salle, capacité) + effectif groupe + nb séances réalisées ; filtres année/formation/niveau/semestre/groupe/enseignant |
| Écrans | nouvel écran « Cours (LMD) » `/cours` (liste branchée ci-dessus + détail : planning, présences) ; le menu garde « Cours & modules » vers `/modules` **rebaptisé** « Modules & formations (CPFAE — héritage) » ; l'entrée GET-INJS « Cours » pointe vers `/cours` |
| Présences | un cours (affectation × créneau) expose son statut d'émargement (lot C) — lien direct 18→08 |

## Garde-fous transverses (inchangés)

- Migrations additives ; aucune colonne supprimée/renommée ; DROP différé et hors périmètre.
- `presences.AuditLog` + `core.EvenementAudit` : tout geste sensible tracé avec motif.
- Permissions : les gated-views existantes (IsSecretariatOrDFRC etc.) sont **étendues**, jamais
  restreintes ; le moteur CURP reste en OBSERVATION sur les nouvelles vues (bascule vue par vue,
  kill-switch LOT 5/6).
- Feux 1-2 à blanc avant clôture (feux-verts.sh), feu 3 non levable en sandbox.
- Contrat d'API : snapshot régénéré en fin de prompt avec justification (aucune rupture prévue).

## Ordre d'exécution

A → C → B (A conditionne la notion de structure utilisée par les écrans ; C est la demande
explicite « ne pas oublier » ; B est le plus transversal). Chaque lot : modèles → API → tests
backend → écran → tests frontend → docs.
