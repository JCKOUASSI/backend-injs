import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

const DECISION_LABELS = {
  ADMIS: 'Admis', AJOURNE: 'Ajourné', EXCLUSION: 'Exclusion', EN_ATTENTE: 'En attente',
}
const DECISION_COLORS = {
  ADMIS:      { background: '#e8f5e9', color: '#1b5e20' },
  AJOURNE:    { background: '#fff3e0', color: '#e65100' },
  EXCLUSION:  { background: '#ffebee', color: '#b71c1c' },
  EN_ATTENTE: { background: '#f5f5f5', color: '#616161' },
}
const MENTION_LABELS = {
  TRES_BIEN: 'Très bien', BIEN: 'Bien', ASSEZ_BIEN: 'Assez bien', PASSABLE: 'Passable', '': '—',
}

export default function DecisionsPedagogiques() {
  const { formationId } = useParams()
  const { showToast } = useToast()

  const [formation, setFormation] = useState(null)
  const [decisions, setDecisions] = useState([])
  const [criteres, setCriteres] = useState({ seuil_admission: 12, taux_presence_min: 80 })
  const [loading, setLoading] = useState(true)
  const [recalc, setRecalc] = useState(false)
  const [filter, setFilter] = useState('')
  const [editing, setEditing] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [formRes, decRes] = await Promise.all([
        api.get(`/formations/${formationId}/`),
        api.get(`/evaluations/formations/${formationId}/decisions/`),
      ])
      setFormation(formRes.data)
      const payload = decRes.data
      setDecisions(Array.isArray(payload) ? payload : (payload.decisions || []))
      if (payload.criteres) setCriteres(payload.criteres)
    } catch {
      showToast('Erreur lors du chargement', 'error')
    } finally {
      setLoading(false)
    }
  }, [formationId, showToast])

  useEffect(() => { fetchData() }, [fetchData])

  const handleRecalc = async () => {
    setRecalc(true)
    try {
      const { data } = await api.post(`/evaluations/formations/${formationId}/decisions/recalculer/`)
      showToast(data.detail || 'Décisions recalculées', 'success')
      fetchData()
    } catch { showToast('Erreur recalcul', 'error') }
    finally { setRecalc(false) }
  }

  const handleValidate = async (dec, overrides = {}) => {
    try {
      await api.patch(`/evaluations/decisions/${dec.id}/`, overrides)
      showToast('Décision validée', 'success')
      setEditing(null)
      fetchData()
    } catch { showToast('Erreur validation', 'error') }
  }

  const filtered = filter ? decisions.filter(d => d.decision === filter) : decisions

  const stats = decisions.reduce((acc, d) => {
    acc[d.decision] = (acc[d.decision] || 0) + 1
    return acc
  }, {})

  if (loading) return <div className="loading"><div className="spinner"></div></div>

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 style={{ margin: 0, fontWeight: 700 }}>Décisions pédagogiques</h2>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            {formation?.formation} · {decisions.length} auditeur{decisions.length !== 1 ? 's' : ''}
            · Admis si moyenne ≥ <strong>{criteres.seuil_admission}/20</strong> et cours effectué ≥ <strong>{criteres.taux_presence_min}%</strong>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to={`/formations/${formationId}`} className="btn btn-sm btn-outline-secondary">
            <i className="bi bi-arrow-left me-1"></i>Retour
          </Link>
          <button className="btn btn-primary btn-sm" onClick={handleRecalc} disabled={recalc}>
            {recalc ? 'Calcul…' : <><i className="bi bi-arrow-clockwise me-1"></i>Recalculer (auto)</>}
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        {['ADMIS', 'AJOURNE', 'EXCLUSION', 'EN_ATTENTE'].map(k => (
          <div key={k} className="card" style={{ padding: '0.6rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', border: filter === k ? '2px solid var(--primary)' : '1px solid var(--border)' }}
            onClick={() => setFilter(filter === k ? '' : k)}>
            <span style={{ ...DECISION_COLORS[k], fontSize: '0.72rem', fontWeight: 700, padding: '2px 9px', borderRadius: '20px' }}>
              {DECISION_LABELS[k]}
            </span>
            <span style={{ fontWeight: 700 }}>{stats[k] || 0}</span>
          </div>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <i className="bi bi-clipboard-check" style={{ fontSize: '3rem', color: 'var(--text-muted)' }}></i>
          <p>Aucune décision. Cliquez sur « Recalculer » pour générer automatiquement.</p>
        </div>
      ) : (
        <div className="card" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)', background: 'var(--bg-secondary, #f9fafb)' }}>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 700 }}>Auditeur</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700 }}>Moyenne</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700 }}>Présence</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700 }}>Décision</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700 }}>Mention</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700 }}>Validée</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d, idx) => (
                <tr key={d.id} style={{ borderBottom: '1px solid var(--border)', background: idx % 2 === 0 ? 'transparent' : 'var(--bg-secondary, #fafafa)' }}>
                  <td style={{ padding: '0.65rem 1rem' }}>
                    <div style={{ fontWeight: 600 }}>{d.participant_nom}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{d.participant_matricule}</div>
                  </td>
                  <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                    <strong style={{ color: d.moyenne_generale >= criteres.seuil_admission ? '#2e7d32' : '#b71c1c' }}>
                      {d.moyenne_generale !== null ? `${d.moyenne_generale}/20` : '—'}
                    </strong>
                  </td>
                  <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                    {d.taux_presence !== null ? (
                      <span style={{ color: d.taux_presence >= criteres.taux_presence_min ? '#2e7d32' : '#b71c1c', fontWeight: 600 }}>
                        {d.taux_presence}%
                      </span>
                    ) : '—'}
                    {d.total_heures_prevues > 0 && (
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        {d.total_heures_presence}h / {d.total_heures_prevues}h
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                    {editing === d.id ? (
                      <select className="form-control form-control-sm" defaultValue={d.decision}
                        onChange={e => handleValidate(d, { decision: e.target.value })}>
                        {Object.keys(DECISION_LABELS).map(k => <option key={k} value={k}>{DECISION_LABELS[k]}</option>)}
                      </select>
                    ) : (
                      <span style={{ ...DECISION_COLORS[d.decision], fontSize: '0.72rem', fontWeight: 700, padding: '2px 9px', borderRadius: '20px' }}>
                        {DECISION_LABELS[d.decision]}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center', fontSize: '0.8rem' }}>
                    {MENTION_LABELS[d.mention] || '—'}
                  </td>
                  <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                    {d.validee_le
                      ? <i className="bi bi-check-circle-fill" style={{ color: '#2e7d32' }} title={`Validée par ${d.validee_par_nom}`}></i>
                      : <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>auto</span>}
                  </td>
                  <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                    {editing === d.id ? (
                      <button className="btn btn-sm btn-outline-secondary" style={{ fontSize: '0.72rem' }} onClick={() => setEditing(null)}>Fermer</button>
                    ) : (
                      <button className="btn btn-sm btn-outline-primary" style={{ fontSize: '0.72rem' }} onClick={() => setEditing(d.id)}>
                        <i className="bi bi-pencil me-1"></i>Ajuster
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
