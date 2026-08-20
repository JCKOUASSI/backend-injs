/** QR de badgeage d'une séance, avec compteurs rafraîchis en continu. */
import { useEffect, useState } from 'react'
import { FiMaximize2, FiMinimize2, FiRefreshCw, FiRotateCw } from 'react-icons/fi'
import Modal from '@app/components/common/Modal'

export default function QrSeanceModal({
  show,
  qr,
  onClose,
  onRefresh,
  onRegenerer,
  onTerminer,
  intervalleMs = 8000,
}) {
  const [pleinEcran, setPleinEcran] = useState(false)

  useEffect(() => {
    if (!show || !onRefresh || !intervalleMs) return undefined
    const timer = setInterval(onRefresh, intervalleMs)
    return () => clearInterval(timer)
  }, [show, onRefresh, intervalleMs])

  useEffect(() => {
    if (!show) setPleinEcran(false)
  }, [show])

  const resume = qr?.resume || {}

  const corps = qr ? (
    <div className="ept-qr-wrapper">
      <div className="text-center">
        <div className="fw-bold fs-5">
          <code className="me-2">{qr.course_code}</code>
          {qr.course_name}
        </div>
        <div className="text-muted small">
          {qr.day_display} {qr.date} · {qr.start_time}–{qr.end_time}
          {qr.room_code && ` · Salle ${qr.room_code}`}
          {qr.promotion_name && ` · ${qr.promotion_name}`}
          {qr.groupe_code && ` · ${qr.groupe_code}`}
        </div>
      </div>

      <div className="ept-qr-canvas">
        <img
          src={`data:image/png;base64,${qr.qr_image_base64}`}
          alt="QR de badgeage de la séance"
          style={{ width: pleinEcran ? 460 : 260, height: 'auto', display: 'block' }}
        />
      </div>

      <p className="text-center text-muted small mb-0">
        Les étudiants scannent ce QR : la première lecture enregistre l’entrée, la seconde la sortie.
      </p>
      <div className="ept-qr-token">{qr.badge_url}</div>

      <div className="d-flex gap-4 justify-content-center text-center">
        <div>
          <div className="fs-4 fw-bold text-success">{resume.presents ?? 0}</div>
          <div className="small text-muted">Présents</div>
        </div>
        <div>
          <div className="fs-4 fw-bold">{resume.attendus ?? 0}</div>
          <div className="small text-muted">Attendus</div>
        </div>
        <div>
          <div className="fs-4 fw-bold text-primary">{resume.en_salle ?? 0}</div>
          <div className="small text-muted">En salle</div>
        </div>
        <div>
          <div className="fs-4 fw-bold">{resume.taux_presence ?? 0} %</div>
          <div className="small text-muted">Taux</div>
        </div>
      </div>
    </div>
  ) : (
    <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  )

  return (
    <Modal
      show={show}
      onClose={onClose}
      size="lg"
      title="QR de badgeage"
      footer={
        <div className="d-flex flex-wrap gap-2 justify-content-between w-100">
          <div className="d-flex gap-2 flex-wrap">
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={onRefresh}>
              <FiRefreshCw className="me-1" /> Actualiser
            </button>
            <button
              type="button"
              className="btn btn-outline-primary btn-sm"
              onClick={() => setPleinEcran((valeur) => !valeur)}
            >
              {pleinEcran
                ? <><FiMinimize2 className="me-1" /> Réduire</>
                : <><FiMaximize2 className="me-1" /> Agrandir</>}
            </button>
            {onRegenerer && (
              <button type="button" className="btn btn-outline-warning btn-sm" onClick={onRegenerer}>
                <FiRotateCw className="me-1" /> Régénérer
              </button>
            )}
          </div>
          {onTerminer && (
            <button type="button" className="btn btn-injs-primary btn-sm" onClick={onTerminer}>
              Terminer la séance
            </button>
          )}
        </div>
      }
    >
      {corps}
    </Modal>
  )
}
