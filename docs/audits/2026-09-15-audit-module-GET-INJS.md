# Audit du module GET-INJS — Gestion des Emplois du Temps (lot L8)

- **Date :** 2026-09-15
- **Périmètre :** `backend/edts/` (app native EDT), écrans React GET-INJS
  (`frontend/src/pages/Edts.jsx`, `EdtNew.jsx`, `AffectationNew.jsx`, écrans génériques
  de `frontend/src/menu/ecrans.js`), contrat scolarité `backend/scolarite/edt_export.py`,
  app mobile `qr_badge_mobile/`.
- **Référentiel de conformité :** les 23 prompts `P00→P22` du dossier
  `workspace/EmploiduTemps-INJS` (génération, plan et mode opératoire) et l'ADR-003.
- **Méthode :** lecture du code + sondes HTTP réelles contre la base de
  démonstration (avant/après), suites de tests, `check_repo_hygiene`.

## 1. Verdict global avant correction

Le module était **structurellement présent mais fonctionnellement cassé** :
presque aucun chemin critique ne survivait à un usage réel.

| Symptôme mesuré (avant) | Preuve |
|---|---|
| `GET/POST /api/edts/emplois/` → **500** dès la première ligne en base | sérialiseur lisant `_population_label`, `semaine_debut/fin`, `creneaux` — champs inexistants sur le modèle |
| `GET /api/edts/publics/` → **500** | filtre `.filter(actif=True)` sur un modèle sans champ `actif` |
| `POST /api/edts/affectations/` sans champs requis → **500** | aucune validation : `IntegrityError` non traitée |
| Référencement aveugle → **500** | FK `annee/formation/groupe` non vérifiées (la base de démo n'avait **aucune année académique**) |
| Écran « Conflits » **faux** | le panneau affichait le compte des affectations *inactives* et ne consultait jamais `/edts/conflits/` ; la réponse de détection était jetée |
| Liste des affectations **mélangeée** | le frontend envoyait `?emploi_du_temps_id=…` mais le backend ignorait **tous** les filtres : toutes les affectations de tous les EDT s'affichaient |
| Détection de conflits **inopérante** | lookup JSON `contains` non supporté sur SQLite (`NotSupportedError`), aucune détection *entre* EDT, aucun clôture des conflits obsolètes, type de conflit calculé faux (`a.enseignant` comparé à `b.groupe`) |
| **Escalade de workflow** | `PATCH statut: 'PUBLIE'` par le simple Secrétariat écrivait PUBLIE en base malgré la réponse 500 (l'endpoint de validation, lui, était correctement protégé) |
| Bouton « supprimer » inversé | visible seulement sur les affectations **inactives** |
| Formulaire de création **hors sol** | année académique codée en dur (`<option value="1">2025-2026</option>`), population saisie par ID numérique brut, semaines « début/fin » envoyées puis silencieusement perdues |
| Tests | `edts/tests/` **vide** (0 test pour tout le module) |

## 2. Conformité prompt par prompt (état avant → après)

| Prompt | Objet | Avant | Après la session |
|---|---|---|---|
| P01 | Calendrier, créneaux, référentiels | créneaux types en lecture seule (pas de création via API) | CRUD complet créneaux + validation doublon/horaires ; périodes = semaines portées par l'EDT |
| P02 | Espaces ↔ activités | salle en texte libre, aucun contrôle | texte libre conservé + liste de suggestions (`/formations/ref/salles/`), conflits de salle détectés (insensibles à la casse) ; compatibilité capacité = roadmap |
| P03 | Besoins d'enseignement | non consommés par le module | le générateur lit `AffectationPedagogique` VALIDÉE/PLANIFIÉE du socle |
| P04 | Disponibilités/contraintes | ignorées | `IndisponibiliteEnseignant` projetée dans la génération (jours indisponibles) |
| P05 | SÉANCES, versions, workflow | workflow nominal mais contournable, pas de semaines sur l'EDT | transitions verrouillées + gel d'édition + semaines sur `EmploiDuTemps` ; **versions = roadmap** |
| P06 | Solver / génération | absent | moteur glouton déterministe `POST /emplois/<id>/generer/` (brouillon uniquement, ADR-003 respecté) |
| P07 | Conflits + explication | cassé (500 SQLite, type faux) | moteur global, explications lisibles, auto-clôture, tests portables |
| P08 | Placement manuel contrôlé | aucun contrôle | `verifier_affectation()` en création/mutation + endpoint `…/deplacer/` (409 avec conflits, forçage motivé tracé) |
| P09 | Annulations/rattrapages | absence d'annulation justifiée | désactivation motivée via commentaire/`actif` + journal ; **rattrapages/restaurations = roadmap** |
| P10 | Examens/réservations | hors module (contrat lecture seule) | inchangé — à budgéter |
| P11 | API `/api/timetable/` | seul préfixe `/api/edts/` | **alias `/api/timetable/` monté** (mêmes vues) ; contrat scolarité v1.1 inchangé |
| P12–P16 | Assiduités/QR/émargements/VH/seuils | déjà portés par le socle (presences, badgeages, seuils) | hors périmètre edts — documenté ; lien grille→séance = roadmap |
| P17 | Écrans React EDT | cassés (cf. §1) | refonte : grille hebdomadaire, panneau de conflits réel, workflow role-aware, modale d'édition, export, sélection persistante URL |
| P18 | Écrans assiduité React | socle existant | inchangé |
| P19 | Mobile « Mon EDT », scan, hors-ligne | **absent** de `qr_badge_mobile` | **roadmap** (nécessite l'outil Flutter, hors du bac à sable) |
| P20 | Exports PDF/Excel | CSV du contrat socle seulement | `GET /emplois/<id>/export.csv/` (BOM, libellés français) branché sur le bouton Export ; PDF = roadmap |
| P21 | Tests/perfs | 0 test, N+1, listes non paginées | **26 tests backend + 8 tests front utils**, annnotations `Count`, filtres serveur, pagination douce `limit/offset` |
| P22 | Migration/déploiement/recette/doc | doc contradictoire (« EDT non intégré ») | addendum au contrat + journalisation `JournalScolarite` des actions EDT |

## 3. Incohérences architecturales relevées (et sort)

1. **`enseignant_id` du module référençait `auth.User` alors que la charge
   pédagogique du socle (`AffectationPedagogique.enseignant`) référence
   `formations.Formateur`.** Ajout d'une clé `formateur` (FK PROTECT) sur
   `AffectationCreneau` comme référence de planification ; `enseignant_id`
   reste l'identité numérique optionnelle. Le générateur remplit les deux.
2. **Le rôle planificateur « DFRC » n'existe pas dans `User.Role`** (le socle
   le mappe sur `CPFAE_ADMIN`/`CHEF_CPFAE_ADMIN`) : les comptes INJS-Admin
   étaient exclus de l'écriture. Liste des rôles alignée sur la matrice CURP.
3. **Le workflow codé (`BROUILLON→EN_VALIDATION→VALIDE→PUBLIE→ARCHIVE`) ne
   correspondait pas à celui de l'ADR-003 (`GÉNÉRÉ/À CONTRÔLER/ACTIF`).** Choix
   d'assumer le workflow des écrans tout en appliquant l'esprit de l'ADR : la
   génération ne produit que du BROUILLON, jamais publié ; l'écart de
   terminologie est signalé ici pour arbitrage Direction.
4. **Deux classes de permissions mortes** (`IsEdtEnseignantReadOnly`,
   `IsEnseignantOuReadOnly`) : supprimées ; le filtrage « mon EDT » devient un
   vrai paramètre serveur (`?selon_role=1`) exploité par l'écran.
5. **L'écran « Disponibilités › Agents » affichait la liste du personnel RH**
   sans aucune donnée d'indisponibilité : onglet retiré (données indisponibles).
6. **`docs/EDT_CONTRAT_DONNEES.md` affirmait « l'EDT n'est pas intégré »** alors
   que le module GET-INJS est décidé : addendum daté ajouté au document.

## 4. Corrections appliquées (inventaire)

### Backend
- `edts/api.py` : réécriture complète — sérialiseurs alignés sur les champs
  réels ; validation d'entrée systématique (400/404/409, plus jamais 500 sur
  une erreur utilisateur) ; filtres serveurs effectifs (`annee_academique_id`,
  `population_type/id`, `statut`, `q`, `emploi_du_temps_id`, `semaine`,
  `enseignant_id`, `groupe_id`, `nature`, `actif`…) ; pagination douce
  `limit/offset` (plafond 1000) ; workflow complet `soumettre/valider/publier/
  dépublier/archiver` avec matrice de transitions et gel d'édition
  (EN_VALIDATION et plus verrouillé pour la planification) ; suppression
  réservée aux brouillons/archives ; `statut` et périmètre rendus immuables en
  PATCH ; export CSV ; grille hebdo ; génération de brouillon ; annuaire
  `referentiel-enseignants`.
- `edts/services.py` : réécriture du moteur — détection **globale** entre EDT
  (enseignant/formateur/groupe/salle), explications lisibles, auto-clôture des
  conflits automatiques devenus obsolètes, respect des signalements manuels,
  portabilité SQLite (fin du lookup `contains`), vérification pré-placement
  `verifier_affectation()`, grille hebdomadaire, générateur glouton
  P06 consommant les affectations pédagogiques validées et les
  indisponibilités datées du socle.
- `edts/models.py` : `semaine_debut/semaine_fin` sur l'EDT (valeurs par défaut,
  validation), `formateur` FK sur l'affectation, `clean()/horaire/population_label`
  — migration `edts/0002`.
