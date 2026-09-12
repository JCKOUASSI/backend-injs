# Tests frontend — stratégie, harnais et couverture (Vitest)

> Document de référence du dispositif de tests du frontend web (`frontend/`, Vite + React 18).
> Introduit par le lot **P00-04 [LOT 0]** (filet de sécurité de tests automatisés), puis
> étendu au **[LOT 1]** (moteur de tableaux/listes génériques et formulaire de décision
> pédagogique), au **[LOT 2]** (page de liste *serveur* typée `Users` : recherche
> debounced, onglets/rôles, pagination et écritures CRUD), au **[LOT 3]** (contrat
> d'**isolation des données par secrétariat** dans `Statistiques`, et période de présence
> du `Dashboard` — ce dernier a révélé un bug réel), au **[LOT 4]** (**correctif** de ce
> bug de closure, voir §10.5), au **[LOT 5]** (hygiène corrective : ferme les
> écarts mineurs §10.4 et §10.6) et au **[LOT 6]** (soldage de **tous** les
> avertissements `react-hooks/exhaustive-deps` : faux positifs dûment tranchés,
> défauts de mémoïsation et trou de synchronisation §10.7, avec régressions).
> Les LOT 4 à 6 sont les seuls à toucher la logique applicative, sur feu vert
> explicite.
> Il décrit l'état **réel** du dépôt, les conventions à respecter et les anomalies
> repérées grâce aux tests mais **laissées volontairement non corrigées** à ce lot.
>
> Voir aussi : [ARCHITECTURE.md](ARCHITECTURE.md), [sécurité des données](SECURITE_DONNEES.md),
> [README racine](../README.md).

Date de référence : 12 septembre 2026.

---

## 1. Objectif et contraintes du lot 0

Mettre en place un filet de tests automatisés **sans modifier le comportement de
l'application** :

- **Aucune montée de version** de React (reste en `^18.2.0`) ni de Vite (reste en `^7.0.0`).
- **Aucune page n'est réécrite pour la rendre testable.** On s'adapte *depuis
  l'extérieur* : providers dédiés, doubles de l'API, et ponctuellement des
  `data-testid` ajoutés sans toucher à la logique.
- **Aucune modification de logique métier.** Quand un test révèle un écart ou un
  bug, il est **signalé** dans ce document (§10) et, au besoin, par un test
  `[écart]` qui fige le comportement observé ; il n'est pas corrigé en silence.
- **Aucune dépendance lourde de composants UI** n'est ajoutée.

Paliers visés (cf. prompt P00-04) :

1. `src/utils/roles.js` — **100 %** (contrat de sécurité de l'UI) ;
2. `src/services/**` et `src/context/**` — **≥ 80 %** (authentification, JWT, refresh, API) ;
3. **au moins un test *smoke* par page existante**, avec publication des pages
   qui n'ont pas de test fonctionnel dédié ;
4. des **seuils de couverture en CI qui ne peuvent que monter**.

---

## 2. Pile de test et versions

Le projet reste sur Vite 7 / React 18.2 ; seules des dépendances de
développement ont été ajoutées (devDependencies) :

| Paquet | Version | Rôle |
| --- | --- | --- |
| `vitest` | `^3.2.4` | moteur de test compatible Vite, transform ESM natif |
| `@vitest/coverage-v8` | `^3.2.4` | couverture instrumentée par V8 |
| `jsdom` | `^25.0.1` | DOM simulé |
| `@testing-library/react` | `^16.1.0` | rendu de composants |
| `@testing-library/dom` | `^10.4.0` | requêtes de requête DOM (pair de RTL) |
| `@testing-library/jest-dom` | `^6.6.3` | matcheurs (`toBeInTheDocument`, …) |
| `@testing-library/user-event` | `^14.5.2` | interactions réalistes (clavier/souris) |

> Pas de `msw` au lot 0 : l'application utilise l'API **`fetch` native** (pas
> axios) ; un double manuel, synchrone et introspectable (`src/test/utils/mockApi.js`)
> s'est révélé plus simple et plus rapide à mettre au point que une surcouche
> réseau. `msw` reste une option pour des lots ultérieurs.

---

## 3. Commandes

Depuis `frontend/` :

```bash
npm run test           # Vitest en mode watch (développement)
npm run test:run       # passage unique (utilisé en local et en CI)
npm run test:coverage # passage unique + couverture + application des seuils
```

Lancer un seul fichier ou une sélection :

```bash
npx vitest run src/utils/roles.test.js
npx vitest run src/context src/services
npx vitest run src/test/smoke/pages.smoke.test.jsx
```

Le code de sortie est non nul si un test échoue **ou** si un seuil de couverture
n'est pas respecté (voir §7). Le rapport HTML de couverture est généré dans
`frontend/coverage/` (dossier ignoré par Git).

---

## 4. Configuration

- **`frontend/vitest.config.js`** — configuration dédiée :
  - `environment: 'jsdom'`, `globals: true` (`describe/it/expect/vi` disponibles sans import) ;
  - alias **`@` strictement identique à celui de Vite**. Pour garantir
    l'alignement, l'alias est défini une seule fois dans `vite.config.js`
    (`const alias = { '@': fileURLToPath(new URL('./src', import.meta.url)) }`)
    et repris à l'identique dans `vitest.config.js` ;
  - `setupFiles: ['./src/test/setup.js']` ;
  - **exécution mono-thread** (`poolOptions.threads.singleThread`) : les tests
    manipulent un même `localStorage`/jsdom et le module de rafraîchissement JWT
    mono-flight (`api.js`) ; l'ordonnancement séquentiel évite les interférences ;
  - `restoreMocks` / `clearMocks` activés ;
  - seuils de couverture (§7).
- **`frontend/src/test/setup.js`** — chargé avant chaque fichier de test :
  matcheurs jest-dom, `cleanup()` après chaque test, vidange des stockages, et
  **polyfils inertes** pour les API absentes de jsdom (`matchMedia`,
  `ResizeObserver`, `IntersectionObserver`, `scrollIntoView`,
  `canvas.getContext`, `offsetWidth/Height` déterministes). Ces polyfils ne sont
  pas des comportements de production : ils débloquent seulement le rendu.
- **`frontend/.eslintrc.cjs`** — un bloc `overrides` déclare les globales Vitest
  pour `src/test/**` et les `*.test.*` / `*.spec.*` (aucune dépendance ESLint
  ajoutée), et `coverage/` est ignoré.

---

## 5. Le harnais de test : `src/test/utils/`

```
src/test/
├── setup.js                  # polyfils jsdom + reset global
├── smoke/
│   └── pages.smoke.test.jsx  # un test de montage par page (53 pages)
├── fixtures/
│   └── dashboard.js          # statistiques 100 % chiffrées (Dashboard/Stats)
└── utils/
    ├── factories.js          # utilisateurs / réponses d'auth / pagination
    ├── mockApi.js            # double de l'API fetch (données « vides » sûres)
    ├── async.js             # helpers d'attente (promesses, timers)
    ├── renderWithProviders.jsx
    └── ErrorBoundary.jsx     # transforme une erreur de rendu en <div data-testid="render-crash">
```

### 5.1 `renderWithProviders(ui, { route, routes, user })`

Emballe l'écran dans les **mêmes providers que la production** :

`QueryClientProvider` (React Query, avec `retry: false`) → `AuthProvider` →
`ToastProvider` → `MemoryRouter` (route initiale paramétrable, routes auxiliaires).

Retourne en plus le conteneur et l'utilisateur courant, pour les assertions.
Les tests ne doivent pas reconstruire eux-mêmes ces providers.

> **Garder la garde d'authentification.** En production `ProtectedRoute`
> (`App.jsx`) n'affiche la page qu'après résolution de `GET /auth/me/`. Le
> harnais, lui, rend le composant tout de suite : pour les pages dont les
> requêtes initiales dépendent du rôle/secrétariat (`Statistiques`,
> `Dashboard`), envelopper le composant d'un petit `WaitForAuth` (qui lit
> `useAuth()` et affiche un spinner le temps de la résolution), sinon une
> requête « anonyme » parasite est émise avant que `user` soit connu. Les
> tests `Statistiques`/`Dashboard` fournissent ce composant.

