# Garde-fous du chantier INJS-LMD

> Introduits par **P00-08 [LOT 0]**. Ces trois dispositifs protègent la
> refonte contre les régressions silencieuses et les changements d'API non
> maîtrisés. **Aucun prompt ultérieur ne doit les affaiblir** ; plusieurs
> prompts des lots suivants explicitent d'ailleurs « *smoke_test_injs toujours
> vert* » comme critère de fin.

| # | Dispositif | Commande / écran | Rôle |
|---|------------|------------------|------|
| 1 | **Feature flags** | écran *Fonctionnalités* (`/parametres/flags`) + `GET /api/parametres/flags/` | Activer/désactiver un comportement nouveau sans redéploiement, avec effet immédiat et historique |
| 2 | **Contrat d'API figé** | `manage.py export_api_contract --check` (CI) | Détecter toute rupture de route / paramètre / clé de réponse |
| 3 | **Parcours de fumée** | `manage.py smoke_test_injs` (CI) | Rejouer la chaîne académique complète de bout en bout sur données auto-ensemencées |
| 4 | **Zéro `print()` runtime** (P00-05) | `manage.py check_repo_hygiene` (CI, étendu) | Interdire les sorties `print()` dans le code Django ; logging structuré obligatoire |

---

## 1. Feature flags

- 13 flags livrés **désactivés** : un par LOT 1 → 12, plus
  `flag.g2_niveaux_n4_validation` (surcharge propre au gate G2).
- Ils **ne pilotent encore aucun comportement** à P00-08 : ils sont livrés
  éteints, et chaque lot qui introduit un comportement nouveau doit
  (a) brancher son flag, (b) livrer le comportement old-style quand le flag
  est OFF, (c) tester les deux états.
- Réglage par l'écran admin *Fonctionnalités* ; chaque bascule est historisée
  (qui, quand, ancienne/valeur nouvelle) et prise en compte immédiatement, y
  compris côté front (invalidation du cache React Query via `useFlag`).
- Règle : **jamais de basculement big-bang** ; un flag ne peut être retiré
  qu'une fois le comportement validé en production, dans un prompt dédié.

## 2. Contrat d'API (`docs/api/contract.snapshot.json`)

- Snapshot produit par drf-spectacular, normalisé par `config/api_contract.py`
  (392 paths / 529 routes au gel initial). Objet = dictionnaire de clés,
  tableau = `{"[]": sous-arbre}`, feuille = `null` ; clés triées, indentation 2.
- **Rupture** (le `--check` échoue) : retrait ou renommage d'une route, d'un
  paramètre, d'une clé de requête *requise*, d'un code de réponse HTTP ou
  d'une clé de réponse (à toute profondeur, y compris dans les tableaux).
- **Ajout autorisé** : routes, paramètres optionnels, clés de réponse
  nouvelles — le snapshot reste vert, on le régénère.
- En cas de rupture **voulue** :
  1. `manage.py update_api_contract --justification "…"` (régénère le
        snapshot et horodate le changement) ;
  2. la justification est tracée dans `docs/api/CHANGELOG_CONTRAT.md` ;
  3. le front (et le mobile, le cas échéant) est adapté dans le même lot.
- **Limite connue** : les vues sans serializer déclaré (ex.
  `presences/stats_api.py` — vue `taux`, `POST /api/auth/login/`) n'exposent
  pas leurs clés de réponse à drf-spectacular ; ces clés ne sont donc pas
  figées par le contrat. Ne pas s'en servir comme prétexte pour y introduire
  des ruptures : y ajouter des serializers dédiés relève d'un lot ultérieur.

## 3. Parcours de fumée `smoke_test_injs`

Commande : `backend/scolarite/management/commands/smoke_test_injs.py`.

- **Auto-ensemencement** : crée son propre jeu de démo (année 2026-2027,
  formation/niveau/parcours, maquette ACTIVE, UE/ECUE, formation
  opérationnelle, campagne, étudiant, acteurs) — aucun fixture externe.
- **23 étapes** `SMOKE-NN-*`, recettes reprises des tests existants
  (`scolarite/tests/test_parcours_complet.py`,
  `admissions/tests/test_admissions.py`, `jurys/tests/test_workflow_api.py`,
  `graduation` et `finances_etudiantes`) :

  ```
  01 campagne → 02 candidature → 03 pièces → 04 admissibilité (épreuves/notes/classement)
  → 05 admission (ADMIS) → 06 inscription administrative → 07 matricule (INJS26-0001)
  → 08 inscriptions pédagogiques → 09 groupe → 10 maquette/UE/ECUE
  → 11 passerelle modules opérationnels → 12 séance → 13 jeton QR → 14 pointage
  → 15 notes → 16 moyennes → 17 jury (calcul → décision → VERROUILLE)
  → 18 diplôme validé (PDF + empreinte SHA-256)
  → 19 tarifs → 20 échéancier → 21 facture → 22 paiement idempotent → 23 quittance
  ```

