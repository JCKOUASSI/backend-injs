RÈGLES CLINE — WORKSPACE INJS-LMD

1. IDENTITÉ DU PROJET

Ce workspace est exclusivement le projet INJS-LMD.

Racine du projet : racine du dépôt (chemins toujours relatifs, jamais absolus).

Architecture principale :

* backend/ : Django + Django REST Framework
* frontend/ : React + Vite
* qr_badge_mobile/ : application mobile
* docs/ : documentation
* scripts/ : scripts techniques et sauvegardes
* .clinerules/ : règles de fonctionnement de Cline

Le projet ne doit pas être confondu avec les anciennes versions du produit (applications antérieures de badgeage et de gestion de formation), dont aucune interface ne doit être réintroduite.

⸻

2. RÈGLE FONDAMENTALE

PRÉSERVER L’EXISTANT.

Avant toute modification :

1. comprendre l’architecture existante ;
2. rechercher les dépendances ;
3. identifier les fichiers concernés ;
4. éviter toute modification inutile ;
5. privilégier les corrections minimales et ciblées.

Ne jamais réécrire massivement un fichier simplement parce qu’une autre architecture semble plus simple.

⸻

3. BACKEND

Backend principal :

backend/

Configuration Django :

* backend/config/settings.py
* backend/config/urls.py

Les applications métier existantes doivent être conservées.

Avant de modifier une architecture Django existante :

* rechercher les modèles concernés ;
* rechercher les serializers ;
* rechercher les views/viewsets ;
* rechercher les URLs ;
* rechercher les tests ;
* vérifier les migrations ;
* vérifier les dépendances frontend.

Ne jamais supprimer une application Django existante sans autorisation explicite.

⸻

4. FRONTEND

Frontend principal :

frontend/

Technologies :

* React
* Vite
* JavaScript/JSX

Entrées principales :

* frontend/src/main.jsx
* frontend/src/App.jsx

Avant toute modification importante de App.jsx :

1. analyser son contenu ;
2. identifier les composants existants ;
3. identifier les routes ;
4. identifier les appels API ;
5. préserver les fonctionnalités existantes.

Ne jamais remplacer massivement App.jsx sans justification et autorisation explicite.

⸻

5. IDENTITÉ VISUELLE INJS

L’application doit rester visuellement cohérente avec l’identité INJS.

Ne pas remplacer arbitrairement :

* logo INJS ;
* couleurs ;
* navigation ;
* libellés métier ;
* terminologie LMD ;
* composants existants.

Ne jamais réintroduire volontairement une interface provenant d’une des anciennes applications du produit.

⸻

6. BASE DE DONNÉES OFFICIELLE DU DÉVELOPPEMENT

Base PostgreSQL actuellement utilisée par le projet :

injs_lmd_current

Connexion locale :

* Host : 127.0.0.1
* Port : 5432
* Database : injs_lmd_current
* User : injs_user

PostgreSQL utilisé actuellement :

PostgreSQL 16 — Homebrew

La base Docker située sur le port 5436 est une instance différente.

Ne jamais confondre :

127.0.0.1:5432 → PostgreSQL INJS-LMD local

avec :

127.0.0.1:5436 → PostgreSQL Docker

⸻

7. PROTECTION ABSOLUE DE LA BASE

Les opérations suivantes sont INTERDITES sans confirmation explicite de l’utilisateur :

* DROP DATABASE
* DROP TABLE
* TRUNCATE
* DELETE massif
* manage.py flush
* réinitialisation complète de la base
* suppression de données de démonstration
* restauration destructive d’un dump
* changement de base de données
* suppression de volumes PostgreSQL

Ne jamais exécuter :

docker compose down -v

sans autorisation explicite.

Ne jamais supprimer un volume PostgreSQL pour résoudre un problème applicatif.

⸻

8. DONNÉES DE DÉMONSTRATION

Les données de démonstration sont considérées comme des données importantes du projet.

Les comptes démo doivent être préservés.

Le fichier :

backend/seed_data.py

ne constitue PAS une autorisation de réinitialiser la base.

Ne jamais :

* supprimer les comptes démo ;
* modifier leurs mots de passe ;
* changer leurs rôles ;
* supprimer leurs données associées ;

sans demande explicite de l’utilisateur.

Toute modification de seed_data.py doit être analysée avec attention afin d’éviter une réinitialisation involontaire.

⸻

9. SAUVEGARDE POSTGRESQL

Script officiel :

scripts/backup_injs_lmd.sh

Il sauvegarde :

injs_lmd_current

vers :

~/Backups/INJS-LMD/database/

Avant toute opération importante susceptible de modifier massivement la base, exécuter :

scripts/backup_injs_lmd.sh

La sauvegarde doit être vérifiée avant de poursuivre.

Le script produit également un SHA-256.

⸻

10. SAUVEGARDES EXISTANTES

Une sauvegarde historique importante existe :

injs_lmd_avant_reinitialisation_2026-08-29.dump

Elle est conservée hors du dépôt Git dans :

~/Backups/INJS-LMD/database/

Ne jamais supprimer cette sauvegarde sans autorisation explicite.

⸻

