import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

const fmtDuration = (minutes) => {
  const value = Number(minutes || 0)
  const h = Math.floor(value / 60)
  const m = Math.round(value % 60)
  return `${h}h ${m}min`
}

export default function FinanceDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await api.get('/formations/finance/dashboard/')
        setData(res.data || null)
        setError('')
      } catch {
        setError('Impossible de charger le dashboard finance.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div className="loading"><div className="spinner"></div></div>

  const kpis = data?.kpis || {}
  const top = Array.isArray(data?.top_formateurs) ? data.top_formateurs : []

  return (
    <div>
      {error && <div className="error-message">{error}</div>}

      <div className="card" style={{ marginBottom: '0.75rem' }}>
        <div className="card-header-bar">
          <span><i className="bi bi-cash-coin me-2"></i>Dashboard Finance</span>
          <Link to="/formateurs" className="btn btn-outline-primary btn-sm">
            Voir le détail formateurs
          </Link>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem', marginBottom: '0.85rem' }}>
        <div className="stat-card">
          <div className="stat-body">
            <div className="stat-icon"><i className="bi bi-person-video3"></i></div>
            <div>
              <div className="stat-value">{kpis.total_formateurs || 0}</div>
              <div className="stat-label">Formateurs (total)</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-body">
            <div className="stat-icon"><i className="bi bi-person-check"></i></div>
            <div>
              <div className="stat-value">{kpis.formateurs_actifs || 0}</div>
              <div className="stat-label">Formateurs actifs</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-body">
            <div className="stat-icon"><i className="bi bi-clock-history"></i></div>
            <div>
              <div className="stat-value">{fmtDuration(kpis.total_duree_minutes)}</div>
              <div className="stat-label">Temps de cours total</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-body">
            <div className="stat-icon"><i className="bi bi-calendar3"></i></div>
            <div>
              <div className="stat-value">{kpis.total_sessions || 0}</div>
              <div className="stat-label">Séances cumulées</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header-bar">
          <span><i className="bi bi-bar-chart-line me-2"></i>Top formateurs (temps total)</span>
        </div>
        <div className="card-body-flush">
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>N°</th>
                  <th>Nom</th>
                  <th>Prénom</th>
                  <th>Séances</th>
                  <th>Temps total</th>
                </tr>
              </thead>
              <tbody>
                {top.length > 0 ? top.map((f, idx) => (
                  <tr key={f.id}>
                    <td>{idx + 1}</td>
                    <td><span className="badge-bg-info">{f.numerobadge || '-'}</span></td>
                    <td><strong>{f.nom}</strong></td>
                    <td>{f.prenom}</td>
                    <td><span className="badge-bg-secondary">{f.sessions_count || 0}</span></td>
                    <td><span className="badge-bg-success">{fmtDuration(f.total_duree_minutes)}</span></td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="6" className="text-center py-4 text-muted">Aucune donnée finance disponible.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
