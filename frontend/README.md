# QR Badge - Frontend React

This is the React frontend for the QR Badge application, a training management system.

## Architecture

```
frontend/
├── src/
│   ├── pages/          # Page components
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Formations.jsx
│   │   ├── FormationDetail.jsx
│   │   ├── Participants.jsx
│   │   ├── Formateurs.jsx
│   │   ├── Users.jsx
│   │   └── ImportExcel.jsx
│   ├── context/         # React contexts
│   │   └── AuthContext.jsx
│   ├── services/       # API services
│   │   └── api.js
│   ├── App.jsx          # Main app with routing
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles
├── index.html
├── package.json
└── vite.config.js
```

## Prerequisites

- Node.js 18+ 
- npm or yarn

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create a `.env` file (optional):
```bash
VITE_API_URL=/api
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### API Proxy

The Vite dev server is configured to proxy API requests to `http://localhost:8000`.
This means you can call `/api/*` in your React code and it will be forwarded to the Django backend.

## Features

- **Authentication**: JWT-based login with token refresh
- **Dashboard**: Overview of formations, participants, and formateurs
- **Formations Management**: List, create, edit, delete formations
- **Sessions Management**: Start/stop sessions, generate QR codes
- **Participants Management**: CRUD operations for participants
- **Formateurs Management**: CRUD operations for formateurs
- **Users Management**: User administration (DFRC only)
- **Excel Import**: Import data from Excel files

## User Roles

| Role | Permissions |
|------|-------------|
| DIRECTION | Full access |
| DFRC | Full access |
| SECRETARIAT | Limited to assigned secretariat |
| SUPERVISEUR | View assigned formations, manage sessions |
| PARTICIPANT | View own attendance |

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Login
- `POST /api/auth/token/refresh/` - Refresh token
- `GET /api/auth/me/` - Current user profile

### Formations
- `GET /api/formations/list/` - List formations (with filters)
- `GET /api/formations/stats/` - Dashboard statistics
- `GET /api/formations/{id}/` - Formation details
- `POST /api/formations/{id}/assign-superviseur/` - Assign supervisor

### Sessions
- `GET /api/formations/{id}/sessions/` - List sessions
- `POST /api/formations/{id}/sessions/new/` - Create session
- `POST /api/formations/{id}/sessions/{session_id}/start/` - Start session
- `POST /api/formations/{id}/sessions/{session_id}/stop/` - Stop session

### Participants
- `GET /api/formations/participants/list/` - List participants
- `POST /api/formations/participants/` - Create participant
- `DELETE /api/formations/participants/{id}/` - Delete participant

### Formateurs
- `GET /api/formations/formateurs/list/` - List formateurs
- `POST /api/formations/formateurs/` - Create formateur
- `DELETE /api/formations/formateurs/{id}/` - Delete formateur

## Production Build

```bash
npm run build
```

The built files will be in the `dist/` directory. Serve these files with any static file server or configure your backend to serve them.
