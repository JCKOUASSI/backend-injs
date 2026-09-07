import React, { useCallback, useEffect, useState } from 'react'
import api from '../../services/api'
import { canActScolarite } from '../../utils/roles'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'

const BADGE_STATUT = {
  BROUILLON: 'secondary', SOUMISE: 'info', EN_INSTRUCTION: 'info',
  A_COMPLETER: 'warning', AVIS_PEDAGOGIQUE: 'primary', DECISION: 'primary',
  VALIDEE: 'success', REJETEE: 'danger', APPLIQUEE: 'dark',
}

export default function Equivalences() {
  const { user } = useAuth()
  const toast = useToast()
  const peutAgir = canActScolarite(user)

  const [demandes, setDemandes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [enCours, setEnCours] = useState(false)
  const [selection, setSelection] = useState(null)
  const [form, setForm] = useState({
    type_demande: 'DISPENSE', etudiant_id: '', annee_academique_id: '',
    ref_formation_id: '', niveau_id: '', etablissement_origine: '', diplome_origine: '',
  })
  const [formDecision, setFormDecision] = useState({
    decision: 'FAVORABLE', credits_reconnus: '', note_transferee: '',
    autorite_validation: 'Direction des études INJS', analyse_pedagogique: '',
  })
  const [options, setOptions] = useState({ annees: [], formations: [], niveaux: [], etudiants: [] })

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const res = await api.get('/equivalences/demandes/')
      setDemandes(res.data)
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Chargement impossible.', 'error')
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
      api.get('/scolarite/ref/niveaux/', { params: { actif: 'true' } }),
      api.get('/scolarite/etudiants/'),
    ])
      .then(([annees, formations, niveaux, etudiants]) => setOptions({
        annees: annees.data, formations: formations.data,
        niveaux: niveaux.data, etudiants: etudiants.data,
      }))
      .catch(() => toast.showToast('Chargement des référentiels impossible.', 'error'))
  }, [peutAgir, toast])

  const creer = async (e) => {
    e.preventDefault()
    setEnCours(true)
    try {
      await api.post('/equivalences/demandes/', {
        ...form,
        annee_academique_id: Number(form.annee_academique_id) || undefined,
        ref_formation_id: Number(form.ref_formation_id) || undefined,
        niveau_id: Number(form.niveau_id) || undefined,
        etudiant_id: Number(form.etudiant_id) || undefined,
      })
      toast.showToast('Demande créée en brouillon.')
      charger()
    } catch (err) {
      toast.showToast(JSON.stringify(err.response?.data) || 'Création impossible.', 'error')
    } finally {
      setEnCours(false)
    }
  }

  const transition = async (demande, statut) => {
    setEnCours(true)
    try {
      await api.post(`/equivalences/demandes/${demande.id}/transition/`, { statut })
      toast.showToast(`Demande ${statut.toLowerCase()}.`)
      charger()
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Transition impossible.', 'error')
    } finally {
      setEnCours(false)
    }
  }

  const decider = async (demande) => {
    setEnCours(true)
    try {
      await api.post(`/equivalences/demandes/${demande.id}/decision/`, {
        ...formDecision,
        credits_reconnus: formDecision.credits_reconnus || undefined,
        note_transferee: formDecision.note_transferee || undefined,
      })
      toast.showToast('Décision enregistrée.')
      setSelection(null)
      charger()
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Décision impossible.', 'error')
    } finally {
      setEnCours(false)
    }
  }

  const appliquer = async (demande) => {
    if (!window.confirm('Appliquer cette dispense/équivalence (effet académique) ?')) return
    setEnCours(true)
    try {
      await api.post(`/equivalences/demandes/${demande.id}/appliquer/`, {})
      toast.showToast('Dispense/équivalence appliquée.')
      charger()
    } catch (err) {
      toast.showToast(err.response?.data?.error || 'Application impossible.', 'error')
    } finally {
      setEnCours(false)
    }

  return (
    <div className="container-fluid py-4">
      <h1 className="h4 mb-3"><i className="bi bi-award me-2"></i>Équivalences et dispenses</h1>

      {peutAgir && (
        <div className="card mb-4">
          <div className="card-body">
            <h2 className="h6 card-title"><i className="bi bi-plus-circle me-1"></i>Nouvelle demande</h2>
            <form className="row g-2" onSubmit={creer}>
              <div className="col-md-2">
                <select className="form-select" value={form.type_demande}
                        onChange={(e) => setForm({ ...form, type_demande: e.target.value })}>
                  <option value="DISPENSE">Dispense</option>
                  <option value="EQUIVALENCE">Équivalence</option>
                </select>
              </div>
              <div className="col-md-3">
                <select className="form-select" required value={form.etudiant_id}
                        onChange={(e) => setForm({ ...form, etudiant_id: e.target.value })}>
                  <option value="">Étudiant…</option>
                  {options.etudiants.map((e) => (
                    <option key={e.id} value={e.id}>{e.matricule} — {e.nom_complet}</option>
                  ))}
                </select>
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
                <select className="form-select" required value={form.niveau_id}
                        onChange={(e) => setForm({ ...form, niveau_id: e.target.value })}>
                  <option value="">Niveau…</option>
                  {options.niveaux.map((n) => <option key={n.id} value={n.id}>{n.code}</option>)}
                </select>
              </div>
              <div className="col-md-1">
                <button className="btn btn-primary w-100" disabled={enCours}>+</button>
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
                <th>Type</th><th>Matricule</th><th>Formation</th><th>Décision</th>
                <th>Statut</th><th>Crédits</th>
                {peutAgir && <th className="text-end">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {chargement ? (
                <tr><td colSpan={7} className="text-center py-4"><div className="spinner-border spinner-border-sm" /></td></tr>
              ) : demandes.length === 0 ? (
                <tr><td colSpan={7} className="text-center text-muted py-4">Aucune demande.</td></tr>
              ) : demandes.map((d) => (
                <tr key={d.id}>
                  <td>{d.type_demande}</td>
                  <td>{d.matricule}</td>
                  <td>{d.ref_formation}</td>
                  <td>{d.decision}</td>
                  <td><span className={`badge text-bg-${BADGE_STATUT[d.statut] || 'secondary'}`}>{d.statut}</span></td>
                  <td>{d.credits_reconnus ?? '—'}</td>
                  {peutAgir && (
                    <td className="text-end">
                      <div className="btn-group btn-group-sm">
                        {d.statut === 'BROUILLON' && (
                          <button className="btn btn-outline-info" disabled={enCours}
                                  onClick={() => transition(d, 'SOUMISE')}>Soumettre</button>
                        )}
                        {d.statut === 'SOUMISE' && (
                          <button className="btn btn-outline-info" disabled={enCours}
                                  onClick={() => transition(d, 'EN_INSTRUCTION')}>Instruire</button>
                        )}
                        {d.statut === 'EN_INSTRUCTION' && (
                          <button className="btn btn-outline-primary" disabled={enCours}
                                  onClick={() => transition(d, 'AVIS_PEDAGOGIQUE')}>Avis pédagogique</button>
                        )}
                        {(d.statut === 'AVIS_PEDAGOGIQUE' || d.statut === 'DECISION') && (
                          <button className="btn btn-outline-primary"
                                  onClick={() => setSelection(d)}>Décider</button>
                        )}
                        {d.statut === 'VALIDEE' && (
                          <button className="btn btn-outline-success" disabled={enCours}
                                  onClick={() => appliquer(d)}>Appliquer</button>
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


      {selection && (
        <div className="card mt-4 border-primary">
          <div className="card-body">
            <h2 className="h6 card-title">Décision — demande #{selection.id}</h2>
            <form className="row g-2" onSubmit={(e) => { e.preventDefault(); decider(selection) }}>
              <div className="col-md-2">
                <select className="form-select" value={formDecision.decision}
                        onChange={(e) => setFormDecision({ ...formDecision, decision: e.target.value })}>
                  <option value="FAVORABLE">Favorable</option>
                  <option value="DEFAVORABLE">Défavorable</option>
                </select>
              </div>
              <div className="col-md-2">
                <input type="number" min="0" className="form-control" placeholder="Crédits reconnus"
                       value={formDecision.credits_reconnus}
                       onChange={(e) => setFormDecision({ ...formDecision, credits_reconnus: e.target.value })} />
              </div>
              <div className="col-md-2">
                <input type="number" step="0.25" min="0" max="20" className="form-control"
                       placeholder="Note transférée" value={formDecision.note_transferee}
                       onChange={(e) => setFormDecision({ ...formDecision, note_transferee: e.target.value })} />
              </div>
              <div className="col-md-4">
                <input className="form-control" placeholder="Autorité de validation"
                       value={formDecision.autorite_validation}
                       onChange={(e) => setFormDecision({ ...formDecision, autorite_validation: e.target.value })} />
              </div>
              <div className="col-md-2">
                <button className="btn btn-primary w-100" disabled={enCours}>Enregistrer</button>
              </div>
            </form>
            <button className="btn btn-link btn-sm mt-1" onClick={() => setSelection(null)}>Annuler</button>
          </div>
        </div>
      )}
    </div>
  )
}
  }
