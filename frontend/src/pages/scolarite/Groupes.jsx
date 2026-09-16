import React, { useCallback, useEffect, useMemo, useState } from 'react'
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

  const totalEffectif = useMemo(
    () => groupes.reduce((somme, g) => somme + g.effectif, 0),
    [groupes],
  )

  const stats = useMemo(() => {
    const totalGroupes = groupes.length
    const actifs = groupes.filter((g) => g.actif).length
    const avecCapacite = groupes.filter((g) => g.capacite_max)
    const tauxMoyen = avecCapacite.length
      ? Math.round(
          avecCapacite.reduce((acc, g) => acc + (g.effectif * 100) / g.capacite_max, 0) /
            avecCapacite.length,
        )
      : null
    return { totalGroupes, actifs, tauxMoyen }
  }, [groupes])

  return (
    <div className="container-fluid py-4" style={{ background: 'linear-gradient(180deg, #F0F5FB 0%, #E8F0F8 100%)', minHeight: 'calc(100vh - 70px)' }}>
      {/* ── En-tête ── */}
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div>
          <h1 className="h4 mb-0 fw-bold text-dark d-flex align-items-center gap-2">
            <i className="bi bi-people-fill text-primary"></i>
            Groupes pédagogiques
          </h1>
          <p className="text-muted small mb-0 mt-1">
            {annee ? `Année académique ${annee.libelle}` : 'Année courante non définie'} · {totalEffectif} étudiant(s) affecté(s) aux sections TD/TP.
          </p>
        </div>
        <button
          className="btn btn-primary d-flex align-items-center gap-2 fw-semibold shadow-sm"
          style={{ borderRadius: '10px', padding: '0.5rem 1.1rem' }}
          disabled={action}
          onClick={repartir}
        >
          {action ? (
            <span className="spinner-border spinner-border-sm me-1"></span>
          ) : (
            <i className="bi bi-diagram-3"></i>
          )}
          Répartir automatiquement
        </button>
      </div>

      {/* ── Plaquettes KPIs ── */}
      <div className="row g-3 mb-4">
        <div className="col-md-3">
          <div
            className="p-3 shadow-sm rounded-4 text-white d-flex align-items-center gap-3"
            style={{ background: 'linear-gradient(135deg, #0e58ab 0%, #0b478a 100%)' }}
          >
            <div className="rounded-3 p-2 bg-white bg-opacity-25 fs-4">
              <i className="bi bi-grid-3x3-gap-fill"></i>
            </div>
            <div>
              <div className="small text-white-50 text-uppercase fw-semibold">Total Groupes</div>
              <div className="fs-4 fw-bold">{stats.totalGroupes}</div>
            </div>
          </div>
        </div>

        <div className="col-md-3">
          <div className="p-3 bg-white shadow-sm rounded-4 border d-flex align-items-center gap-3">
            <div className="rounded-3 p-2 text-primary fs-4" style={{ background: 'rgba(14, 88, 171, 0.1)' }}>
              <i className="bi bi-person-check-fill"></i>
            </div>
            <div>
              <div className="small text-muted text-uppercase fw-semibold">Étudiants Affectés</div>
              <div className="fs-4 fw-bold text-dark">{totalEffectif}</div>
            </div>
          </div>
        </div>

        <div className="col-md-3">
          <div className="p-3 bg-white shadow-sm rounded-4 border d-flex align-items-center gap-3">
            <div className="rounded-3 p-2 text-success fs-4" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
              <i className="bi bi-pie-chart-fill"></i>
            </div>
            <div>
              <div className="small text-muted text-uppercase fw-semibold">Taux Remplissage</div>
              <div className="fs-4 fw-bold text-success">{stats.tauxMoyen !== null ? `${stats.tauxMoyen}%` : '—'}</div>
            </div>
          </div>
        </div>

        <div className="col-md-3">
          <div className="p-3 bg-white shadow-sm rounded-4 border d-flex align-items-center gap-3">
            <div className="rounded-3 p-2 text-info fs-4" style={{ background: 'rgba(6, 182, 212, 0.1)' }}>
              <i className="bi bi-check2-circle"></i>
            </div>
            <div>
              <div className="small text-muted text-uppercase fw-semibold">Groupes Actifs</div>
              <div className="fs-4 fw-bold text-dark">{stats.actifs}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Filtres & Liste ── */}
      <div className="card shadow-sm border-0 rounded-4 mb-4" style={{ background: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(12px)' }}>
        <div className="card-body p-4">
          <div className="row g-3 mb-4">
            <div className="col-md-4">
              <label className="form-label small text-muted fw-semibold">Formation</label>
              <select
                className="form-select shadow-sm"
                value={filtres.ref_formation_id}
                onChange={(e) => setFiltres({ ...filtres, ref_formation_id: e.target.value })}
              >
                <option value="">Toutes les formations</option>
                {formations.map((f) => <option key={f.id} value={f.id}>{f.intitule}</option>)}
              </select>
            </div>
            <div className="col-md-3">
              <label className="form-label small text-muted fw-semibold">Niveau</label>
              <select
                className="form-select shadow-sm"
                value={filtres.niveau_id}
                onChange={(e) => setFiltres({ ...filtres, niveau_id: e.target.value })}
              >
                <option value="">Tous les niveaux</option>
                {niveaux.map((n) => <option key={n.id} value={n.id}>{n.code}</option>)}
              </select>
            </div>
          </div>

          {repartition?.echecs?.length > 0 && (
            <div className="alert alert-warning border-0 rounded-3 shadow-sm mb-3">
              <strong>{repartition.echecs.length} étudiant(s) non affecté(s)</strong>
              <div className="small mt-1">{repartition.echecs[0].motif}</div>
            </div>
          )}

          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Chargement...</span>
              </div>
            </div>
          ) : (
            <div className="table-responsive rounded-3 overflow-hidden border">
              <table className="table table-hover align-middle mb-0">
                <thead style={{ background: '#0B1F3A', color: '#ffffff' }}>
                  <tr>
                    <th style={{ background: '#0B1F3A', color: '#fff', padding: '0.85rem 1rem' }}>Groupe</th>
                    <th style={{ background: '#0B1F3A', color: '#fff' }}>Formation</th>
                    <th style={{ background: '#0B1F3A', color: '#fff' }}>Niveau</th>
                    <th style={{ background: '#0B1F3A', color: '#fff' }}>Effectif</th>
                    <th style={{ minWidth: '180px', background: '#0B1F3A', color: '#fff' }}>Remplissage</th>
                    <th style={{ background: '#0B1F3A', color: '#fff' }}>État</th>
                  </tr>
                </thead>
                <tbody>
                  {groupes.map((g) => {
                    const taux = g.capacite_max ? Math.round((g.effectif * 100) / g.capacite_max) : null
                    return (
                      <tr key={g.id}>
                        <td>
                          <strong className="text-dark">{g.nom}</strong>
                        </td>
                        <td>{g.ref_formation}</td>
                        <td><span className="badge bg-light text-dark border">{g.niveau}</span></td>
                        <td>
                          <span className="fw-semibold">{g.effectif}</span>
                          {g.capacite_max ? <span className="text-muted small"> / {g.capacite_max}</span> : ''}
                        </td>
                        <td>
                          {taux === null ? (
                            <span className="text-muted small">Sans limite</span>
                          ) : (
                            <div>
                              <div className="d-flex justify-content-between small text-muted mb-1">
                                <span>{taux}%</span>
                                <span>{g.effectif}/{g.capacite_max}</span>
                              </div>
                              <div className="progress" style={{ height: '0.55rem', borderRadius: '999px' }}>
                                <div
                                  className={`progress-bar bg-${taux >= 100 ? 'danger' : taux >= 80 ? 'warning' : 'success'}`}
                                  style={{ width: `${Math.min(taux, 100)}%` }}
                                />
                              </div>
                            </div>
                          )}
                        </td>
                        <td>
                          {g.actif ? (
                            <span className="badge bg-success-subtle text-success border border-success-subtle px-2 py-1">
                              Actif
                            </span>
                          ) : (
                            <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1">
                              Inactif
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                  {groupes.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center text-muted py-5">
                        <i className="bi bi-inbox fs-3 d-block text-muted mb-2"></i>
                        Aucun groupe défini pour les filtres sélectionnés.
                      </td>
                    </tr>
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
