import { useMemo, useState } from 'react'
import { FiRefreshCw } from 'react-icons/fi'
import Modal from '../../../components/common/Modal'
import ExportButtons from '../../../components/common/ExportButtons'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import { fetchSeances, fetchSeanceQr, updateSeance, publishSeances } from '../../../api/faculty'

const STATUS_CLASS = {
  draft: 'bg-secondary',
  generated: 'bg-info text-dark',
  validated: 'bg-primary',
  published: 'bg-success',
  in_progress: 'bg-warning text-dark',
  done: 'bg-dark',
  cancelled: 'bg-danger',
  archived: 'bg-secondary',
}

const KIND_LABEL = { cm: 'CM', td: 'TD', tp: 'TP' }
const QR_STATUSES = ['published', 'validated', 'in_progress']

function formatDay(value) {
  if (!value) return '—'
  return new Date(`${value}T12:00:00`).toLocaleDateString('fr-FR', {
    weekday: 'short', day: '2-digit', month: 'short',
  })
}

export default function CalendarPanel({ filters, onChanged }) {
  const { showToast } = useToast()
  const [status, setStatus] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [selected, setSelected] = useState(null)
  const [saving, setSaving] = useState(false)
  const [qrData, setQrData] = useState(null)

  const params = useMemo(() => ({
    period: filters.period || undefined,
    promotion: filters.promotion || undefined,
    status: status || undefined,
    date_from: from || undefined,
    date_to: to || undefined,
    page_size: 200,
    ordering: 'date,start_time',
  }), [filters.period, filters.promotion, status, from, to])

  const { data, loading, error, reload } = useFetch(() => fetchSeances(params), [params])
  const seances = data?.results || []

  const grouped = useMemo(() => {
    const map = new Map()
    for (const seance of seances) {
      const key = seance.date
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(seance)
    }
    return [...map.entries()]
  }, [seances])

  const cancelSeance = async (seance) => {
    const reason = window.prompt('Motif d’annulation ?', seance.cancelled_reason || '')
    if (reason === null) return
    setSaving(true)
    try {
      await updateSeance(seance.id, { status: 'cancelled', cancelled_reason: reason, is_active: false })
      showToast('Séance annulée', 'success')
      setSelected(null)
      reload()
      onChanged?.()
    } catch (err) {
      showToast(err.message || 'Annulation impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const publishOne = async (seance) => {
    setSaving(true)
    try {
      await publishSeances({ ids: [seance.id] })
      showToast('Séance publiée', 'success')
      setSelected({ ...seance, status: 'published', status_display: 'Publiée' })
      reload()
      onChanged?.()
    } catch (err) {
      showToast(err.message || 'Publication impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const openQr = async (seance) => {
    setSaving(true)
    try {
      const data = await fetchSeanceQr(seance.id)
      setQrData(data)
    } catch (err) {
      showToast(err.message || 'QR indisponible pour cette séance', 'danger')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="card-injs p-3 mb-3">
        <div className="row g-2 align-items-end">
          <div className="col-6 col-md-3">
            <label className="form-label small mb-1">Du</label>
            <input type="date" className="form-control" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div className="col-6 col-md-3">
            <label className="form-label small mb-1">Au</label>
            <input type="date" className="form-control" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <div className="col-6 col-md-3">
            <label className="form-label small mb-1">Statut</label>
            <select className="form-select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Tous</option>
              <option value="generated">Généré</option>
              <option value="published">Publié</option>
              <option value="in_progress">En cours</option>
              <option value="done">Terminé</option>
              <option value="cancelled">Annulé</option>
              <option value="draft">Brouillon</option>
            </select>
          </div>
          <div className="col-6 col-md-3">
            <button type="button" className="btn btn-outline-secondary w-100" onClick={reload}>
              <FiRefreshCw className="me-1" /> Actualiser
            </button>
          </div>
          <div className="col-12 col-md-auto ms-md-auto">
            <ExportButtons
              title="Emploi du temps INJS"
              filename="edt_seances"
              resourcePath="/faculty/seances"
              resourceParams={{
                period: filters.period || undefined,
                promotion: filters.promotion || undefined,
                status: status || undefined,
                date_from: from || undefined,
                date_to: to || undefined,
              }}
            />
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <div className="text-center py-4"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {!loading && seances.length === 0 && (
        <div className="card-injs p-4 text-muted">
          Aucune séance datée pour ces filtres. Utilisez l’onglet Génération pour produire l’emploi du temps d’une période.
        </div>
      )}

      {grouped.map(([day, items]) => (
        <div className="card-injs mb-3" key={day}>
          <div className="px-3 py-2 border-bottom fw-semibold">{formatDay(day)}</div>
          <div className="table-responsive">
            <table className="table table-hover mb-0">
              <thead>
                <tr>
                  <th>Horaire</th>
                  <th>ECUE</th>
                  <th>Type</th>
                  <th>Promotion / groupe</th>
                  <th>Professeur</th>
                  <th>Salle</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {items.map((seance) => (
                  <tr key={seance.id} role="button" onClick={() => { setSelected(seance); setQrData(null) }}>
                    <td>{(seance.start_time || '').slice(0, 5)} – {(seance.end_time || '').slice(0, 5)}</td>
                    <td>
                      <strong>{seance.course_code}</strong>
                      <div className="small text-muted">{seance.course_name}</div>
                    </td>
                    <td><span className="badge bg-light text-dark">{KIND_LABEL[seance.session_kind] || seance.session_kind}</span></td>
                    <td>
                      {seance.promotion_name}
                      {seance.group_name ? <div className="small text-muted">{seance.group_name}</div> : null}
                    </td>
                    <td>{seance.teacher_name || '—'}</td>
                    <td>{seance.room_code || '—'}</td>
                    <td>
                      <span className={`badge ${STATUS_CLASS[seance.status] || 'bg-secondary'}`}>
                        {seance.status_display || seance.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      <Modal
        show={Boolean(selected)}
        onClose={() => { setSelected(null); setQrData(null) }}
        title={selected ? `${selected.course_code} — ${formatDay(selected.date)}` : ''}
        footer={selected && (
          <>
            {QR_STATUSES.includes(selected.status) && (
              <button type="button" className="btn btn-outline-primary" disabled={saving} onClick={() => openQr(selected)}>
                QR badgeage
              </button>
            )}
            {['draft', 'generated', 'validated'].includes(selected.status) && (
              <button type="button" className="btn btn-injs-primary" disabled={saving} onClick={() => publishOne(selected)}>
                Publier
              </button>
            )}
            {selected.status !== 'cancelled' && selected.status !== 'done' && (
              <button type="button" className="btn btn-outline-danger" disabled={saving} onClick={() => cancelSeance(selected)}>
                Annuler la séance
              </button>
            )}
            <button type="button" className="btn btn-outline-secondary" onClick={() => { setSelected(null); setQrData(null) }}>Fermer</button>
          </>
        )}
      >
        {selected && (
          <>
            <dl className="row mb-0">
              <dt className="col-sm-4">Horaire</dt>
              <dd className="col-sm-8">{(selected.start_time || '').slice(0, 5)} – {(selected.end_time || '').slice(0, 5)}</dd>
              <dt className="col-sm-4">Professeur</dt>
              <dd className="col-sm-8">{selected.teacher_name || '—'}</dd>
              <dt className="col-sm-4">Encadrant</dt>
              <dd className="col-sm-8">{selected.supervisor_name || '—'}</dd>
              <dt className="col-sm-4">Salle</dt>
              <dd className="col-sm-8">{selected.room_code || 'Non affectée'}</dd>
              <dt className="col-sm-4">Période</dt>
              <dd className="col-sm-8">{selected.period_label || '—'}</dd>
              <dt className="col-sm-4">Statut</dt>
              <dd className="col-sm-8">{selected.status_display}</dd>
            </dl>
            {qrData?.qr_image_base64 && (
              <div className="text-center mt-3">
                <img
                  src={`data:image/png;base64,${qrData.qr_image_base64}`}
                  alt="QR de séance"
                  className="img-fluid"
                  style={{ maxWidth: 240 }}
                />
                <div className="small text-muted mt-2 font-monospace">{qrData.payload}</div>
              </div>
            )}
          </>
        )}
      </Modal>
    </>
  )
}
