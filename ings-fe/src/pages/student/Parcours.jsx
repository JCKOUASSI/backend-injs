import PageHeader from '../../components/common/PageHeader'
import { useAuth } from '../../context/AuthContext'
import { filterGradesByNiveau, filterSemestresByNiveau } from '../../utils/studentLevel'
import { SPECIALITES_STAPS } from '../../data/mockData'

export default function StudentParcours() {
  const { user } = useAuth()
  const niveau = user?.niveau || 'L1'
  const grades = filterGradesByNiveau(niveau)
  const semestres = filterSemestresByNiveau(niveau)
  const currentGrade = grades[0]
  const specColor = SPECIALITES_STAPS.find((s) => user?.specialite?.includes(s.code))?.color || SPECIALITES_STAPS[0].color

  return (
    <>
      <PageHeader
        title="Mon parcours LMD"
        subtitle={`${currentGrade?.label || 'Licence'} STAPS — ${niveau} — ${currentGrade?.credits || 180} CECT`}
      />

      <div className="row g-4 mb-4">
        {grades.map((g) => (
          <div key={g.id} className="col-md-6 col-lg-4">
            <div className="card-injs p-4 border-success border-2">
              <span className={`badge-lmd-${g.id} badge-injs`}>{g.label}</span>
              <p className="mt-2 mb-0 small text-muted">{g.duree} — {g.credits} crédits</p>
              <span className="badge bg-success mt-2">En cours — {niveau}</span>
            </div>
          </div>
        ))}
      </div>

      <h5 className="fw-bold mb-3">Semestres — {niveau}</h5>
      <div className="row g-3 mb-4">
        {semestres.map((s) => (
          <div key={s.id} className="col-md-6">
            <div className={`card-injs p-3 ${s.id === user?.semestre ? 'border-warning border-2' : s.id < user?.semestre ? 'opacity-75' : ''}`}>
              <div className="d-flex justify-content-between">
                <strong>{s.label}</strong>
                <span>{s.credits} ECTS</span>
              </div>
              <small className="text-muted">{s.niveau} — {s.type}</small>
              {s.id < user?.semestre && <span className="grade-badge grade-valid d-block mt-2">Validé ✓</span>}
              {s.id === user?.semestre && <span className="grade-badge grade-pending d-block mt-2">En cours</span>}
            </div>
          </div>
        ))}
      </div>

      {user?.semestre >= 4 && user?.specialite && user.specialite !== '—' && (
        <>
          <h5 className="fw-bold mb-3">Ma spécialité</h5>
          <div className="card-injs p-4" style={{ borderLeft: `4px solid ${specColor}` }}>
            <h6>{user.specialite}</h6>
            <p className="small text-muted mb-0">Parcours {niveau} — spécialisation depuis S4</p>
          </div>
        </>
      )}
    </>
  )
}
