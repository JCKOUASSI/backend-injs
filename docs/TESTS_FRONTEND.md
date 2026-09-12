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
> défauts de mémoïsation et trou de synchronisation §10.7, avec régressions), puis
> au **[LOT 7]** (lint **vierge** : suppression du code mort réel, et — découverte
> majeure — réparation de **5 écrans Scolarité en panne** dont les « variables
> mortes » n'étaient que le symptôme, §10.8, avec régressions dédiées), puis au
> **[LOT 8]** (les actions rétablies au LOT 7 sont désormais exercées **au clic** :
> transitions de campagne, note, application d'équivalence, archivage d'ECUE,
> création d'affectation — écritures POST/DELETE vérifiées), puis au **[LOT 9]**
> (élargissement à un nouvel écran qui écrit : le parcours **candidatures
> d'admission** — liste/filtres, transitions, vérification et dépôt de pièces,
> ouverture d'admission, création candidat + candidature, cas d'erreur), puis au
> **[LOT 10]** (boucle de la chaîne : **décision et annulation d'admission**,
> profil administratif, **inscription d'un admis** via modale de confirmation),
> puis au **[LOT 11]** (termine le parcours étudiant : **inscriptions
> administratives** avec validation en cascade, et fiche étudiant — génération/
> retrait de **pédagogie**, affectation de **groupe**, **passerelle** vers les
> modules opérationnels), puis au **[LOT 12]** (la **fin du parcours académique** :
> **sessions de jury** LMD — workflow de transition contrôler → … → publier
> exercé pour chaque statut — et **diplômation** : validation/gel du PDF,
> révocation motivée et **portail public de vérification** ; ce lot a révélé
> une boucle de rechargement parasite sur échec de chargement, §10.10), puis au
> **[LOT 13]** (**correctif** de cet écart transverse : stabilisation de la
> valeur du `ToastContext.Provider`, avec régressions dédiées — §10.10), puis au
> **[LOT 14]** (la **saisie des notes d'un module** — chaînon entre la
> pédagogie et le jury : grille, calcul en direct mention/moyenne/admission,
> enregistrement en bloc `{notes, synthèses}`, colonnes dynamiques, fiches PDF),
> puis au **[LOT 15]** (domaine **présence** : planification des
> **rattrapages** inter-cohortes avec recherches débordancées, sélection
> multiple de séances/modules, génération de pointage et annulation confirmée ;
> et fiche de suivi d'un **auditeur** avec exports PDF/Excel — deux lots de
> tests purs), puis au **[LOT 16]** (deux volets de tests purs : d'une part
> l'**émargement en temps réel**, au cœur du gros écran `ModuleDetail` —
> onglet Séances (démarrage/fin/suppression/création via `ConfirmModal`) et
> onglet Présences (cinq cartes de statistiques, forçage de pointage
> unitaire, badgeage en masse, habilitations ENCADRANT / secrétariat /
> DIRECTION) ; d'autre part la **complétion des campagnes d'admission** —
> création d'une campagne en brouillon, toutes les transitions de statut
> restantes, ajout d'épreuve, convocations, verrouillage, calcul et
> publication du classement, campagne fermée et lecture seule ; deux
> constats produit en §10.11).
> Les LOT 4 à 7 et le LOT 13 sont les lots qui touchent la logique applicative,
> sur feu vert explicite ; les LOT 8 à 12 et 14 à 16 sont des lots de tests
> purs.
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

### 6.2 Fichiers de test colocalisés (36 fichiers, 620 tests)

Les tests sont **colocalisés** avec les sources (`*.test.js(x)` à côté du code),
à l'exception du smoke groupé.

**Authentification, services et rôles (LOT 0)**

| Fichier | Niveau | Ce qui est vérifié |
| --- | --- | --- |
| `src/utils/roles.test.js` | unitaire | **Matrice complète des 12 rôles** : permissions, libellés, accès aux modules, cohérence des helpers. **100 %** de la fonction. |
| `src/services/api.test.js` | unitaire | Client API : construction d'URL, en-têtes, gestion 401 → refresh JWT, **partage mono-flight** d'un refresh concurrent, refresh depuis cookie ou corps, erreurs réseau/serveur, gestion des noms de fichiers UTF-8 dans `Content-Disposition`. |
| `src/services/scolarite.test.js` | unitaire | Services scolarité/admissions : chemins d'endpoint exacts (slash final Django), paramètres de requête, passages à blanc. |
| `src/context/AuthContext.test.jsx` | intégration | Connexion, persistance, `refreshUser`, **purge de session** en cas de jeton illisible ou de rôle interdit (`FORMATEUR`), absence de stockage quand l'API ne renvoie pas de jeton refresh. |
| `src/context/ToastContext.test.jsx` | intégration | Affichage, types, disparition automatique (fausses horloges), fermeture manuelle, et **stabilité de la valeur de contexte à l'apparition/disparition d'un toast (régression §10.10, LOT 13)**. |
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
| `src/pages/scolarite/scolariteRendu.test.jsx` | page | **5 régressions (LOT 7, §10.8)** sur des écrans qui rendaient une page blanche sans planter : rendu effectif du titre de `Campagnes`, du libellé de `CampagneDetail`, du titre d'`Équivalences`, du libellé de `MaquetteDetail`, et — pour `ChargesEnseignants` — requête de l'année courante **au montage** puis enchaînement sur l'occupation des enseignants. Chaque test échouait avant la correction (preuve de mutation). |
| `src/pages/scolarite/scolariteActions.test.jsx` | page | **6 tests d'écriture au clic (LOT 8, §10.8)** sur les gestionnaires rétablis : `Campagnes` (Planifier sans confirmation puis Ouvrir **avec** `window.confirm`, bon `POST …/transition/` + rechargement ; cas d'erreur serveur avec toast), `CampagneDetail` (enregistrement d'une note `POST /epreuves/:id/notes/` avec les bons identifiants), `Equivalences` (`POST …/appliquer/` après confirmation), `MaquetteDetail` (`DELETE /ecues/:id/?mode=archive`), `ChargesEnseignants` (création d'affectation `POST /enseignants/affectations/` avec l'année courante et les champs typés). |
| `src/pages/scolarite/Candidatures.test.jsx` | page | **9 tests (LOT 9), parcours candidatures qui écrit** : liste + année courante, recherche `q` et filtre `statut` transmis en paramètres au service ; panneau « Dossier » : **transition de statut** (`POST …/transition/` + toast + rechargement), **validation/refus d'une pièce** (`POST …/pieces/:id/verifier/`, boutons désactivés sans fichier), **dépôt de fichier** multipart (`POST …/deposer/`, `FormData`), **ouverture d'admission** (`POST /admissions/admissions/`) ; **création** candidat puis candidature avec l'année courante (`POST /candidats/` puis `/candidatures/`) ; cas d'erreur serveur (transition refusée, création avec message champ). Couvre **97,5 % des lignes** de la page et porte le service `services/scolarite.js` à **100 % de lignes**. |
| `src/pages/scolarite/Admissions.test.jsx` | page | **8 tests (LOT 10), boucle admission** : liste/filtre par décision, état du bouton *Inscrire* selon `permet_inscription` ; panneau **profil administratif** (catégorie→grade liés, `PATCH /admissions/:id/`), **prononcé de décision** (`POST …/decision/`, panneau fermé, cas d'erreur) ; **inscription d'un admis** après modale (`POST /scolarite/inscriptions/depuis-admission/` `{admission_id, valider:true}` → matricule + navigation) ; **annulation** après confirmation (`POST …/annuler/`, rechargement) et annulation de la modale sans écriture. Couvre **98 % des lignes** de la page. |
| `src/pages/scolarite/Inscriptions.test.jsx` | page | **4 tests (LOT 11)** : liste et 4 filtres transmis au service (recherche `q`, statut, formation, niveau — les valeurs vides étant éliminées) ; **validation en cascade** (un brouillon enchaîne `EN_ATTENTE → A_VALIDER → VALIDEE` par 3 `POST …/transition/` dans l'ordre, puis toast + rechargement ; une inscription déjà validée n'a pas de bouton) ; cascade **interrompue** dès qu'une transition échoue (toast de l'erreur, les étapes suivantes ne sont pas émises). Couvre **99,4 % des lignes / 100 % des fonctions**. |
| `src/pages/scolarite/FicheEtudiant.test.jsx` | page | **6 tests (LOT 11)** : fiche avec inscription validée — rendu identité/programme/groupe/passerelle ; **génération de pédagogie** (`POST …/pedagogie/generer/`, nombre d'ajouts en toast), **retrait d'ECUE** (`DELETE /pedagogie/:id`, constats §10.9) ; **affectation à un groupe** (`POST …/affectations/`, bouton désactivé sans choix, option d'un groupe complet désactivée) ; **passerelle** prévisualisation puis synchronisation (`POST …/passerelle/`) ; fiche sans inscription validée = alerte et sections pédagogie/groupe absentes. Couvre **89,8 % des lignes / 100 % des fonctions**. |
| `src/pages/scolarite/Jurys.test.jsx` | page | **14 tests (LOT 12), fin du parcours académique** : sessions avec badges et **3 filtres** transmis tels quels (statut/année/formation, clés toujours présentes) ; **workflow de transition complet** exercé pour chaque statut par test paramétré (Contrôler/Calculer/Délibérer/Décider/Générer PV/Valider/Verrouiller/Publier → le bon `POST …/action/` `{action}`, session PUBLIÉE sans bouton) ; confirmation `window.confirm` acceptée/annulée ; action rejetée (toast du détail backend) ; **lecture seule** (DIRECTION : pas d'actions, référentiels non chargés) ; une **régression §10.10** (un échec de chargement = une seule requête, un seul toast, état vide). Couvre **100 % des lignes / 100 % des fonctions**. |
| `src/pages/scolarite/Graduation.test.jsx` | page | **15 tests (LOT 12), diplômation** : liste (badges, mention/ECTS, tirets de valeur absente, **lien PDF** uniquement pour un diplôme validé, en `target=_blank`), 3 filtres transmis ; **validation** d'un diplôme en attente (`POST …/valider/`, confirmation, toast, rechargement, annulation sans écriture, erreur backend) ; **révocation motivée** (`window.prompt` motif obligatoire : `POST …/revoquer/` `{motif}`, annulation et rejet serveur couverts) ; **portail public de vérification** (`GET …/verifier/{token}/`) : diplôme valide et ses détails, numéro inconnu (`valide:false` + raison), erreur serveur, absence de requête sans numéro ; **lecture seule** qui conserve le portail public ; une **régression §10.10** (échec de chargement sans relance). Couvre **100 % des lignes / 100 % des fonctions**. |
| `src/pages/scolarite/MonEspace.test.jsx` | page | **2 tests (LOT 13)** : rendu de la fiche étudiante (`/scan/me/fiche/`) et **régression §10.10 sur le second patron** (chargeur lancé par un `useEffect([toast])` direct) : quand la fiche est indisponible, une seule requête et un seul toast, sans boucle de rechargement. |
| `src/pages/NotesModule.test.jsx` | page | **20 tests (LOT 14), saisie des notes** (chaînon pédagogie → jury) : chargement module + grille (colonnes, barèmes, notes pré-remplies, critères seuil/présence, mention/moyenne/admission calculés, « saisi par »), recherche/filtre, état vide ; **saisie en direct** (mention normalisée /20, moyenne, bandeau « modifications non sauvegardées », note hors plage **0–20**, observations, navigation clavier **Entrée → champ suivant**) ; **enregistrement en bloc** `POST …/notes/bulk/` avec le payload `{notes, synthèses}` (mention calculée, cellules vides exclues), réponse partiellement en erreur (toast d'avertissement), échec (la saisie est conservée) ; **colonnes dynamiques** (ajout `POST …/notes/colonnes/`, libellé vide refusé, suppression `DELETE` avec confirmation et impossible à 1 colonne) ; **fiches PDF** module/individuelle (`getBlob`), confirmation si saisie non enregistrée, erreur de génération ; liens Décisions/Retour ; une régression §10.10 (une seule requête sur échec de chargement). Couvre **97,6 % des lignes / 92 % des fonctions**. |
| `src/pages/Rattrapages.test.jsx` | page | **18 tests (LOT 15), rattrapages de présence** : liste avec badges de statut/cohorte et **filtres débordancés** (`statut`, `q` vérifiés en query) ; états erreur/vide ; **lecture seule** pour un rôle hors `PRESENCE_ACTION_ROLES` (DIRECTION) ; **création** via recherche d'étudiant puis **sélection multiple de séances** (recherche ciblée `participant=`, séance « déjà inscrit » verrouillée, pastille ajout/retrait), mode **module entier** (ajout de toutes ses séances, module déjà fait verrouillé), motif, case « forcer la présence », validation sans étudiant/séance, **payload** `{participant_id, seance_rattrapage_ids, motif, generer_presence}` vérifié, toast créés/réactivés/ignorés, erreur serveur gardée dans la modale ; **génération de pointage** (`POST …/generer-presence/`) et **annulation** via `ConfirmModal` (avec/sans pointage → `supprimer_pointage`, refus = aucun appel), actions absentes sur un rattrapage annulé, cas d'erreur des deux écritures. Couvre **97,3 % des lignes / 86 % de branches** (le résidu est du filtrage défensif inatteignable via l'UI). |
| `src/pages/FicheAuditeur.test.jsx` | page | **8 tests (LOT 15), fiche de suivi d'un auditeur** : synthèse (formation, moyenne, classement, décision finale), suivi par module (heures présence/prevues, taux, moyenne, épreuves), état « aucun module », tirets des champs absents, erreur de chargement → « fiche introuvable », **exports PDF et Excel** (`getBlob`), nom de fichier par défaut, erreur d'export. Couvre **100 % des lignes / 100 % des fonctions**. |
| `src/pages/ModuleDetail.test.jsx` | page | **15 tests (LOT 16), émargement — onglets Séances et Présences de `ModuleDetail`**. Séances : badges de statut lus sur `en_cours`/`terminee`, compteurs d'onglets ; **démarrage** (`POST …/sessions/:id/start/` via `ConfirmModal`, toast + rechargement) et **annulation sans appel** ; **fin** (`stop/`), **suppression** (`DELETE …/delete/`, annulation puis confirmation), erreur backend (toast du `detail`), **création** (`POST …/sessions/new/` avec les 4 champs). **Habilitations** : un ENCADRANT peut démarrer mais pas créer/supprimer, la DIRECTION est strictement en lecture (pas de forçage). Présences : les **5 cartes de stats** (attendus = étudiants+enseignants+encadrants, en salle, présents, absents, taux), date sans pointage = tout le monde absent et message explicite ; **forçage unitaire** d'un étudiant absent (`POST …/force-pointage/` avec `{personne_id, type_personne, action:'ENTREE', motif, module_id, date_journee}`, bouton désactivé sans motif, toast du détail, fermeture) ; **badgeage en masse** toutes séances (motif obligatoire, `POST …/force-badgeage-étudiants-bulk/`, agrégat `sessions` en toast, fermeture), sur une séance précise (`session_id` transmis), erreur gardée dans la modale. Couvre **51,8 % des lignes / 62,9 % de branches** de la page (les onglets info/étudiants/enseignants, les éditions, la modale QR et les exports feuille restent au backlog). |
| `src/pages/scolarite/campagnesCompletion.test.jsx` | page | **17 tests (LOT 16), complétion des campagnes d'admission**. `Campagnes` : **création en brouillon** (formulaire — sélecteurs année/formation requis, dates, payload avec identifiants numérisés, quotas non exposés → `undefined`, réinitialisation + rechargement), échec serveur (formulaire conservé), **les 4 transitions restantes** du workflow (Suspendre sans confirmation, Clôturer avec confirmation, Réouvrir, Archiver ; annulation = aucun appel), lecture seule DIRECTION (référentiels non chargés). `CampagneDetail` : rendu (compteurs, quota, lignes d'épreuves verrouillées, tableau du classement et ses badges, épreuve verrouillée exclue du sélecteur de note, candidatures des autres campagnes filtrées), **ajout d'épreuve** (POST typé avec/sans salle, valeurs par défaut, reset, erreur JSON conservée), **génération des convocations** (confirm annulée puis acceptée), **verrouillage** (confirm d'irréversibilité, échec notifié), boutons absents sur épreuve verrouillée, **calcul du classement sans confirmation** puis **publication avec confirmation**, campagne clôturée (formulaire d'épreuve masqué) et les deux tests `[écart §10.11]` (saisie de notes/classement encore actifs à clôture ; DIRECTION en lecture seule). Porte `Campagnes.jsx` à **99,4 % de lignes / 100 % de fonctions** et `CampagneDetail.jsx` à **98,8 % / 100 %**. |
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

> **Limite connue (illustrée au LOT 7, §10.8)** : le smoke vérifie l'absence de
> crash, **pas que la page affiche du contenu**. Un composant qui retourne
> `undefined` (ex. `return` avalé par une fonction mal refermée) est valide pour
> React et passe le smoke en rendant une page blanche. Les écrans critiques sont
> donc complétés par des tests dédiés qui affirment la présence d'un titre ou
> d'un contenu caractéristique (ex. `scolariteRendu.test.jsx`).

**Pour ajouter une page** : l'importer et ajouter une ligne à `PAGES`. Si elle
exige des formes de données précises (nombres, clés obligatoires), ajouter une
entrée dans `FIXTURES` plutôt que de modifier l'écran.

---

## 7. Couverture et seuils (qui ne peuvent que monter)

Mesure après le LOT 16 (V8, `npm run test:coverage`), sur les zones ciblées :

| Zone | Lignes | Instructions | Fonctions | Branches |
| --- | --- | --- | --- | --- |
| `src/utils/roles.js` | **100 %** | **100 %** | **100 %** | **100 %** |
| `src/utils/**` (rôles inclus) | 77 % | 77 % | 79 % | 86 % |
| `src/services/**` | **97 %** | **97 %** | 97 % | **91 %** |
| `src/context/**` | **99 %** | **99 %** | 89 % | **91 %** |
| `src/hooks/**` | **94 %** | **94 %** | 84 % | **94 %** |
| `pages/DecisionsPedagogiques.jsx` | **100 %** | 100 % | 100 % | **95 %** |
| `pages/Users.jsx` | **89 %** | 89 % | 49 % | **69 %** |
| `pages/Dashboard.jsx` | **75 %** | 75 % | 43 % | **84 %** |
| `pages/Modules.jsx` | **37 %** | 37 % | 6 % | **59 %** |
| `pages/NotesModule.jsx` (LOT 14) | **98 %** | 98 % | **92 %** | **84 %** |
| `pages/Rattrapages.jsx` (LOT 15) | **97 %** | 97 % | **77 %** | **86 %** |
| `pages/FicheAuditeur.jsx` (LOT 15) | **100 %** | **100 %** | **100 %** | **83 %** |
| `pages/ModuleDetail.jsx` (LOT 16) | **52 %** | 52 % | **33 %** | **63 %** |
| `pages/scolarite/Campagnes.jsx` (LOT 16) | **99 %** | 99 % | **100 %** | **88 %** |
| `pages/scolarite/CampagneDetail.jsx` (LOT 16) | **99 %** | 99 % | **100 %** | **89 %** |
| `pages/Statistiques.jsx` | **28 %** | 28 % | 17 % | **58 %** |
| `pages/scolarite/Candidatures.jsx` | **97 %** | 97 % | 74 % | **79 %** |
| `pages/scolarite/Admissions.jsx` | **98 %** | 98 % | 90 % | **85 %** |
| `pages/scolarite/Inscriptions.jsx` | **99 %** | 99 % | **100 %** | **87 %** |
| `pages/scolarite/FicheEtudiant.jsx` | **90 %** | 90 % | **100 %** | **74 %** |
| `pages/scolarite/Jurys.jsx` (LOT 12) | **100 %** | **100 %** | **100 %** | **88 %** |
| `pages/scolarite/Graduation.jsx` (LOT 12) | **100 %** | **100 %** | **100 %** | **85 %** |
| `pages/scolarite/MonEspace.jsx` (LOT 13) | **74 %** | 74 % | 50 % | **100 %** |
| `pages/scolarite/**` (dossier) | **82 %** | 82 % | **56 %** | **77 %** |
| **Global `src/` (toutes zones)** | **45,3 %** | **45,3 %** | **37,7 %** | **69,7 %** |

> Les LOT 4 à 7 et le LOT 13 sont des correctifs ciblés ; les LOT 8 à 12
> n'ajoutent que des tests.
> Les seuils du LOT 3 restent inchangés (aucun seuil n’a été baissé). Le nombre
> de tests progresse : 464 (LOT 4) → 467 (LOT 5) → 472 (LOT 6) → 477
> (LOT 7) → 483 (LOT 8) → 492 (LOT 9) → 500 (LOT 10) → 510 (LOT 11) →
> 539 (LOT 12) → 542 (LOT 13) → 562 (LOT 14) → 588 (LOT 15) →
> **620 (LOT 16)** ; lignes couvertes globalement 35,3 % (LOT 5) → … →
> 41,6 % (LOT 14) → 43,1 % (LOT 15) → **45,3 % (LOT 16)** (fonctions
> **37,7 %**, branches **69,7 %**).
>
> Le LOT 7 faisait apparaître de la couverture là où les pages étaient
> **invisibles car en panne** (§10.8) ; le LOT 8 y exécutait les actions au
> clic ; les LOT 9 et 10 couvraient la **chaîne admission** (`Candidatures`
> 97,5 %, `Admissions` 98 %) ; le LOT 11 y ajoutait les **inscriptions et la
> fiche étudiant** ; le LOT 12 clôt le **parcours académique jusqu'au diplôme**
> avec `Jurys` et `Graduation`, tous deux à **100 % de lignes / 100 % de
> fonctions** ; le LOT 13 **corrige** l'écart transverse de rechargement qu'il
> avait révélé (§10.10, stabilisation du `ToastContext`) avec 4 régressions,
> et ajoute la première couverture de `MonEspace` (73,6 % de lignes) ; le
> LOT 14 couvre la **saisie des notes d'un module** (`NotesModule`, **97,6 % de
> lignes / 92 % de fonctions**), référencée par les décisions puis le jury ; le
> LOT 15 ouvre le domaine **présence** avec les `Rattrapages` inter-cohortes
> (**97,3 % de lignes** : création, pointage, annulation) et la fiche de suivi
> d'un auditeur `FicheAuditeur` (**100 % de lignes / fonctions**) ; le LOT 16
> attaque l'**émargement en temps réel** au cœur du gros écran `ModuleDetail`
> (onglets Séances + Présences, **51,8 % de lignes / 62,9 % de branches** :
> cycle de vie des séances sous confirmation, pointage forcé unitaire,
> badgeage en masse, cartes de statistiques et habilitations), puis **achève
> la couverture des campagnes d'admission** (`Campagnes` **99,4 %** et
> `CampagneDetail` **98,8 % de lignes, 100 % de fonctions** : création,
> tout le workflow de transitions, épreuves, convocations, verrouillage,
> calcul et publication du classement) ; deux constats produit sont signalés
> en §10.11. Les autres onglets de `ModuleDetail` et son miroir
> `FormationDetail` restent au backlog. Le service `services/scolarite.js`
> reste à **100 % de lignes** et le dossier `pages/scolarite/` progresse à
> **84 % de lignes / 67 % de fonctions / 79 % de branches**.

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
- **« Pas de crash » ne garantit pas « page affichée »** (§10.8). Un composant
  qui retourne `undefined` (ex. `return` avalé par une fonction mal refermée,
  ou un état jamais résolu) monte sans erreur mais rend une page blanche. Les
  tests dédiés doivent retrouver un **contenu caractéristique** (titre,
  colonne, action). Signal d'alarme : un warning `no-unused-vars` sur une
  fonction pourtant appelée dans le JSX = rendu probablement avalé.
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
> tests, le harnais, des fixtures et les seuils. Les LOT 4 à 7 sont les lots
> correctifs (§10.2, §10.4, §10.5, §10.6, §10.7, §10.8). Le seul point encore
> ouvert de cette section est §10.1 (fonctionnalité `must_change_password`, non
> tranchée).

### 10.3 Variables inutilisées (code mort) — soldé au LOT 7, le lint est vierge

Après le LOT 6 (§10.2), il restait **40 avertissements ESLint** : 38
`no-unused-vars` et 2 `no-irregular-whitespace`. Le **LOT 7 les a tous
résolus** ; `npm run lint` ne remonte désormais **plus aucun avertissement ni
erreur**, ce qui rendra immédiatement visible tout nouveau relâchement.

Deux natures distinctes ont été traitées :

- **Vrai code mort / cosmétique, supprimé sans effet comportemental** : imports
  ou constantes jamais référencés (`STAFF_WEB_ROLES`, `DECISION_ROLES`,
  `hasAppRole`, `currentTrimestreParts`, `useLocation`, `formatDate`,
  `nextSessionNumeroForDate`, `STATUTS`, `COULEURS`…), états ou handlers
  réellement détachés (`exportingEncadrants` / `exportFinanceEncadrants` dans
  `Formateurs`, `secretariats`, le composant `Line` et `path`, `filtre_actif`,
  `fmtPct4`, `groupes`, diverses propriétés/arguments non utilisés), et les
  **2 espaces insécables** de `FormationDetail.jsx` remplacés par un
  échappement explicite `\u00A0` (rendu identique autour des guillemets « »).
- **« Variables mortes » qui étaient en réalité le SYMPTÔME d’un bug de
  structure** : les handlers `transition`, `enregistrerNote`, `appliquer`,
  `supprimerEcue` et le chargeur `chargerAnnee` étaient signalés inutilisés
  parce qu’une accolade manquante / un effet absent les rendait injoignables.
  Ce n’était pas du code mort : voir le bug critique **§10.8**.

Leçon pour la suite : un `no-unused-vars` sur une fonction *câblée dans le JSX*
n’est jamais une simple variable à supprimer — c’est souvent l’indice d’un
rendu avalé (accolade manquante) ou d’un effet oublié.

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

### 10.8 BUG CRITIQUE corrigé au LOT 7 — cinq écrans Scolarité en panne (rendu avalé / chargeur non câblé)

Le nettoyage des `no-unused-vars` (§10.3) a révélé que plusieurs « fonctions
mortes » ne l'étaient pas : elles étaient **injoignables** à cause d'une erreur
de structure, et l'écran rendait alors un composant **vide (page blanche) sans
planter** — d'où le fait que le test *smoke* (qui n'exige que « pas de crash »)
restait vert.

**Quatre pages au rendu avalé par une accolade manquante.** Dans `Campagnes`,
`CampagneDetail`, `Equivalences` et `MaquetteDetail`, une fonction de gestion
déclarée juste avant le `return` du composant n'était **pas refermée** (il
manquait le `}` de clôture après le `finally`/`catch` ; une accolade
supplémentaire traînait en fin de fichier). Tout le JSX de la page se retrouvait
donc *à l'intérieur* de cette fonction `async`, qui n'était jamais appelée ; le
composant, lui, n'avait plus de `return` et ne rendait rien. Les gestionnaires
étaient pourtant bien câblés dans ce JSX (6 boutons de transition de campagne,
un `onSubmit` de note, un bouton « Appliquer », un lien « archiver ») :

| Page | Fonction mal refermée | Élément devenu injoignable |
| --- | --- | --- |
| `scolarite/Campagnes.jsx` | `transition(campagne, statut, …)` | tout l'écran (liste + boutons Planifier/Ouvrir/Suspendre/Clôturer/Archiver) |
| `scolarite/CampagneDetail.jsx` | `enregistrerNote(e)` | corps de la fiche (après le spinner initial) et le formulaire de note |
| `scolarite/Equivalences.jsx` | `appliquer(demande)` | tout l'écran (liste + bouton Appliquer) |
| `scolarite/MaquetteDetail.jsx` | `supprimerEcue(ecueId)` | tout l'écran (y compris le spinner de chargement) |

Correctif minimal et purement structurel : refermer chaque fonction au bon
endroit et supprimer l'accolade pendante en fin de fichier (le nombre total
d'accolades reste identique, elles sont simplement à leur place). Le JSX et les
handlers existants redeviennent le `return` du composant.

**Cinquième écran : chargeur jamais appelé.** Dans `ChargesEnseignants.jsx`,
`chargerAnnee()` (GET `/scolarite/annee-courante/`) existait mais n'était lancé
par aucun effet : `annee` restait à `null`, l'effet `[annee, chargerTout]` ne
s'enclenchait pas et l'écran restait inactif (ni occupation, ni anomalies,
création d'affectation bloquée). Le setter n'était appelé que par cette fonction
détachée, d'où le warning. Correctif : restauration du chargeur et effet de
montage `useEffect(() => { chargerAnnee() }, [chargerAnnee])` ; l'effet déjà
présent sur `[annee]` s'enchaîne alors.

**Régressions** dans `src/pages/scolarite/scolariteRendu.test.jsx` (5 tests) :
rendu effectif du titre/libellé de chaque page, et pour `ChargesEnseignants`
appel de l'année courante au montage puis de `/enseignants/occupation/` avec le
bon `annee_id`. Chaque test **échouait avant correction** (preuves de mutation
constatées pour le câblage du chargeur comme pour les pages blanches).

> **Limite du smoke démontrée.** « Monter sans planter » ne garantit pas qu'une
> page *affiche* quelque chose : un composant qui retourne `undefined` est
> valide pour React. Les tests dédiés doivent donc affirmer la présence d'un
> contenu caractéristique (titre, tableau, action), et non seulement l'absence
> d'erreur (voir §6.3 et §9).

**Les actions rétablies sont couvertes au clic au LOT 8**
(`scolariteActions.test.jsx`, 6 tests). Le LOT 7 vérifiait que les pages
*s'affichent* et *chargent* ; le LOT 8 exerce les écritures et confirme chemin,
charge utile, confirmation et message de succès : transitions de campagne
(Planifier sans confirmation, Ouvrir avec `window.confirm`), enregistrement
d'une note, application d'une dispense/équivalence, archivage d'ECUE
(`DELETE ?mode=archive`) et création d'affectation (avec l'année courante). Un
cas de transition **rejetée** couvre aussi la branche d'erreur (toast du
message serveur, sans crash). Couverture des pages : `Campagnes` 61 → **83 %**,
`CampagneDetail` 68 → **82 %**, `ChargesEnseignants` 63 → **73 %** (fonctions
12,5 → 87,5 %), `Equivalences` 51 → **64 %**, `MaquetteDetail` 31 → **68 %**.

### 10.9 Constat au LOT 11 — retrait d'une ECUE pédagogique sans confirmation

Dans `FicheEtudiant.jsx` (section `Pedagogie`), le bouton **Retirer** d'une
ligne pédagogique appelle immédiatement `retirerEcue(ligne.id)`
(`DELETE /scolarite/pedagogie/:id/`) **sans `ConfirmModal`**, alors que les
autres actions destructrices du domaine (archiver une ECUE de *maquette* dans
`MaquetteDetail`, annuler une admission, inscrire un admis) font l'objet d'une
confirmation explicite. Le comportement actuel est figé par un test
(`FicheEtudiant.test.jsx` : clic → DELETE immédiat, aucun `.modal-overlay`) ;
il n'est **pas corrigé** dans ce lot de tests. Décision produit à prendre :
ajouter une `ConfirmModal` de cohérence avec les autres suppressions, ou
assumer un retrait rapide (l'ECUE peut être régénérée depuis la maquette).
À traiter, le cas échéant, dans un lot correctif dédié.

### 10.10 BUG corrigé au LOT 13 — boucle de rechargement sur échec de chargement (valeur de contexte Toast instable)

Constaté au LOT 12 sur `Jurys.jsx` et `Graduation.jsx`, qui mémoïsaient leur
chargeur ainsi :

```js
const toast = useToast()                       // un OBJET { showToast }
const charger = useCallback(async () => {
  /* … */ toast.showToast(message, 'error')    // émis en cas d'échec
}, [toast, filtres])
useEffect(() => { charger() }, [charger])
```

Or `ToastContext.Provider` fournissait `value={{ showToast }}` : la fonction
`showToast` était stable (`useCallback` de deps vide), **mais l'objet `toast`
était recréé à chaque rendu du fournisseur.** Lorsque le chargement initial
échouait, `showToast` faisait évoluer l'état du fournisseur (nouveau toast) →
il se re-rendait → les consommateurs recevaient un nouvel objet `toast` →
`charger` était recréé → l'effet `[charger]` **relançait la requête sans action
de l'utilisateur** ; si l'échec persistait, chaque tentative réémettait un toast
et la chaîne s'**auto-entretenait jusqu'à la limite React** (« Maximum update
depth exceeded ») : spam de toasts et rafale de requêtes, écran inutilisable
quand le backend répondait mal. En cas de succès il n'y avait pas de toast, donc
pas de boucle — c'est pourquoi le smoke (données qui réussissent) restait vert.

Le même patron (`[toast, …]` / `[toast]` sur un chargeur lancé par un effet)
existait dans **cinq autres écrans** : `Campagnes`, `ChargesEnseignants`,
`Equivalences`, `FinancesEtudiantes`, `MonEspace`. Les écrans déjà couverts
(`Inscriptions`, `Admissions`, etc.) échappaient au problème en dépendant de la
fonction stable (`useCallback(…, [filtres, showToast])`).

**Correctif (LOT 13, feu vert explicite), une seule ligne de logique partagée
au niveau du fournisseur.** Dans `src/context/ToastContext.jsx`, la valeur est
désormais mémoïsée :

```js
const value = useMemo(() => ({ showToast }), [showToast])
// …
<ToastContext.Provider value={value}>
```

La référence de l'objet de contexte ne change donc plus quand un toast apparaît
ou disparaît (l'état interne `toasts` change, mais pas la valeur exposée) : tous
les écrans qui dépendaient de `toast` — les sept cités — sont stabilisés
**sans modification de leur code**, et l'API publique du contexte est
inchangée.

**Régressions (toutes en échec avant le correctif — preuve de mutation
constatée)** :

- un test de **stabilité de référence du contexte** dans
  `context/ToastContext.test.jsx` : la valeur reçue par un consommateur reste
  identique à l'apparition *et* à la disparition d'un toast ;
- `Jurys.test.jsx` et `Graduation.test.jsx` : un échec du chargement initial
  (deux échecs programmés puis un succès) ne produit **qu'une seule requête et
  qu'un seul toast**, puis l'état vide — au lieu de ≥3 requêtes et de plusieurs
  toasts ;
- `MonEspace.test.jsx` (nouveau, 2 tests) : couvre le **second patron** (chargeur
  lancé par un `useEffect([toast])` direct, sans `useCallback`) — rendu nominal de
  la fiche, puis une seule requête/un seul toast quand `/scan/me/fiche/`
  échoue.

Les quatre autres écrans au même patron bénéficient du correctif central ; la
régression de référence au niveau du contexte garantit qu'aucun consommateur ne
peut plus rejouer un effet du fait d'un toast.

### 10.11 Constats du LOT 16 — campagnes d'admission (deux incohérences mineures, figées par des tests)

Les tests de complétion du flux admission (`campagnesCompletion.test.jsx`)
ont mis en évidence deux écarts de cohérence, non corrigés dans ce lot de
tests purs :

1. **Quotas non saisissables à la création.** Le formulaire *Nouvelle campagne*
   de `Campagnes.jsx` ne comporte aucun champ `quota_admissibles` /
   `quota_admis`, alors que le gestionnaire `creer` les transmet au backend
   (ils partent donc toujours en `undefined`) et que `CampagneDetail.jsx`
   affiche le « quota admissibles » d'une campagne. Selon les besoins produit,
   il faudrait soit ajouter deux champs au formulaire, soit retirer ces clés
   du payload. Le test fige l'état observé (`quota_admissibles` et
   `quota_admis` `undefined`).
2. **Saisie de notes et actions de classement encore actives sur campagne
   fermée.** Dans `CampagneDetail.jsx`, une campagne `CLOTUREE` / `ANNULEE` /
   `ARCHIVEE` masque bien le formulaire d'ajout d'épreuve ainsi que les
   boutons *Convocations* / *Verrouiller* des épreuves, mais la carte
   *Saisie des notes* et les boutons *Calculer le classement* / *Publier les
   listes* restent rendus et actionnables. Un test `[écart]` fige ce
   comportement. Décision produit : désactiver ces actions sur campagne
   fermée (cohérence avec les autres garde-fous), ou les assumer (correction
   d'une note après clôture).

À traiter, le cas échéant, dans un lot correctif dédié, sur feu vert.

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

**Aucune page n'est dépourvue de test.** État après le LOT 16 :

- dix écrans disposent d'un test **fonctionnel dédié** hors module Scolarité :
  `Login.jsx`, `DecisionsPedagogiques.jsx` (100 % de lignes), `Users.jsx`
  (89 %, liste serveur + CRUD), `Dashboard.jsx` (75 %), `Modules.jsx` (37 %,
  nettoyage des filtres obsolètes), `Statistiques.jsx` (28 %, contrat
  d'isolation par secrétariat + synchro des justificatifs §10.7),
  `NotesModule.jsx` (**97,6 % de lignes**, LOT 14 — grille de saisie, bulk,
  colonnes, fiches PDF), `Rattrapages.jsx` (**97,3 % de lignes**, LOT 15 —
  création inter-cohortes, génération de pointage, annulation),
  `FicheAuditeur.jsx` (**100 % de lignes/fonctions**, LOT 15 — fiche de suivi
  et exports) et `ModuleDetail.jsx` (**51,8 % de lignes / 62,9 % de branches**,
  LOT 16 — émargement : onglets Séances et Présences) ;
- cinq écrans Scolarité (`Campagnes`, `CampagneDetail`, `Equivalences`,
  `MaquetteDetail`, `ChargesEnseignants`) ont un **test de rendu dédié**
  (`scolariteRendu.test.jsx`, §10.8) qui affirme un contenu caractéristique et
  le chargement effectif — allant au-delà du smoke qui n'exclut pas les pages
  blanches ; leurs **actions d'écriture sont en outre exercées au clic** au
  LOT 8 (`scolariteActions.test.jsx`, §10.8), et les deux écrans *Campagnes*
  sont **quasi exhaustivement couverts au LOT 16**
  (`campagnesCompletion.test.jsx`, **99 % de lignes / 100 % de fonctions**) ;
- tout le **parcours administratif de l'étudiant** est couvert par des tests
  fonctionnels dédiés : `Candidatures.jsx` (97,5 % ln, LOT 9), `Admissions.jsx`
  (98 % ln, LOT 10), puis `Inscriptions.jsx` (99,4 % ln / 100 % fonctions,
  LOT 11 — validation en cascade) et `FicheEtudiant.jsx` (89,8 % ln / 100 %
  fonctions, LOT 11 — pédagogie, groupes, passerelle) ;
- la **fin du parcours académique jusqu'au diplôme** l'est aussi (LOT 12) :
  `Jurys.jsx` (100 % ln / 100 % fonctions — workflow de délibération exercé
  pour chaque statut) et `Graduation.jsx` (100 % ln / 100 % fonctions —
  validation/gel du PDF, révocation motivée, portail public de vérification) ;
- au LOT 13, `MonEspace.jsx` (espace étudiant) gagne un **test dédié** qui
  couvre aussi le second patron du bug §10.10 (chargeur direct dans un
  `useEffect([toast])`) ;
- au LOT 14, la **saisie des notes** (`NotesModule.jsx`, 20 tests) est couverte
  en profondeur : c'est le chaînon qui alimente les décisions pédagogiques puis
  la délibération du jury (calcul normalisé /20, mentions, moyennes, seuils
  d'admission, enregistrement en bloc, colonnes dynamiques, fiches PDF) ;
- au LOT 15, le domaine **présence** est entamé : les `Rattrapages`
  inter-cohortes (`Rattrapages.jsx`, 18 tests — recherche d'étudiant,
  sélection multiple de séances ou d'un module entier, verrouillage des
  inscriptions déjà faites, génération de pointage, annulation avec/sans
  pointage, habilitations) et la fiche de suivi d'un auditeur
  (`FicheAuditeur.jsx`, 8 tests, exports PDF/Excel) ;
- au LOT 16, l'**émargement en temps réel** du gros écran `ModuleDetail.jsx`
  (15 tests) est couvert sur ses deux onglets cœur, **Séances** (démarrer /
  terminer / supprimer / créer, chaque écriture destructrice passant par la
  `ConfirmModal` globale, toasts et rechargement) et **Présences** (les cinq
  cartes de statistiques calculées à partir des pointages du jour et de la
  liste des attendus, forçage de pointage **unitaire** et **badgeage en masse**
  80–95 % avec motif obligatoire, filtres date/séance, trois niveaux
  d'habilitation ENCADRANT / secrétariat / DIRECTION) ;
- le même lot **achève la couverture fonctionnelle des campagnes
  d'admission** (`campagnesCompletion.test.jsx`, 17 tests) : création en
  brouillon, les quatre transitions de statut non couvertes par le LOT 8
  (suspendre/clôturer/réouvrir/archiver, avec et sans confirmation), ajout
  d'épreuve (typage, salles, échec JSON), convocations, verrouillage, calcul
  et publication du classement, états « campagne fermée » et lecture seule ;
  deux constats de cohérence sont figés en §10.11 ;
- le **moteur de tableaux/listes génériques** est couvert indépendamment des
  écrans : construction des requêtes/filtres (`listFilters`), pagination
  (`paginationPages`, `paginatedResponse`), formatage des erreurs (`apiErrors`),
  et les hooks associés (`useClientPagination`, `usePickerPagination`,
  `useListReturn`, `usePersistedListQuery`) ;
- composants réutilisables testés : `Pagination`, `ConfirmModal` ; les autres
  composants ne sont exercés qu'indirectement via le smoke ;
- les **31 autres pages** sont couvertes en *smoke* (rendu) mais pas encore en
  *comportement métier* bout-en-bout.

Backlog proposé pour les lots suivants (ordre de valeur) :

1. ~~Moteur de listes + décision pédagogique~~ (LOT 1), ~~liste *serveur*
   typée~~ (LOT 2, `Users`), ~~isolation secrétariat Stats + période Dashboard~~
   (LOT 3). Restes ponctuels connus : branche `Users` « création d'un secrétariat
   à la volée », onglets/exports/widgets internes de `Statistiques`. Les bugs
   §10.4, §10.5 et §10.6 ont été **corrigés aux LOT 4 et 5**, avec régressions ;
   le **LOT 6** a soldé tous les `exhaustive-deps` (§10.2) et corrigé §10.7,
   avec un test dédié `Modules` et deux régressions supplémentaires ; le
   **LOT 7** a rendu le lint **vierge** (§10.3) et réparé **5 écrans Scolarité
   en panne** (§10.8) ;
2. ~~Compléter les écrans Scolarité réparés (§10.8) par des tests au clic~~
   **fait au LOT 8** (`scolariteActions.test.jsx`) : transition de campagne
   (avec/sans confirmation + erreur), note, application d'équivalence,
   archivage d'ECUE, création d'affectation ; **puis au LOT 16**
   (`campagnesCompletion.test.jsx`) : création de campagne, toutes les
   transitions, ajout d'épreuve, convocations, verrouillage, calcul et
   publication du classement. Restent les actions secondaires de ces écrans :
   la modale « Décider » et les autres transitions (`Equivalences`), le
   workflow maquette (valider/activer/archiver/cloner) et l'ajout d'ECUE
   (`MaquetteDetail`), le détail enseignant et la sélection dans
   `ChargesEnseignants` ;
3. flux critiques par rôle : ~~candidatures~~ (LOT 9), ~~admissions/décisions~~
   (LOT 10), ~~inscriptions / pédagogie / groupes / passerelle~~ **(LOT 11)**,
   ~~jurys / diplômation / vérification publique~~ **(LOT 12)** et ~~saisie des
   notes d'un module~~ **(LOT 14, `NotesModule`)** couverts, et les
   ~~rattrapages inter-cohortes + fiche de suivi auditeur~~ **(LOT 15)** : le
   parcours étudiant, de la candidature à la délibération du jury (alimentée
   par les notes) jusqu'à la **délivrance du diplôme et sa vérification par un
   tiers**, est défendu de bout en bout, et la **gestion des rattrapages de
   présence** est couverte. La **réinscription** et la **création
   d'événements** n'ont à ce jour **pas d'écran dédié** (les fonctions
   `reinscrire` / `createEvenement` du service existent et sont déjà couvertes
   à 100 % dans `services/scolarite.test.js`) ; elles ne relèvent donc pas
   encore d'un test de page. Restent, dans le domaine présence qui écrit,
   **l'émargement/QR en temps réel** (les gros `ModuleDetail` et
   `FormationDetail` : démarrage/fin de séance, `force-pointage`, badgeage en
   masse, modale QR, exports de feuille) et le **CRUD des participants**
   (`Participants`), puis les **finances étudiantes**, les **référentiels**, et
   les gros volumes internes `Statistiques` et `Users` (création de secrétariat
   à la volée) ;
4. écarts encore ouverts, dans des lots dédiés :
   - §10.1 `must_change_password` (**fonctionnalité** : parcours forcé, nouvelle
     route protégée, gestion au login et après `refreshUser`) — en attente d'un
     choix produit (blocage total ou lecture seule) ;
   - §10.9 retrait d'une ECUE pédagogique sans confirmation (cohérence UX avec
     les autres actions destructrices) — comportement figé par un test, en
     attente d'un choix produit ;
   - ~~§10.10 boucle de rechargement sur échec de chargement (valeur de contexte
     Toast non mémoïsée)~~ **corrigé au LOT 13** (mémoïsation de la valeur du
     `ToastContext.Provider`, 4 régressions) — ne reste ouvert qu'au titre d'un
     choix produit éventuel sur la *forme* du retour d'erreur de chargement
     (toast transversale vs état d'erreur dédié dans la page) ;
   - §10.11 deux constats mineurs sur les campagnes (LOT 16) : quotas
     `quota_admissibles`/`quota_admis` non saisissables à la création alors
     qu'affichés au détail, et saisie de notes / calcul-publication du
     classement encore actives sur une campagne clôturée/annulée/archivée —
     les deux sont figés par des tests, en attente d'un choix produit ;
5. composants partagés (modales, pickers, badges, panneaux de flux) ;
6. montée progressive du plancher de couverture global (§7) et extension aux
   pages encore couvertes seulement en smoke ; option : durcir le smoke
   (§6.3/§10.8) pour exiger un contenu minimal et non plus seulement « pas de
   crash ».