### 5.2 `factories.js`

- `ALL_ROLES` : les **12 rôles** de l'application, dans l'ordre de la matrice :
  `ADMIN`, `DIRECTION`, `CHEF_CPFAE_ADMIN`, `CPFAE_ADMIN`, `CHEF_SECRETARIAT`,
  `SECRETARIAT`, `FINANCE`, `ARCHIVE`, `ENCADRANT`, `SUPERVISEUR`, `FORMATEUR`,
  `AUDITEUR`.
- `makeUser(role, overrides)` : un utilisateur complet et cohérent pour un rôle.
- `makeUsersForAllRoles()` : utilitaire de parcours matriciel.
- `WEB_FORBIDDEN_ROLES = ['FORMATEUR', 'AUDITEUR']` : ces deux rôles sont des
  comptes à usage mobile ; ils ne doivent pas ouvrir de session web.
- `makeLoginResponse(user, { refreshInCookie, refresh, access })` : corps de
  `/authentication/login/` (jeton refresh en cookie ou dans le corps).
- `paginated(results, page, pageSize)` : réponse DRF paginée (`count/next/previous/results`).

### 5.3 `mockApi.js` — double du module `services/api`

Il remplace le **module** `@/services/api` (pas `window.fetch`) via
`vi.mock('@/services/api', …)` en tête de test, en renvoyant le même objet mock
que celui importé par les pages. Les tests unitaires du client
(`services/api.test.js`) prennent quant à eux le relais en simulant
`window.fetch` directement.

- **`safeData` (Proxy « donnée vide sûre »)** : tant qu'aucune route n'est
  explicitement définie, toute réponse renvoie un objet « caméléon » : accéder à
  une propriété rend un tableau vide, un nombre sûr ou un sous-objet selon
  l'usage, sans jamais lever. Cela permet de monter des pages même quand le test
  ne décrit pas chaque endpoint.
  - Invariant Proxy respecté : pour une cible tableau, le piège `ownKeys`
    délègue à `Reflect.ownKeys` et `getOwnPropertyDescriptor` à `Reflect`, afin
    que `length` reste présent (sinon React/`useState` lèvent
    `'ownKeys' on proxy: trap result did not include 'length'`).
