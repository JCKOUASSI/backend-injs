# Changelog du contrat d’API (P00-08)

Ce fichier est alimenté **exclusivement** par la commande :

```
python manage.py update_api_contract --justification "…"
```

Les **ajouts** de routes/clés sont des extensions non cassantes ; les **retraits ou renommages** sont des ruptures de contrat qui doivent être explicitement justifiés (et coordonnés avec les clients de l’API).


## 2026-09-13 12:10 UTC

**Génération initiale du contrat.**

- Justification : P00-08 : génération initiale du contrat de référence (schéma actuel, aucun comportement modifié).
- Routes figées : 529

## 2026-09-13 18:00 UTC

- **Justification :** P01-01 [LOT 1] : ajout du noyau core et du journal d'audit unifie (GET /api/core/audit/ et detail par code, lecture seule, derriere flag.lot01 et roles d'audit). Aucune route existante modifiee.
- Routes dans le contrat : 531
- **Ruptures (retraits/renommages) : 0**
  - _aucune_
- Ajouts (extensions non cassantes) : 2
  - Route supprimée ou renommée : GET /api/core/audit/
  - Route supprimée ou renommée : GET /api/core/audit/{code}/

## 2026-09-14 03:01 UTC

- **Justification :** U2 CURP : ajout des routes /api/habilitations/ (mes-acces, evaluer, observations, référentiels en lecture) ; aucune route existante modifiée.
- Routes dans le contrat : 537
- **Ruptures (retraits/renommages) : 0**
  - _aucune_
- Ajouts (extensions non cassantes) : 6
  - Route supprimée ou renommée : GET /api/habilitations/mes-acces/
  - Route supprimée ou renommée : GET /api/habilitations/observations/synthese/
  - Route supprimée ou renommée : GET /api/habilitations/permissions/
  - Route supprimée ou renommée : GET /api/habilitations/roles/
  - Route supprimée ou renommée : POST /api/habilitations/evaluer/
  - Route supprimée ou renommée : POST /api/habilitations/observations/remettre-a-zero/

## 2026-09-14 04:56 UTC

- **Justification :** U3 CURP : peuplement du referentiel roles/permissions (annexes A1-A6) ; ajout de deux cles en lecture dans GET /api/habilitations/roles/ (incompatible_avec, permissions_count) ; aucune route ajoutee, modifiee ou supprimee.
- Routes dans le contrat : 537
- **Ruptures (retraits/renommages) : 0**
  - _aucune_
- Ajouts (extensions non cassantes) : 2
  - GET /api/habilitations/roles/ — clé de réponse 200 supprimée : GET /api/habilitations/roles/ → réponse 200.results.[].incompatible_avec
  - GET /api/habilitations/roles/ — clé de réponse 200 supprimée : GET /api/habilitations/roles/ → réponse 200.results.[].permissions_count

## 2026-09-14 05:51 UTC

- **Justification :** U4 CURP : console web d administration des comptes derriere flag.curp_ui_admin (off par defaut) et trio administrateur ; nouvelles routes /api/habilitations/ : comptes (creation, fiche, differentiel obligatoire, modification, statuts), personnes, roles detail, matrice, journal + integrite, derogations, delegations, import-simuler (apercu), revue consultative. Aucune route existante modifiee ni rompue, aucun refus applique (moteur en observation).
- Routes dans le contrat : 556
- **Ruptures (retraits/renommages) : 0**
  - _aucune_
- Ajouts (extensions non cassantes) : 19
  - Route supprimée ou renommée : GET /api/habilitations/comptes/
  - Route supprimée ou renommée : GET /api/habilitations/comptes/revue/
  - Route supprimée ou renommée : GET /api/habilitations/comptes/{id}/
  - Route supprimée ou renommée : GET /api/habilitations/delegations/
  - Route supprimée ou renommée : GET /api/habilitations/derogations/
  - Route supprimée ou renommée : GET /api/habilitations/journal/
  - Route supprimée ou renommée : GET /api/habilitations/journal/integrite/
  - Route supprimée ou renommée : GET /api/habilitations/matrice/
  - Route supprimée ou renommée : GET /api/habilitations/personnes/
  - Route supprimée ou renommée : GET /api/habilitations/roles/{code}/
  - Route supprimée ou renommée : PATCH /api/habilitations/comptes/{id}/modifier/
  - Route supprimée ou renommée : POST /api/habilitations/comptes/
  - Route supprimée ou renommée : POST /api/habilitations/comptes/import-simuler/
  - Route supprimée ou renommée : POST /api/habilitations/comptes/{id}/simuler-modification/
  - Route supprimée ou renommée : POST /api/habilitations/comptes/{id}/statut/
  - Route supprimée ou renommée : POST /api/habilitations/delegations/
  - Route supprimée ou renommée : POST /api/habilitations/delegations/{id}/terminer/
  - Route supprimée ou renommée : POST /api/habilitations/derogations/
  - Route supprimée ou renommée : POST /api/habilitations/derogations/{id}/revoquer/

