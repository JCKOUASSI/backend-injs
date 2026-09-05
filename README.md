# INJS-LMD 2026

Application de gestion académique et administrative de l'Institut National de la Jeunesse et des Sports (INJS) dans le cadre du système LMD.

## Architecture

Le projet est organisé autour de trois composants principaux :

- `backend/` — API Django / Django REST Framework
- `frontend/` — interface web React / Vite
- `qr_badge_mobile/` — application mobile Flutter

## Principaux domaines fonctionnels

- Authentification et gestion des rôles
- Référentiels LMD
- Formations et modules
- Admissions et candidatures
- Scolarité
- Groupes et inscriptions
- Présences et badgeage QR
- Évaluation et suivi académique
- Finances
- Statistiques et rapports
- Paramètres

## Sécurité

Les secrets, mots de passe réels, fichiers `.env`, données personnelles, bases de données, médias utilisateurs et sauvegardes locales ne doivent jamais être versionnés.

Les variables sensibles doivent être fournies par l'environnement d'exécution.

Un fichier d'exemple de configuration est disponible dans `backend/env.exemple`.

## Développement local

### Backend

```bash
cd backend
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Application mobile

```bash
cd qr_badge_mobile
flutter pub get
flutter run
```

## Dépôt Git

Ce dépôt constitue une nouvelle base Git propre pour le projet INJS-LMD 2026.

Il ne doit pas être connecté au dépôt historique SYGEP-CPFAE.
