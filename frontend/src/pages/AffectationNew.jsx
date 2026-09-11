import { useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

export default function AffectationNew() {
  const navigate = useNavigate()
  const { edtId } = useParams()
  const { showToast } = useToast()
  const [submitting, setSubmitting] = useState(false)
  const [creneaux, setCreneaux] = useState([])
  const [form, setForm] = useState({
    semaine_debut: '1',
    semaine_fin: '20',
    salle_nom: '',
    formation_id: '',
    groupe_id: '',
    enseignant_id: '',
    enseignant_nom: '',
    nature: 'COURS',
    intitule: '',
    commentaire: '',
  })

  useEffect(() => {
    const fetchCreneaux = async () => {
      try {
        const res = await api.get('/edts/creneaux-types/')
        const data = res.data
        setCreneaux(Array.isArray(data) ? data : (data.results ?? []))
      } catch (err) { showToast(err.response?.data?.detail || 'Erreur chargement', 'error') }
    }
    fetchCreneaux()
    // showToast est une fonction stable (useCallback du ToastProvider).
  }, [showToast])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!edtId || !form.semaine_debut || !form.semaine_fin) {
      showToast('Veuillez remplir les champs obligatoires', 'error')
      return
    }
    setSubmitting(true)
    try {
      await api.post('/edts/affectations/', {
        ...form,
        emploi_du_temps_id: parseInt(edtId),
      })
      showToast('Affectation créée')
      navigate('/edt')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Erreur création affectation', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container-fluid">
      <div className="row justify-content-center">
        <div className="col-lg-8">
          <div className="card">
            <div className="card-header d-flex justify-content-between">
              <h5><i className="bi bi-calendar-plus"></i> Nouvelle affectation</h5>
                            <Link to="/edt" className="btn btn-outline-secondary btn-sm">
                <i className="bi bi-arrow-left"></i> Retour
              </Link>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="card-body">
                <div className="row g-3">
                  <div className="col-md-4">
                    <label className="form-label">Créneau horaire</label>
                    <select className="form-select" name="creneau_template_id" onChange={handleChange} required>
                      <option value="">Sélectionnez un créneau...</option>
                      {creneaux.map(c => (
                        <option key={c.id} value={c.id}>
                          {c.jour} {c.heure_debut}-{c.heure_fin}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-md-3">
                    <label className="form-label">Semaine début</label>
                    <input type="number" className="form-control" name="semaine_debut" value={form.semaine_debut} onChange={handleChange} min="1" required />
                  </div>
                  <div className="col-md-3">
                    <label className="form-label">Semaine fin</label>
                    <input type="number" className="form-control" name="semaine_fin" value={form.semaine_fin} onChange={handleChange} min="1" required />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Nature</label>
                    <select className="form-select" name="nature" value={form.nature} onChange={handleChange}>
                      <option value="COURS">Cours</option>
                      <option value="TD">Travaux dirigés</option>
                      <option value="TP">Travaux pratiques</option>
                      <option value="EVALUATION">Évaluation</option>
                      <option value="REMPLACEMENT">Remplacement</option>
                      <option value="AUTRE">Autre</option>
                    </select>
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Intitulé</label>
                    <input type="text" className="form-control" name="intitule" value={form.intitule} onChange={handleChange} placeholder="Ex : Algorithmique" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Salle</label>
                    <input type="text" className="form-control" name="salle_nom" value={form.salle_nom} onChange={handleChange} placeholder="Ex : A101" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Enseignant (ID)</label>
                    <input type="number" className="form-control" name="enseignant_id" value={form.enseignant_id} onChange={handleChange} placeholder="ID enseignant" min="1" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Nom enseignant</label>
                    <input type="text" className="form-control" name="enseignant_nom" value={form.enseignant_nom} onChange={handleChange} placeholder="Nom complet" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Formation (ID)</label>
                    <input type="number" className="form-control" name="formation_id" value={form.formation_id} onChange={handleChange} placeholder="ID formation" min="1" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Groupe (ID)</label>
                    <input type="number" className="form-control" name="groupe_id" value={form.groupe_id} onChange={handleChange} placeholder="ID groupe" min="1" />
                  </div>
                  <div className="col-12">
                    <label className="form-label">Commentaire</label>
                    <textarea className="form-control" name="commentaire" value={form.commentaire} onChange={handleChange} rows="2" placeholder="Observations optionnelles"></textarea>
                  </div>
                </div>
              </div>
              <div className="card-footer d-flex justify-content-between">
                <button type="button" className="btn btn-outline-secondary" onClick={() => navigate(-1)}>
                  Annuler
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? <><span className="spinner-border spinner-border-sm me-2"></span>Création...</> : <><i className="bi bi-check2-circle"></i> Créer l affectation</>}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
