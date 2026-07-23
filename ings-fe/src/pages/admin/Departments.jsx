import { useState } from 'react'
import { FiEdit2 } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import ExportButtons from '../../components/common/ExportButtons'
import IconActionButtons from '../../components/common/IconActionButtons'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchDepartments,
  fetchDepartment,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  fetchInstitutions,
} from '../../api/academics'
import { fetchUsers } from '../../api/users'
import { INSTITUTION } from '../../data/mockData'

const EMPTY = {
  code: '',
  name: '',
  description: '',
  institution: '',
  head: '',
}

export default function AdminDepartments() {
  const { showToast } = useToast()
  const { data, loading, error, reload } = useFetch(() => fetchDepartments())
  const { data: institutions } = useFetch(() => fetchInstitutions())
  const { data: usersData } = useFetch(() => fetchUsers({ page_size: 200 }))

  const departments = data?.results || []
  const users = usersData?.results || []

  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const defaultInstitution = institutions?.[0]?.id || ''

  const openCreate = () => {
    setForm({ ...EMPTY, institution: defaultInstitution })
    setShowForm(true)
  }

  const openDetail = async (d) => {
    setSaving(true)
    try {
      const detail = await fetchDepartment(d.id)
      setSelected(detail)
      setShowDetail(true)
    } catch (err) {
      showToast(err.message || 'Impossible de charger la fiche', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const openEdit = async (d) => {
    setSaving(true)
    try {
      const detail = await fetchDepartment(d.id)
      setSelected(detail)
      setForm({
        code: detail.code || '',
        name: detail.label || '',
        description: detail.description || '',
        institution: detail.institutionId || defaultInstitution,
        head: detail.headId || '',
      })
      setShowEdit(true)
    } catch (err) {
      showToast(err.message || 'Impossible de charger la fiche', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const openDelete = (d) => {
    setSelected(d)
    setShowDelete(true)
  }

  const handleCreate = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await createDepartment({
        ...form,
        head: form.head || null,
      })
      showToast(`Département ${form.code} créé`, 'success')
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
      await updateDepartment(selected.id, {
        code: form.code,
        name: form.name,
        description: form.description || '',
        institution: form.institution,
        head: form.head || null,
      })
      showToast('Département mis à jour', 'success')
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
      await deleteDepartment(selected.id)
      showToast('Département supprimé', 'success')
      setShowDelete(false)
      setSelected(null)
      reload()
    } catch (err) {
      showToast(err.message || 'Suppression impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-4">Erreur de chargement : {error}</div>
  }

  return (
    <>
      <PageHeader
        title="Départements & UFR"
        subtitle={`${INSTITUTION.ufr} — ${data?.count || 0} département(s)`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Départements INJS"
              filename="departements"
              headers={['Code', 'Nom', 'Responsable', 'Institution']}
              rows={departments.map((d) => [d.code, d.label, d.responsable, d.institutionName])}
              resourcePath="/academics/departments"
            />
            <button type="button" className="btn btn-injs-primary" onClick={openCreate}>+ Ajouter</button>
          </div>
        }
      />

      <div className="row g-4">
        {departments.map((d) => (
          <div key={d.id} className="col-md-6">
            <div className="card-injs p-4 h-100">
              <span className="badge-injs mb-2">{d.code}</span>
              <h5 className="fw-bold">{d.label}</h5>
              <p className="text-muted small mb-2">Responsable : {d.responsable}</p>
              {d.description && (
                <p className="small text-muted mb-3">{d.description.slice(0, 120)}{d.description.length > 120 ? '…' : ''}</p>
              )}
              <IconActionButtons
                actions={[
                  { type: 'view', onClick: () => openDetail(d) },
                  { type: 'edit', onClick: () => openEdit(d) },
                  { type: 'delete', onClick: () => openDelete(d) },
                ]}
              />
            </div>
          </div>
        ))}
        {!departments.length && (
          <div className="col-12">
            <div className="card-injs p-4 text-muted text-center">Aucun département</div>
          </div>
        )}
      </div>

      {/* Création */}
      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Ajouter un département"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="dept-create-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Création...' : 'Ajouter'}
            </button>
          </>
        }
      >
        <form id="dept-create-form" onSubmit={handleCreate}>
          <DepartmentFormFields form={form} setForm={setForm} institutions={institutions || []} users={users} />
        </form>
      </Modal>

      {/* Visualisation */}
      <Modal
        show={showDetail}
        onClose={() => { setShowDetail(false); setSelected(null) }}
        title={selected ? `Fiche département — ${selected.code}` : 'Fiche département'}
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
            <div className="detail-row"><dt>Nom</dt><dd>{selected.label}</dd></div>
            <div className="detail-row"><dt>Institution</dt><dd>{selected.institutionName || '—'}</dd></div>
            <div className="detail-row"><dt>Responsable</dt><dd>{selected.responsable}</dd></div>
            <div className="detail-row"><dt>Description</dt><dd>{selected.description || '—'}</dd></div>
          </dl>
        )}
      </Modal>

      {/* Modification */}
      <Modal
        show={showEdit}
        onClose={() => { setShowEdit(false); setSelected(null) }}
        title={selected ? `Modifier — ${selected.code}` : 'Modifier le département'}
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowEdit(false)}>Annuler</button>
            <button type="submit" form="dept-edit-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="dept-edit-form" onSubmit={handleEdit}>
          <DepartmentFormFields form={form} setForm={setForm} institutions={institutions || []} users={users} />
        </form>
      </Modal>

      {/* Suppression */}
      <Modal
        show={showDelete}
        onClose={() => setShowDelete(false)}
        title="Supprimer le département"
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
          Voulez-vous vraiment supprimer le département{' '}
          <strong>{selected ? `${selected.code} — ${selected.label}` : ''}</strong> ?
        </p>
        <p className="text-danger small mb-0">
          Le département sera archivé (soft delete) et n’apparaîtra plus dans la liste.
        </p>
      </Modal>
    </>
  )
}

function DepartmentFormFields({ form, setForm, institutions, users }) {
  return (
    <div className="row g-3">
      <div className="col-md-4">
        <label className="form-label">Code *</label>
        <input
          className="form-control"
          required
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
      <div className="col-md-6">
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
      <div className="col-md-6">
        <label className="form-label">Responsable</label>
        <select
          className="form-select"
          value={form.head}
          onChange={(ev) => setForm({ ...form, head: ev.target.value })}
        >
          <option value="">— Aucun —</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.prenom} {u.nom} ({u.email})
            </option>
          ))}
        </select>
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