- `edts/permissions.py` : rôles alignés sur la matrice CURP ; messages 403
  explicites ; suppression du code mort.
- `edts/urls.py` + `config/urls.py` : nouvelles routes + **alias `/api/timetable/`**.
- `scolarite/models.py` : 10 actions d'audit `EDT_*` dans `JournalScolarite`
  (migration `scolarite/0015`) ; le module journalise création, transitions,
  modifications d'affectations, déplacement forcé motivé, résolutions,
  suppressions, générations.
- `seed_data.py` : bloc idempotent GET-INJS (année courante 2026-2027,
  caneva de 22 créneaux types, EDT de démonstration en brouillon avec 4
  affectations dont un conflit volontaire à détecter) — sans cela, la
  création d'EDT était impossible en démo.
- **Tests** : `edts/tests/test_api.py` (26 cas : sérialisation, validation,
  doublons, workflow, gel, permissions, filtres, référentiel créneaux,
  protections de suppression, export, grille, alias) + `test_services.py`
  (primitives, portabilité, détection globale, clôture des obsolètes,
  manuels préservés, placement contrôlé, générateur). `manage.py test edts` :
  **OK** ; suites scolarité/formations rejouées : **490 OK**.

### Frontend
- `src/utils/edts.js` : libellés français (jours/statuts/natures/conflits),
  couleurs de badges, `formatHeure` (fini « 08:00:00 » à l'écran), matrice de
  grille + marquage des cellules en conflit, extracteur d'messages d'erreur
  API (affiche les erreurs de champ du serveur au lieu d'un texte générique) —
  **8 tests vitest**.
- `Edts.jsx` : refonte — filtres année/statut/recherche, sélection persistée
  dans l'URL (`?selection=`), **grille hebdomadaire** (navigation par semaine,
  cellules marquées en conflit), bascule Grille/Tableau, panneau de conflits
  réel (filtré, badgeé, « Résoudre » tracé), détection à la demande avec
  statistiques, workflow complet role-aware (Soumettre, Valider, Publier,
  Dépublier, Archiver/Rouvrir, Supprimer avec confirmations), génération
  automatique de brouillon, export CSV téléchargé via l'API (jeton), modale
  d'édition d'affectation (créneau, semaines, nature, enseignant, groupe,
  salle, commentaire, activation), boutons d'action corrects (épingler/supprimer
  sur les lignes **actives**).
