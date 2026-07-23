import { useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import PaginationBar from '../../components/common/PaginationBar'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchEquipment,
  createEquipment,
  deleteEquipment,
  syncEquipmentRoomTags,
  fetchRooms,
} from '../../api/faculty'
import { fetchInstitutions } from '../../api/academics'
import { translateStatus } from '../../utils/labels'

const EMPTY = {
  code: '',
  name: '',
  category: '',
  quantity: 1,
  room: '',
  status: 'available',
  capability_tags: '',
  institution: '',
}

export default function AdminEquipment() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const { data, loading, error, reload } = useFetch(
    () => fetchEquipment({ page, page_size: 20, search: search || undefined }),
    [page, search],
  )
  const { data: roomsData } = useFetch(() => fetchRooms({ page_size: 200 }), [])
  const { data: institutions } = useFetch(() => fetchInstitutions(), [])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const rows = data?.results || []
  const rooms = roomsData?.results || []
  const defaultInst = institutions?.[0]?.id || ''

  const submit = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await createEquipment({
        code: form.code.trim().toUpperCase(),
        name: form.name,
        category: form.category,
        quantity: Number(form.quantity) || 1,
        room: form.room || null,
        status: form.status,
        institution: form.institution || defaultInst,
        capability_tags: form.capability_tags
          ? form.capability_tags.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
        is_active: true,
      })
      showToast('Équipement enregistré', 'success')
      setShowForm(false)
      setForm({ ...EMPTY, institution: defaultInst })
      reload()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const syncTags = async () => {
    try {
      const res = await syncEquipmentRoomTags()
      showToast(`${res.rooms_updated} salle(s) mises à jour (tags)`, 'success')
    } catch (err) {
      showToast(err.message || 'Sync impossible', 'danger')
    }
  }

  return (
    <>
      <PageHeader
        title="Suivi des équipements"
        subtitle="Inventaire campus — tags pour auto-affectation des salles"
        action={
          <div className="widget-actions">
            <button type="button" className="btn btn-outline-secondary" onClick={syncTags}>Sync tags → salles</button>
            <button
              type="button"
              className="btn btn-injs-primary"
              onClick={() => { setForm({ ...EMPTY, institution: defaultInst }); setShowForm(true) }}
            >
              + Équipement
            </button>
          </div>
        }
      />

      <div className="card-injs p-3 mb-3">
        <input
          className="form-control"
          placeholder="Rechercher code, nom, catégorie…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
      </div>

      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card-injs">
        <div className="table-responsive">
          <table className="table mb-0 align-middle">
            <thead>
              <tr>
                <th>Code</th>
                <th>Nom</th>
                <th>Catégorie</th>
                <th>Salle</th>
                <th>Qté</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id}>
                  <td><code>{e.code}</code></td>
                  <td>
                    {e.name}
                    {!!e.capability_tags?.length && (
                      <div className="small text-muted">{e.capability_tags.join(', ')}</div>
                    )}
                  </td>
                  <td>{e.category || '—'}</td>
                  <td>{e.room_code || '—'}</td>
                  <td>{e.quantity}</td>
                  <td><span className="badge bg-secondary">{translateStatus(e.status)}</span></td>
                  <td className="text-end">
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-danger"
                      onClick={async () => {
                        await deleteEquipment(e.id)
                        showToast('Équipement archivé', 'success')
                        reload()
                      }}
                    >
                      Archiver
                    </button>
                  </td>
                </tr>
              ))}
              {!rows.length && !loading && (
                <tr><td colSpan={7} className="text-center text-muted py-4">Aucun équipement</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationBar page={page} pageSize={20} total={data?.count || 0} onPageChange={setPage} />
      </div>

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Nouvel équipement"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="eq-form" className="btn btn-injs-primary" disabled={saving}>{saving ? '…' : 'Ajouter'}</button>
          </>
        }
      >
        <form id="eq-form" onSubmit={submit} className="row g-3">
          <div className="col-md-4">
            <label className="form-label">Code *</label>
            <input className="form-control" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          </div>
          <div className="col-md-8">
            <label className="form-label">Nom *</label>
            <input className="form-control" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label">Catégorie</label>
            <input className="form-control" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
          </div>
          <div className="col-md-3">
            <label className="form-label">Quantité</label>
            <input type="number" min={1} className="form-control" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
          </div>
          <div className="col-md-3">
            <label className="form-label">Statut</label>
            <select className="form-select" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="available">Disponible</option>
              <option value="in_use">En service</option>
              <option value="maintenance">Maintenance</option>
            </select>
          </div>
          <div className="col-12">
            <label className="form-label">Salle</label>
            <select className="form-select" value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })}>
              <option value="">— Non affecté —</option>
              {rooms.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
            </select>
          </div>
          <div className="col-12">
            <label className="form-label">Tags capacité (auto-affectation)</label>
            <input className="form-control" placeholder="projecteur, wifi, ergomètre" value={form.capability_tags} onChange={(e) => setForm({ ...form, capability_tags: e.target.value })} />
          </div>
        </form>
      </Modal>
    </>
  )
}
