import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../services/api'
import { canActScolarite } from '../../utils/roles'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'

const STATUTS = ['', 'BROUILLON', 'PLANIFIEE', 'OUVERTE', 'SUSPENDUE', 'CLOTUREE', 'ANNULEE', 'ARCHIVEE']
const BADGE_STATUT = {
  BROUILLON: 'secondary', PLANIFIEE: 'info', OUVERTE: 'success',
  SUSPENDUE: 'warning', CLOTUREE: 'dark', ANNULEE: 'danger', ARCHIVEE: 'dark',
}

export default function Campagnes() {
  const { user } = useAuth()
  const toast = useToast()
  const peutAgir = canActScolarite(user)

  const [campagnes, setCampagnes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [enCours, setEnCours] = useState(false)
  const [form, setForm] = useState({
    libelle: '', annee_academique_id: '', ref_formation_id: '',
    date_ouverture: '', date_fermeture: '', quota_admissibles: '', quota_admis: '',
  })
  const [options, setOptions] = useState({ annees: [], formations: [] })

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const res = await api.get('/admissions/campagnes/')
      setCampagnes(res.data)
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Chargement des campagnes impossible.', 'error')
    } finally {
      setChargement(false)
    }
  }, [toast])

  useEffect(() => { charger() }, [charger])

  useEffect(() => {
    if (!peutAgir) return
    Promise.all([
      api.get('/scolarite/ref/annees/', { params: { actif: 'true' } }),
      api.get('/scolarite/ref/formations/'),
    ])
      .then(([annees, formations]) => setOptions({ annees: annees.data, formations: formations.data }))
      .catch(() => toast.showToast('Chargement des référentiels impossible.', 'error'))
  }, [peutAgir, toast])

  const creer = async (e) => {
    e.preventDefault()
    setEnCours(true)
    try {
      await api.post('/admissions/campagnes/', {
        ...form,
        annee_academique_id: Number(form.annee_academique_id) || undefined,
        ref_formation_id: Number(form.ref_formation_id) || undefined,
        quota_admissibles: form.quota_admissibles || undefined,
        quota_admis: form.quota_admis || undefined,
      })
      toast.showToast('Campagne créée en brouillon.')
      setForm({ libelle: '', annee_academique_id: '', ref_formation_id: '', date_ouverture: '', date_fermeture: '', quota_admissibles: '', quota_admis: '' })
      charger()
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Création impossible.', 'error')
    } finally {
      setEnCours(false)
    }
  }

  const transition = async (campagne, statut, confirmation) => {
    if (confirmation && !window.confirm(confirmation)) return
    setEnCours(true)
    try {
      await api.post(`/admissions/campagnes/${campagne.id}/transition/`, { statut })
      toast.showToast(`Campagne ${statut.toLowerCase()}.`)
      charger()
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Transition impossible.', 'error')
    } finally {
      setEnCours(false)
    }

  return (
    <div className="container-fluid py-4">
      <h1 className="h4 mb-3"><i className="bi bi-megaphone me-2"></i>Campagnes d'admission</h1>

      {peutAgir && (
        <div className="card mb-4">
          <div className="card-body">
            <h2 className="h6 card-title"><i className="bi bi-plus-circle me-1"></i>Nouvelle campagne</h2>
            <form className="row g-2" onSubmit={creer}>
              <div className="col-md-3">
                <input className="form-control" placeholder="Libellé" required value={form.libelle}
                       onChange={(e) => setForm({ ...form, libelle: e.target.value })} />
              </div>
              <div className="col-md-2">
                <select className="form-select" required value={form.annee_academique_id}
                        onChange={(e) => setForm({ ...form, annee_academique_id: e.target.value })}>
                  <option value="">Année…</option>
                  {options.annees.map((a) => <option key={a.id} value={a.id}>{a.libelle}</option>)}
                </select>
              </div>
              <div className="col-md-2">
                <select className="form-select" required value={form.ref_formation_id}
                        onChange={(e) => setForm({ ...form, ref_formation_id: e.target.value })}>
                  <option value="">Formation…</option>
                  {options.formations.map((f) => <option key={f.id} value={f.id}>{f.intitule}</option>)}
                </select>
              </div>
              <div className="col-md-2">
                <input type="date" className="form-control" value={form.date_ouverture}
                       onChange={(e) => setForm({ ...form, date_ouverture: e.target.value })} />
              </div>
              <div className="col-md-2">
                <input type="date" className="form-control" value={form.date_fermeture}
                       onChange={(e) => setForm({ ...form, date_fermeture: e.target.value })} />
              </div>
              <div className="col-md-1">
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
                <th>Libellé</th><th>Formation</th><th>Année</th><th>Ouverture</th>
                <th>Fermeture</th><th>Statut</th><th>Candidatures</th>
                {peutAgir && <th className="text-end">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {chargement ? (
                <tr><td colSpan={8} className="text-center py-4"><div className="spinner-border spinner-border-sm" /></td></tr>
              ) : campagnes.length === 0 ? (
                <tr><td colSpan={8} className="text-center text-muted py-4">Aucune campagne.</td></tr>
              ) : campagnes.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/scolarite/campagnes/${c.id}`}>{c.libelle}</Link></td>
                  <td>{c.ref_formation_id}</td>
                  <td>{c.annee_academique_id}</td>
                  <td>{c.date_ouverture || '—'}</td>
                  <td>{c.date_fermeture || '—'}</td>
                  <td><span className={`badge text-bg-${BADGE_STATUT[c.statut] || 'secondary'}`}>{c.statut}</span></td>
                  <td>{c.nb_candidatures}</td>
                  {peutAgir && (
                    <td className="text-end">
                      <div className="btn-group btn-group-sm">
                        {c.statut === 'BROUILLON' && (
                          <button className="btn btn-outline-info" disabled={enCours}
                                  onClick={() => transition(c, 'PLANIFIEE')}>Planifier</button>
                        )}
                        {c.statut === 'PLANIFIEE' && (
                          <button className="btn btn-outline-success" disabled={enCours}
                                  onClick={() => transition(c, 'OUVERTE', 'Ouvrir la campagne aux candidatures ?')}>Ouvrir</button>
                        )}
                        {c.statut === 'OUVERTE' && (
                          <>
                            <button className="btn btn-outline-warning" disabled={enCours}
                                    onClick={() => transition(c, 'SUSPENDUE')}>Suspendre</button>
                            <button className="btn btn-outline-dark" disabled={enCours}
                                    onClick={() => transition(c, 'CLOTUREE', 'Clôturer ? Plus aucune candidature ne sera acceptée.')}>Clôturer</button>
                          </>
                        )}
                        {c.statut === 'SUSPENDUE' && (
                          <button className="btn btn-outline-success" disabled={enCours}
                                  onClick={() => transition(c, 'OUVERTE')}>Réouvrir</button>
                        )}
                        {c.statut === 'CLOTUREE' && (
                          <button className="btn btn-outline-secondary" disabled={enCours}
                                  onClick={() => transition(c, 'ARCHIVEE')}>Archiver</button>
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
  }
