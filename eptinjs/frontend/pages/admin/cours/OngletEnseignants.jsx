/** Équipe pédagogique intervenant sur l'offre, toutes périodes confondues. */
import { EtatVide } from '../../../components/Badges'

const ROLES = { titulaire: 'Titulaire', encadrant: 'Encadrant' }

export default function OngletEnseignants({ offre }) {
  if (!offre.enseignants.length) {
    return (
      <EtatVide message="Aucun enseignant affecté. Affectez un titulaire depuis l’onglet Programmes des emplois du temps." />
    )
  }

  return (
    <div className="card">
      <div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead>
            <tr>
              <th>Matricule</th><th>Nom</th><th>Grade</th><th>Rôles</th>
              <th>Périodes</th><th>Séances assurées</th>
            </tr>
          </thead>
          <tbody>
            {offre.enseignants.map((enseignant) => (
              <tr key={enseignant.id}>
                <td><code>{enseignant.employee_id}</code></td>
                <td className="fw-semibold">{enseignant.nom}</td>
                <td className="small">{enseignant.grade}</td>
                <td className="small">
                  {enseignant.roles.map((role) => ROLES[role] || role).join(', ')}
                </td>
                <td className="small">{enseignant.periodes.join(', ')}</td>
                <td>{enseignant.seances_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
