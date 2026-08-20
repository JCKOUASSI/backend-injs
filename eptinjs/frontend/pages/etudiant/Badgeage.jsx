/** Badgeage QR : scan caméra, saisie manuelle, séances ouvertes et historique. */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Html5Qrcode } from 'html5-qrcode'
import { FiCamera, FiRefreshCw, FiXCircle } from 'react-icons/fi'
import PageHeader from '@app/components/common/PageHeader'
import { captureBadgeContext } from '@app/utils/badgeDevice'
import {
  envoyerHeartbeat,
  fetchMonHistoriqueBadge,
  fetchStatutBadge,
  scannerBadge,
} from '../../api/eptinjs'
import { Chargement, EtatVide, StatutBadge } from '../../components/Badges'

const ZONE_SCAN = 'ept-qr-reader'
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i

/** Le QR encode une URL `…/etudiant/presences?ept_token=<uuid>` ; on tolère l'UUID nu. */
function extraireToken(brut) {
  const valeur = (brut || '').trim()
  if (!valeur) return ''
  const correspondance = valeur.match(UUID)
  return correspondance ? correspondance[0] : ''
}

function heure(iso) {
  return iso ? new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '—'
}

export default function Badgeage() {
  const [parametres, setParametres] = useSearchParams()
  const [saisie, setSaisie] = useState('')
  const [statut, setStatut] = useState(null)
  const [historique, setHistorique] = useState([])
  const [dernier, setDernier] = useState(null)
  const [erreur, setErreur] = useState('')
  const [chargement, setChargement] = useState(true)
  const [scanEnCours, setScanEnCours] = useState(false)
  const [envoi, setEnvoi] = useState(false)
  const scannerRef = useRef(null)
  const occupeRef = useRef(false)

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const [etat, journal] = await Promise.all([
        fetchStatutBadge().catch(() => null),
        fetchMonHistoriqueBadge().catch(() => ({ results: [] })),
      ])
      setStatut(etat)
      setHistorique(journal.results || [])
    } finally {
      setChargement(false)
    }
  }, [])

  useEffect(() => { charger() }, [charger])

  const badger = useCallback(async (brut) => {
    const token = extraireToken(brut)
    if (!token) {
      setErreur('QR de séance non reconnu.')
      return
    }
    if (occupeRef.current) return
    occupeRef.current = true
    setEnvoi(true)
    setErreur('')
    try {
      const contexte = await captureBadgeContext()
      const resultat = await scannerBadge({
        token,
        device_id: contexte.device_id,
        latitude: contexte.latitude,
        longitude: contexte.longitude,
        accuracy_m: contexte.accuracy_m,
      })
      setDernier(resultat)
      setSaisie('')
      parametres.delete('ept_token')
      setParametres(parametres, { replace: true })
      await charger()
    } catch (err) {
      setErreur(err.message || 'Badgeage refusé.')
    } finally {
      occupeRef.current = false
      setEnvoi(false)
    }
  }, [charger, parametres, setParametres])

  const tokenUrl = parametres.get('ept_token')
  useEffect(() => {
    if (tokenUrl) badger(tokenUrl)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokenUrl])

  const arreterScan = useCallback(async () => {
    const scanner = scannerRef.current
    scannerRef.current = null
    setScanEnCours(false)
    if (!scanner) return
    await scanner.stop().catch(() => {})
    scanner.clear().catch(() => {})
  }, [])

  useEffect(() => () => { arreterScan() }, [arreterScan])

  const demarrerScan = async () => {
    setErreur('')
    setScanEnCours(true)
    try {
      const scanner = new Html5Qrcode(ZONE_SCAN)
      scannerRef.current = scanner
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 8, qrbox: { width: 240, height: 240 } },
        async (decode) => {
          await arreterScan()
          await badger(decode)
        },
        () => {},
      )
    } catch (err) {
      setScanEnCours(false)
      setErreur(err?.message || 'Caméra indisponible. Saisissez le code affiché à l’écran.')
    }
  }

  // Signal de présence périodique tant qu'une entrée est ouverte.
  useEffect(() => {
    if (!dernier?.sens || dernier.sens !== 'entree' || !dernier.pointage) return undefined
    const timer = setInterval(async () => {
      const contexte = await captureBadgeContext()
      envoyerHeartbeat({
        pointage: dernier.pointage,
        latitude: contexte.latitude,
        longitude: contexte.longitude,
        accuracy_m: contexte.accuracy_m,
      }).catch(() => {})
    }, 120000)
    return () => clearInterval(timer)
  }, [dernier])

  return (
    <div>
      <PageHeader
        title="Présences et badgeage"
        subtitle="Scannez le QR affiché en salle : la première lecture enregistre l’entrée, la seconde la sortie"
      />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      {dernier && (
        <div className="alert alert-success">
          <strong>{dernier.sens === 'entree' ? 'Entrée enregistrée' : 'Sortie enregistrée'}</strong> —{' '}
          {dernier.seance.course_code} ({dernier.seance.heure_debut}–{dernier.seance.heure_fin})
          {dernier.seance.room_code && ` · salle ${dernier.seance.room_code}`}
          {' · '}
          <StatutBadge statut={dernier.statut} label={dernier.statut} />
          {dernier.duree_minutes ? ` · ${dernier.duree_minutes} min en salle` : ''}
        </div>
      )}

      <div className="row g-3">
        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-body">
              <h6 className="fw-bold mb-3">Scanner le QR</h6>
              <div id={ZONE_SCAN} className="mb-3" style={{ minHeight: scanEnCours ? 260 : 0 }} />

              <div className="d-flex gap-2 mb-3">
                {scanEnCours ? (
                  <button type="button" className="btn btn-outline-danger" onClick={arreterScan}>
                    <FiXCircle className="me-1" /> Arrêter
                  </button>
                ) : (
                  <button type="button" className="btn btn-injs-primary" onClick={demarrerScan}>
                    <FiCamera className="me-1" /> Activer la caméra
                  </button>
                )}
              </div>

              <form
                className="input-group"
                onSubmit={(event) => { event.preventDefault(); badger(saisie) }}
              >
                <input
                  type="text"
                  className="form-control"
                  placeholder="Ou collez ici le code de la séance"
                  value={saisie}
                  onChange={(event) => setSaisie(event.target.value)}
                />
                <button type="submit" className="btn btn-outline-secondary" disabled={envoi}>
                  {envoi ? 'Envoi…' : 'Badger'}
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-header bg-white d-flex justify-content-between align-items-center">
              <h6 className="fw-bold mb-0">Séances ouvertes aujourd’hui</h6>
              <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
                <FiRefreshCw />
              </button>
            </div>
            <div className="card-body">
              {chargement ? <Chargement /> : !statut?.seances?.length ? (
                <EtatVide message="Aucune séance n’est ouverte au badgeage pour le moment." />
              ) : (
                <ul className="list-group list-group-flush">
                  {statut.seances.map((seance) => (
                    <li className="list-group-item px-0" key={seance.id}>
                      <div className="d-flex justify-content-between gap-2">
                        <span className="fw-semibold">
                          <code className="me-1">{seance.course_code}</code>{seance.course_name}
                        </span>
                        <StatutBadge
                          statut={seance.sortie_faite ? 'terminee' : seance.deja_badge ? 'present' : 'attendu'}
                          label={seance.sortie_faite ? 'Sortie faite' : seance.deja_badge ? 'Entrée faite' : 'À badger'}
                        />
                      </div>
                      <div className="small text-muted">
                        {seance.heure_debut}–{seance.heure_fin}
                        {seance.room_code && ` · salle ${seance.room_code}`} · {seance.promotion_name}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>

      <h6 className="fw-bold mt-4 mb-2">Mon historique de badgeage</h6>
      {historique.length === 0 ? (
        <EtatVide message="Aucun badgeage enregistré." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-sm align-middle mb-0">
              <thead>
                <tr><th>Date</th><th>ECUE</th><th>Horaire</th><th>Salle</th><th>Statut</th><th>Entrée</th><th>Sortie</th><th>Durée</th></tr>
              </thead>
              <tbody>
                {historique.map((ligne) => (
                  <tr key={ligne.id}>
                    <td className="text-nowrap small">{ligne.date}</td>
                    <td><code>{ligne.course_code}</code></td>
                    <td className="text-nowrap small">{ligne.heure_debut}–{ligne.heure_fin}</td>
                    <td className="small">{ligne.room_code || '—'}</td>
                    <td><StatutBadge statut={ligne.statut} label={ligne.statut_display} /></td>
                    <td className="small">{heure(ligne.entree_at)}</td>
                    <td className="small">{heure(ligne.sortie_at)}</td>
                    <td className="small">{ligne.duree_minutes ? `${ligne.duree_minutes} min` : '—'}</td>
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
