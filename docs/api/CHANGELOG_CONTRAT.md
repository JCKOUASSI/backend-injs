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

## 2026-09-15 03:04 UTC

- **Justification :** GET-INJS (lot L8, 4e453e7) : le détail creneaux-types/{id} passe de POST à PUT/PATCH (contrat EDT v1.1, addendum docs/EDT_CONTRAT_DONNEES.md) ; LOT 5 (U8) : ajout non cassant du champ perimetres aux lignes d'attribution de la console CURP. Routes et clés retirées hors EDT : aucune.
- Routes dans le contrat : 634
- **Ruptures (retraits/renommages) : 1**
  - Route supprimée ou renommée : POST /api/edts/creneaux-types/{id}/
- Ajouts (extensions non cassantes) : 79
  - Route supprimée ou renommée : DELETE /api/edts/creneaux-types/{id}/
  - Route supprimée ou renommée : DELETE /api/habilitations/organisation/departements/{id}/comptes/
  - Route supprimée ou renommée : DELETE /api/habilitations/organisation/services/{id}/comptes/
  - Route supprimée ou renommée : DELETE /api/timetable/affectations/{id}/
  - Route supprimée ou renommée : DELETE /api/timetable/creneaux-types/{id}/
  - Route supprimée ou renommée : DELETE /api/timetable/emplois/{id}/
  - Route supprimée ou renommée : GET /api/edts/emplois/{id}/export.csv/
  - Route supprimée ou renommée : GET /api/edts/emplois/{id}/grille/
  - Route supprimée ou renommée : GET /api/edts/referentiel-enseignants/
  - Route supprimée ou renommée : GET /api/habilitations/comptes/imports/{reference}/
  - Route supprimée ou renommée : GET /api/habilitations/comptes/{id}/effective-permissions/
  - Route supprimée ou renommée : GET /api/habilitations/notifications/
  - Route supprimée ou renommée : GET /api/habilitations/organisation/departements/
  - Route supprimée ou renommée : GET /api/habilitations/organisation/departements/{id}/
  - Route supprimée ou renommée : GET /api/habilitations/organisation/directions/
  - Route supprimée ou renommée : GET /api/habilitations/organisation/directions/{id}/
  - Route supprimée ou renommée : GET /api/habilitations/organisation/services/
  - Route supprimée ou renommée : GET /api/habilitations/organisation/services/{id}/
  - Route supprimée ou renommée : GET /api/habilitations/propositions/
  - Route supprimée ou renommée : GET /api/timetable/affectations/
  - Route supprimée ou renommée : GET /api/timetable/affectations/{id}/
  - Route supprimée ou renommée : GET /api/timetable/conflits/
  - Route supprimée ou renommée : GET /api/timetable/creneaux-types/
  - Route supprimée ou renommée : GET /api/timetable/creneaux-types/{id}/
  - Route supprimée ou renommée : GET /api/timetable/emplois/
  - Route supprimée ou renommée : GET /api/timetable/emplois/{id}/
  - Route supprimée ou renommée : GET /api/timetable/emplois/{id}/export.csv/
  - Route supprimée ou renommée : GET /api/timetable/emplois/{id}/grille/
  - Route supprimée ou renommée : GET /api/timetable/publics/
  - Route supprimée ou renommée : GET /api/timetable/referentiel-enseignants/
  - Route supprimée ou renommée : PATCH /api/edts/creneaux-types/{id}/
  - Route supprimée ou renommée : PATCH /api/habilitations/organisation/departements/{id}/
  - Route supprimée ou renommée : PATCH /api/habilitations/organisation/directions/{id}/
  - Route supprimée ou renommée : PATCH /api/habilitations/organisation/services/{id}/
  - Route supprimée ou renommée : PATCH /api/timetable/affectations/{id}/
  - Route supprimée ou renommée : PATCH /api/timetable/creneaux-types/{id}/
  - Route supprimée ou renommée : PATCH /api/timetable/emplois/{id}/
  - Route supprimée ou renommée : POST /api/auth/mfa/confirm/
  - Route supprimée ou renommée : POST /api/auth/mfa/disable/
  - Route supprimée ou renommée : POST /api/auth/mfa/setup/
  - Route supprimée ou renommée : POST /api/auth/mfa/verify/
  - Route supprimée ou renommée : POST /api/edts/affectations/{id}/deplacer/
  - Route supprimée ou renommée : POST /api/edts/creneaux-types/
  - Route supprimée ou renommée : POST /api/edts/emplois/{id}/archiver/
  - Route supprimée ou renommée : POST /api/edts/emplois/{id}/depublier/
  - Route supprimée ou renommée : POST /api/edts/emplois/{id}/generer/
  - Route supprimée ou renommée : POST /api/edts/emplois/{id}/publier/
  - Route supprimée ou renommée : POST /api/edts/emplois/{id}/soumettre/
  - Route supprimée ou renommée : POST /api/habilitations/comptes/imports/
  - Route supprimée ou renommée : POST /api/habilitations/comptes/imports/{reference}/annuler/
  - Route supprimée ou renommée : POST /api/habilitations/delegations/{id}/action/
  - Route supprimée ou renommée : POST /api/habilitations/delegations/{id}/activer/
  - Route supprimée ou renommée : POST /api/habilitations/notifications/tout-lire/
  - Route supprimée ou renommée : POST /api/habilitations/notifications/{id}/lire/
  - Route supprimée ou renommée : POST /api/habilitations/organisation/departements/
  - Route supprimée ou renommée : POST /api/habilitations/organisation/departements/{id}/comptes/
  - Route supprimée ou renommée : POST /api/habilitations/organisation/directions/
  - Route supprimée ou renommée : POST /api/habilitations/organisation/services/
  - Route supprimée ou renommée : POST /api/habilitations/organisation/services/{id}/comptes/
  - Route supprimée ou renommée : POST /api/habilitations/propositions/{id}/approuver/
  - Route supprimée ou renommée : POST /api/habilitations/propositions/{id}/rejeter/
  - Route supprimée ou renommée : POST /api/habilitations/provisions/scanner/
  - Route supprimée ou renommée : POST /api/timetable/affectations/
  - Route supprimée ou renommée : POST /api/timetable/affectations/{id}/deplacer/
  - Route supprimée ou renommée : POST /api/timetable/conflits/
  - Route supprimée ou renommée : POST /api/timetable/conflits/{id}/resoudre/
  - Route supprimée ou renommée : POST /api/timetable/creneaux-types/
  - Route supprimée ou renommée : POST /api/timetable/emplois/
  - Route supprimée ou renommée : POST /api/timetable/emplois/{id}/archiver/
  - Route supprimée ou renommée : POST /api/timetable/emplois/{id}/conflits/
  - Route supprimée ou renommée : POST /api/timetable/emplois/{id}/depublier/
  - Route supprimée ou renommée : POST /api/timetable/emplois/{id}/generer/
  - Route supprimée ou renommée : POST /api/timetable/emplois/{id}/publier/
  - Route supprimée ou renommée : POST /api/timetable/emplois/{id}/soumettre/
  - Route supprimée ou renommée : POST /api/timetable/emplois/{id}/valider/
  - Route supprimée ou renommée : PUT /api/edts/creneaux-types/{id}/
  - Route supprimée ou renommée : PUT /api/timetable/affectations/{id}/
  - Route supprimée ou renommée : PUT /api/timetable/creneaux-types/{id}/
  - Route supprimée ou renommée : PUT /api/timetable/emplois/{id}/

