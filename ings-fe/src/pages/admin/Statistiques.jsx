import { useMemo, useState } from 'react'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend } from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import { FiAlertTriangle, FiAward, FiBookOpen, FiCheckSquare, FiDollarSign, FiUsers } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import ExportButtons from '../../components/common/ExportButtons'
import { useFetch } from '../../hooks/useFetch'
import { fetchAcademicStatistics } from '../../api/reports'
import { fetchAcademicYears, fetchDepartments, fetchPrograms } from '../../api/academics'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend)

const TABS = [
  { id: 'overview', label: 'Vue d’ensemble' },
  { id: 'pedagogy', label: 'Pédagogie LMD' },
  { id: 'admin', label: 'Administratif' },
  { id: 'alerts', label: 'Alertes' },
]

const ALERT_CLASS = {
  ok: 'bg-success-subtle text-success',
  avertissement: 'bg-warning-subtle text-warning-emphasis',
  critique: 'bg-danger-subtle text-danger',
  non_configure: 'bg-light text-muted',
}

export default function AdminStatistiques() {
  const [tab, setTab] = useState('overview')
  const [academicYear, setAcademicYear] = useState('')
  const [department, setDepartment] = useState('')
  const [program, setProgram] = useState('')

  const yearsQuery = useFetch(() => fetchAcademicYears({ page_size: 50 }), [])
  const departmentsQuery = useFetch(() => fetchDepartments({ page_size: 200 }), [])
  const programsQuery = useFetch(() => fetchPrograms({ page_size: 200 }), [])

  const years = yearsQuery.data || []
  const departments = departmentsQuery.data?.results || []
  const programs = programsQuery.data || []

  const statsQuery = useFetch(
    () => fetchAcademicStatistics({
      academic_year: academicYear || undefined,
      department: department || undefined,
      program: program || undefined,
    }),
    [academicYear, department, program],
  )

  const stats = statsQuery.data
  const kpis = stats?.kpis
  const pedagogy = stats?.pedagogiques
  const admin = stats?.admin
  const history = stats?.historique
  const alerts = stats?.alertes

  const degreeChart = useMemo(() => ({
    labels: (pedagogy?.by_degree || []).map((row) => row.label),
    datasets: [{
      data: (pedagogy?.by_degree || []).map((row) => row.total),
      backgroundColor: ['#3349A1', '#5B6FC7', '#283D85', '#7B8FD4'],
    }],
  }), [pedagogy])

  const historyChart = useMemo(() => ({
    labels: history?.months || [],
    datasets: [
      {
        label: 'Étudiants créés',
        data: history?.students_created || [],
        backgroundColor: 'rgba(51, 73, 161, 0.75)',
        borderRadius: 6,
      },
      {
        label: 'Inscriptions validées',
        data: history?.enrollments_approved || [],
        backgroundColor: 'rgba(25, 135, 84, 0.65)',
        borderRadius: 6,
      },
    ],
  }), [history])

  const exportRows = [
    ['Étudiants actifs', kpis?.students_active ?? '—'],
    ['Enseignants', kpis?.teachers_active ?? '—'],
    ['Programmes', kpis?.programs_active ?? '—'],
    ['Validation ECTS', kpis ? `${kpis.taux_validation_ects}%` : '—'],
    ['Réussite notes', pedagogy ? `${pedagogy.taux_reussite}%` : '—'],
    ['Recouvrement', admin ? `${admin.taux_recouvrement}%` : '—'],
  ]

  return (
    <>
      <PageHeader
        title="Statistiques"
        subtitle="Indicateurs LMD de l’INJS — effectifs, validation ECTS, réussite et recouvrement"
        action={
          <ExportButtons
            title="Statistiques INJS"
            filename="injs_statistiques"
            headers={['Indicateur', 'Valeur']}
            rows={exportRows}
          />
        }
      />

      <div className="card-injs p-3 mb-4">
        <div className="row g-3 align-items-end">
          <div className="col-md-4">
            <label className="form-label">Année académique</label>
            <select className="form-select" value={academicYear} onChange={(event) => setAcademicYear(event.target.value)}>
              <option value="">Toutes</option>
              {years.map((year) => (
                <option key={year.id} value={year.id}>{year.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Département</label>
            <select className="form-select" value={department} onChange={(event) => { setDepartment(event.target.value); setProgram('') }}>
              <option value="">Tous</option>
              {departments.map((item) => (
                <option key={item.id} value={item.id}>{item.code} — {item.label || item.name}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Programme</label>
            <select className="form-select" value={program} onChange={(event) => setProgram(event.target.value)}>
              <option value="">Tous</option>
              {programs
                .filter((item) => !department || item.department === department)
                .map((item) => (
                  <option key={item.id} value={item.id}>{item.code} — {item.name}</option>
                ))}
            </select>
          </div>
        </div>
        {stats?.filtre?.students_in_scope != null && (
          <p className="text-muted small mb-0 mt-3">
            Périmètre : {stats.filtre.students_in_scope} étudiant(s)
            {stats.filtre.academic_year_label ? ` · ${stats.filtre.academic_year_label}` : ''}.
          </p>
        )}
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="d-flex flex-wrap gap-2">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`btn btn-sm ${tab === item.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {statsQuery.loading ? (
        <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
      ) : statsQuery.error ? (
        <div className="alert alert-danger">{statsQuery.error}</div>
      ) : (
        <>
          {tab === 'overview' && (
            <>
              <div className="row g-4 mb-4">
                <div className="col-md-6 col-xl-3">
                  <StatCard icon={FiUsers} label="Étudiants actifs" value={kpis?.students_active ?? 0} color="green" />
                </div>
                <div className="col-md-6 col-xl-3">
                  <StatCard icon={FiBookOpen} label="Programmes" value={kpis?.programs_active ?? 0} color="blue" />
                </div>
                <div className="col-md-6 col-xl-3">
                  <StatCard icon={FiAward} label="Validation ECTS" value={`${kpis?.taux_validation_ects ?? 0}%`} color="gold" />
                </div>
                <div className="col-md-6 col-xl-3">
                  <StatCard icon={FiCheckSquare} label="Réussite notes" value={`${pedagogy?.taux_reussite ?? 0}%`} color="orange" />
                </div>
              </div>
              <div className="row g-4">
                <div className="col-lg-5">
                  <div className="card-injs p-4 h-100">
                    <h5 className="fw-bold mb-3">Répartition par cycle</h5>
                    {pedagogy?.by_degree?.length ? <Doughnut data={degreeChart} /> : <p className="text-muted mb-0">Aucune donnée.</p>}
                  </div>
                </div>
                <div className="col-lg-7">
                  <div className="card-injs p-4 h-100">
                    <h5 className="fw-bold mb-3">Historique 12 mois</h5>
                    <Bar data={historyChart} options={{ responsive: true, plugins: { legend: { position: 'bottom' } } }} />
                  </div>
                </div>
              </div>
            </>
          )}

          {tab === 'pedagogy' && (
            <>
              <div className="row g-4 mb-4">
                <div className="col-md-4">
                  <StatCard icon={FiAward} label="Notes ≥ 10" value={`${pedagogy?.taux_reussite ?? 0}%`} color="green" />
                </div>
                <div className="col-md-4">
                  <StatCard icon={FiCheckSquare} label="Semestres validés" value={`${pedagogy?.taux_semestres_valides ?? 0}%`} color="blue" />
                </div>
                <div className="col-md-4">
                  <StatCard icon={FiUsers} label="Moyenne semestre" value={pedagogy?.average_semester ?? '—'} color="gold" />
                </div>
              </div>
              <div className="row g-4">
                <div className="col-lg-6">
                  <BreakdownTable
                    title="Par spécialité"
                    rows={pedagogy?.by_specialization || []}
                    columns={['code', 'name', 'total']}
                    labels={['Code', 'Libellé', 'Effectif']}
                  />
                </div>
                <div className="col-lg-6">
                  <BreakdownTable
                    title="Par programme"
                    rows={pedagogy?.by_program || []}
                    columns={['code', 'name', 'total']}
                    labels={['Code', 'Programme', 'Effectif']}
                  />
                </div>
              </div>
            </>
          )}

          {tab === 'admin' && (
            <>
              <div className="row g-4 mb-4">
                <div className="col-md-4">
                  <StatCard icon={FiDollarSign} label="Recouvrement" value={`${admin?.taux_recouvrement ?? 0}%`} color="green" />
                </div>
                <div className="col-md-4">
                  <StatCard icon={FiAlertTriangle} label="Frais non soldés" value={`${admin?.taux_impayes ?? 0}%`} color="orange" />
                </div>
                <div className="col-md-4">
                  <StatCard icon={FiUsers} label="Inscriptions en attente" value={admin?.inscriptions_en_attente ?? 0} color="blue" />
                </div>
              </div>
              <BreakdownTable
                title="Programmes par cycle"
                rows={admin?.programs_by_degree || []}
                columns={['label', 'total']}
                labels={['Cycle', 'Nombre']}
              />
            </>
          )}

          {tab === 'alerts' && (
            <div className="card-injs p-4">
              <div className="d-flex flex-wrap gap-3 mb-4">
                <span className="badge bg-success">{alerts?.ok || 0} OK</span>
                <span className="badge bg-warning text-dark">{alerts?.avertissement || 0} avertissement(s)</span>
                <span className="badge bg-danger">{alerts?.critique || 0} critique(s)</span>
              </div>
              <div className="table-responsive">
                <table className="table align-middle mb-0">
                  <thead>
                    <tr>
                      <th>Indicateur</th>
                      <th>Valeur</th>
                      <th>Seuils</th>
                      <th>Niveau</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(alerts?.indicateurs || []).map((item) => (
                      <tr key={item.code}>
                        <td>{item.label}</td>
                        <td>{item.value ?? '—'}%</td>
                        <td className="small text-muted">Avert. {item.seuil_avertissement} · Crit. {item.seuil_critique}</td>
                        <td>
                          <span className={`badge ${ALERT_CLASS[item.niveau] || 'bg-light text-muted'}`}>{item.niveau}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
}

function BreakdownTable({ title, rows, columns, labels }) {
  return (
    <div className="card-injs p-4 h-100">
      <h5 className="fw-bold mb-3">{title}</h5>
      <div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead>
            <tr>{labels.map((label) => <th key={label}>{label}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.code || row.label || index}>
                {columns.map((column) => <td key={column}>{row[column] ?? '—'}</td>)}
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={columns.length} className="text-center text-muted py-4">Aucune donnée.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
