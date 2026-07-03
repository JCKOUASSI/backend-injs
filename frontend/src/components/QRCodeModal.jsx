import { useState, useEffect, useRef } from 'react'
import QRCode from 'qrcode'
import api from '../services/api'
import ConfirmModal from './ConfirmModal'

// Badge URL must point to the BACKEND (Django serves /dashboard/badge/), not the frontend SPA.
// Derive from VITE_BADGE_BASE_URL, or strip /api from VITE_API_URL as fallback.
const BADGE_BASE_URL = import.meta.env.VITE_BADGE_BASE_URL
  || (import.meta.env.VITE_API_URL || '').replace(/\/api\/?$/, '')
  || window.location.origin

export default function QRCodeModal({ formationId, sessionId, isOpen, onClose }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [token, setToken] = useState(null)
  const [noActiveQr, setNoActiveQr] = useState(false)
  const [confirmRegenerate, setConfirmRegenerate] = useState(false)
  const canvasRef = useRef(null)

  const qrType = sessionId ? 'session' : 'formation'

  useEffect(() => {
    if (isOpen && formationId) loadActiveQR()
  }, [isOpen, formationId, sessionId])

  useEffect(() => {
    if (token && canvasRef.current) {
      const badgeUrl = `${BADGE_BASE_URL}/dashboard/badge/?token=${token}`
      QRCode.toCanvas(canvasRef.current, badgeUrl, {
        width: 220,
        margin: 2,
        color: { dark: '#000000', light: '#ffffff' },
        errorCorrectionLevel: 'H',
      }).catch(console.error)
    }
  }, [token])

  const loadActiveQR = async () => {
    setLoading(true)
    setError(null)
    setToken(null)
    setNoActiveQr(false)
    try {
      const params = sessionId ? { session_id: sessionId } : {}
      const response = await api.get(`/formations/superviseur/${formationId}/qr/`, { params })
      setToken(response.data.token)
    } catch (err) {
      if (err.response?.status === 404) {
        setNoActiveQr(true)
      } else {
        setError('Erreur lors du chargement du QR code')
        console.error(err)
      }
    } finally {
      setLoading(false)
    }
  }

  const generateAndShowQR = async () => {
    setLoading(true)
    setError(null)
    setNoActiveQr(false)
    try {
      const endpoint = sessionId
        ? `/formations/${formationId}/sessions/${sessionId}/generate-qr/`
        : `/formations/${formationId}/generate-qr/`
      const response = await api.post(endpoint)
      setToken(response.data.token)
    } catch (err) {
      setError('Erreur lors de la génération du QR code')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerateClick = () => {
    setConfirmRegenerate(true)
  }

  const downloadQR = () => {
    if (!canvasRef.current) return
    const filename = sessionId
      ? `qr_seance_${formationId}_${sessionId}.png`
      : `qr_formation_${formationId}.png`
    const link = document.createElement('a')
    link.href = canvasRef.current.toDataURL('image/png')
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (!isOpen) return null

  return (
    <>
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '420px' }}>
          <div className="modal-header">
            <h5>
              <i className="bi bi-qr-code me-2"></i>
              {qrType === 'session' ? 'QR Code — Séance' : 'QR Code — Formation'}
            </h5>
            <button className="btn-close" onClick={onClose}>&times;</button>
          </div>
          <div className="modal-body text-center">
            {loading && <div className="loading"><div className="spinner"></div></div>}
            {error && <div className="alert alert-danger"><i className="bi bi-exclamation-triangle me-1"></i>{error}</div>}
            {noActiveQr && !loading && !error && (
              <p className="text-muted mb-0">
                <i className="bi bi-info-circle me-1"></i>
                Aucun QR code actif pour cette {qrType === 'session' ? 'séance' : 'formation'}.
              </p>
            )}
            <div style={{ display: token && !loading ? 'inline-block' : 'none', padding: '1rem', border: '2px solid #e2e8f0', borderRadius: '12px', marginBottom: '1rem', background: '#fff' }}>
              <canvas ref={canvasRef} />
            </div>
            {token && !loading && (
              <p className="text-muted small mb-3">
                <i className="bi bi-key me-1"></i>Token : {token.substring(0, 12)}…
              </p>
            )}
          </div>
          <div className="modal-footer" style={{ justifyContent: 'center' }}>
            {token && !loading && (
              <button onClick={downloadQR} className="btn btn-dfrc btn-sm">
                <i className="bi bi-download me-1"></i>Télécharger
              </button>
            )}
            {token && !loading ? (
              <button onClick={handleRegenerateClick} className="btn btn-outline-warning btn-sm" disabled={loading}>
                <i className="bi bi-arrow-clockwise me-1"></i>Régénérer
              </button>
            ) : !loading && (
              <button onClick={generateAndShowQR} className="btn btn-dfrc btn-sm" disabled={loading}>
                <i className="bi bi-qr-code me-1"></i>Générer le QR code
              </button>
            )}
            <button onClick={onClose} className="btn btn-secondary btn-sm">
              Fermer
            </button>
          </div>
        </div>
      </div>

      {confirmRegenerate && (
        <ConfirmModal
          message="Régénérer le QR code ?"
          detail="L'ancien QR code sera immédiatement invalidé. Les participants devront scanner le nouveau code pour badgear."
          confirmLabel="Régénérer"
          cancelLabel="Annuler"
          variant="primary"
          onConfirm={() => {
            setConfirmRegenerate(false)
            generateAndShowQR()
          }}
          onCancel={() => setConfirmRegenerate(false)}
        />
      )}
    </>
  )
}