## 2026-09-15 03:41 UTC

- **Justification :** Lot A refonte (modèle 13) : ajout de l'API organigramme unifié /api/administrations/organigramme/* (10 routes lecture/écriture, secrétariats rattachés) — aucune route retirée ; /secretariats reste monté (redirect frontend).
- Routes dans le contrat : 657
- **Ruptures (retraits/renommages) : 0**
  - _aucune_
- Ajouts (extensions non cassantes) : 23
  - Route supprimée ou renommée : DELETE /api/administrations/organigramme/departements/{id}/
  - Route supprimée ou renommée : DELETE /api/administrations/organigramme/directions/{id}/
  - Route supprimée ou renommée : DELETE /api/administrations/organigramme/secretariats/{id}/
  - Route supprimée ou renommée : DELETE /api/administrations/organigramme/services/{id}/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/arbre/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/departements/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/departements/{id}/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/directions/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/directions/{id}/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/responsables/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/secretariats/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/secretariats/{id}/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/services/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/services/{id}/
  - Route supprimée ou renommée : GET /api/administrations/organigramme/types-secretariat/
  - Route supprimée ou renommée : PATCH /api/administrations/organigramme/departements/{id}/
  - Route supprimée ou renommée : PATCH /api/administrations/organigramme/directions/{id}/
  - Route supprimée ou renommée : PATCH /api/administrations/organigramme/secretariats/{id}/
  - Route supprimée ou renommée : PATCH /api/administrations/organigramme/services/{id}/
  - Route supprimée ou renommée : POST /api/administrations/organigramme/departements/
  - Route supprimée ou renommée : POST /api/administrations/organigramme/directions/
  - Route supprimée ou renommée : POST /api/administrations/organigramme/secretariats/
  - Route supprimée ou renommée : POST /api/administrations/organigramme/services/