- **Contrôleur `apiController`** :
  - `setRoute(match, data, status = 200)` / `reset()` : `match` est une chaîne
    (chemin exact, comparé **sans** la query string) ou une `RegExp` ; les
    routes sont évaluées dans l'ordre d'enregistrement (déclarer les plus
    spécifiques en premier). `data` est soit une valeur statique, soit une
    **fonction `(path, body) => données | { data, status }`**, appelée à chaque
    requête : c'est ainsi que les tests de listes paginent/filtrent en lisant
    les paramètres de la query string (`new URL(path, base).searchParams`). Une
    fonction qui **lève** (`throw Object.assign(new Error(), { response: { data } })`)
    fait rejeter la promesse du client et permet de simuler une erreur HTTP ;
  - `setMe(user)` : force l'utilisateur authentifié pour les écrans ;
  - `findCall(method, matcher)` / `lastBody(method)` : introspection des appels
    (URL, méthode, corps). Les méthodes `api.*` sont des `vi.fn` : on peut aussi
    employer `mockRejectedValueOnce` pour forcer une erreur ponctuelle.

> Certains écrans font des calculs numériques (ex. `Dashboard` :
> `.toFixed()` sur les statistiques). Une donnée « vide » générique (tableau) ne
> convient pas : on injecte alors une **fixture numérique** via `setRoute`
> (`dashboardStats()` / `dashboardStatsWithPeriods()` dans
> `src/test/fixtures/dashboard.js`, partagées par le smoke et les tests dédiés),
> sans modifier la page.

### 5.4 Helpers asynchrones et d'erreur

- `flushPromises(n)` : vide plusieurs ticks de micro/tâches pour laisser les
  effets de montage et les `await fetch` se résoudre.
- Dans les tests de rendu, on attend de préférence à l'intérieur de
  `await act(async () => { … })` pour ne pas laisser de mises à jour d'état
  asynchrones en suspens (supprime les avertissements *« not wrapped in act »*).
- `TestErrorBoundary` (`ErrorBoundary.jsx`) : capture une erreur de rendu et
  affiche `<div data-testid="render-crash">`. Le smoke (§6.3) s'appuie dessus :
  une page qui jette au montage fait échouer le test au lieu de le faire planter.

---

## 6. Stratégie de test et couverture actuelle

### 6.1 Pyramide retenue

1. **Unitaires purs** — fonctions sans React (`utils/`, `services/`).
2. **Intégration de hooks/contextes** — `AuthProvider`, `ToastProvider`, hooks.
3. **Composants/pages** — interactions réalistes Testing Library.
4. **Smoke de rendu** — chaque page monte sans planter avec des données vides.

### 6.2 Fichiers de test colocalisés (22 fichiers, 472 tests)

Les tests sont **colocalisés** avec les sources (`*.test.js(x)` à côté du code),
à l'exception du smoke groupé.

**Authentification, services et rôles (LOT 0)**

| Fichier | Niveau | Ce qui est vérifié |
| --- | --- | --- |
| `src/utils/roles.test.js` | unitaire | **Matrice complète des 12 rôles** : permissions, libellés, accès aux modules, cohérence des helpers. **100 %** de la fonction. |
| `src/services/api.test.js` | unitaire | Client API : construction d'URL, en-têtes, gestion 401 → refresh JWT, **partage mono-flight** d'un refresh concurrent, refresh depuis cookie ou corps, erreurs réseau/serveur, gestion des noms de fichiers UTF-8 dans `Content-Disposition`. |
| `src/services/scolarite.test.js` | unitaire | Services scolarité/admissions : chemins d'endpoint exacts (slash final Django), paramètres de requête, passages à blanc. |
| `src/context/AuthContext.test.jsx` | intégration | Connexion, persistance, `refreshUser`, **purge de session** en cas de jeton illisible ou de rôle interdit (`FORMATEUR`), absence de stockage quand l'API ne renvoie pas de jeton refresh. |
| `src/context/ToastContext.test.jsx` | intégration | Affichage, types, disparition automatique (fausses horloges), fermeture manuelle. |
| `src/pages/Login.test.jsx` | composant/page | Marque INJS, soumission → création de session, erreurs serveur/génériques, **refus des rôles FORMATEUR/AUDITEUR**, bascule « voir le mot de passe », redirection si déjà authentifié. Contient aussi le test `[écart]` du §10.1. |
| `src/components/Pagination.test.jsx` | composant | Navigation bornée, libellés, gestion des bornes. |
| `src/components/ConfirmModal.test.jsx` | composant | Confirmation/annulation, action en cours, contenu. |
| `src/hooks/useClientPagination.test.jsx` | hook | Slice, remise à la page 1 selon dépendances, bornes, tailles de page. |

**Moteur de tableaux/listes génériques (LOT 1)**

| Fichier | Niveau | Ce qui est vérifié |
| --- | --- | --- |
| `src/utils/listFilters.test.js` | unitaire | Tout le moteur de requêtes des listes : `parseListPage`, persistance `sessionStorage`/liens Retour, lecture/construction des filtres **Modules, Participants, Utilisateurs, Formateurs (+délégation finance), Référentiels, Dashboard, Secrétariats**, omission des valeurs par défaut et de la page 1. |
| `src/utils/paginationPages.test.js` | unitaire | Numéros de page + ellipses (`buildPaginationItems`) : bornes, voisinage courant, absence de doublon, cas ≤ 9 pages. |
| `src/utils/paginatedResponse.test.js` | unitaire | Normalisation DRF (`parsePaginatedResponse`) : tableau legacy, objet paginé, calcul du nombre de pages, réponse nulle. |
| `src/utils/apiErrors.test.js` | unitaire | Formatage des erreurs DRF (`formatApiErrors`) : `detail`, `error`, erreurs de champ et libellés FR, fallback ; ignore les champs vides/blancs (`error: '   '`, `null`, `[]`) qui doivent retomber sur le message générique (§10.4 corrigé). |
| `src/hooks/usePickerPagination.test.jsx` | hook | Pagination des modales de sélection : `applyResponse` (count/total_pages), remise à la page 1 à l'ouverture, bornes. |
| `src/hooks/useListReturn.test.jsx` | hook | Retour vers une liste : priorité à l'état de navigation, puis `sessionStorage`, puis chemin brut ; état `from`. |
| `src/hooks/usePersistedListQuery.test.jsx` | hook | Synchronisation filtres/pagination → URL (`replace`) **et** `sessionStorage`, nettoyage et mise à jour quand une dépendance change. |

