/** Identité de l'ECUE et programmes de période associés. */
import { EtatVide, Jauge } from '../../../components/Badges'

function Info({ libelle, valeur }) {
  return (
    <div className="col-md-4 col-lg-3 mb-3">
      <div className="text-muted text-uppercase" style={{ fontSize: '0.72rem' }}>{libelle}</div>
      <div className="fw-semibold">{valeur ?? '—'}</div>
    </div>
  )
}

export default function OngletInformations({ offre }) {
  return (
    <div>
      <div className="card mb-3">
        <div className="card-body">
          <h6 className="fw-bold mb-3">Identité de l’ECUE</h6>
          <div className="row">
            <Info libelle="Code" valeur={offre.course_code} />
            <Info libelle="Intitulé" valeur={offre.course_name} />
            <Info libelle="Unité d’enseignement" valeur={`${offre.teaching_unit_code} — ${offre.teaching_unit_name}`} />
            <Info libelle="Département" valeur={offre.department_name} />
            <Info libelle="Semestre" valeur={`S${offre.semester_number}`} />
            <Info libelle="Crédits ECTS" valeur={offre.credits_ects} />
            <Info libelle="Coefficient" valeur={offre.coefficient} />
            <Info libelle="Note de validation" valeur={offre.passing_score} />
            <Info libelle="Volume CM" valeur={`${offre.hours_cm} h`} />
            <Info libelle="Volume TD" valeur={`${offre.hours_td} h`} />
            <Info libelle="Volume TP" valeur={`${offre.hours_tp} h`} />
            <Info libelle="Volume maquette" valeur={`${offre.volume_maquette_heures} h`} />
            <Info libelle="Filière" valeur={`${offre.program_code} — ${offre.program_name}`} />
            <Info libelle="Diplôme" valeur={offre.degree_type_display} />
            <Info libelle="Promotion" valeur={offre.promotion_name} />
            <Info libelle="Année académique" valeur={offre.academic_year_label} />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header bg-white">
          <h6 className="fw-bold mb-0">Programmes de période ({offre.programmes_count})</h6>
        </div>
        {offre.programmes.length === 0 ? (
          <div className="card-body">
            <EtatVide message="Cette ECUE n’est programmée sur aucune période de formation." />
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm align-middle mb-0">
              <thead>
                <tr>
                  <th>Période</th><th>Fenêtre</th><th>Nature</th><th>Créneau</th>
                  <th>Volume cible</th><th>Planifié</th><th style={{ width: 150 }}>Couverture</th>
                  <th>Enseignant</th><th>Encadrant</th><th>Groupes</th>
                </tr>
              </thead>
              <tbody>
                {offre.programmes.map((programme) => (
                  <tr key={programme.id}>
                    <td>
                      <code className="me-1">{programme.periode_code}</code>
                      <div className="small text-muted">{programme.periode_libelle}</div>
                    </td>
                    <td className="small text-nowrap">{programme.periode_debut} → {programme.periode_fin}</td>
                    <td>{programme.session_kind_display}</td>
                    <td className="small">{programme.creneau_mode}</td>
                    <td>{programme.volume_cible_heures} h</td>
                    <td>{programme.heures_planifiees} h</td>
                    <td><Jauge valeur={programme.taux_couverture} /></td>
                    <td className="small">{programme.teacher_name || <span className="text-danger">—</span>}</td>
                    <td className="small">{programme.supervisor_name || '—'}</td>
                    <td className="small">
                      {programme.groupes.length
                        ? programme.groupes.map((groupe) => groupe.code).join(', ')
                        : 'Promotion entière'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
