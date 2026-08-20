/** Séances de l'offre, groupées par période de formation. */
import { useState } from 'react'
import { FiPlay, FiSquare } from 'react-icons/fi'
import { demarrerSeance, terminerSeance } from '../../../api/eptinjs'
import { EtatVide, StatutBadge } from '../../../components/Badges'

export default function OngletSeances({ offre, peutGerer, onRefresh, onOuvrirSeance, onOuvrirQr }) {
  const [erreur, setErreur] = useState('')
  const [occupe, setOccupe] = useState(null)

  if (!offre.seances.length) {
    return (
      <EtatVide message="Aucune séance planifiée pour cette offre. Générez l’emploi du temps de la période ou créez une séance." />
    )
  }

  const parPeriode = offre.periodes
    .map((periode) => ({
      periode,
      seances: offre.seances.filter((seance) => seance.periode === periode.id),
    }))
    .filter((bloc) => bloc.seances.length)

  const orphelines = offre.seances.filter(
    (seance) => !offre.periodes.some((periode) => periode.id === seance.periode),
  )
  if (orphelines.length) {
    parPeriode.push({ periode: { id: 'autres', code: '—', libelle: 'Hors programme actif' }, seances: orphelines })
  }

  const agir = async (seance, action) => {
    setErreur('')
    setOccupe(seance.id)
    try {
      if (action === 'demarrer') {
        await demarrerSeance(seance.id)
        onOuvrirQr?.(seance.id)
      } else {
        await terminerSeance(seance.id)
      }
      onRefresh?.()
    } catch (err) {
      setErreur(err.message || 'Opération impossible.')
    } finally {
      setOccupe(null)
    }
  }

  return (
    <div>
      {erreur && <div className="alert alert-danger py-2">{erreur}</div>}

      {parPeriode.map(({ periode, seances }) => (
        <div className="card mb-3" key={periode.id}>
          <div className="card-header bg-white d-flex justify-content-between align-items-center">
            <h6 className="fw-bold mb-0">
              <code className="me-2">{periode.code}</code>{periode.libelle}
            </h6>
            <span className="text-muted small">
              {seances.length} séance(s) ·{' '}
              {seances.reduce((total, item) => total + item.duree_heures, 0).toFixed(1)} h
            </span>
          </div>
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>N°</th><th>Date</th><th>Horaire</th><th>Nature</th><th>Groupe</th>
                  <th>Salle</th><th>Enseignant</th><th>Présences</th><th>Statut</th>
                  {peutGerer && <th />}
                </tr>
              </thead>
              <tbody>
                {seances.map((seance) => (
                  <tr
                    key={seance.id}
                    role={peutGerer ? 'button' : undefined}
                    onClick={peutGerer ? () => onOuvrirSeance?.(seance.id) : undefined}
                  >
                    <td>{seance.numero}</td>
                    <td className="text-nowrap small">{seance.day_display} {seance.date}</td>
                    <td className="text-nowrap">{seance.heure_debut}–{seance.heure_fin}</td>
                    <td>{seance.session_kind_display}</td>
                    <td>{seance.groupe_code || 'Promotion'}</td>
                    <td>{seance.room_code || <span className="text-danger">—</span>}</td>
                    <td className="small">{seance.teacher_name || <span className="text-danger">—</span>}</td>
                    <td className="text-nowrap small">
                      {seance.attendus_count
                        ? `${seance.presents_count}/${seance.attendus_count} (${seance.taux_presence} %)`
                        : '—'}
                    </td>
                    <td><StatutBadge statut={seance.statut} label={seance.statut_display} /></td>
                    {peutGerer && (
                      <td className="text-end text-nowrap" onClick={(event) => event.stopPropagation()}>
                        {seance.statut === 'planifiee' && (
                          <button
                            type="button" className="btn btn-sm btn-outline-success"
                            disabled={occupe === seance.id}
                            onClick={() => agir(seance, 'demarrer')}
                            title="Démarrer et ouvrir le badgeage"
                          >
                            <FiPlay />
                          </button>
                        )}
                        {seance.statut === 'en_cours' && (
                          <>
                            <button
                              type="button" className="btn btn-sm btn-injs-primary me-1"
                              onClick={() => onOuvrirQr?.(seance.id)}
                            >
                              QR
                            </button>
                            <button
                              type="button" className="btn btn-sm btn-outline-secondary"
                              disabled={occupe === seance.id}
                              onClick={() => agir(seance, 'terminer')}
                              title="Clôturer la séance"
                            >
                              <FiSquare />
                            </button>
                          </>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
