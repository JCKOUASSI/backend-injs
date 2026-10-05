import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useToast } from '../../context/ToastContext'
import StatutBadge from '../../components/scolarite/StatutBadge'
import '../../styles/campagnes.css'
import {
  getAnneeCourante,
  getRefFormations,
  getRefScolarite,
  listInscriptions,
  messageErreur,
  transitionInscription,
} from '../../services/scolarite'

const STATUTS = [
  ['BROUILLON', 'Brouillon'],
  ['EN_ATTENTE', 'En attente'],
  ['A_VALIDER', 'À valider'],
  ['VALIDEE', 'Validée'],
  ['REJETEE', 'Rejetée'],
  ['ANNULEE', 'Annulée'],
  ['SUSPENDUE', 'Suspendue'],
  ['TERMINEE', 'Terminée'],
]

/** Enchaîne les transitions jusqu'à la validation, en une seule action. */
const CHEMIN_VALIDATION = {
  BROUILLON: ['EN_ATTENTE', 'A_VALIDER', 'VALIDEE'],
  EN_ATTENTE: ['A_VALIDER', 'VALIDEE'],
  A_VALIDER: ['VALIDEE'],
}

export default function Inscriptions() {
  const { showToast } = useToast()
  const [inscriptions, setInscriptions] = useState([])
  const [annee, setAnnee] = useState(null)
  const [formations, setFormations] = useState([])
  const [niveaux, setNiveaux] = useState([])
  const [filtres, setFiltres] = useState({ statut: '', ref_formation_id: '', niveau_id: '', q: '' })
  const [loading, setLoading] = useState(true)
  const [enCours, setEnCours] = useState(null)

  const charger = useCallback(async () => {
    setLoading(true)
    try {
      const params = Object.fromEntries(
        Object.entries(filtres).filter(([, valeur]) => valeur !== ''),
      )
      const res = await listInscriptions(params)
      setInscriptions(res.data)
    } catch (err) {
      showToast(messageErreur(err, 'Chargement des inscriptions impossible'), 'error')
    } finally {
      setLoading(false)
    }
  }, [filtres, showToast])

  useEffect(() => {
    (async () => {
      const [anneeCourante, formationsRes, niveauxRes] = await Promise.all([
        getAnneeCourante().catch(() => null),
        getRefFormations().catch(() => ({ data: [] })),
        getRefScolarite('niveaux', { actif: 1 }).catch(() => ({ data: [] })),
      ])
      setAnnee(anneeCourante)
      setFormations(formationsRes.data || [])
      setNiveaux(niveauxRes.data || [])
    })()
  }, [])

  useEffect(() => { charger() }, [charger])

  const valider = async (inscription) => {
    const etapes = CHEMIN_VALIDATION[inscription.statut]
    if (!etapes) return
    setEnCours(inscription.id)
    try {
      for (const statut of etapes) {
        await transitionInscription(inscription.id, { statut })
      }
      showToast('Inscription validée')
      charger()
    } catch (err) {
      showToast(messageErreur(err, 'Validation impossible'), 'error')
    } finally {
      setEnCours(null)
    }
  }

  const kpis = useMemo(() => ({
    total: inscriptions.length,
    validees: inscriptions.filter((i) => i.statut === 'VALIDEE').length,
    attente: inscriptions.filter((i) => ['BROUILLON', 'EN_ATTENTE', 'A_VALIDER'].includes(i.statut)).length,
    terminees: inscriptions.filter((i) => i.statut === 'TERMINEE').length,
  }), [inscriptions])

  return (
    <div className="camp-page">
      <div className="camp-hero">
        <div className="camp-hero-text">
          <h1 className="camp-hero-title"><i className="bi bi-person-badge"></i>Inscriptions administratives</h1>
          <p className="camp-hero-sub">{annee ? `Année ${annee.libelle}` : 'Année courante non définie'} · Dossiers étudiants immatriculés depuis les admissions.</p>
        </div>
        <div className="camp-hero-side">
          <span className="plaquette plaquette-primary"><i className="bi bi-mortarboard"></i>{annee?.libelle || 'Année en cours'}</span>
          <Link to="/scolarite/admissions" className="camp-submit-btn text-decoration-none">
            <i className="bi bi-person-plus me-1"></i>Inscrire un admis
          </Link>
        </div>
      </div>

      <div className="camp-kpi-row">
        <div className="camp-kpi">
          <div><span className="camp-kpi-label">Inscriptions</span><span className="camp-kpi-value">{kpis.total}</span></div>
          <span className="camp-kpi-icon is-blue"><i className="bi bi-person-badge"></i></span>
        </div>
        <div className="camp-kpi">
          <div><span className="camp-kpi-label">Validées</span><span className="camp-kpi-value">{kpis.validees}</span></div>
          <span className="camp-kpi-icon is-green"><i className="bi bi-check2-circle"></i></span>
        </div>
        <div className="camp-kpi">
          <div><span className="camp-kpi-label">En attente</span><span className="camp-kpi-value">{kpis.attente}</span></div>
          <span className="camp-kpi-icon is-amber"><i className="bi bi-hourglass-split"></i></span>
        </div>
        <div className="camp-kpi">
          <div><span className="camp-kpi-label">Terminées</span><span className="camp-kpi-value">{kpis.terminees}</span></div>
          <span className="camp-kpi-icon is-slate"><i className="bi bi-mortarboard"></i></span>
        </div>
      </div>

      <div className="camp-panel card">
        <div className="camp-panel-head">
          <h2 className="camp-panel-title"><i className="bi bi-list-check"></i>Dossiers d&apos;inscription</h2>
          <span className="camp-count-pill">{inscriptions.length} dossier{inscriptions.length > 1 ? 's' : ''}</span>
        </div>
        <div className="camp-panel-body">
          <div className="camp-filters mb-3">
            <div className="camp-search">
              <i className="bi bi-search"></i>
              <input
                className="form-control form-control-sm"
                placeholder="Matricule, nom…"
                aria-label="Rechercher une inscription"
                value={filtres.q}
                onChange={(e) => setFiltres({ ...filtres, q: e.target.value })}
              />
            </div>
            <select
              className="form-select form-select-sm camp-filter-select" aria-label="Filtrer par statut" value={filtres.statut}
              onChange={(e) => setFiltres({ ...filtres, statut: e.target.value })}
            >
              <option value="">Tous les statuts</option>
              {STATUTS.map(([valeur, libelle]) => (
                <option key={valeur} value={valeur}>{libelle}</option>
              ))}
            </select>
            <select
              className="form-select form-select-sm camp-filter-select" aria-label="Filtrer par formation" value={filtres.ref_formation_id}
              onChange={(e) => setFiltres({ ...filtres, ref_formation_id: e.target.value })}
            >
              <option value="">Toutes les formations</option>
              {formations.map((f) => <option key={f.id} value={f.id}>{f.intitule}</option>)}
            </select>
            <select
              className="form-select form-select-sm camp-filter-select" aria-label="Filtrer par niveau" value={filtres.niveau_id}
              onChange={(e) => setFiltres({ ...filtres, niveau_id: e.target.value })}
            >
              <option value="">Tous les niveaux</option>
              {niveaux.map((n) => <option key={n.id} value={n.id}>{n.code}</option>)}
            </select>
          </div>

          {loading ? (
            <div className="text-center py-4"><div className="spinner-border"></div></div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0 camp-table">
                <thead className="table-light">
                  <tr>
                    <th>Matricule</th><th>Étudiant</th><th>Formation</th><th>Niveau</th>
                    <th>Type</th><th>Statut</th><th className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {inscriptions.map((i) => (
                    <tr key={i.id}>
                      <td><code className="camp-candidatures">{i.matricule}</code></td>
                      <td><span className="camp-link">{i.etudiant}</span></td>
                      <td>{i.ref_formation}</td>
                      <td>{i.niveau}</td>
                      <td><small className="text-muted">{i.type_inscription_libelle}</small></td>
                      <td><StatutBadge statut={i.statut} libelle={i.statut_libelle} /></td>
                      <td className="text-end">
                        <div className="btn-group btn-group-sm">
                          {CHEMIN_VALIDATION[i.statut] && (
                            <button
                              className="btn btn-outline-success camp-action-btn"
                              disabled={enCours === i.id}
                              onClick={() => valider(i)}
                            >
                              {enCours === i.id && <span className="spinner-border spinner-border-sm me-1"></span>}
                              <i className="bi bi-check2-circle me-1"></i>Valider
                            </button>
                          )}
                          <Link
                            className="btn btn-outline-primary camp-action-btn"
                            to={`/scolarite/etudiants/${i.etudiant_id}`}
                          >
                            <i className="bi bi-person-lines-fill me-1"></i>Fiche
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {inscriptions.length === 0 && (
                    <tr><td colSpan={7}>
                      <div className="camp-empty"><i className="bi bi-inbox"></i>Aucune inscription pour ces critères. Inscrivez un admis depuis les admissions.</div>
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
