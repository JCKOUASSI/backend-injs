import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  FiUsers, FiUserCheck, FiBookOpen, FiTrendingUp, FiDollarSign,
  FiClipboard, FiAward, FiCheckSquare, FiBarChart2, FiMap,
} from 'react-icons/fi'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend } from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import ExportButtons from '../../components/common/ExportButtons'
import Modal from '../../components/common/Modal'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchAnalytics } from '../../api/reports'
import { enrollStudent, fetchStudents } from '../../api/students'
import { fetchPrograms, fetchSpecializations } from '../../api/academics'
import { fetchStudentFees } from '../../api/finance'
import { fetchGrades, fetchDeliberations, runDeliberation, validateDeliberation, publishDeliberation } from '../../api/exams'
import { fetchAttendanceDashboardStats } from '../../api/faculty'
import { INSTITUTION } from '../../data/mockData'
import { StatusBadge } from '../../utils/statusBadge'
import { translateDelibAction } from '../../utils/labels'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend)

export default function AdminDashboard() {
  const { showToast } = useToast()
  const { data: analytics, loading, error, reload } = useFetch(() => fetchAnalytics())
  const { data: studentsData } = useFetch(() => fetchStudents({ page_size: 50 }))
  const { data: programs } = useFetch(() => fetchPrograms())
  const { data: specializations } = useFetch(() => fetchSpecializations())
  const { data: feesData } = useFetch(() => fetchStudentFees())
  const { data: gradesData } = useFetch(() => fetchGrades())
  const { data: deliberations } = useFetch(() => fetchDeliberations())
  const { data: badgeStats } = useFetch(() => fetchAttendanceDashboardStats(), [])

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ nom: '', prenom: '', niveau: 'L1' })
  const [saving, setSaving] = useState(false)
  const [delibBusy, setDelibBusy] = useState(null)

  const students = studentsData?.results || []
  const fees = feesData?.results || []
  const grades = gradesData?.results || []

  const specialitesData = useMemo(() => {
    const list = (specializations || []).slice(0, 6)
    const finalLabels = list.length ? list.map((s) => s.code || s.name) : ['APA', 'EM', 'ES', 'MS']
    const data = list.length
      ? list.map((sp) => students.filter((s) =>
        s.raw?.specialization?.id === sp.id || s.raw?.specialization?.code === sp.code,
      ).length)
      : finalLabels.map(() => 0)
    return {
      labels: finalLabels,
      datasets: [{
        data,
        backgroundColor: ['#3349A1', '#5B6FC7', '#283D85', '#1A1F3D', '#7B8FD4', '#4A5FBD'],
      }],
    }
  }, [specializations, students])

  const inscriptionsData = useMemo(() => {
    const byNiveau = ['L1', 'L2', 'L3', 'M1', 'M2']
    return {
      labels: byNiveau,
      datasets: [{
        label: 'Étudiants par niveau',
        data: byNiveau.map((n) => students.filter((s) => s.niveau === n).length),
        backgroundColor: 'rgba(51, 73, 161, 0.75)',
        borderRadius: 6,
      }],
    }
  }, [students])

  const exportRows = students.map((s) => [s.id, s.nom, s.prenom, s.niveau, s.specialite, s.statut])
  const feeRows = fees.map((f) => [
    f.student_matricule || f.student || '—',
    f.fee_type_name || f.fee_type || '—',
    f.amount_due ?? f.amount ?? '—',
    f.status || '—',
  ])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.nom.trim() || !form.prenom.trim()) {
      showToast('Veuillez remplir le nom et le prénom', 'warning')
      return
    }
    setSaving(true)
    try {
      const created = await enrollStudent({
        nom: form.nom,
        prenom: form.prenom,
        niveau: form.niveau,
        specialite: 'Tronc commun',
        semestre: form.niveau === 'L1' ? 1 : form.niveau === 'L2' ? 3 : 5,
      })
      showToast(`Inscription réussie — matricule ${created.id}`, 'success')
      setShowForm(false)
      setForm({ nom: '', prenom: '', niveau: 'L1' })
      reload?.()
    } catch (err) {
      showToast(err.message || 'Erreur lors de l\'inscription', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleDelib = async (id, action) => {
    setDelibBusy(`${id}-${action}`)
    try {
      if (action === 'run') await runDeliberation(id)
      if (action === 'validate') await validateDeliberation(id)
      if (action === 'publish') await publishDeliberation(id)
      showToast(`Délibération : « ${translateDelibAction(action)} » réussie`, 'success')
    } catch (err) {
      showToast(err.message || 'Action délibération impossible', 'danger')
    } finally {
      setDelibBusy(null)
    }
  }

  const tauxReussite = analytics?.passing_rates?.[0]?.rate
    ? `${Math.round(analytics.passing_rates[0].rate * 100)}%`
    : '—'

  if (loading) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  return (
    <>
      <PageHeader
        title="Tableau de bord — Administration"
        subtitle={`${INSTITUTION.ufr} | Année académique ${INSTITUTION.academicYear}`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Liste étudiants INJS"
              filename="injs_etudiants"
              headers={['Matricule', 'Nom', 'Prénom', 'Niveau', 'Spécialité', 'Statut']}
              rows={exportRows}
              resourcePath="/students"
            />
            <button type="button" className="btn btn-injs-primary" onClick={() => setShowForm(true)}>+ Nouvelle inscription</button>
          </div>
        }
      />

      {error && <div className="alert alert-warning glass">Statistiques API indisponibles — {error}</div>}

      <div className="row g-3 mb-4">
        {[
          { to: '/admin/etudiants', icon: FiUsers, label: 'Étudiants' },
          { to: '/admin/finances', icon: FiDollarSign, label: 'Finances' },
          { to: '/admin/notes', icon: FiAward, label: 'Notes & Jury' },
          { to: '/admin/ue', icon: FiClipboard, label: 'UE / ECUE' },
          { to: '/admin/salles', icon: FiMap, label: 'Salles' },
          { to: '/admin/presences', icon: FiCheckSquare, label: 'Présences' },
          { to: '/admin/rapports', icon: FiBarChart2, label: 'Rapports' },
          { to: '/admin/formations', icon: FiBookOpen, label: 'Formations' },
          { to: '/admin/admissions', icon: FiUserCheck, label: 'Admissions' },
        ].map((a) => (
          <div key={a.to} className="col-6 col-md-3 col-xl-3">
            <Link to={a.to} className="quick-action-btn w-100 justify-content-center">
              <a.icon /> {a.label}
            </Link>
          </div>
        ))}
      </div>

      <div className="row g-4 mb-4">
        <div className="col-md-6 col-xl-3">
          <StatCard icon={FiUsers} label="Étudiants inscrits" value={(analytics?.total_students ?? students.length).toLocaleString()} color="green" />
        </div>
        <div className="col-md-6 col-xl-3">
          <StatCard icon={FiUserCheck} label="Professeurs & encadreurs" value={analytics?.total_teachers || 0} color="blue" />
        </div>
        <div className="col-md-6 col-xl-3">
          <StatCard icon={FiCheckSquare} label={`Présents aujourd'hui`} value={badgeStats?.present ?? '—'} color="orange" />
        </div>
        <div className="col-md-6 col-xl-3">
          <StatCard icon={FiTrendingUp} label="Taux présence (jour)" value={badgeStats?.attendance_rate != null ? `${badgeStats.attendance_rate}%` : '—'} color="gold" />
        </div>
      </div>

      <div className="card-injs p-4 mb-4">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <h5 className="fw-bold mb-0">Présences du jour</h5>
          <Link to="/admin/presences" className="btn btn-sm btn-injs-primary">Ouvrir les présences</Link>
        </div>
        <div className="row g-3 mb-2">
          <div className="col-md-3 small"><strong>{badgeStats?.sessions_open ?? 0}</strong> séances ouvertes</div>
          <div className="col-md-3 small"><strong>{badgeStats?.teachers_badged ?? 0}</strong> formateurs badgés</div>
          <div className="col-md-3 small"><strong>{badgeStats?.absent ?? 0}</strong> absents (roster)</div>
          <div className="col-md-3 small"><strong>{badgeStats?.late ?? 0}</strong> retards</div>
        </div>
        {(badgeStats?.upcoming_sessions || []).slice(0, 5).map((s) => (
          <div key={s.id} className="d-flex justify-content-between py-2 border-bottom small">
            <span>
              <code className="me-1">{s.course_code}</code>
              {s.course_name} — {s.start_time}–{s.end_time}
              {s.room_code && ` · ${s.room_code}`}
            </span>
            <span className="text-muted">{s.present_count} badgé(e)s</span>
          </div>
        ))}
        {!badgeStats?.upcoming_sessions?.length && (
          <p className="text-muted small mb-0">Aucune séance ouverte aujourd&apos;hui.</p>
        )}
        {(badgeStats?.present_students || []).length > 0 && (
          <>
            <h6 className="fw-bold mt-4 mb-2">Étudiants ayant badgé aujourd&apos;hui</h6>
            <div style={{ maxHeight: 220, overflow: 'auto' }}>
              {badgeStats.present_students.slice(0, 40).map((a) => (
                <div key={a.attendance_id} className="d-flex justify-content-between py-1 border-bottom small">
                  <span>
                    <code className="me-1">{a.matricule}</code>
                    {a.name}
                    <span className="text-muted ms-2">{a.course_code} · {a.start_time}</span>
                  </span>
                  <span className="badge bg-success">{a.status_label}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="row g-4 mb-4">
        <div className="col-lg-8">
          <div className="card-injs p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="fw-bold mb-0">Répartition des étudiants par niveau</h5>
              <ExportButtons
                title="Étudiants par niveau"
                filename="injs_niveaux"
                headers={['Niveau', 'Effectif']}
                rows={inscriptionsData.labels.map((l, i) => [l, inscriptionsData.datasets[0].data[i]])}
              />
            </div>
            <Bar data={inscriptionsData} options={{ responsive: true, plugins: { legend: { display: false } } }} height={80} />
          </div>
        </div>
        <div className="col-lg-4">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Spécialités STAPS</h5>
            <Doughnut data={specialitesData} options={{ responsive: true }} />
            <p className="small text-muted mt-2 mb-0">{(programs || []).length} filière(s) active(s)</p>
          </div>
        </div>
      </div>

      <div className="row g-4 mb-4">
        <div className="col-lg-6">
          <div className="card-injs p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="fw-bold mb-0">Finance — Frais étudiants</h5>
              <ExportButtons
                title="Frais étudiants"
                filename="injs_frais"
                headers={['Étudiant', 'Type', 'Montant', 'Statut']}
                rows={feeRows}
                resourcePath="/finance/student-fees"
              />
            </div>
            <div className="d-flex justify-content-between mb-2"><span>En attente</span><strong>{analytics?.pending_fees ?? fees.filter((f) => f.status !== 'paid').length}</strong></div>
            <div className="d-flex justify-content-between mb-2"><span>Payés</span><strong className="text-success">{analytics?.paid_fees ?? fees.filter((f) => f.status === 'paid').length}</strong></div>
            {analytics?.average_grade && (
              <div className="d-flex justify-content-between mb-2"><span>Moyenne générale</span><strong>{analytics.average_grade}/20</strong></div>
            )}
            <div className="d-flex justify-content-between"><span>Notes en base</span><strong>{grades.length}</strong></div>
            <Link to="/admin/finances" className="btn btn-sm btn-injs-primary mt-3">Ouvrir Finances</Link>
          </div>
        </div>
        <div className="col-lg-6">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Délibérations (Jury)</h5>
            {(deliberations || []).length === 0 ? (
              <p className="text-muted mb-0">Aucune délibération — créez-en une via l’API / admin notes, puis lancer / valider / publier ici.</p>
            ) : (
              <div className="table-responsive">
                <table className="table table-sm mb-0">
                  <thead><tr><th>Session</th><th>Statut</th><th>Actions</th></tr></thead>
                  <tbody>
                    {(deliberations || []).slice(0, 5).map((d) => (
                      <tr key={d.id}>
                        <td>{d.exam_session_name || d.name || d.id?.slice?.(0, 8)}</td>
                        <td><StatusBadge statut={d.status || '—'} /></td>
                        <td className="widget-actions">
                          <button type="button" className="btn btn-sm btn-outline-primary" disabled={!!delibBusy} onClick={() => handleDelib(d.id, 'run')}>Lancer</button>
                          <button type="button" className="btn btn-sm btn-outline-success" disabled={!!delibBusy} onClick={() => handleDelib(d.id, 'validate')}>Valider</button>
                          <button type="button" className="btn btn-sm btn-injs-primary" disabled={!!delibBusy} onClick={() => handleDelib(d.id, 'publish')}>Publier</button>
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

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Nouvelle inscription"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="inscription-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Inscription...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="inscription-form" onSubmit={handleSubmit}>
          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label">Nom</label>
              <input className="form-control" required value={form.nom} onChange={(ev) => setForm({ ...form, nom: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Prénom</label>
              <input className="form-control" required value={form.prenom} onChange={(ev) => setForm({ ...form, prenom: ev.target.value })} />
            </div>
            <div className="col-12">
              <label className="form-label">Niveau</label>
              <select className="form-select" value={form.niveau} onChange={(ev) => setForm({ ...form, niveau: ev.target.value })}>
                {['L1', 'L2', 'L3'].map((n) => <option key={n}>{n}</option>)}
              </select>
            </div>
          </div>
        </form>
      </Modal>
    </>
  )
}
