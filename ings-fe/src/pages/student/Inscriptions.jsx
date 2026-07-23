import PageHeader from '../../components/common/PageHeader'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchMyEnrollments } from '../../api/students'
import { semestreIdsForNiveau } from '../../utils/studentLevel'
import { INSTITUTION } from '../../data/mockData'

const TYPE_LABELS = {
  administrative: 'Inscription administrative',
  pedagogical: 'Inscription pédagogique',
  pre_registration: 'Préinscription',
}

const STATUS_LABELS = {
  approved: 'Validée',
  pending: 'En attente',
  rejected: 'Rejetée',
  cancelled: 'Annulée',
}

export default function StudentInscriptions() {
  const { user } = useAuth()
  const semestresNiveau = semestreIdsForNiveau(user?.niveau || 'L1')

  const { data: enrollments, loading, error } = useFetch(
    () => (user?.studentId ? fetchMyEnrollments(user.studentId) : Promise.resolve([])),
    [user?.studentId],
  )

  const pedagogicalSemestres = semestresNiveau.filter((s) => s <= (user?.semestre || 1))
  const nextSemestre = semestresNiveau.find((s) => s > (user?.semestre || 1))

  return (
    <>
      <PageHeader
        title="Inscriptions"
        subtitle={`${user?.niveau} — Année académique ${INSTITUTION.academicYear}`}
      />

      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}

      {(enrollments || []).map((e) => (
        <div key={e.id} className="card-injs p-4 mb-3">
          <h6 className="fw-bold">
            {TYPE_LABELS[e.enrollment_type] || e.enrollment_type}
            {' — '}
            <span className={e.status === 'approved' ? 'text-success' : ''}>
              {STATUS_LABELS[e.status] || e.status}
            </span>
          </h6>
          <p className="small text-muted mb-0">
            Matricule : {user?.matricule || user?.id} — {user?.niveau} {user?.mention}
          </p>
        </div>
      ))}

      {pedagogicalSemestres.map((s) => (
        <div key={s} className="card-injs p-4 mb-3">
          <h6 className="fw-bold">
            Inscription pédagogique S{s}
            {s === user?.semestre && <span className="grade-badge grade-pending ms-2">En cours</span>}
            {s < user?.semestre && <span className="grade-badge grade-valid ms-2">Validée</span>}
          </h6>
          {s >= 4 && user?.specialite && (
            <p className="small mb-0">Spécialité : {user.specialite}</p>
          )}
        </div>
      ))}

      {nextSemestre && (
        <div className="card-injs p-4">
          <h6 className="fw-bold">Réinscription S{nextSemestre} (à venir)</h6>
          <p className="small text-muted">Disponible à la fin du semestre {user?.semestre}</p>
          <button className="btn btn-outline-secondary btn-sm" disabled>Non disponible</button>
        </div>
      )}
    </>
  )
}
