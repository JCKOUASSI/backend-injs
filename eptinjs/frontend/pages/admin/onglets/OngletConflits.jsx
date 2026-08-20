/** Diagnostic des anomalies de l'emploi du temps. */
import { useCallback, useEffect, useState } from 'react'
import { FiRefreshCw } from 'react-icons/fi'
import { fetchConflits } from '../../../api/eptinjs'
import { Chargement, EtatVide, Kpi } from '../../../components/Badges'
import FiltresEdt from '../../../components/FiltresEdt'
import SeanceDetailModal from '../../../components/SeanceDetailModal'

const LIBELLES = {
  salle_double_reservation: 'Salle réservée deux fois',
  enseignant_double_reservation: 'Enseignant en double',
  auditoire_double_reservation: 'Auditoire en double',
  jour_ferie: 'Séance un jour férié',
  jour_non_ouvre: 'Jour non ouvré',
  hors_plage_horaire: 'Hors plage horaire',
  trop_de_seances: 'Trop de séances dans la journée',
  capacite_insuffisante: 'Capacité de salle insuffisante',
  salle_manquante: 'Salle non affectée',
  enseignant_manquant: 'Enseignant non affecté',
}

export default function OngletConflits({ referentiels, filtres, onFiltres }) {
  const [donnees, setDonnees] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [typeActif, setTypeActif] = useState('')
  const [seanceOuverte, setSeanceOuverte] = useState(null)

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      setDonnees(await fetchConflits(filtres))
    } catch (err) {
      setErreur(err.message || 'Analyse des conflits impossible.')
    } finally {
      setChargement(false)
    }
  }, [filtres])

  useEffect(() => { charger() }, [charger])

  const conflits = (donnees?.conflits || []).filter(
    (conflit) => !typeActif || conflit.type === typeActif,
  )
  const parType = donnees?.par_type || {}
  const bloquants = (donnees?.conflits || []).filter((item) => item.gravite === 'bloquant').length
  const majeurs = (donnees?.conflits || []).filter((item) => item.gravite === 'majeur').length

  return (
    <div>
      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <FiltresEdt
        valeurs={filtres}
        onChange={onFiltres}
        periodes={referentiels.periodes}
        promotions={referentiels.promotions}
        salles={referentiels.salles}
        enseignants={referentiels.enseignants}
        champs={['periode', 'promotion', 'teacher', 'room', 'dates']}
        extra={
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
            <FiRefreshCw className="me-1" /> Réanalyser
          </button>
        }
      />

      <div className="ept-kpis mb-3">
        <Kpi valeur={donnees?.count ?? 0} label="Anomalies" />
        <Kpi valeur={bloquants} label="Bloquantes" />
        <Kpi valeur={majeurs} label="Majeures" />
      </div>

      {Object.keys(parType).length > 0 && (
        <div className="d-flex flex-wrap gap-2 mb-3">
          <button
            type="button"
            className={`btn btn-sm ${!typeActif ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setTypeActif('')}
          >
            Tout ({donnees.count})
          </button>
          {Object.entries(parType).map(([type, nombre]) => (
            <button
              key={type}
              type="button"
              className={`btn btn-sm ${typeActif === type ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => setTypeActif(type)}
            >
              {LIBELLES[type] || type} ({nombre})
            </button>
          ))}
        </div>
      )}

      {chargement ? <Chargement /> : conflits.length === 0 ? (
        <EtatVide message="Aucune anomalie détectée sur ce périmètre." />
      ) : (
        conflits.slice(0, 300).map((conflit, index) => (
          <div
            key={`${conflit.type}-${index}`}
            className={`ept-conflit ${conflit.gravite === 'bloquant' ? '' : `ept-conflit-${conflit.gravite}`}`}
            role="button"
            tabIndex={0}
            onClick={() => setSeanceOuverte(conflit.seances[0])}
            onKeyDown={(event) => event.key === 'Enter' && setSeanceOuverte(conflit.seances[0])}
          >
            <div className="d-flex justify-content-between gap-2">
              <strong className="small text-uppercase">{LIBELLES[conflit.type] || conflit.type}</strong>
              <span className="small text-muted">{conflit.gravite}</span>
            </div>
            <div>{conflit.message}</div>
          </div>
        ))
      )}

      <SeanceDetailModal
        show={Boolean(seanceOuverte)}
        seanceId={seanceOuverte}
        peutGerer
        onClose={() => setSeanceOuverte(null)}
        onChange={charger}
      />
    </div>
  )
}
