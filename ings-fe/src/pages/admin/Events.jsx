import { useState } from 'react'
import { FiEdit2 } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import IconActionButtons from '../../components/common/IconActionButtons'
import { useToast } from '../../context/ToastContext'
import { mockSubmit } from '../../utils/mockSubmit'
import { EVENEMENTS } from '../../data/mockData'

const EMPTY = { date: '', titre: '', type: 'Institutionnel', description: '' }

function withIds(list) {
  return list.map((ev, i) => ({
    ...ev,
    id: ev.id || `evt-${i + 1}`,
    description: ev.description || '',
  }))
}

function formatDay(dateStr = '') {
  if (dateStr.includes('-')) return dateStr.slice(8, 10)
  return dateStr.split(' ')[0] || '—'
}

function formatMonth(dateStr = '') {
  if (dateStr.includes('-')) {
    try {
      return new Date(`${dateStr}T12:00:00`).toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' })
    } catch {
      return dateStr
    }
  }
  return dateStr.split(' ').slice(1).join(' ') || ''
}

export default function AdminEvents() {
  const { showToast } = useToast()
  const [events, setEvents] = useState(() => withIds(EVENEMENTS))
  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const openCreate = () => {
    setForm(EMPTY)
    setSelected(null)
    setShowForm(true)
  }

  const openDetail = (ev) => {
    setSelected(ev)
    setShowDetail(true)
  }

  const openEdit = (ev) => {
    setSelected(ev)
    setForm({
      date: ev.date || '',
      titre: ev.titre || '',
      type: ev.type || 'Institutionnel',
      description: ev.description || '',
    })
    setShowEdit(true)
  }

  const openDelete = (ev) => {
    setSelected(ev)
    setShowDelete(true)
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.titre || !form.date) {
      showToast('Titre et date obligatoires', 'warning')
      return
    }
    setSaving(true)
    await mockSubmit(showToast, 'Événement créé')
    setEvents((prev) => [
      {
        id: `evt-${Date.now()}`,
        date: form.date,
        titre: form.titre,
        type: form.type,
        description: form.description || '',
      },
      ...prev,
    ])
    setSaving(false)
    setShowForm(false)
    setForm(EMPTY)
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    if (!form.titre || !form.date) {
      showToast('Titre et date obligatoires', 'warning')
      return
    }
    setSaving(true)
    await mockSubmit(showToast, 'Événement mis à jour')
    setEvents((prev) => prev.map((ev) => (
      ev.id === selected.id
        ? { ...ev, date: form.date, titre: form.titre, type: form.type, description: form.description || '' }
        : ev
    )))
    setSaving(false)
    setShowEdit(false)
    setSelected(null)
  }

  const handleDelete = async () => {
    setSaving(true)
    await mockSubmit(showToast, 'Événement supprimé')
    setEvents((prev) => prev.filter((ev) => ev.id !== selected.id))
    setSaving(false)
    setShowDelete(false)
    setSelected(null)
  }

  return (
    <>
      <PageHeader
        title="Événements"
        subtitle="Calendrier institutionnel INJS / UFHB"
        action={<button type="button" className="btn btn-injs-primary" onClick={openCreate}>+ Nouvel événement</button>}
      />

      <div className="row g-3">
        {events.map((ev) => (
          <div key={ev.id} className="col-md-6">
            <div className="card-injs p-4 h-100">
              <div className="d-flex gap-3 mb-3">
                <div className="text-center" style={{ minWidth: 60 }}>
                  <div className="fw-bold text-success">{formatDay(ev.date)}</div>
                  <small className="text-muted">{formatMonth(ev.date)}</small>
                </div>
                <div>
                  <h6 className="fw-bold mb-1">{ev.titre}</h6>
                  <span className="badge-injs">{ev.type}</span>
                </div>
              </div>
              <IconActionButtons
                actions={[
                  { type: 'view', onClick: () => openDetail(ev) },
                  { type: 'edit', onClick: () => openEdit(ev) },
                  { type: 'delete', onClick: () => openDelete(ev) },
                ]}
              />
            </div>
          </div>
        ))}
        {!events.length && (
          <div className="col-12">
            <div className="card-injs p-4 text-muted text-center">Aucun événement</div>
          </div>
        )}
      </div>

      {/* Création */}
      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Nouvel événement"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="event-create-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="event-create-form" onSubmit={handleCreate}>
          <EventFormFields form={form} setForm={setForm} />
        </form>
      </Modal>

      {/* Visualisation */}
      <Modal
        show={showDetail}
        onClose={() => { setShowDetail(false); setSelected(null) }}
        title={selected ? `Événement — ${selected.titre}` : 'Événement'}
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
            <div className="detail-row"><dt>Date</dt><dd>{selected.date}</dd></div>
            <div className="detail-row"><dt>Titre</dt><dd>{selected.titre}</dd></div>
            <div className="detail-row"><dt>Type</dt><dd><span className="badge-injs">{selected.type}</span></dd></div>
            <div className="detail-row"><dt>Description</dt><dd>{selected.description || '—'}</dd></div>
          </dl>
        )}
      </Modal>

      {/* Modification */}
      <Modal
        show={showEdit}
        onClose={() => { setShowEdit(false); setSelected(null) }}
        title={selected ? `Modifier — ${selected.titre}` : 'Modifier l\'événement'}
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowEdit(false)}>Annuler</button>
            <button type="submit" form="event-edit-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="event-edit-form" onSubmit={handleEdit}>
          <EventFormFields form={form} setForm={setForm} />
        </form>
      </Modal>

      {/* Suppression */}
      <Modal
        show={showDelete}
        onClose={() => setShowDelete(false)}
        title="Supprimer l'événement"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowDelete(false)}>Annuler</button>
            <button type="button" className="btn btn-danger" disabled={saving} onClick={handleDelete}>
              {saving ? 'Suppression...' : 'Confirmer la suppression'}
            </button>
          </>
        }
      >
        <p>
          Voulez-vous vraiment supprimer l&apos;événement{' '}
          <strong>{selected?.titre}</strong> ?
        </p>
        <p className="text-danger small mb-0">Cette action est définitive.</p>
      </Modal>
    </>
  )
}

function EventFormFields({ form, setForm }) {
  const isIsoDate = /^\d{4}-\d{2}-\d{2}$/.test(form.date)
  return (
    <div className="row g-3">
      <div className="col-md-6">
        <label className="form-label">Date *</label>
        <input
          type={isIsoDate || !form.date ? 'date' : 'text'}
          className="form-control"
          required
          placeholder="AAAA-MM-JJ ou texte"
          value={form.date}
          onChange={(ev) => setForm({ ...form, date: ev.target.value })}
        />
      </div>
      <div className="col-md-6">
        <label className="form-label">Type</label>
        <select
          className="form-select"
          value={form.type}
          onChange={(ev) => setForm({ ...form, type: ev.target.value })}
        >
          <option>Institutionnel</option>
          <option>Académique</option>
          <option>Partenariat</option>
          <option>Admission</option>
        </select>
      </div>
      <div className="col-12">
        <label className="form-label">Titre *</label>
        <input
          className="form-control"
          required
          value={form.titre}
          onChange={(ev) => setForm({ ...form, titre: ev.target.value })}
        />
      </div>
      <div className="col-12">
        <label className="form-label">Description</label>
        <textarea
          className="form-control"
          rows={3}
          value={form.description}
          onChange={(ev) => setForm({ ...form, description: ev.target.value })}
        />
      </div>
    </div>
  )
}
