import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

export default function Edts() {
  const [searchParams] = useSearchParams()
  const { showToast } = useToast()
  const [loading, setLoading] = useState(true)
  const [edts, setEdts] = useState([])
  const [affectations, setAffectations] = useState([])
  const [selectedEdt, setSelectedEdt] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const anneeId = searchParams.get('annee')
  const populationId = searchParams.get('pop')
  const typePop = searchParams.get('type') || 'FORMATION'

  const fetchEdts = async () => {
    setLoading(true)
    try {
      const res = await api.get('/edts/emplois/', { params: {
        annee_academique_id: anneeId || undefined,
        population_id: populationId || undefined,
        population_type: typePop || undefined,
      } })
      const data = res.data
      setEdts(Array.isArray(data) ? data : (data.results ?? []))
    } catch (err) { showToast(err.response?.data?.detail || 'Erreur chargement EDTs', 'error') } finally { setLoading(false) }
  }

  const fetchAffectations = async () => {
    if (!selectedEdt) return
    setLoadingDetail(true)
    try {
      const res = await api.get('/edts/affectations/', { params: { emploi_du_temps_id: selectedEdt.id } })
      const data = res.data
      setAffectations(Array.isArray(data) ? data : (data.results ?? []))
    } catch (err) { showToast(err.response?.data?.detail || 'Erreur chargement', 'error') } finally { setLoadingDetail(false) }
  }

  const detecterConflits = async (edtId) => {
    try {
      await api.post(`/edts/emplois/${edtId}/conflits/`)
      showToast('Conflits détectés')
      fetchAffectations()
    } catch (err) { showToast(err.response?.data?.detail || 'Erreur détection', 'error') }
  }

  const validerEdt = async (edtId) => {
    try {
      await api.post(`/edts/emplois/${edtId}/valider/`, { statut: 'VALIDE' })
      showToast('Emploi du temps validé')
      fetchEdts(); fetchAffectations()
    } catch (err) { showToast(err.response?.data?.detail || 'Erreur validation', 'error') }
  }

  const publierEdt = async (edtId) => {
    try {
      await api.post(`/edts/emplois/${edtId}/valider/`, { statut: 'PUBLIE' })
      showToast('Emploi du temps publié')
      fetchEdts(); fetchAffectations()
    } catch (err) { showToast(err.response?.data?.detail || 'Erreur publication', 'error') }
  }

  const supprimerAffectation = async (affId) => {
    try {
      await api.delete(`/edts/affectations/${affId}/`)
      showToast('Affectation supprimée')
      fetchAffectations()
    } catch (err) { showToast(err.response?.data?.detail || 'Erreur suppression', 'error') }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps -- rechargement intentionnel : la fonction de chargement n’est pas mémoïsée (l’ajouter provoquerait une boucle) ; les dépendances de données présentes pilotent déjà le (re)chargement.
  useEffect(() => { fetchEdts() }, [anneeId, populationId, typePop])
  // eslint-disable-next-line react-hooks/exhaustive-deps -- rechargement intentionnel : la fonction de chargement n’est pas mémoïsée (l’ajouter provoquerait une boucle) ; les dépendances de données présentes pilotent déjà le (re)chargement.
  useEffect(() => { if (selectedEdt) fetchAffectations() }, [selectedEdt])

  const badge = (s) => {
    const map = { BROUILLON: 'bg-secondary', EN_VALIDATION: 'bg-warning text-dark', VALIDE: 'bg-info text-dark', PUBLIE: 'bg-success' }
    return `badge ${map[s] || 'bg-secondary'}`
  }

  return (
    <div className="container-fluid">
      <div className="d-flex justify-content-between flex-wrap gap-2 mb-4">
        <h2><i className="bi bi-calendar-week"></i> Emplois du temps</h2>
        <Link to="/edt/nouveau" className="btn btn-outline-primary"><i className="bi bi-plus-circle"></i> Nouvel EDT</Link>
      </div>
      <div className="row mt-3">
        <div className="col-lg-4">
          <div className="card h-100">
            <div className="card-header d-flex justify-content-between align-items-center">
              <span>Emplois du temps</span>
              <span className="badge bg-secondary">{edts.length}</span>
            </div>
            <div className="card-body p-0">
              {loading ? (
                <div className="text-center py-4"><div className="spinner-border text-primary"></div></div>
              ) : edts.length === 0 ? (
                <div className="text-center py-4 text-muted">
                  <i className="bi bi-calendar-x fs-1 d-block mb-2"></i>
                  Aucun emploi du temps
                </div>
              ) : (
                <div className="list-group list-group-flush">
                  {edts.map((edt) => (
                    <button
                      key={edt.id}
                      className={`list-group-item list-group-item-action d-flex justify-content-between align-items-center ${selectedEdt?.id === edt.id ? 'active bg-primary text-white' : ''}`}
                      onClick={() => setSelectedEdt(edt)}
                    >
                      <div>
                        <div className="fw-semibold">{edt.titre || edt.population_label || `Pop. ${edt.population_type} #${edt.population_id}`}</div>
                        <div className="text-muted small">
                          {edt.annee_academique} — Sem. {edt.semaine_debut}-{edt.semaine_fin}
                        </div>
                      </div>
                      <span className={`badge ${badge(edt.statut)}`}>{edt.statut}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
                        {selectedEdt && (
              <div className="card-footer border-0 d-flex justify-content-between">
                <button className="btn btn-sm btn-outline-danger" onClick={() => { setSelectedEdt(null); setAffectations([]) }}>
                  <i className="bi bi-x-circle"></i> Fermer
                </button>
                <div className="d-flex gap-2">
                  <Link to={`/edt/${selectedEdt.id}/affectation/nouveau`} className="btn btn-sm btn-outline-primary">
                    <i className="bi bi-plus-circle"></i> Nouvelle affectation
                  </Link>
                  <div className="btn-group btn-group-sm">
                    <button className="btn btn-outline-primary" onClick={() => detecterConflits(selectedEdt.id)}>
                      <i className="bi bi-emoji-frown"></i> Détecter
                    </button>
                    {selectedEdt.statut === 'BROUILLON' && (
                      <button className="btn btn-outline-warning" onClick={() => validerEdt(selectedEdt.id)}>
                        <i className="bi bi-check2-all"></i> Valider
                      </button>
                    )}
                    {selectedEdt.statut === 'VALIDE' && (
                      <button className="btn btn-outline-success" onClick={() => publierEdt(selectedEdt.id)}>
                        <i className="bi bi-globe"></i> Publier
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>



        <div className="col-lg-8">
          {selectedEdt ? (
            <>
              <div className="card mb-3">
                <div className="card-header d-flex justify-content-between align-items-center">
                  <h5 className="mb-0">{selectedEdt.titre || selectedEdt.population_label}</h5>
                  <span className={`badge ${badge(selectedEdt.statut)}`}>{selectedEdt.statut}</span>
                </div>
                <div className="card-body p-0">
                  {loadingDetail ? (
                    <div className="text-center py-4"><div className="spinner-border text-primary"></div></div>
                  ) : affectations.length === 0 ? (
                    <div className="text-center py-4 text-muted">
                      <i className="bi bi-calendar-x fs-1 d-block mb-2"></i>
                      Aucune affectation
                    </div>
                  ) : (
                    <div className="table-responsive">
                      <table className="table table-striped table-hover mb-0 align-middle">
                        <thead className="table-light">
                          <tr>
                            <th>Semaine</th>
                            <th>Créneau</th>
                            <th>Nature</th>
                            <th>Contenu</th>
                            <th>Salle</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {affectations.map((aff) => (
                            <tr key={aff.id}>
                              <td>{aff.semaine_debut}-{aff.semaine_fin}</td>
                              <td>
                                {aff.creneau ? (
                                  <>{aff.creneau.jour} {aff.creneau.heure_debut}-{aff.creneau.heure_fin}</>
                                ) : (
                                  <span className="text-muted">-</span>
                                )}
                              </td>
                              <td>
                                <span className={"badge bg-" + (aff.nature === 'COURS' ? 'primary' : aff.nature === 'TD' ? 'info' : aff.nature === 'TP' ? 'success' : 'secondary')}>
                                  {aff.nature}
                                </span>
                              </td>
                              <td>
                                <div className="fw-medium">{aff.intitule || aff.formation || aff.groupe || '-'}</div>
                                {aff.enseignant_nom && <div className="text-muted small">{aff.enseignant_nom}</div>}
                              </td>
                              <td>{aff.salle_nom || <span className="text-muted">-</span>}</td>
                              <td>
                                {!aff.actif && (
                                  <button
                                    className="btn btn-sm btn-outline-danger"
                                    onClick={() => supprimerAffectation(aff.id)}
                                  >
                                    <i className="bi bi-trash"></i>
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <i className="bi bi-exclamation-triangle text-danger"></i> Conflits
                </div>
                <div className="card-body">
                  {loadingDetail ? (
                    <div className="text-center py-3"><div className="spinner-border text-danger"></div></div>
                  ) : affectations.filter(a => !a.actif).length === 0 ? (
                    <p className="text-muted mb-0">Aucun conflit détecté.</p>
                  ) : (
                    <div className="alert alert-warning mb-0">
                      {affectations.filter(a => !a.actif).length} affectation(s) inactive(s).
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="card">
              <div className="card-body text-center py-5">
                <i className="bi bi-calendar-week fs-1 text-muted d-block mb-3"></i>
                <p className="text-muted mb-3">Sélectionnez un emploi du temps dans la liste.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

