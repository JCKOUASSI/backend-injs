import { useEffect } from 'react'
import { FiX } from 'react-icons/fi'

export default function Modal({ show, onClose, title, children, size = 'md', footer }) {
  useEffect(() => {
    if (!show) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKey)
    }
  }, [show, onClose])

  if (!show) return null

  return (
    <div className="injs-modal-backdrop" onClick={onClose}>
      <div
        className={`injs-modal injs-modal-${size}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="injs-modal-header">
          <h5 id="modal-title" className="fw-bold mb-0">{title}</h5>
          <button type="button" className="injs-modal-close" onClick={onClose} aria-label="Fermer">
            <FiX size={22} />
          </button>
        </div>
        <div className="injs-modal-body">{children}</div>
        {footer && <div className="injs-modal-footer">{footer}</div>}
      </div>
    </div>
  )
}