- **Idempotence / sûreté en CI** : par défaut, tout le parcours s'exécute dans
  une transaction **annulée en fin** (`transaction.set_rollback(True)`). La
  commande ne laisse aucune trace et peut être rejouée à l'infini sur une base
  neuve de CI. Code de sortie non nul + tableau récapitulatif à la première
  étape défaillante.
- **Base réelle** : l'option explicite `--persist` conserve les données
  (démonstration). Elle n'est jamais utilisée en CI. Sur une base déjà
  peuplée, le mode par défaut peut légitimement échouer sur des contraintes
  d'unicité (ex. année courante) : c'est un dispositif pour base neuve ; pour
  une base de démo existante, utiliser `--persist` en connaissance de cause.
- La smoke **n'introduit aucune règle métier nouvelle** : elle ne fait
  qu'emprunter les services officiels. Elle ne remplace pas les tests
  unitaires/intégration (périmètre réduit à un heureux chemin) ; en revanche
  les tests unitaires ne peuvent pas se substituer à elle.

### Correctif P00-08 livré avec la smoke

La smoke a révélé deux anomalies du chemin de succès des finances (testées
désormais par `finances_etudiantes/tests/test_paiements.py`) :

1. `enregistrer_paiement_idempotent` ne remplissait pas la clé générique
   obligatoire `Paiement.content_type/object_id` → tout paiement réel échouait
   sur contrainte NOT NULL ;
2. `confirmer_paiement` créait la `Quittance` sans sa `date_echeance`
   obligatoire → la confirmation échouait à son tour.

Les deux sont corrigés (source polymorphe renseignée depuis l'étudiant ou le
candidat ; `date_echeance` = jour de la confirmation, surchargeable).

## 4. Zéro `print()` dans le runtime (P00-05)

- La commande `check_repo_hygiene` (job Backend, avant les tests) détecte par
  **analyse AST** tout appel au *builtin* `print()` dans le code Python du
  runtime versionné (`backend/**.py` : apps, `config`, modules racine,
  **commandes de gestion comprises**). Elle ignore les commentaires,
  docstrings et chaînes (donc un identifiant comme `…fingerprint(`), ainsi que
  les redéfinitions locales de `print` (paramètre, import, fonction).
- Sorties attendues à la place :
  - code applicatif (vues, services, modèles, signaux…) :
    `logger = logging.getLogger(__name__)` puis `logger.debug/info/warning/…`,
    la configuration `LOGGING` de `config/settings.py` émet en console en
    DEBUG et dans le fichier rotatif `logs/injs_lmd.log` (niveau WARNING) hors
    DEBUG ;
  - commandes de gestion : `self.stdout.write(...)` / `self.stderr.write(...)`
    (jamais `print`, qui contourne la redirection et le style Django).
