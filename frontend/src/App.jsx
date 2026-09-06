import { useState, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import logo from './assets/logo-injs.svg'
import { AuthProvider, useAuth } from './context/AuthContext'
import { hasAppRole, getUserRoles } from './utils/roles'
import { ToastProvider } from './context/ToastContext'
import AppNotificationsBell from './components/AppNotificationsBell'
import Login from './pages/Login'
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
import Modules from './pages/Modules'
import Profile from './pages/Profile'
import FinanceDashboard from './pages/FinanceDashboard'
import FinanceParametrage from './pages/FinanceParametrage'
import FinanceAjustements from './pages/FinanceAjustements'
import FinanceEncadrants from './pages/FinanceEncadrants'
import EvaluationList from './pages/EvaluationList'
import EvaluationDetail from './pages/EvaluationDetail'
import EvaluationTake from './pages/EvaluationTake'
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
  STAFF_WEB_ROLES,
  USERS_ALLOWED_ROLES,
  IMPORT_ALLOWED_ROLES,
  EVALUATION_ALLOWED_ROLES,
  NOTE_GESTION_ROLES,
  DECISION_ROLES,
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

function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, loading, user } = useAuth()
  if (loading) return <div className="loading"><div className="spinner"></div></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (allowedRoles && !hasAppRole(user, allowedRoles)) return <Navigate to="/" replace />
  return children
}

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
  const canViewFinanceModule = hasAppRole(user, FINANCE_MODULE_ROLES) && !isArchiveRole
  const canViewFinanceDashboard = hasAppRole(user, FINANCE_EXPORT_ROLES) && !isArchiveRole
  const canViewFinanceSettings = hasAppRole(user, FINANCE_SETTINGS_ROLES)
  const canViewParticipants = hasAppRole(user, PARTICIPANT_LIST_ROLES)
  const canViewScolarite = hasAppRole(user, SCOLARITE_VIEW_ROLES)
  const canViewRattrapages = hasAppRole(user, PRESENCE_VIEW_ROLES)
  const canViewFormateurs = hasAppRole(user, [...ADMIN_LEVEL_ROLES, 'DIRECTION', 'ARCHIVE', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'SUPERVISEUR'])
    || canViewFinanceModule
  const canViewUsers = hasAppRole(user, [...ADMIN_LEVEL_ROLES, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT'])
  const canViewSecretariats = hasAppRole(user, ADMIN_LEVEL_ROLES)
  const canViewImport = hasAppRole(user, IMPORT_ALLOWED_ROLES)
  const canViewEvaluations = hasAppRole(user, EVALUATION_ALLOWED_ROLES)
  const canViewReferentiels = hasAppRole(user, ADMIN_LEVEL_ROLES)
  const canViewStatistiques = hasAppRole(user, STATS_ALLOWED_ROLES)
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
      <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <ProtectedRoute>
              <HomeRoute />
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
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Formations</li></>}>
                <Formations />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:formationId/modules/:moduleId/notes" element={
            <ProtectedRoute allowedRoles={NOTE_GESTION_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Notes</li></>}>
                <NotesModule />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:formationId/decisions" element={
            <ProtectedRoute allowedRoles={NOTE_GESTION_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Décisions pédagogiques</li></>}>
                <DecisionsPedagogiques />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:formationId/modules/:moduleId" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Cours</li></>}>
                <ModuleDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/auditeurs/:participantId/formations/:formationId/fiche" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Fiche étudiant</li></>}>
                <FicheAuditeur />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formateurs/:formateurId/modules/:moduleId/fiche" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Fiche enseignant</li></>}>
                <FicheFormateur />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:id" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Formation</li></>}>
                <FormationDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/modules" element={
            <ProtectedRoute allowedRoles={OPERATION_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Cours</li></>}>
                <Modules />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/participants" element={
            <ProtectedRoute allowedRoles={PARTICIPANT_LIST_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Étudiants</li></>}>
                <Participants />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Scolarité</li></>}>
                <ScolariteDashboard />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/candidatures" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Candidatures</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Candidatures />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/admissions" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Admissions</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <AdmissionsPage />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/inscriptions" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Inscriptions</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <Inscriptions />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/etudiants/:id" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Fiche étudiant</li></>}>
                <FicheEtudiant />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/scolarite/groupes" element={
            <ProtectedRoute allowedRoles={SCOLARITE_VIEW_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/scolarite">Scolarité</Link></li><li className="separator">/</li><li>Groupes</li></>}>
                <Suspense fallback={<div className="loading"><div className="spinner"/></div>}>
                  <GroupesPedagogiques />
                </Suspense>
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/rattrapages" element={
            <ProtectedRoute allowedRoles={PRESENCE_VIEW_ROLES}>
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
            <ProtectedRoute allowedRoles={OPERATIONAL_WEB_ROLES}>
              <DashboardRoute />
            </ProtectedRoute>
          } />
          <Route path="/finance-dashboard" element={
            <ProtectedRoute allowedRoles={FINANCE_EXPORT_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Tableau de Bord Finance</li></>}>
                <FinanceDashboard />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-ajustements" element={
            <ProtectedRoute allowedRoles={FINANCE_SETTINGS_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Ajustements Finance</li></>}>
                <FinanceAjustements />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-encadrants" element={
            <ProtectedRoute allowedRoles={FINANCE_EXPORT_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Encadrants Finance</li></>}>
                <FinanceEncadrants />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-parametrage" element={
            <ProtectedRoute allowedRoles={FINANCE_SETTINGS_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Paramétrage Finance</li></>}>
                <FinanceParametrage />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/users" element={
            <ProtectedRoute allowedRoles={USERS_ALLOWED_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Utilisateurs</li></>}>
                <Users />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/secretariats" element={
            <ProtectedRoute allowedRoles={ADMIN_LEVEL_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Secrétariats</li></>}>
                <Secretariats />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/import" element={
            <ProtectedRoute allowedRoles={IMPORT_ALLOWED_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Import Excel</li></>}>
                <ImportExcel />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/evaluations" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES}>
              <EvaluationRoute />
            </ProtectedRoute>
          } />
          <Route path="/evaluations/repondre/:id" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/evaluations">Évaluations</Link></li><li className="separator">/</li><li>Répondre</li></>}>
                <EvaluationTake />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/evaluations/:id" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><Link to="/evaluations">Évaluations</Link></li><li className="separator">/</li><li>Détail</li></>}>
                <EvaluationDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/evaluations/:id/analyse" element={
            <ProtectedRoute allowedRoles={EVALUATION_ALLOWED_ROLES}>
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
          <Route path="/statistiques" element={
            <ProtectedRoute allowedRoles={STATS_ALLOWED_ROLES}>
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}

export default App
