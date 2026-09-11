import React, { useCallback, useEffect, useState } from 'react'
import { useToast } from '../../context/ToastContext'
import {
  getAnneeCourante,
  getEffectifsGroupes,
  getRefFormations,
  getRefScolarite,
  messageErreur,
  repartirGroupes,
} from '../../services/scolarite'

export default function Groupes() {
  const { showToast } = useToast()
  const [annee, setAnnee] = useState(null)
  const [groupes, setGroupes] = useState([])
  const [formations, setFormations] = useState([])
  const [niveaux, setNiveaux] = useState([])
  const [filtres, setFiltres] = useState({ ref_formation_id: '', niveau_id: '' })
  const [loading, setLoading] = useState(true)
  const [repartition, setRepartition] = useState(null)
  const [action, setAction] = useState(false)

  const charger = useCallback(async () => {
    setLoading(true)
    try {
      const params = { ...filtres }
      if (annee?.id) params.annee_academique_id = annee.id
      const res = await getEffectifsGroupes(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '')),
      )
      setGroupes(res.data)
    } catch (err) {
      showToast(messageErreur(err, 'Chargement des groupes impossible'), 'error')
    } finally {
      setLoading(false)
    }
  }, [filtres, annee, showToast])

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

  const repartir = async () => {
    if (!filtres.ref_formation_id || !filtres.niveau_id) {
      showToast('Choisissez une formation et un niveau avant de répartir', 'error')
      return
    }
    setAction(true)
    try {
      const res = await repartirGroupes({
        annee_academique_id: annee?.id,
        ref_formation_id: filtres.ref_formation_id,
        niveau_id: filtres.niveau_id,
      })
      setRepartition(res.data)
      showToast(`${res.data.affectations} étudiant(s) affecté(s)`)
      charger()
    } catch (err) {
      showToast(messageErreur(err, 'Répartition impossible'), 'error')
    } finally {
      setAction(false)
    }
  }

  const totalEffectif = groupes.reduce((somme, g) => somme + g.effectif, 0)

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <div>
          <h4 className="mb-0">Groupes pédagogiques</h4>
          <small className="text-muted">
            {annee ? `Année ${annee.libelle}` : 'Année courante non définie'} · {totalEffectif} étudiant(s) affecté(s)
          </small>
        </div>
        <button className="btn btn-sm btn-primary" disabled={action} onClick={repartir}>
          {action && <span className="spinner-border spinner-border-sm me-1"></span>}
          <i className="bi bi-diagram-3 me-1"></i>Répartir automatiquement
        </button>
      </div>

      <div className="card">
        <div className="card-body">
          <div className="row g-2 mb-3">
            <div className="col-md-4">
              <select
                className="form-select form-select-sm" value={filtres.ref_formation_id}
                onChange={(e) => setFiltres({ ...filtres, ref_formation_id: e.target.value })}
              >
                <option value="">Toutes les formations</option>
                {formations.map((f) => <option key={f.id} value={f.id}>{f.intitule}</option>)}
              </select>
            </div>
            <div className="col-md-3">
              <select
                className="form-select form-select-sm" value={filtres.niveau_id}
                onChange={(e) => setFiltres({ ...filtres, niveau_id: e.target.value })}
              >
                <option value="">Tous les niveaux</option>
                {niveaux.map((n) => <option key={n.id} value={n.id}>{n.code}</option>)}
              </select>
            </div>
          </div>

          {repartition?.echecs?.length > 0 && (
            <div className="alert alert-warning">
              <strong>{repartition.echecs.length} étudiant(s) non affecté(s)</strong>
              <div className="small mt-1">{repartition.echecs[0].motif}</div>
            </div>
          )}

          {loading ? (
            <div className="text-center py-4"><div className="spinner-border"></div></div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr>
                    <th>Groupe</th><th>Formation</th><th>Niveau</th>
                    <th>Effectif</th><th style={{ minWidth: '160px' }}>Remplissage</th><th>État</th>
                  </tr>
                </thead>
                <tbody>
                  {groupes.map((g) => {
                    const taux = g.capacite_max ? Math.round((g.effectif * 100) / g.capacite_max) : null
                    return (
                      <tr key={g.id}>
                        <td><strong>{g.nom}</strong></td>
                        <td>{g.ref_formation}</td>
                        <td>{g.niveau}</td>
                        <td>{g.effectif}{g.capacite_max ? ` / ${g.capacite_max}` : ''}</td>
                        <td>
                          {taux === null ? (
                            <span className="text-muted small">Sans limite</span>
                          ) : (
                            <div className="progress" style={{ height: '0.5rem' }}>
                              <div
                                className={`progress-bar bg-${taux >= 100 ? 'danger' : taux >= 80 ? 'warning' : 'success'}`}
                                style={{ width: `${Math.min(taux, 100)}%` }}
                              />
                            </div>
                          )}
                        </td>
                        <td>
                          {g.actif
                            ? <span className="badge bg-success">Actif</span>
                            : <span className="badge bg-secondary">Inactif</span>}
                        </td>
                      </tr>
                    )
                  })}
                  {groupes.length === 0 && (
                    <tr><td colSpan={6} className="text-center text-muted py-4">Aucun groupe défini.</td></tr>
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
