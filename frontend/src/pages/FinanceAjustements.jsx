import { useCallback, useEffect, useState } from 'react'
import api from '../services/api'
import { useToast } from '../context/ToastContext'
import FinancePageShell, { FinanceNavActions } from '../components/finance/FinancePageShell'
import '../styles/finance.css'

const fmtDuration = (minutes) => {
  const total = Math.round(Number(minutes || 0))
  const h = Math.floor(total / 60)
  const m = total % 60
  if (m === 0) return `${h}h`
  return `${h}h ${m}min`
}

const formatDateTime = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('fr-FR')
}

const STATUT_BADGE = {
  EN_ATTENTE: 'bg-warning text-dark',
  VALIDE: 'bg-success',
  REJETE: 'bg-secondary',
}

export default function FinanceAjustements() {
  const { showToast } = useToast()
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState([])
  const [pendingCount, setPendingCount] = useState(0)
  const [filter, setFilter] = useState('EN_ATTENTE')
  const [actingId, setActingId] = useState(null)
  const [rejectId, setRejectId] = useState(null)
  const [rejectMotif, setRejectMotif] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    session_id: '',
    formateur_id: '',
    minutes_delta: '',
    motif: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const loadItems = useCallback(async () => {
    setLoading(true)
    try {
      const params = filter ? `?statut=${filter}` : ''
      const { data } = await api.get(`/formations/finance/ajustements/${params}`)
      setItems(data.items || [])
      setPendingCount(data.pending_count || 0)
    } catch (err) {
      showToast(err.response?.data?.detail || 'Erreur de chargement', 'error')
    } finally {
      setLoading(false)
    }
  }, [filter, showToast])

  useEffect(() => {
    loadItems()
  }, [loadItems])

  const handleValidate = async (id) => {
    setActingId(id)
    try {
      await api.post(`/formations/finance/ajustements/${id}/valider/`)
      showToast('Ajustement validé — impact paie appliqué', 'success')
      loadItems()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Validation impossible', 'error')
    } finally {
      setActingId(null)
    }
  }

  const handleReject = async () => {
    if (!rejectMotif.trim()) {
      showToast('Le motif de rejet est obligatoire', 'error')
      return
    }
    setActingId(rejectId)
    try {
      await api.post(`/formations/finance/ajustements/${rejectId}/rejeter/`, {
        motif: rejectMotif.trim(),
      })
      showToast('Ajustement rejeté', 'success')
      setRejectId(null)
      setRejectMotif('')
      loadItems()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Rejet impossible', 'error')
    } finally {
      setActingId(null)
    }
  }

  const handlePropose = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/formations/finance/ajustements/', {
        session_id: Number(form.session_id),
        formateur_id: Number(form.formateur_id),
        minutes_delta: Number(form.minutes_delta),
        motif: form.motif.trim(),
      })
      showToast('Ajustement proposé — en attente de validation', 'success')
      setForm({ session_id: '', formateur_id: '', minutes_delta: '', motif: '' })
      setShowForm(false)
      setFilter('EN_ATTENTE')
      loadItems()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Proposition impossible', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <FinancePageShell
      title="Ajustements horaires"
      subtitle="Corrections sur séances réelles — validation Direction/Finance, impact paie, journal d'audit"
      icon="bi-arrow-left-right"
      showPeriodFilter={false}
      actions={<FinanceNavActions active="ajustements" pendingAjustements={pendingCount} />}
    >
      <div className="finance-card">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
          <div className="btn-group btn-group-sm">
            {[
              { key: 'EN_ATTENTE', label: 'En attente' },
              { key: 'VALIDE', label: 'Validés' },
              { key: 'REJETE', label: 'Rejetés' },
              { key: '', label: 'Tous' },
            ].map(({ key, label }) => (
              <button
                key={key || 'all'}
                type="button"
                className={`btn ${filter === key ? 'btn-finance-accent' : 'btn-outline-secondary'}`}
                onClick={() => setFilter(key)}
              >
                {label}
                {key === 'EN_ATTENTE' && pendingCount > 0 && (
                  <span className="badge bg-danger ms-1">{pendingCount}</span>
                )}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="btn btn-sm btn-finance-accent"
            onClick={() => setShowForm((v) => !v)}
          >
            <i className={`bi ${showForm ? 'bi-x-lg' : 'bi-plus-lg'} me-1`}></i>
            {showForm ? 'Fermer' : 'Proposer un ajustement'}
          </button>
        </div>

        {showForm && (
          <form className="finance-filter-panel mb-3" onSubmit={handlePropose}>
            <div className="row g-2">
              <div className="col-md-3">
                <label className="form-label small">ID séance</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  value={form.session_id}
                  onChange={(e) => setForm((f) => ({ ...f, session_id: e.target.value }))}
                  required
                />
              </div>
              <div className="col-md-3">
                <label className="form-label small">ID formateur</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  value={form.formateur_id}
                  onChange={(e) => setForm((f) => ({ ...f, formateur_id: e.target.value }))}
                  required
                />
              </div>
              <div className="col-md-2">
                <label className="form-label small">Minutes (+/−)</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  value={form.minutes_delta}
                  onChange={(e) => setForm((f) => ({ ...f, minutes_delta: e.target.value }))}
                  required
                />
              </div>
              <div className="col-md-4">
                <label className="form-label small">Motif</label>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={form.motif}
                  onChange={(e) => setForm((f) => ({ ...f, motif: e.target.value }))}
                  required
                />
              </div>
            </div>
            <div className="mt-2 d-flex justify-content-end">
              <button type="submit" className="btn btn-sm btn-finance-accent" disabled={submitting}>
                {submitting ? 'Envoi…' : 'Soumettre'}
              </button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="text-center py-4 text-muted">Chargement…</div>
        ) : items.length === 0 ? (
          <div className="text-center py-4 text-muted">Aucun ajustement pour ce filtre.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm finance-table align-middle mb-0">
              <thead>
                <tr>
                  <th>Statut</th>
                  <th>Formateur</th>
                  <th>Séance</th>
                  <th>Δ minutes</th>
                  <th>Réalisé avant → après</th>
                  <th>Motif</th>
                  <th>Proposé</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span className={`badge ${STATUT_BADGE[item.statut] || 'bg-light text-dark'}`}>
                        {item.statut_label}
                      </span>
                    </td>
                    <td>{item.formateur?.label}</td>
                    <td>
                      <div className="small">
                        <strong>{item.session?.module_intitule}</strong>
                        <div className="text-muted">
                          {item.session?.grade} {item.session?.groupe} — {item.session?.date_journee}
                        </div>
                      </div>
                    </td>
                    <td>
                      <strong className={item.minutes_delta >= 0 ? 'text-success' : 'text-danger'}>
                        {item.minutes_delta >= 0 ? '+' : ''}{item.minutes_delta} min
                      </strong>
                    </td>
                    <td>
                      {fmtDuration(item.realise_avant_minutes)}
                      {' → '}
                      {fmtDuration(item.realise_apres_minutes)}
                    </td>
                    <td className="small" style={{ maxWidth: 200 }}>{item.motif}</td>
                    <td className="small text-muted">
                      {item.proposed_by}<br />
                      {formatDateTime(item.proposed_at)}
                    </td>
                    <td className="text-end text-nowrap">
                      {item.statut === 'EN_ATTENTE' && (
                        <>
                          <button
                            type="button"
                            className="btn btn-sm btn-success me-1"
                            disabled={actingId === item.id}
                            onClick={() => handleValidate(item.id)}
                          >
                            Valider
                          </button>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-danger"
                            disabled={actingId === item.id}
                            onClick={() => {
                              setRejectId(item.id)
                              setRejectMotif('')
                            }}
                          >
                            Rejeter
                          </button>
                        </>
                      )}
                      {item.statut === 'VALIDE' && (
                        <span className="small text-muted">
                          par {item.validated_by}
                        </span>
                      )}
                      {item.statut === 'REJETE' && (
                        <span className="small text-muted" title={item.rejection_motif}>
                          {item.rejection_motif || '—'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {rejectId && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.4)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Rejeter l&apos;ajustement</h5>
                <button type="button" className="btn-close" onClick={() => setRejectId(null)}></button>
              </div>
              <div className="modal-body">
                <label className="form-label">Motif de rejet</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={rejectMotif}
                  onChange={(e) => setRejectMotif(e.target.value)}
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setRejectId(null)}>
                  Annuler
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  disabled={actingId === rejectId}
                  onClick={handleReject}
                >
                  Confirmer le rejet
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </FinancePageShell>
  )
}
