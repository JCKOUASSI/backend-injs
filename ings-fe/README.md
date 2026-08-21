# INJS Gestion Universitaire

Application frontend React de gestion de l'**Institut National de la Jeunesse et des Sports (INJS)** en partenariat avec l'**Université Félix Houphouët-Boigny** — **UFR STAPS-JL**.

Inspirée du template **Ericsson React Admin Template for University**, adaptée aux couleurs et au contexte pédagogique INJS (système **LMD** : Licence, Master, Doctorat).

## Fonctionnalités

### 3 interfaces distinctes
- **Administration** — Gestion globale (étudiants, professeurs, UE, EDT, notes, stages, finances)
- **Professeurs** — Cours, évaluations CC/CT, présences, suivi stages
- **Étudiants** — Parcours LMD, notes, emploi du temps, stages, documents

### Contexte pédagogique intégré
- Licence STAPS (4 spécialités : EM, ES, MS, APA)
- Maquettes semestres S1-S6 (2025-2026)
- Règles de validation LMD (CC 40% + CT 60%)
- 180 CECT pour la Licence

## Démarrage

```bash
cd injs-gestion
npm install
npm run dev
```

Ouvrir http://localhost:5173

## Comptes de démonstration

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Administration | admin@injs.ci | admin123 |
| Professeur | seribialliv@gmail.com | prof123 |
| Étudiant | etudiant@injs.ci | etu123 |

## Stack technique

- React 18 + Vite 6
- React Router 6
- Bootstrap 5 + thème INJS personnalisé
- Chart.js (tableaux de bord)
- React Icons

## Structure

```
src/
├── components/layout/   # Sidebar, Header, MainLayout
├── pages/
│   ├── admin/           # 12 pages administration
│   ├── professor/       # 8 pages professeur
│   └── student/         # 8 pages étudiant
├── data/                # Données mock STAPS/LMD
├── context/             # Authentification multi-rôles
└── styles/              # Thème couleurs INJS
```

## Prochaines étapes (backend)

- API REST (Node.js / Spring Boot / Laravel)
- Base de données (PostgreSQL)
- Authentification JWT réelle
- Intégration maquettes pédagogiques complètes
