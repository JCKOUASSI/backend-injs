/** Fiche « Cours (ECUE) » : 5 onglets alimentés par toutes les périodes. */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { FiArrowLeft, FiPlus, FiRefreshCw } from 'react-icons/fi'
import PageHeader from '@app/components/common/PageHeader'
import { fetchOffreCours, fetchQrSeance, genererQrSeance } from '../../api/eptinjs'
import { Chargement, EtatVide, Jauge, Kpi, StatutBadge } from '../../components/Badges'
import QrSeanceModal from '../../components/QrSeanceModal'
import SeanceDetailModal from '../../components/SeanceDetailModal'
import SeanceFormModal from '../../components/SeanceFormModal'
import OngletSeances from './cours/OngletSeances'
import OngletInformations from './cours/OngletInformations'
import OngletEtudiants from './cours/OngletEtudiants'
import OngletPresences from './cours/OngletPresences'
import OngletEnseignants from './cours/OngletEnseignants'

const ONGLETS = [
  { id: 'seances', label: 'Séances', composant: OngletSeances },
  { id: 'informations', label: 'Informations', composant: OngletInformations },
  { id: 'etudiants', label: 'Étudiants', composant: OngletEtudiants },
  { id: 'presences', label: 'Présences', composant: OngletPresences },
  { id: 'enseignants', label: 'Enseignants', composant: OngletEnseignants },
]

export default function CoursDetail({ peutGerer = true, baseRetour = '/admin/cours' }) {
  const { offeringId } = useParams()
  const naviguer = useNavigate()
  const [parametres, setParametres] = useSearchParams()

  const [offre, setOffre] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [periode, setPeriode] = useState(parametres.get('periode') || '')

  const [seanceOuverte, setSeanceOuverte] = useState(null)
  const [seanceEditee, setSeanceEditee] = useState(null)
  const [formOuvert, setFormOuvert] = useState(false)
  const [qrSeanceId, setQrSeanceId] = useState(null)
  const [qr, setQr] = useState(null)

  const ongletActif = parametres.get('onglet') || 'seances'

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      const params = { id: offeringId }
      if (periode) params.periode = periode
      setOffre(await fetchOffreCours(params))
    } catch (err) {
      setErreur(err.message || 'Cette offre de cours est introuvable.')
    } finally {
      setChargement(false)
    }
  }, [offeringId, periode])

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

  const changerOnglet = (id) => {
    parametres.set('onglet', id)
    setParametres(parametres, { replace: true })
  }

  const changerPeriode = (valeur) => {
    setPeriode(valeur)
    if (valeur) parametres.set('periode', valeur)
    else parametres.delete('periode')
    setParametres(parametres, { replace: true })
  }

  if (chargement && !offre) return <Chargement />
  if (erreur && !offre) return <div className="alert alert-danger">{erreur}</div>
  if (!offre) return <EtatVide message="Offre introuvable." />

  const Composant = ONGLETS.find((onglet) => onglet.id === ongletActif)?.composant || OngletSeances

  return (
    <div>
      <PageHeader
        title={`${offre.course_code} — ${offre.course_name}`}
        subtitle={`${offre.promotion_name} · ${offre.teaching_unit_code} ${offre.teaching_unit_name} · ${
          offre.academic_year_label || ''
        }`}
        action={
          <div className="d-flex gap-2">
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => naviguer(baseRetour)}>
              <FiArrowLeft className="me-1" /> Catalogue
            </button>
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={charger}>
              <FiRefreshCw />
            </button>
            {peutGerer && (
              <button
                type="button" className="btn btn-injs-primary btn-sm"
                onClick={() => { setSeanceEditee(null); setFormOuvert(true) }}
              >
                <FiPlus className="me-1" /> Séance
              </button>
            )}
          </div>
        }
      />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <div className="ept-kpis mb-4">
        <Kpi valeur={offre.seances_count} label="Séances" />
        <Kpi valeur={offre.heures_planifiees} suffixe="h" label="Heures planifiées" />
        <Kpi valeur={offre.volume_cible_heures || offre.volume_maquette_heures} suffixe="h" label="Volume cible" />
        <Kpi valeur={offre.etudiants_count} label="Étudiants" />
        <Kpi valeur={offre.enseignants_count} label="Enseignants" />
        <Kpi valeur={offre.presences.taux_presence} suffixe="%" label="Taux de présence" />
      </div>

      <div className="card mb-4">
        <div className="card-body py-3 d-flex flex-wrap align-items-center gap-3">
          <div style={{ minWidth: 260 }}>
            <span className="form-label">Période de formation</span>
            <select
              className="form-select form-select-sm"
              value={periode}
              onChange={(event) => changerPeriode(event.target.value)}
            >
              <option value="">Toutes les périodes ({offre.periodes.length})</option>
              {offre.periodes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.code} — {item.libelle} ({item.seances_count} séances)
                </option>
              ))}
            </select>
          </div>
          <div className="flex-grow-1">
            <span className="form-label">Couverture du volume maquette</span>
            <Jauge valeur={offre.taux_couverture} largeur={260} />
          </div>
          <div>
            <span className="form-label d-block">Statut des séances</span>
            <StatutBadge
              statut={offre.seances_count ? 'planifie' : 'non_programme'}
              label={offre.seances_count ? `${offre.seances_count} séance(s)` : 'Aucune séance'}
            />
          </div>
        </div>
      </div>

      <div className="ept-tabs">
        {ONGLETS.map((onglet) => (
          <button
            key={onglet.id}
            type="button"
            className={`btn btn-sm ${ongletActif === onglet.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => changerOnglet(onglet.id)}
          >
            {onglet.label}
          </button>
        ))}
      </div>

      <Composant
        offre={offre}
        peutGerer={peutGerer}
        onRefresh={charger}
        onOuvrirSeance={setSeanceOuverte}
        onOuvrirQr={setQrSeanceId}
      />

      <SeanceDetailModal
        show={Boolean(seanceOuverte)}
        seanceId={seanceOuverte}
        peutGerer={peutGerer}
        onClose={() => setSeanceOuverte(null)}
        onChange={charger}
        onEdit={(seance) => { setSeanceOuverte(null); setSeanceEditee(seance); setFormOuvert(true) }}
        onOuvrirQr={setQrSeanceId}
      />

      <SeanceFormModal
        show={formOuvert}
        seance={seanceEditee}
        periode={periode}
        onClose={() => setFormOuvert(false)}
        onSaved={charger}
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
