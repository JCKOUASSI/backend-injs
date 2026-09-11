import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

export default function EdtNew() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    titre: '',
    annee_academique_id: '',
    population_type: 'FORMATION',
    population_id: '',
    population_denominateur: '',
    statut: 'BROUILLON',
    rentree: '',
    semaine_debut: '1',
    semaine_fin: '20',
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.annee_academique_id || !form.population_id) {
      showToast('Veuillez remplir l année académique et la population', 'error')
      return
    }
    setLoading(true)
    try {
      await api.post('/edts/emplois/', form)
      showToast('Emploi du temps créé')
      navigate('/edt')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Erreur création EDT', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container-fluid">
      <div className="row justify-content-center">
        <div className="col-lg-8">
          <div className="card">
            <div className="card-header d-flex justify-content-between">
              <h5><i className="bi bi-calendar-plus"></i> Nouvel emploi du temps</h5>
              <Link to="/edt" className="btn btn-outline-secondary btn-sm">
                <i className="bi bi-arrow-left"></i> Retour
              </Link>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="card-body">
                <div className="row g-3">
                  <div className="col-md-6">
                    <label className="form-label">Titre</label>
                    <input type="text" className="form-control" name="titre" value={form.titre} onChange={handleChange} placeholder="Ex : EDT L1 Informatique" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Année académique</label>
                    <select className="form-select" name="annee_academique_id" value={form.annee_academique_id} onChange={handleChange} required>
                      <option value="">Sélectionnez...</option>
                      <option value="1">2025-2026</option>
                    </select>
                  </div>
                  <div className="col-md-4">
                    <label className="form-label">Type de population</label>
                    <select className="form-select" name="population_type" value={form.population_type} onChange={handleChange}>
                      <option value="FORMATION">Formation</option>
                      <option value="GROUPE">Groupe</option>
                      <option value="ENSEIGNANT">Enseignant</option>
                      <option value="SALLE">Salle</option>
                    </select>
                  </div>
                  <div className="col-md-4">
                    <label className="form-label">ID population</label>
                    <input type="number" className="form-control" name="population_id" value={form.population_id} onChange={handleChange} placeholder="ID" min="1" />
                  </div>
                  <div className="col-md-4">
                    <label className="form-label">Dénominateur</label>
                    <input type="text" className="form-control" name="population_denominateur" value={form.population_denominateur} onChange={handleChange} placeholder="Ex : L1 MIF" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Date de rentrée</label>
                    <input type="date" className="form-control" name="rentree" value={form.rentree} onChange={handleChange} />
                  </div>
                  <div className="col-md-3">
                    <label className="form-label">Semaine début</label>
                    <input type="number" className="form-control" name="semaine_debut" value={form.semaine_debut} onChange={handleChange} min="1" />
                  </div>
                  <div className="col-md-3">
                    <label className="form-label">Semaine fin</label>
                    <input type="number" className="form-control" name="semaine_fin" value={form.semaine_fin} onChange={handleChange} min="1" />
                  </div>
                </div>
              </div>
              <div className="card-footer d-flex justify-content-between">
                <button type="button" className="btn btn-outline-secondary" onClick={() => navigate(-1)}>
                  Annuler
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? <><span className="spinner-border spinner-border-sm me-2"></span>Création...</> : <><i className="bi bi-check2-circle"></i> Créer l EDT</>}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
