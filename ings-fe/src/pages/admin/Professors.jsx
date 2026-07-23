import { useEffect, useState } from 'react'
import { FiEdit2 } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import ExportButtons from '../../components/common/ExportButtons'
import IconActionButtons from '../../components/common/IconActionButtons'
import TeacherDetailPanel from '../../components/admin/TeacherDetailPanel'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchTeachers,
  fetchTeacherFullDetail,
  createTeacher,
  updateTeacher,
  deleteTeacher,
  TEACHER_GRADES,
} from '../../api/faculty'
import { fetchDepartments } from '../../api/academics'

const CREATE_EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  grade: 'assistant',
  specialization: '',
  department: '',
  hire_date: '',
}

const EDIT_EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  grade: 'assistant',
  specialization: '',
  department: '',
  hire_date: '',
  is_active: true,
}

export default function AdminProfessors() {
  const { showToast } = useToast()
  const { data, loading, error, reload } = useFetch(() => fetchTeachers())
  const { data: departmentsData } = useFetch(() => fetchDepartments())
  const professors = data?.results || []
  const departments = departmentsData?.results || []

  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  const [selectedUuid, setSelectedUuid] = useState(null)
  const [selectedName, setSelectedName] = useState('')
  const [selectedPhoto, setSelectedPhoto] = useState(null)

  const [form, setForm] = useState(CREATE_EMPTY)
  const [editForm, setEditForm] = useState(EDIT_EMPTY)
  const [photoFile, setPhotoFile] = useState(null)
  const [photoPreview, setPhotoPreview] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    return () => {
      if (photoPreview) URL.revokeObjectURL(photoPreview)
    }
  }, [photoPreview])

  const openCreate = () => {
    setForm({
      ...CREATE_EMPTY,
      department: departments[0]?.id || '',
    })
    setShowForm(true)
  }

  const openDetail = (p) => {
    setSelectedUuid(p.id)
    setSelectedName(p.nom)
    setSelectedPhoto(p.photoUrl)
    setShowDetail(true)
  }

  const openEdit = async (p) => {
    setSelectedUuid(p.id)
    setSelectedName(p.nom)
    setPhotoFile(null)
    setPhotoPreview(null)
    setSaving(true)
    try {
      const detail = await fetchTeacherFullDetail(p.id)
      const { teacher, user } = detail
      setEditForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        phone: user.phone || '',
        grade: teacher.grade || 'assistant',
        specialization: teacher.specialization || '',
        department: teacher.department || '',
        hire_date: teacher.hire_date || '',
        is_active: teacher.is_active !== false,
      })
      setSelectedPhoto(teacher.photo_url || user.photo_url || null)
      setShowEdit(true)
    } catch (err) {
      showToast(err.message || 'Impossible de charger la fiche', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const openDelete = (p) => {
    setSelectedUuid(p.id)
    setSelectedName(`${p.nom} (${p.employeeId})`)
    setShowDelete(true)
  }

  const handleSubmit = async (ev) => {
    ev.preventDefault()
    if (!form.first_name.trim() || !form.last_name.trim()) {
      showToast('Veuillez remplir le nom et le prénom', 'warning')
      return
    }
    setSaving(true)
    try {
      const created = await createTeacher(form)
      showToast(`Enseignant ajouté — ${created.employeeId}`, 'success')
      setShowForm(false)
      setForm(CREATE_EMPTY)
      reload()
    } catch (err) {
      showToast(err.message || 'Erreur lors de la création', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleEditSubmit = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await updateTeacher(selectedUuid, {
        userPatch: {
          first_name: editForm.first_name,
          last_name: editForm.last_name,
          email: editForm.email,
          phone: editForm.phone,
        },
        teacherPatch: {
          grade: editForm.grade,
          specialization: editForm.specialization,
          department: editForm.department || undefined,
          hire_date: editForm.hire_date || null,
          is_active: editForm.is_active,
        },
        photoFile,
      })
      showToast('Fiche professeur mise à jour', 'success')
      setShowEdit(false)
      setPhotoFile(null)
      setPhotoPreview(null)
      reload()
    } catch (err) {
      showToast(err.message || 'Échec de la modification', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setSaving(true)
    try {
      await deleteTeacher(selectedUuid)
      showToast('Fiche professeur supprimée', 'success')
      setShowDelete(false)
      setSelectedUuid(null)
      reload()
    } catch (err) {
      showToast(err.message || 'Suppression impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const onPhotoChange = (ev) => {
    const file = ev.target.files?.[0]
    if (!file) return
    if (photoPreview) URL.revokeObjectURL(photoPreview)
    setPhotoFile(file)
    setPhotoPreview(URL.createObjectURL(file))
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
        title="Gestion des professeurs"
        subtitle={`Enseignants INJS & UFHB — ${data?.count || 0} professeur(s)`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Enseignants INJS"
              filename="enseignants"
              headers={['ID', 'Nom', 'Grade', 'Spécialisation', 'Email', 'Téléphone']}
              rows={professors.map((p) => [p.employeeId, p.nom, p.grade, p.ue, p.email, p.tel])}
              resourcePath="/faculty/teachers"
            />
            <button type="button" className="btn btn-injs-primary" onClick={openCreate}>+ Ajouter</button>
          </div>
        }
      />

      <div className="row g-4">
        {professors.map((p) => (
          <div key={p.id} className="col-md-6 col-lg-4">
            <div className="card-injs p-4 h-100">
              <div className="d-flex align-items-center gap-3 mb-3">
                {p.photoUrl ? (
                  <img
                    src={p.photoUrl}
                    alt=""
                    className="rounded-circle"
                    style={{ width: 56, height: 56, objectFit: 'cover' }}
                  />
                ) : (
                  <div className="user-avatar" style={{ width: 56, height: 56, fontSize: '1.1rem' }}>
                    {(p.nom || '?').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()}
                  </div>
                )}
                <div>
                  <h6 className="fw-bold mb-0">{p.nom}</h6>
                  <small className="text-muted">
                    {p.grade}
                    {p.gender === 'M' ? ' · H' : p.gender === 'F' ? ' · F' : ''}
                  </small>
                </div>
              </div>
              <p className="small mb-1"><strong>UE :</strong> {p.ue}</p>
              <p className="small mb-1"><strong>Email :</strong> {p.email || '—'}</p>
              <p className="small mb-3"><strong>Tél :</strong> {p.tel || '—'}</p>
              <IconActionButtons
                actions={[
                  { type: 'view', onClick: () => openDetail(p) },
                  { type: 'edit', onClick: () => openEdit(p) },
                  { type: 'delete', onClick: () => openDelete(p) },
                ]}
              />
            </div>
          </div>
        ))}
        {!professors.length && (
          <div className="col-12">
            <div className="card-injs p-4 text-muted text-center">Aucun professeur</div>
          </div>
        )}
      </div>

      {/* Création */}
      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Ajouter un professeur"
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="prof-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Création...' : 'Ajouter'}
            </button>
          </>
        }
      >
        <form id="prof-form" onSubmit={handleSubmit}>
          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label">Prénom *</label>
              <input className="form-control" required value={form.first_name} onChange={(ev) => setForm({ ...form, first_name: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Nom *</label>
              <input className="form-control" required value={form.last_name} onChange={(ev) => setForm({ ...form, last_name: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Email *</label>
              <input type="email" className="form-control" required value={form.email} onChange={(ev) => setForm({ ...form, email: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Téléphone</label>
              <input className="form-control" value={form.phone} onChange={(ev) => setForm({ ...form, phone: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Grade</label>
              <select className="form-select" value={form.grade} onChange={(ev) => setForm({ ...form, grade: ev.target.value })}>
                {TEACHER_GRADES.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Département</label>
              <select className="form-select" value={form.department} onChange={(ev) => setForm({ ...form, department: ev.target.value })}>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.code} — {d.label}</option>)}
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Spécialisation / UE</label>
              <input className="form-control" value={form.specialization} onChange={(ev) => setForm({ ...form, specialization: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Date d&apos;embauche</label>
              <input type="date" className="form-control" value={form.hire_date} onChange={(ev) => setForm({ ...form, hire_date: ev.target.value })} />
            </div>
          </div>
        </form>
      </Modal>

      {/* Visualisation */}
      <Modal
        show={showDetail}
        onClose={() => { setShowDetail(false); setSelectedUuid(null) }}
        title={selectedName ? `Fiche professeur — ${selectedName}` : 'Fiche professeur'}
        size="xl"
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
                const row = professors.find((s) => s.id === selectedUuid)
                if (row) openEdit(row)
              }}
            >
              <FiEdit2 size={16} />
            </button>
          </>
        }
      >
        <TeacherDetailPanel teacherUuid={selectedUuid} />
      </Modal>

      {/* Modification */}
      <Modal
        show={showEdit}
        onClose={() => { setShowEdit(false); setPhotoFile(null); setPhotoPreview(null) }}
        title={selectedName ? `Modifier — ${selectedName}` : 'Modifier la fiche'}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowEdit(false)}>Annuler</button>
            <button type="submit" form="prof-edit-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="prof-edit-form" onSubmit={handleEditSubmit}>
          <div className="d-flex align-items-center gap-3 mb-4">
            {(photoPreview || selectedPhoto) ? (
              <img src={photoPreview || selectedPhoto} alt="" className="student-photo" style={{ width: 96, height: 96 }} />
            ) : (
              <div className="student-photo student-photo-placeholder" style={{ width: 96, height: 96 }}>
                {`${editForm.first_name?.[0] || ''}${editForm.last_name?.[0] || ''}`.toUpperCase() || '?'}
              </div>
            )}
            <div>
              <label className="form-label">Photo du professeur</label>
              <input type="file" accept="image/*" className="form-control" onChange={onPhotoChange} />
              <small className="text-muted">JPG/PNG — affichée sur la fiche</small>
            </div>
          </div>

          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label">Prénom *</label>
              <input className="form-control" required value={editForm.first_name} onChange={(ev) => setEditForm({ ...editForm, first_name: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Nom *</label>
              <input className="form-control" required value={editForm.last_name} onChange={(ev) => setEditForm({ ...editForm, last_name: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Email *</label>
              <input type="email" className="form-control" required value={editForm.email} onChange={(ev) => setEditForm({ ...editForm, email: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Téléphone</label>
              <input className="form-control" value={editForm.phone} onChange={(ev) => setEditForm({ ...editForm, phone: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Grade</label>
              <select className="form-select" value={editForm.grade} onChange={(ev) => setEditForm({ ...editForm, grade: ev.target.value })}>
                {TEACHER_GRADES.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Département</label>
              <select className="form-select" value={editForm.department} onChange={(ev) => setEditForm({ ...editForm, department: ev.target.value })}>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.code} — {d.label}</option>)}
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Spécialisation / UE</label>
              <input className="form-control" value={editForm.specialization} onChange={(ev) => setEditForm({ ...editForm, specialization: ev.target.value })} />
            </div>
            <div className="col-md-3">
              <label className="form-label">Date d&apos;embauche</label>
              <input type="date" className="form-control" value={editForm.hire_date} onChange={(ev) => setEditForm({ ...editForm, hire_date: ev.target.value })} />
            </div>
            <div className="col-md-3">
              <label className="form-label">Statut</label>
              <select
                className="form-select"
                value={editForm.is_active ? '1' : '0'}
                onChange={(ev) => setEditForm({ ...editForm, is_active: ev.target.value === '1' })}
              >
                <option value="1">Actif</option>
                <option value="0">Inactif</option>
              </select>
            </div>
          </div>
        </form>
      </Modal>

      {/* Suppression */}
      <Modal
        show={showDelete}
        onClose={() => setShowDelete(false)}
        title="Supprimer la fiche professeur"
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
          Voulez-vous vraiment supprimer la fiche de <strong>{selectedName}</strong> ?
        </p>
        <p className="text-danger small mb-0">
          Cette action est définitive (profil enseignant + compte associé si possible).
        </p>
      </Modal>
    </>
  )
}