- `EdtNew.jsx` : selecteurs réels (années via `/scolarite/ref/annees/` avec
  repli sur l'année courante ; population selon le type — formation/groupe/
  enseignant/salle ; dénominateur reporté automatiquement ; bornes de semaines
  cohérentes validées avant envoi ; alerte explicite quand le référentiel
  d'années est vide) ; l'ID numérique brut a disparu.
- `AffectationNew.jsx` : le EDT parent est rappelé dans l'en-tête, le
  verrouillage par statut bloque le formulaire avec explication, pré-remplissage
  des semaines depuis l'URL (`?semaine=`) et de l'EDT, créneaux libellés en
  français, sélecteurs enseignant/groupe, suggestion de salle (datalist),
  **bandeau des conflits renvoyés par le serveur** après pose, navigation de
  retour vers l'EDT sélectionné.
- `ecrans.js` : écran « Conflits & contraintes » colonnes explicites + filtres
  (statut, type) + action « Résoudre » masquée sur les conflits clôturés ;
  onglet « Agents » mensonger retiré de « Disponibilités » ; libellé de menu
  « Génération EDT » → « Créer un emploi du temps » (l'écran crée un EDT ; la
  génération automatique vit dans le tableau, conforme à l'usage).
- `EcranRessource.jsx` : support générique `action.visible(ligne)` (utilisé par
  la résolution de conflits).

## 5. Résultats de la re-sonde (mêmes cas qu'à l'audit, en base réelle)

```
GET emplois (avec lignes)            200   (avant : 500)
GET publics (auth / anonyme)         200 / 401 (avant : 500 / 401)
POST emploi valide                   201   (avant : 500)
POST sans population_id / FK        400   (avant : 500)
PATCH statut direct (escalade)      400 refus (avant : écriture malgré 500)
POST affectation sans requis        400   (avant : 500)
Détection conflits SQLite           200, conflits créés et closés (avant : NotSupportedError)
Avertissements à la pose            3 renvoyés ( Placement contrôlé P08)
Workflow soumettre→valider→publier  409 conflits ouverts / 403 secrétariat / 200 Direction
Gel d'édition après validation      409 (avant : aucune protection)
Grille + export CSV                 200 (nouveaux)
Alias /api/timetable/               200 (nouveau)
Suppression + reliquat              204, zéro orphan (avant : suppression en cascade non testée)
```

## 6. insuffisances restantes — plan proposé

| # | Écart | Proposition | Charge estimée |
|---|---|---|---|
| 1 | Workflow en 4 états ≠ chaîne ADR-003 (`GÉNÉRÉ/À CONTRÔLER/ACTIF`) | trancher en Direction ; si acté, mappage `GÉNÉRÉ→BROUILLON` (drapeau `genere`), `À CONTRÔLER→EN_VALIDATION`, `ACTIF` dérivé du lien vers les séances du socle | 1 lot |
| 2 | Pas de **versions** d'EDT (P05) | table `EmploiDuTempsVersion` (snapshot JSON + auteur + motif), comparaison entre versions | 1 lot |
| 3 | Génération = glouton simple (P06 complet : recuit/pondérations) | itérer : score de qualité (répartition dans la semaine, matinée privilégiée, VH enseignant), optimisation par échanges locaux | 1–2 lots |
| 4 | Annulations/rattrapages/replacements (P09) avec notifications | modèles `AnnulationSeance` + `Rattrapage` + notification in-app ; gel des lignes annulées | 1 lot |
| 5 | Examens et réservations d'espaces multi-usages (P10) | consommation d'`espaces/<salle>/occupation` en écriture contrôlée côté `edts` | 1 lot |
| 6 | Pointage depuis la grille (P12 : ouvrir une séance d'un créneau) | bouton « Ouvre la séance » branché sur `presences.SessionBadgeage` quand l'EDT est PUBLIE | ½ lot |
| 7 | Mobile « Mon EDT » + QR (P19) | 3 écrans Flutter (emploi, scan, émargement enseignant) + cache hors-ligne | 1 lot mobile |
| 8 | PDF institutionnel (P20) | gabarit ReportLab A4 paysage (existant dans le socle d'exports) | ½ lot |
| 9 | Salle : capacité et compatibilité activité (P02 complet) | FK `RefSalle` + contrôle capacité/crédits et type d'espace vs nature | ½ lot |
| 10 | Tests de charge (P21 perf) | benchmark 200 EDT × 500 affectations ; si >300 ms détection, index partiel (poste `date`) et tri par buckets de semaine | ½ lot |

## 7. Consignes d'exploitation

- Lancement : `bash scripts/start_dev.sh` (tout) ou les deux
  `bash arena/lancer-front.sh` / `bash arena/lancer-api.sh` — ports figés
  **site 3000 / API 8000** (règle impérative n°18).
- La base de démo contient un EDT « démo — Encadrant superviseur1 » en brouillon
  avec un conflit volontaire : cliquer **Détection** dans `/edt` pour le voir
  apparaître, puis **Générer le brouillon** pour l'exemple de génération.
- Comptes de démonstration : `admin/admin123` (tous droits), `secretariat/sec123`
  (planification), `superviseur1/sup123` (encadrant).

---

## Suivi (2026-09-15, LOT 5)

Le test de contrat d'API (`config.tests.test_api_contract`) signalait la
disparition de `POST /api/edts/creneaux-types/{id}/` (remplacé par
PUT/PATCH/DELETE au détail dans la refonte L8, addendum du contrat de
données) : le snapshot a été **régénéré** lors du LOT 5 via
`manage.py update_api_contract --justification "…"` — une rupture justifiée,
79 ajouts non cassants (routes L8 + alias `/api/timetable/`), voir
`docs/api/CHANGELOG_CONTRAT.md` (entrée 2026-09-15).
