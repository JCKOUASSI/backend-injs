import { useEffect, useMemo, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import PaginationBar from '../../components/common/PaginationBar'
import { useFetch } from '../../hooks/useFetch'
import { fetchPrograms, fetchSpecializations, fetchPromotions, fetchAcademicYears } from '../../api/academics'
import { GRADES_LMD } from '../../data/mockData'

function programGrade(p) {
  const raw = String(p.degree || p.degree_type || p.level || p.code || '').toLowerCase()
  if (raw.startsWith('l') || raw.includes('licence')) return 'licence'
  if (raw.startsWith('m') || raw.includes('master')) return 'master'
  if (raw.startsWith('d') || raw.includes('doctor')) return 'doctorat'
  return 'autre'
}

function gradeLabel(id) {
  return GRADES_LMD.find((g) => g.id === id)?.label || id
}

export default function AdminFormations() {
  const { data: programs, loading } = useFetch(() => fetchPrograms({ page_size: 200 }))
  const { data: specializations } = useFetch(() => fetchSpecializations({ page_size: 200 }))
  const { data: promotions } = useFetch(() => fetchPromotions({ page_size: 200 }))
  const { data: years } = useFetch(() => fetchAcademicYears())

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [gradeFilter, setGradeFilter] = useState('')
  const [viewMode, setViewMode] = useState('table')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [searchInput])

  const allPrograms = programs || []
  const allSpecs = specializations || []
  const allPromos = promotions || []

  const byGrade = useMemo(() => {
    const map = { licence: 0, master: 0, doctorat: 0, autre: 0 }
    for (const p of allPrograms) {
      const g = programGrade(p)
      map[g] = (map[g] || 0) + 1
    }
    return map
  }, [allPrograms])

  const filtered = useMemo(() => {
    return allPrograms.filter((p) => {
      if (gradeFilter && programGrade(p) !== gradeFilter) return false
      if (!search) return true
      const hay = `${p.code || ''} ${p.name || ''} ${p.track || ''} ${p.degree || ''} ${p.level || ''}`.toLowerCase()
      return hay.includes(search)
    })
  }, [allPrograms, gradeFilter, search])

  const total = filtered.length
  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return filtered.slice(start, start + pageSize)
  }, [filtered, page, pageSize])

  const rows = filtered.map((p) => [
    p.code,
    p.name,
    gradeLabel(programGrade(p)),
    p.track || '—',
    p.credits_ects || p.duration_years || '—',
  ])

  const setGradeAndReset = (value) => {
    setGradeFilter(value)
    setPage(1)
  }

  if (loading && !programs) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  return (
    <>
      <PageHeader
        title="Formations LMD"
        subtitle="Filières, promotions et spécialités (référentiel API)"
        action={
          <ExportButtons
            title="Formations INJS"
            filename="injs_formations"
            headers={['Code', 'Nom', 'Grade', 'Track', 'Crédits/Durée']}
            rows={rows}
            resourcePath="/academics/programs"
          />
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{allPrograms.length}</div>
            <div className="small text-muted">Programmes</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{allSpecs.length}</div>
            <div className="small text-muted">Spécialités</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{allPromos.length}</div>
            <div className="small text-muted">Promotions</div>
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
          <span className="small text-muted me-1">Grades :</span>
          <button
            type="button"
            className={`btn btn-sm ${gradeFilter === '' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setGradeAndReset('')}
          >
            Tous ({allPrograms.length})
          </button>
          {GRADES_LMD.map((g) => (
            <button
              key={g.id}
              type="button"
              className={`btn btn-sm ${gradeFilter === g.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => setGradeAndReset(g.id)}
              title={`${g.credits} ECTS · ${g.duree}`}
            >
              {g.label} <span className="opacity-75">({byGrade[g.id] || 0})</span>
            </button>
          ))}
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-5">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="Code, intitulé, track…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-4">
            <label className="form-label small mb-1">Grade</label>
            <select
              className="form-select"
              value={gradeFilter}
              onChange={(ev) => setGradeAndReset(ev.target.value)}
            >
              <option value="">Tous</option>
              {GRADES_LMD.map((g) => (
                <option key={g.id} value={g.id}>{g.label}</option>
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

      <div className="card-injs position-relative rooms-list-shell mb-4">
        {loading && (
          <div className="position-absolute top-0 end-0 m-2" style={{ zIndex: 3 }}>
            <div className="spinner-border spinner-border-sm text-primary" />
          </div>
        )}

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          disabled={loading}
          pageSizeOptions={[10, 15, 25, 50]}
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
                    <th>Intitulé</th>
                    <th>Grade</th>
                    <th>Track</th>
                    <th>Crédits / durée</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((p) => {
                    const g = programGrade(p)
                    return (
                      <tr key={p.id}>
                        <td><code className="small">{p.code}</code></td>
                        <td className="fw-semibold">{p.name}</td>
                        <td>
                          <span className={`badge-injs badge-lmd-${g}`}>{gradeLabel(g)}</span>
                        </td>
                        <td>{p.track || '—'}</td>
                        <td className="small text-muted">
                          {p.credits_ects ? `${p.credits_ects} ECTS` : (p.duration_years ? `${p.duration_years} an(s)` : '—')}
                        </td>
                      </tr>
                    )
                  })}
                  {!pageItems.length && (
                    <tr>
                      <td colSpan={5} className="text-center text-muted py-4">
                        Aucun programme — importer la maquette STAPS.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {pageItems.map((p) => {
                  const g = programGrade(p)
                  const meta = GRADES_LMD.find((x) => x.id === g)
                  return (
                    <div key={p.id} className="col-md-6 col-xl-4">
                      <div className="border rounded-3 p-3 h-100">
                        <div className="d-flex justify-content-between align-items-start mb-2">
                          <code className="small">{p.code}</code>
                          <span className={`badge-injs badge-lmd-${g}`}>{gradeLabel(g)}</span>
                        </div>
                        <h6 className="fw-bold mb-2">{p.name}</h6>
                        <p className="small text-muted mb-1">
                          Track : <strong className="text-dark">{p.track || '—'}</strong>
                        </p>
                        <p className="small text-muted mb-0">
                          {p.credits_ects
                            ? `${p.credits_ects} ECTS`
                            : (meta ? `${meta.credits} ECTS · ${meta.duree}` : '—')}
                        </p>
                      </div>
                    </div>
                  )
                })}
                {!pageItems.length && (
                  <div className="col-12 text-center text-muted py-4">
                    Aucun programme — importer la maquette STAPS.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          disabled={loading}
          pageSizeOptions={[10, 15, 25, 50]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />
      </div>

      <div className="row g-3">
        <div className="col-lg-6">
          <div className="card-injs p-3 h-100">
            <h6 className="fw-bold mb-2">Spécialités STAPS ({allSpecs.length})</h6>
            {allSpecs.length === 0 ? (
              <p className="text-muted small mb-0">Aucune spécialité.</p>
            ) : allSpecs.map((s) => (
              <div key={s.id} className="d-flex justify-content-between py-2 border-bottom">
                <span className="small"><strong>{s.code}</strong> — {s.name}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="col-lg-6">
          <div className="card-injs p-3 h-100">
            <h6 className="fw-bold mb-2">Promotions & années ({allPromos.length})</h6>
            <p className="small text-muted mb-2">
              Années : {(years || []).map((y) => y.name || y.label).join(', ') || '—'}
            </p>
            {allPromos.length === 0 ? (
              <p className="text-muted small mb-0">Aucune promotion.</p>
            ) : allPromos.map((p) => (
              <div key={p.id} className="d-flex justify-content-between align-items-center py-2 border-bottom gap-2">
                <span className="small fw-semibold">{p.name || p.code}</span>
                <span className="badge-injs text-truncate" style={{ maxWidth: '55%' }}>
                  {p.program_name || ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
