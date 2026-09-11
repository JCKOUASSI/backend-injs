# Carte d'acces role FINANCE

## Objectif du role

Le role `FINANCE` est un role de consultation centre sur les formateurs.
Il doit permettre de:
- voir la liste des formateurs (synthese : nombre de seances, temps total);
- ouvrir un **detail** par formateur pour voir le temps de cours **par seance**;
- voir le temps total de cours par formateur (liste et detail).

## Menu visible (frontend)

Avec un compte `FINANCE`, le menu lateral affiche typiquement:
- `Suivi Finance` (page formateurs dediee)
- `Dashboard Finance`
- `Mon profil`

Avec un compte `DIRECTION`, les donnees finance restent visibles via:
- `Dashboard Finance`
- la vue finance des formateurs (temps total + detail par seance).

Le menu ne montre pas:
- `Auditeurs`
- `Utilisateurs`
- `Secretariats`
- `Import Excel`
- `Referentiels`

## Ecran Formateurs (attendu metier)

En mode `FINANCE` / `DIRECTION` (vue finance), l'ecran `Formateurs` est en lecture seule:
- pas de creation de formateur;
- pas de modification;
- pas de suppression;
- liste : nombre de seances, temps total, bouton **Detail** (pas de detail par seance dans le tableau);
- detail : modal apres clic sur **Detail**, donne la repartition par seance.

Source API utilisee par le frontend pour ce role:
- `GET /formations/formateurs/finance-report/?include_sessions=0&page=...` (liste legere)
- `GET /formations/formateurs/finance-report/?formateur_id=<id>` (detail avec seances)
- `GET /formations/finance/dashboard/` (KPI finance + top formateurs)

## Endpoints explicitement autorises a FINANCE

- `GET /auth/me/` (profil connecte)
- `PATCH /auth/me/` (mise a jour de son propre profil)
- `POST /auth/change-password/` (changement de mot de passe)
- `GET /formations/formateurs/finance-report/` (rapport finance formateurs)

## Endpoints explicitement refuses a FINANCE

- `GET/POST /auth/users/` (gestion utilisateurs)
- `GET/PATCH/DELETE /auth/users/{id}/`

## Point d'attention important (validation equipe)

Plusieurs endpoints formations react sont encore en `IsAuthenticated` (authentifie uniquement),
donc accessibles techniquement par `FINANCE` si appele manuellement (URL directe ou client API),
alors que le besoin metier est lecture finance ciblee.

Exemples a verifier avec l'equipe:
- `GET /formations/list/`
- `GET /formations/{id}/detail/`
- `GET /formations/participants/list/`
- `GET /formations/formateurs/list/`
- `POST /formations/{formation_pk}/modules/{module_pk}/formateurs/add/`
- `PUT/PATCH /formations/{formation_pk}/modules/{module_pk}/`

Ces acces ne sont pas tous exposes dans le menu, mais ils existent cote API.

## Checklist de validation fonctionnelle (QA)

1. Connexion avec un compte `FINANCE`.
2. Verifier le menu (interface finance dediee : pas de tableau de bord / cours pour `FINANCE`).
3. Ouvrir la page formateurs finance et verifier:
   - colonnes liste : nombre de seances, temps total (pas de liste des seances dans le tableau);
   - bouton **Detail** par ligne;
   - absence des boutons creer/modifier/supprimer.
4. Verifier que `GET /formations/formateurs/finance-report/?include_sessions=0` retourne:
   - `sessions_count`, `total_duree_minutes`, `total_duree_heures` (sans cle `sessions`).
   Puis `GET ...?formateur_id=<id>` retourne une ligne avec `sessions[]`.
5. Verifier qu'un appel `GET /auth/users/` avec token finance retourne `403`.
6. Tester les endpoints "Point d'attention" ci-dessus pour confirmer le comportement decide
   (autorise ou bloque) avant passage en production.

## Decision metier attendue

Avant mise en production, valider formellement:
- la liste exacte des endpoints autorises au role `FINANCE`;
- si `FINANCE` doit rester strictement lecture sur toutes les APIs formations;
- si les routes frontend non visibles doivent aussi etre bloquees par role cote routage.
