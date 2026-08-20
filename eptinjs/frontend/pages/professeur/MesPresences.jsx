/** Conduite des séances de l'enseignant : ouverture du badgeage et émargement. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { FiPlay, FiRefreshCw, FiSquare } from 'react-icons/fi'
import PageHeader from '@app/components/common/PageHeader'
import {
  demarrerSeance,
  fetchMonPlanning,
  fetchQrSeance,
  genererQrSeance,
  terminerSeance,
} from '../../api/eptinjs'
import { Chargement, EtatVide, Kpi, StatutBadge } from '../../components/Badges'
import EmargementPanel from '../../components/EmargementPanel'
import QrSeanceModal from '../../components/QrSeanceModal'

const AUJOURDHUI = () => new Date().toISOString().slice(0, 10)

export default function MesPresences() {
  const [date, setDate] = useState(AUJOURDHUI())
  const [grille, setGrille] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [seanceActive, setSeanceActive] = useState(null)
  const [qrSeanceId, setQrSeanceId] = useState(null)
  const [qr, setQr] = useState(null)
  const [occupe, setOccupe] = useState(false)

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      setGrille(await fetchMonPlanning({ date }))
    } catch (err) {
      setErreur(err.message || 'Chargement de vos séances impossible.')
    } finally {
      setChargement(false)
    }
  }, [date])

  useEffect(() => { charger() }, [charger])

  const seances = useMemo(() => grille?.seances || [], [grille])

  useEffect(() => {
    if (!seances.length) {
      setSeanceActive(null)
      return
    }
    setSeanceActive((courante) =>
      seances.some((item) => item.id === courante)
        ? courante
        : (seances.find((item) => item.statut === 'en_cours') || seances[0]).id,
    )
  }, [seances])

  const rafraichirQr = useCallback(async () => {
    if (!qrSeanceId) return
    try {
      setQr(await fetchQrSeance(qrSeanceId))
    } catch {
      setQr(null)
    }
  }, [qrSeanceId])

  useEffect(() => { rafraichirQr() }, [rafraichirQr])

  const seance = seances.find((item) => item.id === seanceActive)

  const agir = async (action) => {
    setErreur('')
    setOccupe(true)
    try {
      if (action === 'demarrer') {
        await demarrerSeance(seance.id)
        setQrSeanceId(seance.id)
      } else {
        await terminerSeance(seance.id)
        setQrSeanceId(null)
      }
      await charger()
    } catch (err) {
      setErreur(err.message || 'Opération impossible.')
    } finally {
      setOccupe(false)
    }
  }

  const totalPresents = seances.reduce((total, item) => total + item.presents_count, 0)
  const totalAttendus = seances.reduce((total, item) => total + item.attendus_count, 0)

  return (
    <div>
      <PageHeader
        title="Présences"
        subtitle="Ouvrez le badgeage de vos séances et complétez la feuille d’émargement"
      />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <div className="ept-toolbar mb-3">
        <div className="d-flex flex-column">
          <span className="form-label">Journée</span>
          <input
            type="date" className="form-control form-control-sm"
            value={date} onChange={(event) => setDate(event.target.value)}
          />
        </div>
        <div className="d-flex align-items-end gap-2">
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setDate(AUJOURDHUI())}>
            Aujourd’hui
          </button>
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
            <FiRefreshCw className="me-1" /> Actualiser
          </button>
        </div>
      </div>

      <div className="ept-kpis mb-4">
        <Kpi valeur={seances.length} label="Séances du jour" />
        <Kpi valeur={seances.filter((item) => item.statut === 'en_cours').length} label="En cours" />
        <Kpi valeur={totalPresents} label="Présents" />
        <Kpi
          valeur={totalAttendus ? Math.round((totalPresents / totalAttendus) * 1000) / 10 : 0}
          suffixe="%"
          label="Taux du jour"
        />
      </div>

      {chargement ? <Chargement /> : !seances.length ? (
        <EtatVide message="Aucune séance ne vous est affectée ce jour-là." />
      ) : (
        <div className="row g-3">
          <div className="col-lg-4">
            <div className="list-group">
              {seances.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`list-group-item list-group-item-action ${item.id === seanceActive ? 'active' : ''}`}
                  onClick={() => setSeanceActive(item.id)}
                >
                  <div className="d-flex justify-content-between gap-2">
                    <span className="fw-semibold">{item.heure_debut}–{item.heure_fin}</span>
                    <StatutBadge statut={item.statut} label={item.statut_display} />
                  </div>
                  <div className="small">
                    <code className="me-1">{item.course_code}</code>{item.course_name}
                  </div>
                  <div className="small">
                    {item.promotion_name}{item.groupe_code && ` · ${item.groupe_code}`}
                    {item.room_code && ` · ${item.room_code}`}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="col-lg-8">
            {seance && (
              <div className="card">
                <div className="card-header bg-white d-flex flex-wrap justify-content-between align-items-center gap-2">
                  <h6 className="fw-bold mb-0">
                    {seance.course_code} — {seance.heure_debut}–{seance.heure_fin}
                    {seance.room_code && ` · salle ${seance.room_code}`}
                  </h6>
                  <div className="d-flex gap-2">
                    {seance.statut === 'planifiee' && (
                      <button
                        type="button" className="btn btn-sm btn-success"
                        onClick={() => agir('demarrer')} disabled={occupe}
                      >
                        <FiPlay className="me-1" /> Démarrer le badgeage
                      </button>
                    )}
                    {seance.statut === 'en_cours' && (
                      <>
                        <button
                          type="button" className="btn btn-sm btn-injs-primary"
                          onClick={() => setQrSeanceId(seance.id)}
                        >
                          Afficher le QR
                        </button>
                        <button
                          type="button" className="btn btn-sm btn-secondary"
                          onClick={() => agir('terminer')} disabled={occupe}
                        >
                          <FiSquare className="me-1" /> Terminer
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div className="card-body">
                  <EmargementPanel seanceId={seance.id} onChange={charger} />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <QrSeanceModal
        show={Boolean(qrSeanceId)}
        qr={qr}
        onClose={() => { setQrSeanceId(null); setQr(null); charger() }}
        onRefresh={rafraichirQr}
        onRegenerer={async () => setQr(await genererQrSeance(qrSeanceId, true))}
        onTerminer={async () => { await agir('terminer'); setQrSeanceId(null) }}
      />
    </div>
  )
}
