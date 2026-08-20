/** Périodes de formation et paramètres du moteur de planification. */
import { useCallback, useEffect, useState } from 'react'
import { FiPlus, FiSettings, FiTrash2 } from 'react-icons/fi'
import Modal from '@app/components/common/Modal'
import { fetchAcademicYears, fetchSemesters } from '@app/api/academics'
import {
  createPeriode,
  deletePeriode,
  fetchParametresPeriode,
  fetchPeriodes,
  updateParametresPeriode,
  updatePeriode,
} from '../../../api/eptinjs'
import { Chargement, EtatVide, StatutBadge } from '../../../components/Badges'

const JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

const PERIODE_VIDE = {
  academic_year: '',
  semester: '',
  code: '',
  libelle: '',
  date_debut: '',
  date_fin: '',
  ordre: 1,
  rythme_mensuel: 'aucun',
  statut: 'brouillon',
  is_active: true,
}

function FormulairePeriode({ show, periode, annees, semestres, onClose, onSaved }) {
  const [valeurs, setValeurs] = useState(PERIODE_VIDE)
  const [erreur, setErreur] = useState('')

  useEffect(() => {
    if (!show) return
    setErreur('')
    setValeurs(periode ? { ...PERIODE_VIDE, ...periode, semester: periode.semester || '' } : PERIODE_VIDE)
  }, [show, periode])

  const modifier = (champ) => (event) =>
    setValeurs((courant) => ({ ...courant, [champ]: event.target.value }))

  const soumettre = async (event) => {
    event.preventDefault()
    try {
      const corps = { ...valeurs, semester: valeurs.semester || null, ordre: Number(valeurs.ordre) || 1 }
      if (periode) await updatePeriode(periode.id, corps)
      else await createPeriode(corps)
      onSaved()
      onClose()
    } catch (err) {
      setErreur(err.message || 'Enregistrement impossible.')
    }
  }

  return (
    <Modal
      show={show}
      onClose={onClose}
      title={periode ? 'Modifier la période' : 'Nouvelle période de formation'}
      footer={
        <div className="d-flex gap-2 justify-content-end w-100">
          <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Annuler</button>
          <button type="submit" form="ept-periode-form" className="btn btn-injs-primary">Enregistrer</button>
        </div>
      }
    >
      <form id="ept-periode-form" onSubmit={soumettre} className="row g-3">
        {erreur && <div className="col-12"><div className="alert alert-danger py-2 mb-0">{erreur}</div></div>}

        <div className="col-md-6">
          <label className="form-label">Année académique</label>
          <select className="form-select" value={valeurs.academic_year} onChange={modifier('academic_year')} required>
            <option value="">— Sélectionner —</option>
            {annees.map((annee) => (
              <option key={annee.id} value={annee.id}>{annee.label}</option>
            ))}
          </select>
        </div>
        <div className="col-md-6">
          <label className="form-label">Semestre (optionnel)</label>
          <select className="form-select" value={valeurs.semester} onChange={modifier('semester')}>
            <option value="">Aucun</option>
            {semestres
              .filter((item) => !valeurs.academic_year || item.academic_year === valeurs.academic_year)
              .map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
          </select>
        </div>
        <div className="col-md-4">
          <label className="form-label">Code</label>
          <input type="text" className="form-control" value={valeurs.code} onChange={modifier('code')} required />
        </div>
        <div className="col-md-8">
          <label className="form-label">Libellé</label>
          <input
            type="text" className="form-control"
            value={valeurs.libelle} onChange={modifier('libelle')} required
          />
        </div>
        <div className="col-md-4">
          <label className="form-label">Début</label>
          <input
            type="date" className="form-control"
            value={valeurs.date_debut} onChange={modifier('date_debut')} required
          />
        </div>
        <div className="col-md-4">
          <label className="form-label">Fin</label>
          <input
            type="date" className="form-control"
            value={valeurs.date_fin} onChange={modifier('date_fin')} required
          />
        </div>
        <div className="col-md-4">
          <label className="form-label">Ordre</label>
          <input type="number" min="1" className="form-control" value={valeurs.ordre} onChange={modifier('ordre')} />
        </div>
        <div className="col-md-6">
          <label className="form-label">Rythme mensuel</label>
          <select className="form-select" value={valeurs.rythme_mensuel} onChange={modifier('rythme_mensuel')}>
            <option value="aucun">Continu</option>
            <option value="premiere_quinzaine">1re quinzaine du mois</option>
            <option value="seconde_quinzaine">2e quinzaine du mois</option>
          </select>
        </div>
        <div className="col-md-6">
          <label className="form-label">Statut</label>
          <select className="form-select" value={valeurs.statut} onChange={modifier('statut')}>
            <option value="brouillon">Brouillon</option>
            <option value="publiee">Publiée</option>
            <option value="cloturee">Clôturée</option>
          </select>
        </div>
      </form>
    </Modal>
  )
}

function FormulaireParametres({ show, periode, onClose }) {
  const [valeurs, setValeurs] = useState(null)
  const [erreur, setErreur] = useState('')

  useEffect(() => {
    if (!show || !periode) return
    fetchParametresPeriode(periode.id).then(setValeurs).catch((err) => setErreur(err.message))
  }, [show, periode])

  const modifier = (champ) => (event) => {
    const { type, checked, value } = event.target
    setValeurs((courant) => ({ ...courant, [champ]: type === 'checkbox' ? checked : value }))
  }

  const basculerJour = (index) =>
    setValeurs((courant) => {
      const actifs = new Set(courant.jours_actifs || [])
      if (actifs.has(index)) actifs.delete(index)
      else actifs.add(index)
      return { ...courant, jours_actifs: [...actifs].sort((a, b) => a - b) }
    })

  const soumettre = async (event) => {
    event.preventDefault()
    try {
      await updateParametresPeriode(periode.id, {
        ...valeurs,
        duree_seance_minutes: Number(valeurs.duree_seance_minutes),
        max_seances_par_jour: Number(valeurs.max_seances_par_jour),
        tolerance_capacite_pct: Number(valeurs.tolerance_capacite_pct),
      })
      onClose()
    } catch (err) {
      setErreur(err.message || 'Enregistrement impossible.')
    }
  }

  return (
    <Modal
      show={show}
      onClose={onClose}
      title={`Paramètres — ${periode?.code || ''}`}
      footer={
        <div className="d-flex gap-2 justify-content-end w-100">
          <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Fermer</button>
          <button type="submit" form="ept-params-form" className="btn btn-injs-primary">Enregistrer</button>
        </div>
      }
    >
      {!valeurs ? <Chargement /> : (
        <form id="ept-params-form" onSubmit={soumettre} className="row g-3">
          {erreur && <div className="col-12"><div className="alert alert-danger py-2 mb-0">{erreur}</div></div>}
          {valeurs.herite && (
            <div className="col-12">
              <div className="alert alert-info py-2 mb-0">
                Cette période hérite des paramètres par défaut ; enregistrer crée une surcharge.
              </div>
            </div>
          )}

          <div className="col-12">
            <label className="form-label">Jours ouvrés</label>
            <div className="d-flex flex-wrap gap-2">
              {JOURS.map((jour, index) => (
                <button
                  key={jour}
                  type="button"
                  className={`btn btn-sm ${
                    (valeurs.jours_actifs || []).includes(index) ? 'btn-injs-primary' : 'btn-outline-secondary'
                  }`}
                  onClick={() => basculerJour(index)}
                >
                  {jour}
                </button>
              ))}
            </div>
          </div>

          <div className="col-md-4 d-flex align-items-end">
            <div className="form-check">
              <input
                type="checkbox" className="form-check-input" id="matin_actif"
                checked={valeurs.matin_actif} onChange={modifier('matin_actif')}
              />
              <label className="form-check-label" htmlFor="matin_actif">Plage du matin</label>
            </div>
          </div>
          <div className="col-md-4">
            <label className="form-label">Matin — début</label>
            <input
              type="time" className="form-control"
              value={(valeurs.matin_debut || '').slice(0, 5)} onChange={modifier('matin_debut')}
            />
          </div>
          <div className="col-md-4">
            <label className="form-label">Matin — fin</label>
            <input
              type="time" className="form-control"
              value={(valeurs.matin_fin || '').slice(0, 5)} onChange={modifier('matin_fin')}
            />
          </div>

          <div className="col-md-4 d-flex align-items-end">
            <div className="form-check">
              <input
                type="checkbox" className="form-check-input" id="soir_actif"
                checked={valeurs.soir_actif} onChange={modifier('soir_actif')}
              />
              <label className="form-check-label" htmlFor="soir_actif">Plage de l’après-midi</label>
            </div>
          </div>
          <div className="col-md-4">
            <label className="form-label">Après-midi — début</label>
            <input
              type="time" className="form-control"
              value={(valeurs.soir_debut || '').slice(0, 5)} onChange={modifier('soir_debut')}
            />
          </div>
          <div className="col-md-4">
            <label className="form-label">Après-midi — fin</label>
            <input
              type="time" className="form-control"
              value={(valeurs.soir_fin || '').slice(0, 5)} onChange={modifier('soir_fin')}
            />
          </div>

          <div className="col-md-4">
            <label className="form-label">Durée d’une séance (min)</label>
            <input
              type="number" min="30" step="15" className="form-control"
              value={valeurs.duree_seance_minutes} onChange={modifier('duree_seance_minutes')}
            />
          </div>
          <div className="col-md-4">
            <label className="form-label">Séances max. / jour</label>
            <input
              type="number" min="1" max="6" className="form-control"
              value={valeurs.max_seances_par_jour} onChange={modifier('max_seances_par_jour')}
            />
          </div>
          <div className="col-md-4">
            <label className="form-label">Tolérance de capacité (%)</label>
            <input
              type="number" min="0" max="50" className="form-control"
              value={valeurs.tolerance_capacite_pct} onChange={modifier('tolerance_capacite_pct')}
            />
          </div>

          <div className="col-12">
            <div className="form-check">
              <input
                type="checkbox" className="form-check-input" id="verrou_salle"
                checked={valeurs.verrouiller_salle_par_groupe} onChange={modifier('verrouiller_salle_par_groupe')}
              />
              <label className="form-check-label" htmlFor="verrou_salle">
                Verrouiller la salle d’un groupe sur la journée
              </label>
            </div>
          </div>
        </form>
      )}
    </Modal>
  )
}

export default function OngletPeriodes({ onRefresh }) {
  const [periodes, setPeriodes] = useState([])
  const [annees, setAnnees] = useState([])
  const [semestres, setSemestres] = useState([])
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [formPeriode, setFormPeriode] = useState({ show: false, periode: null })
  const [formParams, setFormParams] = useState({ show: false, periode: null })

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const [liste, listeAnnees, listeSemestres] = await Promise.all([
        fetchPeriodes({ page_size: 100 }),
        fetchAcademicYears({ page_size: 50 }),
        fetchSemesters({ page_size: 100 }),
      ])
      setPeriodes(liste.results || [])
      setAnnees(Array.isArray(listeAnnees) ? listeAnnees : listeAnnees.results || [])
      setSemestres(Array.isArray(listeSemestres) ? listeSemestres : listeSemestres.results || [])
    } catch (err) {
      setErreur(err.message || 'Chargement des périodes impossible.')
    } finally {
      setChargement(false)
    }
  }, [])

  useEffect(() => { charger() }, [charger])

  const supprimer = async (periode) => {
    if (!window.confirm(`Supprimer la période « ${periode.libelle} » et ses séances ?`)) return
    try {
      await deletePeriode(periode.id)
      await charger()
      onRefresh?.()
    } catch (err) {
      setErreur(err.message || 'Suppression impossible.')
    }
  }

  if (chargement) return <Chargement />

  return (
    <div>
      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <div className="d-flex justify-content-end mb-3">
        <button
          type="button" className="btn btn-injs-primary btn-sm"
          onClick={() => setFormPeriode({ show: true, periode: null })}
        >
          <FiPlus className="me-1" /> Nouvelle période
        </button>
      </div>

      {periodes.length === 0 ? (
        <EtatVide message="Aucune période de formation. Créez-en une pour commencer à planifier." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Code</th><th>Libellé</th><th>Année</th><th>Fenêtre</th>
                  <th>Rythme</th><th>Programmes</th><th>Séances</th><th>Statut</th><th />
                </tr>
              </thead>
              <tbody>
                {periodes.map((periode) => (
                  <tr key={periode.id}>
                    <td><code>{periode.code}</code></td>
                    <td
                      role="button"
                      className="fw-semibold"
                      onClick={() => setFormPeriode({ show: true, periode })}
                    >
                      {periode.libelle}
                    </td>
                    <td>{periode.academic_year_label}</td>
                    <td className="text-nowrap small">{periode.date_debut} → {periode.date_fin}</td>
                    <td className="small">{periode.rythme_display}</td>
                    <td>{periode.programmes_count}</td>
                    <td>{periode.seances_count}</td>
                    <td><StatutBadge statut={periode.statut} label={periode.statut_display} /></td>
                    <td className="text-end text-nowrap">
                      <button
                        type="button" className="btn btn-sm btn-outline-secondary me-1"
                        onClick={() => setFormParams({ show: true, periode })}
                        title="Paramètres du moteur"
                      >
                        <FiSettings />
                      </button>
                      <button
                        type="button" className="btn btn-sm btn-outline-danger"
                        onClick={() => supprimer(periode)}
                      >
                        <FiTrash2 />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <FormulairePeriode
        show={formPeriode.show}
        periode={formPeriode.periode}
        annees={annees}
        semestres={semestres}
        onClose={() => setFormPeriode({ show: false, periode: null })}
        onSaved={() => { charger(); onRefresh?.() }}
      />

      <FormulaireParametres
        show={formParams.show}
        periode={formParams.periode}
        onClose={() => setFormParams({ show: false, periode: null })}
      />
    </div>
  )
}