**Pages fonctionnelles (LOT 1, 2 & 3) et smoke**

| Fichier | Niveau | Ce qui est vérifié |
| --- | --- | --- |
| `src/pages/DecisionsPedagogiques.test.jsx` | page | **Tableau + formulaire de décision pédagogique** : en-têtes et critères, moyennes/présence/mentions/état validé, réponse en tableau ou objet, **filtrage par les cartes KPI**, état vide, **recalcul (POST → notification → rechargement)**, **ajustement d'une décision (sélect → PATCH → fermeture)**, annulation, et les trois chemins d'erreur (chargement, recalcul, validation). **100 % des lignes** de la page. |
| `src/pages/Users.test.jsx` | page | **Liste *serveur* typée, assemblage bout-en-bout (17 tests)** : chargement initial (`exclude_role`, page 1), **pagination serveur** (page 2 / précédent, plage « x–y sur n »), **recherche avec debounce 400 ms**, **filtre par rôle**, **onglets personnel / étudiants / enseignants** (reset page, `role=AUDITEUR/FORMATEUR`), persistance `sessionStorage`/URL, état vide, **erreur de chargement formatée**, permissions (les contrôles de gestion sont masqués sans `can_mutate_users`), **repli sur le seul onglet autorisé** quand l'URL réclame un onglet interdit (§10.2 LOT 6), **création** personnel et étudiant (POST + toast adapté), **erreur de validation** serveur, **édition** (PATCH, statut, mot de passe vide non transmis) et **suppression** avec confirmation. Couvre **89 % des lignes** de la page (reste surtout la branche « création d'un secrétariat à la volée »). Le mock reproduit un backend paginé (50/page) via une route dynamique. |
| `src/pages/Modules.test.jsx` | page | **Nettoyage des filtres obsolètes (2 tests, LOT 6)** : à l'arrivée des référentiels, un filtre d'URL absent des options (`grade=999`) est écarté, la liste est rechargée sans lui (un filtre valide comme `statut` est conservé) et un toast « Filtre(s) ignoré(s) » informe l'utilisateur ; cas contraire (filtres tous valides), aucune alerte. Couvre l'effet `referentielsData` dont les dépendances faisaient un faux positif ESLint (§10.2). |
| `src/pages/Statistiques.test.jsx` | page | **Contrat d'isolation multi-secrétariat (6 tests)** : admin sans périmètre forcé, application du filtre global, et pour les onglets **Point Journalier, Rapports & Bilans, Alertes** vérification que chaque requête porte le secrétariat **courant** (les 5 `useCallback` signalés par ESLint sont ainsi testés : pas de secrétariat périmé, voir §10.2) ; pour un **Chef Secrétariat**, TOUTES les requêtes (dès la première, méta comprise) sont verrouillées sur son id, le sélecteur est masqué et les onglets non autorisés absents. Rendu fidèle via la garde `WaitForAuth`. **+ 2 tests (LOT 6, §10.7)** sur le sous-composant exporté `BilanPeriodeFormationTable` : reprise d'un justificatif serveur reçu à clés de ligne identiques, et non-écrasement d'une saisie utilisateur. |
| `src/pages/Dashboard.test.jsx` | page | **Chargement, période de présence et erreurs (7 tests)** : endpoints stats/formations, liste « séance en cours » par défaut, bascule en **mode date** pour un jour spécifique passé, changement d'indicateurs Jour→Année, **deux tests de régression** de la bascule de période (bug de closure §10.5), et la **distinction échec total / échec partiel** (§10.6 corrigé). |
| `src/test/smoke/pages.smoke.test.jsx` | smoke | **53 pages montent sans erreur** (voir §6.3). |

### 6.3 Smoke « une page = un montage »

`src/test/smoke/pages.smoke.test.jsx` tient une table `PAGES` de tuples
`[nom, Composant, motif de route, URL]` couvrant les **53 écrans** : 37 racines,
3 pages d'archives, 13 écrans du module scolarité/admissions.

Chaque test : rend la page en `ADMIN`, avec `safeData` vide et l'utilisateur
injecté, attend la résolution des effets **dans `act()`**, puis affirme
l'absence de `data-testid="render-crash"`. Des fixtures ciblées sont associées
par nom via la table `FIXTURES` (ex. statistiques numériques du tableau de bord).

**Pour ajouter une page** : l'importer et ajouter une ligne à `PAGES`. Si elle
exige des formes de données précises (nombres, clés obligatoires), ajouter une
entrée dans `FIXTURES` plutôt que de modifier l'écran.

---

## 7. Couverture et seuils (qui ne peuvent que monter)

Mesure après le LOT 6 (V8, `npm run test:coverage`), sur les zones ciblées :

