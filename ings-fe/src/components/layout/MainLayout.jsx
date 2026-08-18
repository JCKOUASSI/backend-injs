import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header, { Footer } from './Header'

const SIDEBAR_COLLAPSED_KEY = 'injs-sidebar-collapsed'

export default function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(sidebarCollapsed))
    } catch {
      // ignore storage errors
    }
  }, [sidebarCollapsed])

  const handleToggleSidebar = () => {
    if (window.matchMedia('(max-width: 992px)').matches) {
      setSidebarOpen((open) => !open)
      return
    }
    setSidebarCollapsed((collapsed) => !collapsed)
  }

  return (
    <div className={`app-layout ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Sidebar
        open={sidebarOpen}
        collapsed={sidebarCollapsed}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="main-content">
        <Header
          sidebarCollapsed={sidebarCollapsed}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={handleToggleSidebar}
        />
        <main className="page-content">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  )
}
