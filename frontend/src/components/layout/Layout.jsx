import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { hasAppRole, peut } from '../../utils/roles'
import AppNotificationsBell from '../AppNotificationsBell'
import Sidebar from './Sidebar'
import { FINANCE_MODULE_ROLES } from '../../utils/roles'

/**
 * Coquille de l'application : barre latérale + barre supérieure + contenu.
 *
 * La navigation elle-même est déléguée à `Sidebar`, qui rend l'arborescence
 * **filtrée par les droits** du compte connecté (`useMenuAutorise`). Ce
 * composant ne contient donc plus aucune liste d'entrées codée en dur : il
 * garde uniquement la responsabilité du comportement de la coquille (panneau
 * mobile, repli desktop, fil d'Ariane, cloche de notifications, accès profil).
 *
 * Extrait de `App.jsx` sans changement de comportement pour les écrans
 * existants (mêmes classes CSS, mêmes largeurs, mêmes gardes de notification).
 */
export default function Layout({ children, breadcrumb }) {
  const { user } = useAuth()
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

  // Gardes de notification conservées à l'identique de l'écran historique.
  const isDirection = hasAppRole(user, ['DIRECTION'])
  // Destinataires des alertes d'absence (modèle 08) : direction + secrétariat.
  const isChaineAbsences = hasAppRole(user, ['DIRECTION', 'SECRETARIAT', 'CHEF_SECRETARIAT'])
  const canViewStatistiques = peut(user, 'statistiques', 'voir')
  const canViewFinanceNotifications = hasAppRole(user, FINANCE_MODULE_ROLES)
    && !hasAppRole(user, ['ARCHIVE'])
  const showAppNotifications = isDirection || canViewStatistiques || canViewFinanceNotifications

  const userInitials = `${(user?.first_name || '')[0] || ''}${(user?.last_name || '')[0] || ''}`
  const fullName = user?.get_full_name
    ? user.get_full_name()
    : `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.username

  return (
    <div className={`app-container${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
            zIndex: 99, display: 'block',
          }}
        />
      )}

      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

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
                showPresences={isChaineAbsences}
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

/** Fil d'Ariane standard : Accueil / …segments. */
export function FilAriane({ segments = [] }) {
  return (
    <>
      <li><Link to="/">Accueil</Link></li>
      {segments.map((segment, index) => (
        <span key={`${segment.libelle}-${index}`}>
          <li className="separator">/</li>
          {segment.chemin && index < segments.length - 1
            ? <li><Link to={segment.chemin}>{segment.libelle}</Link></li>
            : <li>{segment.libelle}</li>}
        </span>
      ))}
    </>
  )
}
