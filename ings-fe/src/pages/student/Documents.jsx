import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import { useToast } from '../../context/ToastContext'
import { useAuth } from '../../context/AuthContext'
import { semestreIdsForNiveau } from '../../utils/studentLevel'
import { downloadTranscriptPdf } from '../../api/reports'
import { INSTITUTION } from '../../data/mockData'
import { exportTableToPdf, exportTableToExcel, exportTableToWord } from '../../utils/exportFormats'

export default function StudentDocuments() {
  const { showToast } = useToast()
  const { user } = useAuth()
  const semestres = semestreIdsForNiveau(user?.niveau || 'L1').filter((s) => s <= (user?.semestre || 1))

  const docs = [
    ...semestres.map((s) => ({ label: `Relevé de notes S${s}`, type: 'releve', semester: s })),
    { label: `Attestation d'inscription ${INSTITUTION.academicYear}`, type: 'attestation' },
    { label: 'Certificat de scolarité', type: 'certificat' },
  ]

  const handleDownload = async (doc, format = 'pdf') => {
    try {
      if (user?.studentId && doc.type === 'releve' && format === 'pdf') {
        await downloadTranscriptPdf(user.studentId, { semester: doc.semester })
        showToast(`Relevé S${doc.semester} téléchargé`, 'success')
        return
      }

      const headers = ['Document', 'Étudiant', 'Matricule', 'Année']
      const rows = [[doc.label, user?.name || '—', user?.matricule || '—', INSTITUTION.academicYear]]
      const file = doc.label.replace(/\s+/g, '_').toLowerCase()
      if (format === 'pdf') exportTableToPdf(file, doc.label, headers, rows)
      else if (format === 'excel') exportTableToExcel(file, headers, rows)
      else exportTableToWord(file, doc.label, headers, rows)
      showToast(`${doc.label} exporté (${format})`, 'success')
    } catch (err) {
      showToast(err.message || 'Téléchargement impossible', 'danger')
    }
  }

  return (
    <>
      <PageHeader
        title="Documents & relevés"
        subtitle={`${user?.niveau} — Semestres S${semestres.join(', S')}`}
        action={
          <ExportButtons
            title="Inventaire documents"
            filename="mes_documents"
            headers={['Document']}
            rows={docs.map((d) => [d.label])}
          />
        }
      />
      <div className="row g-3">
        {docs.map((d) => (
          <div key={d.label} className="col-md-6">
            <div className="card-injs p-3">
              <div className="d-flex justify-content-between align-items-center mb-2">
                <span className="fw-semibold">{d.label}</span>
              </div>
              <ExportButtons onExport={(format) => handleDownload(d, format)} />
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
