# Rapport LOT 5 (U8) — bascule CURP : correctifs additifs, rattachement et amorçage progressif

**Date :** 2026-09-15 · **Domaine :** `backend/habilitations` (+ `authentication`,
`parametres`, scolarite/finances pour le branchement pilote, `frontend` console)
**Feu vert :** consigne commanditaire « relance le lot 5 » — le LOT 5 était
suspendu à un feu vert explicite (docs §10) ; la bascule en mode APPLICATION
elle-même **ne l'est pas** et reste progressive vue par vue.

---

## 1. Périmètre exécuté

Le package LOT 5, tel que défini par `docs/architecture/IAM.md` §10,
`docs/administration/utilisateurs.md` §13 et `docs/audit/permissions.md` §5 :

| Livrable | Nature | Emplacement |
|---|---|---|
| **L4-01** — couverture des cibles « objet métier » | correctif additif d'une ligne (+ `id`) | `habilitations/services/moteur.py::_decrire_perimetre` |
| **J2-4** — résolveurs hiérarchiques + type `DEPARTEMENT` | service nouveau + choices + migration | `habilitations/services/resolveurs.py`, `habilitations/models/perimetre.py`, migration `habilitations/0013` |
| **L4-02** — périmètres non secrétariat depuis la console | API additive + UI assistants | `habilitations/services/comptes_admin.py::_perimetre_borne`, `habilitations/api/serializers_admin.py`, `frontend/src/pages/habilitations/PerimetresOrganisation.jsx` |
| **L4-03** — événement `CONNEXION` au journal d'habilitation | émission best effort, double piste assumée | `backend/authentication/connexion_sure.py::finaliser_connexion` |
| **L4-04** — cible dict journalisée | tolérance du résolveur de cible | `habilitations/services/journalisation.py::_resoudre_cible` |
| **Étape 1** — rattachement additif des comptes legacy | commande idempotente, simulation par défaut | `habilitations/management/commands/rattacher_comptes_legacy.py` |
| **Étape 3** — amorçage du branchement vue par vue | 2 vues pilotes en OBSERVATION | `scolarite/inscription_api.py`, `finances_etudiantes/api.py` |

**Hors périmètre, volontairement** : arbitrage des cases J2 de la matrice
(décision humaine — atelier commanditaire, rien d'unilatéral) ; mode
APPLICATION par défaut ; retrait du legacy ; renommage des drapeaux
(homonymie L4-06 clarifiée par la doc uniquement).

## 2. Choix de conception notables

- **Le résolveur est un service, pas un fork du moteur.** Le contrôle 9 du
  moteur tente, dans l'ordre : global `INJS_ENTIER` → rapprochement exact
  `content_type`+pk (désormais possible grâce à L4-01) → règle générique
  `SECRETARIAT` → **ancêtres hiérarchiques** (`resolveurs.couvert_par_ancetre`).
  Un `contexte={'couverture': …}` injecté reste strictement prioritaire (voie
  démontrée au LOT 4). Le module `resolveurs` n'importe aucun modèle métier :
  les chaînes sont décrites par étiquettes `app_label.model` et chemins
  d'attributs parcourus tardivement (décision U1 de non-couplage).
- **Additivité vérifiée par les témoins.** Les 60 tests du LOT 4 (refus
  croisés §34) passent sans modification de logique : seule la classe née
  pour caractériser l'écart (`CouvertureObjetEcartTests`) a été **inversée**
  en verrou de non-régression (5 tests : couvert sur objet, refus motivé +
  tracé sur objet voisin, description portant `content_type_id`/`id`, voie
  DRF opérationnelle, résolveur injecté toujours prioritaire).
- **Console : types bornables = registre unique.** `resolveurs.TYPES_OBJETS`
  sert à la fois à la validation du sérialiseur, à la résolution de
  l'objet (400 `PERIMETRE_INCONNU` si type hors liste ou objet introuvable,
  atomicité — aucun `User` fantôme) et à la couverture hiérarchique.
  L'alliage `perimetres_secretariats` continue de fonctionner combiné.
