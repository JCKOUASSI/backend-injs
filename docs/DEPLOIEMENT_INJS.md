# Déploiement INJS — chaîne `app-injslmd2026demo` → `injs-app` → Docker Hub → VPS

> Document d'exploitation du maillon **sync/push** ajouté le 2026-09-16.
> Il décrit la chaîne réelle d'après l'état du dépôt, et signale explicitement ce
> qui **n'a pas pu être vérifié** depuis le bac à sable (réseau sortant filtré).
> Le code de la sync vit dans [`scripts/sync-injs-app.sh`](../scripts/sync-injs-app.sh),
> piloté par [`.github/workflows/sync-injs-app.yml`](../.github/workflows/sync-injs-app.yml).

---

## 1. La chaîne, maillon par maillon

```
JCKOUASSI/app-injslmd2026demo @ <branche source>
        │  (1) sync/push  — ce dépôt : workflow Sync + scripts/sync-injs-app.sh
        ▼
Tobi-nw/injs-app @ main
        │  (2) Actions Docker Hub — dépôt cible : build & push linux/amd64
        ▼
images ophirdesire/qrcode-badge  +  ophirdesire/qr-badge-frontend
        │  (3) pull & relance — VPS (AlmaLinux x86_64)
        ▼
https://injs.badge-qr-code.pro/
```

| # | Maillon | Où ça tourne | Piloté par | Preuve à produire |
|---|---------|--------------|------------|-------------------|
| 1 | sync de l'arbre | Actions du **dépôt de dev** | `sync-injs-app.yml` → `scripts/sync-injs-app.sh` | commit `chore(sync): …` sur `injs-app@main` |
| 2 | build & push images | Actions du **dépôt cible** | ses propres workflows Docker Hub (mêmes Dockerfile que ici) | `gh run list -R Tobi-nw/injs-app` au vert + tags poussés |
| 3 | déploiement | VPS | `docker compose pull && up -d` (ou équivalent systemd) | digest d'image identique à celui de Docker Hub |
| 4 | service | VPS + reverse proxy | `frontend/nginx.conf` (SPA) + `backend/nginx/upstream.conf` | `curl` 200 sur `/` et sur l'API |

