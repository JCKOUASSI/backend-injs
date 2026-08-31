# INJS-LMD — Règles de travail Cline

## 1. Projet
- Le workspace est l'application INJS-LMD.
- Ne jamais remplacer ce projet par une ancienne application SYGEP-CPFAE, QR-Badge ou une autre version.
- Respecter prioritairement l'architecture et les fonctionnalités déjà présentes dans le workspace.
- Avant toute modification importante, inspecter le code existant et comprendre les dépendances.

## 2. Architecture
- Backend : Django + Django REST Framework dans `backend/`.
- Frontend : React + Vite dans `frontend/`.
- Application mobile : `qr_badge_mobile/`.
- Documentation : `docs/`.
- Scripts : `scripts/`.
- Configuration Django principale : `backend/config/settings.py` et `backend/config/urls.py`.
- Entrée principale React : `frontend/src/main.jsx`.
- Application React principale : `frontend/src/App.jsx`.

## 3. Méthode de travail
Toujours suivre cette séquence :
1. Inspecter.
2. Comprendre.
3. Proposer un plan court.
4. Modifier uniquement les fichiers nécessaires.
5. Vérifier les erreurs.
6. Tester lorsque c'est possible.
7. Résumer précisément les changements effectués.

## 4. Protection du projet
NE JAMAIS exécuter sans confirmation explicite :
- `git reset --hard`
- `git clean -fd`
- suppression massive de fichiers
- `git checkout` ou `git restore` visant à écraser des modifications locales
- migrations destructives
- suppression ou réinitialisation de la base de données
- commandes pouvant détruire des données.

Ne jamais supprimer ou modifier la sauvegarde :
`injs_lmd_avant_reinitialisation_2026-08-29.dump`
sans demande explicite.

## 5. Git
- Ne jamais effectuer automatiquement de `git push`.
- Ne jamais modifier l'historique Git sans confirmation.
- Avant toute opération Git potentiellement destructive, afficher la commande proposée et demander confirmation.
- Préserver les modifications locales existantes.

## 6. Base de données
- Ne pas réinitialiser la base de données pour résoudre un problème de code.
- Ne pas supprimer des données de production ou de développement sans confirmation.
- Avant une migration complexe, analyser les modèles et migrations existants.
- Privilégier les migrations réversibles et les vérifications préalables.

## 7. Code
- Modifier le minimum nécessaire.
- Ne pas réécrire un fichier entier lorsqu'une modification ciblée suffit.
- Ne pas créer de doublons de modèles, routes, composants ou services.
- Réutiliser les fonctions et composants existants lorsqu'ils conviennent.
- Respecter les conventions déjà utilisées dans le projet.
- Ne pas introduire une nouvelle bibliothèque lorsque la fonctionnalité peut être réalisée avec l'existant.

## 8. INJS-LMD
Les fonctionnalités INJS-LMD existantes sont prioritaires, notamment :
- Scolarité LMD
- Candidatures
- Admissions
- Inscriptions
- Groupes pédagogiques
- Formations
- Modules
- Référentiels
- Notes et évaluations
- Présences
- EDT
- statistiques
- exports.

Ne pas modifier une règle métier existante sans analyser ses usages et ses dépendances.

## 9. Frontend
- Préserver l'identité visuelle INJS existante.
- Ne pas remplacer le logo ou les éléments visuels par ceux d'une ancienne application.
- Vérifier les routes et les rôles avant de modifier la navigation.
- Éviter les changements globaux lorsqu'une correction locale suffit.

## 10. Backend
- Respecter les modèles Django existants.
- Respecter les serializers, services, permissions, URLs et vues existants.
- Pour une logique métier complexe, privilégier les services existants plutôt que de dupliquer la logique dans les vues.
- Vérifier les relations entre modèles avant de modifier une logique métier.

## 11. Tests et vérification
Après une modification :
- vérifier les erreurs Python lorsque pertinent ;
- vérifier les imports ;
- vérifier les routes concernées ;
- vérifier le frontend lorsque concerné ;
- lancer les tests existants lorsque possible ;
- ne pas considérer une modification comme terminée simplement parce qu'elle compile.

## 12. Commandes terminal
- Utiliser des commandes ciblées et réversibles.
- Avant une commande potentiellement destructive, demander confirmation.
- Ne pas lancer plusieurs opérations risquées dans une seule commande.
- Ne pas démarrer ou arrêter inutilement les serveurs déjà fonctionnels.

## 13. Communication
- Expliquer brièvement ce qui sera fait avant une modification importante.
- Signaler clairement les fichiers modifiés.
- Signaler les tests effectués et leur résultat.
- Si une information manque, demander plutôt que deviner.
- Ne jamais prétendre avoir exécuté un test qui n'a pas réellement été exécuté.
