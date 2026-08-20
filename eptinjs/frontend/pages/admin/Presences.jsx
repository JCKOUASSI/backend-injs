/** Suivi des présences et du badgeage sur l'ensemble des séances. */
import { useCallback, useEffect, useState } from 'react'
import { FiRefreshCw } from 'react-icons/fi'
import PageHeader from '@app/components/common/PageHeader'
import { fetchGrille, fetchQrSeance, fetchStatistiquesEdt, genererQrSeance } from '../../api/eptinjs'
import { Chargement, EtatVide, Jauge, Kpi, StatutBadge } from '../../components/Badges'
import FiltresEdt from '../../components/FiltresEdt'
import QrSeanceModal from '../../components/QrSeanceModal'
import SeanceDetailModal from '../../components/SeanceDetailModal'
import useReferentiels from '../../hooks/useReferentiels'

export default function Presences() {
  const referentiels = useReferentiels()
  const [filtres, setFiltres] = useState({})
  const [grille, setGrille] = useState(null)
  const [stats, setStats] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [seanceOuverte, setSeanceOuverte] = useState(null)
  const [qrSeanceId, setQrSeanceId] = useState(null)
  const [qr, setQr] = useState(null)

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
      setErreur(err.message || 'Chargement des présences impossible.')
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

  const seances = (grille?.seances || []).filter((seance) => seance.statut !== 'planifiee' || seance.attendus_count)

  return (
    <div>
      <PageHeader
        title="Présences & badgeage"
        subtitle="Émargements des séances, taux de présence et QR de badgeage"
      />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <FiltresEdt
        valeurs={filtres}
        onChange={setFiltres}
        periodes={referentiels.periodes}
        promotions={referentiels.promotions}
        salles={referentiels.salles}
        enseignants={referentiels.enseignants}
        champs={['periode', 'promotion', 'teacher', 'statut', 'dates']}
        extra={
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
            <FiRefreshCw className="me-1" /> Actualiser
          </button>
        }
      />

      {stats && (
        <div className="ept-kpis mb-4">
          <Kpi valeur={stats.presences.attendus} label="Pointages attendus" />
          <Kpi valeur={stats.presences.presents} label="Présences" />
          <Kpi valeur={stats.presences.absents} label="Absences" />
          <Kpi valeur={stats.presences.retards} label="Retards" />
          <Kpi valeur={stats.presences.taux_presence} suffixe="%" label="Taux de présence" />
          <Kpi valeur={stats.seances.en_cours} label="Séances en cours" />
        </div>
      )}

      {chargement ? <Chargement /> : seances.length === 0 ? (
        <EtatVide message="Aucune séance émargée sur ce périmètre." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Date</th><th>Horaire</th><th>ECUE</th><th>Promotion</th>
                  <th>Enseignant</th><th>Salle</th><th>Présents</th>
                  <th style={{ width: 150 }}>Taux</th><th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {seances.map((seance) => (
                  <tr key={seance.id} role="button" onClick={() => setSeanceOuverte(seance.id)}>
                    <td className="text-nowrap small">{seance.day_display} {seance.date}</td>
                    <td className="text-nowrap">{seance.heure_debut}–{seance.heure_fin}</td>
                    <td><code className="me-1">{seance.course_code}</code>{seance.course_name}</td>
                    <td className="small">
                      {seance.promotion_name}{seance.groupe_code && ` · ${seance.groupe_code}`}
                    </td>
                    <td className="small">{seance.teacher_name || '—'}</td>
                    <td className="small">{seance.room_code || '—'}</td>
                    <td className="text-nowrap">{seance.presents_count} / {seance.attendus_count}</td>
                    <td>
                      <Jauge
                        valeur={
                          seance.attendus_count
                            ? (seance.presents_count / seance.attendus_count) * 100
                            : 0
                        }
                      />
                    </td>
                    <td><StatutBadge statut={seance.statut} label={seance.statut_display} /></td>
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
