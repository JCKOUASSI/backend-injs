import { useEffect, useState } from 'react'
import { FiMenu, FiBell, FiSearch, FiLogOut, FiChevronsLeft, FiChevronsRight } from 'react-icons/fi'
import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { INSTITUTION } from '../../data/mockData'

export default function Header({ onToggleSidebar, sidebarCollapsed, sidebarOpen }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 992px)')
    const update = () => setIsMobile(mediaQuery.matches)
    update()
    mediaQuery.addEventListener('change', update)
    return () => mediaQuery.removeEventListener('change', update)
  }, [])

  const sidebarHidden = isMobile ? !sidebarOpen : sidebarCollapsed
  const toggleLabel = sidebarHidden ? 'Afficher le menu' : 'Masquer le menu'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="top-header">
      <div className="d-flex align-items-center gap-3">
        <button
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label={toggleLabel}
          title={toggleLabel}
        >
          {sidebarHidden ? <FiChevronsRight /> : isMobile ? <FiMenu /> : <FiChevronsLeft />}
        </button>
        <div className="header-search d-none d-md-block position-relative">
          <FiSearch className="position-absolute" style={{ left: 14, top: '50%', transform: 'translateY(-50%)', color: '#6B7C77' }} />
          <input type="search" className="form-control" placeholder="Rechercher étudiants, UE, professeurs..." />
        </div>
      </div>
      <div className="header-actions">
        <button className="header-icon-btn" aria-label="Notifications">
          <FiBell />
          <span className="notification-dot" />
        </button>
        <div className="user-profile" onClick={handleLogout} title="Déconnexion">
          <div className="user-avatar">{user?.avatar}</div>
          <div className="d-none d-md-block">
            <div className="fw-semibold" style={{ fontSize: '0.9rem' }}>{user?.name}</div>
            <div className="text-muted" style={{ fontSize: '0.75rem' }}>{user?.title}</div>
          </div>
          <FiLogOut className="text-muted ms-2" />
        </div>
      </div>
    </header>
  )
}

export function Footer() {
  return (
    <footer className="page-footer">
      © {new Date().getFullYear()} {INSTITUTION.name} — {INSTITUTION.university}, {INSTITUTION.city} — {INSTITUTION.motto}
    </footer>
  )
}
