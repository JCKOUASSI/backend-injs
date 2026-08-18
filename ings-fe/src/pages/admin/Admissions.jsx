import { useEffect, useMemo, useState } from 'react'
import { FiInbox, FiUsers, FiFolder, FiClock } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import PaginationBar from '../../components/common/PaginationBar'
import { useFetch } from '../../hooks/useFetch'
import { fetchCampaigns, fetchPreRegistrations } from '../../api/admissions'
import { StatusBadge } from '../../utils/statusBadge'
import { translateStatus } from '../../utils/labels'

function candidateName(p) {
  const first = p.first_name || p.prenom || ''
  const last = p.last_name || p.nom || ''
  return `${first} ${last}`.trim() || '—'
}

function candidateEmail(p) {
  return p.email || p.candidate_email || '—'
}

function candidateProgram(p) {
  return p.desired_program || p.program_name || p.program || '—'
}

function isOpenCampaign(c) {
  return c.is_open === true || c.is_active === true || c.status === 'open' || c.status === 'ouverte'
}

function initials(p) {
  const first = (p.first_name || p.prenom || '?')[0] || '?'
  const last = (p.last_name || p.nom || '')[0] || ''
  return `${first}${last}`.toUpperCase()
}

export default function AdminAdmissions() {
  const { data: campaigns, loading: loadingCampaigns } = useFetch(() => fetchCampaigns({ page_size: 100 }))
  const { data: prereg, loading } = useFetch(() => fetchPreRegistrations({ page_size: 200 }))

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [campaignFilter, setCampaignFilter] = useState('')
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

  const allCampaigns = campaigns || []
  const dossiers = prereg?.results || []

  const counts = useMemo(() => {
    let pending = 0
    let accepted = 0
    let rejected = 0
    for (const p of dossiers) {
      if (p.status === 'pending' || p.status === 'submitted') pending += 1
      else if (p.status === 'accepted') accepted += 1
      else if (p.status === 'rejected') rejected += 1
    }
    return {
      campaigns: allCampaigns.length,
      openCampaigns: allCampaigns.filter(isOpenCampaign).length,
      dossiers: prereg?.count ?? dossiers.length,
      pending,
      accepted,
      rejected,
    }
  }, [allCampaigns, dossiers, prereg?.count])

  const filtered = useMemo(() => {
    return dossiers.filter((p) => {
      if (statusFilter === 'pending' && !(p.status === 'pending' || p.status === 'submitted')) return false
      if (statusFilter === 'accepted' && p.status !== 'accepted') return false
      if (statusFilter === 'rejected' && p.status !== 'rejected') return false
      if (campaignFilter && String(p.campaign) !== campaignFilter && String(p.campaign_id) !== campaignFilter) return false
      if (!search) return true
      const hay = `${candidateEmail(p)} ${candidateName(p)} ${candidateProgram(p)} ${p.status || ''} ${translateStatus(p.status)}`.toLowerCase()
      return hay.includes(search)
    })
  }, [dossiers, statusFilter, campaignFilter, search])

  const total = filtered.length
  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return filtered.slice(start, start + pageSize)
  }, [filtered, page, pageSize])

  const rows = filtered.map((p) => [
    candidateEmail(p),
    p.first_name || p.prenom || '—',
    p.last_name || p.nom || '—',
    translateStatus(p.status),
    candidateProgram(p),
  ])

  const setStatusAndReset = (value) => {
    setStatusFilter(value)
    setPage(1)
  }

  const setCampaignAndReset = (value) => {
    setCampaignFilter(value)
    setPage(1)
  }

  if (loading && !prereg && loadingCampaigns) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  return (
    <>
      <PageHeader
        title="Admissions & préinscriptions"
        subtitle="Campagnes et dossiers candidats — vue Gestion des salles"
        action={
          <ExportButtons
            title="Préinscriptions INJS"
            filename="preinscriptions"
            headers={['Email', 'Prénom', 'Nom', 'Statut', 'Filière']}
            rows={rows}
          />
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{counts.campaigns}</div>
            <div className="small text-muted">Campagnes</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{counts.dossiers}</div>
            <div className="small text-muted">Dossiers</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-warning">{counts.pending}</div>
            <div className="small text-muted">À instruire</div>
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
          <span className="small text-muted me-1">Statut :</span>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === '' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('')}
          >
            Tous ({counts.dossiers})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'pending' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('pending')}
          >
            À instruire <span className="opacity-75">({counts.pending})</span>
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'accepted' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('accepted')}
          >
            Acceptés <span className="opacity-75">({counts.accepted})</span>
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'rejected' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('rejected')}
          >
            Rejetés <span className="opacity-75">({counts.rejected})</span>
          </button>
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-4">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="Email, nom, filière…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Campagne</label>
            <select
              className="form-select"
              value={campaignFilter}
              onChange={(ev) => setCampaignAndReset(ev.target.value)}
            >
              <option value="">Toutes</option>
              {allCampaigns.map((c) => (
                <option key={c.id} value={c.id}>{c.name || c.title}</option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Statut</label>
            <select
              className="form-select"
              value={statusFilter}
              onChange={(ev) => setStatusAndReset(ev.target.value)}
            >
              <option value="">Tous</option>
              <option value="pending">À instruire</option>
              <option value="accepted">Acceptés</option>
              <option value="rejected">Rejetés</option>
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

      <div className="card-injs p-3 mb-4">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
          <h6 className="fw-bold mb-0">Campagnes ({counts.campaigns})</h6>
          {counts.openCampaigns > 0 && (
            <span className="badge-injs">{counts.openCampaigns} ouverte(s)</span>
          )}
        </div>
        {allCampaigns.length === 0 ? (
          <div className="admissions-empty text-center py-4">
            <FiFolder className="admissions-empty-icon mb-2" aria-hidden />
            <p className="fw-semibold mb-1">Aucune campagne</p>
            <p className="small text-muted mb-0">
              Créez une campagne via l&apos;API ou l&apos;administration serveur pour ouvrir les préinscriptions.
            </p>
          </div>
        ) : (
          <div className="row g-2">
            {allCampaigns.map((c) => (
              <div key={c.id} className="col-md-6 col-xl-4">
                <button
                  type="button"
                  className={`admissions-campaign-card w-100 text-start ${campaignFilter === String(c.id) ? 'is-active' : ''}`}
                  onClick={() => setCampaignAndReset(campaignFilter === String(c.id) ? '' : String(c.id))}
                >
                  <div className="d-flex justify-content-between align-items-start gap-2">
                    <div className="min-w-0">
                      <div className="fw-semibold text-truncate">{c.name || c.title}</div>
                      <div className="small text-muted text-truncate">
                        {c.program_name || c.program || 'Programme —'}
                      </div>
                    </div>
                    <span className={`grade-badge ${isOpenCampaign(c) ? 'grade-valid' : 'grade-pending'}`}>
                      {isOpenCampaign(c) ? 'Ouverte' : 'Fermée'}
                    </span>
                  </div>
                </button>
              </div>
            ))}
          </div>
        )}
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
                    <th>Candidat</th>
                    <th>Email</th>
                    <th>Filière</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          <span className="user-avatar">{initials(p)}</span>
                          <span className="fw-semibold">{candidateName(p)}</span>
                        </div>
                      </td>
                      <td className="small">{candidateEmail(p)}</td>
                      <td className="small">{candidateProgram(p)}</td>
                      <td><StatusBadge statut={p.status || '—'} /></td>
                    </tr>
                  ))}
                  {!pageItems.length && (
                    <tr>
                      <td colSpan={4} className="text-center py-5">
                        <div className="admissions-empty">
                          <FiInbox className="admissions-empty-icon mb-2" aria-hidden />
                          <div className="fw-semibold">Aucun dossier</div>
                          <div className="small text-muted mt-1">
                            Les préinscriptions apparaîtront ici dès qu&apos;une campagne sera ouverte.
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {pageItems.map((p) => (
                  <div key={p.id} className="col-md-6 col-xl-4">
                    <div className="border rounded-3 p-3 h-100">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <span className="user-avatar">{initials(p)}</span>
                        <StatusBadge statut={p.status || '—'} />
                      </div>
                      <h6 className="fw-bold mb-1">{candidateName(p)}</h6>
                      <p className="small text-muted mb-2">{candidateEmail(p)}</p>
                      <p className="small mb-0">
                        <FiUsers className="me-1" style={{ verticalAlign: '-2px' }} />
                        {candidateProgram(p)}
                      </p>
                    </div>
                  </div>
                ))}
                {!pageItems.length && (
                  <div className="col-12 text-center py-5">
                    <div className="admissions-empty">
                      <FiClock className="admissions-empty-icon mb-2" aria-hidden />
                      <div className="fw-semibold">Aucun dossier</div>
                      <div className="small text-muted mt-1">
                        Les préinscriptions apparaîtront ici dès qu&apos;une campagne sera ouverte.
                      </div>
                    </div>
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
    </>
  )
}
