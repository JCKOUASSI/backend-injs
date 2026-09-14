# Documentation du projet INJS-LMD 2026

Point d'entrée de toute la documentation. La présentation générale et le démarrage sont
dans le [README racine](../README.md) ; l'architecture réelle et les décisions sont dans
[ARCHITECTURE.md](ARCHITECTURE.md).

## Documentation technique

| Document | Contenu |
|---------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture réelle, table modules ↔ applications, décisions DA-01 → DA-12 |
| [GARDE_FOUS.md](GARDE_FOUS.md) | Garde-fous du chantier (feature flags, contrat d'API figé, parcours de fumée) — P00-08 |
| [api/](api/) | Contrat d'API figé (`contract.snapshot.json`) et journal des évolutions (`CHANGELOG_CONTRAT.md`) |
| [ADR/](ADR/README.md) | Registre des décisions d'architecture (ADR-001 à ADR-006) |
| [CARTOGRAPHIE_CIBLE_INJS_LMD.md](CARTOGRAPHIE_CIBLE_INJS_LMD.md) | Cartographie détaillée par module (existants / à créer / doubles représentations) |
| [API_ENDPOINTS.md](API_ENDPOINTS.md) | Référence des endpoints REST du backend INJS-LMD |
| [STATISTIQUES_INDICATEURS.md](STATISTIQUES_INDICATEURS.md) | Définition et traçabilité des indicateurs statistiques |
| [SECURITE_DONNEES.md](SECURITE_DONNEES.md) | Sécurité et protection des données, jeux de données fictifs |
| [modeles/](modeles/) | Modèles de données fictifs (jamais de données réelles dans le dépôt) |
| [audits/BASELINE_2026-09.md](audits/BASELINE_2026-09.md) | Baseline chiffrée de référence |
| [archives/](archives/README.md) | Documents d'époque — **« Document d'archive — ne pas utiliser »** |

> Les guides d'administration du backend (dépannage, actions courantes) se trouvent dans
> [`../backend/docs/`](../backend/docs/).

## Identité, droits et administration — module Utilisateurs (LOT 4)

Documents de consolidation du chantier CURP (identité, comptes, rôles, permissions,
périmètres, journal). Ils décrivent **l'état réel du dépôt** au 2026-09-14 et sont
adossés aux tests cités.

| Document | Contenu |
|---------|---------|
| [architecture/IAM.md](architecture/IAM.md) | Architecture d'identité et de contrôle d'accès : les deux couches (legacy + CURP), authentification (JWT, MFA TOTP, verrouillage), autorisation et modes du moteur, organisation, journalisation, surface d'API et écrans, plan de bascule |
| [security/RBAC.md](security/RBAC.md) | Règles de droits : niveaux N0–N4, 81 rôles, 1 155 permissions, matrice A2/J2, 12 périmètres, les 10 contrôles et leurs motifs, séparation des tâches, écarts à arbitrer |
| [administration/utilisateurs.md](administration/utilisateurs.md) | Guide d'exploitation : drapeaux, création/modification de comptes, machine à états A5, MFA, organisation, dérogations et délégations, imports, surveillance et dépannage |
| [audit/permissions.md](audit/permissions.md) | Rapport d'audit LOT 4 : méthode, volumes mesurés, 60 tests de refus croisés (§34) et de bout en bout (§35), écarts numérotés (L4-01…L4-06, J2-1…J2-4), plan de remédiation |

> **Note de nomenclature** : les rapports d'audit **datés** du projet sont dans
> [`audits/`](audits/) (pluriel) ; le dossier [`audit/`](audit/) (singulier) porte le
> rapport consolidé des permissions du module Utilisateurs, comme prévu par le plan
> [`curp/05-architecture-completion-module-utilisateurs.md`](curp/05-architecture-completion-module-utilisateurs.md) §5.

## Manuel utilisateur — Module Statistiques

| Fichier | Description |
|---------|-------------|
| [Manuel utilisateur App Statistiques.md](./Manuel%20utilisateur%20App%20Statistiques.md) | Source Markdown (maintenue à jour par l'équipe / l'agent) |
| [Manuel utilisateur App Statistiques.docx](./Manuel%20utilisateur%20App%20Statistiques.docx) | Version Word formatée |

Régénérer le Word après modification du Markdown :

```bash
python scripts/generate_manuel_statistiques_docx.py
```

## Pages légales & confidentialité (HTML statique)

Contenu prêt à être servi par **GitHub Pages** (ou tout hébergement statique). Les
**noms de fichiers** et l'URL actuellement publiée conservent une nomenclature héritée
(ils sont référencés par les fiches des magasins d'applications) ; leur renommage se fera
avec le rebranding des fiches stores (DA-12). Les titres et contenus visibles sont en
revanche en terminologie INJS.

| Fichier | Usage |
|---------|--------|
| `index.html` (racine de `docs/`) | Redirige vers `legal/index.html`. |
| `legal/index.html` | Sommaire avec liens vers toutes les pages. |
| `legal/confidentialite-qr-badge-mobile.html` | **Google Play / App Store** — caméra, localisation, application mobile INJS — Présences. |
| `legal/confidentialite-badgeage-web.html` | Badgeage navigateur / PWA / hors ligne. |
| `legal/confidentialite-plateforme-sygep.html` | Vue globale plateforme INJS-LMD (web + API). |
| `legal/donnees-personnelles-droits.html` | Droits sur les données personnelles (accès, rectification, limitation, etc.). |
| `legal/mentions-legales.html` | Éditeur, hébergement (modèle à compléter). |
| `legal/politique-cookies.html` | Cookies & traceurs. |
| `legal/assets/style.css` | Mise en forme commune. |

Remplacez les champs entre **crochets** `[…]` par les informations officielles de l'INJS.

### Publier avec GitHub Pages

1. Pousser le dossier `docs/` sur la branche de publication du dépôt GitHub.
2. **Settings** → **Pages** → **Build and deployment** : source **Deploy from a branch**,
   dossier **`/docs`**.
3. Après build, les pages légales sont du type
   `https://<utilisateur>.github.io/<nom-du-depot>/legal/index.html`.
   L'URL de politique de confidentialité à fournir à la Play Console (exigence caméra) est
   celle de la page « application mobile INJS — Présences ».

Le fichier **`.nojekyll`** à la racine de `docs/` évite que Jekyll ignore ou transforme des
fichiers. GitHub Pages sert le site en **HTTPS** par défaut, comme l'exige la Play Console.