| Zone | Lignes | Instructions | Fonctions | Branches |
| --- | --- | --- | --- | --- |
| `src/utils/roles.js` | **100 %** | **100 %** | **100 %** | **100 %** |
| `src/utils/**` (rôles inclus) | 77 % | 77 % | 79 % | 86 % |
| `src/services/**` | **97 %** | 97 % | 97 % | **91 %** |
| `src/context/**` | **99 %** | 99 % | 89 % | **91 %** |
| `src/hooks/**` | **94 %** | 94 % | 84 % | **94 %** |
| `pages/DecisionsPedagogiques.jsx` | **100 %** | 100 % | 100 % | **95 %** |
| `pages/Users.jsx` | **89 %** | 89 % | 49 % | **69 %** |
| `pages/Dashboard.jsx` | **75 %** | 75 % | 43 % | **84 %** |
| `pages/Modules.jsx` | **37 %** | 37 % | 6 % | **59 %** |
| `pages/Statistiques.jsx` | **28 %** | 28 % | 17 % | **58 %** |
| **Global `src/` (toutes zones)** | **36 %** | 36 % | **26 %** | **64 %** |

> Les LOT 4 à 6 sont des correctifs ciblés : les seuils du LOT 3 restent
> inchangés (aucun seuil n'a été baissé), mais les régressions ajoutées font
> progressivement monter la couverture : 464 (LOT 4) → 467 (LOT 5) →
> **472 tests (LOT 6)** ; global 35,3 % de lignes / 24,9 % de fonctions au
> LOT 5 → **35,9 % / 25,5 %** au LOT 6. Le LOT 6 apporte notamment un test
> dédié à `Modules.jsx` (était couvert seulement par le smoke) et deux tests
> sur le tableau des justificatifs de `Statistiques.jsx` (§10.7).

Fichiers du moteur de listes quasi exhaustivement couverts : `listFilters.js`
97,5 % lignes / 97,3 % branches ; `paginationPages.js`, `paginatedResponse.js`
et les hooks de liste testés à **100 % de lignes** ; `apiErrors.js`
**97,8 % lignes / 93,5 % branches** (§10.4 corrigé).

Les seuils sont déclarés dans `vitest.config.js` (`coverage.thresholds`,
`perFile: false` pour les globes). Valeurs après le LOT 3 (ordres : lignes,
instructions, fonctions, branches) :

- `src/utils/roles.js` : **100 / 100 / 100 / 100** (contrat de sécurité) ;
- `src/utils/**` : **70 / 70 / 72 / 78** ;
- `src/services/**` : **90 / 90 / 90 / 85** ;
- `src/context/**` : **95 / 95 / 85 / 85** ;
- `src/hooks/**` : **88 / 88 / 80 / 85** ;
- plancher **global** : **34** % lignes/instructions, **23** % fonctions,
  **60** % branches (relevé à chaque lot : 28/16/48 au LOT 0 → 30/20/54 au
  LOT 1 → 32/22/58 au LOT 2 → ces valeurs au LOT 3).

Chaque seuil est arrondi *sous* la mesure pour absorber la volatilité du
maillage des branches. Le garde-fou est vérifié en CI : un build dont la
couverture passe sous un seuil échoue (contrôle positif validé — une couverture
artificiellement abaissée fait bien retourner un code de sortie non nul).

Règle d'hygiène : **ces chiffres ne peuvent qu'augmenter.** En ajoutant des
tests, on relève d'abord le plancher global puis les seuils par zone. On ne
les baisse jamais pour faire passer un build ; si une évolution légitime fait
chuter la couverture, on ajoute les tests correspondants dans le même lot.

La couverture est calculée sur `src/**/*.{js,jsx}` hors `main.jsx`, `src/test/**`,
fichiers `*.test.*`/`*.spec.*` et `src/assets/**`.

---

## 8. Intégration continue

`.github/workflows/ci.yml` contient deux emplois frontend **distincts** :

- **Frontend (Vite / React)** — `npm ci`, `npm run lint`, `npm run build` ;
- **Frontend tests (Vitest)** — `npm ci` puis **`npm run test:coverage`** (fait
  échouer le build si un test casse ou si un seuil de couverture régresse). Le
  rapport HTML de couverture est archivé comme artefact `frontend-coverage`
  (rétention 14 jours).

Ces emplois sont parallèles et indépendants de l'emploi backend (Django/Postgres)
et de l'emploi mobile (Flutter).

---

## 9. Conventions et pièges rencontrés

- **API = `fetch` natif.** Les tests remplacent `window.fetch` ; ne pas introduire
  axios ni mocker un module inexistant.
- **`user-event` + fausses horloges** peut boucler/dépasser le délai sous jsdom.
  Pour les tests qui utilisent `vi.useFakeTimers()`, préférer
  `fireEvent` puis `vi.advanceTimersByTime(...)` ; réserver `userEvent` aux tests
  en horloge réelle.
- **Sélecteurs de libellés stricts.** Sur la page de connexion, le bouton
  « Voir/masquer le mot de passe » fait qu'une recherche *regex*
  (`/mot de passe/i`) correspond à deux éléments. Utiliser les libellés exacts :
  `getByLabelText('Mot de passe')` et `getByLabelText("Nom d'utilisateur")`.
- **Toujours vider les effets dans `act()`** (voir §5.4) pour ne pas masquer de
  vraies erreurs derrière des avertissements React.
- **Données numériques vs « données vides »** : ne pas laisser `safeData`
  répondre à un endpoint dont les champs sont exploités arithmétiquement
  (`.toFixed`, totaux, pourcentages) — injecter une fixture chiffrée.
- **Texte interfolié dans un conteneur** (`{valeur} · <strong>…</strong>`).
  Testing Library évalue le texte d'un élément à partir de ses seuls nœuds texte
  directs : un fragment comme un nom de formation noyé dans un `<p>` contenant
  d'autres `<strong>` n'est pas trouvé par correspondance *chaîne exacte*. Utiliser
  une expression régulière (`findByText(/Licence/)`) ou réduire la portée avec
  `within(conteneur)`.
- **Libellé dupliqué entre une carte KPI cliquable et le badge d'une ligne**
  (page Décisions). Préférer `getAllByText('Ajourné')[0]` (la carte est rendue
  avant le tableau) ou restreindre avec `within(ligne.closest('tr'))`.
- **Libellés non reliés par `htmlFor` dans certaines modales** (ex. `Users`).
  `getByLabelText` ne trouve pas ces champs : on les récupère via leur
  `.form-group` (helper `modalField(modal, /libellé/)` du test `Users`, qui
  prend le `<label>` puis le `input/select` du même bloc).
- **Recherche avec debounce** : taper ne déclenche la requête qu'après 400 ms.
  Avec des horloges réelles, `fireEvent.change` puis
  `waitFor(() => expect(derniersParamètres.search)…)` suffit (timeout par défaut
  1 s) ; ne pas affirmer la requête immédiatement après la frappe.
- **Simuler une erreur HTTP avec le mock** : deux options — une route dynamique
  qui **lève** (le client `async` rejette alors), ou `mockRejectedValueOnce`
  sur une méthode (consommée une seule fois, sans réinitialisation manuelle).
- **Les tests ne changent pas la production** : pas de garde spécifique au test
  dans le code métier, pas de court-circuit `if (test)`. Les polyfils restent
  confinés à `src/test/setup.js` ; les assertions de sécurité (rôles) doivent
  rester en dehors du rendu.

---

## 10. Écarts et anomalies SIGNALÉS par les tests

Conformément aux contraintes, les lots 0 à 3 n'ont **jamais** modifié la
logique applicative : les écarts y étaient seulement constatés et tracés. Les
**LOT 4 et 5**, sur feu vert explicite, sont des lots correctifs (§10.4, §10.5,
§10.6). Les points encore ouverts sont ci-dessous.

### 10.1 Changement de mot de passe obligatoire ignoré par le web

Le backend expose l'attribut **`user.must_change_password`**
(`backend/authentication/models.py`, sérialiseurs, badges de comptes). Le
frontend (`src/pages/Login.jsx` et `AuthContext`) **ne gère aucune redirection
vers un écran de changement de mot de passe obligatoire** : un compte signalé
devant changer son mot de passe ouvre quand même une session normale.

Ce comportement est figé par un test `[écart]` dans `src/pages/Login.test.jsx`.
**À traiter** dans un lot de durcissement de l'authentification (parcours forcé,
route protégée, détection au login et après `refreshUser`).

