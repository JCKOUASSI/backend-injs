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
> publication du classement, campagne fermée et lecture seule ; les deux
> constats produit alors relevés en §10.11 y étaient figés), puis au
> **[LOT 17]** (**lot correctif** sur feu vert explicite : les deux constats
> §10.11 sont traités — champs **quota** à la création de campagne (valeurs
> numérisées dans le payload), et **masquage de la saisie de notes et des
> actions de classement sur campagne fermée** ; les tests `[écart]` deviennent
> des tests de régression), puis au **[LOT 18]** (approfondissement du gros
> écran `ModuleDetail` : inscription/retrait des étudiants, assignation/retrait
> des enseignants, édition du module, assignation du superviseur, exports
> PDF/Excel de séance et du module ; un **bug bloquant §10.12** y était
> révélé — la modale d'assignation d'un enseignant plantait dès qu'une ligne
> s'affichait), puis au **[LOT 19]** (**lot correctif** sur feu vert explicite :
> le bug §10.12 est réparé par l'alignement du nom de prop (`formateur`), et le
> test `[écart]` devient un parcours d'assignation bout-en-bout avec ses cas
> de conflit d'emploi du temps), puis au **[LOT 20]** (lot de tests purs :
> achèvement de `ModuleDetail` — la **modale QR des séances** est exercée
> (chargement, génération, régénération confirmée, téléchargement PNG,
> garde-fou inter-module, erreurs), l'**archivage à trois confirmations**
> `TripleConfirmModal` est couvert de bout en bout (POST, annulation,
> erreur, habilitations), ainsi que la **pagination serveur** des pickers
> enseignants/étudiants), puis au **[LOT 21]** (écran miroir
> `FormationDetail`, niveau formation : chargement/en-tête/onglets,
> regroupement des séances par module et tout le cycle de vie des séances,
> étudiants et enseignants avec pickers, assignation de l'encadrant,
> habilitations — 25 tests, 63 % de lignes ; le global `src/` franchit 50 %),
> puis au **[LOT 22]** (achèvement de cette fiche, portée à **98,4 % de
> lignes / 63 tests** : onglet Présences en temps réel — dashboard, sélecteur
> de séance, recherche côté client, libellés multi-séances et badge
> rattrapage, forçage de pointage unitaire aujourd'hui et un jour passé avec
> timestamps, habilitations et états d'erreur ; exports formation/séance ;
> intégration QR de séance ; archivage `TripleConfirmModal` depuis les
> groupes ; import Excel réservé au SECRETARIAT ; pagination serveur des
> pickers ; états vides et filets d'erreur), puis au **[LOT 23]** (le **CRUD
> des participants** `Participants.jsx` est couvert à **100 % de lignes / 100 %
> de fonctions / 35 tests** : liste serveur paginée avec recherche debounce et
> six filtres, création/édition avec référentiels liés catégorie→grade et
> site→salle, suppressions confirmées, fenêtre de détail fiche-admin vs
> formations selon le rôle, exports liste de classe PDF/Excel et
> habilitations création/gestion/export), puis aux **[LOT 24] et [LOT 25]**
> (la fenêtre `ParticipantDetailModal`, 1 134 lignes, est couverte à
> **98,8 % de lignes / 100 % de fonctions / 50 tests** : le LOT 24 défend
> la lecture — navigation des cinq onglets, statistiques et états vides,
> identité formatée, modules avec heures/taux/statuts et déploiement des
> séances (`GET …/full/`, cache, échec silencieux, propagation arrêtée),
> notes et **moteur de décision** ADMIS/AJOURNÉ/EXCLUSION/EN_ATTENTE avec
> priorité à la décision backend et mention de validation manuelle,
> chargement paresseux de la fiche de notes et ses erreurs, séances triées
> et détails techniques de badgeage ; le LOT 25 défend les **écritures** —
> saisie de moyenne `bulk` (payload notes/synthèses, garde 0–20, tableaux
> vides, colonne absente, réponses partielles et erreurs, recalcul en
> cascade avalé en cas d'échec, module sans formation), recalcul manuel de
> décision et exports relevé PDF/Excel avec leurs filets d'erreur ; le
> résidu est du code défensif inatteignable par l'UI), puis au **[LOT 26]**
> (le domaine **finance étudiante** `scolarite/FinancesEtudiantes` est
> verrouillé à **100 % de lignes / 100 % de fonctions / 25 tests** :
> échéanciers et paiements, création de paiement **idempotente** via
> `transaction_externe`, confirmation sous `window.confirm` avec preuve
> exigée, navigation par onglets, badges de statut et leurs replis, états
> de chargement/vide/erreur, bouton Actualiser et la matrice d'habilitation
> FINANCE/DIRECTION/admin (écriture + confirmation), SECRÉTARIAT (saisie
> seule) et lecture stricte), puis au **[LOT 27]** (le **rapport des
> encadrants** `FinanceEncadrants` est couvert à **100 % de lignes /
> 100 % de fonctions / 100 % de branches / 19 tests** : KPI et tableaux par
> encadrant/groupe avec les replis défensifs, période partagée mois/
> trimestre/année/personnalisé appliquée via le shell commun, exports PDF/
> Excel reportant la période, période dégradée sans preset, nom de fichier
> par défaut et filets d'erreur), puis au **[LOT 28]** (l'écran de
> **paramétrage finance** `FinanceParametrage` est verrouillé à **100 % de
> lignes / 100 % de fonctions / 100 % de branches / 26 tests** : tarifs
> horaires par formation (actifs puis inactifs, valeur appliquée formatée,
> tarif non défini), marge de tolérance et douze champs de personnalisation
> des exports, PATCH complet avec validation des tarifs négatifs et
> séparateur virgule, répercussion de la réponse (y compris réponses sparse
> ou `data:null`), état « Enregistrement… », méta-audit avec ses replis,
> matrice FINANCE/lecture seule et période partagée via le shell), puis au
> **[LOT 29]** (les **ajustements horaires** `FinanceAjustements` sont
> verrouillés à **100 % de lignes / 100 % de fonctions / 98,7 % de branches
> / 35 tests** : KPI et filtres de statut côté client, lignes détaillées
> (delta positif/négatif, avant→après, badges de statut et leur repli
> neutre, valideur/motif de rejet), workflow **valider / rejeter** avec
> modale de motif obligatoire et états d'action, proposition d'ajustement
> avec recherche d'enseignant **débordancée à 300 ms** et séances issues du
> rapport finance (tri, filtrage, sélecteur verrouillé), payload exact,
> compteur d'attente reporté sur la navigation, réponses et pickers
> dégradés ; les 2 branches non couvertes sont des double-protections
> inatteignables par l'UI), puis au **[LOT 30]** (le **tableau de bord
> finance** `FinanceDashboard` est verrouillé à **99,8 % de lignes /
> 100 % de fonctions / 97,2 % de branches / 29 tests** : cinq KPI héro
> cliquables avec sous-textes et badges d'évolution (hausse/baisse/plat,
> durée/argent/points), KPI d'effectifs, alerte de tolérance et info
> tarifs, repli du coût prévisionnel par somme des modules, activité
> mensuelle, forage des spécialités et ventilation modale par module
> (cinq mesures, recherche, totaux), classement trois mesures avec
> médailles, synthèse de paie paginée à 25 et badges de tolérance,
> période partagée et `rank_tab` persistant ; les 5 branches non
> couvertes sont des aiguillages de formatage défensifs figés par les
> tables de configuration statiques, donc inatteignables par l'UI — le
> **module Finance transverse est ainsi entièrement couvert**), puis au
> **[LOT 31]** (l'écran **équivalences/dispenses** `Equivalences` est
> verrouillé à **100 % de lignes / 100 % de fonctions / 100 % de branches /
> 27 tests** : chargement et `Promise.all` des quatre référentiels sous
> habilitation, table des badges de statut et des crédits, création en
> brouillon avec identifiants typés (`Number(x) || undefined`), tout le
> workflow des transitions par statut, la modale de décision pédagogique et
> l'application après confirmation `window.confirm`, avec chaque chemin
> d'erreur et la lecture seule des rôles non acteurs), puis au **[LOT 32]**
> (l'écran **détail de maquette pédagogique** `MaquetteDetail` est
> verrouillé à **100 % de lignes / 100 % de fonctions / 100 % de branches /
> 35 tests** : consultation groupée par semestre et journal des validations,
> workflow valider / activer / archiver sous confirmation avec remontée des
> `problemes` de cohérence, clonage versionné avec redirection, ajout d'UE et
> d'ECUE typés, archivage d'ECUE et habilitations), puis au **[LOT 33]**
> (l'écran **charges pédagogiques des enseignants** `ChargesEnseignants` est
> verrouillé à **100 % de lignes / 100 % de fonctions / 96,9 % de branches (après le correctif du LOT 34) /
> 23 tests** : année courante au montage puis occupation et anomalies en
> parallèle, détail d'enseignant (charge + affectations), création
> d'affectation typée, cinq référentiels et carte de création sous
> habilitation ; deux tests `[écart]` y signalent le **crash §10.13** de la
> carte quand les référentiels échouent ou répondent trop lentement — état
> initial `options` incomplet — crash alors corrigé dès le **[LOT 34]** par
> un état initial complet, les deux tests `[écart]` devenant des régressions).
> Ce lot **solde les cinq écrans Scolarité réparés au §10.8**, puis le
> **[LOT 35]** ouvre l'administration transverse : l'écran **référentiels de
> formation** `Referentiels` (neuf onglets chargés en un seul GET) est
> verrouillé à **99,7 % de lignes / 100 % de fonctions / 95,2 % de branches /
> 56 tests** : CRUD des neuf collections (dont les modules multi-formations
> avec grille de volumes horaires formation × catégorie et les salles/bâtiments
> hiérarchiques), activation/désactivation, suppression confirmée avec 404
> dédoublonné, import/export Excel, pagination client et persistance de
> l'onglet dans l'URL ; les branches résiduelles sont des filets défensifs
> bornés par la lecture d'onglet.
> Les LOT 4 à 7, 13, 17, 19 et 34 sont les lots qui touchent la logique
> applicative, sur feu vert explicite ; les LOT 8 à 12, 14, 16, 18, 20, 21,
> 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33 et 35 sont des lots de tests purs.
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

### 6.2 Fichiers de test colocalisés (49 fichiers, 1078 tests)

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
| `src/pages/Referentiels.test.jsx` | page | **56 tests (LOT 35), référentiels de formation — 99,7 % lignes/instructions, 100 % fonctions, 95,2 % branches** (les branches résiduelles sont des filets défensifs inatteignables : onglet borné par `readReferentielsTab`, états `data`/`formation_ids` toujours initialisés). Les **neuf onglets** (formations, modules, catégories, grades, vagues, sites, bâtiments, salles, types secrétariat) sont chargés en un seul `GET /formations/referentiels/gestion/` : spinner, compteurs par onglet, colonnes spécifiques avec résolution des liens (catégorie de grade, site/bâtiment des salles et bâtiments, replis « — » dont les clés mortes), résumé des volumes de modules groupé par formation (`F (CM: 5h, TD: 4h)`, repli `Formation #id`, total simple `12 h`, vide « — »), état vide « Aucune entrée — cliquez sur Ajouter », réponse sparse (clés absentes → tableaux vides sans crash), erreur « Erreur de chargement », **pagination client 25/page** et **onglet lu dans `?tab=`** (inconnu → Formations), changement d'onglet qui referme la modale. **CRUD** : création par onglet (POST, payloads et valeurs par défaut — formations/catégories/sites/types/vagues/grades), édition (PUT, pré-remplissage, toasts « Ajouté/Modifié avec succès », rechargement + invalidation du cache React Query), bouton « Enregistrement… » pendant l'envoi, erreurs de validation formatées puis message générique, fermetures croix/Annuler/voile sans appel ; **bascule actif/inactif** (PUT du corps complet, toasts Activé/Désactivé, échec « Erreur »). **Suppressions** via `ConfirmModal` (annulation sans DELETE, succès « Supprimé », **404 → « Entrée déjà supprimée — liste actualisée »**, autre erreur générique). **Clés typées** : grades/bâtiments/salles (identifiants `Number()` ou `null`, capacité non numérique neutralisée — y compris une valeur véreuse servie par le backend en édition, bâtiments filtrés par site, changement de site qui réinitialise le bâtiment, défauts `type_lieu:'SALLE'`/`equipements:''`). **Modules** : cases des formations actives seules, garde « au moins une formation » puis « au moins un volume horaire », grille de volumes par formation × catégorie active (valeurs vides/`NaN` écartées, décochage, cases/grille réinitialisées), payload `volumes_horaires` reconstruit (clés de grille et `formations` retirées), POST **201 → ajout** vs **200 → « Module déjà au référentiel — formations rattachées »**, édition avec grille pré-remplie (volume sans formation écarté, ancien format `volumes_par_categorie`, formation morte en `Formation #id`). **Excel** : export `getBlob /formations/ref/excel/{onglet}/` (ancre cliquée, nom serveur ou nom par défaut `referentiel_{onglet}.xlsx`, révocation d'URL, échec notifié), import via l'input caché (clic programmé, extension non `.xlsx` refusée, sélection annulée sans effet, POST `FormData` avec bilan `N ligne(s)…`, réponse sans données → zéros, deux niveaux d'erreur). |
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
| `src/pages/scolarite/Equivalences.test.jsx` | page | **27 tests (LOT 31), équivalences/dispenses — 100 % lignes/fonctions/branches/instructions**. `GET /equivalences/demandes/` au montage : spinner, tableau (neuf statuts dont un inconnu en repli, crédits `?? '—'` y compris `0`), message « Aucune demande. », erreur détaillée puis « Chargement impossible. ». **Habilitations** : pour un rôle acteur (`canActScolarite`), les quatre référentiels sont chargés en `Promise.all` (`/scolarite/ref/annees/?actif=true`, `…/formations/`, `…/niveaux/?actif=true`, `…/etudiants/`) ; la liste des rôles non acteurs (DIRECTION, ENCADRANT, FINANCE) ne les requête pas et ne montre ni carte de création ni boutons d'action ; l'échec des référentiels toasté (« Chargement des référentiels impossible. ») sans masquer la liste. **Badges de statut** : les neuf apparences (`BADGE_STATUT`) dont APPLIQUÉE en `dark` et le repli `secondary`. **Création** `POST /equivalences/demandes/` : payload exact avec IDs `Number(x) || undefined` (soumission sans sélection exercée via `fireEvent.submit`), toast « Demande créée en brouillon. » et rechargement, bouton « + » désactivé pendant l'envoi (promesse différée), erreur `JSON.stringify` du détail serveur puis « Création impossible. ». **Transitions** `POST …/:id/transition/` `{statut}` : les cinq boutons du workflow (Soumettre, Instruire, Avis pédagogique, Décider), absence de bouton sur REJETÉE/APPLIQUÉE/statut inconnu, désactivation globale pendant une action, toasts `Demande {statut}.` (rechargement) et « Transition impossible. ». **Décision** : ouverture de la carte inline (titre `Décision — demande #N`, Annuler/Enregistrer), payload `POST …/:id/decision/` avec défauts `FAVORABLE` / « Direction des études INJS », champs crédits/note vides → `undefined`, fermeture après succès, rechargement, cas d'erreur qui laisse la carte ouverte. **Application** `POST …/:id/appliquer/` `{}` après `window.confirm(/effet académique/i)` : annulation sans appel, succès (« Dispense/équivalence appliquée. », rechargement), échec (« Application impossible. »). Aucune alerte `act` (mûrissement du rechargement après chaque écriture). |
| `src/pages/scolarite/MaquetteDetail.test.jsx` | page | **35 tests (LOT 32), détail de maquette pédagogique — 100 % lignes/fonctions/branches/instructions**. Chargement en parallèle `GET /scolarite/maquettes/:id/` + `…/journal/` : spinner puis en-tête (titre `libelle` avec repli `ref_formation`, niveau · année · version · badge statut · crédits et volume, lien Retour), regroupement des **UE par semestre** (deux UE d'un même semestre dans une seule carte), rendu UE (code/intitulé/crédits/caractère) et ECUE (crédits, coefficient, volume), badge « archivée » sans action pour une ECUE archivée, alerte des **problèmes de cohérence** (absente sinon), journal des validations (action, utilisateur avec tiret de repli, date `fr-FR`, état « Aucune entrée. »), erreur de chargement détaillée puis « Chargement impossible. » avec écran en spinner. **Habilitations** : contrôles de rédaction (groupe workflow, formulaires UE/ECUE, archivage) et `GET /scolarite/ref/semestres/` réservés aux rôles `canActScolarite` (SECRETARIAT inclus ; ENCADRANT/DIRECTION en lecture stricte) et au statut BROUILLON ; le référentiel des semestres n'est plus demandé en VALIDEE/ACTIVE/ARCHIVEE et son échec est avalé en silence (select avec la seule option fantôme). **Boutons par statut** : Valider (BROUILLON), Activer (VALIDEE), Archiver (ACTIVE), Cloner (tout sauf brouillon). **Workflow** : confirmations exactes (« contenu gelé », « immuable », « Archiver cette maquette ? ») — annulation sans appel puis acceptation, `POST …/{valider|activer|archiver}/` `{}`, toast « Opération effectuée. », maquette rechargée avec nouveaux boutons et formulaires retirés, groupe désactivé pendant l'appel (promesse différée), trois niveaux d'erreur (`problemes` concaténés, détail `error`, « Action impossible. ») sans rechargement. **Clonage** `POST …/cloner/` : annulation sans navigation, toast versionné `Version v{n} créée en brouillon.`, redirection `window.location.href` vers la nouvelle maquette, échecs détaillé/générique (« Clonage impossible. »). **Ajout d'UE** `POST …/ues/` : select alimenté par les semestres, payload typé `{semestre_id: Number, code, intitule, credits: Number||0}` (crédits non numériques → 0 par soumission directe), bouton Ajouter désactivé pendant l'envoi, réinitialisation du formulaire et rechargement, échecs détaillé/générique avec formulaire conservé. **Ajout d'ECUE** `POST …/ues/:id/ecues/` : formulaire propre à chaque UE (le `focus` fixe l'UE rattachée, la saisie reste invisible dans le formulaire de l'autre UE), payload `{code, intitule, credits typés, coefficient: 1}` sans `ue_id` dans le corps, réinitialisation, crédits invalides → 0, deux niveaux d'erreur. **Archivage d'ECUE** `DELETE /scolarite/ecues/:id/?mode=archive` : confirmation exacte, annulation sans appel, succès (« ECUE archivée. », rechargement), échecs détaillé/générique (« Suppression impossible. »). |
| `src/pages/scolarite/ChargesEnseignants.test.jsx` | page | **23 tests (LOT 33), charges pédagogiques des enseignants — 100 % lignes/fonctions, 96,9 % branches** (les 2 branches résiduelles sont des filets défensifs inatteignables par l'UI : la carte n'est rendue qu'une fois l'année résolue et le clic de ligne fournit toujours un identifiant réel). **Année courante** `GET /scolarite/annee-courante/` au montage (§10.8), puis **occupation + anomalies en `Promise.all`** avec `{params:{annee_id}}` : spinner puis titre et libellé d'année, les six colonnes d'occupation avec badges OK (`text-bg-success`) / Surcharge (`text-bg-danger`), état vide « Aucune affectation. », alerte d'anomalies (compteur `N anomalie(s) détectée(s)`, détails `a.detail`, **tronquée aux 8 premières**), absence d'alerte sinon, réponses sans clés `occupation`/`anomalies` repliées sur `[]`. **Absence d'année** : toast « Aucune année académique courante. », aucun chargement d'occupation (écran en attente — comportement figé) ; **échec occupation ou anomalies** : toast « Chargement des charges impossible. » mais `finally` qui rend la page et son état vide. **Détail enseignant** (clic de ligne, ligne mise en `table-active`) : `GET /enseignants/charges/:id/` puis `…/affectations/?enseignant_id=&annee_academique_id=`, carte « Détail — {enseignant} » (heures prévue/affectée/planifiée/réalisée, table ECUE/type/volume/statut, ECUE absente → tiret), changement d'enseignant, échec « Chargement de la charge impossible. » sans carte ; le détail reste ouvert aux rôles non acteurs. **Référentiels** : cinq GET pour un rôle acteur (`annees` et `niveaux` avec `actif:'true'`, `formations`, `semestres`, `formateurs/list/`) alimentant les sélecteurs (nom/prénom, intitulé, code), **semestres filtrés par niveau** (`niveau_id`, option fantôme seule avant choix du niveau), aucun GET pour un rôle non acteur (ENCADRANT) dont la carte de création est absente. **Deux régressions §10.13 (corrigé au LOT 34)** : l'échec des référentiels affiche le toast SANS crasher (occupation conservée, sélecteurs réduits à leur option fantôme) et des référentiels lents servis après l'occupation laissent l'écran stable ; ces deux tests figuraient `[écart]` au LOT 33 (la carte crashait sur `options.formateurs.map` avec un état `options` incomplet). **Création** `POST /enseignants/affectations/` : payload typé complet (`type_enseignement:'CM'` par défaut, `ecue_id`/`groupe_id` chaînes vides, IDs `Number(x) || undefined`, `volume_horaire: Number||0`, `annee_academique_id` repris de l'année courante), libellé du bouton portant l'année, soumission directe sans sélection (IDs `undefined`, volume invalide → 0), bouton verrouillé pendant l'envoi (promesse différée), **réinitialisation partielle** (enseignant et volume vidés, formation/niveau/semestre conservés), rechargement global (occupation + anomalies) ET du détail si un enseignant était sélectionné, erreur `JSON.stringify` du détail puis « Création impossible. ». |
| `src/pages/scolarite/FinancesEtudiantes.test.jsx` | page | **25 tests (LOT 26), finance étudiante — 100 % de lignes / 100 % de fonctions / 97 % de branches**. Chargement parallèle `GET /finances-etudiantes/echeanciers/` et `…/paiements/` (normalisation `results || data` sur les deux formes), titre/onglets/bouton Actualiser (qui recharge les deux ressources), spinner initial puis lignes. **Onglet Échéanciers** : étudiant/année/`lignes_count`, badges de statut global (`IMPAYE` danger, `PARTIELLEMENT_PAYE` warning, `COMPLETE` success, statut inconnu → repli secondaire), état vide, navigation entre onglets et retour. **Onglet Paiements** : neuf colonnes (dont Action sous habilitation), identité Étudiant/Candidat/tiret, montant + devise, mode, référence ou tiret, table de badges complète (`INITIE`…`RAPPROCHE`), bouton **Confirmer uniquement pour INITIE/EN_ATTENTE**, état vide et spinner d'onglet. **Création** `POST …/paiements/` : payload exact `{etudiant_id, nature, montant, devise (texte libre), mode, transaction_externe}` (nature/mode sur les listes fermées), message d'idempotence, réinitialisation du formulaire (les `<input type=number>` vides valent `null` en jest-dom), rechargement, erreur serveur détaillée puis message générique. **Confirmation** `POST …/paiements/:id/confirmer/` : `window.confirm` (libellé contenant id/montant/devise, annulation = aucun appel), succès avec toast de quittance et rechargement, échec détaillé (preuve manquante) puis générique. **Habilitations** : FINANCE/DIRECTION/CHEF_CPFAE_ADMIN/CPFAE_ADMIN (saisie + colonne Action), SECRETARIAT/CHEF_SECRETARIAT (saisie mais pas de confirmation), ENCADRANT (lecture stricte, données consultables). |
| `src/pages/FinanceEncadrants.test.jsx` | page | **19 tests (LOT 27), rapport finance des encadrants — 100 % lignes/fonctions/branches**. Rendu via `FinancePageShell` (titre/sous-titre, liens de navigation dont l'onglet courant accentué, panneau de période). **Chargement** `GET /formations/finance/encadrants/?preset=mois&mois=…` : spinner puis trois KPI (`encadrants_count`, planifié/réalisé formatés par `fmtDuration`, ex. 720 min → `12h`, 450 → `7h 30min`, valeur nulle → `0h`), sections par encadrant (libellé puis repli sur le nom d'utilisateur, badge de sous-total, sept colonnes, sessions en badge, lignes sans grade/module/formation en tirets, pied de tableau), encadrant sans lignes, état vide (`{encadrants:[]}` comme `data:null`) avec KPI à zéro, erreur de chargement détaillée puis générique. **Période** (filtre partagé) : « Cette année » ne recharge qu'après **Appliquer** (nouvelle variante de données, persistance `sessionStorage`), trimestre T1 → `trimestre=YYYY-Q1`, personnalisé avec dates (`date_debut/date_fin`), Appliquer désactivé tant qu'une date manque. **Exports** `getBlob /exports/finance/encadrants/pdf|excel/` reportant la query de période, toasts `(PDF)`/`(XLSX)`, clic d'ancre/révocation, nom par défaut `liste_encadrants.pdf` quand le serveur n'en donne pas, deux niveaux d'erreur. **Filets défensifs** : période persistée sans `preset` → requêtes et export sur les chemins de base sans query, lignes et `sessions_count` absents (repli `[]`/`0`). |
| `src/pages/FinanceDashboard.test.jsx` | page | **29 tests (LOT 30), tableau de bord finance — 99,8 % lignes, 100 % fonctions, 97,2 % branches** (5 aiguillages de formatage défensifs, figés par les configs KPI statiques, sont inatteignables par l'UI). Rendu via `FinancePageShell` avec la période et le badge de période servie, onglet Tableau de bord accentué, recherche `GET /formations/finance/dashboard/?preset=mois&mois=…` (chemin sans query pour une période dégradée sans preset). **Chargement/erreurs** : spinner, détail serveur puis message générique, `data:null` sans crash. **Cinq KPI héro cliquables** : valeurs durée/argent/pourcentage (2h, 1h 30min, 75 %, 200 000/150 000 FCFA), sous-textes (séances, heures planifiées arrondies, actifs, période précédente ou repli, nombre de tarifs appliqués > 1 puis singulier), badges `EvolutionBadge` hausse/baisse/plat en durée/argent/`pts` avec infobulle du pourcentage. **KPI d'effectifs** (6 cartes, moy. en heures arrondies, replis à 0) ; **alerte de tolérance** active (compteurs avec `?? 0` quand absents, masquée inactive) et **info tarifs** (liste entre parenthèses). **Coût prévisionnel de repli** : somme des `montant_prevu` des modules quand la clé KPI est null/vide/absente (`|| 0` sur les modules sans montant). **Activité mensuelle** : barres proportionnelles à l'activité max (100/50/0 %), durée et montant par mois, section masquée sans données. **Spécialités** : table, forage par le compteur vers une modale (formateurs avec matricule/tiret, liste `|| []`, message vide, fermeture croix/« Fermer »/voile avec `stopPropagation` dans le contenu). **Classement enseignants** : trois mesures (réalisé/planifié/montants avec en-tête et formats changeants), médailles d'or/argent/bronze puis numéro grisé au-delà du top 3, replis matricule/spécialité/séances, état vide, onglet initial lu sur `?rank_tab=` (inconnu → repli réalisé), persistance `rank_tab` dans la query partagée. **Synthèse de paie** : pagination 25/page (26 lignes → 2 pages, suivante/numéros/précédente, badge « N formateur(s) — page x/y »), 13 colonnes, taux avec jauge, `FinanceToleranceBadge` ok/alerte/anomalie/écart/inconnu/absent, ligne lacunaire (tirets/zéros), état vide, réinitialisation de la pagination après Appliquer. **Ventilation par module** (`FinanceModuleBreakdownModal`, ouverte par les cinq KPI) : titres par mesure, tri décroissant, totaux de pied (8h, 6h, 75 %, 150 000/180 000 FCFA), colonne et ligne tarif, secrétariat, libellés et séances en tirets, recherche instantanée avec « N affiché(s) », total filtré + rappel global, absence de correspondance, période sans module, singulier « 1 module », fermetures croix/pied/voile. **Période** : « Cette année » ne recharge qu'après Appliquer (99 séances/100h, variante de données), persistance `sessionStorage finance_period`, sous-texte de taux par défaut sans comparaison, horodatage `generated_at` présent/absent. |
| `src/pages/FinanceParametrage.test.jsx` | page | **26 tests (LOT 28), paramétrage finance — 100 % lignes/fonctions/branches**. Rendu via `FinancePageShell` (titre/sous-titre, navigation, onglet Paramétrage accentué, **pas de panneau de période** sur cet écran). **Chargement** `GET /formations/finance/settings/` : spinner puis tarifs par formation (actifs d'abord, inactifs en dernier avec classe `text-muted` et badge `Inactif`, nombres servis en chaînes, `null` → champ vide, colonne « Tarif appliqué » avec séparateurs de milliers fr-FR ou mention « Non défini »), référentiel vide, interrupteur de tolérance révélant les deux champs (valeurs servies puis défauts 30 min / 5 %), douze champs d'exports restitués avec leurs valeurs par défaut (`FICHE DE PAIE DÉTAILLÉE`, `EFI`), méta-audit de dernière mise à jour (date `fr-FR`, auteur, ses trois cas dégradés : absent, date nulle, date illisible), erreur de chargement toastée. **Habilitations** : FINANCE en écriture ; hors FINANCE (ENCADRANT) — alerte « Consultation seule », bouton Enregistrer absent, tous les champs désactivés, soumission sans PATCH. **Édition/sauvegarde** `PATCH /formations/finance/settings/` : rafraîchissement en direct de la colonne tarif, **refus des tarifs négatifs** (`Tarif invalide pour « … »`, pas d'appel), séparateur décimal virgule accepté depuis une valeur serveur chaîne, payload complet (tarifs `{id, prix}` avec vide → `null`, tolérance `Number() || 0`, tous les champs d'exports dont les 12 éditables), répercussion de la réponse (tarifs, interrupteurs, méta-audit), réponses **sparse puis `data:null`** replongeant aux valeurs par défaut, état « Enregistrement… » (promesse différée : bouton et champs désactivés puis réactivés), deux niveaux d'erreur de sauvegarde. **Navigation** : la période courante est persistée (`sessionStorage finance_list_query`, mois courant) et reprise dans les liens du shell. |
| `src/pages/FinanceAjustements.test.jsx` | page | **35 tests (LOT 29), ajustements horaires finance — 100 % lignes/fonctions, 98,7 % branches** (seules 2 double-protections inatteignables par l'UI restent non couvertes). Rendu via `FinancePageShell` (onglet Ajustements accentué avec le **compteur d'attente** issu de `pending_count`, pas de panneau de période). **Chargement** `GET /formations/finance/ajustements/` (`{items, pending_count}`) : spinner, quatre KPI calculés (total/en attente/validés/rejetés), filtres de statut **côté client** (En attente par défaut, Validés, Rejetés, Tous ; badge compteur sur l'onglet), message vide spécifique au statut ou générique, réponse sans clé `items` (KPI à zéro, compteur nav seul). **Table** : badge de statut et son apparence (warning/success/secondary, repli neutre `bg-light`/`bi-circle` pour un statut inconnu), séance (module, grade/groupe, date), Δ positif (flèche haut, `+`, vert, `data-positive=true`) ou négatif (flèche bas, rouge), avant→après via `fmtDuration` local, motif (infobulle complète / **tronqué à 40 caractères + « … »** / tiret), proposition datée `fr-FR` ou tiret (date nulle comme illisible), valideur pour un VALIDE, boutons Valider/Rejeter réservés aux lignes en attente (y compris une ligne sans formateur/session). **Workflow** : `POST …/{id}/valider/` (toast de succès paie, rechargement, état d'action avec spinner et boutons désactivés via promesse différée, deux niveaux d'erreur), modale de rejet (résumé formateur/date/delta coloré, **motif obligatoire**, bouton désactivé à vide, annulation croix/bouton sans appel et réinitialisation à la réouverture, `POST …/{id}/rejeter/` avec motif élagué au `.trim()`, fermeture et rechargement, modale conservée avec les deux niveaux d'erreur). **Proposition** : formulaire toggle (en-tête et pied, réinitialisation), recherche d'enseignant `GET /formations/formateurs/list/` **débordancée à 300 ms** (rien sous 2 caractères, ni après annulation totale ; spinner ; `{search, page_size:20}` vérifiés ; matricule/spécialité ; réponse sans `results` et rejet réseau → liste vide), sélection à la souris puis `GET /formations/formateurs/finance-report/` (`{formateur_id, include_sessions:1, preset:'tout'}`) : **séances sans date écartées, tri date décroissante**, sélecteur verrouillé avant choix, trois libellés de placeholder (enseignant d'abord / aucune séance / choisir), durée arrondie, grade sans groupe, changement d'enseignant (crayon, séance réinitialisée), rapports dégradés (`{results:[]}`, bloc sans `sessions`, objet vide), `POST …/ajustements/` avec payload exact `{session_id, formateur_id, minutes_delta, motif}` en nombres/élagué (Soumettre désactivé sans séance, état « Envoi… », fermeture/reset/filtre En attente/rechargement, deux niveaux d'erreur sans fermer). Un `afterEach` purge les minuteurs de debounce résiduels (plus aucune alerte act). |
| `src/pages/NotesModule.test.jsx` | page | **20 tests (LOT 14), saisie des notes** (chaînon pédagogie → jury) : chargement module + grille (colonnes, barèmes, notes pré-remplies, critères seuil/présence, mention/moyenne/admission calculés, « saisi par »), recherche/filtre, état vide ; **saisie en direct** (mention normalisée /20, moyenne, bandeau « modifications non sauvegardées », note hors plage **0–20**, observations, navigation clavier **Entrée → champ suivant**) ; **enregistrement en bloc** `POST …/notes/bulk/` avec le payload `{notes, synthèses}` (mention calculée, cellules vides exclues), réponse partiellement en erreur (toast d'avertissement), échec (la saisie est conservée) ; **colonnes dynamiques** (ajout `POST …/notes/colonnes/`, libellé vide refusé, suppression `DELETE` avec confirmation et impossible à 1 colonne) ; **fiches PDF** module/individuelle (`getBlob`), confirmation si saisie non enregistrée, erreur de génération ; liens Décisions/Retour ; une régression §10.10 (une seule requête sur échec de chargement). Couvre **97,6 % des lignes / 92 % des fonctions**. |
| `src/pages/Rattrapages.test.jsx` | page | **18 tests (LOT 15), rattrapages de présence** : liste avec badges de statut/cohorte et **filtres débordancés** (`statut`, `q` vérifiés en query) ; états erreur/vide ; **lecture seule** pour un rôle hors `PRESENCE_ACTION_ROLES` (DIRECTION) ; **création** via recherche d'étudiant puis **sélection multiple de séances** (recherche ciblée `participant=`, séance « déjà inscrit » verrouillée, pastille ajout/retrait), mode **module entier** (ajout de toutes ses séances, module déjà fait verrouillé), motif, case « forcer la présence », validation sans étudiant/séance, **payload** `{participant_id, seance_rattrapage_ids, motif, generer_presence}` vérifié, toast créés/réactivés/ignorés, erreur serveur gardée dans la modale ; **génération de pointage** (`POST …/generer-presence/`) et **annulation** via `ConfirmModal` (avec/sans pointage → `supprimer_pointage`, refus = aucun appel), actions absentes sur un rattrapage annulé, cas d'erreur des deux écritures. Couvre **97,3 % des lignes / 86 % de branches** (le résidu est du filtrage défensif inatteignable via l'UI). |
| `src/pages/FicheAuditeur.test.jsx` | page | **8 tests (LOT 15), fiche de suivi d'un auditeur** : synthèse (formation, moyenne, classement, décision finale), suivi par module (heures présence/prevues, taux, moyenne, épreuves), état « aucun module », tirets des champs absents, erreur de chargement → « fiche introuvable », **exports PDF et Excel** (`getBlob`), nom de fichier par défaut, erreur d'export. Couvre **100 % des lignes / 100 % des fonctions**. |
| `src/pages/ModuleDetail.test.jsx` | page | **15 tests (LOT 16), émargement — onglets Séances et Présences de `ModuleDetail`**. Séances : badges de statut lus sur `en_cours`/`terminee`, compteurs d'onglets ; **démarrage** (`POST …/sessions/:id/start/` via `ConfirmModal`, toast + rechargement) et **annulation sans appel** ; **fin** (`stop/`), **suppression** (`DELETE …/delete/`, annulation puis confirmation), erreur backend (toast du `detail`), **création** (`POST …/sessions/new/` avec les 4 champs). **Habilitations** : un ENCADRANT peut démarrer mais pas créer/supprimer, la DIRECTION est strictement en lecture (pas de forçage). Présences : les **5 cartes de stats** (attendus = étudiants+enseignants+encadrants, en salle, présents, absents, taux), date sans pointage = tout le monde absent et message explicite ; **forçage unitaire** d'un étudiant absent (`POST …/force-pointage/` avec `{personne_id, type_personne, action:'ENTREE', motif, module_id, date_journee}`, bouton désactivé sans motif, toast du détail, fermeture) ; **badgeage en masse** toutes séances (motif obligatoire, `POST …/force-badgeage-étudiants-bulk/`, agrégat `sessions` en toast, fermeture), sur une séance précise (`session_id` transmis), erreur gardée dans la modale. **Complété aux LOTs 18 et 19 (33 tests au total)** : onglet Étudiants (liste + recherche débordancée 400 ms, **inscription via picker** avec exclusion des déjà inscrits, message d'erreur en modale, **retrait via ConfirmModal**, lecture seule DIRECTION), onglet Enseignants (liste, **assignation au clic via le picker** — happy path POST `formateurs/add/`, refus pour conflit d'emploi du temps affiché dans la modale, gating du bouton, liste vide avec `module_id`, **retrait confirmé** ; ces parcours sont les **régressions §10.12 du LOT 19**), onglet Informations (**édition du module PATCH**, erreur backend, **assignation/retrait du superviseur** encadrant, absence des boutons en DIRECTION), et **exports PDF/Excel** (`getBlob` module et séance avec nom de fichier dérivé, erreur notifiée). **Le LOT 20 porte le fichier à 46 tests et achève la page** : **modale QR des séances** (`QRCodeModal` — GET `superviseur/:id/qr/` avec `session_id`/`module_id`, état 404 « aucun QR actif », **génération** POST `sessions/:id/generate-qr/`, **régénération** derrière `ConfirmModal`, téléchargement PNG (`qr_seance_F_S.png`), refus d'un QR appartenant à un autre module, détail backend en échec, pas de QR sur séance terminée), **archivage** (`TripleConfirmModal` — les 3 étapes puis POST `…/archive/` et toast, annulation sans écriture, erreur backend, bouton masqué si `archived` ou pour un ENCADRANT), et **pagination serveur des pickers** (enseignant et étudiant : `page=2` après « Suivant », libellé `1–50 sur 80`, réinitialisation page 1 à la réouverture). Porte la page à **90,2 % de lignes / 67,9 % de branches / 61,7 % de fonctions** ; `QRCodeModal` atteint **95,8 % de lignes** et `TripleConfirmModal` **100 %** au travers de ces parcours. |
| `src/pages/FormationDetail.test.jsx` | page | **63 tests (LOTs 21 et 22), fiche formation — miroir de `ModuleDetail`, achevée à 98,4 % de lignes**. Chargement `GET /formations/:id/detail/` : titre, badges statut, lien module, cartes de résumé, **erreur de chargement** (carte d'erreur + bouton Retour), **onglet Présences masqué** pour un rôle non habilité (SUPERVISEUR). **Onglet Séances regroupées par module** : compteurs de présence/statuts, **démarrage** et **fin** via `ConfirmModal` (`POST sessions/:id/start|stop/`, annulation sans appel), **suppression** (`DELETE …/delete/`, annulation puis confirmation), **création inline** (`POST sessions/new/` avec `numero = sessions.length + 1` et intitulé calculé), **modification** (`PATCH …/update/`, titre de modale résolu par rôle *heading*), détail backend en échec, séance terminée sans action de vie. **Habilitations** : ENCADRANT peut démarrer mais pas créer/supprimer/modifier ; DIRECTION strictement lecture (séances comme étudiants). **Onglet Étudiants** : coordonnées, **ajout via picker** (`POST participants/add/`, exclusion des inscrits, debounce 300 ms), erreur backend (toast), **retrait confirmé** (`DELETE`). **Onglet Enseignants** : chargement paresseux `GET /formations/:id/formateurs/` à l'activation, **ajout au niveau formation** (`POST formateurs/add/` depuis une liste **sans `module_id`**, exclusion des assignés), **retrait confirmé**. **Onglet Informations** : assignation de l'encadrant (picker `GET /auth/users/?role=ENCADRANT`, clic ligne, `POST assign-superviseur/` en `superviseur_id` chaîne), validation refusée sans sélection, crayon masqué en DIRECTION. **Le LOT 22 achève l'écran (63 tests, 98,4 % de lignes / 81,8 % de branches)** avec : l'**onglet Présences temps réel** (`GET …/dashboard/?date&session_id`) — 5 cartes de stats, sections En salle/Sortis/Absents avec badges de type de personne et durées, sélecteur de séance, recherche côté client (`x / total`), libellés multi-séances et **badge Rattrapage** inter-cohortes, états vides, erreurs **403/404/500** ; le **forçage de pointage unitaire** (`POST …/force-pointage/`) — entrée étudiant (`Forcer présence`, durée planifiée, motif obligatoire, pas de timestamps aujourd'hui), **entrée enseignant** (`Badger`, `type_personne=formateur`), **fermeture de session** (SORTIE), **jour passé** avec heure d'entrée obligatoire et `timestamp_entree/sortie`, erreur backend, bouton « Aujourd'hui », DIRECTION sans action ; les **exports** `getBlob` formation (`rapport_formation_F.pdf/.xlsx`) et séance (nom dérivé de l'intitulé, accents remplacés), erreur notifiée ; l'**intégration QR de séance** (`QRCodeModal` recevant `session_id`/`module_id`) ; l'**archivage depuis l'en-tête de groupe** (`TripleConfirmModal` → `POST …/modules/:id/archive/`, annulation, échec, masqué pour un ENCADRANT et pour un groupe « Sans module ») ; l'**import Excel** réservé au SECRETARIAT (`POST …/import-excel/` en FormData `file/type/formation_id`, bilans créés/mises à jour/erreurs/rien traité, échec, bouton absent pour un ADMIN) ; la **pagination serveur** des deux pickers ; les états vides et filets d'erreur (liste enseignants, assignation, garde date obligatoire à la modification). |
| `src/pages/Participants.test.jsx` | page | **35 tests (LOT 23), CRUD des étudiants — 100 % de lignes / 100 % de fonctions / 93 % de branches**. **Liste serveur** (`GET /formations/participants/list/`, 50/page) : titre, colonnes, badges sexe/grade, compteur `n résultat(s)`, plage `x–y sur n`, **recherche débordancée 400 ms** avec retour page 1, six **filtres** (secrétariat, grade, groupe, type de concours, sexe, vague référentielle) transmis en query et cumulables, options garnies depuis `filter_options`, état vide, **erreur de chargement**, **pagination** page 2 et tirets de valeur absente. **Habilitations** : ADMIN (tout), SECRETARIAT (modifie/supprime/exporte mais **ne crée pas**), DIRECTION (lecture + export, pas de gestion), SUPERVISEUR (ni gestion ni export). **Création/édition** : POST/PATCH ciblés, `date_naissance` vide omise, pré-remplissage avec replis `''`, erreurs de validation backend formatées (`champ : msg`, valeur tableau ou scalaire), message générique, annulation/X/clic sur le voile sans écriture, **référentiels liés** (catégorie→grade filtré et remis à vide, site→salle filtré) et **repli en champs texte** quand les référentiels sont vides. **Suppression** via `ConfirmModal` (annulation, DELETE + toast, échec notifié). **Fenêtre de détail** : `GET /participant/:id/fiche-admin/` pour un rôle habilité à la vue présence vs `/formations/participants/:id/formations/` (tableau ou objet `{results}`) sinon, échec silencieux sans crash, fermeture. **Exports liste de classe** PDF/Excel (`getBlob /exports/participants/liste-classe/:fmt/`) : tous groupes vs libellé singulier avec filtre de groupe, tous les filtres reportés en query, toasts adaptés, détail d'erreur serveur puis message générique. Le composant `ParticipantDetailModal.jsx` (1 134 lignes) est achevé par son propre test aux LOTs 24 et 25 (98,8 % de lignes / 100 % de fonctions). |
| `src/components/ParticipantDetailModal.test.jsx` | composant | **50 tests (LOTs 24 et 25), fenêtre de fiche participant — 98,8 % de lignes / 100 % de fonctions / 84 % de branches**. Rendu direct avec les props (modules/pointages/stats/`initialNotesFiche`) plutôt que par la page, le câblage parent étant déjà couvert par `Participants.test.jsx`. **LOT 24, lecture** : en-tête (pastilles Modules/Présences/Temps total/En cours/À vérifier, matricule optionnel, spinner et boutons désactivés pendant `loading`, fermeture Fermer/X/voile, clic interne sans fermeture), 4 cartes de statistiques et état « Aucune donnée disponible », 19 champs d'identité formatés (`formatDate`, badge sexe, tirets de repli), onglet Modules (méta grade/groupe/vague/site, dates et statut, heures effectuées/prévues et taux coloré, présence vs séances planifiées vs « Aucune séance », heures fractionnaires 1,5 h, volume contractuel, date d'inscription, **déploiement des séances** `GET /formations/:f/modules/:m/full/` avec association par `seance_numero` — Présent/En cours/Non badgé, cache : un seul GET, clic interne sans repli, échec silencieux → « Aucune séance planifiée »), onglet Notes (moyenne/mention/taux depuis `initialNotesFiche` sans GET redondant, lecture seule sans `canManageNotes`, module dont la moyenne est introuvable, **moteur de décision** ADMIS/AJOURNÉ 72,73 %/EXCLUSION/EN_ATTENTE, priorité à la décision backend avec totaux horaires et « Validée manuellement », titres multi-formations, **chargement paresseux** `GET /participant/:id/notes-fiche/` avec grand spinner puis données, toast d'échec, état vide), onglet Séances (groupes **triés par formation**, résumé heures/terminées/en cours, lignes avec horaires, entrée/sortie, durée, appareil tronqué, géolocalisation `±12m`, batterie, heartbeat, sorties géofence). **LOT 25, écritures** : activation du bouton Enregistrer après saisie, POST `…/modules/:m/notes/bulk/` avec le payload `{notes:[{participant_id,colonne_id,note}],syntheses:[{participant_id,mention,observations}]}` suivi du recalcul `POST /evaluations/formations/:f/decisions/recalculer/` puis du rechargement de la fiche et du toast, garde 0–20 (y compris négatif), tableau vide quand la moyenne est effacée, bouton désactivé sans modification ou sans `colonne_id`, réponse partielle (`0 enregistrement(s), 2 erreur(s)`), erreur de sauvegarde détaillée puis générique, échec de recalcul avalé sans masquer le succès, module sans formation (chemin `…/formations/null/…`, pas de recalcul) ; **recalcul manuel** (POST, rechargement, toast de succès, détail d'erreur, erreur générique, masqué en lecture seule) ; **exports relevé** PDF et Excel (`getBlob /participant/:id/notes-fiche/export/:fmt/`, clic d'ancre et révocation d'URL, détail d'erreur puis message générique). Les quelques lignes non couvertes sont du code défensif inatteignable par l'UI (objet de stats de repli, squelette par carte rendu impossible par le spinner englobant, rappel de seuil sans heures que les valeurs calculées à 0 rendent inaccessible). |
| `src/components/formateurs/FormateurAssignPickerItem.test.jsx` | composant | **3 tests (LOT 18)** : rendu nom/prénom/spécialité, clic → `onAssign(id)` exact, gating conflit d'emploi du temps (le message remplace le bouton, ligne grisée), spécialité absente. Teste le contrat déclaré par le composant (prop `formateur`) ; le câblage de `ModuleDetail` aligné sur ce contrat au LOT 19 (§10.12) est testé dans `ModuleDetail.test.jsx`. **100 % de lignes / branches / fonctions**. |
| `src/pages/scolarite/campagnesCompletion.test.jsx` | page | **19 tests (LOT 16, complétés au LOT 17 §10.11), campagnes d'admission**. `Campagnes` : **création en brouillon** (formulaire — sélecteurs année/formation requis, dates, **champs quota d'admissibles/d'admis transmis en nombres**, quotas vides → `undefined`, réinitialisation + rechargement), échec serveur (formulaire conservé), **les 4 transitions restantes** du workflow (Suspendre sans confirmation, Clôturer avec confirmation, Réouvrir, Archiver ; annulation = aucun appel), lecture seule DIRECTION (référentiels non chargés). `CampagneDetail` : rendu (compteurs, quota, lignes d'épreuves verrouillées, tableau du classement et ses badges, épreuve verrouillée exclue du sélecteur de note, candidatures des autres campagnes filtrées), **ajout d'épreuve** (POST typé avec/sans salle, valeurs par défaut, reset, erreur JSON conservée), **génération des convocations** (confirm annulée puis acceptée), **verrouillage** (confirm d'irréversibilité, échec notifié), boutons absents sur épreuve verrouillée, **calcul du classement sans confirmation** puis **publication avec confirmation**, campagne clôturée (formulaire d'épreuve masqué) et les **régressions §10.11 (LOT 17)** : la carte de saisie de notes et les boutons de calcul/publication sont masqués sur campagne **clôturée comme annulée** (le classement reste consultable), DIRECTION en lecture seule. Porte `Campagnes.jsx` à **99,4 % de lignes / 100 % de fonctions** et `CampagneDetail.jsx` à **98,8 % / 100 %**. |
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

Mesure après le LOT 35 (V8, `npm run test:coverage`), sur les zones ciblées :

| Zone | Lignes | Instructions | Fonctions | Branches |
| --- | --- | --- | --- | --- |
| `src/utils/roles.js` | **100 %** | **100 %** | **100 %** | **100 %** |
| `src/utils/**` (rôles inclus) | 77 % | 77 % | 79 % | 86 % |
| `src/services/**` | **97 %** | **97 %** | 97 % | **91 %** |
| `src/context/**` | **99 %** | **99 %** | 89 % | **91 %** |
| `src/hooks/**` | **94 %** | **94 %** | 84 % | **94 %** |
| `pages/DecisionsPedagogiques.jsx` | **100 %** | 100 % | 100 % | **95 %** |
| `pages/Referentiels.jsx` (LOT 35) | **99,7 %** | **99,7 %** | **100 %** | **95,2 %** |
| `pages/Users.jsx` | **89 %** | 89 % | 49 % | **69 %** |
| `pages/Dashboard.jsx` | **75 %** | 75 % | 43 % | **84 %** |
| `pages/Modules.jsx` | **37 %** | 37 % | 6 % | **59 %** |
| `pages/NotesModule.jsx` (LOT 14) | **98 %** | 98 % | **92 %** | **84 %** |
| `pages/Rattrapages.jsx` (LOT 15) | **97 %** | 97 % | **77 %** | **86 %** |
| `pages/FicheAuditeur.jsx` (LOT 15) | **100 %** | **100 %** | **100 %** | **83 %** |
| `pages/ModuleDetail.jsx` (LOT 16/18/19/20) | **90 %** | 90 % | **62 %** | **68 %** |
| `pages/FormationDetail.jsx` (LOT 21/22) | **98 %** | 98 % | **77 %** | **82 %** |
| `pages/Participants.jsx` (LOT 23) | **100 %** | **100 %** | **100 %** | **93 %** |
| `components/ParticipantDetailModal.jsx` (LOT 24/25) | **99 %** | **99 %** | **100 %** | **84 %** |
| `pages/scolarite/FinancesEtudiantes.jsx` (LOT 26) | **100 %** | **100 %** | **100 %** | **97 %** |
| `pages/FinanceEncadrants.jsx` (LOT 27) | **100 %** | **100 %** | **100 %** | **100 %** |
| `pages/FinanceParametrage.jsx` (LOT 28) | **100 %** | **100 %** | **100 %** | **100 %** |
| `pages/FinanceAjustements.jsx` (LOT 29) | **100 %** | **100 %** | **100 %** | **98,7 %** |
| `pages/FinanceDashboard.jsx` (LOT 30) | **99,8 %** | **99,8 %** | **100 %** | **97,2 %** |
| `components/QRCodeModal.jsx` (via ModuleDetail, LOT 20) | **96 %** | 96 % | 90 % | **82 %** |
| `components/TripleConfirmModal.jsx` (via ModuleDetail, LOT 20) | **100 %** | **100 %** | **100 %** | **89 %** |
| `components/formateurs/FormateurAssignPickerItem.jsx` (LOT 18) | **100 %** | **100 %** | **100 %** | **100 %** |
| `pages/scolarite/Campagnes.jsx` (LOT 16/17) | **99 %** | 99 % | **100 %** | **89 %** |
| `pages/scolarite/CampagneDetail.jsx` (LOT 16/17) | **99 %** | 99 % | **100 %** | **89 %** |
| `pages/Statistiques.jsx` | **28 %** | 28 % | 17 % | **58 %** |
| `pages/scolarite/Candidatures.jsx` | **97 %** | 97 % | 74 % | **79 %** |
| `pages/scolarite/Admissions.jsx` | **98 %** | 98 % | 90 % | **85 %** |
| `pages/scolarite/Inscriptions.jsx` | **99 %** | 99 % | **100 %** | **87 %** |
| `pages/scolarite/FicheEtudiant.jsx` | **90 %** | 90 % | **100 %** | **74 %** |
| `pages/scolarite/Jurys.jsx` (LOT 12) | **100 %** | **100 %** | **100 %** | **88 %** |
| `pages/scolarite/Graduation.jsx` (LOT 12) | **100 %** | **100 %** | **100 %** | **85 %** |
| `pages/scolarite/MonEspace.jsx` (LOT 13) | **74 %** | 74 % | 50 % | **100 %** |
| `pages/scolarite/Equivalences.jsx` (LOT 31) | **100 %** | **100 %** | **100 %** | **100 %** |
| `pages/scolarite/MaquetteDetail.jsx` (LOT 32) | **100 %** | **100 %** | **100 %** | **100 %** |
| `pages/scolarite/ChargesEnseignants.jsx` (LOT 33/34) | **100 %** | **100 %** | **100 %** | **96,9 %** |
| `pages/scolarite/**` (dossier, 16 écrans) | **94,1 %** | **94,1 %** | **90,1 %** | **88,5 %** |
| **Global `src/` (toutes zones)** | **62,3 %** | **62,3 %** | **59,2 %** | **80,6 %** |

> Les LOT 4 à 7, 13 et 17 sont des correctifs ciblés ; les LOT 8 à 12 et 14 à
> 16 n'ajoutent que des tests.
> Les seuils du LOT 3 restent inchangés (aucun seuil n’a été baissé). Le nombre
> de tests progresse : 464 (LOT 4) → 467 (LOT 5) → 472 (LOT 6) → 477
> (LOT 7) → 483 (LOT 8) → 492 (LOT 9) → 500 (LOT 10) → 510 (LOT 11) →
> 539 (LOT 12) → 542 (LOT 13) → 562 (LOT 14) → 588 (LOT 15) →
> 620 (LOT 16) → 622 (LOT 17) → 641 (LOT 18) → 643 (LOT 19) →
> 656 (LOT 20) → 681 (LOT 21) → 719 (LOT 22) → 754 (LOT 23) →
> 783 (LOT 24) → 803 (LOT 25) → 828 (LOT 26) → 847 (LOT 27) →
> 873 (LOT 28) → 908 (LOT 29) → 937 (LOT 30) → 964 (LOT 31) → 999 (LOT 32)
> → 1022 (LOT 33) → **1078 (LOT 35)** ; lignes
> couvertes globalement 35,3 % (LOT 5) → … → 41,6 % (LOT 14) → 43,1 %
> (LOT 15) → 45,3 % (LOT 16/17) → 47,4 % (LOT 18) → 47,5 % (LOT 19) →
> 48,1 % (LOT 20) → 50,3 % (LOT 21) → 52,2 % (LOT 22) → 53,7 % (LOT 23) →
> 55,9 % (LOT 24) → 56,3 % (LOT 25) → 56,7 % (LOT 26) → 57,3 % (LOT 27) →
> 57,8 % (LOT 28) → 59,0 % (LOT 29) → 60,1 % (LOT 30) → 60,4 % (LOT 31) →
> 60,6 % (LOT 32) → 60,8 % (LOT 33) → **62,3 % (LOT 35)** — le seuil des
> 60 % de lignes reste franchi, les fonctions approchent les 60 %
> (**59,2 %**, pour un plancher CI de 23 %) et les branches dépassent
> **80 %**. Les LOT 17 et 19 corrigent
> la logique (transformation de tests `[écart]` en régressions, sans
> nouveau fichier) ; le LOT 18 était un lot de tests purs qui a révélé le
> bug bloquant §10.12, corrigé au LOT 19 ; le LOT 20 achève la couverture
> fonctionnelle de `ModuleDetail`, le LOT 21 ouvre l'écran miroir
> `FormationDetail` (63 % de lignes, global au-delà de 50 %), le **LOT 22
> l'achève à 98,4 % de lignes**, le **LOT 23 porte le CRUD des
> participants `Participants.jsx` à 100 % de lignes / 100 % de fonctions** et
> les **LOTs 24 et 25 achèvent la fenêtre `ParticipantDetailModal` à
> 98,8 % de lignes / 100 % de fonctions** (lecture : onglets, moteur de
> décision et séances ; écritures : saisie de moyenne `bulk`, recalcul et
> exports relevé) : les deux fiches du domaine présence sont défendues de
> bout en bout, et le référentiel étudiant — liste, CRUD, fiche détaillée,
> décisions pédagogiques et exports — est entièrement verrouillé.
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
> calcul et publication du classement) ; le LOT 17, sur feu vert explicite,
> **corrige les deux constats §10.11** relevés au passage (champs quota à la
> création, et saisie de notes/actions de classement interdites sur campagne
> fermée) avec des régressions dédiées. Le LOT 18 approfondit ensuite le gros
> écran d'émargement `ModuleDetail` (**51,8 → 88,3 % de lignes** :
> inscriptions/retraits d'étudiants, édition du module et du superviseur,
> exports de feuille), porte le composant `FormateurAssignPickerItem` à
> **100 %**, et révèle le bug bloquant §10.12 (modale d'assignation d'un
> enseignant en panne) ; le **LOT 19 corrige ce bug** par l'alignement du nom
> de prop (`formateur`), l'assignation étant désormais exercée bout-en-bout
> (happy path, conflit d'emploi du temps, gating) et la page portée à
> **89,3 % de lignes** ; le **LOT 20 achève la couverture fonctionnelle de
> l'écran** à **90,2 % de lignes / 61,7 % de fonctions** en exerçant la
> modale QR (95,8 %), l'archivage à trois confirmations (`TripleConfirmModal`
> à 100 %) et la pagination serveur des pickers.
> Le **LOT 21 ouvre ensuite l'écran miroir `FormationDetail`** (niveau
> formation, **63,0 % de lignes** dès ses 25 premiers tests) : onglets et
> regroupement des séances par module, cycle de vie complet des séances,
> étudiants/enseignants avec pickers et encadrant. Le **LOT 22 l'achève à
> 98,4 % de lignes (63 tests)** : l'onglet Présences temps réel (dashboard,
> sélecteur de séance, recherche, forçage unitaire aujourd'hui / jour passé
> avec timestamps, 403/404/500, DIRECTION sans action), les exports
> formation/séance, le QR, l'archivage depuis l'en-tête de groupe, l'import
> Excel SECRETARIAT, la pagination serveur des pickers et les états vides ;
> les deux fiches présence (module et formation) sont ainsi couvertes de
> bout en bout. Le **LOT 23 verrouille le CRUD des étudiants**
> (`Participants.jsx`, **35 tests, 100 % de lignes / 100 % de fonctions**) :
> liste serveur avec recherche débordancée et six filtres, création/édition
> (avec les référentiels liés catégorie→grade et site→salle et le repli en
> champs texte), suppressions confirmées, fenêtre de détail fiche-admin vs
> formations selon le rôle, exports liste de classe PDF/Excel et les quatre
> niveaux d'habilitation (ADMIN, SECRETARIAT sans création, DIRECTION
> lecture + export, SUPERVISEUR sans gestion). Les **LOTs 24 et 25
> achèvent la fenêtre `ParticipantDetailModal` (1 134 lignes) à 98,8 % de
> lignes / 100 % de fonctions (50 tests)** : le LOT 24 couvre la lecture
> (cinq onglets, moteur de décision ADMIS/AJOURNÉ/EXCLUSION avec priorité à
> la décision backend, déploiement des séances) et le LOT 25 les écritures
> (saisie de moyenne `bulk` avec recalcul en cascade et leurs filets
> d'erreur, recalcul manuel, exports relevé PDF/Excel). Le **LOT 26 verrouille
> la finance étudiante** (`scolarite/FinancesEtudiantes`, **25 tests,
> 100 % de lignes / 100 % de fonctions**) : échéanciers, paiements
> idempotents et confirmation sous preuve, avec toute la matrice
> d'habilitation. Le **LOT 27 ouvre le module Finance transverse** avec le
> **rapport des encadrants** (`FinanceEncadrants`, **19 tests,
> 100 % lignes/fonctions/branches**) : KPI et tableaux de volumes horaires,
> période partagée mois/trimestre/année/personnalisé via le shell commun,
> exports PDF/Excel et filets défensifs (période sans preset, données
> lacunaires). Le **LOT 28 verrouille le paramétrage finance**
> (`FinanceParametrage`, **26 tests, 100 % lignes/fonctions/branches**) :
> tarifs horaires par formation (ordre actifs/inactifs, valeur appliquée,
> validation des négatifs), marge de tolérance et douze champs d'exports,
> PATCH complet et répercussion des réponses sparse/null, matrice
> FINANCE/consultation seule et état d'enregistrement. Le **LOT 29
> verrouille les ajustements horaires** (`FinanceAjustements`, **35 tests,
> 100 % lignes/fonctions, 98,7 % branches**) : KPI et filtres de statut côté
> client, workflow valider/rejeter avec modale de motif et états d'action,
> proposition avec recherche d'enseignant débordancée et séances issues du
> rapport finance triées/filtrées, avec tous les états dégradés (les 2
> branches restantes sont des double-protections inatteignables par l'UI).
> Le **LOT 30 achève le module Finance transverse** (`FinanceDashboard`,
> **29 tests, 99,8 % de lignes / 100 % de fonctions / 97,2 % de branches**) :
> KPI héro évolutifs et forages (spécialités, ventilation par module en
> cinq mesures avec recherche et totaux), classements médaillés, synthèse
> paginée avec badges de tolérance, période partagée et `rank_tab`
> persistant ; les 5 branches résiduelles sont des aiguillages de
> formatage figés par les tables de configuration statiques des KPI.
> Le **LOT 31 verrouille l'écran équivalences/dispenses** (`Equivalences`,
> **27 tests, 100 % lignes/fonctions/branches**) : référentiels chargés sous
> habilitation seulement, création typée, transitions selon le statut,
> décision pédagogique et application confirmée, tous les chemins d'erreur et
> la lecture seule des rôles non acteurs. Le **LOT 32 verrouille le détail de
> maquette pédagogique** (`MaquetteDetail`, **35 tests, 100 %
> lignes/fonctions/branches**) : regroupement des UE par semestre et journal,
> workflow valider/activer/archiver avec les trois niveaux d'erreur
> (`problemes` de cohérence compris), clonage versionné avec redirection,
> ajout typé d'UE et d'ECUE (formulaires isolés par UE), archivage d'ECUE et
> contrôles réservés aux brouillons des rôles acteurs. Le **LOT 33 verrouille
> les charges pédagogiques des enseignants** (`ChargesEnseignants`,
> **23 tests, 100 % lignes/fonctions, 96,9 % branches**) : année courante au
> montage, occupation/anomalies, détail et affectations d'un enseignant,
> > création typée avec rechargements ciblés, référentiels sous habilitation ;
> le **crash §10.13** alors révélé (état `options` incomplet) est **corrigé
> au LOT 34** par un état initial complet, avec les deux tests `[écart]`
> transformés en régressions (toast sans crash, course de résolution
> stable). Avec ces lots, **les cinq écrans Scolarité réparés au §10.8 sont
> tous couverts en profondeur** et le dossier `pages/scolarite/` atteint
> **94,1 % de lignes / 90,1 % de fonctions / 88,5 % de branches** (le
> service `services/scolarite.js` reste à **100 % de lignes**).
> Le **LOT 35 ouvre l'administration transverse avec les référentiels de
> formation** (`Referentiels`, **56 tests, 99,7 % de lignes, 100 % de
> fonctions, 95,2 % de branches**) : les neuf collections sont chargées en
> un GET, paginées et gérées en CRUD (modules multi-formations avec grille de
> volumes, hiérarchie site/bâtiment/salle, coercitions d'identifiants),
> activation, suppression confirmée avec le cas 404 dédoublonné, import/export
> Excel et persistance de l'onglet dans l'URL ; les seules branches non
> couvertes sont les replis défensifs d'un onglet déjà borné par
> `readReferentielsTab` et d'états que le composant initialise toujours.

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
§10.6), de même que les LOT 6/7 (§10.2, §10.7, §10.8), le LOT 13 (§10.10), le
**LOT 17 (§10.11)**, le **LOT 19 (§10.12)** et le **LOT 34 (§10.13)**. Les
points encore ouverts sont ci-dessous (§10.1 et §10.9).

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

### 10.11 Corrigé au LOT 17 — deux incohérences des campagnes d'admission

Les tests de complétion du flux admission (`campagnesCompletion.test.jsx`,
LOT 16) avaient mis en évidence deux écarts de cohérence. Le **LOT 17**, sur
feu vert explicite, les corrige minimalement, sans toucher aux contrats
d'API :

1. **Quotas non saisissables à la création.** Le formulaire *Nouvelle campagne*
   de `Campagnes.jsx` ne comportait aucun champ `quota_admissibles` /
   `quota_admis`, alors que le gestionnaire `creer` les transmettait au
   backend (ils partaient donc toujours en `undefined`) et que
   `CampagneDetail.jsx` affiche le « quota admissibles » d'une campagne.
   **Correctif** : deux champs numériques optionnels (`min=0`, libellés
   *Quota admiss.* / *Quota admis*) sont ajoutés au formulaire, et le
   gestionnaire les numérise (`Number(form.quota_admissibles) || undefined`,
   comme les identifiants) ; champs vides → clés absentes du payload.
   **Régressions** : le test de création remplit les quotas (30 / 25) et
   vérifie leur envoi sous forme de **nombres** et la réinitialisation du
   formulaire ; un test dédié vérifie que des quotas vides restent non
   transmis (`undefined`).
2. **Saisie de notes et actions de classement actives sur campagne fermée.**
   Dans `CampagneDetail.jsx`, une campagne `CLOTUREE` / `ANNULEE` /
   `ARCHIVEE` masquait déjà le formulaire d'ajout d'épreuve et les boutons
   *Convocations* / *Verrouiller*, mais la carte *Saisie des notes* (qui
   contient aussi *Calculer le classement* / *Publier les listes*) restait
   rendue et actionnable. **Correctif** : la carte est désormais conditionnée
   par `peutAgir && !campagneFermee` (une seule ligne modifiée), par
   cohérence avec les autres garde-fous ; le tableau de classement en lecture
   reste affiché. **Régressions** : deux tests (campagne `CLOTUREE`, puis
   `ANNULEE`) vérifient l'absence de la carte et des deux boutons, le
   classement restant consultable ; la carte reste bien présente sur une
   campagne `PLANIFIEE` (tous les tests de saisie préexistants continuent de
   passer).

Le test `[écart]` du LOT 16 a été remplacé par ces régressions ; le lint
reste vierge et les deux écrans se maintiennent à **99 % de lignes / 100 % de
fonctions**.

### 10.12 BUG corrigé au LOT 19 — la modale « Assigner un enseignant » de ModuleDetail plantait

Révélé au LOT 18 en testant l'assignation d'un enseignant à un module
(onglet *Enseignants* → bouton *Assigner*), il s'agissait d'un **bug
bloquant de câblage de propriété** :

- la page `ModuleDetail.jsx` rendait
  `<FormateurAssignPickerItem enseignant={f} onAssign={…} />` (prop
  **`enseignant`**) ;
- or le composant `components/formateurs/FormateurAssignPickerItem.jsx`
  déstructure **`formateur`**.

`formateur` valait donc `undefined`, et la première ligne rendue
(`const { nom } = formateur`) levait
`TypeError: Cannot destructure property 'nom' of 'formateur' as it is
undefined` : la page basculait sur l'erreur React dès qu'un enseignant
disponible était renvoyé (liste vide = pas de crash, d'où la discrétion ; le
smoke n'ouvrait jamais la modale). Il était **impossible d'assigner un
enseignant à un module depuis le web**, alors que le retrait fonctionnait et
que le backend était prêt.

**Correctif (LOT 19, feu vert explicite), une seule ligne de
`ModuleDetail.jsx`** : la prop passée au composant est renommée pour
s'aligner sur son contrat et son unique appelant —
`<FormateurAssignPickerItem formateur={f} … />`. Le composant et son test
unitaire (prop `formateur`, **100 %**) restent inchangés.

**Régressions (dans `ModuleDetail.test.jsx`, en remplacement du test
`[écart]` du LOT 18)** :

- **happy path** : ouverture du picker, les enseignants déjà assignés sont
  exclus, clic sur le bouton `+` → `POST …/modules/:id/formateurs/add/`
  avec `{ formateur_id }`, toast « Enseignant assigné », modale conservée ;
- **refus backend** (conflit d'emploi du temps) : le détail reste affiché
  dans une alerte de la modale (qui ne se ferme pas), sans fausse
  réussite ;
- **gating** : un enseignant porteur d'un `conflit_assignation` n'offre pas
  de bouton d'assignation (le message explique l'occupation) ;
- cas de la **liste vide** (message dédié) et transmission du `module_id`
  au chargement.

La page `ModuleDetail.jsx` passe de 88,3 à **89,3 % de lignes** et
l'assignation d'enseignant est désormais défendue de bout en bout.

### 10.13 BUG corrigé au LOT 34 — `ChargesEnseignants` : crash de la carte de création si les référentiels échouent (ou répondent trop lentement)

Révélé au LOT 33 en testant l'écran des charges pédagogiques
(`ChargesEnseignants.jsx`), d'abord figé par deux tests `[écart §10.13]`
(assertés via la `TestErrorBoundary`), il s'agissait d'un **crash
d'écran blanc** :

- l'état initial `options` est
  `{ formations: [], niveaux: [], semestres: [], ecues: [], groupes: [] }`
  — il **ne déclare pas `formateurs`** (ni `annees`, ajouté seulement
  comme clé après résolution) ;
- les cinq référentiels sont chargés en parallèle au montage pour un rôle
  acteur ; si cet appel **échoue**, le `.catch` affiche bien le toast
  « Chargement des référentiels impossible. » mais `setOptions` n'est
  jamais appelé : la carte « Nouvelle affectation pédagogique » rend alors
  `options.formateurs.map(...)` sur `undefined` et la page entière bascule
  sur l'erreur React (`Cannot read properties of undefined (reading 'map')`)
  au lieu d'afficher des sélecteurs vides ;
- le même crash se produit sur une **course de résolution** :
  l'occupation/anomalies (enchaînement année courante → chargement) peut
  s'afficher **avant** que le `Promise.all` des référentiels ait répondu
  (référentiel lent) ; la carte s'affique alors que `options.formateurs`
  n'existe pas encore.

**Comportement fautif constaté au LOT 33** : après un échec des
référentiels, le toast s'affichait **puis** l'arbre de la carte crashait ;
avec des référentiels lents (formateurs en promesse non résolue) et une
occupation immédiatement servie, l'écran crashait également (course de
résolution).

**Correctif (LOT 34, feu vert explicite), uniquement l'état initial de
`ChargesEnseignants.jsx`** : celui-ci déclare désormais toutes les clés lues
au rendu — `{ annees: [], formateurs: [], formations: [], niveaux: [],
semestres: [], ecues: [], groupes: [] }` — ce qui rend la carte
résiliente aux deux cas.

**Régressions (dans `ChargesEnseignants.test.jsx`, en remplacement des deux
tests `[écart]` du LOT 33)** : un échec des référentiels affiche le toast
« Chargement des référentiels impossible. » **sans crasher** (l'occupation
reste affichée, les sélecteurs ne contiennent que leur option fantôme), et
des référentiels lents servis après l'occupation laissent l'écran stable
avec les sélecteurs vides. Les deux tests échouent sur l'ancien état
initial (preuve de mutation par aller-retour du correctif). La page reste à
**100 % de lignes/fonctions, 96,9 % de branches**.

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

**Aucune page n'est dépourvue de test.** État après le LOT 35 :

- dix-sept écrans disposent d'un test **fonctionnel dédié** hors module
  Scolarité (les quatre écrans du module Finance transverse —
  `FinanceEncadrants`, `FinanceParametrage`, `FinanceAjustements`,
  `FinanceDashboard` — et l'écran d'administration `Referentiels` s'ajoutent
  aux douze initiaux) :
  `Login.jsx`, `DecisionsPedagogiques.jsx` (100 % de lignes), `Users.jsx`
  (89 %, liste serveur + CRUD), `Dashboard.jsx` (75 %), `Modules.jsx` (37 %,
  nettoyage des filtres obsolètes), `Statistiques.jsx` (28 %, contrat
  d'isolation par secrétariat + synchro des justificatifs §10.7),
  `NotesModule.jsx` (**97,6 % de lignes**, LOT 14 — grille de saisie, bulk,
  colonnes, fiches PDF), `Rattrapages.jsx` (**97,3 % de lignes**, LOT 15 —
  création inter-cohortes, génération de pointage, annulation),
  `FicheAuditeur.jsx` (**100 % de lignes/fonctions**, LOT 15 — fiche de suivi
  et exports) et `ModuleDetail.jsx` (**90,2 % de lignes / 67,9 % de branches /
  61,7 % de fonctions**, LOTs 16, 18, 19 et 20 — émargement : séances/présences,
  étudiants, enseignants dont l'assignation réparée §10.12, édition,
  superviseur, exports, QR des séances, archivage et pagination des pickers ;
  l'écran est désormais couvert fonctionnellement de bout en bout), et
  `FormationDetail.jsx` (**98,4 % de lignes / 81,8 % de branches / 77,4 % de
  fonctions**, LOTs 21 et 22 — fiche de niveau formation **achevée** :
  séances regroupées par module et leur cycle de vie, étudiants/enseignants
  avec pickers paginés, encadrant, onglet Présences temps réel avec forçage
  de pointage unitaire (aujourd'hui / jour passé), exports, QR, archivage
  depuis les groupes, import Excel SECRETARIAT, états vides/erreurs et
  habilitations), et
  `Participants.jsx` (**100 % de lignes/fonctions / 93 % de branches**,
  LOT 23 — **CRUD des étudiants** : liste serveur paginée, recherche
  débordancée et six filtres, création/édition avec référentiels liés,
  suppressions confirmées, fenêtre de détail fiche-admin/formations selon
  le rôle, exports liste de classe et quatre niveaux d'habilitation) ;
  sa **fenêtre de détail `ParticipantDetailModal` est achevée aux LOTs 24 et
  25** (50 tests, 98,8 % de lignes / 100 % de fonctions : lecture des cinq
  onglets, moteur de décision ADMIS/AJOURNÉ/EXCLUSION/EN_ATTENTE avec
  priorité à la décision backend, déploiement et tri des séances, saisie de
  moyenne `bulk` avec recalcul en cascade, recalcul manuel et exports
  relevé PDF/Excel ; seul du code défensif inatteignable par l'UI reste non
  couvert), et
  `Referentiels.jsx` (**99,7 % de lignes / 100 % de fonctions / 95,2 % de
  branches**, LOT 35 — **administration des neuf référentiels de formation** :
  un seul GET pour les neuf collections, pagination client, CRUD typé par
  onglet, modules multi-formations avec grille de volumes, hiérarchie
  site/bâtiment/salle, activation, suppression confirmée avec cas 404
  dédoublonné, import/export Excel et onglet persistant dans l'URL ; les
  branches résiduelles sont des replis défensifs d'un onglet borné par
  `readReferentielsTab`) ;
- cinq écrans Scolarité (`Campagnes`, `CampagneDetail`, `Equivalences`,
  `MaquetteDetail`, `ChargesEnseignants`) ont un **test de rendu dédié**
  (`scolariteRendu.test.jsx`, §10.8) qui affirme un contenu caractéristique et
  le chargement effectif — allant au-delà du smoke qui n'exclut pas les pages
  blanches ; leurs **actions d'écriture sont en outre exercées au clic** au
  LOT 8 (`scolariteActions.test.jsx`, §10.8), les deux écrans *Campagnes*
  sont **quasi exhaustivement couverts au LOT 16**
  (`campagnesCompletion.test.jsx`, **99 % de lignes / 100 % de fonctions**),
  **`Equivalences` est verrouillé de bout en bout au LOT 31**
  (`Equivalences.test.jsx`, **27 tests, 100 % lignes/fonctions/branches**),
  **`MaquetteDetail` au LOT 32** (`MaquetteDetail.test.jsx`, **35 tests,
  100 % lignes/fonctions/branches**) et **`ChargesEnseignants` au LOT 33**
  (`ChargesEnseignants.test.jsx`, **23 tests, 100 % lignes/fonctions,
  96,9 % branches après le correctif §10.13 du LOT 34**) : **les cinq
  écrans réparés au §10.8 sont désormais tous couverts en profondeur** ;
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
  est couvert sur ses deux onglets cœur, **Séances** (démarrer /
  terminer / supprimer / créer, chaque écriture destructrice passant par la
  `ConfirmModal` globale, toasts et rechargement) et **Présences** (les cinq
  cartes de statistiques calculées à partir des pointages du jour et de la
  liste des attendus, forçage de pointage **unitaire** et **badgeage en masse**
  80–95 % avec motif obligatoire, filtres date/séance, trois niveaux
  d'habilitation ENCADRANT / secrétariat / DIRECTION) ;
- aux LOTs 18 et 19, le même écran est **approfondi à 89,3 % de lignes**
  (33 tests) : onglet Étudiants (recherche débordancée, inscription via
  picker, retrait confirmé), onglet Enseignants (**assignation au clic**
  réparée et testée au LOT 19 après le bug §10.12 — happy path, conflit
  d'emploi du temps en modale, gating ; retrait confirmé), onglet
  Informations (édition du module PATCH, assignation et retrait du
  superviseur encadrant), exports PDF/Excel du module et d'une séance
  (`getBlob`, nom de fichier dérivé) ; le composant
  `FormateurAssignPickerItem` est testé unitairement à **100 %** ;
- au LOT 20, l'écran est **porté à 90,2 % de lignes (46 tests)** et achevé
  fonctionnellement : la **modale QR des séances** (chargement du QR actif,
  état 404, génération, régénération avec confirmation, téléchargement PNG,
  rejet d'un QR d'un autre module, échecs backend, absence sur séance
  terminée — `QRCodeModal` à 95,8 %), l'**archivage à trois confirmations**
  (parcours complet POST, annulation, échec, bouton masqué si déjà archivé
  ou pour un ENCADRANT — `TripleConfirmModal` à 100 %) et la **pagination
  serveur des pickers** enseignants/étudiants (`page=2`, libellé d'intervalle,
  retour page 1 à la réouverture) ;
- aux LOTs 21 et 22, l'écran miroir **`FormationDetail`** est couvert par un
  **test dédié de 63 tests (98,4 % de lignes)**. Le LOT 21 pose les fondations
  (63 % de lignes) : chargement et erreur, masquage de l'onglet Présences
  selon le rôle, séances **regroupées par module** avec démarrage/fin/
  suppression/création inline/modification, étudiants (ajout picker, retrait),
  enseignants (chargement paresseux de l'onglet, ajout **niveau formation
  sans `module_id`**, retrait) et assignation de l'encadrant, avec les
  habilitations ENCADRANT/DIRECTION. Le **LOT 22 achève l'écran** : onglet
  Présences temps réel (dashboard, sélecteur de séance, recherche, forçage
  unitaire étudiant/enseignant/fermeture, jour passé avec timestamps,
  403/404/500, rattrapage inter-cohortes, multi-séances, DIRECTION sans
  action), exports formation/séance, QR de séance, archivage
  `TripleConfirmModal` depuis les en-têtes de groupe (y compris l'absence
  pour « Sans module »), **import Excel réservé au SECRETARIAT** (FormData,
  bilans created/updated/errors), pagination serveur des pickers et états
  vides ;
- au LOT 23, le **CRUD des étudiants** `Participants.jsx` est couvert par un
  **test dédié de 35 tests à 100 % de lignes / 100 % de fonctions / 93 % de
  branches** : liste serveur 50/page (recherche débordancée, six filtres
  cumulables, `filter_options`, état vide, erreur, pagination), créations et
  éditions POST/PATCH (date vide omise, erreurs de validation formatées,
  référentiels liés catégorie→grade et site→salle, repli texte sans
  référentiels), suppressions confirmées et leur échec, fenêtre de détail
  fiche-admin vs formations selon le rôle, exports liste de classe
  PDF/Excel avec report des filtres, et les quatre niveaux d'habilitation
  (ADMIN, SECRETARIAT sans création, DIRECTION lecture + export, SUPERVISEUR
  sans gestion ni export) ;
- aux LOTs 24 et 25, le composant **`ParticipantDetailModal`**
  (1 134 lignes) reçoit un **test dédié de 50 tests qui l'achève à
  98,8 % de lignes / 100 % de fonctions / 84 % de branches**. Le LOT 24
  couvre toute la lecture : cinq onglets, états vides et spinner,
  statistiques agrégées, identité formatée, cartes modules avec heures et
  taux colorés, **déploiement des séances** via `GET …/modules/:id/full/`
  (association des pointages, cache, clic interne sans repli, échec
  silencieux), **moteur de décision de formation** (calculs
  ADMIS/AJOURNÉ/EXCLUSION/EN_ATTENTE selon moyenne pondérée et taux de
  présence, priorité à la décision backend, mention de validation
  manuelle, totaux horaires, groupement multi-formations), chargement
  paresseux de la fiche de notes (spinner, données, toast d'erreur), tri
  des séances par formation et détails techniques des badgeages (appareil,
  géolocalisation, batterie, geofence). Le LOT 25 couvre les **écritures** :
  saisie de moyenne `bulk` (payload `notes`/`synthèses`, garde 0–20,
  tableaux vides, colonne absente, réponse partielle et erreurs, recalcul
  en cascade dont l'échec est avalé, module sans formation), recalcul
  manuel de décision (succès, deux niveaux d'erreur, masquage en lecture
  seule) et exports relevé PDF/Excel (téléchargement, deux niveaux
  d'erreur) ;
- au LOT 26, l'écran **`scolarite/FinancesEtudiantes`** (domaine finance
  qui écrit) reçoit un **test dédié de 25 tests à 100 % de lignes / 100 %
  de fonctions / 97 % de branches** : chargement parallèle échéanciers +
  paiements (deux formes de réponse), navigation par onglets et Actualiser,
  échéanciers avec badges de statut global et repli, paiements avec la
  table de badges complète, **création de paiement idempotente** via
  `transaction_externe` (POST exact, réinitialisation, rechargement, deux
  niveaux d'erreur) et **confirmation sous `window.confirm`** (preuve
  exigée, annulation sans appel, quittance, deux niveaux d'erreur), et la
  matrice d'habilitation FINANCE/DIRECTION/admin (saisie + confirmation),
  SECRÉTARIAT (saisie seule), ENCADRANT (lecture stricte) ;
- au LOT 27, l'écran **`FinanceEncadrants`** (premier rapport du module
  Finance transverse, basé sur le shell et la période partagés) reçoit un
  **test dédié de 19 tests à 100 % de lignes / fonctions / branches** :
  KPI de synthèse formatés (`fmtDuration`), sections par encadrant et
  tableaux par groupe avec tous les replis (libellé/nom d'utilisateur,
  tirets, lignes absentes, compteurs nuls), navigation du shell, périodes
  mois/trimestre/année/personnalisé appliquées après « Appliquer » et
  persistées, exports PDF/Excel reportant la période (nom de fichier par
  défaut, deux niveaux d'erreur), période dégradée sans preset et erreurs
  de chargement ;
- au LOT 28, l'écran **`FinanceParametrage`** (paramétrage du module
  Finance transverse) reçoit un **test dédié de 26 tests à 100 % de lignes
  / fonctions / branches** : tarifs horaires par formation (actifs puis
  inactifs badgés, colonne « tarif appliqué » formatée en fr-FR, « Non
  défini »), interrupteur et champs de marge de tolérance, douze champs de
  personnalisation des exports éditables et restitués, PATCH complet avec
  validation des tarifs (négatif refusé, virgule décimale acceptée, vide →
  null, coercition `Number() || 0`), répercussion des réponses serveur y
  compris sparse et `data:null`, état « Enregistrement… » par promesse
  différée, méta-audit avec ses trois cas dégradés, matrice FINANCE contre
  consultation seule (ENCADRANT) et persistance de la période partagée dans
  les liens du shell ;
- au LOT 29, l'écran **`FinanceAjustements`** (workflow des corrections
  manuelles sur séances) reçoit un **test dédié de 35 tests à 100 % de
  lignes / fonctions et 98,7 % de branches** : quatre KPI et filtres de
  statut côté client (avec compteur d'attente reporté sur la navigation),
  lignes détaillées (delta colorés, avant→après, badges de statut et repli
  neutre, motif de rejet tronqué, valideur, dates/auteurs), **valider** et
  **rejeter** (modale de motif obligatoire, états d'action par promesse
  différée, annulation sans appel, rechargement, deux niveaux d'erreur), et
  la **proposition** d'ajustement : recherche d'enseignant débordancée à
  300 ms (seuil de 2 caractères, spinner, annulation, réponses dégradées),
  séances du rapport finance filtrées sans date et triées par date
  décroissante, sélecteur verrouillé et ses trois libellés de repli,
  changement d'enseignant, payload exact en nombres avec motif élagué,
  état « Envoi… » ; les deux seules branches non couvertes sont le garde
  `motif vide` (rendu inaccessible par le bouton désactivé) et le résumé de
  modale pour un item disparu entre temps (inatteignable depuis l'UI) ;
- au LOT 30, l'écran **`FinanceDashboard`**, plus gros du module, reçoit un
  **test dédié de 29 tests à 99,8 % de lignes / 100 % de fonctions /
  97,2 % de branches** : les cinq KPI héro cliquables (formats durée/
  argent/pourcentage, sous-textes et badges d'évolution hausse/baisse/plat
  avec infobulle), les six KPI d'effectifs, l'alerte de tolérance et l'info
  tarifs, le **repli du coût prévisionnel** par somme des modules
  (null/chaîne vide/module sans montant), l'activité mensuelle en barres
  proportionnelles, le **forage des spécialités** (modale liste/vide,
  voile et stopPropagation), le **classement trois mesures** avec
  médailles et replis (onglet initial `?rank_tab=`, inconnu → réalisé,
  persistance dans la query partagée), la **synthèse de paie paginée** à
  25 lignes/page (suivante/numéros/précédente, réinitialisation après
  Appliquer, 13 colonnes, badges de tolérance ok/alerte/anomalie/écart/
  inconnu/absents, ligne lacunaire, état vide), et la **ventilation par
  module** ouverte par chaque KPI (cinq mesures avec tri, totaux, colonne
  tarif, recherche instantanée et total filtré/global, périodes sans
  module, singulier, trois fermetures), plus la période partagée
  (rechargement après Appliquer, persistence, période dégradée sans
  preset) ; les cinq branches résiduelles sont les aiguillages de
  formatage des helpers KPI figés par des tables de configuration
  statiques (format jamais sélectionnable par les données) ;
- au LOT 31, l'écran **`Equivalences`** (workflow des demandes
  d'équivalence/dispense) reçoit un **test dédié de 27 tests à 100 % de
  lignes / 100 % de fonctions / 100 % de branches** : chargement de la
  liste et des neuf badges de statut (crédits `null`/`0`/valeur avec tiret
  de repli), chargement parallèle des quatre référentiels **seulement pour
  les rôles acteurs** (`canActScolarite`) et son échec toasté, création en
  brouillon (payload typé `Number(x) || undefined`, y compris par soumission
  directe du formulaire, bouton verrouillé pendant l'envoi, erreur JSON puis
  message générique), les cinq transitions du workflow et l'absence de
  bouton sur les statuts terminaux/inconnus, la carte de **décision
  pédagogique** (valeurs par défaut FAVORABLE / autorité, champs vides
  omis, fermeture après succès, ouverte sur erreur), et **l'application**
  après `window.confirm` (annulation sans appel, succès/échec) ; les
  régressions §10.8 existantes (rendu puis application au clic) restent en
  place, le dossier `pages/scolarite/` passe à 90,0 % de lignes ;
- au LOT 32, l'écran **`MaquetteDetail`** (maquette pédagogique et ses
  UE/ECUE) reçoit un **test dédié de 35 tests à 100 % de lignes / 100 % de
  fonctions / 100 % de branches** : chargement parallèle maquette + journal
  et ses replis (titre sur `ref_formation`, tiret d'utilisateur, état
  « Aucune entrée. », date `fr-FR`), regroupement des UE par semestre,
  badges et alerte de cohérence ; matrice d'habilitation et de statuts
  (les contrôles et le référentiel des semestres n'existent que pour un
  brouillon ouvert à un rôle `canActScolarite`, l'échec du référentiel
  étant avalé en silence) ; les trois transitions **valider / activer /
  archiver** sous confirmation avec la réponse `problemes` de cohérence
  concaténée et les deux autres niveaux d'erreur, boutons verrouillés
  pendant l'appel ; le **clonage** versionné (annulation sans navigation,
  redirection `window.location.href`, échecs) ; l'**ajout d'UE** puis
  l'**ajout d'ECUE** (payloads typés `Number(...) || 0`, formulaires ECUE
  isolés par UE grâce au `focus`, coefficient 1 non éditable, réinitialisation
  et rechargement, formulaires conservés sur erreur) ; et l'**archivage
  d'ECUE** (DELETE `?mode=archive`, annulation, succès, deux niveaux
  d'erreur) — l'archivage avec confirmation confirme au passage le
  comportement figé au titre du §10.9 sur cet écran ;
- au LOT 33, l'écran **`ChargesEnseignants`** (charges pédagogiques des
  enseignants) reçoit un **test dédié de 23 tests à 100 % de lignes /
  100 % de fonctions / 96,9 % de branches après le LOT 34** : résolution de l'année
  académique courante au montage puis chargement parallèle de l'occupation
  et des anomalies (avec leurs paramètres, leurs états vides, l'alerte
  tronquée à 8 anomalies et les deux niveaux d'erreur), tableau
  d'occupation (badges OK/Surcharge), **détail d'un enseignant au clic**
  (charge puis affectations, ECUE absente en tiret, ligne
  `table-active`, échec), matrice d'habilitation (cinq référentiels et
  carte de création pour les seuls rôles `canActScolarite`, semestres
  filtrés par niveau, détail laissé consultable en lecture), et
  **création d'affectation** (payload typé complet avec `type_enseignement`
  « CM » par défaut, coercitions `Number(...) || undefined/0`, bouton
  verrouillé pendant l'envoi, réinitialisation partielle, rechargement
  global et du détail sélectionné, erreurs JSON/génériques) ; deux tests
  d'abord écrits en **`[écart §10.13]`** ont révélé le crash de la carte
  de création quand les référentiels échouent ou répondent après
  l'occupation ; **ce lot solde les cinq écrans Scolarité réparés au
  §10.8** (les deux seules branches non couvertes sont des filets
  défensifs inatteignables par l'UI) ;
- le **LOT 34, sur feu vert explicite, corrige le crash §10.13** par une
  seule modification de `ChargesEnseignants.jsx` (l'état initial `options`
  déclare désormais aussi `annees` et `formateurs`, soit toutes les clés
  lues au rendu) : les deux tests `[écart]` deviennent des **régressions**
  qui affirment le toast sans crash (occupation conservée, sélecteurs
  réduits à leur option fantôme) et la stabilité en cas de course de
  résolution ; les deux échouent sur l'ancien état initial (preuve de
  mutation par aller-retour) ;
- le **LOT 35 ouvre l'administration transverse avec `Referentiels.jsx`**
  (**56 tests, 99,7 % de lignes / 100 % de fonctions / 95,2 % de branches**,
  lot de tests purs, fichier produit non modifié, **aucun écart produit**) :
  les neuf onglets et leur chargement unique (spinner, erreur, réponse
  sparse, compteurs, état vide), la pagination 25/page et la lecture de
  `?tab=`, le CRUD des neuf collections avec payloads typés et valeurs par
  défaut, la bascule d'activation, la suppression via `ConfirmModal` avec
  le message 404 « déjà supprimée », la création de modules multi-formations
  (cases des formations actives, grille formation × catégorie, gardes,
  statut 200 vs 201, ancien format de volumes), les coercitions numériques
  (y compris des valeurs non numériques servies par le backend en édition)
  et l'import/export Excel (extension, ancre de téléchargement, bilan,
  erreurs) ; les quelques branches non couvertes sont des filets défensifs
  bornés par la whitelist des onglets ;
- le LOT 16 **achevait aussi la couverture fonctionnelle des campagnes
  d'admission** (`campagnesCompletion.test.jsx`, 19 tests après le LOT 17) :
  création en brouillon **avec quotas**, les quatre transitions de statut
  non couvertes par le LOT 8 (suspendre/clôturer/réouvrir/archiver, avec et
  sans confirmation), ajout d'épreuve (typage, salles, échec JSON),
  convocations, verrouillage, calcul et publication du classement, états
  « campagne fermée » ; le **LOT 17** y ajoute les régressions §10.11
  (quotas numérisés à la création, carte notes/actions de classement
  masquée en campagne fermée) ;
- le **moteur de tableaux/listes génériques** est couvert indépendamment des
  écrans : construction des requêtes/filtres (`listFilters`), pagination
  (`paginationPages`, `paginatedResponse`), formatage des erreurs (`apiErrors`),
  et les hooks associés (`useClientPagination`, `usePickerPagination`,
  `useListReturn`, `usePersistedListQuery`) ;
- composants réutilisables testés : `Pagination`, `ConfirmModal` et
  `formateurs/FormateurAssignPickerItem` (**100 %**, LOT 18) ; au LOT 20,
  `QRCodeModal` (95,8 %) et `TripleConfirmModal` (100 %) sont exercés en
  profondeur via les parcours de `ModuleDetail` ; aux LOTs 24 et 25,
  `ParticipantDetailModal` est **achevé à 98,8 % de lignes / 100 % de
  fonctions** (50 tests, lecture puis écritures) ; les autres composants ne
  sont exercés qu'indirectement via le smoke ;
- les **21 autres pages** sont couvertes en *smoke* (rendu) mais pas encore en
  *comportement métier* bout-en-bout (les quatre écrans du module Finance
  transverse en sont sortis aux LOTs 27 à 30, puis `Equivalences` au LOT 31,
  `MaquetteDetail` au LOT 32, `ChargesEnseignants` au LOT 33 et
  `Referentiels` au LOT 35).

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
   publication du classement, **parachevés au LOT 17 par les correctifs
   §10.11** (quotas, campagne fermée), la modale « Décider », les
   transitions, la création et l'application de `Equivalences` sont
   **couverts à 100 % au LOT 31**, le workflow maquette
   (valider/activer/archiver/cloner), l'ajout d'UE/ECUE et l'archivage de
   `MaquetteDetail` **au LOT 32**, et les charges pédagogiques
   (occupation, détail enseignant, création d'affectation) de
   `ChargesEnseignants` **au LOT 33** : **ce point est soldé**, les cinq
   écrans réparés au §10.8 ont tous leur test dédié en profondeur, et le
   crash §10.13 révélé au passage est **corrigé au LOT 34** ;
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
   encore d'un test de page. Dans le domaine présence qui écrit,
   **l'émargement de `ModuleDetail` est couvert aux LOTs 16, 18, 19 et 20 à
   90,2 % de lignes, fonctionnellement achevé** (cycle de vie des séances,
   `force-pointage`, badgeage en masse, inscriptions/retraits d'étudiants,
   **assignation d'enseignants réparée §10.12**, édition, superviseur,
   exports, **QR des séances au LOT 20**, **archivage à trois
   confirmations** et pagination serveur des pickers) ; l'écran miroir de
   niveau formation **`FormationDetail` est ouvert au LOT 21 puis achevé au
   LOT 22 à 98,4 % de lignes** (séances regroupées par module et leur cycle
   de vie, étudiants/enseignants paginés, encadrant, onglet Présences temps
   réel et forçage unitaire jour courant/passé, exports, QR, archivage
   depuis les groupes, import Excel SECRETARIAT) — **les deux fiches du
   domaine présence sont défendues de bout en bout**, et le **CRUD des
   participants `Participants` est verrouillé à 100 % au LOT 23** (liste,
   création, édition, suppression, détail, exports, habilitations), et sa
   fenêtre de détail `ParticipantDetailModal` est **achevée aux LOTs 24 et
   25** (98,8 % de lignes / 100 % de fonctions : lecture, moteur de
   décision, saisie de moyenne `bulk`, recalcul, exports relevé), et la
   **finance étudiante `FinancesEtudiantes` est verrouillée à 100 % au
   LOT 26** (échéanciers, paiements idempotents, confirmation sous
   preuve, habilitations), et le **rapport `FinanceEncadrants` est
   couvert à 100 % au LOT 27** (volumes horaires, période partagée,
   exports), et l'écran de **`FinanceParametrage` est verrouillé à 100 %
   au LOT 28** (tarifs, tolérance, exports, habilitations), et les
   **ajustements horaires `FinanceAjustements` sont verrouillés au LOT 29**
   (100 % lignes/fonctions : KPI/filtres, workflow valider/rejeter,
   proposition avec pickers débordancés), et le **tableau de bord
   `FinanceDashboard` achève le module Finance transverse au LOT 30**
   (99,8 % lignes / 100 % fonctions : KPI évolutifs, forages, classements,
   synthèse paginée, ventilation modale, période et `rank_tab` partagés) —
   **les quatre écrans Finance transverse ont désormais leur test dédié**,
   et les trois derniers écrans Scolarité réparés (`Equivalences`,
   `MaquetteDetail`, `ChargesEnseignants`) sont **verrouillés aux LOTs 31 à
   33, et les **référentiels de formation `Referentiels.jsx` sont
   verrouillés au LOT 35** (56 tests, 99,7 % de lignes). Restent les gros
   volumes internes `Users` (reste connu : branche « création d'un
   secrétariat à la volée ») et `Statistiques` (onglets, exports et widgets
   internes) ;
4. écarts encore ouverts, dans des lots dédiés :
   - ~~§10.12 bug bloquant de la modale d'**assignation d'un enseignant**
     (prop `enseignant`/`formateur`)~~ **corrigé au LOT 19** (alignement du
     nom de prop, parcours d'assignation bout-en-bout en régressions) ;
   - §10.1 `must_change_password` (**fonctionnalité** : parcours forcé, nouvelle
     route protégée, gestion au login et après `refreshUser`) — en attente d'un
     choix produit (blocage total ou lecture seule) ;
   - §10.9 retrait d'une ECUE pédagogique sans confirmation (cohérence UX avec
     les autres actions destructrices) — comportement figé par un test, en
     attente d'un choix produit ;
   - ~~§10.13 crash de la carte de création de `ChargesEnseignants` quand
     les référentiels échouent ou répondent après l'occupation (état
     initial `options` sans clé `formateurs`)~~ **corrigé au LOT 34** (état
     initial complet ; les deux tests `[écart]` du LOT 33 sont devenus des
     régressions) ;
   - ~~§10.10 boucle de rechargement sur échec de chargement (valeur de contexte
     Toast non mémoïsée)~~ **corrigé au LOT 13** (mémoïsation de la valeur du
     `ToastContext.Provider`, 4 régressions) — ne reste ouvert qu'au titre d'un
     choix produit éventuel sur la *forme* du retour d'erreur de chargement
     (toast transversale vs état d'erreur dédié dans la page) ;
   - ~~§10.11 deux constats mineurs sur les campagnes (quotas absents du
     formulaire de création, notes/classement actifs en campagne fermée)~~
     **corrigés au LOT 17** (champs quota ajoutés et numérisés, carte de
     saisie masquée sur campagne fermée, régressions dédiées) ;
5. composants partagés (modales, pickers, badges, panneaux de flux) ;
6. montée progressive du plancher de couverture global (§7) et extension aux
   pages encore couvertes seulement en smoke ; option : durcir le smoke
   (§6.3/§10.8) pour exiger un contenu minimal et non plus seulement « pas de
   crash ».
