import { useMemo, useState } from 'react'
import { FiEdit2, FiCheck, FiX } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import Modal from '../../components/common/Modal'
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
      statusLabel: studentScore == null ? 'Non noté' : validated ? 'ECUE validé' : 'ECUE invalidé',
    }
  })
}

export default function AdminGrades() {
  const { showToast } = useToast()
  const { data: gradesData, loading, reload: reloadGrades } = useFetch(() => fetchGrades())
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

  const grades = gradesData?.results || []
  const ecueRows = useMemo(
    () => buildEcueValidations(grades, passingOverrides),
    [grades, passingOverrides],
  )

  const rows = ecueRows.map((e) => [
    e.courseCode,
    e.courseName,
    e.matricule,
    e.studentName,
    e.studentScore ?? '—',
    e.passingScore,
    e.statusLabel,
  ])

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

  if (loading) return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>

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

      <div className="row g-4 mb-4">
        <div className="col-md-4"><div className="card-injs p-4"><h6>Validation ECUE</h6><p className="small text-muted mb-0">Moyenne CC+CT ≥ note de validation (modifiable)</p></div></div>
        <div className="col-md-4"><div className="card-injs p-4"><h6>Validation UE</h6><p className="small text-muted mb-0">Tous ECUE ≥ seuil ou compensation (aucun &lt; 8)</p></div></div>
        <div className="col-md-4"><div className="card-injs p-4"><h6>Validation Semestre</h6><p className="small text-muted mb-0">Compensation inter-UE si moyenne ≥ 10</p></div></div>
      </div>

      <div className="row g-4 mb-4">
        <div className="col-lg-5">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Sessions d&apos;examens</h5>
            {(sessions || []).length === 0 ? (
              <p className="text-muted">Aucune session — créez-en une.</p>
            ) : (sessions || []).map((s) => (
              <div key={s.id} className="d-flex justify-content-between py-2 border-bottom">
                <span>{s.name || s.id}</span>
                <span className="badge-injs me-2">{translateSessionType(s.session_type)}</span>
                <StatusBadge statut={s.status || 'ouverte'} />
              </div>
            ))}
          </div>
        </div>
        <div className="col-lg-7">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Délibérations</h5>
            {(deliberations || []).length === 0 ? (
              <p className="text-muted mb-0">Aucune délibération en base. Créez une délibération (admin / API) puis utilisez Lancer / Valider / Publier.</p>
            ) : (
              <table className="table table-sm mb-0">
                <thead><tr><th>Libellé</th><th>Statut</th><th /></tr></thead>
                <tbody>
                  {(deliberations || []).map((d) => (
                    <tr key={d.id}>
                      <td>{d.name || d.exam_session_name || d.id?.slice?.(0, 8)}</td>
                      <td><StatusBadge statut={d.status || '—'} /></td>
                      <td className="widget-actions">
                        <button type="button" className="btn btn-sm btn-outline-primary" disabled={!!busy} onClick={() => handleDelib(d.id, 'run')}>Lancer</button>
                        <button type="button" className="btn btn-sm btn-outline-success" disabled={!!busy} onClick={() => handleDelib(d.id, 'validate')}>Valider</button>
                        <button type="button" className="btn btn-sm btn-injs-primary" disabled={!!busy} onClick={() => handleDelib(d.id, 'publish')}>Publier</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      <div className="card-injs overflow-hidden">
        <div className="p-3 border-bottom">
          <h5 className="fw-bold mb-0">Condition(s) de validation des ECUES</h5>
          <p className="small text-muted mb-0 mt-1">
            Note étudiant (CC 40 % + CT 60 %) comparée au seuil de validation ECUE (modifiable).
          </p>
        </div>

        {!ecueRows.length ? (
          <div className="p-4 text-muted text-center">Aucun ECUE noté pour le moment.</div>
        ) : (
          <div className="p-3">
            <div className="row g-3">
              {ecueRows.map((e) => {
                const isEditing = editingKey === e.key
                return (
                  <div key={e.key} className="col-md-6 col-xl-4">
                    <div className={`ecue-validation-card ${e.validated ? 'is-valid' : e.studentScore == null ? 'is-pending' : 'is-invalid'}`}>
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
                          {isEditing ? (
                            <div className="d-flex align-items-center gap-1 mt-1">
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
                                onClick={() => savePassing(e)}
                              >
                                <FiCheck size={14} />
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary btn-icon-action"
                                title="Annuler"
                                aria-label="Annuler"
                                disabled={savingPass}
                                onClick={cancelEditPassing}
                              >
                                <FiX size={14} />
                              </button>
                            </div>
                          ) : (
                            <div className="d-flex align-items-center gap-2">
                              <strong>{e.passingScore}/20</strong>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-primary btn-icon-action"
                                title="Modifier la note de validation"
                                aria-label="Modifier la note de validation"
                                onClick={() => startEditPassing(e)}
                              >
                                <FiEdit2 size={14} />
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className={`grade-badge ${e.studentScore == null ? 'grade-pending' : e.validated ? 'grade-valid' : 'grade-fail'}`}>
                          {e.statusLabel}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
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
