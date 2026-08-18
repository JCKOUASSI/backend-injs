import { Link } from 'react-router-dom'
import { FiAward, FiBookOpen, FiBriefcase, FiCalendar, FiCreditCard, FiFileText, FiCheckSquare } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import ExportButtons from '../../components/common/ExportButtons'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchTeachingUnits } from '../../api/academics'
import { fetchGrades } from '../../api/exams'
import { fetchSchedules, fetchAttendanceDashboardStats } from '../../api/faculty'
import { fetchStudentFees } from '../../api/finance'
import { semestreIdsForNiveau } from '../../utils/studentLevel'
import { INSTITUTION } from '../../data/mockData'

const DAY_LABELS = { 0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi' }

export default function StudentDashboard() {
  const { user } = useAuth()
  const niveau = user?.niveau || 'L1'
  const semestresNiveau = semestreIdsForNiveau(niveau)
  const creditsTotal = user?.creditsTotal || 180
  const progress = user?.credits ? Math.round((user.credits / creditsTotal) * 100) : 0

  const { data: units } = useFetch(
    () => fetchTeachingUnits({ semester_number: user?.semestre || 1 }).then((r) => r.results),
    [user?.semestre],
  )
  const { data: gradesData } = useFetch(() => fetchGrades())
  const { data: schedules } = useFetch(() => fetchSchedules({ page_size: 50 }).catch(() => []))
  const { data: feesData } = useFetch(() => fetchStudentFees().catch(() => ({ results: [] })))
  const { data: badgeStats } = useFetch(() => fetchAttendanceDashboardStats(), [])

  const grades = gradesData?.results || []
  const scored = grades.filter((g) => g.moyenne != null)
  const moyenne = scored.length
    ? (scored.reduce((a, n) => a + Number(n.moyenne), 0) / scored.length).toFixed(2)
    : '—'
  const ueCount = units?.length || 0
  const fees = feesData?.results || []
  const pendingFees = fees.filter((f) => f.status !== 'paid')
  const edt = (schedules || []).slice(0, 6)

  const gradeRows = grades.map((g) => [g.label, g.ue, g.moyenne ?? '—', g.statut])

  return (
    <>
      <PageHeader
        title={`Bonjour, ${user?.name}`}
        subtitle={`${niveau} ${user?.mention || 'STAPS'} — ${user?.specialite || ''} | ${INSTITUTION.academicYear}`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Mes notes"
              filename="mes_notes"
              headers={['Évaluation', 'UE', 'Note', 'Statut']}
              rows={gradeRows}
            />
            <Link to="/etudiant/paiements" className="btn btn-injs-primary">Payer mes frais</Link>
          </div>
        }
      />

      <div className="card-injs p-4 mb-4">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
          <div>
            <h6 className="text-muted mb-1">Progression {niveau}</h6>
            <h3 className="fw-bold mb-0">{user?.credits || scored.length * 3 || 0} / {creditsTotal} ECTS</h3>
            <small className="text-muted">Semestre {user?.semestre} — {niveau} — Matricule {user?.matricule || user?.studentMatricule || '—'}</small>
          </div>
          <div className="semester-timeline">
            {semestresNiveau.map((s) => (
              <div
                key={s}
                className={`semester-dot ${s < user?.semestre ? 'completed' : s === user?.semestre ? 'current' : ''}`}
              >
                S{s}
              </div>
            ))}
          </div>
        </div>
        <div className="progress mt-3" style={{ height: 10 }}>
          <div className="progress-bar progress-bar-injs" style={{ width: `${progress || Math.min(100, scored.length * 8)}%` }} />
        </div>
      </div>

      <div className="row g-3 mb-4">
        {[
          { to: '/etudiant/notes', icon: FiAward, label: 'Notes & crédits' },
          { to: '/etudiant/documents', icon: FiFileText, label: 'Relevés PDF' },
          { to: '/etudiant/paiements', icon: FiCreditCard, label: 'Paiements' },
          { to: '/etudiant/emploi-du-temps', icon: FiCalendar, label: 'EDT' },
          { to: '/etudiant/presences', icon: FiCheckSquare, label: 'Présences' },
          { to: '/etudiant/inscriptions', icon: FiBookOpen, label: 'Inscriptions' },
        ].map((a) => (
          <div key={a.to} className="col-6 col-md-4 col-xl-2">
            <Link to={a.to} className="quick-action-btn w-100 justify-content-center"><a.icon /> {a.label}</Link>
          </div>
        ))}
      </div>

      <div className="row g-4 mb-4">
        <div className="col-md-3"><StatCard icon={FiAward} label="Moyenne générale" value={moyenne === '—' ? '—' : `${moyenne}/20`} color="green" /></div>
        <div className="col-md-3"><StatCard icon={FiBookOpen} label={`UE S${user?.semestre || 1}`} value={ueCount} color="blue" /></div>
        <div className="col-md-3"><StatCard icon={FiCheckSquare} label="Présences (jour)" value={(badgeStats?.my_today || []).filter((a) => a.status !== 'absent').length} color="orange" /></div>
        <div className="col-md-3"><StatCard icon={FiCalendar} label="Créneaux EDT" value={edt.length} color="gold" /></div>
      </div>

      <div className="card-injs p-4 mb-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Présences aujourd&apos;hui</h5>
          <Link to="/etudiant/presences" className="btn btn-sm btn-injs-primary">Pointer ma présence</Link>
        </div>
        {(badgeStats?.my_today || []).length === 0 ? (
          <p className="text-muted small mb-0">Aucune séance rosterée pour aujourd&apos;hui — scannez le QR en cours.</p>
        ) : (
          badgeStats.my_today.map((a, idx) => (
            <div key={`${a.course_code}-${idx}`} className="d-flex justify-content-between py-2 border-bottom small">
              <span>
                <strong>{a.course_code}</strong> — {a.course_name}
                <span className="text-muted ms-2">{a.start_time}</span>
              </span>
              <span className={`badge ${a.status === 'present' ? 'bg-success' : a.status === 'late' ? 'bg-warning text-dark' : 'bg-secondary'}`}>
                {a.status_label || a.status_display || a.status}
              </span>
            </div>
          ))
        )}
      </div>

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Emploi du temps</h5>
            {edt.length === 0 ? (
              <p className="text-muted mb-0">Aucun créneau API — consultez la page Emploi du temps.</p>
            ) : (
              edt.map((c) => (
                <div key={c.id} className="d-flex justify-content-between py-2 border-bottom">
                  <div>
                    <strong>{DAY_LABELS[c.day_of_week] || `Jour ${c.day_of_week}`}</strong>
                    <br /><small className="text-muted">{c.start_time} – {c.end_time} • {c.room_name || 'Salle'}</small>
                  </div>
                  <span className="badge-injs">Cours</span>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="col-lg-5">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Alertes & actions</h5>
            {pendingFees.length > 0 ? (
              <div className="alert alert-warning py-2">
                {pendingFees.length} frais non soldé(s) — <Link to="/etudiant/paiements">payer maintenant</Link>
              </div>
            ) : (
              <div className="alert alert-success py-2 mb-3">Aucun frais en attente détecté.</div>
            )}
            <Link to="/etudiant/documents" className="btn btn-sm btn-outline-primary me-2">Télécharger relevé</Link>
            <Link to="/etudiant/notes" className="btn btn-sm btn-injs-primary">Voir mes notes</Link>
          </div>
        </div>
      </div>
    </>
  )
}
