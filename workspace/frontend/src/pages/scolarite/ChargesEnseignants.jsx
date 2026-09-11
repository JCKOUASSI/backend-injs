import React, { useCallback, useEffect, useState } from 'react'
import api from '../../services/api'
import { canActScolarite } from '../../utils/roles'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'

const COULEURS = {
  MODULE_SANS_ENSEIGNANT: 'danger',
  VOLUME_NON_COUVERT: 'warning',
  DOUBLE_AFFECTATION: 'warning',
  CONFLIT_DISPONIBILITE: 'danger',
  MAQUETTE_INCOMPATIBLE: 'danger',
  SURCHARGE: 'danger',
}

export default function ChargesEnseignants() {
  const { user } = useAuth()
  const toast = useToast()
  const peutAgir = canActScolarite(user)

  const [annee, setAnnee] = useState(null)
  const [annees, setAnnees] = useState([])
  const [enseignants, setEnseignants] = useState([])
  const [enseignantChoisi, setEnseignantChoisi] = useState('')
  const [charge, setCharge] = useState(null)
  const [occupation, setOccupation] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [affectations, setAffectations] = useState([])
  const [chargement, setChargement] = useState(true)
  const [enCours, setEnCours] = useState(false)
  const [form, setForm] = useState({
    ref_formation_id: '', niveau_id: '', semestre_id: '', ecue_id: '',
    groupe_id: '', enseignant_id: '', type_enseignement: 'CM', volume_horaire: '',
  })
  const [options, setOptions] = useState({ formations: [], niveaux: [], semestres: [], ecues: [], groupes: [] })

  const chargerAnnee = useCallback(async () => {
    try {
      const res = await api.get('/scolarite/annee-courante/')
      setAnnee(res.data)
      return res.data
    } catch {
      toast.showToast('Aucune année académique courante.', 'error')
      return null
    }
  }, [toast])

  const chargerTout = useCallback(async (anneeCourante) => {
    setChargement(true)
    try {
      const [occupationRes, anomaliesRes] = await Promise.all([
        api.get('/enseignants/occupation/', { params: { annee_id: anneeCourante.id } }),
        api.get('/enseignants/anomalies/', { params: { annee_id: anneeCourante.id } }),
      ])
      setOccupation(occupationRes.data.occupation || [])
      setAnomalies(anomaliesRes.data.anomalies || [])
    } catch (err) {
      toast.showToast('Chargement des charges impossible.', 'error')
    } finally {
      setChargement(false)
    }
  }, [toast])

  useEffect(() => {
    if (!peutAgir) return
    Promise.all([
      api.get('/scolarite/ref/annees/', { params: { actif: 'true' } }),
      api.get('/scolarite/ref/formations/'),
      api.get('/scolarite/ref/niveaux/', { params: { actif: 'true' } }),
      api.get('/scolarite/ref/semestres/'),
      api.get('/formateurs/list/'),
    ])
      .then(([annees, formations, niveaux, semestres, formateurs]) => setOptions({
        annees: annees.data, formations: formations.data, niveaux: niveaux.data,
        semestres: semestres.data, formateurs: formateurs.data,
      }))
      .catch(() => toast.showToast('Chargement des référentiels impossible.', 'error'))
  }, [peutAgir, toast])

  useEffect(() => {
    if (!annee) return
    chargerTout(annee)
  }, [annee, chargerTout])

  const choisirEnseignant = async (enseignantId) => {
    setEnseignantChoisi(enseignantId)
    if (!enseignantId || !annee) { setCharge(null); return }
    try {
      const res = await api.get(`/enseignants/charges/${enseignantId}/`, { params: { annee_id: annee.id } })
      setCharge(res.data)
      const aff = await api.get('/enseignants/affectations/', {
        params: { enseignant_id: enseignantId, annee_academique_id: annee.id },
      })
      setAffectations(aff.data)
    } catch {
      toast.showToast('Chargement de la charge impossible.', 'error')
    }
  }

  const creerAffectation = async (e) => {
    e.preventDefault()
    setEnCours(true)
    try {
      await api.post('/enseignants/affectations/', {
        ...form,
        annee_academique_id: annee?.id,
        ref_formation_id: Number(form.ref_formation_id) || undefined,
        niveau_id: Number(form.niveau_id) || undefined,
        semestre_id: Number(form.semestre_id) || undefined,
        enseignant_id: Number(form.enseignant_id) || undefined,
        volume_horaire: Number(form.volume_horaire) || 0,
      })
      toast.showToast('Affectation créée.')
      setForm({ ...form, ecue_id: '', enseignant_id: '', volume_horaire: '' })
      if (annee) chargerTout(annee)
      if (enseignantChoisi) choisirEnseignant(enseignantChoisi)
    } catch (err) {
      toast.showToast(JSON.stringify(err.response?.data) || 'Création impossible.', 'error')
    } finally {
      setEnCours(false)
    }
  }


  if (chargement) {
    return <div className="container-fluid py-4"><div className="spinner-border" /></div>
  }

  return (
    <div className="container-fluid py-4">
      <h1 className="h4 mb-3"><i className="bi bi-people me-2"></i>Charges pédagogiques des enseignants</h1>

      {anomalies.length > 0 && (
        <div className="alert alert-warning">
          <strong><i className="bi bi-exclamation-triangle me-1"></i>
            {anomalies.length} anomalie(s) détectée(s) :</strong>
          <ul className="mb-0 mt-1">
            {anomalies.slice(0, 8).map((a, i) => <li key={i}>{a.detail}</li>)}
          </ul>
        </div>
      )}

      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h6 card-title">Occupation par enseignant — {annee?.libelle}</h2>
          <div className="table-responsive">
            <table className="table table-sm table-hover mb-0">
              <thead className="table-light">
                <tr>
                  <th>Enseignant</th><th>Prévue (h)</th><th>Affectée (h)</th>
                  <th>Planifiée (h)</th><th>Réalisée (h)</th><th>Charge</th>
                </tr>
              </thead>
              <tbody>
                {occupation.length === 0 ? (
                  <tr><td colSpan={6} className="text-muted">Aucune affectation.</td></tr>
                ) : occupation.map((o) => (
                  <tr key={o.enseignant_id} style={{ cursor: 'pointer' }}
                      className={o.enseignant_id === Number(enseignantChoisi) ? 'table-active' : ''}
                      onClick={() => choisirEnseignant(o.enseignant_id)}>
                    <td>{o.enseignant}</td>
                    <td>{o.prevue}</td>
                    <td>{o.affectee}</td>
                    <td>{o.planifiee}</td>
                    <td>{o.realisee}</td>
                    <td>{o.surcharge
                      ? <span className="badge text-bg-danger">Surcharge</span>
                      : <span className="badge text-bg-success">OK</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {charge && (
        <div className="card mb-3 border-primary">
          <div className="card-body">
            <h2 className="h6 card-title">Détail — {charge.enseignant}</h2>
            <ul className="list-unstyled mb-2">
              <li>Prévue : {charge.prevue} h · Affectée : {charge.affectee} h ·
                Planifiée : {charge.planifiee} h · Réalisée : {charge.realisee} h</li>
            </ul>
            <table className="table table-sm mb-0">
              <thead className="table-light">
                <tr><th>ECUE</th><th>Type</th><th>Volume (h)</th><th>Statut</th></tr>
              </thead>
              <tbody>
                {affectations.map((a) => (
                  <tr key={a.id}>
                    <td>{a.ecue || '—'}</td>
                    <td>{a.type_enseignement}</td>
                    <td>{a.volume_horaire}</td>
                    <td>{a.statut}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {peutAgir && (
        <div className="card mb-3">
          <div className="card-body">
            <h2 className="h6 card-title"><i className="bi bi-plus-circle me-1"></i>Nouvelle affectation pédagogique</h2>
            <form className="row g-2" onSubmit={creerAffectation}>
              <div className="col-md-3">
                <select className="form-select" required value={form.enseignant_id}
                        onChange={(e) => setForm({ ...form, enseignant_id: e.target.value })}>
                  <option value="">Enseignant…</option>
                  {options.formateurs.map((f) => (
                    <option key={f.id} value={f.id}>{f.nom} {f.prenom}</option>
                  ))}
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
              <div className="col-md-2">
                <select className="form-select" required value={form.semestre_id}
                        onChange={(e) => setForm({ ...form, semestre_id: e.target.value })}>
                  <option value="">Semestre…</option>
                  {options.semestres.filter((s) => s.niveau_id === Number(form.niveau_id)).map((s) => (
                    <option key={s.id} value={s.id}>{s.libelle}</option>
                  ))}
                </select>
              </div>
              <div className="col-md-2">
                <input type="number" min="0" step="0.5" className="form-control" placeholder="Volume (h)"
                       required value={form.volume_horaire}
                       onChange={(e) => setForm({ ...form, volume_horaire: e.target.value })} />
              </div>
              <div className="col-12">
                <button className="btn btn-primary btn-sm" disabled={enCours || !annee}>
                  Créer l'affectation {annee ? `(${annee.libelle})` : ''}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
