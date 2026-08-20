/** Emploi du temps personnel de l'étudiant. */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiRefreshCw } from 'react-icons/fi'
import PageHeader from '@app/components/common/PageHeader'
import Modal from '@app/components/common/Modal'
import { fetchMonPlanning, fetchPeriodes } from '../../api/eptinjs'
import { Chargement, Kpi, StatutBadge } from '../../components/Badges'
import PlanningGrid from '../../components/PlanningGrid'

function debutDeSemaine(date = new Date()) {
  const copie = new Date(date)
  copie.setDate(copie.getDate() - ((copie.getDay() + 6) % 7))
  return copie.toISOString().slice(0, 10)
}

export default function MonEmploiDuTemps() {
  const naviguer = useNavigate()
  const [periodes, setPeriodes] = useState([])
  const [periode, setPeriode] = useState('')
  const [semaine, setSemaine] = useState(debutDeSemaine())
  const [toutesSemaines, setToutesSemaines] = useState(false)
  const [grille, setGrille] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [seance, setSeance] = useState(null)

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

  const decalerSemaine = (jours) => {
    const date = new Date(`${semaine}T00:00:00`)
    date.setDate(date.getDate() + jours)
    setSemaine(date.toISOString().slice(0, 10))
  }

  return (
    <div>
      <PageHeader title="Mon emploi du temps" subtitle="Vos séances de cours et vos salles" />

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
              type="checkbox" className="form-check-input" id="ept-etu-toutes"
              checked={toutesSemaines} onChange={(event) => setToutesSemaines(event.target.checked)}
            />
            <label className="form-check-label" htmlFor="ept-etu-toutes">Toute la période</label>
          </div>
        </div>

        <div className="d-flex align-items-end gap-2">
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
            <FiRefreshCw className="me-1" /> Actualiser
          </button>
          <button
            type="button" className="btn btn-sm btn-injs-primary"
            onClick={() => naviguer('/etudiant/presences')}
          >
            Badger une séance
          </button>
        </div>
      </div>

      {grille && (
        <div className="ept-kpis mb-4">
          <Kpi valeur={grille.count} label="Séances" />
          <Kpi valeur={grille.heures_totales} suffixe="h" label="Volume" />
          <Kpi valeur={grille.jours?.length ?? 0} label="Jours de cours" />
        </div>
      )}

      {chargement ? (
        <Chargement />
      ) : (
        <PlanningGrid
          jours={grille?.jours || []}
          onSelect={setSeance}
          message="Aucune séance programmée sur cette période."
        />
      )}

      <Modal
        show={Boolean(seance)}
        onClose={() => setSeance(null)}
        title={seance ? `${seance.course_code} — ${seance.course_name}` : ''}
        footer={
          seance?.statut === 'en_cours' && (
            <button
              type="button" className="btn btn-injs-primary"
              onClick={() => naviguer('/etudiant/presences')}
            >
              Badger maintenant
            </button>
          )
        }
      >
        {seance && (
          <ul className="list-unstyled mb-0">
            <li className="mb-2"><strong>Date :</strong> {seance.day_display} {seance.date}</li>
            <li className="mb-2"><strong>Horaire :</strong> {seance.heure_debut}–{seance.heure_fin}</li>
            <li className="mb-2"><strong>Nature :</strong> {seance.session_kind_display}</li>
            <li className="mb-2"><strong>Salle :</strong> {seance.room_code || 'à préciser'}</li>
            <li className="mb-2"><strong>Enseignant :</strong> {seance.teacher_name || 'à préciser'}</li>
            <li className="mb-2"><strong>Période :</strong> {seance.periode_code}</li>
            <li><strong>Statut :</strong> <StatutBadge statut={seance.statut} label={seance.statut_display} /></li>
          </ul>
        )}
      </Modal>
    </div>
  )
}