### 10.2 Avertissements `react-hooks/exhaustive-deps` — TOUT SOLDÉ au LOT 6

Le lot 0 avait fait reculer les `exhaustive-deps` de **49 à 11** (les
avertissements « fonction de chargement au montage » étant réglés par une
**désactivation inline justifiée** : une fonction non mémoïsée dans les deps
provoquerait une boucle). Le LOT 4 en a soldé un vrai bug (§10.5). Le **LOT 6 a
tranché et soldé les 10 derniers** ; le lint ne remonte désormais **aucun**
avertissement `exhaustive-deps` (il ne reste que des `no-unused-vars`, §10.3) :

| Écran | Hook / sujet | Verdict et traitement LOT 6 |
| --- | --- | --- |
| `Statistiques.jsx` (5 `useCallback`) | `effectiveSecretariatId` absent | ✅ **FAUX POSITIF** prouvé au LOT 3 (6 tests d'isolation). `effectiveSecretariatId = lockedSecretariatId(user) || secretariatId` est une **string** : les 5 callbacks listent maintenant cette valeur **à la place de** `secretariatId` (qu'ils ne lisent pas directement — ESLint le signalait alors comme dépendance superflue). Aucun risque de boucle (primitive), requêtes identiques vérifiées. |
| `Statistiques.jsx` (`useEffect` justificatifs) | `data?.justificatifs` non listé | ⚠️ **TROU RÉEL CORRIGÉ** → §10.7 : la dépendance est ajoutée ; la saisie reste prioritaire via `justificatifsText \|\| …`. Deux régressions (synchronisation serveur, non-écrasement de la saisie), dont une preuve de mutation (échec sans le correctif). |
| ~~`Dashboard.jsx` (`useCallback`)~~ | ~~`presencePeriod` absent~~ | ✅ **CORRIGÉ au LOT 4** (§10.5). |
| `Modules.jsx` (`useEffect`) | `filters` + `showToast` absents | ✅ **FAUX POSITIF.** L'effet ne doit se déclencher qu'**à l'arrivée des référentiels** pour y confronter les filtres persistés ; il lit le `filters` du rendu courant (jamais périmé : React exécute la dernière version de l'effet). Ajouter `filters` ferait revalider après chaque saisie. Désactivation inline justifiée ; fonction de nettoyage désormais couverte par 2 tests (`Modules.test.jsx`). |
| `Users.jsx` (`useEffect`) | `availableTabs`, `userTab` absents | ✅ **FAUX POSITIF, dangereux à corriger naïvement.** Le repli d'onglet ne dépend que des trois booléens de permission : `availableTabs` est un tableau **neuf à chaque rendu** (son ajout ferait boucler l'effet), `userTab` est lu à jour. Désactivation inline justifiée ; régression « repli sur onglet autorisé » ajoutée. |
| `FinanceDashboard.jsx` (2 `useMemo`) | `volumesParModule`, `synthese` conditionnels | ⚠️ **DÉFAUT DE PERF RÉEL (sans donnée périmée).** Le fallback `[]` était un tableau neuf à chaque rendu, ce qui rendait les `useMemo` qui en dépendaient inopérants. Les deux valeurs sont désormais elles-mêmes mémoïsées (`useMemo` sur `data?.…`) ; comportement identique, rendu allégé, smoke validé. |

