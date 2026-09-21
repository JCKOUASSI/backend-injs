# Travailler sur INJS-LMD depuis VS Code

Ce guide couvre **tout le cycle** depuis VS Code : développement local (API + site),
tests, PR GitHub, et déploiement vers la prod (`injs.badge-qr-code.pro`).

La configuration versionnée vit dans `.vscode/` (tasks, launch, extensions, settings) ;
VS Code propose d'installer les extensions recommandées à l'ouverture du dossier.

---

## 1. Prérequis (une seule fois)

| Outil | Version | Usage |
|---|---|---|
| Python | 3.12 visé (3.11 OK) | API Django |
| Node.js | 22 | Front Vite/React |
| VS Code | récent | + extensions recommandées |
| GitHub CLI (`gh`) | toute récente | PR, Actions, déploiement |
| bash | macOS/Linux natif ; **Windows : WSL ou Git Bash** | scripts `arena/*.sh` |

Authentification GitHub depuis un terminal VS Code : `gh auth login`.

## 2. Premier lancement

```bash
git clone https://github.com/JCKOUASSI/backend-injs.git
cd backend-injs
git checkout arena/01a0c1b3-backend-injs   # ou main après fusion du PR #2
code .
```

Puis, dans VS Code :

1. **Terminal ▸ Exécuter la tâche… ▸ `INJS 1 · Bootstrap`** — crée `backend/.venv`,
   installe les dépendances Python et NPM, écrit l'overlay sandbox.
2. **Terminal ▸ Exécuter la tâche… ▸ `INJS · Migrations (sandbox)`** — applique les
   migrations sur la base SQLite.

## 3. Lancer l'API (8000) et le site (3000)

Deux façons équivalentes :

- **Tâches** : `INJS · API Django :8000 (sandbox SQLite)` puis `INJS · Site web :3000 (Vite)` ;
- **Débogage** : `F5` ▸ **`Stack INJS complète (API + Front)`** — démarre l'API sous le
  débogueur Python, le front Vite, puis ouvre Chrome sur `http://localhost:3000`
  (points d'arrêt Django **et** React actifs).

| URL | Quoi |
|---|---|
| `http://localhost:3000` | Site web INJS-LMD (proxy `/api` vers l'API, zéro CORS) |
| `http://localhost:8000/api/docs/` | Documentation Swagger de l'API |
| `http://localhost:8000/admin/` | Admin Django |

**Compte de démonstration** : `admin` / `Arena-Demo#2026` (créé par `migrate` via les
variables `DJANGO_SUPERUSER_*`, voir `backend/authentication/apps.py`).
Sur le sandbox d'aperçu Arena uniquement, `/admin/` auto-connecte en `admin`.

> Port figés par règle projet : API **8000**, front **3000** (Vite `strictPort`).
> En cas de port occupé : `pkill -f 'manage.py runserver'` / `pkill -f vite`.

## 4. Tâches disponibles (Terminal ▸ Exécuter la tâche…)

| Tâche | Rôle |
|---|---|
| `INJS 1 · Bootstrap` | Préparer l'environnement (une fois / après reset) |
| `INJS · Migrations (sandbox)` | Appliquer les migrations SQLite |
| `INJS · API Django :8000 (sandbox SQLite)` | API dev (réglages sandbox) |
| `INJS · API Django :8000 (config réelle)` | API avec `config.settings` (PostgreSQL) |
| `INJS · Site web :3000 (Vite)` | Front + proxy API |
| `INJS · Tests backend` | Suite Django complète |
| `INJS · Tests frontend (Vitest)` | Suite Vitest |
| `INJS · Lint frontend` / `Build frontend` | ESLint / build de prod |
| `INJS · Hygiène du dépôt` | Garde-fou P00-02/P00-05 (CI) |
| `INJS · Smoke INJS-LMD` | Parcours métier 23 étapes |
| `INJS · Sonde sandbox` | Feux verts environnement |
| `PR · État et vérifications` | Statut des PR/checks |
| `Déploiement · Sync dry-run` | Simulation `main → injs-app` |
| `Déploiement · Sync push réel` | **Arme** le push vers la prod |
| `Déploiement · Suivre les exécutions` | Historique du workflow de sync |

## 5. Cycle PR depuis VS Code

- Extension **GitHub Pull Requests and Issues** (recommandée) : créer, relire,
  fusionner les PR et relancer les checks sans quitter VS Code ;
- ou CLI : `gh pr create`, `gh pr checks 2 --watch`, `gh pr merge 2`.

> ⚠️ Si les checks restent « pending → failure » en quelques secondes sans exécuter
> d'étape, c'est le blocage **facturation GitHub** (Billing & plans → moyen de
> paiement / spending limit). Aucun rapport avec le code.

## 6. Déploiement (chaîne complète)

```
JCKOUASSI/backend-injs @ main
  → sync-injs-app.yml → Tobi-nw/injs-app @ main
  → Actions Docker Hub → images ophirdesire/*
  → VPS → https://injs.badge-qr-code.pro/
```

1. Fusionner le PR vers `main` (checks verts obligatoires) ;
2. **Une fois** : s'assurer que la variable du dépôt `SYNC_SOURCE_REF` vaut `main`
   (le déclencheur automatique du workflow n'écoute aujourd'hui que l'ancienne
   branche `arena/01a0a27f-…` — l'astuce « dry-run/push réel » passe explicitement
   `source_ref=main`, donc elle fonctionne sans autre modification) ;
3. Tâche `Déploiement · Sync dry-run vers injs-app` → lire le rapport dans
   l'onglet **Actions** ;
4. Tâche `Déploiement · Sync push réel vers injs-app` → les Actions du dépôt cible
   construisent les images `ophirdesire/*`, le VPS les déploie ;
5. Vérifier `https://injs.badge-qr-code.pro/` (le script pousse en mode
   `fastforward`, jamais de force — l'historique cible est préservé).

## 7. Dépannage

| Symptôme | Cause / solution |
|---|---|
| `bash` introuvable (Windows) | Utiliser WSL ou Git Bash, ouvrir le dossier dedans |
| `${command:python.interpreterPath}` non résolu | Installer l'extension Python puis sélectionner l'interpréteur `backend/.venv` |
| `lancer-api.sh` : « environnement absent » | Lancer la tâche `INJS 1 · Bootstrap` |
| Site 3000 refusé / page blanche | Vérifier que l'API tourne sur 8000 (le proxy cible `127.0.0.1:8000`) |
| Connexion web OK API mais échec front | Stockage navigateur bloquant — corrigé par `safeStorage.js` (vider le site des paramètres du navigateur si résidu) |
| Checks PR rouges en 2 s | Facturation GitHub (voir §5) |
