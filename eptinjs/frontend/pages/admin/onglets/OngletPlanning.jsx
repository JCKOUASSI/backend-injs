/** Grille d'emploi du temps administrable, toutes périodes confondues. */
import { useCallback, useEffect, useState } from 'react'
import { FiList, FiGrid, FiPlus, FiRefreshCw } from 'react-icons/fi'
import { fetchGrille, fetchStatistiquesEdt, fetchQrSeance, genererQrSeance } from '../../../api/eptinjs'
import { Chargement, Jauge, Kpi, StatutBadge } from '../../../components/Badges'
import FiltresEdt from '../../../components/FiltresEdt'
import PlanningGrid from '../../../components/PlanningGrid'
import QrSeanceModal from '../../../components/QrSeanceModal'
import SeanceDetailModal from '../../../components/SeanceDetailModal'
import SeanceFormModal from '../../../components/SeanceFormModal'

export default function OngletPlanning({ referentiels, filtres, onFiltres }) {
  const [grille, setGrille] = useState(null)
  const [stats, setStats] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [vue, setVue] = useState('grille')

  const [seanceOuverte, setSeanceOuverte] = useState(null)
  const [seanceEditee, setSeanceEditee] = useState(null)
  const [formOuvert, setFormOuvert] = useState(false)
  const [qr, setQr] = useState(null)
  const [qrSeanceId, setQrSeanceId] = useState(null)

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      const [donnees, indicateurs] = await Promise.all([
        fetchGrille(filtres),
        fetchStatistiquesEdt(filtres),
      ])
      setGrille(donnees)
      setStats(indicateurs)
    } catch (err) {
      setErreur(err.message || 'Chargement de l’emploi du temps impossible.')
    } finally {
      setChargement(false)
    }
  }, [filtres])

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

  const ouvrirQr = (seanceId) => setQrSeanceId(seanceId)

  const fermerQr = () => {
    setQrSeanceId(null)
    setQr(null)
    charger()
  }

  const editer = (seance) => {
    setSeanceOuverte(null)
    setSeanceEditee(seance)
    setFormOuvert(true)
  }

  const seances = grille?.seances || []

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
        extra={
          <div className="d-flex gap-2 align-items-end">
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
              <FiRefreshCw className="me-1" /> Actualiser
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={() => setVue(vue === 'grille' ? 'liste' : 'grille')}
            >
              {vue === 'grille' ? <><FiList className="me-1" /> Liste</> : <><FiGrid className="me-1" /> Grille</>}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-injs-primary"
              onClick={() => { setSeanceEditee(null); setFormOuvert(true) }}
            >
              <FiPlus className="me-1" /> Séance
            </button>
          </div>
        }
      />

      {stats && (
        <div className="ept-kpis mb-4">
          <Kpi valeur={stats.seances.total} label="Séances" />
          <Kpi valeur={stats.seances.heures} suffixe="h" label="Volume planifié" />
          <Kpi valeur={stats.seances.sans_salle} label="Sans salle" />
          <Kpi valeur={stats.seances.sans_enseignant} label="Sans enseignant" />
          <Kpi valeur={stats.presences.taux_presence} suffixe="%" label="Taux de présence" />
          <Kpi valeur={stats.periodes_actives} label="Périodes actives" />
        </div>
      )}

      {stats?.par_periode?.length > 1 && (
        <div className="card mb-4">
          <div className="card-body py-3">
            <h6 className="fw-bold mb-3">Répartition par période de formation</h6>
            <div className="table-responsive">
              <table className="table table-sm mb-0 align-middle">
                <thead>
                  <tr><th>Période</th><th>Séances</th><th>Heures</th><th style={{ width: 200 }}>Part</th></tr>
                </thead>
                <tbody>
                  {stats.par_periode.map((ligne) => (
                    <tr key={ligne.periode}>
                      <td><code className="me-2">{ligne.code}</code>{ligne.libelle}</td>
                      <td>{ligne.seances}</td>
                      <td>{ligne.heures} h</td>
                      <td>
                        <Jauge
                          valeur={stats.seances.total ? (ligne.seances / stats.seances.total) * 100 : 0}
                          largeur={120}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {chargement ? (
        <Chargement />
      ) : vue === 'grille' ? (
        <PlanningGrid
          jours={grille?.jours || []}
          onSelect={(seance) => setSeanceOuverte(seance.id)}
          afficherPresences
        />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Date</th><th>Horaire</th><th>ECUE</th><th>Promotion</th>
                  <th>Nature</th><th>Salle</th><th>Enseignant</th><th>Statut</th><th>Présences</th>
                </tr>
              </thead>
              <tbody>
                {seances.map((seance) => (
                  <tr key={seance.id} role="button" onClick={() => setSeanceOuverte(seance.id)}>
                    <td className="text-nowrap">{seance.day_display} {seance.date}</td>
                    <td className="text-nowrap">{seance.heure_debut}–{seance.heure_fin}</td>
                    <td><code className="me-1">{seance.course_code}</code>{seance.course_name}</td>
                    <td>{seance.promotion_name}{seance.groupe_code && ` · ${seance.groupe_code}`}</td>
                    <td>{seance.session_kind_display}</td>
                    <td>{seance.room_code || <span className="text-danger">—</span>}</td>
                    <td>{seance.teacher_name || <span className="text-danger">—</span>}</td>
                    <td><StatutBadge statut={seance.statut} label={seance.statut_display} /></td>
                    <td className="text-nowrap">
                      {seance.attendus_count ? `${seance.presents_count}/${seance.attendus_count}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <SeanceDetailModal
        show={Boolean(seanceOuverte)}
        seanceId={seanceOuverte}
        peutGerer
        onClose={() => setSeanceOuverte(null)}
        onChange={charger}
        onEdit={editer}
        onOuvrirQr={ouvrirQr}
      />

      <SeanceFormModal
        show={formOuvert}
        seance={seanceEditee}
        periode={filtres.periode}
        onClose={() => setFormOuvert(false)}
        onSaved={charger}
      />

      <QrSeanceModal
        show={Boolean(qrSeanceId)}
        qr={qr}
        onClose={fermerQr}
        onRefresh={rafraichirQr}
        onRegenerer={async () => {
          setQr(await genererQrSeance(qrSeanceId, true))
        }}
      />
    </div>
  )
}
