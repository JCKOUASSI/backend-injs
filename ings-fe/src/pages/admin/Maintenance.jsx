import { useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import PaginationBar from '../../components/common/PaginationBar'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchMaintenanceTickets,
  createMaintenanceTicket,
  updateMaintenanceTicket,
  fetchRooms,
} from '../../api/faculty'
import { translateStatus } from '../../utils/labels'

const EMPTY = { room: '', title: '', description: '', priority: 'medium' }

export default function AdminMaintenance() {
  const { showToast } = useToast()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useFetch(
    () => fetchMaintenanceTickets({ status: status || undefined, page, page_size: 15 }),
    [status, page],
  )
  const { data: roomsData } = useFetch(() => fetchRooms({ page_size: 200 }), [])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const rows = data?.results || []
  const rooms = roomsData?.results || []

  const submit = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await createMaintenanceTicket(form)
      showToast('Ticket ouvert — salle passée en maintenance', 'success')
      setShowForm(false)
      setForm(EMPTY)
      reload()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const setTicketStatus = async (id, next) => {
    try {
      await updateMaintenanceTicket(id, { status: next })
      showToast(`Ticket → ${next}`, 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  return (
    <>
      <PageHeader
        title="Maintenance des bâtiments"
        subtitle="Tickets liés aux salles — synchronisation automatique du statut"
        action={<button type="button" className="btn btn-injs-primary" onClick={() => setShowForm(true)}>+ Ticket</button>}
      />

      <div className="card-injs p-3 mb-3">
        <select className="form-select w-auto" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">Tous</option>
          <option value="open">Ouverts</option>
          <option value="in_progress">En cours</option>
          <option value="resolved">Résolus</option>
          <option value="closed">Fermés</option>
        </select>
      </div>

      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card-injs">
        <div className="table-responsive">
          <table className="table mb-0 align-middle">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Salle / bâtiment</th>
                <th>Priorité</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div className="fw-semibold">{t.title}</div>
                    <small className="text-muted">{t.reported_by_name || '—'}</small>
                  </td>
                  <td>
                    <code>{t.room_code}</code> {t.room_name}
                    <div className="small text-muted">{t.building || '—'}</div>
                  </td>
                  <td>{t.priority_display || t.priority}</td>
                  <td><span className="badge bg-secondary">{translateStatus(t.status)}</span></td>
                  <td className="text-end text-nowrap">
                    {t.status === 'open' && (
                      <button type="button" className="btn btn-sm btn-outline-primary me-1" onClick={() => setTicketStatus(t.id, 'in_progress')}>Prendre</button>
                    )}
                    {['open', 'in_progress'].includes(t.status) && (
                      <button type="button" className="btn btn-sm btn-success" onClick={() => setTicketStatus(t.id, 'resolved')}>Résoudre</button>
                    )}
                    {t.status === 'resolved' && (
                      <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setTicketStatus(t.id, 'closed')}>Clôturer</button>
                    )}
                  </td>
                </tr>
              ))}
              {!rows.length && !loading && (
                <tr><td colSpan={5} className="text-center text-muted py-4">Aucun ticket</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationBar page={page} pageSize={15} total={data?.count || 0} onPageChange={setPage} />
      </div>

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Nouveau ticket maintenance"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="maint-form" className="btn btn-injs-primary" disabled={saving}>{saving ? '…' : 'Ouvrir'}</button>
          </>
        }
      >
        <form id="maint-form" onSubmit={submit} className="row g-3">
          <div className="col-12">
            <label className="form-label">Salle *</label>
            <select className="form-select" required value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })}>
              <option value="">—</option>
              {rooms.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
            </select>
          </div>
          <div className="col-md-8">
            <label className="form-label">Titre *</label>
            <input className="form-control" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label">Priorité</label>
            <select className="form-select" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              <option value="low">Basse</option>
              <option value="medium">Moyenne</option>
              <option value="high">Haute</option>
              <option value="critical">Critique</option>
            </select>
          </div>
          <div className="col-12">
            <label className="form-label">Description</label>
            <textarea className="form-control" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
        </form>
      </Modal>
    </>
  )
}