Les quelques avertissements « fonction de chargement au montage » (déjà traités
au lot 0) et les deux faux positifs ci-dessus portent une désactivation
**nominative et commentée** : c'est le résultat d'un tranchage, pas une mise
sous silence. Les tests associés (régressions LOT 4/6 + isolements LOT 3)
garantissent que toute régression future sera capturée.

> Les lots 0 à 3 n'ont modifié **aucune logique applicative** : uniquement des
> tests, le harnais, des fixtures et les seuils. Les LOT 4, 5 et 6 sont les lots
> correctifs (§10.4, §10.5, §10.6, §10.7 et §10.2). Le seul écart encore ouvert
> de cette section est §10.1 (fonctionnalité `must_change_password`, non
> tranchée).

### 10.3 Variables inutilisées (code mort) — 38 warnings, lot d'hygiène suivant

Les **10 `exhaustive-deps` étant soldés au LOT 6** (§10.2), les **40
avertissements ESLint restants** se réduisent à du **code mort / cosmétique**,
sans aucun effet sur le comportement :

- **38 `no-unused-vars`** préexistants (variables, imports ou états jamais lus,
  ex. `currentTrimestreParts`, `exportingEncadrants`, `nextSessionNumeroForDate`,
  `formatDate`, `navigate`, `Line`, `filtre_actif`, `fmtPct4`, `groupes`…) ;
- **2 `no-irregular-whitespace`** dans `FormationDetail.jsx:470` (espaces
  insécables dans un libellé de confirmation « Terminer la séance … ? »).

Ils sont antérieurs aux lots et ont été laissés hors périmètre pour garder des
commits focaux. Les `no-unused-vars` peuvent être supprimés dans un lot dédié
après vérification qu'il ne s'agit pas d'API publiques ; les espaces insolites
sont à remplacer par des espaces ordinaires (le sens du libellé est conservé).
**C'est le candidat naturel du LOT 7.**

### 10.4 Corrigé au LOT 5 — `formatApiErrors` : champ `error` blanc / valeurs vides

`formatApiErrors` (`src/utils/apiErrors.js`) reformatait auparavant une clé
`error` uniquement composée d'espaces comme une **erreur de champ**
(`error :    `) au lieu de retomber sur le message générique. **Corrigé au
LOT 5** : les valeurs sans message exploitable (`null`, chaîne blanche, tableau
vide) sont ignorées ; si aucune ligne exploitable ne reste, le `fallback` est
renvoyé. Tests dans `src/utils/apiErrors.test.js` (clés `error`/`empty`/
`missing`/`nothing` ignorées, champ renseigné conservé).

### 10.5 BUG corrigé au LOT 4 — `Dashboard` : closure périmée sur la période de présence

**Écran** : `src/pages/Dashboard.jsx` (chargement des « formations en cours »).

`loadDashboardData` est un `useCallback` dont le tableau de dépendances omettait
`presencePeriod` (il ne contenait que `selectedSecretariatId`, `referenceDate`,
`appliedVhPeriod`), alors que l'effet déclencheur, lui, listait `presencePeriod`.
Conséquence : après **« Jour spécifique » avec une date non courante →
Semaine / Mois / Année**, l'effet rappelait une ancienne closure encore en mode
« jour » ; la requête `GET /formations/list/` restait épinglée sur la date
(`date_mode=date&date=…`) au lieu de revenir à `seance_en_cours=true` (et
symétriquement, Semaine → Jour ne passait pas en mode date). Le bug était
invisible avec la date du jour.

**Correctif (LOT 4, feu vert explicite)** : ajout de `presencePeriod` aux
dépendances du `useCallback` (une seule ligne de logique applicative modifiée
dans tout le lot) :

```js
}, [selectedSecretariatId, referenceDate, presencePeriod, appliedVhPeriod])
```

Le polling (`useVisibilityPolling`) transite par un `ref` : changer l'identité
du callback ne crée pas de boucle de minuteur. Le test `[écart]` du LOT 3 a été
remplacé par **deux tests de régression** (les deux sens de bascule) dans
`src/pages/Dashboard.test.jsx`. L'avertissement ESLint correspondant a disparu
(51 → 50 warnings ; `exhaustive-deps` 11 → 10), et les 10 derniers warnings de
cette règle ont été soldés au **LOT 6** (§10.2) : le lint n'en affiche plus
aucun aujourd'hui.

### 10.6 Corrigé au LOT 5 — branche d'erreur « 3 » inatteignable dans `Dashboard`

`loadDashboardData` attend **2** promesses via `Promise.allSettled` mais testait
`failures.length === 3` pour le message « Erreur lors du chargement des
données » : cette branche était inatteignable, et un échec des deux requêtes
affichait à tort le message d'erreur partielle. **Corrigé au LOT 5** en
comparant au nombre de promesses réellement attendues
(`failures.length === settled.length`). Deux tests dans
`src/pages/Dashboard.test.jsx` distinguent désormais l'échec total (les 2
requêtes en échec → message total) de l'échec partiel (une seule → message
partiel).

