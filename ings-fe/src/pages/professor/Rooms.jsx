import { useEffect, useMemo, useState } from 'react'
import { FiMapPin } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import PaginationBar from '../../components/common/PaginationBar'
import { useFetch } from '../../hooks/useFetch'
import { fetchRooms, fetchRoomsMeta } from '../../api/faculty'
import { INSTITUTION } from '../../data/mockData'
import { translateStatus } from '../../utils/labels'

function statusBadgeClass(status) {
  switch (status) {
    case 'available': return 'bg-success'
    case 'maintenance': return 'bg-warning text-dark'
    case 'reserved': return 'bg-info text-dark'
    default: return 'bg-secondary'
  }
}

/** Consultation campus (lecture seule) pour les enseignants. */
export default function ProfessorRooms() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [building, setBuilding] = useState('')
  const [roomType, setRoomType] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(12)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 350)
    return () => clearTimeout(t)
  }, [searchInput])

  const filters = useMemo(() => ({
    search: search || undefined,
    building: building || undefined,
    room_type: roomType || undefined,
    status: 'available',
    page,
    page_size: pageSize,
  }), [search, building, roomType, page, pageSize])

  const { data, loading, error } = useFetch(
    () => fetchRooms(filters),
    [filters.search, filters.building, filters.room_type, filters.page, filters.page_size],
  )
  const { data: meta } = useFetch(() => fetchRoomsMeta(), [])

  const rooms = data?.results || []
  const total = data?.count ?? 0

  if (loading && !data) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-4">Erreur : {error}</div>
  }

  return (
    <>
      <PageHeader
        title="Campus & salles"
        subtitle={`${INSTITUTION.shortName} — ${total} espace(s) disponible(s)`}
      />

      <div className="card-injs p-3 mb-4">
        <div className="row g-2">
          <div className="col-md-5">
            <input
              className="form-control"
              placeholder="Rechercher (code, nom…)"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-4">
            <select
              className="form-select"
              value={building}
              onChange={(ev) => { setBuilding(ev.target.value); setPage(1) }}
            >
              <option value="">Tous les bâtiments</option>
              {(meta?.buildings || []).map((b) => (
                <option key={b.value} value={b.value}>{b.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-3">
            <select
              className="form-select"
              value={roomType}
              onChange={(ev) => { setRoomType(ev.target.value); setPage(1) }}
            >
              <option value="">Tous les types</option>
              {(meta?.room_types || []).map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card-injs">
        <div className="p-3">
          <div className="row g-3">
            {rooms.map((r) => (
              <div key={r.id} className="col-md-6 col-xl-4">
                <div className="border rounded-3 p-3 h-100">
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <code className="small">{r.code}</code>
                    <span className={`badge ${statusBadgeClass(r.status)}`}>
                      {translateStatus(r.status)}
                    </span>
                  </div>
                  <h6 className="fw-bold mb-1">{r.name}</h6>
                  <p className="small text-muted mb-2">{r.buildingLabel} · {r.roomTypeLabel}</p>
                  <div className="d-flex justify-content-between small">
                    <span>{r.capacity} places</span>
                    {r.floor && <span>Étage {r.floor}</span>}
                  </div>
                  {r.latitude && r.longitude && (
                    <div className="small text-muted mt-2 d-flex align-items-center gap-1">
                      <FiMapPin size={12} /> {r.latitude}, {r.longitude}
                    </div>
                  )}
                  {r.equipment?.length > 0 && (
                    <div className="mt-2">
                      {r.equipment.slice(0, 4).map((eq) => (
                        <span key={eq} className="badge bg-light text-dark me-1 mb-1">{eq}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {!rooms.length && (
              <div className="col-12">
                <div className="text-muted text-center py-4">Aucun espace trouvé</div>
              </div>
            )}
          </div>
        </div>
        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          disabled={loading}
          pageSizeOptions={[12, 24, 48]}
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
