import { useEffect, useMemo, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import PaginationBar from '../../components/common/PaginationBar'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchTeachingUnits } from '../../api/academics'

export default function StudentCourses() {
  const { user } = useAuth()
  const semestre = user?.semestre || 1

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [creditFilter, setCreditFilter] = useState('')
  const [viewMode, setViewMode] = useState('cards')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [searchInput])

  const { data: units, loading, error } = useFetch(
    () => fetchTeachingUnits({ semester_number: semestre }).then((r) => r.results || r || []),
    [semestre],
  )

  const allUnits = units || []

  const totalCredits = allUnits.reduce((sum, ue) => sum + (ue.credits_ects || 0), 0)
  const totalEcue = allUnits.reduce((sum, ue) => sum + (ue.courses?.length || 0), 0)

  const creditBuckets = useMemo(() => {
    const map = {}
    for (const ue of allUnits) {
      const c = ue.credits_ects || 0
      map[c] = (map[c] || 0) + 1
    }
    return Object.entries(map)
      .map(([value, count]) => ({ value: Number(value), count }))
      .sort((a, b) => a.value - b.value)
  }, [allUnits])

  const filtered = useMemo(() => {
    return allUnits.filter((ue) => {
      if (creditFilter !== '' && Number(ue.credits_ects) !== Number(creditFilter)) return false
      if (!search) return true
      const hay = `${ue.code || ''} ${ue.name || ''} ${(ue.courses || []).map((c) => `${c.code} ${c.name}`).join(' ')}`.toLowerCase()
      return hay.includes(search)
    })
  }, [allUnits, creditFilter, search])

  const total = filtered.length
  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return filtered.slice(start, start + pageSize)
  }, [filtered, page, pageSize])

  const setCreditAndReset = (value) => {
    setCreditFilter(value)
    setPage(1)
  }

  if (loading && !units) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-4">Erreur : {error}</div>
  }

  return (
    <>
      <PageHeader
        title="Mes UE / ECUE"
        subtitle={`${user?.niveau || '—'} — Semestre ${semestre} — ${totalCredits} CECT`}
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{allUnits.length}</div>
            <div className="small text-muted">UE du semestre</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{totalEcue}</div>
            <div className="small text-muted">ECUE</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{totalCredits}</div>
            <div className="small text-muted">Crédits CECT</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{total}</div>
            <div className="small text-muted">Résultats filtrés</div>
          </div>
        </div>
      </div>

      <div className="card-injs p-3 mb-3">
        <div className="d-flex flex-wrap gap-2 align-items-center">
          <span className="small text-muted me-1">Crédits :</span>
          <button
            type="button"
            className={`btn btn-sm ${creditFilter === '' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setCreditAndReset('')}
          >
            Toutes ({allUnits.length})
          </button>
          {creditBuckets.map((b) => (
            <button
              key={b.value}
              type="button"
              className={`btn btn-sm ${Number(creditFilter) === b.value ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => setCreditAndReset(String(b.value))}
            >
              {b.value} CECT <span className="opacity-75">({b.count})</span>
            </button>
          ))}
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-6">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="Code UE, nom, ECUE…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Crédits</label>
            <select
              className="form-select"
              value={creditFilter}
              onChange={(ev) => setCreditAndReset(ev.target.value)}
            >
              <option value="">Tous</option>
              {creditBuckets.map((b) => (
                <option key={b.value} value={b.value}>{b.value} CECT</option>
              ))}
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Affichage</label>
            <div className="btn-group w-100" role="group">
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'table' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setViewMode('table')}
              >
                Liste
              </button>
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'cards' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setViewMode('cards')}
              >
                Cartes
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card-injs position-relative rooms-list-shell">
        {loading && (
          <div className="position-absolute top-0 end-0 m-2" style={{ zIndex: 3 }}>
            <div className="spinner-border spinner-border-sm text-primary" />
          </div>
        )}

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          pageSizeOptions={[6, 10, 15, 25]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />

        <div className="rooms-list-body">
          {viewMode === 'table' ? (
            <div className="table-responsive">
              <table className="table table-hover mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>UE</th>
                    <th>CECT</th>
                    <th>ECUE</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((ue) => (
                    <tr key={ue.id}>
                      <td><code className="small">{ue.code}</code></td>
                      <td>
                        <div className="fw-semibold">{ue.name}</div>
                        {(ue.courses || []).length > 0 && (
                          <small className="text-muted d-block mt-1">
                            {(ue.courses || []).map((c) => c.code).join(' · ')}
                          </small>
                        )}
                      </td>
                      <td><span className="badge-injs">{ue.credits_ects} CECT</span></td>
                      <td>{ue.courses?.length || 0}</td>
                    </tr>
                  ))}
                  {!pageItems.length && (
                    <tr>
                      <td colSpan={4} className="text-center text-muted py-4">Aucune UE trouvée</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {pageItems.map((ue) => (
                  <div key={ue.id} className="col-md-6">
                    <div className="border rounded-3 p-3 h-100 student-ue-plaque">
                      <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
                        <code className="student-ue-code">{ue.code}</code>
                        <span className="badge-injs flex-shrink-0">{ue.credits_ects} CECT</span>
                      </div>
                      <h6 className="student-ue-title mb-2">{ue.name}</h6>
                      <div className="small text-muted text-uppercase fw-semibold mb-1" style={{ fontSize: '0.7rem' }}>
                        ECUE ({ue.courses?.length || 0})
                      </div>
                      {(ue.courses || []).length === 0 ? (
                        <p className="small text-muted mb-0">Aucun ECUE</p>
                      ) : (
                        <ul className="small text-muted mb-0 ps-3 student-ue-ecue">
                          {ue.courses.map((c) => (
                            <li key={c.id}>
                              <code>{c.code}</code> — {c.name}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                ))}
                {!pageItems.length && (
                  <div className="col-12 text-center text-muted py-4">Aucune UE trouvée</div>
                )}
              </div>
            </div>
          )}
        </div>

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          pageSizeOptions={[6, 10, 15, 25]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />
      </div>
    </>
  )
}
