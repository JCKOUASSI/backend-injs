# Manuel Utilisateur Institutionnel — QR Badge (Plateforme Web)
**MEMFPMA — DFRC / CPFAE**  
*Système de gestion des présences par QR Code*  
*Version 2026*

---

## Table des matières

1. [Présentation générale](#1-présentation-générale)
2. [Connexion et déconnexion](#2-connexion-et-déconnexion)
3. [Tableau de bord](#3-tableau-de-bord)
4. [Formations](#4-formations)
5. [Détail d'une formation](#5-détail-dune-formation)
   - 5.1 [Informations générales](#51-informations-générales)
   - 5.2 [Séances](#52-séances)
   - 5.3 [Présences](#53-présences)
   - 5.4 [Auditeurs inscrits](#54-auditeurs-inscrits)
   - 5.5 [Formateurs assignés](#55-formateurs-assignés)
6. [Auditeurs](#6-auditeurs)
7. [Formateurs](#7-formateurs)
8. [Utilisateurs](#8-utilisateurs)
9. [Secrétariats](#9-secrétariats)
10. [Import Excel](#10-import-excel)
11. [Référentiels](#11-référentiels)
12. [Badgeage QR Code (web)](#12-badgeage-qr-code-web)
13. [Rôles et permissions](#13-rôles-et-permissions)

---

## 1. Présentation générale

**QR Badge** est une plateforme de gestion des présences aux formations par QR Code.  
Elle permet de :

- Gérer les formations, leurs séances, et les inscriptions d'auditeurs
- Générer des QR Codes par séance pour le badgeage automatique
- Suivre en temps réel les présences (entrées / sorties)
- Exporter les listes de présence
- Importer en masse des données depuis Excel

Ce manuel couvre **l’ensemble de la plateforme web** (interface de gestion et page de badgeage web), **hors application mobile**.

---

## 2. Connexion et déconnexion

### Connexion
1. Ouvrez l'application dans votre navigateur.
2. Saisissez votre **Identifiant** et votre **Mot de passe**.
3. Cliquez sur **Se connecter**.

> En cas d'identifiants incorrects, un message d'erreur s'affiche sous le formulaire. Contactez votre administrateur pour réinitialiser votre mot de passe.

### Déconnexion
Cliquez sur **Déconnexion** en bas du menu latéral gauche. Vous êtes redirigé vers la page de connexion.

---

## 3. Tableau de bord

Page d'accueil après connexion.

### Statistiques affichées

**Bloc Formations :**
| Indicateur | Description |
|---|---|
| Modules | Nombre total de formations enregistrées |
| En cours | Formations actuellement actives |
| Terminées | Formations clôturées |
| Planifiées | Formations programmées mais non démarrées |

**Bloc Activité :**
| Indicateur | Description |
|---|---|
| Auditeurs | Nombre total d'auditeurs dans le système |
| Formateurs | Nombre total de formateurs *(visible selon rôle)* |
| Séances actives | Séances en cours de démarrage |
| Pointages du jour | Nombre de badgeages enregistrés aujourd'hui |
| En salle maintenant | Nombre de personnes actuellement en salle |

### Taux de présence du jour
Un encart affiche le taux de présence global pour la journée en cours : nombre de présents, absents, et pourcentage.

### Formations en cours
Liste des formations actuellement en cours, avec pour chacune : titre, site, dates, encadrant, et un bouton **Voir** pour accéder au détail.

### Formations planifiées
Liste des prochaines formations à venir.

---

## 4. Formations

### Accès
Menu latéral → **Formations**

### Liste des formations
Le tableau affiche pour chaque formation :
- Module / Titre
- Secrétariat rattaché
- Site, Catégorie, Grade, Groupe, Vague
- Dates de début et de fin
- Encadrant assigné
- Nombre d'auditeurs attendus
- Statut : `Planifiée` | `En cours` | `Suspendue` | `Terminée`

### Filtres disponibles
- **Recherche** libre par titre, site, grade, groupe ou vague
- **Statut** : liste déroulante pour filtrer par état
- **Secrétariat** : visible selon votre rôle

### Créer une formation *(Chef Secrétariat / Secrétariat / CPFAE Admin / Chef CPFAE Admin)*
1. Cliquez sur **+ Nouvelle formation**.
2. Remplissez les champs :
   - **Formation** *(obligatoire)* — sélectionner dans la liste des formations de référence
   - **Module** *(obligatoire)* — intitulé du module
   - **Site** — lieu de la formation
   - **Catégorie**, **Grade**, **Groupe**, **Vague**
   - **Dates** de début et de fin *(obligatoires)*
   - **Volume horaire** prévu (en heures)
   - **Statut** initial (`Planifiée` par défaut)
   - **Encadrant** à assigner *(optionnel)*
3. Cliquez sur **Créer**.

### Modifier une formation
1. Cliquez sur l'icône **crayon** sur la ligne de la formation.
2. Modifiez les champs souhaités.
3. Cliquez sur **Enregistrer**.

### Supprimer une formation
1. Cliquez sur l'icône **corbeille**.
2. Confirmez la suppression dans la boîte de dialogue.

> ⚠️ La suppression est **irréversible** et supprime également toutes les séances et pointages associés.

---

## 5. Détail d'une formation

Cliquez sur l'icône **œil** dans la liste des formations, ou sur le bouton **Voir** depuis le tableau de bord.

La page est organisée en **5 onglets** :

---

### 5.1 Informations générales

Affiche toutes les métadonnées de la formation :
- Module, site, catégorie, grade, groupe, vague
- Dates de début et de fin, volume horaire
- Secrétariat, encadrant assigné, créateur du dossier
- Statistiques de séances (terminées, en cours, planifiées, durée totale)

**Assigner / changer l'encadrant** *(Chef CPFAE Admin / CPFAE Admin / Chef Secrétariat / Secrétariat)* :
1. Cliquez sur l'icône **crayon** à côté du nom de l'encadrant.
2. Sélectionnez un encadrant dans la liste déroulante.
3. Cliquez sur **Assigner**.

---

### 5.2 Séances

Liste toutes les séances de la formation.

**Informations affichées par séance :**
- Numéro et intitulé
- Date et heure de début / fin prévues
- Statut : `Planifiée` | `En cours` | `Terminée`
- Nombre de présences enregistrées

**Actions par séance *(selon rôle)* :**

| Bouton | Rôle requis | Description |
|---|---|---|
| ▶ Démarrer | Encadrant / Secrétariat / CPFAE | Lance la séance |
| ⏹ Terminer | Encadrant / Secrétariat / CPFAE | Clôture la séance |
| QR Code | Tous rôles actifs | Génère et affiche le QR de la séance |
| ✏ Modifier | Secrétariat / CPFAE | Modifie date, intitulé, heures |
| 🗑 Supprimer | Secrétariat / CPFAE | Supprime la séance (si non démarrée) |

**Générer un QR Code :**
1. Cliquez sur l'icône **QR** de la séance souhaitée.
2. Le QR Code s'affiche dans une fenêtre modale.
3. Cliquez sur **Télécharger** pour sauvegarder l'image PNG.
4. Cliquez sur **Régénérer** pour créer un nouveau token (invalide l'ancien).
5. Affichez ou imprimez le QR Code pour que les auditeurs le scannent.

> Le QR Code encode l'URL de badgeage avec un token unique. Il est valable **24 heures** par défaut.

**Créer une séance :**
1. Cliquez sur **+ Nouvelle séance**.
2. Renseignez : date *(obligatoire)*, intitulé, heures de début et de fin prévues.
3. Cliquez sur **Créer**.

**Modifier une séance *(non terminée)* :**
1. Cliquez sur l'icône **crayon** de la séance.
2. Modifiez l'intitulé, la date, ou les heures.
3. Cliquez sur **Enregistrer**.

> Une séance **terminée** ne peut plus être modifiée.

---

### 5.3 Présences

Tableau de suivi des présences en temps réel pour une date sélectionnée.

**Filtres disponibles :**
- **Date** — sélectionnez la date souhaitée (par défaut : aujourd'hui)
- **Séance** — filtrer par séance spécifique ou afficher toutes
- **Recherche** — chercher un auditeur par nom ou matricule

**Trois catégories affichées :**

| Catégorie | Description |
|---|---|
| 🟢 En salle | Personnes dont l'entrée a été badgée, pas encore sorties |
| ✅ Présents | Personnes dont la session est terminée (entrée + sortie) |
| ❌ Absents | Personnes inscrites sans aucun badgeage pour cette date |

**Informations par ligne :**
- Nom, prénom, matricule, grade, site
- Heure d'entrée, heure de sortie, durée de présence
- Type : Auditeur ou Formateur

**Actions manuelles *(Encadrant / Secrétariat / CPFAE Admin)* :**

- **Fermer session** : pour les personnes "En salle", enregistre manuellement la sortie.
  1. Cliquez sur **Fermer session**.
  2. Saisissez un **motif** obligatoire (ex : "Oubli de scan sortie").
  3. Si la date est dans le passé, renseignez l'heure de sortie exacte.
  4. Cliquez sur **Confirmer**.

- **Badger entrée** : pour les personnes "Absentes", enregistre manuellement une entrée.
  1. Cliquez sur **Badger entrée**.
  2. Saisissez un **motif** obligatoire.
  3. Si la date est dans le passé, renseignez l'heure d'entrée exacte.
  4. Cliquez sur **Confirmer**.

> Toutes les actions manuelles sont **auditées** (traçabilité avec l'auteur et l'horodatage).

---

### 5.4 Auditeurs inscrits

Liste les auditeurs inscrits à cette formation avec : matricule, nom, prénom, adresse e-mail, téléphone, structure.

**Ajouter un auditeur *(Secrétariat / CPFAE)* :**
1. Cliquez sur **+ Ajouter un auditeur**.
2. Recherchez par nom ou matricule dans la liste.
3. Cliquez sur **Ajouter** à côté de l'auditeur souhaité.

**Retirer un auditeur *(Secrétariat / CPFAE)* :**
1. Cliquez sur l'icône **corbeille** à côté de l'auditeur.
2. Confirmez le retrait.

---

### 5.5 Formateurs assignés

Liste les formateurs affectés à cette formation avec : numéro, nom, prénom, spécialité, adresse e-mail, téléphone.

**Ajouter un formateur *(Secrétariat / CPFAE)* :**
1. Cliquez sur **+ Ajouter un formateur**.
2. Recherchez dans la liste des formateurs disponibles.
3. Cliquez sur **Ajouter**.

**Retirer un formateur *(Secrétariat / CPFAE)* :**
Cliquez sur l'icône **corbeille** puis confirmez.

---

## 6. Auditeurs

### Accès
Menu latéral → **Auditeurs**

### Liste des auditeurs
Tableau paginé affichant pour chaque auditeur :
- N° d'inscription, Nom & Prénom
- Sexe, Catégorie / Grade
- Téléphone
- Actions

### Filtres disponibles
- **Recherche** libre : nom, prénom, matricule, e-mail, type concours, libellé concours, grade, groupe, secrétariat
- **Secrétariat** : choix en liste (menu déroulant)
- **Grade** : choix en liste (menu déroulant)
- **Groupe** : choix en liste (menu déroulant)
- **Type concours** : choix en liste (menu déroulant)
- **Sexe** : Masculin / Féminin

> Note : le secrétariat reste aussi appliqué automatiquement selon le rôle utilisateur (un compte Secrétariat voit uniquement les auditeurs de son secrétariat).

### Consulter la fiche détail d'un auditeur
Cliquez sur l'icône **œil** pour afficher la fiche complète :
- **Identité** : N° d'inscription, genre, date et lieu de naissance, adresse e-mail, téléphones
- **Administratif** : catégorie, grade, groupe, vague, type et libellé du concours
- **Localisation** : site, salle
- **Formations** : liste des formations auxquelles l'auditeur est inscrit

### Créer un auditeur *(Secrétariat / CPFAE)*
1. Cliquez sur **+ Nouvel auditeur**.
2. Remplissez les champs obligatoires : **Nom** *(obligatoire)*, **Prénoms** *(obligatoire)*.
3. Complétez les champs optionnels :
   - Matricule / N° d'inscription, genre, date et lieu de naissance
   - Adresse e-mail, téléphone 1, téléphone 2
   - Type et libellé du concours
   - Catégorie, grade, groupe, vague
   - Site, salle
4. Cliquez sur **Créer**.

### Modifier un auditeur *(Secrétariat / CPFAE)*
1. Cliquez sur l'icône **crayon**.
2. Modifiez les informations souhaitées.
3. Cliquez sur **Enregistrer**.

### Supprimer un auditeur *(Secrétariat / CPFAE)*
1. Cliquez sur l'icône **corbeille**.
2. Confirmez la suppression.

---

## 7. Formateurs

### Accès
Menu latéral → **Formateurs**

### Liste des formateurs
Tableau affichant pour chaque formateur :
- Numéro interne, Nom, Prénom
- Spécialité, Adresse e-mail, Téléphone
- Nombre de formations auxquelles il est assigné

### Filtres disponibles
- **Recherche** libre : nom, prénom, numéro, spécialité, organisation

### Créer un formateur *(Secrétariat / CPFAE)*
1. Cliquez sur **+ Nouveau formateur**.
2. Remplissez les champs :
   - **Nom** et **Prénom** *(obligatoires)*
   - Numéro interne, spécialité, organisation
   - Adresse e-mail, téléphone
3. Cliquez sur **Créer**.

### Modifier / Supprimer un formateur *(Secrétariat / CPFAE)*
- Icône **crayon** → modifier les informations.
- Icône **corbeille** → supprimer (confirmation requise).

---

## 8. Utilisateurs

### Accès
Menu latéral → **Utilisateurs**

> Cette page est visible uniquement si votre rôle vous permet de créer des utilisateurs.

### Liste des utilisateurs
Tableau affichant : nom complet, identifiant, adresse e-mail, rôle, téléphone, statut (Actif / Inactif).

### Filtres disponibles
- **Recherche** libre : nom, identifiant, e-mail
- **Rôle** : filtrer par rôle

### Créer un utilisateur
> Vous ne pouvez créer que des utilisateurs dont le rôle est **inférieur** au vôtre dans la hiérarchie.

1. Cliquez sur **+ Nouvel utilisateur**.
2. Remplissez les champs :
   - **Prénom** et **Nom** *(obligatoires)*
   - **Identifiant** *(obligatoire, unique)*
   - **Rôle** *(obligatoire)* — limité selon votre propre rôle
   - Adresse e-mail, téléphone
   - **Mot de passe** *(obligatoire)*
3. Si le rôle choisi est **Secrétariat** ou **Chef Secrétariat** :
   - Sélectionnez un secrétariat existant **ou**
   - Créez un nouveau secrétariat en renseignant son nom et son type (A, B ou C)
4. Cliquez sur **Créer**.

> Un seul compte **Chef CPFAE Admin** peut exister sur la plateforme. Un avertissement s'affiche si vous tentez d'en créer un second.

### Modifier un utilisateur
1. Cliquez sur l'icône **crayon**.
2. Modifiez les champs souhaités.
3. Pour **changer le mot de passe** : renseignez le nouveau dans le champ dédié (laisser vide pour ne pas le modifier).
4. Cliquez sur **Enregistrer**.

### Désactiver un utilisateur
Dans le formulaire de modification, changez le **Statut** de *Actif* à *Inactif*. L'utilisateur ne pourra plus se connecter.

### Supprimer un utilisateur
Cliquez sur l'icône **corbeille** puis confirmez. La suppression est définitive.

---

## 9. Secrétariats

### Accès
Menu latéral → **Secrétariats** *(Chef CPFAE Admin / CPFAE Admin uniquement)*

### Liste des secrétariats
Tableau avec : nom, type (A / B / C), nombre de membres, nombre d'auditeurs rattachés, nombre de formations.

Cliquez sur l'icône **personnes** pour voir la liste des membres d'un secrétariat.

### Créer un secrétariat
1. Cliquez sur **+ Nouveau secrétariat**.
2. Renseignez :
   - **Nom** *(obligatoire)*
   - **Type** : A, B ou C
   - **Description** *(optionnel)*
3. Cliquez sur **Créer**.

> Le **type** détermine les grades de participants associés à ce secrétariat :
> - Type **A** → grades de catégorie A
> - Type **B** → grades de catégorie B
> - Type **C** → grades de catégorie C

### Modifier / Supprimer un secrétariat
- Icône **crayon** → modifier.
- Icône **corbeille** → supprimer (confirmation requise).

---

## 10. Import Excel

### Accès
Menu latéral → **Import Excel** *(Secrétariat / Chef Secrétariat / CPFAE Admin / Chef CPFAE Admin)*

Permet d'importer en masse des données depuis des fichiers Excel (`.xlsx`).

### Ordre d'import recommandé

1. **Cours** (formations / modules) — les cours doivent exister en premier
2. **Formateurs**
3. **Auditeurs** (inscriptions aux cours)
4. **Séances** (planning rattaché aux cours)

> Les séances sont reliées aux cours par la combinaison **module_titre + grade + groupe + vague**. Ces quatre valeurs doivent être **identiques** entre l'import des cours et celui des séances.

### Types d'import disponibles

#### Cours (formations)
**Feuille Excel :** `Formations`  
**Colonnes attendues :**
`N°` · `Formation` · `Module (titre)` · `Site` · `Bâtiment` · `Salle` · `Date début` · `Date fin` · `Volume horaire (h)` · `Catégorie` · `Grade` · `Groupe` · `Vague`

> La colonne `Lieu` est acceptée en remplacement de `Site`. Les dates début et fin sont obligatoires.

#### Auditeurs
**Feuille Excel :** `Participants` (ou `Auditeurs` pour les exports compatibles)  
**Colonnes attendues :**
`N° d'inscription` · `Nom` · `Prénoms` · `Genre` · `Date de naissance` · `Lieu de naissance` · `E-mail` · `Téléphone 1` · `Téléphone 2` · `Type concours` · `Libellé concours` · `Catégorie` · `Grade` · `Groupe` · `Grade-Groupe` · `Vague` · `Formation(s)`

> Variantes acceptées : `Prénom` / `Sexe` / `Email`. La colonne `Formation(s)` permet l'inscription automatique (titres séparés par `|`). Sans cette colonne, l'inscription se fait par correspondance grade + groupe (+ vague).

#### Formateurs
**Feuille Excel :** `Formateurs`  
**Colonnes attendues :**
`Numéro` · `Nom` · `Prénom` · `E-mail` · `Téléphone` · `Spécialité` · `Organisation`

#### Séances
**Feuille Excel :** `Séances` (ou `Seances`)

**Depuis la page Import Excel** (plusieurs cours dans le même fichier) :
`module_titre` · `grade` · `groupe` · `vague` · `date_journee` · `numero` · `intitule` · `heure_debut` · `heure_fin`

**Depuis la fiche d'une formation** (menu Formations → détail → onglet Séances → Importer Excel) :
`date_journee` · `numero` · `intitule` · `heure_debut` · `heure_fin`

> Dans ce second cas, le cours cible est déjà connu : seules les colonnes de planning sont nécessaires.

> **Format des données :** date → `JJ/MM/AAAA` · heure → `HH:MM` · numéro → `1, 2, 3…` (1 = matin, 2 = après-midi, etc.)

### Procédure d'import

1. Cliquez sur **Modèle CSV** pour télécharger un modèle (en-têtes + lignes d'exemple, séparateur `;`).
2. Ouvrez le modèle dans Excel, adaptez ou complétez les données, puis sauvegardez en `.xlsx` (feuille nommée selon le type : `Formations`, `Participants`, `Formateurs` ou `Séances`).
3. Sur la page **Import Excel**, sélectionnez le fichier et cliquez sur **Importer** pour le type concerné (Cours, Auditeurs, Formateurs ou Séances).
4. Pour importer des séances **d'une formation précise**, ouvrez la fiche de cette formation → onglet **Séances** → **Importer Excel**.
5. Consultez le message de résultat (éléments créés, mis à jour, erreurs éventuelles).

### Résultats de l'import
Après chaque import, un message s'affiche indiquant :
- ✅ **Import réussi** : nombre d'éléments créés, nombre déjà existants (mis à jour ou ignorés)
- ❌ **Erreurs** : nombre d'erreurs avec le nombre d'éléments créés malgré les erreurs

> En cas d'erreur, seules les lignes valides sont importées. Corrigez les lignes en erreur et relancez l'import.

---

## 11. Référentiels

### Accès
Menu latéral → **Référentiels** *(Chef CPFAE Admin / CPFAE Admin / Chef Secrétariat / Secrétariat)*

Gestion des données de référence utilisées dans les formulaires de la plateforme.

### Onglets disponibles

| Onglet | Données gérées |
|---|---|
| **Formations** | Intitulés de formations de référence |
| **Modules** | Modules avec leur volume horaire |
| **Catégories** | Catégories d'auditeurs (code + libellé) |
| **Grades** | Grades rattachés à une catégorie (code + libellé) |
| **Sites** | Sites / lieux de formation |
| **Bâtiments** | Bâtiments rattachés à un site |
| **Salles** | Salles rattachées à un bâtiment et un site |

### Ajouter un élément
1. Sélectionnez l'onglet souhaité.
2. Cliquez sur **+ Ajouter**.
3. Remplissez les champs du formulaire.
4. Cliquez sur **Enregistrer**.

### Modifier un élément
Cliquez sur l'icône **crayon** sur la ligne correspondante, modifiez, puis **Enregistrer**.

### Activer / Désactiver un élément
Cliquez sur le bouton **Actif / Inactif** pour basculer le statut. Les éléments inactifs n'apparaissent plus dans les listes déroulantes des formulaires.

### Supprimer un élément
Cliquez sur l'icône **corbeille** puis confirmez. Un élément utilisé par des formations existantes ne peut pas être supprimé.

---

## 12. Badgeage QR Code (web)

### Accès
Le badgeage web s'effectue depuis la page publique :

`/dashboard/badge/`

Le QR Code généré depuis l'onglet **Séances** d'une formation contient le token de badgeage.

### Procédure de badgeage

1. Ouvrez la page de badgeage web dans un navigateur.
2. Chargez le token QR :
   - soit en scannant le QR via la caméra web ;
   - soit en saisissant manuellement le token QR.
3. Saisissez le **numéro matricule** dans le champ prévu.
4. Cliquez sur **Badger**.
5. Confirmez l'opération dans la fenêtre de confirmation.
6. Un résultat s'affiche :
   - **Entrée enregistrée** → vous êtes maintenant "En salle"
   - **Sortie enregistrée** → votre durée de présence est calculée

### Badgeage hors ligne
Si le navigateur n'a pas de connexion internet au moment du badgeage :
1. Le badgeage est **sauvegardé localement** sur l'appareil.
2. Dès que la connexion est rétablie, la synchronisation s'effectue **automatiquement**.

### Vérification du statut avant badgeage
Avant d'enregistrer, la plateforme affiche votre statut actuel :
- **ABSENT** → prochain action : Entrée
- **EN SALLE** → prochain action : Sortie
- **TERMINÉ** → session déjà complète pour cette séance

---

## 13. Rôles et permissions

### Hiérarchie des rôles (du plus élevé au plus bas)
1. **Direction** — lecture seule globale
2. **Chef CPFAE Admin** — administrateur principal
3. **CPFAE Admin** — administrateur CPFAE
4. **Chef Secrétariat** — responsable d'un secrétariat
5. **Secrétariat** — agent de secrétariat
6. **Encadrant** — superviseur de formation
7. **Auditeur** — badgeage uniquement (page publique de badgeage)

### Tableau des accès par module

| Module | Direction | Chef CPFAE | CPFAE Admin | Chef Secr. | Secrétariat | Encadrant |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Tableau de bord | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Formations (lecture) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Formations (création/modif) | — | ✓ | ✓ | ✓ | ✓ | — |
| Séances (démarrer/terminer) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Séances (créer/modifier) | — | ✓ | ✓ | ✓ | ✓ | — |
| QR Code (générer) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Présences (consulter) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Présences (forcer badgeage) | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Auditeurs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Auditeurs (créer/modif/suppr) | — | ✓ | ✓ | ✓ | ✓ | — |
| Formateurs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Formateurs (créer/modif/suppr) | — | ✓ | ✓ | ✓ | ✓ | — |
| Utilisateurs | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Utilisateurs (créer/modif/suppr) | — | ✓ | ✓ | ✓ | ✓ | — |
| Secrétariats | — | ✓ | ✓ | — | — | — |
| Import Excel | — | ✓ | ✓ | ✓ | ✓ | — |
| Référentiels | — | ✓ | ✓ | — | — | — |

### Règle de création d'utilisateurs
Chaque rôle ne peut créer que des utilisateurs dont le rôle est **strictement inférieur** dans la hiérarchie.

| Qui crée | Peut créer |
|---|---|
| Chef CPFAE Admin | Direction, CPFAE Admin, Chef Secrétariat, Secrétariat, Encadrant, Auditeur |
| CPFAE Admin | Chef Secrétariat, Secrétariat, Encadrant, Auditeur |
| Chef Secrétariat | Secrétariat, Encadrant, Auditeur |
| Secrétariat | Encadrant, Auditeur |

---

*Document institutionnel plateforme web (hors app mobile) — MEMFPMA — DFRC/CPFAE — QR Badge 2026*
