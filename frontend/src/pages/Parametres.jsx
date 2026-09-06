import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'
import { formatApiErrors } from '../utils/apiErrors'

const CATEGORIES = [
  { value: 'general', label: 'Général', icon: 'bi-building' },
  { value: 'scolarite', label: 'Scolarité / LMD', icon: 'bi-mortarboard' },
  { value: 'presences', label: 'Présences', icon: 'bi-qr-code' },
  { value: 'edt', label: 'EDT (import)', icon: 'bi-calendar3' },
  { value: 'notifications', label: 'Notifications', icon: 'bi-bell' },
  { value: 'securite', label: 'Sécurité', icon: 'bi-shield-lock' },
  { value: 'interface', label: 'Interface', icon: 'bi-palette' },
]

function parseChoices(json) {
  try {
    const parsed = JSON.parse(json || '{}')
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function displayValue(row) {
  if (row.type === 'bool') {
    const v = String(row.valeur || '').toLowerCase()
    return ['true', '1', 'yes', 'oui'].includes(v) ? 'Oui' : 'Non'
  }
  return row.valeur || '—'
}

function ParamValueInput({ type, value, choices, onChange, disabled }) {
  if (type === 'bool') {
    return (
      <select className="form-select" value={value} onChange={e => onChange(e.target.value)} disabled={disabled}>
        <option value="true">Oui</option>
        <option value="false">Non</option>
      </select>
    )
  }
  if (type === 'choice' && choices) {
    return (
      <select className="form-select" value={value} onChange={e => onChange(e.target.value)} disabled={disabled}>
        <option value="">—</option>
        {Object.entries(choices).map(([k, v]) => (
          <option key={k} value={k}>{v}</option>
        ))}
      </select>
    )
  }
  if (type === 'integer' || type === 'decimal') {
    return (
      <input
        type="number"
        className="form-control"
        step={type === 'decimal' ? '0.01' : '1'}
        min="0"
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
      />
    )
  }
  if (type === 'email') {
    return (
      <input type="email" className="form-control" value={value} onChange={e => onChange(e.target.value)} disabled={disabled} />
    )
  }
  if (type === 'date') {
    return (
      <input type="date" className="form-control" value={value} onChange={e => onChange(e.target.value)} disabled={disabled} />
    )
  }
  return (
    <input type="text" className="form-control" value={value} onChange={e => onChange(e.target.value)} disabled={disabled} />
  )
}

export default function Parametres() {
  const { showToast } = useToast()
  const [tab, setTab] = useState('general')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [params, setParams] = useState([])
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState({})
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get('/parametres/', { params: { actif: 'true' } })
      setParams(res.data?.results ?? res.data ?? [])
    } catch {
      showToast('Erreur de chargement des paramètres.', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const visibleTabs = useMemo(() => {
    const counts = {}
    params.forEach(p => { counts[p.categorie] = (counts[p.categorie] || 0) + 1 })
    return CATEGORIES.filter(c => counts[c.value])
  }, [params])

  useEffect(() => {
    if (visibleTabs.length && !visibleTabs.some(c => c.value === tab)) {
      setTab(visibleTabs[0].value)
    }
  }, [visibleTabs, tab])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return params.filter(p => {
      if (p.categorie !== tab) return false
      if (!q) return true
      return [p.libelle, p.cle, p.description, p.valeur].some(
        v => String(v || '').toLowerCase().includes(q)
      )
    })
  }, [params, tab, query])

  const openEdit = (row) => {
    setHistory([])
    setModal({ type: 'edit', row })
    setForm({
      valeur: row.valeur,
      motif_modification: '',
      confirmation: false,
    })
  }

  const closeModal = () => {
    setModal(null)
    setForm({})
    setHistory([])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!modal || modal.type !== 'edit') return
    const row = modal.row
    if (row.est_critique && !form.confirmation) {
      showToast('Cochez la confirmation pour ce paramètre critique.', 'error')
      return
    }
    setSaving(true)
    try {
      const payload = {
        valeur: form.valeur,
        motif_modification: form.motif_modification || '',
      }
      if (row.est_critique) payload.confirmation = true
      await api.patch(`/parametres/${row.id}/`, payload)
      showToast('Paramètre enregistré')
      closeModal()
      await load()
    } catch (err) {
      showToast(formatApiErrors(err.response?.data, { fallback: 'Erreur lors de l\'enregistrement' }), 'error')
    } finally {
      setSaving(false)
    }
  }

  const openHistory = async (row) => {
    setModal({ type: 'history', row })
    setHistoryLoading(true)
    try {
      const res = await api.get(`/parametres/${row.id}/historique/`)
      setHistory(res.data ?? [])
    } catch {
      showToast('Erreur de chargement de l\'historique.', 'error')
    } finally {
      setHistoryLoading(false)
    }
  }

  const canEdit = (row) => row.can_edit && row.modifiable
  const editing = modal?.type === 'edit' ? modal.row : null

  return (
    <div className="container-fluid">
      <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
        <h4 className="mb-0"><i className="bi bi-gear me-2"></i>Paramètres</h4>
        <input
          type="search"
          className="form-control"
          style={{ maxWidth: 280 }}
          placeholder="Rechercher un paramètre…"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </div>

      <p className="text-muted small mb-3">
        Paramètres fonctionnels de l’établissement. Les tarifs finance restent dans{' '}
        <Link to="/finance-parametrage">Paramétrage finance</Link>.
        Les emplois du temps sont générés dans <strong>app-ept-injs-lmd 2026</strong> puis importés dans Cours → Séances.
      </p>

      <ul className="nav nav-tabs mb-3">
        {visibleTabs.map(c => (
          <li className="nav-item" key={c.value}>
            <button
              type="button"
              className={`nav-link ${tab === c.value ? 'active' : ''}`}
              onClick={() => setTab(c.value)}
            >
              <i className={`${c.icon} me-1`}></i>{c.label}
            </button>
          </li>
        ))}
      </ul>

      {loading ? (
        <div className="loading py-5"><div className="spinner"></div></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-5 text-muted">
          <i className="bi bi-inbox" style={{ fontSize: '2rem' }}></i>
          <p className="mt-2">Aucun paramètre dans cette catégorie.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-hover align-middle">
            <thead className="table-light">
              <tr>
                <th>Libellé</th>
                <th>Clé</th>
                <th>Type</th>
                <th style={{ minWidth: 220 }}>Valeur</th>
                <th style={{ width: 110 }}>Modifiable</th>
                <th style={{ width: 160 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(row => (
                <tr key={row.id}>
                  <td>
                    <div className="fw-semibold">
                      {row.libelle}
                      {row.est_critique && (
                        <span className="badge bg-warning text-dark ms-2">Critique</span>
                      )}
                    </div>
                    {row.description && (
                      <small className="text-muted" style={{ display: 'block', marginTop: 2 }}>
                        {row.description}
                      </small>
                    )}
                  </td>
                  <td><code>{row.cle}</code></td>
                  <td>{row.type}</td>
                  <td>{displayValue(row)}</td>
                  <td>
                    {row.modifiable ? (
                      <span className="badge bg-success">Oui</span>
                    ) : (
                      <span className="badge bg-secondary">Non</span>
                    )}
                  </td>
                  <td>
                    <div className="btn-group">
                      <button
                        type="button"
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => openEdit(row)}
                        disabled={!canEdit(row)}
                        title={canEdit(row) ? 'Modifier' : 'Non modifiable'}
                      >
                        <i className="bi bi-pencil"></i>
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => openHistory(row)}
                        title="Historique"
                      >
                        <i className="bi bi-clock-history"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" style={{ maxWidth: 520 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h5>Modifier le paramètre</h5>
              <button type="button" className="btn-close" onClick={closeModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <p className="small text-muted mb-3">
                  <strong>{editing.libelle}</strong> <code>({editing.cle})</code>
                </p>
                <div className="mb-3">
                  <div className="small text-muted">Ancienne valeur</div>
                  <code>{displayValue(editing)}</code>
                </div>
                <div className="form-group mb-3">
                  <label className="form-label">Nouvelle valeur</label>
                  <ParamValueInput
                    type={editing.type}
                    value={form.valeur ?? ''}
                    choices={parseChoices(editing.choices_json)}
                    onChange={val => setForm(prev => ({ ...prev, valeur: val }))}
                    disabled={saving || !editing.modifiable}
                  />
                </div>
                <div className="form-group mb-3">
                  <label className="form-label">
                    Motif de modification {editing.est_critique ? '(obligatoire)' : '(optionnel)'}
                  </label>
                  <textarea
                    className="form-control"
                    rows={2}
                    value={form.motif_modification ?? ''}
                    onChange={e => setForm(prev => ({ ...prev, motif_modification: e.target.value }))}
                    placeholder="Raison du changement..."
                    disabled={saving}
                    required={Boolean(editing.est_critique)}
                  />
                </div>
                {editing.est_critique && (
                  <div className="form-check">
                    <input
                      id="confirm-param"
                      type="checkbox"
                      className="form-check-input"
                      checked={Boolean(form.confirmation)}
                      onChange={e => setForm(prev => ({ ...prev, confirmation: e.target.checked }))}
                      disabled={saving}
                    />
                    <label className="form-check-label" htmlFor="confirm-param">
                      Je confirme le remplacement de <code>{displayValue(editing)}</code> par <code>{form.valeur || '—'}</code>
                    </label>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={closeModal} disabled={saving}>Annuler</button>
                <button type="submit" className="btn btn-dfrc" disabled={saving || !editing.modifiable}>
                  {saving ? 'Enregistrement…' : 'Enregistrer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {modal?.type === 'history' && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" style={{ maxWidth: 640 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h5>Historique — {modal.row.libelle}</h5>
              <button type="button" className="btn-close" onClick={closeModal}>&times;</button>
            </div>
            <div className="modal-body">
              {historyLoading ? (
                <div className="loading py-3"><div className="spinner"></div></div>
              ) : history.length === 0 ? (
                <p className="text-muted mb-0">Aucune modification enregistrée.</p>
              ) : (
                <div className="table-responsive">
                  <table className="table table-sm">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Utilisateur</th>
                        <th>Ancienne valeur</th>
                        <th>Nouvelle valeur</th>
                        <th>Motif</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map(h => (
                        <tr key={h.id}>
                          <td className="small">{new Date(h.modifie_le).toLocaleString('fr-FR')}</td>
                          <td>{h.modifie_par_username ?? '—'}</td>
                          <td><code>{h.ancienne_valeur ?? '—'}</code></td>
                          <td><code>{h.nouvelle_valeur ?? '—'}</code></td>
                          <td className="small">{h.motif_modification || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={closeModal}>Fermer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
