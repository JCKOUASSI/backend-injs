# Manuel Utilisateur Institutionnel
## Badgeage Web des Auditeurs

**Application** : QR Badge - DFRC/CPFAE
**Canal** : Portail web de badgeage (`/dashboard/badge/`)
**Public cible** : Auditeurs
**Version** : 2.0
**Statut** : Document operationnel
**Date d'application** : A renseigner

---

## Fiche administrative de validation

### 0.1 Identification documentaire

- **Code document** : MAN-DFRC-CPFAE-BADGE-WEB-AUDITEURS
- **Intitule officiel** : Manuel utilisateur institutionnel - Badgeage web des auditeurs
- **Type de document** : Procedure operationnelle standard
- **Service emetteur** : DFRC / CPFAE
- **Niveau de confidentialite** : Interne administration
- **Etat du document** : Projet pour validation hierarchique

### 0.2 Circuit de visa (a renseigner)

- **Redacteur**
  - Nom et prenoms : ........................................................
  - Fonction : ...............................................................
  - Date : ....../....../........
  - Visa / Signature : ......................................................

- **Relecteur fonctionnel**
  - Nom et prenoms : ........................................................
  - Fonction : ...............................................................
  - Date : ....../....../........
  - Visa / Signature : ......................................................

- **Validation hierarchique (N+1)**
  - Nom et prenoms : ........................................................
  - Fonction : ...............................................................
  - Date : ....../....../........
  - Visa / Signature : ......................................................

- **Approbation finale (Autorite competente)**
  - Nom et prenoms : ........................................................
  - Fonction : ...............................................................
  - Date : ....../....../........
  - Visa / Signature : ......................................................

### 0.3 Diffusion et destinataires

- **Diffusion principale** : Auditeurs, Encadrants, Secretariat, Administration DFRC/CPFAE
- **Canaux de diffusion** : intranet, dossier qualite, affichage numerique, partage interne
- **Reference exemplaire maitre** : Service DFRC / CPFAE
- **Gestion des copies** : toute copie imprimee est non maitrisable sauf mention contraire

### 0.4 Conditions d'entree en vigueur

Le present document entre en vigueur apres :
- signature du redacteur ;
- visa du relecteur fonctionnel ;
- validation hierarchique ;
- approbation finale.

---

## 1. Objet du document

Le present manuel definit la procedure officielle de badgeage des auditeurs via l'interface web QR Badge.

Il a pour finalite de :
- normaliser les pratiques de pointage entree/sortie ;
- garantir la fiabilite des donnees de presence ;
- encadrer le traitement des incidents courants.

## 2. Champ d'application

Ce document s'applique a tout auditeur devant enregistrer sa presence sur une seance de formation via le portail web.

Le document couvre :
- l'acces a la page de badgeage ;
- la saisie des informations de pointage ;
- la validation des messages de resultat ;
- la conduite a tenir en cas d'anomalie.

## 3. References fonctionnelles

- Page de badgeage web : `http://<serveur>/dashboard/badge/`
- API de pointage utilisee en arriere-plan : `POST /api/scan/`
- Verification d'etat avant confirmation : `GET /api/scan/check-status/`

## 4. Definitions

- **Matricule auditeur** : identifiant individuel utilise pour le badgeage.
- **Token QR** : identifiant technique de la seance transmis par QR code.
- **Entree** : premier badgeage valide sur la seance.
- **Sortie** : second badgeage valide sur la meme seance.
- **Mode hors ligne** : enregistrement local temporaire des badgeages en absence de reseau.

## 5. Roles et responsabilites

- **Auditeur**
  - renseigne son matricule exact ;
  - effectue son badgeage a l'entree puis a la sortie ;
  - verifie le message de confirmation affiche.

- **Encadrant / Secretariat**
  - met a disposition un QR actif ;
  - assiste les auditeurs en cas d'erreur de token ou d'inscription.

- **Administration technique**
  - garantit la disponibilite du service ;
  - assure le suivi des incidents applicatifs.

## 6. Conditions prealables

Avant tout badgeage, l'auditeur doit disposer de :
- un navigateur web recent (ordinateur, tablette ou smartphone) ;
- un acces reseau au serveur QR Badge ;
- son matricule auditeur ;
- un QR code actif de la seance en cours.

## 7. Procedure normalisee de badgeage

### 7.1 Acces

1. Ouvrir la page `http://<serveur>/dashboard/badge/`.
2. Verifier l'affichage correct de l'interface de badgeage.

### 7.2 Methode A - Scan camera web (prioritaire)

1. Activer le scanner camera depuis l'interface.
2. Autoriser l'acces camera si le navigateur le demande.
3. Scanner le QR de la seance.
4. Saisir le matricule auditeur.
5. Cliquer sur **Badger**.
6. Confirmer l'operation dans la fenetre de confirmation.

### 7.3 Methode B - Saisie manuelle (secours)

1. Saisir le matricule auditeur.
2. Saisir le token QR dans le champ prevu.
3. Cliquer sur **Badger**.
4. Confirmer l'operation.

### 7.4 Regle de gestion entree/sortie

- 1er badgeage valide : enregistrement de l'entree ;
- 2e badgeage valide : enregistrement de la sortie ;
- si le statut est deja "en salle", la confirmation bascule automatiquement vers une sortie.

## 8. Controle du resultat

L'auditeur doit verifier l'affichage de l'un des messages suivants :
- **Entree enregistree** ;
- **Sortie enregistree** ;
- message d'erreur explicite.

En absence de confirmation visuelle, le pointage est considere comme non garanti et doit etre repris.

## 9. Gestion du mode hors ligne

En cas de perte reseau :
- l'interface affiche l'etat **Hors ligne** ;
- les badgeages sont places en file d'attente locale ;
- la synchronisation est automatique au retour de la connexion.

Consignes :
- ne pas vider le cache navigateur tant que des pointages sont en attente ;
- ne pas changer d'appareil avant synchronisation complete.

## 10. Incidents frequents et mesures correctives

### 10.1 QR invalide ou expire
- **Cause probable** : token non actif.
- **Action** : demander un QR actif a l'encadrant.

### 10.2 Auditeur non autorise
- **Cause probable** : auditeur non inscrit a la seance/module.
- **Action** : escalader au Secretariat pour verification des inscriptions.

### 10.3 Camera indisponible
- **Cause probable** : permission refusee ou camera non detectee.
- **Action** : autoriser la camera, recharger la page, ou appliquer la methode manuelle.

### 10.4 Defaut reseau
- **Cause probable** : interruption d'acces serveur.
- **Action** : maintenir le badgeage en mode hors ligne puis controler la synchronisation.

## 11. Escalade et support

Tout litige de presence doit etre remonte avec les informations minimales suivantes :
- matricule auditeur ;
- date et heure approximative du badgeage ;
- intitule du cours/seance ;
- message d'erreur observe (capture ecran recommandee).

## 12. Gouvernance documentaire

- **Proprietaire metier** : DFRC / CPFAE
- **Validation fonctionnelle** : A renseigner
- **Validation technique** : A renseigner
- **Periodicite de revision** : semestrielle ou a chaque evolution majeure du module de badgeage

---

### Historique des versions

- **v2.0** : Refonte institutionnelle du manuel, recentrage exclusif sur le badgeage web auditeurs.
- **v1.1** : Version operationnelle web simplifiee.

### Suivi des revisions (a renseigner)

- Date de prochaine revue : ....../....../........
- Responsable de revue : ....................................................
- Motif de revue : ..........................................................
