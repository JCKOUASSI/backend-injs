import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useToast } from '../../context/ToastContext'
import StatutBadge from '../../components/scolarite/StatutBadge'
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

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <div>
          <h4 className="mb-0">Inscriptions administratives</h4>
          <small className="text-muted">{annee ? `Année ${annee.libelle}` : 'Année courante non définie'}</small>
        </div>
        <Link to="/scolarite/admissions" className="btn btn-sm btn-outline-primary">
          <i className="bi bi-person-plus me-1"></i>Inscrire un admis
        </Link>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="row g-2 mb-3">
            <div className="col-md-3">
              <input
                className="form-control form-control-sm"
                placeholder="Matricule, nom…"
                value={filtres.q}
                onChange={(e) => setFiltres({ ...filtres, q: e.target.value })}
              />
            </div>
            <div className="col-md-2">
              <select
                className="form-select form-select-sm" value={filtres.statut}
                onChange={(e) => setFiltres({ ...filtres, statut: e.target.value })}
              >
                <option value="">Tous les statuts</option>
                {STATUTS.map(([valeur, libelle]) => (
                  <option key={valeur} value={valeur}>{libelle}</option>
                ))}
              </select>
            </div>
            <div className="col-md-3">
              <select
                className="form-select form-select-sm" value={filtres.ref_formation_id}
                onChange={(e) => setFiltres({ ...filtres, ref_formation_id: e.target.value })}
              >
                <option value="">Toutes les formations</option>
                {formations.map((f) => <option key={f.id} value={f.id}>{f.intitule}</option>)}
              </select>
            </div>
            <div className="col-md-2">
              <select
                className="form-select form-select-sm" value={filtres.niveau_id}
                onChange={(e) => setFiltres({ ...filtres, niveau_id: e.target.value })}
              >
                <option value="">Tous les niveaux</option>
                {niveaux.map((n) => <option key={n.id} value={n.id}>{n.code}</option>)}
              </select>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-4"><div className="spinner-border"></div></div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Matricule</th><th>Étudiant</th><th>Formation</th><th>Niveau</th>
                    <th>Type</th><th>Statut</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {inscriptions.map((i) => (
                    <tr key={i.id}>
                      <td><code>{i.matricule}</code></td>
                      <td>{i.etudiant}</td>
                      <td>{i.ref_formation}</td>
                      <td>{i.niveau}</td>
                      <td><small>{i.type_inscription_libelle}</small></td>
                      <td><StatutBadge statut={i.statut} libelle={i.statut_libelle} /></td>
                      <td className="text-end">
                        <div className="btn-group btn-group-sm">
                          {CHEMIN_VALIDATION[i.statut] && (
                            <button
                              className="btn btn-outline-success"
                              disabled={enCours === i.id}
                              onClick={() => valider(i)}
                            >
                              {enCours === i.id && <span className="spinner-border spinner-border-sm me-1"></span>}
                              Valider
                            </button>
                          )}
                          <Link
                            className="btn btn-outline-primary"
                            to={`/scolarite/etudiants/${i.etudiant_id}`}
                          >
                            Fiche
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {inscriptions.length === 0 && (
                    <tr><td colSpan={7} className="text-center text-muted py-4">Aucune inscription.</td></tr>
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