- **Rattachement legacy sans auto-élévation.** `rattacher_comptes_legacy`
  applique la table A6 (`CORRESPONDANCE_LEGACY`) : les rôles non sensibles
  sont posés `ACTIVE` (motif tracé, journal `COMPTE_CREE`/`ROLE_ATTRIBUE`) ;
  un rôle sensible est posé `PROPOSEE` — et si le rôle legacy ne correspond
  **qu'à** des rôles sensibles (ADMIN → ADMIN_SYSTEME), le compte est
  **laissé non gouverné** avec avertissement (écart J2-1 en attente
  d'atelier). Simulation par défaut ; `--appliquer` écrit une transaction
  par utilisateur ; un second passage est nul (idempotence prouvée par test
  et sur la base de démo).
- **`CONNEXION` est un miroir, pas une dépendance.** L'émission est
  enveloppée `try/except` : une panne du journal chaîné ne bloque jamais une
  connexion ; le test le prouve (journal mocké en erreur → 200 + tokens).
- **Vues pilotes inertes par construction.** En OBSERVATION,
  `ExigePermission` évalue, compte (via `observation.enregistrer_decision`)
  et s'abstient ; les tests verrouillent la réponse inchangée (200 là où
  l'ancien dispositif accordait ; jamais 403 CURP sur le compte gouverné
  sans droit ; zéro compteur en mode OFF).

## 3. Preuves chiffrées

| Contrôles | Résultat |
|---|---|
| `habilitations` (module complet, U1→U5 + LOT 4 + **LOT 5**) | **415 tests OK** (2 ignorés : déclencheurs PostgreSQL) |
| dont `test_lot5_bascule` | 26 — résolveurs, console, cible dict, `CONNEXION`, commande, pilotes |
| dont `test_lot4_refus_croises` (dont classe inversée) | 51 OK sans perte des refus croisés §34 |
| `authentication` + `scolarite` + `finances_etudiantes` | **467 tests OK** |
| frontend `pages/habilitations` | **63 tests OK** (dont 6 nouveaux) ; ESLint 0 erreur sur les fichiers du lot |
| Migration | `habilitations/0013` — choices seuls (3 champs liés au même enum), aucune opération SQL destructive ; `makemigrations --check` propre |
| Smoke serveur réel (démo) | console API ouverte temporairement : création de compte avec périmètres `DIRECTION`+`DEPARTEMENT` → 201, cibles résolues, journal intact ; `CONNEXION` émis à la connexion du compte gouverné ; rattachement : 8 comptes posés, rejeu → 0 ; ménage complet, drapeau restauré ÉTEINT |
| Garde-fou d'audit | `verifier_chaine()` → `[]` dans toutes les écritures du lot |
| Contrat d'API (P00-08) | Snapshot régénéré `update_api_contract` : 1 rupture **justifiée** (reliquat GET-INJS L8 : `POST /api/edts/creneaux-types/{id}/` → PUT/PATCH) + 79 ajouts non cassants ; `config.tests.test_api_contract` : **11/11 OK** |

Rejeu :

```bash
cd backend
./.venv/bin/python manage.py test habilitations.tests.test_lot5_bascule -v 1   # 26
./.venv/bin/python manage.py test habilitations -v 1                            # 415
./.venv/bin/python manage.py test authentication scolarite finances_etudiantes  # 467
./.venv/bin/python manage.py rattacher_comptes_legacy                           # simulation
./.venv/bin/python manage.py observations_habilitations                         # compteurs
cd ../frontend && npx vitest run src/pages/habilitations && npx eslint src/pages/habilitations
```

## 4. Effets de bord contrôlés

- `Perimetre.Type.DEPARTEMENT` **ajoute** un choix ; les rôles de département
  continuent de porter `DIRECTION` par défaut (J2-4 : option « assumer
  DIRECTION » retenue pour les octrois existants, le nouveau type étant
  disponible à la pose — aucun octroi réécrit).
- La règle d'élargissement (`couvert_par_ancetre`) ne peut que convertir un
  `CIBLE_HORS_PERIMETRE` en « couvert » **pour une paire déjà accordée par
  ailleurs** : elle ne crée aucun octroi, ne touche ni niveaux ni canaux ; en
  mode OFF/observation, elle ne change aucune réponse.
- Les compteurs d'observation peuvent monter (vus pilotes) : c'est le signal
  voulu ; `observations_habilitations --remettre-a-zero` pour repartir propre.
- Frontend : le payload des assistants gagne une clé optionnelle
  `perimetres` ; absente ou vide, le comportement est bit à bit identique.

## 5. Reste à faire (hors LOT 5)

1. **Atelier J2** : lignes A2 `ADMIN_SYSTEME` (J2-1), `CHEF_DEPARTEMENT`
   `administration: N2` (J2-2), rôles SI/`parametres` (J2-3) ;
2. branchement des vues restantes, puis bascule APPLICATION progressive par
   drapeau sur la foi des compteurs (critère S1 : zéro écart
   « legacy autorise / moteur refuse » non traité) ;
3. retrait du legacy (E1/E2/E7) après stabilisation ;
4. sélecteurs pédagogiques (Formation/Parcours/Groupe/ECUE) dans l'assistant —
   l'API les accepte déjà ;
5. rejeu d’immuabilité sous PostgreSQL (2 tests ignorés) et `collectstatic`
   préalable de la suite complète (L4-05, environnement).
