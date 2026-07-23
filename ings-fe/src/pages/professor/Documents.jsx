import PageHeader from '../../components/common/PageHeader'
import { useToast } from '../../context/ToastContext'

const DOCS = ['Syllabus SVS8101', 'Fiche descriptive UE MET8115', 'Grille évaluation CC', 'Procès-verbal UP — Janvier 2026']

export default function ProfDocuments() {
  const { showToast } = useToast()

  return (
    <>
      <PageHeader title="Documents pédagogiques" />
      <div className="row g-3">
        {DOCS.map((d, i) => (
          <div key={i} className="col-md-6">
            <div className="card-injs p-3 d-flex justify-content-between align-items-center">
              <span>{d}</span>
              <button type="button" className="btn btn-sm btn-outline-success" onClick={() => showToast(`Téléchargement : ${d} (démo)`, 'info')}>Télécharger</button>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
