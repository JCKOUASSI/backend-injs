/** Lancement du moteur de planification et historique des générations. */
import { useCallback, useEffect, useState } from 'react'
import { FiPlay } from 'react-icons/fi'
import { fetchRuns, genererPlanning } from '../../../api/eptinjs'
import { Chargement, EtatVide, Kpi, StatutBadge } from '../../../components/Badges'

export default function OngletGeneration({ referentiels, filtres, onFiltres, onRefresh }) {
  const [promotions, setPromotions] = useState([])
  const [mode, setMode] = useState('best_effort')
  const [remplacer, setRemplacer] = useState(true)
  const [dryRun, setDryRun] = useState(false)
  const [resultat, setResultat] = useState(null)
  const [erreur, setErreur] = useState('')
  const [encours, setEncours] = useState(false)
  const [runs, setRuns] = useState([])
  const [chargement, setChargement] = useState(true)

  const chargerRuns = useCallback(async () => {
    setChargement(true)
    try {
      const reponse = await fetchRuns({ page_size: 25, ...(filtres.periode ? { periode: filtres.periode } : {}) })
      setRuns(reponse.results || [])
    } catch (err) {
      setErreur(err.message || 'Historique indisponible.')
    } finally {
      setChargement(false)
    }
  }, [filtres.periode])

  useEffect(() => { chargerRuns() }, [chargerRuns])

  const lancer = async () => {
    if (!filtres.periode) {
      setErreur('Choisissez la période de formation à planifier.')
      return
    }
    setErreur('')
    setResultat(null)
    setEncours(true)
    try {
      const reponse = await genererPlanning({
        periode: filtres.periode,
        promotions,
        mode,
        remplacer,
        dry_run: dryRun,
      })
      setResultat(reponse)
      await chargerRuns()
      if (!dryRun) onRefresh?.()
    } catch (err) {
      setErreur(err.message || 'La génération a échoué.')
    } finally {
      setEncours(false)
    }
  }

  const synthese = resultat?.synthese

  return (
    <div>
      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <div className="card mb-4">
        <div className="card-body">
          <h6 className="fw-bold mb-3">Générer l’emploi du temps</h6>

          <div className="row g-3">
            <div className="col-md-4">
              <label className="form-label">Période de formation</label>
              <select
                className="form-select"
                value={filtres.periode || ''}
                onChange={(event) => onFiltres({ ...filtres, periode: event.target.value })}
              >
                <option value="">— Sélectionner —</option>
                {referentiels.periodes.map((periode) => (
                  <option key={periode.id} value={periode.id}>
                    {periode.code} — {periode.libelle} ({periode.date_debut} → {periode.date_fin})
                  </option>
                ))}
              </select>
            </div>

            <div className="col-md-4">
              <label className="form-label">Promotions (vide = toutes)</label>
              <select
                multiple
                className="form-select"
                size={4}
                value={promotions}
                onChange={(event) =>
                  setPromotions([...event.target.selectedOptions].map((option) => option.value))
                }
              >
                {referentiels.promotions.map((promotion) => (
                  <option key={promotion.id} value={promotion.id}>{promotion.name}</option>
                ))}
              </select>
            </div>

            <div className="col-md-4">
              <label className="form-label">Mode</label>
              <select className="form-select mb-3" value={mode} onChange={(event) => setMode(event.target.value)}>
                <option value="best_effort">Au mieux — place ce qui est possible</option>
                <option value="strict">Strict — échoue si une séance ne tient pas</option>
              </select>

              <div className="form-check">
                <input
                  type="checkbox" className="form-check-input" id="ept-remplacer"
                  checked={remplacer} onChange={(event) => setRemplacer(event.target.checked)}
                />
                <label className="form-check-label" htmlFor="ept-remplacer">
                  Remplacer les séances générées existantes
                </label>
              </div>
              <div className="form-check">
                <input
                  type="checkbox" className="form-check-input" id="ept-dryrun"
                  checked={dryRun} onChange={(event) => setDryRun(event.target.checked)}
                />
                <label className="form-check-label" htmlFor="ept-dryrun">
                  Simulation (aucune écriture)
                </label>
              </div>
            </div>
          </div>

          <div className="mt-3">
            <button type="button" className="btn btn-injs-primary" onClick={lancer} disabled={encours}>
              <FiPlay className="me-1" /> {encours ? 'Génération en cours…' : 'Lancer la génération'}
            </button>
          </div>
        </div>
      </div>

      {synthese && (
        <div className="card mb-4">
          <div className="card-body">
            <h6 className="fw-bold mb-3">
              Résultat {dryRun && <span className="badge bg-secondary ms-1">simulation</span>}
            </h6>
            <div className="ept-kpis mb-3">
              <Kpi valeur={synthese.seances ?? 0} label="Séances créées" />
              <Kpi valeur={synthese.heures_placees ?? 0} suffixe="h" label="Heures placées" />
              <Kpi valeur={synthese.heures_demandees ?? 0} suffixe="h" label="Heures demandées" />
              <Kpi valeur={synthese.taux_couverture ?? 0} suffixe="%" label="Couverture" />
              <Kpi valeur={synthese.echecs ?? 0} label="Flux incomplets" />
            </div>

            {synthese.message && <p className="text-muted">{synthese.message}</p>}

            {resultat.echecs?.length > 0 && (
              <div>
                <h6 className="small text-uppercase text-muted">Volumes non placés</h6>
                {resultat.echecs.slice(0, 40).map((echec) => (
                  <div className="ept-conflit ept-conflit-majeur" key={`${echec.programme}-${echec.groupe || ''}`}>
                    <strong>{echec.flux}</strong> — {echec.heures_non_placees} h non planifiables
                    {' '}(placé : {echec.heures_placees} h / {echec.heures_demandees} h)
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <h6 className="fw-bold mb-2">Historique des générations</h6>
      {chargement ? <Chargement /> : runs.length === 0 ? (
        <EtatVide message="Aucune génération enregistrée." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-sm align-middle mb-0">
              <thead>
                <tr><th>Date</th><th>Période</th><th>Mode</th><th>Statut</th><th>Séances</th><th>Lancée par</th></tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td className="text-nowrap small">
                      {new Date(run.created_at).toLocaleString('fr-FR')}
                    </td>
                    <td><code>{run.periode_code}</code></td>
                    <td className="small">{run.mode}</td>
                    <td><StatutBadge statut={run.statut} label={run.statut} /></td>
                    <td>{run.synthese?.seances ?? '—'}</td>
                    <td className="small">{run.started_by_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
