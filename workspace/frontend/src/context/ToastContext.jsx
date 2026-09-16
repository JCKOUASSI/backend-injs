import { createContext, useContext, useState, useCallback } from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const showToast = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, message, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 6000)
  }, [])

  const iconMap = { success: 'check-circle-fill', error: 'exclamation-triangle-fill', info: 'info-circle-fill' }
  const bgMap = { success: '#125a99', error: '#c62828', info: '#1565C0' }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div style={{ position: 'fixed', bottom: '1.5rem', right: '1.5rem', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: '0.5rem', pointerEvents: 'none' }}>
        {toasts.map(t => (
          <div key={t.id} style={{
            padding: '0.75rem 1.25rem',
            borderRadius: '8px',
            color: '#fff',
            fontWeight: 500,
            fontSize: '0.9rem',
            boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
            background: bgMap[t.type] || bgMap.success,
            maxWidth: '340px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}>
            <i className={`bi bi-${iconMap[t.type] || iconMap.success}`}></i>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