- **Périmètre exclu, par construction et de façon explicite** (listé dans la
  constante `RUNTIME_EXCLUDED_ROOT_SCRIPTS` et les règles de la commande) :
  - les **scripts manuels d'import / reprise / génération** :
    `backend/scripts/*.py` et les scripts historiques à la racine de `backend/`
    (`seed_data.py`, `count_*.py`, `extract_*.py`, `generate_*.py`,
    `analyze_edt.py`, `analyse_dossier.py`, `verify_import_files.py`,
    `build_import_from_donnees.py`). Ce sont des CLI opérateur hors runtime
    serveur, dont la sortie console est la fonction même ; ils portent un
    en-tête normalisé « Script manuel HORS RUNTIME Django (P00-05) » ;
  - les tests (les affichages n'y ont de toute façon aucun effet utile) et les
    migrations (fichiers historiques figés, jamais retouchés).
- Côté frontend, les `console.log` hors tests sont également proscrits ; ESLint
  et les revues s'appliquent (aucun résidu au jour du P00-05).

### Observabilité / Sentry

La baseline initiale relevait l'absence de Sentry. Le rattachement d'un
agrégateur d'erreurs SaaS est un **actif d'infrastructure DSI** (DSN,
conservation, chiffrement, hébergement des données) au même titre que P00-07 ;
il n'est pas câblé dans le code applicatif tant que la DSI ne fournit pas le
DSN et le cadre contractuel. En attendant, la configuration `LOGGING`
(console + fichier rotatif `logs/injs_lmd.log`, 5 Mo × 5) constitue
l'observabilité locale. Aucune dépendance `sentry-sdk` ne doit être ajoutée
sans prompt dédié et feu vert explicite.

## 5. Journal d'audit unifié `core` (P01-01)

- Nouvelle application **`core`** (LOT 1) portant le registre d'audit
  transverse `core.EvenementAudit` : append-only strict (création seule ;
  modification et suppression interdites par le modèle, le queryset et
  l'admin Django, qui est en lecture seule).
- Chaque événement possède un **code métier unique et atomique**
  `AUDIT-AAAAMMJJ-NNNNNN` (séquence continue remise à zéro chaque jour),
  généré sous verrou (`CompteurCode` + `select_for_update`, reprise sur
  collision testée ; la concurrence réelle est vérifiée par un test
  conditionné PostgreSQL).
- Les journaux applicatifs existants **restent la référence dans leur app et
  ne sont pas modifiés** : `presences.AuditLog`, `scolarite.JournalScolarite`,
  `referentiels.ReferentielJournal` (les 3 apps pilotes). Quand le flag LOT 1
  est activé, chaque entrée créée est dupliquée **une seule fois** dans core
  par des signaux (contrainte d'idempotence sur `(source, source_entree_id)`,
  horodatage d'origine conservé). Flag OFF (livraison) : aucun signal
  n'écrit, comportement strictement identique à l'avant P01-01.
- **API** `GET /api/core/audit/` et `GET /api/core/audit/<code>/`, lecture
  seule, avec filtres (`source`, `action`, `acteur`, `date_debut/date_fin`,
  recherche `objet`). Autorisée uniquement aux rôles validés au cadrage :
  ADMIN, DIRECTION, CHEF_CPFAE_ADMIN, CPFAE_ADMIN (N4) + AUDITEUR et ARCHIVE
  (N1). Les autres rôles gardent les journaux métier ciblés existants ;
  l'API répond 403 tant que le flag est OFF (y compris pour les admins).
- **Commande** `manage.py audit_integrity_check` (CI, après la smoke) :
  vérifie en lecture seule les doublons de codes, les séquences trouées, les
  compteurs incohérents, les répliques dupliquées et les orphelines ; code 1
  sur la moindre anomalie.

## 6. Aperçu Arena : ports figés et admin en iframe (anti-403 CSRF)

- **Ports canoniques, invariables jusqu'à la fin du projet** : frontend Vite
  sur **3000**, API Django sur **8000**. `frontend/vite.config.js` impose
  `port: 3000` + **`strictPort: true`** (Vite échoue plutôt que de basculer
  sur un autre port — notamment plus jamais le port par défaut 5173, qui fut
  un contournement ponctuel d'incident). Si un port est occupé, on le libère,
  on ne déplace pas le serveur. Lanceurs idempotents :
  `arena/lancer-front.sh`, `arena/lancer-api.sh`. Après une réinitialisation :
  `bash arena/bootstrap.sh` puis les deux lanceurs.
- **Admin Django en iframe https cross-site** : le proxy Arena termine le
  TLS. L'overlay `arena/settings_sandbox.py` (et son générateur `bootstrap.sh`,
  pour survivre aux resets) porte en dur :
  - `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` ;
  - `SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = 'None'` ;
  - `SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True` ;
  - **noms de cookies dédiés** `injs_csrftoken` / `injs_sessionid` : un vieux
    cookie `csrftoken` hérité dans le navigateur (mauvaise longueur, datant
    d'avant le durcissement) provoquait « Interdit (403) — vérification CSRF »
    ; le renommage rend cette collision impossible. Le refresh JWT du front
    utilise son propre cookie `refresh_token` (inchangé).
- **L'admin s'ouvre via le proxy Vite (port 3000), pas seulement via 8000** :
  dans l'aperçu, l'URL `https://3000-<sandbox>.e2b.app/admin/…` transite par
  Vite qui relaie vers Django. Le proxy Arena transmet (ou fait défaut sur)
  **`X-Forwarded-Proto: http`** alors que la navigation est en HTTPS : Django
  se croyait en HTTP et émettait des cookies `Secure` que le navigateur
  refusait en iframe → « CSRF cookie not set » (cause réelle du 403 du
  2026-09-13, vérifiée par capture d'en-têtes, PAS un blocage de cookies
  tiers). `frontend/vite.config.js` (`forwardHeaders`) force donc `https`
  dès que l'hôte public transmis correspond à `*.e2b.app`
  (override `VITE_FORCE_HTTPS=1` possible). Test gardé :
  `test_vite_force_https_derriere_proxy_e2b`.
- Ces réglages ne vivent **que dans l'overlay d'aperçu** (jamais dans
  `config/settings.py`, qui garde les défauts de production Lax/non sécurisés
  selon l'environnement). Un test les fige :
  `config/tests/test_apercu_hardening.py` (overlay + bootstrap + ports +
  forçage https Vite).
- Cas résiduel non contournable côté serveur : un navigateur en politique de
  cookies tiers **stricte** peut refuser tout cookie d'iframe ; ouvrir alors la
  vignette API dans un onglet dédié (cookie première partie).

---

## Bruit de fond connu (ne pas « réparer » hors prompt dédié)

- **SQLite** : `referentiels…test_regle4_doublon_libelle_casse_rejete` échoue
  sous SQLite mais passe sous PostgreSQL (sensibilité à la casse des
  classements). La CI reste la référence sur PostgreSQL ; ne pas modifier la
  migration 0086 pour contourner ce point.
- Les avertissements drf-spectacular sur les vues non typées sont du bruit
  baseline (voir limite du contrat ci-dessus).
- Le gate **Flutter (R6)** ne peut pas être levé dans ce dépôt (outillage DSI
  / P00-07) : son échec en CI est attendu et documenté.