### 10.7 Corrigé au LOT 6 — `Statistiques` : justificatifs non synchronisés à clés de ligne identiques

Le sous-composant `BilanPeriodeFormationTable` (tableau *Bilan période
formation*, volet Rapports & Bilans) synchronise la zone libre « justificatifs »
par un `useEffect` qui ne dépendait que des clés d'identité de ligne
(`data.titre`, `formation_id`, `annee`) et de la prop `justificatifsText`. Si
des justificatifs serveur arrivaient **pour une ligne déjà affichée** (mêmes clés
— rafraîchissement du tableau, réponse enrichie), la zone restait vide alors que
les données existaient. **Corrigé au LOT 6** en ajoutant `data?.justificatifs`
aux dépendances. La correction est **sans risque pour la saisie** : l'effet
écrit `justificatifsText || normalize(…)`, donc dès que l'utilisateur a saisi
quelque chose (prop parent non vide), la valeur serveur ne peut rien écraser.

Le sous-composant quasi pur est exporté pour les tests et couvert par deux
régressions dans `src/pages/Statistiques.test.jsx` : reprise d'un justificatif
serveur à clés identiques (en échec sans le correctif — preuve de mutation
constatée), et non-écrasement d'une saisie utilisateur.

---

## 11. Couverture des pages — ce qui reste à faire

Les **53 pages** existantes bénéficient d'au moins un test smoke (montage sans
erreur avec données vides) :

`Admissions, AffectationNew, AnalyseQualitative, ArchiveCahiersAppel,
ArchiveListesNotes, ArchivesDashboard, CampagneDetail, Campagnes, Candidatures,
ChargesEnseignants, Dashboard, DecisionsPedagogiques, EdtNew, Edts, Equivalences,
EvaluationAcademique, EvaluationDashboard, EvaluationDetail, EvaluationList,
EvaluationTake, FicheAuditeur, FicheEtudiant, FicheFormateur, FinanceAjustements,
FinanceDashboard, FinanceEncadrants, FinanceParametrage, FinancesEtudiantes,
Formateurs, FormationDetail, Formations, Graduation, Groupes, ImportExcel,
Inscriptions, Jurys, MaquetteDetail, Maquettes, ModuleDetail, Modules, MonEspace,
NotesModule, Parametres, Participants, Profile, QuizList, QuizTake, Rattrapages,
Referentiels, ScolariteDashboard, Secretariats, Statistiques, Users`.

**Aucune page n'est dépourvue de test.** État après le LOT 6 :

- six écrans disposent d'un test **fonctionnel dédié** : `Login.jsx`,
  `DecisionsPedagogiques.jsx` (100 % de lignes), `Users.jsx` (89 %, liste
  serveur + CRUD), `Dashboard.jsx` (75 %), `Modules.jsx` (37 %, nettoyage des
  filtres obsolètes) et `Statistiques.jsx` (28 %, contrat d'isolation par
  secrétariat + synchro des justificatifs §10.7) ;
- le **moteur de tableaux/listes génériques** est couvert indépendamment des
  écrans : construction des requêtes/filtres (`listFilters`), pagination
  (`paginationPages`, `paginatedResponse`), formatage des erreurs (`apiErrors`),
  et les hooks associés (`useClientPagination`, `usePickerPagination`,
  `useListReturn`, `usePersistedListQuery`) ;
- composants réutilisables testés : `Pagination`, `ConfirmModal` ; les autres
  composants ne sont exercés qu'indirectement via le smoke ;
- les **47 autres pages** sont couvertes en *smoke* (rendu) mais pas encore en
  *comportement métier* bout-en-bout.

Backlog proposé pour les lots suivants (ordre de valeur) :

1. ~~Moteur de listes + décision pédagogique~~ (LOT 1), ~~liste *serveur*
   typée~~ (LOT 2, `Users`), ~~isolation secrétariat Stats + période Dashboard~~
   (LOT 3). Restes ponctuels connus : branche `Users` « création d'un secrétariat
   à la volée », onglets/exports/widgets internes de `Statistiques`. Les bugs
   §10.4, §10.5 et §10.6 ont été **corrigés aux LOT 4 et 5**, avec régressions ;
   le **LOT 6** a soldé tous les `exhaustive-deps` (§10.2) et corrigé §10.7,
   avec un test dédié `Modules` et deux régressions supplémentaires ;
2. flux critiques par rôle : admissions/candidatures, présences/QR, notes et
   jurys, finances étudiantes, référentiels (priorité aux écrans qui écrivent) ;
3. **[candidat LOT 7] hygiène résiduelle sans risque comportemental** :
   - 38 `no-unused-vars` (§10.3) : suppression du code mort, fichier par
     fichier, en vérifiant qu'aucune API publique n'est concernée ;
   - 2 `no-irregular-whitespace` dans `FormationDetail.jsx:470` ;
   après ce lot, le lint frontend devrait être **vierge de warnings** ;
4. écart encore ouvert, dans un lot dédié :
   - §10.1 `must_change_password` (**fonctionnalité** : parcours forcé, nouvelle
     route protégée, gestion au login et après `refreshUser`) — en attente d'un
     choix produit (blocage total ou lecture seule) ;
5. composants partagés (modales, pickers, badges, panneaux de flux) ;
6. montée progressive du plancher de couverture global (§7) et extension aux
   pages encore couvertes seulement en smoke.
