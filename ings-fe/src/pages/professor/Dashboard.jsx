import { Link } from 'react-router-dom'
import { FiBookOpen, FiUsers, FiCheckSquare, FiClock, FiFileText, FiAward } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import ExportButtons from '../../components/common/ExportButtons'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchMyTeacherProfile, fetchSchedules, fetchAttendanceDashboardStats } from '../../api/faculty'
import { fetchGrades, fetchEvaluations } from '../../api/exams'
import { fetchStudents } from '../../api/students'
import { apiGet } from '../../api/client'
import { INSTITUTION } from '../../data/mockData'
import { StatusBadge } from '../../utils/statusBadge'

const DAY_LABELS = { 0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi' }

export default function ProfDashboard() {
  const { user } = useAuth()
  const { data: teacher, loading: loadingTeacher } = useFetch(() => fetchMyTeacherProfile().catch(() => null))
  const { data: assignments } = useFetch(
    () => (teacher?.id
      ? apiGet('/faculty/assignments/', { teacher: teacher.id, page_size: 100 }).then((r) => r.results)
      : Promise.resolve([])),
    [teacher?.id],
  )
  const { data: schedules } = useFetch(
    () => fetchSchedules({ page_size: 200 }).catch(() => []),
    [],
  )
  const { data: gradesData } = useFetch(() => fetchGrades())
  const { data: evaluations } = useFetch(() => fetchEvaluations())
  const { data: studentsData } = useFetch(() => fetchStudents({ page_size: 100 }))
  const { data: badgeStats } = useFetch(() => fetchAttendanceDashboardStats(), [])

  const myAssignmentIds = new Set((assignments || []).map((a) => a.id))
  const mySchedules = (schedules || []).filter((s) => myAssignmentIds.has(s.assignment))
  const grades = gradesData?.results || []
  const students = studentsData?.results || []

  const exportRows = mySchedules.map((s) => [
    DAY_LABELS[s.day_of_week] || s.day_of_week,
    s.start_time,
    s.end_time,
    s.room_code ? `${s.room_code} — ${s.room_name || ''}` : (s.room_name || s.room || '—'),
    s.assignment,
  ])

  if (loadingTeacher) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  return (
    <>
      <PageHeader
        title={`Bonjour, ${user?.name}`}
        subtitle={`${user?.department || teacher?.department_name || 'Enseignement'} — ${INSTITUTION.academicYear}`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Emploi du temps enseignant"
              filename="injs_edt_prof"
              headers={['Jour', 'Début', 'Fin', 'Salle', 'Affectation']}
              rows={exportRows}
            />
            <Link to="/professeur/presence" className="btn btn-injs-primary">Ouvrir présences QR</Link>
          </div>
        }
      />

      <div className="row g-3 mb-4">
        {[
          { to: '/professeur/cours', icon: FiBookOpen, label: 'Mes cours' },
          { to: '/professeur/etudiants', icon: FiUsers, label: 'Étudiants' },
          { to: '/professeur/evaluations', icon: FiAward, label: 'Saisie notes' },
          { to: '/professeur/presence', icon: FiCheckSquare, label: 'Présences' },
          { to: '/professeur/documents', icon: FiFileText, label: 'Supports' },
        ].map((a) => (
          <div key={a.to} className="col-6 col-md-4 col-xl">
            <Link to={a.to} className="quick-action-btn w-100 justify-content-center"><a.icon /> {a.label}</Link>
          </div>
        ))}
      </div>

      <div className="row g-4 mb-4">
        <div className="col-md-3"><StatCard icon={FiBookOpen} label="Affectations / UE" value={(assignments || []).length} color="green" /></div>
        <div className="col-md-3"><StatCard icon={FiUsers} label="Étudiants (cohorte)" value={students.length} color="blue" /></div>
        <div className="col-md-3"><StatCard icon={FiCheckSquare} label="Présents (jour)" value={badgeStats?.present ?? '—'} color="orange" /></div>
        <div className="col-md-3"><StatCard icon={FiClock} label="Séances ouvertes" value={badgeStats?.sessions_open ?? 0} color="gold" /></div>
      </div>

      <div className="card-injs p-4 mb-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Badgeage — mes séances du jour</h5>
          <Link to="/professeur/presence" className="btn btn-sm btn-injs-primary">Présenter QR</Link>
        </div>
        {(badgeStats?.upcoming_sessions || []).length === 0 ? (
          <p className="text-muted small mb-0">Aucune séance ouverte aujourd&apos;hui.</p>
        ) : (
          badgeStats.upcoming_sessions.map((s) => (
            <div key={s.id} className="d-flex justify-content-between py-2 border-bottom small">
              <span>
                <code className="me-1">{s.course_code}</code>
                {s.start_time}–{s.end_time}
                {s.room_code && ` · ${s.room_code}`}
              </span>
              <span>
                {s.teacher_checked_in ? <span className="badge bg-success me-2">Badgé</span> : null}
                {s.present_count} badgé(e)s
              </span>
            </div>
          ))
        )}
        {(badgeStats?.present_students || []).length > 0 && (
          <>
            <h6 className="fw-bold mt-4 mb-2">Étudiants ayant badgé</h6>
            <div style={{ maxHeight: 220, overflow: 'auto' }}>
              {badgeStats.present_students.slice(0, 40).map((a) => (
                <div key={a.attendance_id} className="d-flex justify-content-between py-1 border-bottom small">
                  <span>
                    <code className="me-1">{a.matricule}</code>
                    {a.name}
                    <span className="text-muted ms-2">{a.course_code}</span>
                  </span>
                  <span className="badge bg-success">{a.status_label}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Prochains cours (API)</h5>
            {mySchedules.length === 0 ? (
              <p className="text-muted mb-0">Aucun créneau lié à vos affectations. Vérifiez les données de démo (Prof. Martin).</p>
            ) : (
              mySchedules.slice(0, 8).map((c) => (
                <div key={c.id} className="d-flex justify-content-between py-2 border-bottom">
                  <div>
                    <strong>{DAY_LABELS[c.day_of_week] || `Jour ${c.day_of_week}`}</strong>
                    <br />
                    <small className="text-muted">{c.start_time} – {c.end_time} — {c.room_code ? `${c.room_code} · ` : ''}{c.room_name || 'Salle'}</small>
                  </div>
                  <span className="badge-injs">EDT</span>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="col-lg-5">
          <div className="card-injs p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="fw-bold mb-0">Notes récentes</h5>
              <ExportButtons
                title="Notes"
                filename="injs_notes_prof"
                headers={['Évaluation', 'UE', 'Note', 'Statut']}
                rows={grades.slice(0, 50).map((g) => [g.label, g.ue, g.moyenne ?? '—', g.statut])}
                resourcePath="/exams/grades"
              />
            </div>
            {grades.slice(0, 6).map((g) => (
              <div key={g.id} className="d-flex justify-content-between align-items-center py-2 border-bottom gap-2">
                <span className="small">{g.label}</span>
                <div className="d-flex align-items-center gap-2">
                  <strong>{g.moyenne ?? '—'}</strong>
                  <StatusBadge statut={g.statut} />
                </div>
              </div>
            ))}
            {!grades.length && <p className="text-muted mb-0">Aucune note chargée.</p>}
            <Link to="/professeur/evaluations" className="btn btn-sm btn-injs-primary mt-3">Saisir / gérer notes</Link>
          </div>
        </div>
      </div>
    </>
  )
}
