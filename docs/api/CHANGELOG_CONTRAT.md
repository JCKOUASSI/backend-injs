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

