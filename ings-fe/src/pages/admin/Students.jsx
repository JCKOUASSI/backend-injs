import { useEffect, useMemo, useState } from 'react'
import { FiEdit2 } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import ExportButtons from '../../components/common/ExportButtons'
import IconActionButtons from '../../components/common/IconActionButtons'
import PaginationBar from '../../components/common/PaginationBar'
import StudentDetailPanel from '../../components/admin/StudentDetailPanel'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchStudents,
  fetchStudentsMeta,
  enrollStudent,
  fetchStudentFullDetail,
  updateStudent,
  deleteStudent,
} from '../../api/students'
import { fetchSpecializations } from '../../api/academics'
import { SPECIALITES_STAPS, INSTITUTION } from '../../data/mockData'
import { StatusBadge } from '../../utils/statusBadge'

const EMPTY = { nom: '', prenom: '', email: '', niveau: 'L1', specialite: 'Tronc commun', semestre: 1 }

const EDIT_EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  date_of_birth: '',
  place_of_birth: '',
  nationality: 'Ivoirienne',
  gender: '',
  address: '',
  emergency_contact: '',
  emergency_phone: '',
  status: 'active',
  specialization: '',
}

function genderLabel(g) {
  if (g === 'M') return 'H'
  if (g === 'F') return 'F'
  return '—'
}