11. GIT — PROTECTION DU CODE

Le dépôt Git constitue le mécanisme principal de restauration du code.

Avant une modification importante :

* vérifier git status ;
* identifier la branche ;
* vérifier les modifications existantes.

Ne jamais exécuter sans autorisation explicite :

* git reset --hard
* git clean -fd
* git checkout .
* suppression massive de fichiers
* réécriture de l’historique Git
* git push --force

Ne jamais écraser des modifications utilisateur existantes.

Si des modifications non commitées sont détectées :

les préserver et demander confirmation avant toute opération risquant de les écraser.

⸻

12. CHECKPOINTS GIT

Après une modification importante et validée :

1. exécuter les tests ;
2. exécuter :

git diff --check

3. examiner :

git diff

4. demander confirmation avant un commit si la modification est substantielle.

Les commits doivent être explicites et descriptifs.

⸻

13. MODE PLAN

En mode PLAN :

* analyser ;
* rechercher ;
* expliquer ;
* identifier les fichiers concernés ;
* proposer une stratégie ;
* ne pas effectuer de modification destructive.

Pour une tâche complexe, fournir :

1. diagnostic ;
2. fichiers concernés ;
3. stratégie ;
4. risques ;
5. tests prévus.

⸻

14. MODE ACT

En mode ACT :

* appliquer uniquement les modifications nécessaires ;
* ne pas élargir inutilement le périmètre ;
* conserver les fonctionnalités existantes ;
* effectuer les tests appropriés ;
* vérifier les différences Git.

Après modification :

git diff --check

doit être exécuté.

⸻

15. COMMANDES DANGEREUSES

Les commandes suivantes nécessitent une confirmation explicite :

* rm -rf
* git reset --hard
* git clean
* DROP DATABASE
* DROP TABLE
* TRUNCATE
* DELETE sans condition précise
* manage.py flush
* suppression de migrations existantes
* suppression de volumes Docker
* docker compose down -v
* restauration destructive PostgreSQL

En cas de doute :

NE PAS EXÉCUTER.

Demander confirmation.

⸻

16. MIGRATIONS DJANGO

Ne jamais supprimer ou réécrire arbitrairement les migrations existantes.

Avant une migration :

1. analyser les modèles ;
2. vérifier les migrations existantes ;
3. vérifier l’état de la base ;
4. générer la migration ;
5. examiner la migration ;
6. appliquer la migration seulement après validation.

Ne jamais utiliser une migration comme moyen de supprimer des données sans justification explicite.

⸻

17. TESTS

Après toute modification significative :

* vérifier le backend ;
* vérifier le frontend concerné ;
* vérifier les API concernées ;
* exécuter les tests disponibles ;
* vérifier les erreurs console ;
* vérifier les migrations si concernées.

Ne pas considérer une modification comme terminée simplement parce que le fichier a été modifié.

⸻

18. SERVEURS LOCAUX

Backend Django :

http://127.0.0.1:8000

Frontend Vite :

http://localhost:3000

Ne pas modifier les ports existants sans nécessité.

Ne pas démarrer inutilement plusieurs instances concurrentes du même serveur.

⸻

19. OLLAMA / CLINE

Ollama local :

http://127.0.0.1:11434

Modèles disponibles :

* qwen3:4b
* qwen2.5-coder:7b
* qwen2.5-coder:3b

Configuration Cline recommandée :

PLAN :

* Provider : Ollama
* Base URL : http://127.0.0.1:11434
* Model : qwen3:4b

ACT :

* Provider : Ollama
* Base URL : http://127.0.0.1:11434
* Model : qwen2.5-coder:7b

⸻

20. UTILISATION DES OUTILS

Avant de modifier un fichier :

* le lire ;
* comprendre son contexte ;
* rechercher ses références ;
* modifier uniquement ce qui est nécessaire.

Ne pas modifier plusieurs systèmes simultanément sans nécessité.

Ne pas effectuer de refactorisation générale lorsqu’une correction ciblée suffit.

⸻

21. EN CAS D’INCERTITUDE

Si une opération risque :

* de supprimer des données ;
* de modifier massivement le code ;
* de changer l’architecture ;
* de modifier PostgreSQL ;
* de supprimer des fichiers ;
* de changer les comptes démo ;
* de changer les migrations ;

STOP.

Présenter le risque à l’utilisateur et demander confirmation.

⸻

22. PRIORITÉ DES RÈGLES

Ordre de priorité :

1. sécurité des données ;
2. préservation du code existant ;
3. respect de l’architecture INJS-LMD ;
4. correction du problème demandé ;
5. tests ;
6. optimisation/refactorisation.

Une optimisation ne doit jamais sacrifier la stabilité.

⸻

23. RÈGLE FINALE

MIEUX VAUT DEMANDER CONFIRMATION QUE DÉTRUIRE UNE DONNÉE.

Le workspace INJS-LMD doit rester récupérable à tout moment grâce à :

* Git ;
* sauvegardes PostgreSQL ;
* dumps vérifiés ;
* modifications minimales ;
* tests ;
* checkpoints.

Toute action destructive ou irréversible doit être explicitement autorisée par l’utilisateur.