import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../services/api'
import { canActScolarite } from '../../utils/roles'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'

const STATUTS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'BROUILLON', label: 'Brouillons' },
  { value: 'VALIDEE', label: 'Validées' },
  { value: 'ACTIVE', label: 'Actives' },
  { value: 'ARCHIVEE', label: 'Archivées' },
]

const BADGE_STATUT = {
  BROUILLON: 'secondary',
  VALIDEE: 'info',
  ACTIVE: 'success',
  ARCHIVEE: 'dark',
}

export default function Maquettes() {
  const { user } = useAuth()
  const toast = useToast()
  const peutAgir = canActScolarite(user)

  const [maquettes, setMaquettes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [filtreStatut, setFiltreStatut] = useState('')
  const [enCours, setEnCours] = useState(false)
  const [form, setForm] = useState({
    annee_academique_id: '', ref_formation_id: '', niveau_id: '', libelle: '',
  })
  const [options, setOptions] = useState({ annees: [], formations: [], niveaux: [] })

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const params = {}
      if (filtreStatut) params.statut = filtreStatut
      const res = await api.get('/scolarite/maquettes/', { params })
      setMaquettes(res.data)
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Chargement des maquettes impossible.', 'error')
    } finally {
      setChargement(false)
    }
  }, [filtreStatut, toast])

  useEffect(() => { charger() }, [charger])

  useEffect(() => {
    if (!peutAgir) return
    ;(async () => {
      try {
        const [annees, formations, niveaux] = await Promise.all([
          api.get('/scolarite/ref/annees/', { params: { actif: 'true' } }),
          api.get('/scolarite/ref/formations/'),
          api.get('/scolarite/ref/niveaux/', { params: { actif: 'true' } }),
        ])
        setOptions({ annees: annees.data, formations: formations.data, niveaux: niveaux.data })
      } catch {
        toast.showToast('Chargement des référentiels impossible.', 'error')
      }
    })()
  }, [peutAgir, toast])

  const creer = async (e) => {
    e.preventDefault()
    setEnCours(true)
    try {
      const res = await api.post('/scolarite/maquettes/creer/', {
        ...form,
        annee_academique_id: Number(form.annee_academique_id) || undefined,
        ref_formation_id: Number(form.ref_formation_id) || undefined,
        niveau_id: Number(form.niveau_id) || undefined,
      })
      toast.showToast(`Maquette v${res.data.version} créée en brouillon.`)
      setForm({ annee_academique_id: '', ref_formation_id: '', niveau_id: '', libelle: '' })
      charger()
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Création impossible.', 'error')
    } finally {
      setEnCours(false)
    }
  }

  const action = async (maquette, verbe, confirmation) => {
    if (confirmation && !window.confirm(confirmation)) return
    setEnCours(true)
    try {
      const res = await api.post(`/scolarite/maquettes/${maquette.id}/${verbe}/`, {})
      toast.showToast(res.data?.detail || 'Opération effectuée.')
      charger()
    } catch (err) {
      const problemes = err.response?.data?.problemes
      toast.showToast(
        problemes?.length ? problemes.join(' ') : (err.response?.data?.error || 'Action impossible.'),
        'error',
      )
    } finally {
      setEnCours(false)
    }
  }

  return (
    <div className="container-fluid py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="h4 mb-0"><i className="bi bi-diagram-3 me-2"></i>Maquettes pédagogiques LMD</h1>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <label className="form-label small text-muted">Filtrer par statut</label>
          <select className="form-select" value={filtreStatut} onChange={(e) => setFiltreStatut(e.target.value)}>
            {STATUTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      {peutAgir && (
        <div className="card mb-4">
          <div className="card-body">
            <h2 className="h6 card-title"><i className="bi bi-plus-circle me-1"></i>Nouvelle maquette</h2>
            <form className="row g-2" onSubmit={creer}>
              <div className="col-md-3">
                <select className="form-select" required value={form.annee_academique_id}
                        onChange={(e) => setForm({ ...form, annee_academique_id: e.target.value })}>
                  <option value="">Année académique…</option>
                  {options.annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
                </select>
              </div>
              <div className="col-md-3">
                <select className="form-select" required value={form.ref_formation_id}
                        onChange={(e) => setForm({ ...form, ref_formation_id: e.target.value })}>
                  <option value="">Formation…</option>
                  {options.formations.map((f) => <option key={f.id} value={f.id}>{f.intitule}</option>)}
                </select>
              </div>
              <div className="col-md-2">
                <select className="form-select" required value={form.niveau_id}
                        onChange={(e) => setForm({ ...form, niveau_id: e.target.value })}>
                  <option value="">Niveau…</option>
                  {options.niveaux.map((n) => <option key={n.id} value={n.id}>{n.code}</option>)}
                </select>
              </div>
              <div className="col-md-2">
                <input className="form-control" placeholder="Libellé (optionnel)"
                       value={form.libelle} onChange={(e) => setForm({ ...form, libelle: e.target.value })} />
              </div>
              <div className="col-md-2">
                <button className="btn btn-primary w-100" disabled={enCours}>Créer</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light">
              <tr>
                <th>Formation</th><th>Niveau</th><th>Parcours</th><th>Année</th>
                <th>Version</th><th>Statut</th><th>UE</th><th>Crédits</th>
                {peutAgir && <th className="text-end">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {chargement ? (
                <tr><td colSpan={9} className="text-center py-4"><div className="spinner-border spinner-border-sm" /></td></tr>
              ) : maquettes.length === 0 ? (
                <tr><td colSpan={9} className="text-center text-muted py-4">Aucune maquette.</td></tr>
              ) : maquettes.map((m) => (
                <tr key={m.id}>
                  <td><Link to={`/scolarite/maquettes/${m.id}`}>{m.ref_formation}</Link></td>
                  <td>{m.niveau}</td>
                  <td>{m.parcours || '—'}</td>
                  <td>{m.annee_academique}</td>
                  <td>v{m.version}</td>
                  <td><span className={`badge text-bg-${BADGE_STATUT[m.statut] || 'secondary'}`}>{m.statut}</span></td>
                  <td>{m.nb_ue}</td>
                  <td>{m.total_credits}</td>
                  {peutAgir && (
                    <td className="text-end">
                      <div className="btn-group btn-group-sm">
                        {m.statut === 'BROUILLON' && (
                          <button className="btn btn-outline-info" disabled={enCours}
                                  onClick={() => action(m, 'valider', 'Valider cette maquette (contenu gelé) ?')}>
                            Valider
                          </button>
                        )}
                        {m.statut === 'VALIDEE' && (
                          <button className="btn btn-outline-success" disabled={enCours}
                                  onClick={() => action(m, 'activer', 'Activer cette maquette (immuable) ?')}>
                            Activer
                          </button>
                        )}
                        {m.statut === 'ACTIVE' && (
                          <button className="btn btn-outline-dark" disabled={enCours}
                                  onClick={() => action(m, 'archiver', 'Archiver cette maquette ?')}>
                            Archiver
                          </button>
                        )}
                        {m.statut !== 'BROUILLON' && (
                          <button className="btn btn-outline-secondary" disabled={enCours}
                                  onClick={() => action(m, 'cloner', 'Créer une nouvelle version (clonage) ?')}>
                            Cloner
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
