/** Étudiants de la promotion et assiduité cumulée sur l'offre. */
import { useMemo, useState } from 'react'
import { EtatVide, Jauge } from '../../../components/Badges'

export default function OngletEtudiants({ offre }) {
  const [recherche, setRecherche] = useState('')

  const visibles = useMemo(() => {
    const terme = recherche.trim().toLowerCase()
    if (!terme) return offre.etudiants
    return offre.etudiants.filter((etudiant) =>
      `${etudiant.matricule} ${etudiant.nom}`.toLowerCase().includes(terme),
    )
  }, [offre.etudiants, recherche])

  if (!offre.etudiants.length) {
    return <EtatVide message="Aucun étudiant actif dans cette promotion." />
  }

  return (
    <div>
      <div className="d-flex flex-wrap gap-3 align-items-center mb-3">
        <input
          type="search"
          className="form-control form-control-sm"
          style={{ maxWidth: 280 }}
          placeholder="Matricule ou nom…"
          value={recherche}
          onChange={(event) => setRecherche(event.target.value)}
        />
        <span className="text-muted small">{visibles.length} / {offre.etudiants.length} étudiants</span>
        {offre.groupes.length > 0 && (
          <span className="text-muted small">
            Groupes : {offre.groupes.map((groupe) => `${groupe.code} (${groupe.effectif})`).join(', ')}
          </span>
        )}
      </div>

      <div className="card">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>Matricule</th><th>Nom</th><th>Statut</th>
                <th>Séances suivies</th><th>Présences</th><th>Absences</th><th style={{ width: 150 }}>Assiduité</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((etudiant) => (
                <tr key={etudiant.id}>
                  <td><code>{etudiant.matricule}</code></td>
                  <td>{etudiant.nom}</td>
                  <td className="small">{etudiant.statut}</td>
                  <td>{etudiant.seances_suivies}</td>
                  <td className="text-success fw-semibold">{etudiant.presents}</td>
                  <td className="text-danger fw-semibold">{etudiant.absents}</td>
                  <td><Jauge valeur={etudiant.taux_presence} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
