import { useEffect, useMemo, useState } from 'react'
import { FiEdit2, FiMapPin } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import ExportButtons from '../../components/common/ExportButtons'
import IconActionButtons from '../../components/common/IconActionButtons'
import PaginationBar from '../../components/common/PaginationBar'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchRooms,
  fetchRoom,
  fetchRoomsMeta,
  createRoom,
  updateRoom,
  deleteRoom,
} from '../../api/faculty'
import { fetchInstitutions } from '../../api/academics'
import { INSTITUTION } from '../../data/mockData'
import { translateStatus } from '../../utils/labels'

const EMPTY = {
  code: '',
  name: '',
  capacity: 30,
  building: '',
  room_type: 'classroom',
  floor: '',
  equipment: '',
  status: 'available',
  latitude: '',
  longitude: '',
  notes: '',
  institution: '',
}

function statusBadgeClass(status) {
  switch (status) {
    case 'available': return 'bg-success'
    case 'maintenance': return 'bg-warning text-dark'
    case 'reserved': return 'bg-info text-dark'
    case 'inactive': return 'bg-secondary'
    default: return 'bg-secondary'
  }
}

export default function AdminRooms() {
  const { showToast } = useToast()
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [building, setBuilding] = useState('')
  const [roomType, setRoomType] = useState('')
  const [status, setStatus] = useState('')
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
    building: building || undefined,
    room_type: roomType || undefined,
    status: status || undefined,
    page,
    page_size: pageSize,
  }), [search, building, roomType, status, page, pageSize])

  const { data, loading, error, reload } = useFetch(
    () => fetchRooms(filters),
    [filters.search, filters.building, filters.room_type, filters.status, filters.page, filters.page_size],
  )
  const { data: meta } = useFetch(() => fetchRoomsMeta(), [])
  const { data: institutions } = useFetch(() => fetchInstitutions(), [])

  const rooms = data?.results || []
  const total = data?.count ?? 0
  const defaultInstitution = institutions?.[0]?.id || ''

  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const setFilterAndResetPage = (setter) => (value) => {
    setter(value)
    setPage(1)
  }

  const openCreate = () => {
    setForm({ ...EMPTY, institution: defaultInstitution })
    setShowForm(true)
  }

  const openDetail = async (r) => {
    setSaving(true)
    try {
      const detail = await fetchRoom(r.id)
      setSelected(detail)
      setShowDetail(true)
    } catch (err) {
      showToast(err.message || 'Impossible de charger la fiche', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const fillFormFromRoom = (detail) => ({
    code: detail.code || '',
    name: detail.name || '',
    capacity: detail.capacity ?? 30,
    building: detail.building || '',
    room_type: detail.roomType || 'classroom',
    floor: detail.floor || '',
    equipment: (detail.equipment || []).join(', '),
    status: detail.status || 'available',
    latitude: detail.latitude ?? '',
    longitude: detail.longitude ?? '',
    notes: detail.notes || '',
    institution: detail.institutionId || defaultInstitution,
  })

  const openEdit = async (r) => {
    setSaving(true)
    try {
      const detail = await fetchRoom(r.id)
      setSelected(detail)
      setForm(fillFormFromRoom(detail))
      setShowEdit(true)
    } catch (err) {
      showToast(err.message || 'Impossible de charger la fiche', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const openDelete = (r) => {
    setSelected(r)
    setShowDelete(true)
  }

  const toPayload = () => {
    const equipment = String(form.equipment || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    return {
      code: form.code.trim().toUpperCase(),
      name: form.name.trim(),
      capacity: Number(form.capacity) || 30,
      building: form.building || '',
      room_type: form.room_type,
      floor: form.floor || '',
      equipment,
      status: form.status,
      latitude: form.latitude === '' ? null : form.latitude,
      longitude: form.longitude === '' ? null : form.longitude,
      notes: form.notes || '',
      institution: form.institution,
      is_active: true,
    }
  }

  const handleCreate = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await createRoom(toPayload())
      showToast(`Salle ${form.code} créée`, 'success')
      setShowForm(false)
      setForm(EMPTY)
      reload()
    } catch (err) {
      showToast(err.message || 'Création impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await updateRoom(selected.id, toPayload())
      showToast('Salle mise à jour', 'success')
      setShowEdit(false)
      setSelected(null)
      reload()
    } catch (err) {
      showToast(err.message || 'Modification impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setSaving(true)
    try {
      await deleteRoom(selected.id)
      showToast('Salle archivée', 'success')
      setShowDelete(false)
      setSelected(null)
      reload()
    } catch (err) {
      showToast(err.message || 'Suppression impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !data) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-4">Erreur de chargement : {error}</div>
  }

  const buildingOptions = meta?.buildings || []
  const typeOptions = meta?.room_types || []
  const statusOptions = meta?.statuses || []
  const byBuilding = meta?.counts?.by_building || {}

  return (
    <>
      <PageHeader
        title="Gestion des salles"
        subtitle={`${INSTITUTION.shortName || 'INJS'} — ${meta?.counts?.total ?? total} espace(s) pédagogique(s)`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Salles campus INJS"
              filename="salles_injs"
              headers={['Code', 'Nom', 'Type', 'Bâtiment', 'Capacité', 'Statut', 'Étage']}
              rows={rooms.map((r) => [
                r.code, r.name, r.roomTypeLabel, r.buildingLabel, r.capacity, r.statusLabel, r.floor || '—',
              ])}
              resourcePath="/faculty/rooms"
            />
            <button type="button" className="btn btn-injs-primary" onClick={openCreate}>+ Ajouter</button>
          </div>
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{meta?.counts?.total ?? total}</div>
            <div className="small text-muted">Espaces actifs</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{Object.keys(byBuilding).length || '—'}</div>
            <div className="small text-muted">Bâtiments / zones</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{Object.keys(meta?.counts?.by_type || {}).length || '—'}</div>
            <div className="small text-muted">Types d'espaces</div>
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
          <span className="small text-muted me-1">Zones :</span>
          <button
            type="button"
            className={`btn btn-sm ${!building ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilterAndResetPage(setBuilding)('')}
          >
            Toutes ({meta?.counts?.total ?? '—'})
          </button>
          {buildingOptions
            .filter((b) => byBuilding[b.value])
            .map((b) => (
              <button
                key={b.value}
                type="button"
                className={`btn btn-sm ${building === b.value ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setFilterAndResetPage(setBuilding)(b.value)}
                title={b.label}
              >
                {b.value} <span className="opacity-75">({byBuilding[b.value]})</span>
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
              placeholder="Code, nom…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Bâtiment / zone</label>
            <select
              className="form-select"
              value={building}
              onChange={(ev) => setFilterAndResetPage(setBuilding)(ev.target.value)}
            >
              <option value="">Tous</option>
              {buildingOptions.map((b) => (
                <option key={b.value} value={b.value}>{b.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Type</label>
            <select
              className="form-select"
              value={roomType}
              onChange={(ev) => setFilterAndResetPage(setRoomType)(ev.target.value)}
            >
              <option value="">Tous</option>
              {typeOptions.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
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
          <div className="col-md-2">
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
                    <th>Code</th>
                    <th>Nom</th>
                    <th>Type</th>
                    <th>Bâtiment</th>
                    <th>Capacité</th>
                    <th>Statut</th>
                    <th>EDT</th>
                    <th className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rooms.map((r) => (
                    <tr key={r.id}>
                      <td><code className="small">{r.code}</code></td>
                      <td>
                        <div className="fw-semibold">{r.name}</div>
                        {r.floor && <small className="text-muted">Étage {r.floor}</small>}
                      </td>
                      <td><span className="badge-injs">{r.roomTypeLabel}</span></td>
                      <td className="small">{r.buildingLabel}</td>
                      <td>{r.capacity}</td>
                      <td>
                        <span className={`badge ${statusBadgeClass(r.status)}`}>
                          {translateStatus(r.status) !== '—' ? translateStatus(r.status) : r.statusLabel}
                        </span>
                      </td>
                      <td>{r.schedulesCount}</td>
                      <td className="text-end">
                        <IconActionButtons
                          actions={[
                            { type: 'view', onClick: () => openDetail(r) },
                            { type: 'edit', onClick: () => openEdit(r) },
                            { type: 'delete', onClick: () => openDelete(r) },
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                  {!rooms.length && (
                    <tr>
                      <td colSpan={8} className="text-center text-muted py-4">Aucun espace trouvé</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
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
                      <div className="d-flex justify-content-between small mb-2">
                        <span>{r.capacity} places</span>
                        {r.floor && <span>Étage {r.floor}</span>}
                      </div>
                      <IconActionButtons
                        actions={[
                          { type: 'view', onClick: () => openDetail(r) },
                          { type: 'edit', onClick: () => openEdit(r) },
                          { type: 'delete', onClick: () => openDelete(r) },
                        ]}
                      />
                    </div>
                  </div>
                ))}
                {!rooms.length && (
                  <div className="col-12 text-center text-muted py-4">Aucun espace trouvé</div>
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

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Ajouter un espace pédagogique"
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="room-create-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Création...' : 'Ajouter'}
            </button>
          </>
        }
      >
        <form id="room-create-form" onSubmit={handleCreate}>
          <RoomFormFields
            form={form}
            setForm={setForm}
            institutions={institutions || []}
            buildings={buildingOptions}
            types={typeOptions}
            statuses={statusOptions}
          />
        </form>
      </Modal>

      <Modal
        show={showDetail}
        onClose={() => { setShowDetail(false); setSelected(null) }}
        title={selected ? `${selected.code} — ${selected.name}` : 'Fiche salle'}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowDetail(false)}>Fermer</button>
            <button
              type="button"
              className="btn btn-outline-primary btn-icon-action"
              title="Modifier"
              aria-label="Modifier"
              onClick={() => {
                setShowDetail(false)
                if (selected) openEdit(selected)
              }}
            >
              <FiEdit2 size={16} />
            </button>
          </>
        }
      >
        {selected && (
          <dl className="detail-view mb-0">
            <div className="detail-row"><dt>Code</dt><dd><code>{selected.code}</code></dd></div>
            <div className="detail-row"><dt>Nom</dt><dd>{selected.name}</dd></div>
            <div className="detail-row"><dt>Type</dt><dd>{selected.roomTypeLabel}</dd></div>
            <div className="detail-row"><dt>Bâtiment</dt><dd>{selected.buildingLabel}</dd></div>
            <div className="detail-row"><dt>Étage</dt><dd>{selected.floor || '—'}</dd></div>
            <div className="detail-row"><dt>Capacité</dt><dd>{selected.capacity} places</dd></div>
            <div className="detail-row"><dt>Statut</dt><dd>{selected.statusLabel}</dd></div>
            <div className="detail-row"><dt>Équipements</dt><dd>{selected.equipment?.length ? selected.equipment.join(', ') : '—'}</dd></div>
            <div className="detail-row">
              <dt>Géolocalisation</dt>
              <dd>
                {selected.latitude && selected.longitude ? (
                  <span className="d-inline-flex align-items-center gap-1">
                    <FiMapPin size={14} /> {selected.latitude}, {selected.longitude}
                  </span>
                ) : '—'}
              </dd>
            </div>
            <div className="detail-row"><dt>Créneaux EDT</dt><dd>{selected.schedulesCount}</dd></div>
            <div className="detail-row"><dt>Notes</dt><dd>{selected.notes || '—'}</dd></div>
          </dl>
        )}
      </Modal>

      <Modal
        show={showEdit}
        onClose={() => { setShowEdit(false); setSelected(null) }}
        title={selected ? `Modifier — ${selected.code}` : 'Modifier la salle'}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowEdit(false)}>Annuler</button>
            <button type="submit" form="room-edit-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="room-edit-form" onSubmit={handleEdit}>
          <RoomFormFields
            form={form}
            setForm={setForm}
            institutions={institutions || []}
            buildings={buildingOptions}
            types={typeOptions}
            statuses={statusOptions}
          />
        </form>
      </Modal>

      <Modal
        show={showDelete}
        onClose={() => setShowDelete(false)}
        title="Archiver la salle"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowDelete(false)}>Annuler</button>
            <button type="button" className="btn btn-danger" disabled={saving} onClick={handleDelete}>
              {saving ? 'Archivage...' : 'Confirmer'}
            </button>
          </>
        }
      >
        <p>
          Archiver l’espace{' '}
          <strong>{selected ? `${selected.code} — ${selected.name}` : ''}</strong> ?
        </p>
        <p className="text-danger small mb-0">
          Soft delete : la salle disparaîtra des listes actives mais restera liée aux historiques EDT.
        </p>
      </Modal>
    </>
  )
}

function RoomFormFields({ form, setForm, institutions, buildings, types, statuses }) {
  return (
    <div className="row g-3">
      <div className="col-md-4">
        <label className="form-label">Code *</label>
        <input
          className="form-control"
          required
          placeholder="ex. SC-151"
          value={form.code}
          onChange={(ev) => setForm({ ...form, code: ev.target.value })}
        />
      </div>
      <div className="col-md-8">
        <label className="form-label">Nom *</label>
        <input
          className="form-control"
          required
          value={form.name}
          onChange={(ev) => setForm({ ...form, name: ev.target.value })}
        />
      </div>
      <div className="col-md-4">
        <label className="form-label">Type *</label>
        <select
          className="form-select"
          required
          value={form.room_type}
          onChange={(ev) => setForm({ ...form, room_type: ev.target.value })}
        >
          {types.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>
      <div className="col-md-4">
        <label className="form-label">Bâtiment / zone</label>
        <select
          className="form-select"
          value={form.building}
          onChange={(ev) => setForm({ ...form, building: ev.target.value })}
        >
          <option value="">—</option>
          {buildings.map((b) => (
            <option key={b.value} value={b.value}>{b.label}</option>
          ))}
        </select>
      </div>
      <div className="col-md-2">
        <label className="form-label">Étage</label>
        <input
          className="form-control"
          value={form.floor}
          onChange={(ev) => setForm({ ...form, floor: ev.target.value })}
        />
      </div>
      <div className="col-md-2">
        <label className="form-label">Capacité *</label>
        <input
          type="number"
          min={1}
          className="form-control"
          required
          value={form.capacity}
          onChange={(ev) => setForm({ ...form, capacity: ev.target.value })}
        />
      </div>
      <div className="col-md-4">
        <label className="form-label">Statut</label>
        <select
          className="form-select"
          value={form.status}
          onChange={(ev) => setForm({ ...form, status: ev.target.value })}
        >
          {statuses.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>
      <div className="col-md-8">
        <label className="form-label">Institution *</label>
        <select
          className="form-select"
          required
          value={form.institution}
          onChange={(ev) => setForm({ ...form, institution: ev.target.value })}
        >
          <option value="">—</option>
          {institutions.map((i) => (
            <option key={i.id} value={i.id}>{i.acronym || i.code} — {i.name}</option>
          ))}
        </select>
      </div>
      <div className="col-12">
        <label className="form-label">Équipements (séparés par des virgules)</label>
        <input
          className="form-control"
          placeholder="projecteur, wifi, climatisation"
          value={form.equipment}
          onChange={(ev) => setForm({ ...form, equipment: ev.target.value })}
        />
      </div>
      <div className="col-md-6">
        <label className="form-label">Latitude</label>
        <input
          className="form-control"
          value={form.latitude}
          onChange={(ev) => setForm({ ...form, latitude: ev.target.value })}
        />
      </div>
      <div className="col-md-6">
        <label className="form-label">Longitude</label>
        <input
          className="form-control"
          value={form.longitude}
          onChange={(ev) => setForm({ ...form, longitude: ev.target.value })}
        />
      </div>
      <div className="col-12">
        <label className="form-label">Notes</label>
        <textarea
          className="form-control"
          rows={2}
          value={form.notes}
          onChange={(ev) => setForm({ ...form, notes: ev.target.value })}
        />
      </div>
    </div>
  )
}
