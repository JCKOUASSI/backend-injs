import { Link, useLocation } from 'react-router-dom'
import { getMenuByRole, getRoleLabel } from '../../data/navigation'
import { INSTITUTION } from '../../data/mockData'
import { useAuth } from '../../context/AuthContext'

export default function Sidebar({ open, collapsed, onClose }) {
  const { user } = useAuth()
  const location = useLocation()
  const menu = getMenuByRole(user?.role)

  return (
    <>
      {open && <div className="sidebar-overlay d-lg-none" onClick={onClose} />}
      <aside className={`sidebar ${open ? 'open' : ''} ${collapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <img src="/logo-INJS-ABIDJAN-1.png" alt="Logo INJS" />
          <div className="sidebar-brand">
            <h5>{INSTITUTION.shortName}</h5>
            <small>{INSTITUTION.ufr}</small>
            <small>{getRoleLabel(user?.role)}</small>
          </div>
        </div>
        <nav className="sidebar-nav">
          {menu.map((item, idx) =>
            item.section ? (
              <div key={idx} className="sidebar-section">{item.section}</div>
            ) : (
              <Link
                key={item.path}
                to={item.path}
                className={`sidebar-link ${location.pathname === item.path ? 'active' : ''}`}
                onClick={onClose}
              >
                <item.icon />
                <span>{item.label}</span>
              </Link>
            )
          )}
        </nav>
        <div className="sidebar-footer">
          <div>{INSTITUTION.university}</div>
          <div>Année {INSTITUTION.academicYear}</div>
        </div>
      </aside>
    </>
  )
}
