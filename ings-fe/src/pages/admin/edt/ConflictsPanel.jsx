import { useMemo } from 'react'
import { FiAlertTriangle } from 'react-icons/fi'
import { useFetch } from '../../../hooks/useFetch'
import { fetchSeanceConflicts } from '../../../api/faculty'

export default function ConflictsPanel({ filters }) {
  const params = useMemo(
    () => ({ period: filters.period || undefined, promotion: filters.promotion || undefined }),
    [filters.period, filters.promotion],
  )
  const { data, loading, error } = useFetch(() => fetchSeanceConflicts(params), [params])
  const rows = data?.results || []

  return (
    <div className="card-injs">
      <div className="p-3 border-bottom d-flex justify-content-between align-items-center">
        <h2 className="h6 mb-0">Conflits des séances datées</h2>
        <span className="small text-muted">
          {data?.errors || 0} erreur(s) · {data?.warnings || 0} alerte(s)
        </span>
      </div>
      {error && <div className="alert alert-danger m-3">{error}</div>}
      {loading && <div className="text-center py-4"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {!loading && rows.length === 0 && (
        <p className="text-muted p-4 mb-0">Aucun conflit sur ce périmètre.</p>
      )}
      {rows.length > 0 && (
        <div className="table-responsive">
          <table className="table table-hover mb-0">
            <thead>
              <tr>
                <th>Gravité</th>
                <th>Type</th>
                <th>Message</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  <td>
                    <span className={`badge ${row.severity === 'error' ? 'bg-danger' : 'bg-warning text-dark'}`}>
                      {row.severity === 'error' ? 'Erreur' : 'Alerte'}
                    </span>
                  </td>
                  <td>{row.type}</td>
                  <td>
                    <FiAlertTriangle className="me-1 text-warning" />
                    {row.message}
                  </td>
                  <td>{row.date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
