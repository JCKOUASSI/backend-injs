# Sécurité des données nominatives et hygiène du dépôt (P00-02)

Application INJS-LMD 2026 — ce document décrit la politique de versionnement des données,
l'inventaire réalisé le 2026-09-11 et la procédure (différée) de nettoyage de l'historique Git.

## 1. Règle générale

- Les **données nominatives** (noms de participants, auditeurs, étudiants, formateurs ;
  adresses e-mail, téléphones, dates/lieux de naissance, coordonnées bancaires) **ne sont pas
  versionnées** dans Git.
- Le dépôt ne contient que du code, de la documentation et des **modèles d'import vides**
  (en-têtes + une ligne d'exemple fictive), dans [`modeles/`](modeles/).
- Les artefacts de build (`staticfiles/`), bases locales (`*.sqlite3`), secrets (`.env`,
  `assets/app.env`) et classeurs d'import (`*.xlsx`, `*.csv`, `*.numbers`, `importverif/`) sont
  ignorés (`.gitignore`).
- Exception admise : la fixture **synthétique** de tests `backend/test_import_formations_seances.xlsx`
  (générée par `backend/scripts/generate_test_import.py`, sans donnée nominative), exigée par la
  suite de tests.

## 2. Inventaire du 2026-09-11

### (a) Modèles vides conservés → `docs/modeles/`
- `modele_formations.csv`, `modele_formateurs.csv`, `modele_participants.csv`, `modele_seances.csv`
  (en-têtes + 1 ligne d'exemple fictive non nominative). Génération Excel :
  `python backend/scripts/generate_import_template.py` (désormais orienté vers `docs/modeles/`).

### (b) Données nominatives sorties du suivi Git (conservées sur le disque de travail)
| Fichier (sous `backend/`) | Type | Usage |
|---|---|---|
| `LISTE DES FORMATEURS FAB 2026 - 19-04-2026.numbers` | nominatif (formateurs) | liste réelle, hors dépôt |
| `import_formateurs.xlsx`, `import_formations.xlsx` | données d'import réelles | `manage.py import_excel` / API d'import |
| `import_participants.xlsx`, `import_participants.csv` | nominatif (auditeurs) | import participants |
| `import_seances.xlsx` | séances réelles | import emploi du temps |
| `modele_formateurs.csv`, `modele_formations.csv`, `modele_participants.csv`, `modele_seances.csv` (exemplaires `backend/`) | exemples avec données | remplacés par les modèles de `docs/modeles/` |
| `importverif/` (5 classeurs, dont `FAB A4 OPHIR.xlsx`, `corrige/`) | vérifications réelles | tests de ré-import (les tests s'auto-passen si absents) |

### (c) Artefacts de build sortis du suivi
- `backend/staticfiles/` (1 175 fichiers, ~18 Mo) : généré au build par `collectstatic`
  (Docker backend). Il reste produit localement / en image, mais n'est plus versionné.

### Commande de contrôle
```bash
python backend/manage.py check_repo_hygiene   # sort en code 1 si une donnée interdite réapparaît
```
Branchée dans la CI (job **Backend**, avant les migrations/tests).

## 3. Ne casse ni les imports ni les builds

- Les imports lisent un fichier **fourni à l'exécution** (argument de `import_excel`, ou
  upload via l'API) : aucun chemin de fichier réel n'est codé en dur vers le dépôt.
- Les deux tests qui s'appuyaient sur `importverif/` se passent proprement
  (`skipTest('fichiers de vérification absents')`) quand ces données réelles ne sont pas présentes
  (typiquement en CI / clone neuf).
- La fixture synthétique `test_import_formations_seances.xlsx` reste suivie pour les tests
  pipelines (`test_full_pipeline_dry_run`, cohérence).
- `collectstatic` reste exécuté à la construction de l'image Docker backend ; le fait de ne plus
  suivre `staticfiles/` ne change pas le runtime.

## 4. Nettoyage de l'historique Git (opération DIFFÉRÉE, à planifier)

Défaire le suivi des fichiers ne les retire **pas de l'historique**. Les données nominatives y
restent présentes dans les anciens commits. Un nettoyage d'historique est une opération sensible,
à mener séparément et en coordination.

Prérequis :
1. **Sauvegarde complète et vérifiée** du dépôt (miroir `git clone --mirror`) et des données.
2. Décision/accord de la Direction et de la DSI ; communication à tous les développeurs (arrêt
   des travaux sur les branches existantes).
3. Relevé exhaustif des chemins à purger (jeux `import_*`, `*.numbers`, `importverif/`,
   `staticfiles/`, tout ancien secret).

Procédure recommandée (hors bande, sur un clone de maintenance) :
```bash
# Outil : git-filter-repo (à préférer à filter-branch)
pip install git-filter-repo
git clone --mirror <URL_DU_DEPOT> depot-miroir.git
cd depot-miroir.git
git filter-repo \
  --path-glob 'backend/import_*.xlsx' \
  --path-glob 'backend/import_*.csv' \
  --path-glob 'backend/modele_*.csv' \
  --path-glob 'backend/*.numbers' \
  --path-glob 'backend/importverif/*' \
  --path backend/staticfiles \
  --invert-paths
# Vérification : aucun résultat attendu
git log --all --full-history -- 'backend/importverif/*' '**/*.numbers'
```
Après purge :
- réécrire les tags si besoin ; **forcer la mise à jour** du dépôt central (les identifiants de
  commits changent toutes les références) ;
- **invalider tous les clones existants** (re-clonage obligatoire, les anciens clones contiennent
  les données) ;
- considérer comme **compromis tout secret ayant été commité** : rotation des clés/mots de passe
  (même après purge) ;
- mettre à jour les intégrations, PR ouvertes et environnements de CI.

Risques : perte de références (numéros de commits, liens), réécriture des PR, travail non poussé
écarté, nécessité de re-cloner. Cette opération n'est **jamais** exécutée par l'agent sans ordre
explicite et prérequis vérifiés (règle 3 / règle 21 des règles maîtresses).

## 5. Vérification continue

- `check_repo_hygiene` en CI empêche toute réintroduction suivie.
- Les données réelles sont à déposer hors dépôt (répertoire local non versionné ou stockage
  sécurisé), et importées à la demande via les commandes/API prévues.
