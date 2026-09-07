# Contrat de données EDT — INJS-LMD (v1.1)

**Décision actée** : l'emploi du temps n'est **pas intégré** à l'application.
Une application externe (`app-ept-injs-lmd 2026`) planifie les cours en
consommant ce contrat de données **en lecture seule**. Le retour vers la
gestion se fait par import Excel manuel (Cours → Séances).

**Base** : `/api/scolarite/edt/` — endpoints strictement en lecture, formats
JSON et CSV (`?export=csv`), versionnement par champ `version`.

## Ressources

| Endpoint (préfixe `/api/scolarite/edt/`) | Contenu | Ajout |
|---|---|---|
| `contrat` | Description du contrat, volumétrie, UR des ressources | v1.0 |
| `groupes/` | Groupes LMD à planifier + effectif réel (AffectationGroupe actif) + capacité | v1.0 |
| `enseignements/` | Une ligne par ECUE × semestre × groupe, avec volumes CM/TD/TP et effectif | v1.0 |
| `etudiants/` | Liste nominative des inscrits validés, avec groupe actif | v1.0 |
| `indisponibilites/` | 🆕 v1.1 — indisponibilités des enseignants (périodes, motif) | L10 |
| `creneaux/` | 🆕 v1.1 — séances planifiées du socle opérationnel (SessionModule : date, horaires prévus, module) | L10 |
| `affectations/` | 🆕 v1.1 — affectations pédagogiques LMD (ECUE × groupe × enseignant, volume, période, statut) | L10 |
| `espaces/<salle_id>/occupation/` | 🆕 v1.1 — occupations connues d'une salle (épreuves de concours, lot L2) — consultation seule | L10 |

## Filtres disponibles

- Communs : `annee_academique_id` (défaut : année courante), `export=csv`.
- `groupes` : `ref_formation_id`, `niveau_id`, `parcours_id`, `groupe_id`.
- `enseignements` / `etudiants` : `ref_formation_id`, `niveau_id`, `parcours_id`, `groupe_id`.
- `indisponibilites` : `enseignant_id`, `date_debut_min`.
- `creneaux` : `ref_formation_id`, `date_min`, `date_max`.
- `affectations` : `ref_formation_id`, `niveau_id`, `parcours_id`, `groupe_id`, `enseignant_id`.

## Règles de versionnement

1. Tout ajout se fait par **nouveau champ ou nouvelle ressource** — jamais de
   renommage ni de suppression d'un champ publié.
2. `version` passe à `1.x` pour un ajout compatible, `2.0` pour une rupture
   (requiert un accord avec le planificateur).
3. Les données ne sont jamais modifiées par ce contrat (lecture seule).

## Espaces (lecture seule)

- Les salles (`formations.RefSalle`) portent désormais `type_espace` →
  `referentiels.RefTypeEspaceSportif` (gymnase, piscine, terrain… — référentiel
  du lot L5) et restent exposées via `/api/formations/ref/salles/`.
- `GET /api/scolarite/edt/espaces/<salle_id>/occupation/` retourne les
  occupations connues (épreuves de concours, lot L2). **Aucun moteur de
  réservation** : consultation destinée au planificateur et aux modules
  futurs (maintenance).

## Tests de non-régression

`backend/scolarite/tests/test_edt_export.py` (contrat existant) et
`backend/scolarite/tests/test_edt_extensions.py` (indisponibilités,
créneaux, affectations, occupation d'espace, version 1.1).
