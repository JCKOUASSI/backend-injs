import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchAnalytics } from '../../api/reports'
import { fetchStudents } from '../../api/students'
import { fetchGrades } from '../../api/exams'
import { fetchStudentFees } from '../../api/finance'
import { downloadBackendExport, exportTableToPdf, exportTableToExcel, exportTableToWord } from '../../utils/exportFormats'
import { translateStatus } from '../../utils/labels'

const REPORTS = [
  {
    name: 'Liste des étudiants',
    resourcePath: '/students',
    buildClient: (ctx) => ({
      headers: ['Matricule', 'Nom', 'Prénom', 'Niveau', 'Statut'],
      rows: (ctx.students || []).map((s) => [s.id, s.nom, s.prenom, s.niveau, s.statut]),
    }),
  },
  {
    name: 'Notes & évaluations',
    resourcePath: '/exams/grades',
    buildClient: (ctx) => ({
      headers: ['Évaluation', 'UE', 'Note', 'Statut'],
      rows: (ctx.grades || []).map((g) => [g.label, g.ue, g.moyenne ?? '—', g.statut]),
    }),
  },
  {
    name: 'Frais & paiements',
    resourcePath: '/finance/student-fees',
    buildClient: (ctx) => ({
      headers: ['Étudiant', 'Type', 'Dû', 'Payé', 'Statut'],
      rows: (ctx.fees || []).map((f) => [f.student || '—', f.fee_type || '—', f.amount_due, f.amount_paid, translateStatus(f.status)]),
    }),
  },
  {
    name: 'Indicateurs direction',
    resourcePath: null,
    buildClient: (ctx) => ({
      headers: ['Indicateur', 'Valeur'],
      rows: [
        ['Étudiants', ctx.analytics?.total_students ?? '—'],
        ['Enseignants', ctx.analytics?.total_teachers ?? '—'],
        ['Frais en attente', ctx.analytics?.pending_fees ?? '—'],
        ['Frais payés', ctx.analytics?.paid_fees ?? '—'],
        ['Moyenne', ctx.analytics?.average_grade ?? '—'],
      ],
    }),
  },
  {
    name: 'Enseignants',
    resourcePath: '/faculty/teachers',
    buildClient: () => ({ headers: ['Export serveur'], rows: [['Utiliser l\'export PDF/Excel/Word du serveur']] }),
  },
]

export default function AdminReports() {
  const { showToast } = useToast()
  const { data: analytics } = useFetch(() => fetchAnalytics())
  const { data: studentsData } = useFetch(() => fetchStudents({ page_size: 200 }))
  const { data: gradesData } = useFetch(() => fetchGrades())
  const { data: feesData } = useFetch(() => fetchStudentFees())

  const ctx = {
    analytics,
    students: studentsData?.results || [],
    grades: gradesData?.results || [],
    fees: feesData?.results || [],
  }

  const generate = async (report, format) => {
    try {
      if (report.resourcePath) {
        try {
          await downloadBackendExport(report.resourcePath, format, report.name.replace(/\s+/g, '_').toLowerCase())
          showToast(`Exportation ${format.toUpperCase()} (serveur) prête`, 'success')
          return
        } catch {
          // fallback client
        }
      }
      const { headers, rows } = report.buildClient(ctx)
      const file = report.name.replace(/\s+/g, '_').toLowerCase()
      if (format === 'pdf') exportTableToPdf(file, report.name, headers, rows)
      else if (format === 'excel') exportTableToExcel(file, headers, rows)
      else exportTableToWord(file, report.name, headers, rows)
      showToast(`Rapport « ${report.name} » exporté (${format})`, 'success')
    } catch (err) {
      showToast(err.message || 'Échec génération', 'danger')
    }
  }

  return (
    <>
      <PageHeader
        title="Rapports & Statistiques"
        subtitle="Exports PDF, Excel et Word — export serveur + repli local"
        action={
          <ExportButtons
            title="Indicateurs INJS"
            filename="injs_analytics"
            headers={['Indicateur', 'Valeur']}
            rows={[
              ['Étudiants', analytics?.total_students ?? '—'],
              ['Enseignants', analytics?.total_teachers ?? '—'],
              ['Frais en attente', analytics?.pending_fees ?? '—'],
            ]}
          />
        }
      />
      <div className="row g-3">
        {REPORTS.map((r) => (
          <div key={r.name} className="col-md-6">
            <div className="card-injs p-4">
              <div className="d-flex justify-content-between align-items-start gap-3 mb-3">
                <span className="fw-semibold">{r.name}</span>
              </div>
              <ExportButtons onExport={(format) => generate(r, format)} />
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
