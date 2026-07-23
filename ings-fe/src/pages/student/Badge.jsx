import { useCallback, useEffect, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'
import { useSearchParams } from 'react-router-dom'
import PageHeader from '../../components/common/PageHeader'
import { useToast } from '../../context/ToastContext'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { checkInSession, fetchMyAttendanceHistory } from '../../api/faculty'

function extractToken(raw) {
  const value = (raw || '').trim()
  if (!value) return ''
  if (value.includes('token=')) {
    try {
      const url = value.startsWith('http') ? new URL(value) : new URL(value, window.location.origin)
      const t = url.searchParams.get('token')
      if (t) return decodeURIComponent(t)
    } catch {
      const m = value.match(/token=([^&\s#]+)/)
      if (m) return decodeURIComponent(m[1])
    }
  }
  return value
}

export default function StudentBadge() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [token, setToken] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [scanning, setScanning] = useState(false)
  const scannerRef = useRef(null)
  const busyRef = useRef(false)

  const { data: history, reload: reloadHistory } = useFetch(() => fetchMyAttendanceHistory(), [])

  const doCheckIn = useCallback(async (raw) => {
    const value = extractToken(raw)
    if (!value.startsWith('INJS:SESSION:')) {
      showToast('QR de séance invalide', 'warning')
      return
    }
    if (busyRef.current) return
    busyRef.current = true
    setSubmitting(true)
    try {
      const result = await checkInSession(value)
      setLastResult(result)
      showToast(result.message || 'Présence enregistrée', 'success')
      setToken('')
      setSearchParams({})
      reloadHistory()
    } catch (err) {
      showToast(err.message || 'Échec du badgeage', 'danger')
    } finally {
      setSubmitting(false)
      busyRef.current = false
    }
  }, [showToast, setSearchParams, reloadHistory])

  // Deep-link depuis QR téléphone
  useEffect(() => {
    const q = searchParams.get('token')
    if (q) {
      setToken(extractToken(q))
      doCheckIn(q)
    }
  }, [searchParams, doCheckIn])

  useEffect(() => () => {
    if (scannerRef.current) {
      scannerRef.current.stop().catch(() => {})
      scannerRef.current.clear().catch(() => {})
      scannerRef.current = null
    }
  }, [])

  const startScan = async () => {
    setScanning(true)
    try {
      const scanner = new Html5Qrcode('injs-qr-reader')
      scannerRef.current = scanner
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 8, qrbox: { width: 240, height: 240 } },
        async (decoded) => {
          await scanner.stop().catch(() => {})
          scanner.clear().catch(() => {})
          scannerRef.current = null
          setScanning(false)
          await doCheckIn(decoded)
        },
        () => {},
      )
    } catch (err) {
      setScanning(false)
      showToast(err?.message || 'Caméra indisponible — utilisez la saisie manuelle', 'warning')
    }
  }

  const stopScan = async () => {
    if (scannerRef.current) {
      await scannerRef.current.stop().catch(() => {})
      await scannerRef.current.clear().catch(() => {})
      scannerRef.current = null
    }
    setScanning(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    await doCheckIn(token)
  }

  const rows = history?.results || []

  return (
    <>
      <PageHeader
        title="Badgeage présence"
        subtitle={`Scannez le QR projeté par le professeur / l'administration — ${user?.name || 'Étudiant'}`}
      />

      <div className="row g-4">
        <div className="col-lg-6">
          <div className="card-injs p-4 mb-3">
            <h6 className="fw-bold mb-3">Scanner le QR de séance</h6>
            <p className="text-muted small">
              Pointez la caméra vers le QR affiché en salle (vidéoprojecteur).
              Vous pouvez aussi ouvrir le lien scanné depuis l&apos;appareil photo du téléphone.
            </p>

            <div id="injs-qr-reader" className="mb-3 rounded overflow-hidden bg-dark" style={{ minHeight: scanning ? 280 : 0 }} />

            {!scanning ? (
              <button type="button" className="btn btn-injs-primary w-100 mb-3" onClick={startScan} disabled={submitting}>
                Ouvrir la caméra
              </button>
            ) : (
              <button type="button" className="btn btn-outline-danger w-100 mb-3" onClick={stopScan}>
                Arrêter le scan
              </button>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label">Ou coller le code / lien</label>
                <textarea
                  className="form-control font-monospace"
                  rows={3}
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="INJS:SESSION:… ou URL badgeage"
                />
              </div>
              <button type="submit" className="btn btn-outline-primary w-100" disabled={submitting || !token.trim()}>
                {submitting ? 'Enregistrement…' : 'Confirmer ma présence'}
              </button>
            </form>
          </div>

          {lastResult && (
            <div className="alert alert-success">
              <strong>{lastResult.course_name}</strong>
              <br />
              <small>Séance du {lastResult.session_date} — {lastResult.message}</small>
            </div>
          )}
        </div>

        <div className="col-lg-6">
          <div className="card-injs p-4 h-100">
            <h6 className="fw-bold mb-3">Comment ça marche ?</h6>
            <ol className="small text-muted ps-3 mb-4">
              <li className="mb-2">Le QR est généré pour chaque cours de l&apos;emploi du temps du jour.</li>
              <li className="mb-2">Le professeur ou l&apos;administration l&apos;affiche en plein écran en salle.</li>
              <li className="mb-2">Vous scannez pendant la fenêtre horaire du créneau (±30 min).</li>
              <li className="mb-2">Votre présence passe automatiquement à « Présent » (ou « Retard »).</li>
            </ol>

            <h6 className="fw-bold mb-2">Mes derniers badgeages</h6>
            {!rows.length && <p className="small text-muted mb-0">Aucun badgeage enregistré.</p>}
            <ul className="list-unstyled mb-0">
              {rows.slice(0, 12).map((a) => (
                <li key={a.id} className="d-flex justify-content-between py-2 border-bottom small">
                  <span>
                    <strong>{a.course_name}</strong>
                    <br />
                    <span className="text-muted">{a.date}</span>
                  </span>
                  <span className={`badge ${a.status === 'present' ? 'bg-success' : a.status === 'late' ? 'bg-warning text-dark' : 'bg-secondary'}`}>
                    {a.status_label || (a.status === 'present' ? 'Présent' : a.status === 'late' ? 'Retard' : a.status)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </>
  )
}
