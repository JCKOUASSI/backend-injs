import { useMemo, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import Modal from '../../components/common/Modal'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchEvaluations, fetchGrades, createGrade } from '../../api/exams'
import { fetchStudents } from '../../api/students'
import { StatusBadge, getStatusBadgeClass } from '../../utils/statusBadge'
import { translateStatus } from '../../utils/labels'

const GRADE_FILTERS = [
  { id: 'all', label: 'Toutes les notes' },
  { id: 'valid', label: 'Notes validées' },
  { id: 'invalid', label: 'Notes non validées' },
]

function isValidatedGrade(g) {
  const s = String(g.statut || '').toLowerCase()
  if (s.includes('non valid')) return false
  if (s.includes('valid')) return true
  if (g.moyenne != null && g.moyenne !== '—') return Number(g.moyenne) >= 10
  return getStatusBadgeClass(g.statut) === 'grade-valid'
}

function typeLabel(type) {
  const t = String(type || '').toLowerCase()
  if (t === 'cc' || t.includes('continu')) return 'CC'
  if (t === 'ct' || t.includes('terminal')) return 'CT'
  return translateStatus(type) || type || '—'
}

export default function ProfEvaluations() {
  const { showToast } = useToast()
  const { data: evaluations, loading, reload } = useFetch(() => fetchEvaluations())
  const { data: gradesData, reload: reloadGrades } = useFetch(() => fetchGrades())
  const { data: studentsData } = useFetch(() => fetchStudents({ page_size: 50 }))

  const [active, setActive] = useState(null)
  const [notes, setNotes] = useState({})
  const [saving, setSaving] = useState(false)
  const [gradeFilter, setGradeFilter] = useState('all')

  const students = studentsData?.results || []
  const grades = gradesData?.results || []

  const filteredGrades = useMemo(() => {
    if (gradeFilter === 'valid') return grades.filter(isValidatedGrade)
    if (gradeFilter === 'invalid') return grades.filter((g) => !isValidatedGrade(g))
    return grades
  }, [grades, gradeFilter])

  const rows = useMemo(
    () => filteredGrades.map((g) => [g.label, g.ue, g.moyenne ?? '—', g.statut]),
    [filteredGrades],
  )

  const openGrille = (evaluation) => {
    setActive(evaluation)
    setNotes({})
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!active) return
    setSaving(true)
    try {
      const entries = Object.entries(notes).filter(([, v]) => v !== '' && v != null)
      for (const [studentId, score] of entries) {
        await createGrade({
          evaluation: active.id,
          student: studentId,
          score: Number(score),
        })
      }
      showToast(`${entries.length} note(s) enregistrée(s)`, 'success')
      setActive(null)
      reloadGrades()
      reload()
    } catch (err) {
      showToast(err.message || 'Échec saisie (vérifier droits / champs API)', 'danger')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>

  return (
    <>
      <PageHeader
        title="Évaluations CC / CT"
        subtitle="Contrôle Continu (40%) + Contrôle Terminal (60%) — saisie API"
        action={
          <ExportButtons
            title="Notes"
            filename="notes_evaluations"
            headers={['Évaluation', 'UE', 'Note', 'Statut']}
            rows={rows}
            resourcePath="/exams/grades"
          />
        }
      />

      {!(evaluations || []).length ? (
        <div className="card-injs p-4 text-muted">
          Aucune évaluation en base. Les évaluations de démo (CC/CT) apparaîtront ici après le chargement des données de démonstration.
        </div>
      ) : (
        <div className="row row-cols-2 row-cols-md-3 row-cols-xl-5 g-3 mb-4">
          {(evaluations || []).map((s) => (
            <div key={s.id} className="col">
              <div className="card-injs eval-card h-100 p-3 d-flex flex-column">
                <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
                  <span className="badge-injs">{typeLabel(s.evaluation_type || s.type)}</span>
                  <small className="text-muted">/{s.max_score || 20}</small>
                </div>
                <h6 className="fw-bold eval-card-title mb-2">
                  {s.name || s.title || s.code || 'Évaluation'}
                </h6>
                <p className="text-muted small mb-3 flex-grow-1">
                  {s.code ? <code className="me-1">{s.code}</code> : null}
                  {s.course_name || s.teaching_unit_code || 'UE / ECUE'}
                </p>
                <button
                  type="button"
                  className="btn btn-sm btn-injs-secondary w-100 mt-auto"
                  onClick={() => openGrille(s)}
                >
                  Grille
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card-injs overflow-hidden mt-2">
        <div className="p-3 border-bottom d-flex flex-wrap justify-content-between align-items-center gap-2">
          <strong>Notes déjà saisies</strong>
          <div className="btn-group" role="group" aria-label="Filtrer les notes">
            {GRADE_FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                className={`btn btn-sm ${gradeFilter === f.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setGradeFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div className="table-responsive">
          <table className="table table-injs mb-0">
            <thead>
              <tr>
                <th>Évaluation</th>
                <th>UE</th>
                <th>Note</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {filteredGrades.map((g) => (
                <tr key={g.id}>
                  <td>{g.label}</td>
                  <td>{g.ue}</td>
                  <td>{g.moyenne ?? '—'}</td>
                  <td><StatusBadge statut={g.statut} /></td>
                </tr>
              ))}
              {!filteredGrades.length && (
                <tr>
                  <td colSpan={4} className="text-center text-muted py-3">
                    {grades.length
                      ? 'Aucune note pour ce filtre'
                      : 'Aucune note'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {filteredGrades.length > 0 && (
          <div className="px-3 py-2 border-top small text-muted">
            {filteredGrades.length} note(s) affichée(s)
            {gradeFilter !== 'all' ? ` sur ${grades.length}` : ''}
          </div>
        )}
      </div>

      <Modal
        show={!!active}
        onClose={() => setActive(null)}
        title={`Grille — ${active?.name || active?.title || ''}`}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setActive(null)}>Annuler</button>
            <button type="submit" form="notes-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer les notes'}
            </button>
          </>
        }
      >
        <form id="notes-form" onSubmit={handleSubmit}>
          <p className="text-muted small mb-3">Saisissez une note /20 pour chaque étudiant.</p>
          {students.slice(0, 15).map((st) => (
            <div key={st.uuid || st.id} className="row g-2 mb-2 align-items-center">
              <div className="col-6">
                <span className="fw-semibold">{st.nom} {st.prenom}</span>
                <br />
                <small className="text-muted">{st.id}</small>
              </div>
              <div className="col-6">
                <input
                  type="number"
                  min="0"
                  max="20"
                  step="0.25"
                  className="form-control form-control-sm"
                  placeholder="Note /20"
                  value={notes[st.uuid] || ''}
                  onChange={(ev) => setNotes({ ...notes, [st.uuid]: ev.target.value })}
                />
              </div>
            </div>
          ))}
          {!students.length && <p className="text-danger">Aucun étudiant chargé.</p>}
        </form>
      </Modal>
    </>
  )
}