**Le maillon 1 ne construit rien** : il déplace un arbre de fichiers. C'est le
maillon 2 (dans l'autre dépôt) qui produit les images. Aucun workflow de ce
dépôt-ci ne pousse d'image `injs` : `docker-hub-main.yml` et
`docker-hub-channel1.yml` construisent à partir de **ce** dépôt, pour les
domaines `sygepcpfae.org` (prod historique) et `badge-qr-code.pro` (channel1).

---

## 2. État vérifié le 2026-09-16 (et ce qui ne l'est pas)

| Constat | Mesure | Conséquence |
|---------|--------|-------------|
| La branche de chaîne `arena/01a0a27f-app-injslmd2026demo` = `872e2668` (fusion PR #6) | `git merge-base --is-ancestor 872e2668 origin/main` → **non** ; `main` = `23499208` | **Cette branche est en retard sur `main`** : la pousser en prod déployerait un état antérieur (sans le lot « Dashboard Engine aligné sur Tableaux de bord INJS LMD-2026 »). À corriger avant toute exécution (voir §6.0). |
| `Tobi-nw/injs-app` | API GitHub → `404`, `git ls-remote` → `Repository not found` avec le compte du bac à sable | Le dépôt est **privé et hors de portée** de l'agent, ou inexistant. Rien n'a pu être lu de ses workflows : la configuration du maillon 2 est à vérifier sur place (§4.1). |
| `https://injs.badge-qr-code.pro/` | DNS → `152.228.233.123` ; TLS sortant du bac à sable bloqué (`SSL_ERROR_SYSCALL`, y compris sur `tobi-nw.github.io`) | **Site non vérifiable depuis l'agent.** Les vérifications §6.4 sont à faire depuis un navigateur ou le VPS. |
| `api.badge-qr-code.pro` | DNS → `57.128.215.210` (autre hôte que `injs.`) | L'API de l'instance INJS n'est **pas** le même serveur que le front `injs.` : le `VITE_API_URL` embarqué dans l'image de prod doit être décidé, pas deviné (§5). |
| `docker-hub-main.yml` (défauts prod) | `VITE_API_URL=https://api.sygepcpfae.org/api`, `VITE_BADGE_BASE_URL=https://api.sygepcpfae.org` | Si le dépôt cible réutilise ce fichier tel quel, **l'image « INJS » sera câblée sur le mauvais backend** (front blanc ou erreurs réseau). D'où §4.1 et §5. |
| Déchets de build suivis sur la branche de chaîne | `git ls-tree -r --name-only` sur `872e2668` : **100 fichiers sous `.pycache/`** (dont une arborescence `Applications/Xcode.app/…`), `backend/staticfiles/` exclu par `.gitignore` | Les pousser dans `injs-app` est bénin pour l'image Docker mais pollue son historique : `SYNC_EXCLUDE_PATHS=.pycache`. |
| CI du dépôt de dev | `ci.yml` rejeté par un parseur YAML strict (deux `name:` non quotés contenant ` : `, lignes 101 et 114). **Mesure avant/après** : runs `#130` (main) et `#129` (branche d'avant) = `failure` avec **0 job** (fichier jamais exécuté) ; sur la branche de ce lot, run `#134` = 5 jobs, dont 3 ✅ (Frontend, Frontend tests, **Outillage de sync**) | Les deux noms ont été quotés : la CI **s'exécute de nouveau**. Elle expose aussitôt deux échecs **préexistants et hors périmètre de ce lot** : Backend → étape « Hygiène du dépôt (données nominatives) » (à confirmer, probablement les dépôts de build suivis, voir ligne suivante) ; Mobile → « Pub get et analyse statique ». Ces deux verts sont le prérequis d'une ouverture de la sync automatique sur `main`. |
| Workflows Docker Hub sur `main` | `docker-hub-main.yml` : **4 échecs consécutifs** (runs 6 → 9), étape en échec = **« Login Docker Hub »** | Secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` absents ou révoqués : **aucune image produite**. Le maillon 2 d'INJS repose sur le même compte `ophirdesire` → à créer sur le dépôt cible **avant** la première sync, sinon la sync réussira et rien ne sera déployé. (Corps du log illisible depuis le bac à sable : `results-receiver.actions.githubusercontent.com` filtré ; preuve = nom d'étape en échec.) |
| Harnais de la sync | `scripts/sync-injs-app.sh --self-test` → **53 assertions / 14 cas, 0 échec** (hors ligne) | Le maillon 1 est testé ; les maillons 2 à 4 dépendent de dépôts/serveurs hors de portée d'ici. |

---

## 3. Règles de la sync (pourquoi ce design)

- **G0 — jamais de `--force` sur la cible.** Le mode par défaut `fastforward`
  crée **un commit fils de la pointe actuelle de `injs-app@main`**, porteur de
  l'arbre de la source. L'historique et les autres branches de la cible
  survivent ; le push est refusé s'il n'est plus un fast-forward (sync
  concurrente), jamais contourné. Le mode `mirror` (miroir exact, historique
  remplacé) n'est atteignable qu'avec `SYNC_ALLOW_MIRROR=1` posé à la main.
- **G1 — la cible ne doit pas être publique.** Un dépôt public recevrait le
  code, la documentation interne et tout l'historique accessible. `curl` sur
  l'API GitHub avant le clone ; blocage si `"private": false`. Dérogation
  explicite : `SYNC_ALLOW_PUBLIC_TARGET=1` (à ne pas utiliser pour INJS).
- **G2 — aucun secret ne sort.** L'arbre source est scanné avant push :
  `.env*`, `.netrc`, `.git-credentials`, clés `id_rsa`/`id_ed25519`, `*.pem`,
  `*.key`, `*.p12`, `credentials*.txt`, `*.dump`, `*.sql.gz`, `.pgpass` ⇒
  **sync refusée**. (Cohérent avec `manage.py check_repo_hygiene`.)
- **G3 — le contenu de la cible est remplacé, pas fusionné.** Tout fichier propre
  à `injs-app` (sa config CI, ses fichiers de déploiement) disparaîtrait. Les
  chemins à conserver se déclarent dans `SYNC_KEEP_PATHS` ; le script les
  **repêche dans l'historique** de la cible s'ils ont déjà été effacés, donc la
  liste reste stable d'une sync à l'autre. Un `checkout` qui échoue ou un chemin
  annoncé conservé et absent de l'index = **sync annulée** (pas de production
  amputée « par erreur »).
- **G4 — token hors journaux.** Le PAT ne transite ni dans l'URL poussée, ni
  dans `.git/config` (le remote est réécrit sans identifiants après le clone),
  ni en clair : il est fourni par `GIT_ASKPASS` et effacé à la sortie.
- **G5 — idempotence.** Arbre final == pointe cible ⇒ « déjà à jour », sortie 0,
  aucun push, aucune image reconstruite inutilement. En `mirror`, la comparaison
  porte sur les **commits** (pas seulement les arbres), pour ne jamais masquer
  un décalage d'historique.

---

## 4. Configuration à poser une fois

### 4.1 Dépôt cible `Tobi-nw/injs-app`

- [ ] dépôt **privé** ; `main` protégée autorisant les mainteneurs (pas de force-push) ;
- [ ] secrets d'Actions : `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (compte `ophirdesire`) ;
- [ ] variables d'Actions, **alignées sur le domaine INJS** :

  | Variable | Valeur visée INJS | Défaut actuel du workflow |
  |----------|-------------------|---------------------------|
  | `DOCKER_MAIN_VITE_API_URL` | `https://<api-injs>/api` (à trancher, §5) | `https://api.sygepcpfae.org/api` |
  | `DOCKER_MAIN_VITE_BADGE_BASE_URL` | `https://<api-injs>` | `https://api.sygepcpfae.org` |
  | `DOCKER_MAIN_VERSION_PREFIX` | `1.1` | `1.1` |

- [ ] un workflow déclenché par `push` sur `main` qui build `backend/` et
  `frontend/` et pousse un **tag épinglable** (le `main-<version>-amd64` du
  workflow actuel convient), en gardant le contrôle « `staticfiles` appartient à
  `appuser` » déjà présent ici ;
- [ ] `VITE_APP_TITLE=INJS-LMD — INJS Marcory` si la cible doit se démarquer de la prod historique.

### 4.2 Dépôt source `JCKOUASSI/app-injslmd2026demo`

- [ ] secret `INJS_APP_SYNC_TOKEN` : PAT fine-grained, **un seul repository**
  (`Tobi-nw/injs-app`), `Contents: Read and write` (+ `Actions: Read and write`
  si `SYNC_TRIGGER_DISPATCH=1`) ;
- [ ] variables : `SYNC_TARGET_REPO=Tobi-nw/injs-app`, `SYNC_TARGET_BRANCH=main`,
  `SYNC_SOURCE_REF=<branche source validée>` ; `SYNC_KEEP_PATHS` **rempli par le relevé**
  `bash scripts/sync-injs-app.sh --suggest-keep` (jamais à dire d'avance : c'est la liste
  des fichiers que la sync effacerait sur la cible, mesurée sur son contenu réel) ;
- [ ] tant que le maillon 2 de la cible n'est pas vert, **ne pas armer** : laisser
  `SYNC_DRY_RUN` absent (= mode sec sur `push`) ;
- [ ] environment `sync-injs-app` : *Required reviewers* + *Deployment branches*
  pour qu'une sync manuelle soit validée par un humain ;
- [ ] le fichier de workflow **et** le script doivent exister sur la branche qui
  déclenche : un `push` n'exécute que les workflows présents dans le commit poussé.

### 4.3 VPS

- [ ] images **épinglées par tag**, jamais `latest` (un `latest` partagé entre
  `sygepcpfae.org` et INJS ferait basculer l'instance INJS au gré des builds de
  l'autre produit) ;
- [ ] `docker compose pull && docker compose up -d`, puis contrôle §6.4 ;
- [ ] rollback = redémarrer sur le tag précédent (garder 2-3 tags locaux).

---

## 5. Le point qui casse une prod silencieuse : l'URL de l'API

`frontend/nginx.conf` **ne proxifie pas `/api`** (uniquement le fallback SPA), donc
`VITE_API_URL` doit être une **URL absolue** vers l'API : un `VITE_API_URL=/api`
relatif produirait un front muet. Deux hôtes existent dans le DNS :

| Hôte | IP relevée | Lecture |
|------|-----------|---------|
| `injs.badge-qr-code.pro` | `152.228.233.123` | front INJS (le VPS de cette chaîne) |
| `api.badge-qr-code.pro` | `57.128.215.210` | API du produit historique, **autre serveur** |

À trancher par l'exploitant, mesures à l'appui :

```bash
# 1) l'API est-elle servie sous le même hôte que le front INJS ?
curl -sS -o /dev/null -w '%{http_code}\n' https://injs.badge-qr-code.pro/api/
# 2) ou sur un sous-domaine dédié ?
curl -sS -o /dev/null -w '%{http_code}\n' https://api.injs.badge-qr-code.pro/api/
# 3) depuis le VPS, sans dépendre du DNS public :
docker compose -f backend/compose.yml ps && curl -sS localhost:8001/api/
```

Puis fixer la valeur dans **le dépôt cible** (§4.1) — pas dans la sync : la sync
ne fait que déplacer des fichiers, le câblage de l'API se fige au **build** de
l'image frontend.

---

## 6. Recette de première exécution

### 6.0 D'abord : décider ce qui est déployé

`arena/01a0a27f-app-injslmd2026demo` est en retard sur `main` (§2). Deux options,
à valoir explicitement :

- **A (recommandé)** — synchroniser `main` : `SYNC_SOURCE_REF=main`, et ajouter
  `main` à la liste `on.push.branches` **en connaissance de cause** (chaque
  fusion partirait alors en prod) ;
- **B** — assumer la branche de chaîne, en y amenant l'outillage. **Attention au ref** :
  l'outillage n'existe que sur la branche qui l'a créé (ici `arena/01a0a87d-…`, via le PR),
  **pas sur `main` tant que le PR n'est pas fusionné** — un `git checkout origin/main -- …`
  échoue en `pathspec … did not match any file(s)` :

```bash
OUTIL=arena/01a0a87d-app-injslmd2026demo     # ref QUI CONTIENT l'outillage (ou main, une fois fusionne)
git fetch origin arena/01a0a27f-app-injslmd2026demo "$OUTIL"
git switch -c outillage-sync 872e266828db6eac4733c6582bd64a37abd6b708
git checkout "$OUTIL" -- .github/workflows/sync-injs-app.yml scripts/sync-injs-app.sh docs/DEPLOIEMENT_INJS.md
git commit -m "chore(deploy): outillage de sync vers injs-app sur la branche de chaine"

# deux controles avant de pousser (le second est le plus important, voir ci-dessous)
bash scripts/sync-injs-app.sh --self-test | tail -1
git merge-base --is-ancestor 872e266828db6eac4733c6582bd64a37abd6b708 HEAD && echo "fast-forward OK"

git push origin HEAD:refs/heads/arena/01a0a27f-app-injslmd2026demo
```

> **Ce push déclenche lui-même le workflow — en mode sec.** Le défaut d'un run par
> `push` est `SYNC_DRY_RUN=1` : rien n'est poussé sur `injs-app` tant que le dépôt
> n'a pas été **armé explicitement** :
>
> ```bash
> # armement du push automatique sur push (volontaire, et seulement quand le
> # maillon « Actions Docker Hub » de la cible est vert) :
> gh variable set SYNC_DRY_RUN --repo JCKOUASSI/app-injslmd2026demo --body 0
> # toute autre valeur (variable absente, '1', 'true') = mode sec
> ```
>
> Grille de vérité des expressions (évaluée sur le fichier, pas sur une lecture à
> l'œil) : `push`+variable absente ⇒ SEC · `push`+`0` ⇒ REEL · `dispatch`+case
> `dry_run` cochée ⇒ SEC · `dispatch`+décochée ⇒ REEL. La version précédente du
> workflow poussait **réellement** sur `push` par défaut ; corrigé le 2026-09-16.
> Sans secret `INJS_APP_SYNC_TOKEN`, le run échoue à l'étape « Contrôle du secret de
> sync » : bruyant, sans effet de bord.

### 6.1 Sécheresse d'abord (aucune écriture)

```bash
cd app-injslmd2026demo
SYNC_OFFLINE=1 bash scripts/sync-injs-app.sh --self-test   # 53 assertions (14 cas), vert attendu
bash scripts/sync-injs-app.sh --suggest-keep                # ce que la cible PERDRAIT -> remplit SYNC_KEEP_PATHS
bash scripts/sync-injs-app.sh --dry-run                     # lit la cible, ne pousse pas
```

Les variables et le secret se posent par un **compte admin du dépôt** (le token de
l'agent n'a pas de portée Actions : `403 Resource not accessible by integration`).
`gh variable` existe à partir de **gh 2.22** ; sinon, équivalent API :

```bash
# variable d'Actions
gh api -X PUT repos/JCKOUASSI/app-injslmd2026demo/actions/variables/SYNC_EXCLUDE_PATHS \
  -f name=SYNC_EXCLUDE_PATHS -f value=.pycache
gh api repos/JCKOUASSI/app-injslmd2026demo/actions/variables | jq -r '.variables[]|"\(.name)=\(.value)"'
# secret d'Actions (la valeur transite par stdin, jamais par l'historique de shell)
gh api -X PUT repos/JCKOUASSI/app-injslmd2026demo/actions/secrets/INJS_APP_SYNC_TOKEN \
  --input <(jq -n --arg v "$(cat pat.txt)" '{name:"INJS_APP_SYNC_TOKEN", encrypted_value:$v}')   # via `gh secret set` : preferred
```

> Le dépôt de dev **ne doit contenir aucun** `pat.txt` : à créer hors du workspace,
> puis effacer. `gh secret set` chiffre côté client ; les `gh api` bruts exigent le
> public key (d'où la préférence pour `gh secret set`).

Le `--dry-run` répond aux trois questions qui comptent : quels fichiers
entrent/sortent (`+a / ~m / -d`), l'arbre est-il déjà à jour, et des fichiers
propres à la cible seraient-ils supprimés (⇒ à ajouter à `SYNC_KEEP_PATHS`).

### 6.2 Via Actions (voie normale)

`Actions → Sync (app-injslmd2026demo -> injs-app) → Run workflow`, `dry_run`
coché, puis re-déclencher `dry_run` décoché. Le run d'essai doit montrer :
harnais vert, dry-run, et le détail de l'effet sur la cible.

### 6.3 Ligne de commande (si l'agent n'a pas les droits)

```bash
export SYNC_TOKEN=ghp_…            # PAT fine-grained, cible uniquement
export SYNC_TARGET_REPO=Tobi-nw/injs-app SYNC_TARGET_BRANCH=main
export SYNC_SOURCE_REF=arena/01a0a27f-app-injslmd2026demo
bash scripts/sync-injs-app.sh --dry-run && bash scripts/sync-injs-app.sh
```

### 6.4 Contrôles après déploiement

```bash
gh run list -R Tobi-nw/injs-app -L 3                       # maillon 2 vert
docker buildx imagetools inspect ophirdesire/qr-badge-frontend:<tag>   # digest attendu
# sur le VPS :
docker image ls --digests | grep ophirdesire
curl -sS -o /dev/null -w 'front %{http_code}\n' https://injs.badge-qr-code.pro/
grep -o 'VITE_API_URL=[^ ]*' /etc/injs/.env 2>/dev/null || true   # câblage API réellement utilisé
```

Dans le navigateur : `Ctrl+Maj+R`, console vide d'erreur CORS/réseau, puis
connexion réelle sur un compte de test (le contrat d'API est figé par
`manage.py export_api_contract --check`, donc une réponse inattendue signal un
mauvais backend).

---

## 7. Runbook

| Symptôme | Cause probable | Remède |
|----------|---------------|--------|
| `Repository not found` au clone | PAT sans droit sur la cible, ou dépôt inexistant/renommé | PAT fine-grained **limité à** `Tobi-nw/injs-app` avec `Contents: Read and write` ; vérifier l'orthographe `owner/repo` |
| `G1 bloqué : cible publique` | le dépôt de prod est public | le passer privé (ou changer de cible) ; jamais `SYNC_ALLOW_PUBLIC_TARGET` pour INJS |
| `G2 hygiène` | un `.env`/dump suité dans la branche source | le retirer de l'historique de la branche (`git rm --cached` + commit) ; la sortie `SYNC_ALLOW_HYGIENE` n'existe que pour un cas documenté |
| `push refusé (…) non fast-forward` | une sync a couru entre-temps | relancer : le rebase du commit de sync est automatique |
| `Déjà à jour` alors qu'on attend un build | l'arbre est identique, donc **aucune** image reconstruite | forcer un run vide côté cible (`workflow_dispatch`) si le but est seulement de rebâtir |
| `des fichiers propres à la cible disparaissent` | `SYNC_KEEP_PATHS` incomplet | ajouter les chemins (§4.2), relancer — le script les repêche dans l'historique |
| `note: N fichier(s) de build suivis dans la branche source` | `.pycache/`, `dist/`, `*.pyc` commis sur la branche source | `SYNC_EXCLUDE_PATHS=.pycache` pour la sync, puis `git rm -r --cached` + `check_repo_hygiene` pour le régler à la source |
| `Sync poussée` côté dev mais aucune image sur Docker Hub | secrets `DOCKERHUB_*` absents sur le **dépôt cible** (état constaté ici : « Login Docker Hub » en échec) | créer `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` sur `injs-app`, relancer son workflow |
| Front blanc / erreurs réseau après déploiement | `VITE_API_URL` de build pointant ailleurs (§5) | reposer la variable cible puis **rebuilder** : la sync seule ne change pas une image déjà construite |
| `La branche « X » n'existe pas encore` | première sync vers une branche inexistante en `fastforward` | créer la branche sur la cible, ou `--mode mirror` avec `SYNC_ALLOW_MIRROR=1` |
| CI `main` rouge (cf. `docs/audits/BASELINE_2026-09.md` R10) | workflows Docker Hub en échec | réparer le maillon 2 **avant** d'ouvrir la sync automatique sur `main` |

---

## 8. Preuve : relier la prod au commit de dev

Chaîne de preuves à consigner à chaque déploiement (le champ est déjà dans le
message de commit généré par la sync) :

```
commit dev <sha>  →  commit sync <sha> (injs-app@main)  →  tags images <version>
                  →  digest VPS  →  HTTP 200 + parcours de fumée
```

```bash
git -C injs-app log -1 --format='%H%n%B' main | sed -n '1,8p'   # source + sha amont
```

---

## 9. Limites assumées

1. Le maillon 1 (sync) est testé ici ; les maillons 2 à 4 vivent dans un dépôt et
   un serveur **hors de portée de l'agent** : leurs cases §4 restent à cocher par
   l'exploitant.
2. Aucune vérification en ligne du site `injs.badge-qr-code.pro` n'a été possible
   depuis le bac à sable (§2) : les résultats attendus sont donnés en commandes,
   pas en affirmations.
3. **Le maillon 2 est en échec constaté** (4 runs rouges, étape « Login Docker Hub ») sur ce dépôt, et l'état du dépôt cible n'a pas pu être lu : rien ne garantit qu'une sync soit suivie d'une image. La sync doit rester **validée à la main** (`dry_run` d'abord, environment avec reviewers) tant que ce point n'est pas réglé.
4. La sync est **univoque** : `dev → prod`. Rien dans ce dépôt ne rapatrie un
   correctif chaud fait directement sur `injs-app` ; si cela arrive, il faut le
   rejouer à la main sur la branche source avant la sync suivante, sinon G0
   l'écrase au prochain passage.
