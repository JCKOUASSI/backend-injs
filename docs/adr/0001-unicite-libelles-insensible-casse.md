# ADR 0001 — Anti-doublon de libellé insensible à la casse et aux accents, portable sur SQLite et PostgreSQL

- **Statut :** Accepté (décision d'expert P00-01), **implémentation fléchée LOT 1 (référentiels, P01-02/P01-03)** — non implémenté pendant le LOT 0 (lecture seule / filets).
- **Date :** 2026-09-11.
- **Contexte :** écart moteur constaté lors de la baseline P00-01.
- **Risques / règles liés :** règle 11 (référentiels issus de l'API, pas de doublon), règle 20 (ne pas deviner), DA-02 (une seule source de vérité).

## Constat

Les référentiels socles (`referentiels/models.py`, classe abstraite de base) portent une
`UniqueConstraint(Lower('libelle'))` et la vue (`referentiels/views.py`, `perform_create`) se
contente de capter l'`IntegrityError` pour renvoyer un 400 « valeur en doublon ».

- Sur **PostgreSQL** (production et CI), `LOWER()` replie les caractères accentués :
  `'Épreuve écrite'` et `'épreuve ÉCRITE'` sont considérées égales → le test
  `test_regle4_doublon_libelle_casse_rejete` passe.
- Sur **SQLite** (base de secours du sandbox Arena), `LOWER()` ne travaille que sur l'ASCII :
  les accents ne sont pas repliés, la contrainte ne déclenche pas et le test échoue
  (HTTP 201 au lieu de 400).

C'est le **seul échec résiduel** de la suite backend dans le sandbox après les correctifs de
stabilisation P00-01 (942 tests verts sur 943). La CI backend PostgreSQL reste verte.

## Décision

Ajouter, en **défense de profondeur et au niveau application**, une normalisation comparée
indépendante du moteur, en plus de la contrainte base de données (conservée) :

1. normaliser avec `unicodedata.normalize('NFKD', valeur)` puis supprimer les marques
   diacritiques, `.casefold()` et `.strip()` ;
2. avant insertion/mise à jour d'un référentiel, tester l'existence d'une autre ligne ayant la
   même forme normalisée sur le même modèle ; si oui, renvoyer une 400 explicite
   (`Cette valeur existe déjà (code ou libellé en doublon).`) ;
3. conserver la `UniqueConstraint(Lower('libelle'))` comme garde-fou PostgreSQL ;
4. prévoir une commande de vérification (en lecture/signalement) des doublons préexistants.

Aucun comportement en production n'est modifié (PostgreSQL appliquait déjà la règle) ; le
changeur rend seulement la règle **portable et explicite**, et améliore le message d'erreur.

## Conséquences

- `referentiels/tests/test_api.py::test_regle4_doublon_libelle_casse_rejete` devient vert sur
  SQLite **et** PostgreSQL.
- Cette décision et sa mise en œuvre restent dans le périmètre référentiels du LOT 1 ; aucun
  correctif de ce type n'est introduit pendant le LOT 0.
- La recette REC-01 (référentiels) vérifiera le rejet des doublons accentués/casse.
