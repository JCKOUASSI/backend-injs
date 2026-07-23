import { useMemo, useState } from 'react'
import { FiExternalLink, FiMapPin } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import { useFetch } from '../../hooks/useFetch'
import { fetchRoomsGeo, fetchRoomsMeta } from '../../api/faculty'

/** Carte campus relative (lat/lng) sans dépendance carto externe. */
export default function AdminCampusMap() {
  const { data, loading, error } = useFetch(() => fetchRoomsGeo(), [])
  const { data: meta } = useFetch(() => fetchRoomsMeta(), [])
  const [building, setBuilding] = useState('')
  const [selected, setSelected] = useState(null)

  const rooms = useMemo(() => {
    const list = data?.results || []
    if (!building) return list
    return list.filter((r) => r.building === building)
  }, [data, building])

  const bounds = data?.bounds
  const markers = useMemo(() => {
    if (!rooms.length || !bounds?.lat_min) return []
    const latSpan = Math.max(Number(bounds.lat_max) - Number(bounds.lat_min), 0.0008)
    const lngSpan = Math.max(Number(bounds.lng_max) - Number(bounds.lng_min), 0.0008)
    return rooms.map((r) => {
      const lat = Number(r.latitude)
      const lng = Number(r.longitude)
      const x = ((lng - Number(bounds.lng_min)) / lngSpan) * 100
      const y = (1 - (lat - Number(bounds.lat_min)) / latSpan) * 100
      return {
        ...r,
        x: Math.min(96, Math.max(4, x)),
        y: Math.min(96, Math.max(4, y)),
      }
    })
  }, [rooms, bounds])

  return (
    <>
      <PageHeader
        title="Carte du campus"
        subtitle={`${data?.count || 0} salle(s) géolocalisée(s) — INJS Abidjan`}
      />

      <div className="card-injs p-3 mb-3">
        <select className="form-select w-auto" value={building} onChange={(e) => setBuilding(e.target.value)}>
          <option value="">Toutes les zones</option>
          {(meta?.buildings || []).map((b) => (
            <option key={b.value} value={b.value}>{b.label}</option>
          ))}
        </select>
      </div>

      {loading && <div className="text-center py-4"><div className="spinner-border text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row g-3">
        <div className="col-lg-8">
          <div className="card-injs campus-map-canvas">
            <div className="campus-map-grid">
              {markers.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className={`campus-map-pin ${selected?.id === m.id ? 'is-active' : ''}`}
                  style={{ left: `${m.x}%`, top: `${m.y}%` }}
                  title={`${m.code} — ${m.name}`}
                  onClick={() => setSelected(m)}
                >
                  <FiMapPin size={18} />
                </button>
              ))}
              {!markers.length && !loading && (
                <div className="campus-map-empty text-muted">Aucune coordonnée GPS pour le filtre actuel</div>
              )}
            </div>
            <div className="campus-map-legend small text-muted px-3 py-2 border-top">
              Projection relative des latitudes / longitudes renseignées sur les salles.
            </div>
          </div>
        </div>
        <div className="col-lg-4">
          <div className="card-injs p-3 h-100">
            <h6 className="fw-bold mb-3">Détail</h6>
            {!selected && <p className="text-muted small">Cliquez un point sur la carte.</p>}
            {selected && (
              <>
                <code>{selected.code}</code>
                <h5 className="fw-bold mt-1">{selected.name}</h5>
                <dl className="detail-view mb-3">
                  <div className="detail-row"><dt>Zone</dt><dd>{selected.building_display || selected.building}</dd></div>
                  <div className="detail-row"><dt>Type</dt><dd>{selected.room_type_display || selected.room_type}</dd></div>
                  <div className="detail-row"><dt>Capacité</dt><dd>{selected.capacity}</dd></div>
                  <div className="detail-row"><dt>GPS</dt><dd>{selected.latitude}, {selected.longitude}</dd></div>
                </dl>
                <a
                  className="btn btn-sm btn-outline-primary"
                  href={`https://www.openstreetmap.org/?mlat=${selected.latitude}&mlon=${selected.longitude}#map=18/${selected.latitude}/${selected.longitude}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <FiExternalLink className="me-1" /> Ouvrir OpenStreetMap
                </a>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
