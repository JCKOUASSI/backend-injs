import { FiGrid, FiUsers, FiBookOpen, FiCalendar, FiClipboard, FiAward, FiBriefcase, FiDollarSign, FiSettings, FiHome, FiClock, FiFileText, FiTrendingUp, FiCheckSquare, FiLayers, FiUserCheck, FiBarChart2, FiCreditCard, FiUserPlus, FiMap, FiTool, FiBox, FiMapPin } from 'react-icons/fi'

export const ADMIN_MENU = [
  { section: 'Principal' },
  { path: '/admin', icon: FiGrid, label: 'Tableau de bord' },
  { path: '/admin/etudiants', icon: FiUsers, label: 'Étudiants' },
  { path: '/admin/professeurs', icon: FiUserCheck, label: 'Professeurs' },
  { path: '/admin/departements', icon: FiLayers, label: 'Départements & UFR' },
  { path: '/admin/referentiels', icon: FiSettings, label: 'Référentiels' },
  { path: '/admin/import-excel', icon: FiFileText, label: 'Import Excel' },
  { path: '/admin/admissions', icon: FiUserPlus, label: 'Admissions' },
  { section: 'Pédagogie LMD' },
  { path: '/admin/formations', icon: FiBookOpen, label: 'Formations (L/M/D)' },
  { path: '/admin/ue', icon: FiClipboard, label: 'Unités d\'Enseignement' },
  { path: '/admin/notes', icon: FiAward, label: 'Notes & Validation' },
  { path: '/admin/emploi-du-temps', icon: FiClock, label: 'Emplois du temps' },
  { path: '/admin/presences', icon: FiCheckSquare, label: 'Présences' },
  { path: '/admin/salles', icon: FiMap, label: 'Gestion des salles' },
  { path: '/admin/stages', icon: FiBriefcase, label: 'Stages' },
  { section: 'Campus & infrastructures' },
  { path: '/admin/reservations', icon: FiCalendar, label: 'Réservations' },
  { path: '/admin/maintenance', icon: FiTool, label: 'Maintenance' },
  { path: '/admin/equipements', icon: FiBox, label: 'Équipements' },
  { path: '/admin/carte-campus', icon: FiMapPin, label: 'Carte du campus' },
  { section: 'Administration' },
  { path: '/admin/evenements', icon: FiCalendar, label: 'Événements' },
  { path: '/admin/finances', icon: FiDollarSign, label: 'Finances' },
  { path: '/admin/statistiques', icon: FiTrendingUp, label: 'Statistiques' },
  { path: '/admin/rapports', icon: FiBarChart2, label: 'Rapports' },
  { path: '/admin/parametres', icon: FiSettings, label: 'Paramètres' },
]

export const PROFESSEUR_MENU = [
  { section: 'Principal' },
  { path: '/professeur', icon: FiGrid, label: 'Tableau de bord' },
  { path: '/professeur/cours', icon: FiBookOpen, label: 'Mes cours & UE' },
  { path: '/professeur/emploi-du-temps', icon: FiCalendar, label: 'Mon emploi du temps' },
  { path: '/professeur/presences', icon: FiCheckSquare, label: 'Présences' },
  { path: '/professeur/etudiants', icon: FiUsers, label: 'Mes étudiants' },
  { path: '/professeur/salles', icon: FiMap, label: 'Campus & salles' },
  { section: 'Évaluation APC' },
  { path: '/professeur/evaluations', icon: FiClipboard, label: 'Évaluations (CC/CT)' },
  { path: '/professeur/stages', icon: FiBriefcase, label: 'Suivi stages' },
  { section: 'Recherche' },
  { path: '/professeur/recherche', icon: FiTrendingUp, label: 'Projets recherche' },
  { path: '/professeur/documents', icon: FiFileText, label: 'Documents' },
]

export const ETUDIANT_MENU = [
  { section: 'Principal' },
  { path: '/etudiant', icon: FiHome, label: 'Tableau de bord' },
  { path: '/etudiant/parcours', icon: FiTrendingUp, label: 'Mon parcours LMD' },
  { path: '/etudiant/notes', icon: FiAward, label: 'Mes notes & crédits' },
  { section: 'Formation' },
  { path: '/etudiant/cours', icon: FiBookOpen, label: 'Mes UE / ECUE' },
  { path: '/etudiant/emploi-du-temps', icon: FiCalendar, label: 'Emploi du temps' },
  { path: '/etudiant/presences', icon: FiCheckSquare, label: 'Présences' },
  { path: '/etudiant/stages', icon: FiBriefcase, label: 'Mes stages' },
  { section: 'Services' },
  { path: '/etudiant/documents', icon: FiFileText, label: 'Documents & relevés' },
  { path: '/etudiant/paiements', icon: FiCreditCard, label: 'Mes paiements' },
  { path: '/etudiant/inscriptions', icon: FiClipboard, label: 'Inscriptions' },
]

export function getMenuByRole(role) {
  switch (role) {
    case 'admin': return ADMIN_MENU
    case 'professeur': return PROFESSEUR_MENU
    case 'etudiant': return ETUDIANT_MENU
    default: return []
  }
}

export function getRoleLabel(role) {
  switch (role) {
    case 'admin': return 'Administration'
    case 'professeur': return 'Professeur'
    case 'etudiant': return 'Étudiant'
    default: return role
  }
}

export function getRoleBasePath(role) {
  switch (role) {
    case 'admin': return '/admin'
    case 'professeur': return '/professeur'
    case 'etudiant': return '/etudiant'
    default: return '/'
  }
}
