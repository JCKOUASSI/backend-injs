import { useEffect, useMemo, useState } from 'react'
import { FiEdit2, FiCheck, FiX } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import Modal from '../../components/common/Modal'
import PaginationBar from '../../components/common/PaginationBar'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchGrades,
  fetchExamSessions,
  createExamSession,
  fetchDeliberations,
  runDeliberation,
  validateDeliberation,
  publishDeliberation,
} from '../../api/exams'
import { fetchAcademicYears, updateCourse, updateTeachingUnit } from '../../api/academics'
import { StatusBadge } from '../../utils/statusBadge'
import { translateDelibAction, translateSessionType } from '../../utils/labels'

const CC_WEIGHT = 0.4
const CT_WEIGHT = 0.6

/**
 * Agrège CC/CT par étudiant + ECUE → moyenne LMD et statut de validation.
 */
function buildEcueValidations(grades, passingOverrides = {}) {
  const groups = new Map()

  for (const g of grades) {
    const key = `${g.studentId || g.matricule || 'x'}::${g.courseId || g.courseCode}`
    if (!groups.has(key)) {
      const targetId = g.courseId
      const defaultPassing = g.passingScore ?? 10
      groups.set(key, {
        key,
        studentName: g.studentName || '—',
        matricule: g.matricule || '—',
        courseCode: g.courseCode || g.ue || '—',
        courseName: g.courseName || g.label || '—',
        ue: g.ue,
        courseId: targetId,
        hasCourse: g.hasCourse !== false,
        passingScore: targetId && passingOverrides[targetId] != null
          ? Number(passingOverrides[targetId])
          : defaultPassing,
        cc: null,
        ct: null,
        scores: [],
      })
    }
    const row = groups.get(key)
    const type = String(g.evaluationType || '').toLowerCase()
    if (g.moyenne != null) {
      row.scores.push(Number(g.moyenne))
      if (type === 'cc' || type.includes('continu')) row.cc = Number(g.moyenne)
      else if (type === 'exam' || type === 'ct' || type.includes('terminal')) row.ct = Number(g.moyenne)
    }
  }

  return [...groups.values()].map((row) => {
    let studentScore = null
    if (row.cc != null && row.ct != null) {
      studentScore = Math.round((row.cc * CC_WEIGHT + row.ct * CT_WEIGHT) * 100) / 100
    } else if (row.cc != null) {
      studentScore = row.cc
    } else if (row.ct != null) {
      studentScore = row.ct
    } else if (row.scores.length) {
      studentScore = Math.round((row.scores.reduce((a, b) => a + b, 0) / row.scores.length) * 100) / 100
    }

    const passing = Number(row.passingScore) || 10
    const validated = studentScore != null && studentScore >= passing

    return {
      ...row,
      studentScore,
      passingScore: passing,
      validated,
      statusKey: studentScore == null ? 'pending' : validated ? 'valid' : 'invalid',
      statusLabel: studentScore == null ? 'Non noté' : validated ? 'ECUE validé' : 'ECUE invalidé',
    }
  })
}

function EcuePassingEditor({
  row,
  isEditing,
  editValue,
  setEditValue,
  savingPass,
  onStart,
  onSave,
  onCancel,
}) {
  if (isEditing) {
    return (
      <div className="d-flex align-items-center gap-1">
        <input
          type="number"
          min="0"
          max="20"
          step="0.25"
          className="form-control form-control-sm"
          style={{ maxWidth: 72 }}
          value={editValue}
          onChange={(ev) => setEditValue(ev.target.value)}
          disabled={savingPass}
        />
        <button
          type="button"
          className="btn btn-sm btn-outline-success btn-icon-action"
          title="Enregistrer"
          aria-label="Enregistrer"
          disabled={savingPass}
          onClick={() => onSave(row)}
        >
          <FiCheck size={14} />
        </button>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary btn-icon-action"
          title="Annuler"
          aria-label="Annuler"
          disabled={savingPass}
          onClick={onCancel}
        >
          <FiX size={14} />
        </button>
      </div>
    )
  }

  return (
    <div className="d-flex align-items-center gap-2">
      <strong>{row.passingScore}/20</strong>
      <button
        type="button"
        className="btn btn-sm btn-outline-primary btn-icon-action"
        title="Modifier la note de validation"
        aria-label="Modifier la note de validation"
        onClick={() => onStart(row)}
      >
        <FiEdit2 size={14} />
      </button>
    </div>
  )
}

