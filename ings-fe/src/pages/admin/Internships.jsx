import PageHeader from '../../components/common/PageHeader'
import { STAGES } from '../../data/mockData'

export default function AdminInternships() {
  return (
    <>
      <PageHeader title="Gestion des stages" subtitle="3 stages obligatoires — S4, S5, S6 — ~450h (18 crédits)" />
      <div className="card-injs overflow-hidden">
        <table className="table table-injs mb-0">
          <thead><tr><th>Type</th><th>Semestre</th><th>Lieu</th><th>Durée</th><th>Superviseur</th><th>Statut</th></tr></thead>
          <tbody>
            {STAGES.map((s, i) => (
              <tr key={i}>
                <td className="fw-semibold">{s.type}</td>
                <td>S{s.semestre}</td>
                <td>{s.lieu}</td>
                <td>{s.duree}</td>
                <td>{s.superviseur}</td>
                <td><span className={`grade-badge ${s.statut === 'En cours' ? 'grade-pending' : 'grade-valid'}`}>{s.statut}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
