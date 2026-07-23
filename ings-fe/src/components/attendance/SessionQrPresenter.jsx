import { useEffect, useState } from 'react'
import { FiMaximize2, FiMinimize2, FiRefreshCw, FiUsers } from 'react-icons/fi'

/**
 * Présentation QR séance (admin / professeur).
 * Bouton « Liste des étudiants » → ouvre la liste complète hors de ce modal.
 */
export default function SessionQrPresenter({
  qrData,
  summary,
  onRefresh,
  onOpenStudentList,
  onTeacherBadge,
  teacherBadging = false,
  showTeacherBadge = false,
  pollMs = 8000,
}) {
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    if (!onRefresh || !pollMs) return undefined
    const id = setInterval(() => { onRefresh() }, pollMs)
    return () => clearInterval(id)
  }, [onRefresh, pollMs])

  if (!qrData) {
    return <div className="text-center py-4"><div className="spinner-border text-primary" /></div>
  }

  const presentCount = summary?.present ?? 0
  const totalCount = summary?.total ?? '—'

  const body = (
    <div className={`session-qr-presenter ${fullscreen ? 'session-qr-presenter--fs' : ''}`}>
      {onOpenStudentList && (
        <div className="d-flex justify-content-end mb-3">
          <button
            type="button"
            className="btn btn-injs-primary btn-sm"
            onClick={() => {
              setFullscreen(false)
              onOpenStudentList()
            }}
          >
            <FiUsers className="me-1" /> Liste des étudiants
          </button>
        </div>
      )}

      <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
        <div>
          <div className="text-uppercase small text-muted fw-semibold">QR séance INJS</div>
          <h4 className="fw-bold mb-1">
            <code className="me-2">{qrData.course_code}</code>
            {qrData.course_name}
          </h4>
          <div className="text-muted">
            {qrData.day_display} {qrData.date} — {String(qrData.start_time).slice(0, 5)}–{String(qrData.end_time).slice(0, 5)}
            {(qrData.room_code || qrData.room_name) && ` · ${[qrData.room_code, qrData.room_name].filter(Boolean).join(' ')}`}
            {qrData.promotion_name && ` · ${qrData.promotion_name}`}
          </div>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          {onRefresh && (
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={onRefresh}>
              <FiRefreshCw className="me-1" /> Actualiser
            </button>
          )}
          <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={() => setFullscreen((v) => !v)}
          >
            {fullscreen ? <><FiMinimize2 className="me-1" /> Réduire</> : <><FiMaximize2 className="me-1" /> Plein écran</>}
          </button>
        </div>
      </div>

      <div className="row g-4 align-items-center">
        <div className="col-lg-7 text-center">
          <img
            src={`data:image/png;base64,${qrData.qr_image_base64}`}
            alt="QR badgeage séance"
            className="session-qr-image"
          />
          <p className="small text-muted mt-2 mb-0">
            Les étudiants scannent ce QR avec leur téléphone
            <br />
            (ouvre automatiquement la page Badgeage)
          </p>
          <p className="small font-monospace text-break mt-2 mb-0" style={{ fontSize: '0.7rem' }}>
            {qrData.badge_url || qrData.payload}
          </p>
        </div>
        <div className="col-lg-5">
          <div className="card-injs p-3 mb-3 text-center">
            <div className="fs-2 fw-bold text-primary">{presentCount}</div>
            <div className="small text-muted">Badgé(e)s / {totalCount}</div>
            {summary?.teacher_checked_in != null && (
              <div className="mt-2">
                {summary.teacher_checked_in
                  ? <span className="badge bg-success">Formateur badgé</span>
                  : <span className="badge bg-warning text-dark">Formateur non badgé</span>}
              </div>
            )}
          </div>

          {showTeacherBadge && onTeacherBadge && (
            <button
              type="button"
              className="btn btn-outline-primary w-100"
              onClick={onTeacherBadge}
              disabled={teacherBadging || summary?.teacher_checked_in}
            >
              {summary?.teacher_checked_in
                ? 'Présence formateur enregistrée'
                : (teacherBadging ? 'Badgeage…' : 'Badger ma présence (formateur)')}
            </button>
          )}
        </div>
      </div>
    </div>
  )

  if (fullscreen) {
    return (
      <div className="session-qr-overlay" role="dialog" aria-modal="true">
        <div className="session-qr-overlay-inner card-injs p-4">
          {body}
        </div>
      </div>
    )
  }

  return body
}