export default function AdminGrades() {
  const { showToast } = useToast()
  const { data: gradesData, loading, reload: reloadGrades } = useFetch(() => fetchGrades({ page_size: 500 }))
  const { data: sessions, reload: reloadSessions } = useFetch(() => fetchExamSessions())
  const { data: deliberations, reload: reloadDelib } = useFetch(() => fetchDeliberations())
  const { data: years } = useFetch(() => fetchAcademicYears())

  const [showSession, setShowSession] = useState(false)
  const [form, setForm] = useState({ name: 'Session S1', session_type: 'normal', academic_year: '' })
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState(null)
  const [passingOverrides, setPassingOverrides] = useState({})
  const [editingKey, setEditingKey] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [savingPass, setSavingPass] = useState(false)

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [viewMode, setViewMode] = useState('cards')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [searchInput])

  const grades = gradesData?.results || []
  const ecueRows = useMemo(
    () => buildEcueValidations(grades, passingOverrides),
    [grades, passingOverrides],
  )

  const counts = useMemo(() => {
    let valid = 0
    let invalid = 0
    let pending = 0
    for (const e of ecueRows) {
      if (e.statusKey === 'valid') valid += 1
      else if (e.statusKey === 'invalid') invalid += 1
      else pending += 1
    }
    return {
      total: ecueRows.length,
      valid,
      invalid,
      pending,
      sessions: (sessions || []).length,
      deliberations: (deliberations || []).length,
    }
  }, [ecueRows, sessions, deliberations])

  const filtered = useMemo(() => {
    return ecueRows.filter((e) => {
      if (statusFilter && e.statusKey !== statusFilter) return false
      if (!search) return true
      const hay = `${e.courseCode} ${e.courseName} ${e.matricule} ${e.studentName} ${e.statusLabel}`.toLowerCase()
      return hay.includes(search)
    })
  }, [ecueRows, statusFilter, search])

  const total = filtered.length
  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return filtered.slice(start, start + pageSize)
  }, [filtered, page, pageSize])

  const rows = filtered.map((e) => [
    e.courseCode,
    e.courseName,
    e.matricule,
    e.studentName,
    e.studentScore ?? '—',
    e.passingScore,
    e.statusLabel,
  ])

  const setStatusAndReset = (value) => {
    setStatusFilter(value)
    setPage(1)
  }

  const startEditPassing = (row) => {
    setEditingKey(row.key)
    setEditValue(String(row.passingScore))
  }

  const cancelEditPassing = () => {
    setEditingKey(null)
    setEditValue('')
  }

  const savePassing = async (row) => {
    const value = Number(editValue)
    if (Number.isNaN(value) || value < 0 || value > 20) {
      showToast('La note de validation doit être entre 0 et 20', 'warning')
      return
    }
    if (!row.courseId) {
      showToast('Impossible d\'enregistrer : ECUE introuvable', 'danger')
      return
    }
    setSavingPass(true)
    try {
      if (row.hasCourse) {
        await updateCourse(row.courseId, { passing_score: value })
      } else {
        await updateTeachingUnit(row.courseId, { passing_score: value })
      }
      setPassingOverrides((prev) => ({ ...prev, [row.courseId]: value }))
      showToast(`Note de validation de ${row.courseCode} mise à jour : ${value}/20`, 'success')
      setEditingKey(null)
      setEditValue('')
      reloadGrades()
    } catch (err) {
      showToast(err.message || 'Échec de la modification', 'danger')
    } finally {
      setSavingPass(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const yearId = form.academic_year || years?.[0]?.id
      await createExamSession({
        name: form.name,
        session_type: form.session_type,
        academic_year: yearId,
        start_date: new Date().toISOString().slice(0, 10),
        end_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
      })
      showToast('Session d\'examens créée', 'success')
      setShowSession(false)
      reloadSessions()
    } catch (err) {
      showToast(err.message || 'Création session impossible (vérifier champs API)', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleDelib = async (id, action) => {
    setBusy(`${id}-${action}`)
    try {
      if (action === 'run') await runDeliberation(id)
      if (action === 'validate') await validateDeliberation(id)
      if (action === 'publish') await publishDeliberation(id)
      showToast(`Délibération « ${translateDelibAction(action)} » réussie`, 'success')
      reloadDelib()
      reloadGrades()
    } catch (err) {
      showToast(err.message || 'Action impossible', 'danger')
    } finally {
      setBusy(null)
    }
  }

  if (loading && !gradesData) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  return (
    <>
      <PageHeader
        title="Notes & Validation"
        subtitle="Règles LMD : CC 40 % + CT 60 % — Seuil modifiable par ECUE — Compensation UE/Semestre"
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Validation ECUE INJS"
              filename="validation_ecue"
              headers={['Code ECUE', 'Libellé', 'Matricule', 'Étudiant', 'Note étudiant', 'Seuil', 'Statut']}
              rows={rows}
              resourcePath="/exams/grades"
            />
            <button type="button" className="btn btn-injs-primary" onClick={() => setShowSession(true)}>
              + Session d&apos;examens
            </button>
          </div>
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{counts.total}</div>
            <div className="small text-muted">Validations ECUE</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-success">{counts.valid}</div>
            <div className="small text-muted">ECUE validés</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-danger">{counts.invalid}</div>
            <div className="small text-muted">ECUE invalidés</div>
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
          <span className="small text-muted me-1">Statut :</span>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === '' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('')}
          >
            Tous ({counts.total})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'valid' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('valid')}
          >
            Validés <span className="opacity-75">({counts.valid})</span>
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'invalid' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('invalid')}
          >
            Invalidés <span className="opacity-75">({counts.invalid})</span>
          </button>
          <button
            type="button"
            className={`btn btn-sm ${statusFilter === 'pending' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setStatusAndReset('pending')}
          >
            Non notés <span className="opacity-75">({counts.pending})</span>
          </button>
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-5">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="ECUE, matricule, étudiant…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-4">
            <label className="form-label small mb-1">Statut</label>
            <select
              className="form-select"
              value={statusFilter}
              onChange={(ev) => setStatusAndReset(ev.target.value)}
            >
              <option value="">Tous</option>
              <option value="valid">Validés</option>
              <option value="invalid">Invalidés</option>
              <option value="pending">Non notés</option>
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

      <div className="row g-3 mb-4">
        <div className="col-lg-5">
          <div className="card-injs p-3 h-100">
            <h6 className="fw-bold mb-2">Sessions d&apos;examens ({counts.sessions})</h6>
            {(sessions || []).length === 0 ? (
              <p className="text-muted small mb-0">Aucune session — créez-en une.</p>
            ) : (sessions || []).slice(0, 5).map((s) => (
              <div key={s.id} className="d-flex justify-content-between align-items-center py-2 border-bottom">
                <span className="small fw-semibold text-truncate me-2">{s.name || s.id}</span>
                <div className="d-flex align-items-center gap-1 flex-shrink-0">
                  <span className="badge-injs">{translateSessionType(s.session_type)}</span>
                  <StatusBadge statut={s.status || 'ouverte'} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="col-lg-7">
          <div className="card-injs p-3 h-100">
            <h6 className="fw-bold mb-2">Délibérations ({counts.deliberations})</h6>
            {(deliberations || []).length === 0 ? (
              <p className="text-muted small mb-0">
                Aucune délibération en base. Créez une délibération (admin / API) puis utilisez Lancer / Valider / Publier.
              </p>
            ) : (
              <div className="table-responsive">
                <table className="table table-sm mb-0 align-middle">
                  <thead>
                    <tr><th>Libellé</th><th>Statut</th><th className="text-end">Actions</th></tr>
                  </thead>
                  <tbody>
                    {(deliberations || []).map((d) => (
                      <tr key={d.id}>
                        <td className="small">{d.name || d.exam_session_name || d.id?.slice?.(0, 8)}</td>
                        <td><StatusBadge statut={d.status || '—'} /></td>
                        <td className="text-end widget-actions">
                          <button type="button" className="btn btn-sm btn-outline-primary" disabled={!!busy} onClick={() => handleDelib(d.id, 'run')}>Lancer</button>
                          <button type="button" className="btn btn-sm btn-outline-success" disabled={!!busy} onClick={() => handleDelib(d.id, 'validate')}>Valider</button>
                          <button type="button" className="btn btn-sm btn-injs-primary" disabled={!!busy} onClick={() => handleDelib(d.id, 'publish')}>Publier</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
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
                    <th>ECUE</th>
                    <th>Étudiant</th>
                    <th>Note</th>
                    <th>Seuil</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((e) => (
                    <tr key={e.key}>
                      <td>
                        <code className="small">{e.courseCode}</code>
                        <div className="small text-muted">{e.courseName}</div>
                      </td>
                      <td>
                        <div className="fw-semibold">{e.studentName}</div>
                        <code className="small">{e.matricule}</code>
                      </td>
                      <td className="fw-bold">{e.studentScore != null ? `${e.studentScore}/20` : '—'}</td>
                      <td>
                        <EcuePassingEditor
                          row={e}
                          isEditing={editingKey === e.key}
                          editValue={editValue}
                          setEditValue={setEditValue}
                          savingPass={savingPass}
                          onStart={startEditPassing}
                          onSave={savePassing}
                          onCancel={cancelEditPassing}
                        />
                      </td>
                      <td>
                        <span className={`grade-badge ${e.statusKey === 'pending' ? 'grade-pending' : e.validated ? 'grade-valid' : 'grade-fail'}`}>
                          {e.statusLabel}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {!pageItems.length && (
                    <tr>
                      <td colSpan={5} className="text-center text-muted py-4">Aucun ECUE trouvé</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {pageItems.map((e) => (
                  <div key={e.key} className="col-md-6 col-xl-4">
                    <div className={`ecue-validation-card h-100 ${e.validated ? 'is-valid' : e.studentScore == null ? 'is-pending' : 'is-invalid'}`}>
                      <div className="ecue-validation-head">
                        <code className="ecue-validation-code">{e.courseCode}</code>
                        <span className="ecue-validation-label">{e.courseName}</span>
                      </div>
                      <div className="ecue-validation-student small text-muted mb-2">
                        {e.matricule} — {e.studentName}
                      </div>
                      <div className="ecue-validation-scores">
                        <div>
                          <span className="ecue-score-caption">Note étudiant</span>
                          <strong>{e.studentScore != null ? `${e.studentScore}/20` : '—'}</strong>
                        </div>
                        <div>
                          <span className="ecue-score-caption">Note de validation</span>
                          <div className="mt-1">
                            <EcuePassingEditor
                              row={e}
                              isEditing={editingKey === e.key}
                              editValue={editValue}
                              setEditValue={setEditValue}
                              savingPass={savingPass}
                              onStart={startEditPassing}
                              onSave={savePassing}
                              onCancel={cancelEditPassing}
                            />
                          </div>
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className={`grade-badge ${e.statusKey === 'pending' ? 'grade-pending' : e.validated ? 'grade-valid' : 'grade-fail'}`}>
                          {e.statusLabel}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
                {!pageItems.length && (
                  <div className="col-12 text-center text-muted py-4">Aucun ECUE trouvé</div>
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
        show={showSession}
        onClose={() => setShowSession(false)}
        title="Ouvrir une session d'examens"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowSession(false)}>Annuler</button>
            <button type="submit" form="session-form" className="btn btn-injs-primary" disabled={saving}>{saving ? 'Création...' : 'Créer'}</button>
          </>
        }
      >
        <form id="session-form" onSubmit={handleSubmit}>
          <div className="row g-3">
            <div className="col-12">
              <label className="form-label">Libellé</label>
              <input className="form-control" required value={form.name} onChange={(ev) => setForm({ ...form, name: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Type</label>
              <select className="form-select" value={form.session_type} onChange={(ev) => setForm({ ...form, session_type: ev.target.value })}>
                <option value="normal">Normale</option>
                <option value="retake">Rattrapage</option>
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Année académique</label>
              <select className="form-select" value={form.academic_year} onChange={(ev) => setForm({ ...form, academic_year: ev.target.value })}>
                <option value="">(année courante)</option>
                {(years || []).map((y) => <option key={y.id} value={y.id}>{y.name || y.label}</option>)}
              </select>
            </div>
          </div>
        </form>
      </Modal>
    </>
  )
}
