import { Link, useParams } from 'react-router-dom'
import { FiArrowLeft, FiClock, FiUsers, FiCalendar, FiCheckSquare } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import { useFetch } from '../../hooks/useFetch'
import { fetchCoursOffering } from '../../api/academics'
import { statusBadge } from './Cours'

function Ligne({ libelle, valeur }) {
  return (
    <div className="d-flex justify-content-between border-bottom py-2">
      <span className="text-muted small">{libelle}</span>
      <span className="fw-semibold text-end">{valeur ?? '—'}</span>
    </div>
  )
}

function couvertureCouleur(pourcentage) {
  if (pourcentage >= 90) return 'bg-success'
  if (pourcentage >= 50) return 'bg-warning'
  return 'bg-danger'
}

export default function AdminCoursDetail() {
  const { offeringId } = useParams()
  const { data: cours, loading, error } = useFetch(
    () => fetchCoursOffering({ id: offeringId }),
    [offeringId],
  )

  const retour = (
    <Link to="/admin/cours" className="btn btn-sm btn-outline-secondary">
      <FiArrowLeft className="me-1" aria-hidden /> Retour au catalogue
    </Link>
  )

  if (loading) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error || !cours) {
    return (
      <div>
        <PageHeader title="Cours introuvable" action={retour} />
        <div className="alert alert-danger">
          {error || "Ce cours n'existe pas pour l'année académique courante."}
        </div>
      </div>
    )
  }

  const couverture = cours.coverage_pct || 0
  const creneaux = cours.schedules || []
  const seances = (cours.seances && cours.seances.length)
    ? cours.seances.map((row) => ({
      ...row,
      session_date: row.date,
      day_display: row.period_label || '',
      is_active: row.status === 'in_progress' || row.status === 'published',
    }))
    : (cours.sessions || [])
  const enseignants = cours.assignments || []

  return (
    <div>
      <PageHeader
        title={`${cours.course_code} — ${cours.course_name}`}
        subtitle={`${cours.program_code} · ${cours.promotion_name} · année ${cours.academic_year_label}`}
        action={retour}
      />

      <div className="d-flex align-items-center gap-2 mb-4">
        {statusBadge(cours.status, cours.status_label)}
        <span className="badge bg-light text-dark">{cours.degree_type_display}</span>
        <span className="badge bg-light text-dark">S{cours.semester_number}</span>
        <span className="badge bg-light text-dark">{cours.credits_ects} ECTS</span>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-6 col-lg-3">
          <StatCard icon={FiClock} label="Volume à couvrir" value={`${cours.hours_total} h`} color="orange" />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard icon={FiCalendar} label="Heures / semaine" value={cours.weekly_hours ?? 0} color="blue" />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard icon={FiCheckSquare} label="Séances tenues" value={cours.sessions_count ?? 0} color="purple" />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard icon={FiUsers} label="Étudiants" value={cours.students_count ?? 0} color="green" />
        </div>
      </div>

      <div className="row g-3">
        <div className="col-12 col-lg-5">
          <div className="card-injs p-4 h-100">
            <h5 className="mb-3">Informations</h5>
            <Ligne libelle="Unité d'enseignement" valeur={`${cours.teaching_unit_code} — ${cours.teaching_unit_name}`} />
            <Ligne libelle="Programme" valeur={`${cours.program_code} — ${cours.program_name}`} />
            <Ligne libelle="Promotion" valeur={cours.promotion_name} />
            <Ligne libelle="Semestre" valeur={`S${cours.semester_number}`} />
            <Ligne libelle="Crédits ECTS" valeur={cours.credits_ects} />
            <Ligne libelle="Coefficient" valeur={cours.coefficient} />
            <Ligne libelle="Volume CM / TD / TP" valeur={`${cours.hours_cm} / ${cours.hours_td} / ${cours.hours_tp} h`} />
            <Ligne libelle="Année académique" valeur={cours.academic_year_label} />
          </div>
        </div>

        <div className="col-12 col-lg-7">
          <div className="card-injs p-4 h-100">
            <h5 className="mb-3">Couverture du volume horaire</h5>
            <div className="d-flex justify-content-between small text-muted mb-1">
              <span>
                {cours.estimated_semester_hours ?? 0} h projetées sur le semestre
              </span>
              <span>objectif {cours.volume_objectif ?? cours.hours_total} h</span>
            </div>
            <div className="progress mb-3" style={{ height: 10 }}>
              <div
                className={`progress-bar ${couvertureCouleur(couverture)}`}
                style={{ width: `${Math.min(couverture, 100)}%` }}
                role="progressbar"
                aria-valuenow={couverture}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
            <p className="text-muted small mb-4">
              Projection calculée à partir des {creneaux.length} créneau(x) hebdomadaire(s) actif(s),
              soit {couverture} % du volume prévu.
            </p>

            <h6 className="mb-2">Équipe pédagogique</h6>
            {enseignants.length === 0 ? (
              <p className="text-muted small mb-0">Aucun enseignant affecté.</p>
            ) : (
              <ul className="list-unstyled mb-0">
                {enseignants.map((item) => (
                  <li key={item.id} className="d-flex justify-content-between border-bottom py-2">
                    <span>
                      {item.teacher_name}
                      {item.is_primary && <span className="badge bg-primary ms-2">Titulaire</span>}
                      {item.supervisor_name && (
                        <div className="small text-muted">Encadrant : {item.supervisor_name}</div>
                      )}
                    </span>
                    <span className="text-muted small">{item.slots_count} créneau(x)</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <div className="card-injs p-0 mt-3">
        <div className="p-3 border-bottom"><h5 className="mb-0">Créneaux hebdomadaires</h5></div>
        {creneaux.length === 0 ? (
          <div className="text-center text-muted py-4">Aucun créneau planifié.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Jour</th>
                  <th>Horaire</th>
                  <th>Type</th>
                  <th>Salle</th>
                  <th className="text-end">Durée</th>
                </tr>
              </thead>
              <tbody>
                {creneaux.map((creneau) => (
                  <tr key={creneau.id}>
                    <td>{creneau.day_display}</td>
                    <td>{creneau.start_time} – {creneau.end_time}</td>
                    <td><span className="badge bg-light text-dark">{creneau.session_kind_display}</span></td>
                    <td>{creneau.room_code || <span className="text-muted">—</span>}</td>
                    <td className="text-end">{creneau.hours} h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card-injs p-0 mt-3">
        <div className="p-3 border-bottom d-flex justify-content-between align-items-center">
          <h5 className="mb-0">Séances</h5>
          <span className="text-muted small">{cours.session_hours ?? 0} h tenues</span>
        </div>
        {seances.length === 0 ? (
          <div className="text-center text-muted py-4">Aucune séance enregistrée.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Horaire</th>
                  <th>Type</th>
                  <th>Salle</th>
                  <th className="text-end">Présents</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {seances.map((seance) => (
                  <tr key={seance.id}>
                    <td>
                      {new Date(seance.session_date).toLocaleDateString('fr-FR')}
                      <div className="small text-muted">{seance.day_display}</div>
                    </td>
                    <td>{seance.start_time} – {seance.end_time}</td>
                    <td><span className="badge bg-light text-dark">{seance.session_kind_display}</span></td>
                    <td>{seance.room_code || <span className="text-muted">—</span>}</td>
                    <td className="text-end">
                      {seance.roster_count
                        ? `${seance.present_count} / ${seance.roster_count}`
                        : <span className="text-muted">—</span>}
                    </td>
                    <td>
                      <span className={`badge ${seance.is_active ? 'bg-success' : 'bg-secondary'}`}>
                        {seance.status_label}
                      </span>
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
