# Pages légales & confidentialité (HTML statique)

Contenu prêt pour un dépôt GitHub servi via **GitHub Pages** (ou tout autre hébergement de fichiers statiques).

## Fichiers

| Fichier | Usage |
|---------|--------|
| `index.html` | Redirige vers `legal/index.html`. |
| `legal/index.html` | Sommaire avec liens vers toutes les pages. |
| `legal/confidentialite-qr-badge-mobile.html` | **Google Play** — caméra, localisation, app mobile. |
| `legal/confidentialite-badgeage-web.html` | Badgeage navigateur / PWA / hors ligne. |
| `legal/confidentialite-plateforme-sygep.html` | Vue globale plateforme (web + API). |
| `legal/donnees-personnelles-droits.html` | Droits RGPD (accès, rectification, CNIL, etc.). |
| `legal/mentions-legales.html` | Éditeur, hébergement (modèle à compléter). |
| `legal/politique-cookies.html` | Cookies & traceurs. |
| `legal/assets/style.css` | Mise en forme commune. |

Remplacez les champs entre **crochets** `[…]` par les informations officielles de votre structure.

## Publier avec GitHub Pages

1. Poussez le dossier `docs/` sur la branche `main` (ou `master`) du dépôt GitHub.
2. **Settings** → **Pages** → **Build and deployment** : source **Deploy from a branch**, dossier **`/docs`**, branche **`main`**.
3. Après build, l’URL sera du type :  
   `https://<utilisateur>.github.io/<nom-du-depot>/`  
   Les pages légales :  
   `https://<utilisateur>.github.io/<nom-du-depot>/legal/index.html`  
   Pour la Play Console (politique confidentialité + caméra), utilisez par exemple :  
   `https://<utilisateur>.github.io/<nom-du-depot>/legal/confidentialite-qr-badge-mobile.html`

Le fichier **`.nojekyll`** à la racine de `docs/` évite que Jekyll ignore ou transforme des fichiers.

## HTTPS

GitHub Pages sert le site en **HTTPS** par défaut — compatible avec l’exigence Play Console pour l’URL de politique de confidentialité.
