import { useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import PaginationBar from '../../components/common/PaginationBar'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchReservations,
  createReservation,
  approveReservation,
  rejectReservation,
  cancelReservation,
  fetchRooms,
} from '../../api/faculty'
import { translateStatus } from '../../utils/labels'

const EMPTY = {
  room: '',
  title: '',
  purpose: '',
  start_datetime: '',
  end_datetime: '',
  attendees_count: 20,
  required_equipment: '',
}

export default function AdminReservations() {
  const { showToast } = useToast()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useFetch(
    () => fetchReservations({ status: status || undefined, page, page_size: 15 }),
    [status, page],
  )
  const { data: roomsData } = useFetch(() => fetchRooms({ page_size: 200, status: 'available' }), [])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const rows = data?.results || []
  const rooms = roomsData?.results || []

  const submit = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await createReservation({
        room: form.room,
        title: form.title,
        purpose: form.purpose,
        start_datetime: form.start_datetime,
        end_datetime: form.end_datetime,
        attendees_count: Number(form.attendees_count) || 0,
        required_equipment: form.required_equipment
          ? form.required_equipment.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
        status: 'pending',
      })
      showToast('Réservation enregistrée (en attente)', 'success')
      setShowForm(false)
      setForm(EMPTY)
      reload()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const act = async (fn, id, okMsg) => {
    try {
      await fn(id)
      showToast(okMsg, 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Action impossible', 'danger')
    }
  }

  return (
    <>
      <PageHeader
        title="Réservations d'infrastructures"
        subtitle="Réservation hors EDT — validation capacité & équipements"
        action={<button type="button" className="btn btn-injs-primary" onClick={() => setShowForm(true)}>+ Réserver</button>}
      />

      <div className="card-injs p-3 mb-3">
        <select className="form-select w-auto" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">Tous les statuts</option>
          <option value="pending">En attente</option>
          <option value="approved">Approuvées</option>
          <option value="rejected">Refusées</option>
          <option value="cancelled">Annulées</option>
        </select>
      </div>

      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card-injs">
        <div className="table-responsive">
          <table className="table mb-0 align-middle">
            <thead>
              <tr>
                <th>Titre</th>
                <th>Salle</th>
                <th>Période</th>
                <th>Effectif</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <div className="fw-semibold">{r.title}</div>
                    <small className="text-muted">{r.requested_by_name || '—'}</small>
                  </td>
                  <td><code>{r.room_code}</code> {r.room_name}</td>
                  <td className="small">
                    {new Date(r.start_datetime).toLocaleString('fr-FR')}<br />
                    → {new Date(r.end_datetime).toLocaleString('fr-FR')}
                  </td>
                  <td>{r.attendees_count}</td>
                  <td><span className="badge bg-secondary">{translateStatus(r.status)}</span></td>
                  <td className="text-end text-nowrap">
                    {r.status === 'pending' && (
                      <>
                        <button type="button" className="btn btn-sm btn-success me-1" onClick={() => act(approveReservation, r.id, 'Approuvée')}>OK</button>
                        <button type="button" className="btn btn-sm btn-outline-danger me-1" onClick={() => act((id) => rejectReservation(id, 'Refus admin'), r.id, 'Refusée')}>Refuser</button>
                      </>
                    )}
                    {['pending', 'approved'].includes(r.status) && (
                      <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => act(cancelReservation, r.id, 'Annulée')}>Annuler</button>
                    )}
                  </td>
                </tr>
              ))}
              {!rows.length && !loading && (
                <tr><td colSpan={6} className="text-center text-muted py-4">Aucune réservation</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationBar page={page} pageSize={15} total={data?.count || 0} onPageChange={setPage} />
      </div>

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Nouvelle réservation"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="res-form" className="btn btn-injs-primary" disabled={saving}>{saving ? '…' : 'Demander'}</button>
          </>
        }
      >
        <form id="res-form" onSubmit={submit} className="row g-3">
          <div className="col-12">
            <label className="form-label">Salle *</label>
            <select className="form-select" required value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })}>
              <option value="">—</option>
              {rooms.map((r) => (
                <option key={r.id} value={r.id}>{r.code} — {r.name} ({r.capacity} pl.)</option>
              ))}
            </select>
          </div>
          <div className="col-12">
            <label className="form-label">Titre *</label>
            <input className="form-control" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label">Début *</label>
            <input type="datetime-local" className="form-control" required value={form.start_datetime} onChange={(e) => setForm({ ...form, start_datetime: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label">Fin *</label>
            <input type="datetime-local" className="form-control" required value={form.end_datetime} onChange={(e) => setForm({ ...form, end_datetime: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label">Effectif</label>
            <input type="number" min={0} className="form-control" value={form.attendees_count} onChange={(e) => setForm({ ...form, attendees_count: e.target.value })} />
          </div>
          <div className="col-md-8">
            <label className="form-label">Équipements requis</label>
            <input className="form-control" placeholder="projecteur, sono" value={form.required_equipment} onChange={(e) => setForm({ ...form, required_equipment: e.target.value })} />
          </div>
          <div className="col-12">
            <label className="form-label">Objet</label>
            <textarea className="form-control" rows={2} value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
          </div>
        </form>
      </Modal>
    </>
  )
}
