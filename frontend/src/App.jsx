import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import logo from './assets/logo.png'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Formations from './pages/Formations'
import FormationDetail from './pages/FormationDetail'
import ModuleDetail from './pages/ModuleDetail'
import Participants from './pages/Participants'
import Formateurs from './pages/Formateurs'
import Users from './pages/Users'
import ImportExcel from './pages/ImportExcel'
import Secretariats from './pages/Secretariats'
import Referentiels from './pages/Referentiels'
import Modules from './pages/Modules'
import Profile from './pages/Profile'
import FinanceDashboard from './pages/FinanceDashboard'
import FinanceParametrage from './pages/FinanceParametrage'
import ModulesListLink from './components/ModulesListLink'
import { LIST_STORAGE_KEYS, listHref } from './utils/listFilters'
import { financeNavHref } from './utils/financePeriod'

function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, loading, user } = useAuth()
  if (loading) return <div className="loading"><div className="spinner"></div></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (allowedRoles && !allowedRoles.includes(user?.role)) return <Navigate to="/" replace />
  return children
}

function Layout({ children, breadcrumb }) {
  const { user } = useAuth()
  const location = useLocation()
  const path = location.pathname
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

  const isFinanceRole = user?.role === 'FINANCE'
  const canViewFinanceDashboard = ['FINANCE', 'DIRECTION'].includes(user?.role)
  const canViewParticipants = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT'].includes(user?.role)
  const canViewFormateurs = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'FINANCE', 'ENCADRANT'].includes(user?.role)
  const canViewUsers = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT'].includes(user?.role)
  const canViewSecretariats = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN'].includes(user?.role)
  const canViewImport = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT'].includes(user?.role)
  const canViewReferentiels = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN'].includes(user?.role)

  const ROLE_LABELS = { DIRECTION: 'Direction', CHEF_CPFAE_ADMIN: 'Chef CPFAE Admin', CPFAE_ADMIN: 'CPFAE Admin', CHEF_SECRETARIAT: 'Chef Secrétariat', SECRETARIAT: 'Secrétariat', FINANCE: 'Finance', ENCADRANT: 'Encadrant', FORMATEUR: 'Formateur', AUDITEUR: 'Auditeur' }
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
          <img src={logo} alt="MEMFPMA" style={{ width: '80px', marginBottom: '0.5rem' }} />
          <h5 style={{ marginBottom: '0.1rem' }}>SYGEP-CPFAE</h5>
          <small>DFRC — Gestion des présences</small>
        </div>

        {user && (
          <div className="sidebar-user">
            <small>Connecté en tant que</small><br/>
            <span className="user-name">{fullName}</span><br/>
            {user.role === 'SECRETARIAT' && user.secretariat_nom
              ? <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}><i className="bi bi-building me-1"></i>{user.secretariat_nom}</small>
              : <span className="user-role">{ROLE_LABELS[user.role] || user.role}</span>
            }
          </div>
        )}

        <nav className="sidebar-nav">
          {canViewFinanceDashboard && (
            <Link to={financeNavHref('/finance-dashboard')} className={`nav-item ${isActive('/finance-dashboard') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-speedometer2"></i> <span className="nav-label">Dashboard Finance</span></span>
            </Link>
          )}
          {!isFinanceRole && (
            <Link to={listHref('/', LIST_STORAGE_KEYS.dashboard)} className={`nav-item ${isActive('/') && path === '/' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-speedometer2"></i> <span className="nav-label">Tableau de bord</span></span>
            </Link>
          )}
          {!isFinanceRole && (
            <Link to={listHref('/modules', LIST_STORAGE_KEYS.modules)} className={`nav-item ${isActive('/modules') || isActive('/formations') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-book"></i> <span className="nav-label">Cours</span></span>
            </Link>
          )}
          {canViewParticipants && (
            <Link to={listHref('/participants', LIST_STORAGE_KEYS.participants)} className={`nav-item ${isActive('/participants') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className="bi bi-people"></i> <span className="nav-label">Auditeurs</span></span>
            </Link>
          )}
          {canViewFormateurs && (
            <Link to={isFinanceRole ? financeNavHref('/formateurs') : listHref('/formateurs', LIST_STORAGE_KEYS.formateurs)} className={`nav-item ${isActive('/formateurs') ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span><i className={`bi ${isFinanceRole ? 'bi-cash-stack' : 'bi-person-video3'}`}></i> <span className="nav-label">{isFinanceRole ? 'Suivi Finance' : 'Formateurs'}</span></span>
            </Link>
          )}
          {canViewFinanceDashboard && (
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
        </nav>

        <div className="sidebar-footer">
          <Link to="/profile" className={`nav-item ${path === '/profile' ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
            <span><i className="bi bi-person-circle"></i> <span className="nav-label">Mon profil</span></span>
          </Link>
          <div className="nav-label" style={{ textAlign: 'center', padding: '0.75rem 0 0.25rem', fontSize: '0.68rem', color: 'var(--text-muted)', opacity: 0.7, lineHeight: 1.4 }}>
            Developpé par<br/>
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
          <Link to="/profile" className="top-bar-user" title="Mon profil" style={{ textDecoration: 'none', color: 'inherit' }}>
            <span className="text-muted small">{fullName}</span>
            <div className="user-avatar">{userInitials}</div>
          </Link>
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
    if (user?.role === 'FINANCE') return <Navigate to="/finance-dashboard" replace />
    return (
      <Layout breadcrumb={<li>Tableau de bord</li>}>
        <Dashboard />
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
            <ProtectedRoute allowedRoles={['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Formations</li></>}>
                <Formations />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:formationId/modules/:moduleId" element={
            <ProtectedRoute allowedRoles={['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Cours</li></>}>
                <ModuleDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formations/:id" element={
            <ProtectedRoute allowedRoles={['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li><ModulesListLink>Cours</ModulesListLink></li><li className="separator">/</li><li>Détail</li></>}>
                <FormationDetail />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/modules" element={
            <ProtectedRoute allowedRoles={['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Cours</li></>}>
                <Modules />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/participants" element={
            <ProtectedRoute allowedRoles={['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Auditeurs</li></>}>
                <Participants />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/formateurs" element={
            <ProtectedRoute>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Formateurs</li></>}>
                <Formateurs />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-dashboard" element={
            <ProtectedRoute allowedRoles={['FINANCE', 'DIRECTION']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Dashboard Finance</li></>}>
                <FinanceDashboard />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/finance-parametrage" element={
            <ProtectedRoute allowedRoles={['FINANCE', 'DIRECTION']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Paramétrage Finance</li></>}>
                <FinanceParametrage />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/users" element={
            <ProtectedRoute>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Utilisateurs</li></>}>
                <Users />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/secretariats" element={
            <ProtectedRoute allowedRoles={['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Secrétariats</li></>}>
                <Secretariats />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/import" element={
            <ProtectedRoute>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Import Excel</li></>}>
                <ImportExcel />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/referentiels" element={
            <ProtectedRoute allowedRoles={['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN']}>
              <Layout breadcrumb={<><li><Link to="/">Accueil</Link></li><li className="separator">/</li><li>Référentiels</li></>}>
                <Referentiels />
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
