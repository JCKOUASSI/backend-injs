/** Emploi du temps personnel de l'enseignant, avec ouverture du badgeage. */
import { useCallback, useEffect, useState } from 'react'
import { FiRefreshCw } from 'react-icons/fi'
import PageHeader from '@app/components/common/PageHeader'
import {
  fetchMonPlanning,
  fetchPeriodes,
  fetchQrSeance,
  genererQrSeance,
} from '../../api/eptinjs'
import { Chargement, Kpi } from '../../components/Badges'
import PlanningGrid from '../../components/PlanningGrid'
import QrSeanceModal from '../../components/QrSeanceModal'
import SeanceDetailModal from '../../components/SeanceDetailModal'

function debutDeSemaine(date = new Date()) {
  const copie = new Date(date)
  const decalage = (copie.getDay() + 6) % 7
  copie.setDate(copie.getDate() - decalage)
  return copie.toISOString().slice(0, 10)
}

export default function MonEmploiDuTemps() {
  const [periodes, setPeriodes] = useState([])
  const [periode, setPeriode] = useState('')
  const [semaine, setSemaine] = useState(debutDeSemaine())
  const [toutesSemaines, setToutesSemaines] = useState(false)
  const [grille, setGrille] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [seanceOuverte, setSeanceOuverte] = useState(null)
  const [qrSeanceId, setQrSeanceId] = useState(null)
  const [qr, setQr] = useState(null)

  useEffect(() => {
    fetchPeriodes({ page_size: 100 })
      .then((reponse) => setPeriodes(reponse.results || []))
      .catch(() => setPeriodes([]))
  }, [])

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      const params = {}
      if (periode) params.periode = periode
      if (!toutesSemaines) params.semaine = semaine
      setGrille(await fetchMonPlanning(params))
    } catch (err) {
      setErreur(err.message || 'Chargement de votre emploi du temps impossible.')
    } finally {
      setChargement(false)
    }
  }, [periode, semaine, toutesSemaines])

  useEffect(() => { charger() }, [charger])

  const rafraichirQr = useCallback(async () => {
    if (!qrSeanceId) return
    try {
      setQr(await fetchQrSeance(qrSeanceId))
    } catch {
      setQr(null)
    }
  }, [qrSeanceId])

  useEffect(() => { rafraichirQr() }, [rafraichirQr])

  const decalerSemaine = (jours) => {
    const date = new Date(`${semaine}T00:00:00`)
    date.setDate(date.getDate() + jours)
    setSemaine(date.toISOString().slice(0, 10))
  }

  return (
    <div>
      <PageHeader
        title="Mon emploi du temps"
        subtitle="Vos séances, toutes périodes de formation, et l’ouverture du badgeage"
      />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <div className="ept-toolbar mb-3">
        <div className="d-flex flex-column">
          <span className="form-label">Période de formation</span>
          <select
            className="form-select form-select-sm"
            value={periode}
            onChange={(event) => setPeriode(event.target.value)}
          >
            <option value="">Toutes les périodes</option>
            {periodes.map((item) => (
              <option key={item.id} value={item.id}>{item.code} — {item.libelle}</option>
            ))}
          </select>
        </div>

        {!toutesSemaines && (
          <div className="d-flex flex-column">
            <span className="form-label">Semaine du</span>
            <div className="input-group input-group-sm">
              <button type="button" className="btn btn-outline-secondary" onClick={() => decalerSemaine(-7)}>‹</button>
              <input
                type="date" className="form-control"
                value={semaine} onChange={(event) => setSemaine(event.target.value)}
              />
              <button type="button" className="btn btn-outline-secondary" onClick={() => decalerSemaine(7)}>›</button>
            </div>
          </div>
        )}

        <div className="d-flex align-items-end">
          <div className="form-check">
            <input
              type="checkbox" className="form-check-input" id="ept-toutes-semaines"
              checked={toutesSemaines} onChange={(event) => setToutesSemaines(event.target.checked)}
            />
            <label className="form-check-label" htmlFor="ept-toutes-semaines">Toute la période</label>
          </div>
        </div>

        <div className="d-flex align-items-end">
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
            <FiRefreshCw className="me-1" /> Actualiser
          </button>
        </div>
      </div>

      {grille && (
        <div className="ept-kpis mb-4">
          <Kpi valeur={grille.count} label="Séances" />
          <Kpi valeur={grille.heures_totales} suffixe="h" label="Volume" />
          <Kpi valeur={grille.jours?.length ?? 0} label="Jours occupés" />
        </div>
      )}

      {chargement ? (
        <Chargement />
      ) : (
        <PlanningGrid
          jours={grille?.jours || []}
          onSelect={(seance) => setSeanceOuverte(seance.id)}
          afficherPresences
          message="Aucune séance sur cette période."
        />
      )}

      <SeanceDetailModal
        show={Boolean(seanceOuverte)}
        seanceId={seanceOuverte}
        peutGerer
        onClose={() => setSeanceOuverte(null)}
        onChange={charger}
        onOuvrirQr={setQrSeanceId}
      />

      <QrSeanceModal
        show={Boolean(qrSeanceId)}
        qr={qr}
        onClose={() => { setQrSeanceId(null); setQr(null); charger() }}
        onRefresh={rafraichirQr}
        onRegenerer={async () => setQr(await genererQrSeance(qrSeanceId, true))}
      />
    </div>
  )
}
