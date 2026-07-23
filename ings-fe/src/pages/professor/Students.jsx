import { useEffect, useMemo, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import PaginationBar from '../../components/common/PaginationBar'
import { useFetch } from '../../hooks/useFetch'
import { fetchStudents, fetchStudentsMeta } from '../../api/students'
import { StatusBadge } from '../../utils/statusBadge'
import { mediaUrl } from '../../utils/labels'

function genderLabel(g) {
  if (g === 'M') return 'H'
  if (g === 'F') return 'F'
  return '—'
}

function studentPhoto(e) {
  return mediaUrl(e.photoUrl) || e.photoUrl
}

function initials(e) {
  return `${e.prenom?.[0] || ''}${e.nom?.[0] || ''}`.toUpperCase() || '?'
}

export default function ProfStudents() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [program, setProgram] = useState('')
  const [promotion, setPromotion] = useState('')
  const [status, setStatus] = useState('')
  const [gender, setGender] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)
  const [viewMode, setViewMode] = useState('table')

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(t)
  }, [searchInput])

  const filters = useMemo(() => ({
    search: search || undefined,
    program: program || undefined,
    promotion: promotion || undefined,
    status: status || undefined,
    gender: gender || undefined,
    page,
    page_size: pageSize,
  }), [search, program, promotion, status, gender, page, pageSize])

  const { data, loading, error } = useFetch(
    () => fetchStudents(filters),
    [filters.search, filters.program, filters.promotion, filters.status, filters.gender, filters.page, filters.page_size],
  )
  const { data: meta } = useFetch(() => fetchStudentsMeta(), [])

  const students = data?.results || []
  const total = data?.count ?? 0
  const programOptions = meta?.programs || []
  const promotionOptions = (meta?.promotions || []).filter((p) => !program || p.program === program)
  const statusOptions = meta?.statuses || []
  const counts = meta?.counts || {}

  const setFilterAndResetPage = (setter) => (value) => {
    setter(value)
    setPage(1)
  }

  const rows = students.map((e) => [
    e.id,
    e.nom,
    e.prenom,
    e.programName || e.specialite || '—',
    e.promotionName || e.niveau || '—',
    genderLabel(e.gender),
    e.statut,
  ])

  if (loading && !data) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-4">Erreur de chargement : {error}</div>
  }

  return (
    <>
      <PageHeader
        title="Mes étudiants"
        subtitle={`Cohortes accessibles — ${counts.total ?? total} étudiant(s)`}
        action={
          <ExportButtons
            title="Liste étudiants"
            filename="mes_etudiants"
            headers={['Matricule', 'Nom', 'Prénom', 'Formation', 'Promotion', 'Genre', 'Statut']}
            rows={rows}
            resourcePath="/students"
          />
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{counts.total ?? total}</div>
            <div className="small text-muted">Étudiants</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{counts.men ?? '—'}</div>
            <div className="small text-muted">Hommes</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{counts.women ?? '—'}</div>
            <div className="small text-muted">Femmes</div>
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
          <span className="small text-muted me-1">Formations :</span>
          <button
            type="button"
            className={`btn btn-sm ${!program ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => {
              setProgram('')
              setPromotion('')
              setPage(1)
            }}
          >
            Toutes ({counts.total ?? '—'})
          </button>
          {programOptions.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`btn btn-sm ${program === p.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => {
                setProgram(p.id)
                setPromotion('')
                setPage(1)
              }}
              title={p.name}
            >
              {p.code} <span className="opacity-75">({p.count})</span>
            </button>
          ))}
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-3">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="Matricule, nom, email…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Promotion</label>
            <select
              className="form-select"
              value={promotion}
              onChange={(ev) => setFilterAndResetPage(setPromotion)(ev.target.value)}
            >
              <option value="">Toutes</option>
              {promotionOptions.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.count})</option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Genre</label>
            <select
              className="form-select"
              value={gender}
              onChange={(ev) => setFilterAndResetPage(setGender)(ev.target.value)}
            >
              <option value="">Tous</option>
              <option value="M">Hommes</option>
              <option value="F">Femmes</option>
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Statut</label>
            <select
              className="form-select"
              value={status}
              onChange={(ev) => setFilterAndResetPage(setStatus)(ev.target.value)}
            >
              <option value="">Tous</option>
              {statusOptions.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
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
                    <th>Photo</th>
                    <th>Matricule</th>
                    <th>Nom & Prénom</th>
                    <th>Formation</th>
                    <th>Promotion</th>
                    <th>Genre</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((e) => {
                    const photo = studentPhoto(e)
                    return (
                      <tr key={e.uuid || e.id}>
                        <td>
                          {photo ? (
                            <img src={photo} alt="" className="student-photo-sm" />
                          ) : (
                            <div className="student-photo-sm student-photo-placeholder">{initials(e)}</div>
                          )}
                        </td>
                        <td><code className="small">{e.id}</code></td>
                        <td>
                          <div className="fw-semibold">{e.nom} {e.prenom}</div>
                          {e.email && <small className="text-muted">{e.email}</small>}
                        </td>
                        <td className="small">{e.programName || e.specialite || '—'}</td>
                        <td><span className="badge-injs">{e.promotionName || e.niveau}</span></td>
                        <td>{genderLabel(e.gender)}</td>
                        <td><StatusBadge statut={e.statut} /></td>
                      </tr>
                    )
                  })}
                  {!students.length && (
                    <tr>
                      <td colSpan={7} className="text-center text-muted py-4">Aucun étudiant trouvé</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {students.map((e) => {
                  const photo = studentPhoto(e)
                  return (
                    <div key={e.uuid || e.id} className="col-md-6 col-xl-4">
                      <div className="border rounded-3 p-3 h-100">
                        <div className="d-flex justify-content-between align-items-start mb-2">
                          <code className="small">{e.id}</code>
                          <StatusBadge statut={e.statut} />
                        </div>
                        <div className="d-flex align-items-center gap-2 mb-2">
                          {photo ? (
                            <img src={photo} alt="" className="student-photo-sm" />
                          ) : (
                            <div className="student-photo-sm student-photo-placeholder">{initials(e)}</div>
                          )}
                          <div>
                            <h6 className="fw-bold mb-0">{e.nom} {e.prenom}</h6>
                            <small className="text-muted">{genderLabel(e.gender)}</small>
                          </div>
                        </div>
                        <p className="small text-muted mb-0">
                          {e.programName || e.specialite || '—'} · {e.promotionName || e.niveau}
                        </p>
                      </div>
                    </div>
                  )
                })}
                {!students.length && (
                  <div className="col-12 text-center text-muted py-4">Aucun étudiant trouvé</div>
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
    </>
  )
}
