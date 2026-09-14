import { useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import logo from './assets/logo-injs.svg'
import { AuthProvider, useAuth } from './context/AuthContext'
import { hasAppRole, getUserRoles, peut } from './utils/roles'
import { ToastProvider } from './context/ToastContext'
import AppNotificationsBell from './components/AppNotificationsBell'
import ProtectedRoute, { FORCED_PASSWORD_PATH } from './components/auth/ProtectedRoute'
import CapabilitiesSync from './components/auth/CapabilitiesSync'
import Login from './pages/Login'
import ForcedPasswordChange from './pages/ForcedPasswordChange'
import Dashboard from './pages/Dashboard'
import Formations from './pages/Formations'
import FormationDetail from './pages/FormationDetail'
import ModuleDetail from './pages/ModuleDetail'
import Participants from './pages/Participants'
import Rattrapages from './pages/Rattrapages'
import Formateurs from './pages/Formateurs'
import Users from './pages/Users'
import ImportExcel from './pages/ImportExcel'
import Secretariats from './pages/Secretariats'
import Referentiels from './pages/Referentiels'
import Parametres from './pages/Parametres'
import FeatureFlags from './pages/FeatureFlags'
// U4 — console CURP d'administration des comptes (derrière le drapeau
// CURP_UI_ADMIN : sans la capacité habilitations_admin.gerer, rien n'apparaît).
import HabilitationsLayout from './pages/habilitations/HabilitationsLayout'
import ListeComptes from './pages/habilitations/ListeComptes'
import FicheCompte from './pages/habilitations/FicheCompte'
import AssistantCreation from './pages/habilitations/AssistantCreation'
import ModificationCompte from './pages/habilitations/ModifierCompte'
import GestionRoles from './pages/habilitations/GestionRoles'
import MatricePermissions from './pages/habilitations/MatricePermissions'
import Derogations from './pages/habilitations/Derogations'
import Delegations from './pages/habilitations/Delegations'
import OperationsMasse from './pages/habilitations/OperationsMasse'
import FileProvisionnement from './pages/habilitations/FileProvisionnement'
import NotificationsHabilitation from './pages/habilitations/NotificationsHabilitation'
import RevueHabilitations from './pages/habilitations/RevueHabilitations'
import JournalHabilitations from './pages/habilitations/JournalHabilitations'
import Modules from './pages/Modules'
import Profile from './pages/Profile'
import FinanceDashboard from './pages/FinanceDashboard'
import FinanceParametrage from './pages/FinanceParametrage'
import FinanceAjustements from './pages/FinanceAjustements'
import FinanceEncadrants from './pages/FinanceEncadrants'
import EvaluationList from './pages/EvaluationList'
import EvaluationDetail from './pages/EvaluationDetail'
import EvaluationTake from './pages/EvaluationTake'
import Edts from './pages/Edts'
import EdtNew from './pages/EdtNew'
import AffectationNew from './pages/AffectationNew'

import FicheAuditeur from './pages/FicheAuditeur'
import FicheFormateur from './pages/FicheFormateur'
import EvaluationDashboard from './pages/EvaluationDashboard'
import AnalyseQualitative from './pages/AnalyseQualitative'
import NotesModule from './pages/NotesModule'
import DecisionsPedagogiques from './pages/DecisionsPedagogiques'
import ArchivesDashboard from './pages/archives/ArchivesDashboard'
import ArchiveListesNotes from './pages/archives/ArchiveListesNotes'
import ArchiveCahiersAppel from './pages/archives/ArchiveCahiersAppel'
import ModulesListLink from './components/ModulesListLink'
import { LIST_STORAGE_KEYS, listHref } from './utils/listFilters'
import { financeNavHref } from './utils/financePeriod'
import {
  ADMIN_LEVEL_ROLES,
  STATS_ALLOWED_ROLES,
  USERS_ALLOWED_ROLES,
  IMPORT_ALLOWED_ROLES,
  EVALUATION_ALLOWED_ROLES,
  NOTE_GESTION_ROLES,
  FINANCE_MODULE_ROLES,
  FINANCE_EXPORT_ROLES,
  FINANCE_SETTINGS_ROLES,
  OPERATION_VIEW_ROLES,
  OPERATIONAL_WEB_ROLES,
  PARTICIPANT_LIST_ROLES,
  ARCHIVE_CONSULT_ROLES,
  PRESENCE_VIEW_ROLES,
  SCOLARITE_VIEW_ROLES,
} from './utils/roles'

const Statistiques = lazy(() => import('./pages/Statistiques'))
const ScolariteDashboard = lazy(() => import('./pages/scolarite/ScolariteDashboard'))
const Candidatures = lazy(() => import('./pages/scolarite/Candidatures'))
const AdmissionsPage = lazy(() => import('./pages/scolarite/Admissions'))
const Inscriptions = lazy(() => import('./pages/scolarite/Inscriptions'))
const FicheEtudiant = lazy(() => import('./pages/scolarite/FicheEtudiant'))
const GroupesPedagogiques = lazy(() => import('./pages/scolarite/Groupes'))
const Maquettes = lazy(() => import('./pages/scolarite/Maquettes'))
const MaquetteDetail = lazy(() => import('./pages/scolarite/MaquetteDetail'))
const Campagnes = lazy(() => import('./pages/scolarite/Campagnes'))
const CampagneDetail = lazy(() => import('./pages/scolarite/CampagneDetail'))
const MonEspace = lazy(() => import('./pages/scolarite/MonEspace'))
const Equivalences = lazy(() => import('./pages/scolarite/Equivalences'))
const ChargesEnseignants = lazy(() => import('./pages/scolarite/ChargesEnseignants'))
const Jurys = lazy(() => import('./pages/scolarite/Jurys'))
const Graduation = lazy(() => import('./pages/scolarite/Graduation'))
const FinancesEtudiantes = lazy(() => import('./pages/scolarite/FinancesEtudiantes'))


function Layout({ children, breadcrumb }) {
  const { user } = useAuth()
  const location = useLocation()
  const path = location.pathname
  const searchTab = new URLSearchParams(location.search).get('tab')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const isMobileViewport = () => window.matchMedia('(max-width: 768px)').matches
  const toggleSidebar = () => {
    if (isMobileViewport()) {
      setSidebarOpen((o) => !o)
      return
    }
    setSidebarCollapsed((c) => !c)
  }

  const isActive = (route) => {
    if (route === '/') return path === '/'
    if (route === '/formations') return path.startsWith('/formations') && !path.includes('/modules/')
    return path.startsWith(route)
  }

  const isFinanceRole = hasAppRole(user, ['FINANCE'])
  const isArchiveRole = hasAppRole(user, ['ARCHIVE'])
  const isSuperviseurRole = hasAppRole(user, ['SUPERVISEUR'])
  // P00-06 : la visibilité des entrées de menu dérive des capacités backend
  // (repli statique identique tant qu'elles ne sont pas chargées).
  const canViewFinanceModule = peut(user, 'finance', 'voir') && !isArchiveRole
  const canViewFinanceDashboard = peut(user, 'finance', 'exporter') && !isArchiveRole
  const canViewFinanceSettings = peut(user, 'finance', 'parametrer')
  const canViewParticipants = peut(user, 'participants', 'lister')
  const canViewScolarite = peut(user, 'scolarite', 'voir')
  const canViewRattrapages = peut(user, 'presences', 'voir')
  const canViewFormateurs = hasAppRole(user, [...ADMIN_LEVEL_ROLES, 'DIRECTION', 'ARCHIVE', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'SUPERVISEUR'])
    || canViewFinanceModule
  const canViewUsers = peut(user, 'utilisateurs', 'voir')
  const canViewHabilitations = peut(user, 'habilitations_admin', 'gerer')
  const canViewSecretariats = hasAppRole(user, ADMIN_LEVEL_ROLES)
  const canViewImport = peut(user, 'participants', 'gerer')
  const canViewEvaluations = peut(user, 'evaluations', 'gerer_questionnaires')
  const canViewReferentiels = hasAppRole(user, ADMIN_LEVEL_ROLES)
  const canViewStatistiques = peut(user, 'statistiques', 'voir')
  const isDirection = hasAppRole(user, ['DIRECTION'])
  const canViewFinanceNotifications = hasAppRole(user, FINANCE_MODULE_ROLES) && !hasAppRole(user, ['ARCHIVE'])
  const showAppNotifications = isDirection || canViewStatistiques || canViewFinanceNotifications

  const ROLE_LABELS = { ADMIN: 'Administrateur', DIRECTION: 'Direction', CHEF_CPFAE_ADMIN: 'Chef INJS Admin', CPFAE_ADMIN: 'INJS Admin', CHEF_SECRETARIAT: 'Chef Secrétariat', SECRETARIAT: 'Secrétariat', FINANCE: 'Finance', ARCHIVE: 'Archiviste', ENCADRANT: 'Encadrant', SUPERVISEUR: 'Superviseur', FORMATEUR: 'Enseignant', AUDITEUR: 'Étudiant' }
  const userInitials = `${(user?.first_name || '')[0] || ''}${(user?.last_name || '')[0] || ''}`
  const fullName = user?.get_full_name ? user.get_full_name() : `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.username

  return (
    <div className={`app-container${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
            zIndex: 99, display: 'block'
          }}
        />
      )}
      <aside className={`sidebar${sidebarOpen ? ' show' : ''}`} id="sidebar">
        <div className="sidebar-brand">
          <img src={logo} alt="INJS Abidjan" className="sidebar-logo" />
          <h5 style={{ marginBottom: '0.1rem' }}>INJS UFR STAPS-JL</h5>
          <small>Institut National de la Jeunesse et des Sports</small>
        </div>

        {user && (
          <div className="sidebar-user">
            <small>Connecté en tant que</small><br/>
            <span className="user-name">{fullName}</span><br/>
            {hasAppRole(user, ['SECRETARIAT']) && user.secretariat_nom
              ? <small style={{ color: 'rgba(255,255,255,0.65)', fontSize: '0.75rem' }}><i className="bi bi-building me-1"></i>{user.secretariat_nom}</small>
              : <span className="user-role">{getUserRoles(user).map((r) => ROLE_LABELS[r] || r).join(', ') || user.role}</span>
            }
          </div>
        )}

        <nav className="sidebar-nav">
          
          {!isFinanceRole && !isArchiveRole && !isSuperviseurRole && (
            <Link to={listHref('/dashboard', LIST_STORAGE_KEYS.dashboard)} className={`nav-item ${isActive('/dashboard') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-speedometer2"></i> <span className="nav-label">Tableau de bord</span></span>
            </Link>
          )}

          {isArchiveRole && (
            <>
              <Link to="/archives" className={`nav-item ${path === '/archives' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-archive"></i> <span className="nav-label">Tableau de bord</span></span>
              </Link>
              <Link to="/archives/listes-notes" className={`nav-item ${isActive('/archives/listes-notes') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-card-checklist"></i> <span className="nav-label">Listes de note</span></span>
              </Link>
              <Link to="/archives/cahiers-appel" className={`nav-item ${isActive('/archives/cahiers-appel') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-journal-check"></i> <span className="nav-label">Cahiers d'appel</span></span>
              </Link>
            </>
          )}

          {canViewFinanceDashboard && (
            <Link to={financeNavHref('/finance-dashboard')} className={`nav-item ${isActive('/finance-dashboard') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-speedometer2"></i> <span className="nav-label">Tableau de Bord Finance</span></span>
            </Link>
          )}
          {canViewStatistiques && (
            <Link to="/statistiques" className={`nav-item ${isActive('/statistiques') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-bar-chart-line"></i> <span className="nav-label">Statistiques</span></span>
            </Link>
          )}
          {!isFinanceRole && !isArchiveRole && (
            <Link to={listHref('/modules', LIST_STORAGE_KEYS.modules)} className={`nav-item ${isActive('/modules') || isActive('/formations') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-book"></i> <span className="nav-label">Cours</span></span>
            </Link>
          )}
          {canViewParticipants && (
            <Link to={listHref('/participants', LIST_STORAGE_KEYS.participants)} className={`nav-item ${isActive('/participants') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-people"></i> <span className="nav-label">Étudiants</span></span>
            </Link>
          )}
          {canViewScolarite && (
            <>
              <div className="nav-section-title">Scolarité LMD</div>
              <Link to="/scolarite" className={`nav-item ${path === '/scolarite' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-mortarboard"></i> <span className="nav-label">Tableau de bord</span></span>
              </Link>
              <Link to="/scolarite/candidatures" className={`nav-item ${isActive('/scolarite/candidatures') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-file-earmark-person"></i> <span className="nav-label">Candidatures</span></span>
              </Link>
              <Link to="/scolarite/admissions" className={`nav-item ${isActive('/scolarite/admissions') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-check2-circle"></i> <span className="nav-label">Admissions</span></span>
              </Link>
              <Link to="/scolarite/inscriptions" className={`nav-item ${isActive('/scolarite/inscriptions') || isActive('/scolarite/etudiants') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-journal-check"></i> <span className="nav-label">Inscriptions</span></span>
              </Link>
              <Link to="/scolarite/groupes" className={`nav-item ${isActive('/scolarite/groupes') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-diagram-3"></i> <span className="nav-label">Groupes</span></span>
              </Link>
              <Link to="/scolarite/maquettes" className={`nav-item ${isActive('/scolarite/maquettes') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-layout-text-window-reverse"></i> <span className="nav-label">Maquettes LMD</span></span>
              </Link>
              <Link to="/scolarite/campagnes" className={`nav-item ${isActive('/scolarite/campagnes') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-megaphone"></i> <span className="nav-label">Campagnes</span></span>
              </Link>
              <Link to="/scolarite/equivalences" className={`nav-item ${isActive('/scolarite/equivalences') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-arrow-left-right"></i> <span className="nav-label">Équivalences</span></span>
              </Link>
              <Link to="/scolarite/charges" className={`nav-item ${isActive('/scolarite/charges') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-person-workspace"></i> <span className="nav-label">Charges pédagogiques</span></span>
              </Link>
              <Link to="/scolarite/jurys" className={`nav-item ${isActive('/scolarite/jurys') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-clipboard-check"></i> <span className="nav-label">Jurys LMD</span></span>
              </Link>
              <Link to="/scolarite/graduation" className={`nav-item ${isActive('/scolarite/graduation') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-mortarboard-fill"></i> <span className="nav-label">Diplômation</span></span>
              </Link>
              <Link to="/scolarite/finances" className={`nav-item ${isActive('/scolarite/finances') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-cash-coin"></i> <span className="nav-label">Finances étudiantes</span></span>
              </Link>
            </>
          )}
          {canViewRattrapages && (
            <Link to="/rattrapages" className={`nav-item ${isActive('/rattrapages') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-arrow-left-right"></i> <span className="nav-label">Rattrapages</span></span>
            </Link>
          )}
          {canViewFormateurs && (
            <Link
              to={canViewFinanceModule ? financeNavHref('/formateurs') : listHref('/formateurs', LIST_STORAGE_KEYS.formateurs)}
              className={`nav-item ${isActive('/formateurs') ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              <span>
                <i className={`bi ${canViewFinanceModule ? 'bi-cash-stack' : 'bi-person-video3'}`}></i>
                {' '}
                <span className="nav-label">{canViewFinanceModule ? 'Suivi Finance' : 'Enseignants'}</span>
              </span>
            </Link>
          )}
          {canViewFinanceDashboard && (
            <Link to={financeNavHref('/finance-encadrants')} className={`nav-item ${isActive('/finance-encadrants') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-person-badge"></i> <span className="nav-label">Encadrants</span></span>
            </Link>
          )}
          {canViewFinanceSettings && (
            <Link to={financeNavHref('/finance-parametrage')} className={`nav-item ${isActive('/finance-parametrage') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-sliders"></i> <span className="nav-label">Paramétrage</span></span>
            </Link>
          )}
          {canViewUsers && (
            <Link to={listHref('/users', LIST_STORAGE_KEYS.users)} className={`nav-item ${isActive('/users') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-person-gear"></i> <span className="nav-label">Utilisateurs</span></span>
            </Link>
          )}
          {canViewHabilitations && (
            <Link to="/administration/comptes" className={`nav-item ${path.startsWith('/administration/comptes') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)} data-testid="nav-habilitations">
              <span><i className="bi bi-shield-lock"></i> <span className="nav-label">Habilitations (CURP)</span></span>
            </Link>
          )}
          {canViewSecretariats && (
            <Link to={listHref('/secretariats', LIST_STORAGE_KEYS.secretariats)} className={`nav-item ${isActive('/secretariats') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-building"></i> <span className="nav-label">Secrétariats</span></span>
            </Link>
          )}
          {isSuperviseurRole && (
            <Link to="/evaluations?tab=dashboard" className={`nav-item ${isActive('/evaluations') && searchTab !== 'questionnaires' && !path.includes('/analyse') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-speedometer2"></i> <span className="nav-label">Dashboard</span></span>
            </Link>
          )}
          {isSuperviseurRole && (
            <Link to="/evaluations?tab=questionnaires" className={`nav-item ${isActive('/evaluations') && searchTab === 'questionnaires' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-clipboard-check"></i> <span className="nav-label">Évaluations</span></span>
            </Link>
          )}
          {canViewEvaluations && !isSuperviseurRole && (
            <>
              <Link to="/evaluations" className={`nav-item ${isActive('/evaluations') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <span><i className="bi bi-clipboard-check"></i> <span className="nav-label">Évaluations</span></span>
              </Link>
            </>
          )}
          {canViewImport && (
            <Link to="/import" className={`nav-item ${isActive('/import') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-file-earmark-excel"></i> <span className="nav-label">Import Excel</span></span>
            </Link>
          )}
          {canViewReferentiels && (
            <Link to={listHref('/referentiels', LIST_STORAGE_KEYS.referentiels)} className={`nav-item ${isActive('/referentiels') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-sliders"></i> <span className="nav-label">Référentiels</span></span>
            </Link>
          )}
          {canViewReferentiels && (
            <Link to="/parametres" className={`nav-item ${path === '/parametres' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-gear"></i> <span className="nav-label">Paramètres</span></span>
            </Link>
          )}
          {canViewReferentiels && (
            <Link to="/parametres/flags" className={`nav-item ${path === '/parametres/flags' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-toggles"></i> <span className="nav-label">Fonctionnalités</span></span>
            </Link>
          )}
        </nav>

        <div className="sidebar-footer">
          <Link to="/profile" className={`nav-item ${path === '/profile' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
            <span><i className="bi bi-person-circle"></i> <span className="nav-label">Mon profil</span></span>
          </Link>
          <div className="nav-label" style={{ textAlign: 'center', padding: '0.75rem 0 0.25rem', fontSize: '0.68rem', color: 'rgba(255,255,255,0.5)', lineHeight: 1.4 }}>
            Développé par<br/>
            <span style={{ fontWeight: 600, letterSpacing: '0.02em' }}>Ophir Technologies</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <div className="top-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button className="btn btn-sm btn-outline-secondary sidebar-toggle" onClick={toggleSidebar}>
              <i className={`bi ${isMobileViewport() ? 'bi-list' : (sidebarCollapsed ? 'bi-layout-sidebar-inset' : 'bi-layout-sidebar')}`}></i>
            </button>
            <nav>
              <ol className="breadcrumb">
                {breadcrumb || <li>Accueil</li>}
              </ol>
            </nav>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            {showAppNotifications && (
              <AppNotificationsBell
                showNotes={isDirection}
                showRapports={canViewStatistiques}
                showFinance={canViewFinanceNotifications}
              />
            )}
            <Link to="/profile" className="top-bar-user" title="Mon profil" style={{ textDecoration: 'none', color: 'inherit' }}>
              <span className="text-muted small">{fullName}</span>
              <div className="user-avatar">{userInitials}</div>
            </Link>
          </div>
        </div>
        <div className="page-content">
          {children}
        </div>
      </main>
    </div>
  )
}

function App() {
  function HomeRoute() {
    const { user } = useAuth()
    // FINANCE est redirigé vers finance-dashboard par défaut
    if (user?.role === 'FINANCE') return <Navigate to="/finance-dashboard" replace />
    if (user?.role === 'ARCHIVE') return <Navigate to="/archives" replace />
    // DIRECTION peut choisir entre les deux dashboards
    if (user?.role === 'SUPERVISEUR') return <Navigate to="/evaluations" replace />
    return (
      <Layout breadcrumb={<li>Tableau de bord</li>}>
        <Dashboard />
      </Layout>
    )
  }

  function DashboardRoute() {
    return (
      <Layout breadcrumb={<li>Tableau de bord</li>}>
        <Dashboard />
      </Layout>
    )
  }

  function EvaluationRoute() {
    const { user } = useAuth()
    return (
      <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Évaluations</li></>}>
        {user?.role === 'SUPERVISEUR' ? <EvaluationDashboard /> : <EvaluationList />}
      </Layout>
    )
  }

  return (
    <AuthProvider>
      <CapabilitiesSync />
      <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path={FORCED_PASSWORD_PATH} element={
            <ProtectedRoute>
              <ForcedPasswordChange />
            </ProtectedRoute>
          } />
          <Route path="/" element={
            <ProtectedRoute>
              <HomeRoute />
            </ProtectedRoute>
          } />
          <Route path="/mon-espace" element={
            <ProtectedRoute>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Mon espace étudiant</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <MonEspace />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Mon profil</li></>}>
                <Profile />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Formations</li></>}>
                <Formations />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:formationId/modules/:moduleId/notes" element={
            <ProtectedRoute allowedRoles={NOTE_GESTION_ROLES} capacite={{ module: 'notes', action: 'gerer' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Notes</li></>}>
                <NotesModule />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:formationId/decisions" element={
            <ProtectedRoute allowedRoles={NOTE_GESTION_ROLES} capacite={{ module: 'notes', action: 'gerer' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Décisions pédagogiques</li></>}>
                <DecisionsPedagogiques />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:formationId/modules/:moduleId" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Cours</li></>}>
                <ModuleDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/auditeurs/:participantId/formations/:formationId/fiche" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Fiche étudiant</li></>}>
                <FicheAuditeur />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formateurs/:formateurId/modules/:moduleId/fiche" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Fiche enseignant</li></>}>
                <FicheFormateur />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:id" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Formation</li></>}>
                <FormationDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/modules" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Cours</li></>}>
                <Modules />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/participants" element={
            <ProtectedRoute allowedRoles={PARTICIPANT_LIST_ROLES} capacite={{ module: 'participants', action: 'lister' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Étudiants</li></>}>
                <Participants />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Scolarité</li></>}>
                <ScolariteDashboard />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/candidatures" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Candidatures</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Candidatures />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/admissions" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Admissions</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <AdmissionsPage />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/inscriptions" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Inscriptions</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Inscriptions />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/etudiants/:id" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Fiche étudiant</li></>}>
                <FicheEtudiant />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/groupes" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Groupes</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <GroupesPedagogiques />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/maquettes" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Maquettes LMD</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Maquettes />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/maquettes/:id" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li><Link to="/scolarite/maquettes">Maquettes LMD</Link></li><li className="separator">/</li><li>Détail</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <MaquetteDetail />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/campagnes" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Campagnes d'admission</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Campagnes />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/campagnes/:id" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li><Link to="/scolarite/campagnes">Campagnes</Link></li><li className="separator">/</li><li>Détail</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <CampagneDetail />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/equivalences" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Équivalences et dispenses</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Equivalences />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/charges" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Charges pédagogiques</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <ChargesEnseignants />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/jurys" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Sessions de jury</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Jurys />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/graduation" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Diplômation</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Graduation />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/finances" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES} capacite={{ module: 'scolarite', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Finances étudiantes</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <FinancesEtudiantes />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/rattrapages" element={
            <ProtectedRoute allowedRoles={PRESENCE_VIEW_ROLES} capacite={{ module: 'presences', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Rattrapages</li></>}>
                <Rattrapages />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formateurs" element={
            <ProtectedRoute allowedRoles={[...OPERATION_VIEW_ROLES, 'FINANCE']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Enseignants</li></>}>
                <Formateurs />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute allowedRoles={OPERATIONAL_WEB_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <DashboardRoute />
            </ProtectedRoute>
          } />
          <Route path="/finance-dashboard" element={
            <ProtectedRoute allowedRoles={FINANCE_EXPORT_ROLES} capacite={{ module: 'finance', action: 'exporter' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Tableau de Bord Finance</li></>}>
                <FinanceDashboard />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-ajustements" element={
            <ProtectedRoute allowedRoles={FINANCE_SETTINGS_ROLES} capacite={{ module: 'finance', action: 'parametrer' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Ajustements Finance</li></>}>
                <FinanceAjustements />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-encadrants" element={
            <ProtectedRoute allowedRoles={FINANCE_EXPORT_ROLES} capacite={{ module: 'finance', action: 'exporter' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Encadrants Finance</li></>}>
                <FinanceEncadrants />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-parametrage" element={
            <ProtectedRoute allowedRoles={FINANCE_SETTINGS_ROLES} capacite={{ module: 'finance', action: 'parametrer' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Paramétrage Finance</li></>}>
                <FinanceParametrage />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/users" element={
            <ProtectedRoute allowedRoles={USERS_ALLOWED_ROLES} capacite={{ module: 'utilisateurs', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Utilisateurs</li></>}>
                <Users />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/administration/comptes" element={
            <ProtectedRoute capacite={{ module: 'habilitations_admin', action: 'gerer' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Habilitations</li></>}>
                <HabilitationsLayout />
              </Layout>
            </ProtectedRoute>
          }>
            <Route index element={<ListeComptes />} />
            <Route path="nouveau" element={<AssistantCreation />} />
            <Route path="provisionnement" element={<FileProvisionnement />} />
            <Route path="operations-masse" element={<OperationsMasse />} />
            <Route path="notifications" element={<NotificationsHabilitation />} />
            <Route path="revue" element={<RevueHabilitations />} />
            <Route path="journal" element={<JournalHabilitations />} />
            <Route path="roles" element={<GestionRoles />} />
            <Route path="matrice" element={<MatricePermissions />} />
            <Route path="derogations" element={<Derogations />} />
            <Route path="delegations" element={<Delegations />} />
            <Route path=":id" element={<FicheCompte />} />
            <Route path=":id/modifier" element={<ModificationCompte />} />
          </Route>
          <Route path="/secretariats" element={
            <ProtectedRoute allowedRoles={ADMIN_LEVEL_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Secrétariats</li></>}>
                <Secretariats />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/import" element={
            <ProtectedRoute allowedRoles={IMPORT_ALLOWED_ROLES} capacite={{ module: 'participants', action: 'gerer' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Import Excel</li></>}>
                <ImportExcel />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/evaluations" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES} capacite={{ module: 'evaluations', action: 'gerer_questionnaires' }}>
              <EvaluationRoute />
            </ProtectedRoute>
          } />
          <Route path="/evaluations/repondre/:id" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES} capacite={{ module: 'evaluations', action: 'gerer_questionnaires' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/evaluations">Évaluations</Link></li><li className="separator">/</li><li>Répondre</li></>}>
                <EvaluationTake />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/evaluations/:id" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES} capacite={{ module: 'evaluations', action: 'gerer_questionnaires' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/evaluations">Évaluations</Link></li><li className="separator">/</li><li>Détail</li></>}>
                <EvaluationDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/evaluations/:id/analyse" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES} capacite={{ module: 'evaluations', action: 'gerer_questionnaires' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/evaluations">Évaluations</Link></li><li className="separator">/</li><li>Analyse qualitative</li></>}>
                <AnalyseQualitative />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/referentiels" element={
            <ProtectedRoute allowedRoles={ADMIN_LEVEL_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Référentiels</li></>}>
                <Referentiels />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/parametres" element={
            <ProtectedRoute allowedRoles={ADMIN_LEVEL_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Paramètres</li></>}>
                <Parametres />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/parametres/flags" element={
            <ProtectedRoute allowedRoles={ADMIN_LEVEL_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/parametres">Paramètres</Link></li><li className="separator">/</li><li>Fonctionnalités</li></>}>
                <FeatureFlags />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/statistiques" element={
            <ProtectedRoute allowedRoles={STATS_ALLOWED_ROLES} capacite={{ module: 'statistiques', action: 'voir' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Statistiques</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Statistiques />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/archives" element={
            <ProtectedRoute allowedRoles={ARCHIVE_CONSULT_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Archives</li></>}>
                <ArchivesDashboard />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/archives/listes-notes" element={
            <ProtectedRoute allowedRoles={ARCHIVE_CONSULT_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/archives">Archives</Link></li><li className="separator">/</li><li>Listes de note</li></>}>
                <ArchiveListesNotes />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/archives/cahiers-appel" element={
            <ProtectedRoute allowedRoles={ARCHIVE_CONSULT_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/archives">Archives</Link></li><li className="separator">/</li><li>Cahiers d'appel</li></>}>
                <ArchiveCahiersAppel />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/edt" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Emplois du temps</li></>}>
                <Edts />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/edt/nouveau" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/edt">Emplois du temps</Link></li><li className="separator">/</li><li>Nouvel EDT</li></>}>
                <EdtNew />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/edt/:edtId/affectation/nouveau" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES} capacite={{ module: 'web', action: 'operationnel' }}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/edt">Emplois du temps</Link></li><li className="separator">/</li><li>Nouvelle affectation</li></>}>
                <AffectationNew />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}

export default App