export default function AdminStudents() {
  const { showToast } = useToast()
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [program, setProgram] = useState('')
  const [promotion, setPromotion] = useState('')
  const [status, setStatus] = useState('')
  const [gender, setGender] = useState('')
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
    program: program || undefined,
    promotion: promotion || undefined,
    status: status || undefined,
    gender: gender || undefined,
    page,
    page_size: pageSize,
  }), [search, program, promotion, status, gender, page, pageSize])

  const { data, loading, error, reload } = useFetch(
    () => fetchStudents(filters),
    [filters.search, filters.program, filters.promotion, filters.status, filters.gender, filters.page, filters.page_size],
  )
  const { data: meta, reload: reloadMeta } = useFetch(() => fetchStudentsMeta(), [])
  const { data: specializations } = useFetch(() => fetchSpecializations(), [])

  const students = data?.results || []
  const total = data?.count ?? 0

  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  const [selectedUuid, setSelectedUuid] = useState(null)
  const [selectedName, setSelectedName] = useState('')
  const [selectedPhoto, setSelectedPhoto] = useState(null)

  const [form, setForm] = useState(EMPTY)
  const [editForm, setEditForm] = useState(EDIT_EMPTY)
  const [photoFile, setPhotoFile] = useState(null)
  const [photoPreview, setPhotoPreview] = useState(null)
  const [saving, setSaving] = useState(false)

  const setFilterAndResetPage = (setter) => (value) => {
    setter(value)
    setPage(1)
  }

  useEffect(() => {
    return () => {
      if (photoPreview) URL.revokeObjectURL(photoPreview)
    }
  }, [photoPreview])

  const openCreate = () => {
    setForm(EMPTY)
    setShowForm(true)
  }

  const openDetail = (e) => {
    setSelectedUuid(e.uuid)
    setSelectedName(`${e.prenom} ${e.nom}`)
    setSelectedPhoto(e.photoUrl)
    setShowDetail(true)
  }

  const openEdit = async (e) => {
    setSelectedUuid(e.uuid)
    setSelectedName(`${e.prenom} ${e.nom}`)
    setPhotoFile(null)
    setPhotoPreview(null)
    setSaving(true)
    try {
      const detail = await fetchStudentFullDetail(e.uuid)
      const { student, user } = detail
      setEditForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        phone: user.phone || '',
        date_of_birth: student.date_of_birth || '',
        place_of_birth: student.place_of_birth || '',
        nationality: student.nationality || 'Ivoirienne',
        gender: student.gender || '',
        address: student.address || '',
        emergency_contact: student.emergency_contact || '',
        emergency_phone: student.emergency_phone || '',
        status: student.status || 'active',
        specialization: student.specialization || '',
      })
      setSelectedPhoto(student.photo_url || user.photo_url || null)
      setShowEdit(true)
    } catch (err) {
      showToast(err.message || 'Impossible de charger la fiche', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const openDelete = (e) => {
    setSelectedUuid(e.uuid)
    setSelectedName(`${e.prenom} ${e.nom} (${e.id})`)
    setShowDelete(true)
  }

  const handleSubmit = async (ev) => {
    ev.preventDefault()
    if (!form.nom.trim() || !form.prenom.trim()) {
      showToast('Veuillez remplir le nom et le prénom', 'warning')
      return
    }
    setSaving(true)
    try {
      const created = await enrollStudent(form)
      showToast(`Étudiant inscrit — matricule ${created.id}`, 'success')
      setShowForm(false)
      setForm(EMPTY)
      reload()
      reloadMeta()
    } catch (err) {
      showToast(err.message || 'Erreur lors de l\'inscription', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleEditSubmit = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await updateStudent(selectedUuid, {
        userPatch: {
          first_name: editForm.first_name,
          last_name: editForm.last_name,
          email: editForm.email,
          phone: editForm.phone,
        },
        studentPatch: {
          date_of_birth: editForm.date_of_birth || null,
          place_of_birth: editForm.place_of_birth,
          nationality: editForm.nationality,
          gender: editForm.gender || '',
          address: editForm.address,
          emergency_contact: editForm.emergency_contact,
          emergency_phone: editForm.emergency_phone,
          status: editForm.status,
          specialization: editForm.specialization || null,
        },
        photoFile,
      })
      showToast('Fiche étudiant mise à jour', 'success')
      setShowEdit(false)
      setPhotoFile(null)
      setPhotoPreview(null)
      reload()
      reloadMeta()
    } catch (err) {
      showToast(err.message || 'Échec de la modification', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setSaving(true)
    try {
      await deleteStudent(selectedUuid)
      showToast('Fiche étudiant supprimée', 'success')
      setShowDelete(false)
      setSelectedUuid(null)
      reload()
      reloadMeta()
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

  if (loading && !data) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-4">Erreur de chargement : {error}</div>
  }

  const programOptions = meta?.programs || []
  const promotionOptions = (meta?.promotions || []).filter((p) => !program || p.program === program)
  const statusOptions = meta?.statuses || []
  const counts = meta?.counts || {}

  return (
    <>
      <PageHeader
        title="Gestion des étudiants"
        subtitle={`${INSTITUTION.shortName || 'INJS'} — ${counts.total ?? total} étudiant(s)`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Étudiants INJS"
              filename="etudiants"
              headers={['Matricule', 'Nom', 'Prénom', 'Formation', 'Promotion', 'Genre', 'Statut']}
              rows={students.map((e) => [
                e.id, e.nom, e.prenom, e.programName, e.promotionName, genderLabel(e.gender), e.statut,
              ])}
              resourcePath="/students"
            />
            <button type="button" className="btn btn-injs-primary" onClick={openCreate}>+ Inscrire un étudiant</button>
          </div>
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{counts.total ?? total}</div>
            <div className="small text-muted">Étudiants</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{counts.men ?? '—'}</div>
            <div className="small text-muted">Hommes</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{counts.women ?? '—'}</div>
            <div className="small text-muted">Femmes</div>
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
          <span className="small text-muted me-1">Formations :</span>
          <button
            type="button"
            className={`btn btn-sm ${!program ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => {
              setProgram('')
              setPromotion('')
              setPage(1)
            }}
          >
            Toutes ({counts.total ?? '—'})
          </button>
          {programOptions.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`btn btn-sm ${program === p.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => {
                setProgram(p.id)
                setPromotion('')
                setPage(1)
              }}
              title={p.name}
            >
              {p.code} <span className="opacity-75">({p.count})</span>
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
              placeholder="Matricule, nom, email…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Promotion</label>
            <select
              className="form-select"
              value={promotion}
              onChange={(ev) => setFilterAndResetPage(setPromotion)(ev.target.value)}
            >
              <option value="">Toutes</option>
              {promotionOptions.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.count})</option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Genre</label>
            <select
              className="form-select"
              value={gender}
              onChange={(ev) => setFilterAndResetPage(setGender)(ev.target.value)}
            >
              <option value="">Tous</option>
              <option value="M">Hommes</option>
              <option value="F">Femmes</option>
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
                    <th>Photo</th>
                    <th>Matricule</th>
                    <th>Nom & Prénom</th>
                    <th>Formation</th>
                    <th>Promotion</th>
                    <th>Genre</th>
                    <th>Statut</th>
                    <th className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((e) => (
                    <tr key={e.uuid}>
                      <td>
                        {e.photoUrl ? (
                          <img src={e.photoUrl} alt="" className="student-photo-sm" />
                        ) : (
                          <div className="student-photo-sm student-photo-placeholder">
                            {`${e.prenom?.[0] || ''}${e.nom?.[0] || ''}`.toUpperCase() || '?'}
                          </div>
                        )}
                      </td>
                      <td><code className="small">{e.id}</code></td>
                      <td>
                        <div className="fw-semibold">{e.nom} {e.prenom}</div>
                        {e.email && <small className="text-muted">{e.email}</small>}
                      </td>
                      <td className="small">{e.programName || '—'}</td>
                      <td><span className="badge-injs">{e.promotionName || e.niveau}</span></td>
                      <td>{genderLabel(e.gender)}</td>
                      <td><StatusBadge statut={e.statut} /></td>
                      <td className="text-end">
                        <IconActionButtons
                          actions={[
                            { type: 'view', onClick: () => openDetail(e) },
                            { type: 'edit', onClick: () => openEdit(e) },
                            { type: 'delete', onClick: () => openDelete(e) },
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                  {!students.length && (
                    <tr>
                      <td colSpan={8} className="text-center text-muted py-4">Aucun étudiant trouvé</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {students.map((e) => (
                  <div key={e.uuid} className="col-md-6 col-xl-4">
                    <div className="border rounded-3 p-3 h-100">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <code className="small">{e.id}</code>
                        <StatusBadge statut={e.statut} />
                      </div>
                      <div className="d-flex align-items-center gap-2 mb-2">
                        {e.photoUrl ? (
                          <img src={e.photoUrl} alt="" className="student-photo-sm" />
                        ) : (
                          <div className="student-photo-sm student-photo-placeholder">
                            {`${e.prenom?.[0] || ''}${e.nom?.[0] || ''}`.toUpperCase() || '?'}
                          </div>
                        )}
                        <div>
                          <h6 className="fw-bold mb-0">{e.nom} {e.prenom}</h6>
                          <small className="text-muted">{genderLabel(e.gender)}</small>
                        </div>
                      </div>
                      <p className="small text-muted mb-2">
                        {e.programName || '—'} · {e.promotionName || e.niveau}
                      </p>
                      <IconActionButtons
                        actions={[
                          { type: 'view', onClick: () => openDetail(e) },
                          { type: 'edit', onClick: () => openEdit(e) },
                          { type: 'delete', onClick: () => openDelete(e) },
                        ]}
                      />
                    </div>
                  </div>
                ))}
                {!students.length && (
                  <div className="col-12 text-center text-muted py-4">Aucun étudiant trouvé</div>
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

      {/* Création */}
      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Inscrire un étudiant"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="student-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Inscription...' : 'Inscrire'}
            </button>
          </>
        }
      >
        <form id="student-form" onSubmit={handleSubmit}>
          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label">Email (optionnel)</label>
              <input type="email" className="form-control" placeholder="Généré automatiquement si vide" value={form.email} onChange={(ev) => setForm({ ...form, email: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Nom *</label>
              <input className="form-control" required value={form.nom} onChange={(ev) => setForm({ ...form, nom: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Prénom *</label>
              <input className="form-control" required value={form.prenom} onChange={(ev) => setForm({ ...form, prenom: ev.target.value })} />
            </div>
            <div className="col-md-4">
              <label className="form-label">Niveau</label>
              <select className="form-select" value={form.niveau} onChange={(ev) => setForm({ ...form, niveau: ev.target.value })}>
                {['L1', 'L2', 'L3', 'M1', 'M2'].map((n) => <option key={n}>{n}</option>)}
              </select>
            </div>
            <div className="col-md-4">
              <label className="form-label">Spécialité</label>
              <select className="form-select" value={form.specialite} onChange={(ev) => setForm({ ...form, specialite: ev.target.value })}>
                <option>Tronc commun</option>
                {SPECIALITES_STAPS.map((s) => <option key={s.id} value={s.code}>{s.label}</option>)}
              </select>
            </div>
            <div className="col-md-4">
              <label className="form-label">Semestre</label>
              <select className="form-select" value={form.semestre} onChange={(ev) => setForm({ ...form, semestre: ev.target.value })}>
                {[1, 2, 3, 4, 5, 6].map((s) => <option key={s} value={s}>S{s}</option>)}
              </select>
            </div>
          </div>
        </form>
      </Modal>

      {/* Visualisation */}
      <Modal
        show={showDetail}
        onClose={() => { setShowDetail(false); setSelectedUuid(null) }}
        title={selectedName ? `Fiche étudiant — ${selectedName}` : 'Fiche étudiant'}
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
                const row = students.find((s) => s.uuid === selectedUuid)
                if (row) openEdit(row)
              }}
            >
              <FiEdit2 size={16} />
            </button>
          </>
        }
      >
        <StudentDetailPanel studentUuid={selectedUuid} />
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
            <button type="submit" form="student-edit-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="student-edit-form" onSubmit={handleEditSubmit}>
          <div className="d-flex align-items-center gap-3 mb-4">
            {(photoPreview || selectedPhoto) ? (
              <img src={photoPreview || selectedPhoto} alt="" className="student-photo" style={{ width: 96, height: 96 }} />
            ) : (
              <div className="student-photo student-photo-placeholder" style={{ width: 96, height: 96 }}>
                {`${editForm.first_name?.[0] || ''}${editForm.last_name?.[0] || ''}`.toUpperCase() || '?'}
              </div>
            )}
            <div>
              <label className="form-label">Photo de l&apos;étudiant</label>
              <input type="file" accept="image/*" className="form-control" onChange={onPhotoChange} />
              <small className="text-muted">JPG/PNG — affichée sur la fiche et la carte</small>
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
            <div className="col-md-4">
              <label className="form-label">Date de naissance</label>
              <input type="date" className="form-control" value={editForm.date_of_birth} onChange={(ev) => setEditForm({ ...editForm, date_of_birth: ev.target.value })} />
            </div>
            <div className="col-md-4">
              <label className="form-label">Lieu de naissance</label>
              <input className="form-control" value={editForm.place_of_birth} onChange={(ev) => setEditForm({ ...editForm, place_of_birth: ev.target.value })} />
            </div>
            <div className="col-md-4">
              <label className="form-label">Genre</label>
              <select className="form-select" value={editForm.gender} onChange={(ev) => setEditForm({ ...editForm, gender: ev.target.value })}>
                <option value="">—</option>
                <option value="M">Masculin</option>
                <option value="F">Féminin</option>
              </select>
            </div>
            <div className="col-md-4">
              <label className="form-label">Nationalité</label>
              <input className="form-control" value={editForm.nationality} onChange={(ev) => setEditForm({ ...editForm, nationality: ev.target.value })} />
            </div>
            <div className="col-md-4">
              <label className="form-label">Statut</label>
              <select className="form-select" value={editForm.status} onChange={(ev) => setEditForm({ ...editForm, status: ev.target.value })}>
                <option value="active">Actif</option>
                <option value="suspended">Suspendu</option>
                <option value="graduated">Diplômé</option>
                <option value="withdrawn">Retiré</option>
              </select>
            </div>
            <div className="col-md-4">
              <label className="form-label">Spécialité</label>
              <select className="form-select" value={editForm.specialization} onChange={(ev) => setEditForm({ ...editForm, specialization: ev.target.value })}>
                <option value="">Tronc commun</option>
                {(specializations || []).map((s) => (
                  <option key={s.id} value={s.id}>{s.code} — {s.name}</option>
                ))}
              </select>
            </div>
            <div className="col-12">
              <label className="form-label">Adresse</label>
              <textarea className="form-control" rows={2} value={editForm.address} onChange={(ev) => setEditForm({ ...editForm, address: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Contact d&apos;urgence</label>
              <input className="form-control" value={editForm.emergency_contact} onChange={(ev) => setEditForm({ ...editForm, emergency_contact: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Tél. urgence</label>
              <input className="form-control" value={editForm.emergency_phone} onChange={(ev) => setEditForm({ ...editForm, emergency_phone: ev.target.value })} />
            </div>
          </div>
        </form>
      </Modal>

      {/* Suppression */}
      <Modal
        show={showDelete}
        onClose={() => setShowDelete(false)}
        title="Supprimer la fiche étudiant"
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
          Cette action est définitive (profil étudiant + compte associé si possible).
        </p>
      </Modal>
    </>
  )
}
