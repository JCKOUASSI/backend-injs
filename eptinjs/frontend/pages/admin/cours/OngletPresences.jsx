/** Présences et badgeage : synthèse par séance et feuille d'émargement. */
import { useState } from 'react'
import { FiPlay } from 'react-icons/fi'
import { demarrerSeance } from '../../../api/eptinjs'
import { EtatVide, Jauge, Kpi, StatutBadge } from '../../../components/Badges'
import EmargementPanel from '../../../components/EmargementPanel'

export default function OngletPresences({ offre, peutGerer, onRefresh, onOuvrirQr }) {
  const [seanceActive, setSeanceActive] = useState(offre.seances[0]?.id || null)
  const [erreur, setErreur] = useState('')

  if (!offre.seances.length) {
    return <EtatVide message="Le badgeage sera disponible dès qu’une séance sera planifiée." />
  }

  const seance = offre.seances.find((item) => item.id === seanceActive) || offre.seances[0]

  // La feuille d'émargement relève du module « faculty » : hors de portée d'un étudiant.
  if (!peutGerer) {
    return (
      <div>
        <div className="ept-kpis mb-4">
          <Kpi valeur={offre.presences.attendus} label="Pointages" />
          <Kpi valeur={offre.presences.presents} label="Présences" />
          <Kpi valeur={offre.presences.absents} label="Absences" />
          <Kpi valeur={offre.presences.taux_presence} suffixe="%" label="Taux global" />
        </div>

        <div className="card">
          <div className="table-responsive">
            <table className="table table-sm align-middle mb-0">
              <thead>
                <tr><th>Date</th><th>Horaire</th><th>Nature</th><th>Salle</th><th>Présents</th><th style={{ width: 150 }}>Taux</th><th>Statut</th></tr>
              </thead>
              <tbody>
                {offre.seances.map((item) => (
                  <tr key={item.id}>
                    <td className="text-nowrap small">{item.day_display} {item.date}</td>
                    <td className="text-nowrap">{item.heure_debut}–{item.heure_fin}</td>
                    <td>{item.session_kind_display}</td>
                    <td className="small">{item.room_code || '—'}</td>
                    <td className="text-nowrap">{item.presents_count} / {item.attendus_count}</td>
                    <td><Jauge valeur={item.taux_presence} /></td>
                    <td><StatutBadge statut={item.statut} label={item.statut_display} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    )
  }

  const demarrer = async () => {
    setErreur('')
    try {
      await demarrerSeance(seance.id)
      onOuvrirQr?.(seance.id)
      onRefresh?.()
    } catch (err) {
      setErreur(err.message || 'Impossible de démarrer la séance.')
    }
  }

  return (
    <div>
      {erreur && <div className="alert alert-danger py-2">{erreur}</div>}

      <div className="ept-kpis mb-4">
        <Kpi valeur={offre.presences.attendus} label="Pointages attendus" />
        <Kpi valeur={offre.presences.presents} label="Présences" />
        <Kpi valeur={offre.presences.absents} label="Absences" />
        <Kpi valeur={offre.presences.taux_presence} suffixe="%" label="Taux global" />
      </div>

      <div className="row g-3">
        <div className="col-lg-5">
          <div className="card">
            <div className="card-header bg-white">
              <h6 className="fw-bold mb-0">Séances ({offre.seances.length})</h6>
            </div>
            <div className="list-group list-group-flush" style={{ maxHeight: 520, overflowY: 'auto' }}>
              {offre.seances.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`list-group-item list-group-item-action ${
                    item.id === seance.id ? 'active' : ''
                  }`}
                  onClick={() => setSeanceActive(item.id)}
                >
                  <div className="d-flex justify-content-between gap-2">
                    <span className="fw-semibold small">
                      {item.day_display} {item.date} · {item.heure_debut}–{item.heure_fin}
                    </span>
                    <StatutBadge statut={item.statut} label={item.statut_display} />
                  </div>
                  <div className="small">
                    {item.periode_code} · {item.session_kind_display}
                    {item.groupe_code && ` · ${item.groupe_code}`}
                    {item.room_code && ` · ${item.room_code}`}
                  </div>
                  <div className="mt-1">
                    <Jauge valeur={item.taux_presence} largeur={110} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="card">
            <div className="card-header bg-white d-flex flex-wrap justify-content-between align-items-center gap-2">
              <h6 className="fw-bold mb-0">
                Émargement — {seance.day_display} {seance.date} ({seance.heure_debut}–{seance.heure_fin})
              </h6>
              {peutGerer && (
                seance.statut === 'planifiee' ? (
                  <button type="button" className="btn btn-sm btn-success" onClick={demarrer}>
                    <FiPlay className="me-1" /> Démarrer le badgeage
                  </button>
                ) : seance.statut === 'en_cours' ? (
                  <button
                    type="button" className="btn btn-sm btn-injs-primary"
                    onClick={() => onOuvrirQr?.(seance.id)}
                  >
                    Afficher le QR
                  </button>
                ) : null
              )}
            </div>
            <div className="card-body">
              <EmargementPanel seanceId={seance.id} editable={peutGerer} onChange={onRefresh} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
