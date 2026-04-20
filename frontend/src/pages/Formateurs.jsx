import { useState, useEffect } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'
import { useDebounce } from '../hooks/useDebounce'

const emptyForm = { numerobadge: '', nom: '', prenom: '', email: '', telephone: '', specialite: '', organisation: '', secretariats: [] }

export default function Formateurs() {
  const { user } = useAuth()
  const [formateurs, setFormateurs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({ ...emptyForm })
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState(null)
  const { showToast } = useToast()

  const [secretariats, setSecretariats] = useState([])

  const debouncedSearch = useDebounce(search)
  useEffect(() => { loadFormateurs() }, [page, debouncedSearch])
  useEffect(() => {
    api.get('/formations/secretariats/')
      .then(res => setSecretariats(Array.isArray(res.data) ? res.data : (res.data.results || [])))
      .catch(() => {})
  }, [])

  const loadFormateurs = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page })
      if (debouncedSearch) params.set('search', debouncedSearch)
      const response = await api.get(`/formations/formateurs/list/?${params}`)
      const data = Array.isArray(response.data) ? response.data : (response.data.results || [])
      setFormateurs(data)
      setTotalPages(response.data.total_pages || 1)
    } catch (err) {
      setError('Erreur lors du chargement des formateurs')
      console.error(err)
    } finally { setLoading(false) }
  }

  const openCreate = () => { setEditingId(null); setForm({ ...emptyForm }); setFormError(''); setShowModal(true) }
  const openEdit = (f) => {
    setEditingId(f.id)
    setForm({
      numerobadge: f.numerobadge || '',
      nom: f.nom || '',
      prenom: f.prenom || '',
      email: f.email || '',
      telephone: f.telephone || '',
      specialite: f.specialite || '',
      organisation: f.organisation || '',
      secretariats: f.secretariats || [],
    })
    setFormError('')
    setShowModal(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError('')
    setSaving(true)
    try {
      if (editingId) {
        await api.patch(`/formations/formateurs/${editingId}/`, form)
      } else {
        await api.post('/formations/formateurs/', form)
      }
      setShowModal(false)
      loadFormateurs()
      showToast(editingId ? 'Formateur modifié' : 'Formateur créé')
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const msgs = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        setFormError(msgs.join('\n'))
      } else {
        setFormError('Erreur lors de la sauvegarde')
      }
    } finally { setSaving(false) }
  }

  const handleDelete = (id) => {
    setConfirmDialog({
      message: 'Supprimer ce formateur ?',
      detail: 'Cette action est définitive.',
      onConfirm: async () => {
        try { await api.delete(`/formations/formateurs/${id}/`); loadFormateurs(); showToast('Formateur supprimé') }
        catch { showToast('Erreur lors de la suppression', 'error') }
      }
    })
  }

  const canEdit = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT'].includes(user?.role)
  const canDelete = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT'].includes(user?.role)

  return (
    <div>
      {/* Search bar */}
      <div className="card">
        <div className="card-body">
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ flex: '1 1 250px' }}>
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-search"></i></span>
                <input type="text" className="form-control" placeholder="Rechercher par nom, prénom ou spécialité..."
                  value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
              </div>
            </div>
            {canDelete && (
              <button onClick={openCreate} className="btn btn-dfrc">
                <i className="bi bi-plus-lg me-1"></i>Nouveau formateur
              </button>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Table */}
      <div className="card">
        <div className="card-header-bar">
          <span><i className="bi bi-person-video3 me-2"></i>Liste des formateurs</span>
          <span className="badge-bg-secondary">{formateurs.length} résultat(s)</span>
        </div>
        <div className="card-body-flush">
          {loading ? <div className="loading"><div className="spinner"></div></div> : (
            <>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Numéro</th>
                      <th>Nom</th>
                      <th>Prénom</th>
                      <th>Spécialité</th>
                      <th>Adresse e-mail</th>
                      <th>Téléphone</th>
                      <th>Modules</th>
                      {canEdit && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {formateurs.length > 0 ? formateurs.map((f) => (
                      <tr key={f.id}>
                        <td><span className="badge-bg-info">{f.numerobadge || '-'}</span></td>
                        <td><strong>{f.nom}</strong></td>
                        <td>{f.prenom}</td>
                        <td>{f.specialite || '-'}</td>
                        <td>{f.email || '-'}</td>
                        <td>{f.telephone || '-'}</td>
                        <td><span className="badge-bg-success">{f.nb_formations || 0}</span></td>
                        {canEdit && (
                          <td>
                            <div className="btn-group">
                              <button onClick={() => openEdit(f)} className="btn btn-outline-primary btn-sm" title="Modifier">
                                <i className="bi bi-pencil"></i>
                              </button>
                              {canDelete && (
                                <button onClick={() => handleDelete(f.id)} className="btn btn-outline-danger btn-sm" title="Supprimer">
                                  <i className="bi bi-trash"></i>
                                </button>
                              )}
                            </div>
                          </td>
                        )}
                      </tr>
                    )) : (
                      <tr><td colSpan={canEdit ? 10 : 9} className="text-center py-4 text-muted">Aucun formateur trouvé</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="pagination">
                  <button className="pagination-btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                    <i className="bi bi-chevron-left"></i> Précédent
                  </button>
                  <span className="small">Page {page} / {totalPages}</span>
                  <button className="pagination-btn" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                    Suivant <i className="bi bi-chevron-right"></i>
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {confirmDialog && (
        <ConfirmModal
          message={confirmDialog.message}
          detail={confirmDialog.detail}
          onConfirm={() => { setConfirmDialog(null); confirmDialog.onConfirm() }}
          onCancel={() => setConfirmDialog(null)}
        />
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h5>{editingId ? 'Modifier le formateur' : 'Nouveau formateur'}</h5>
              <button className="btn-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {formError && <div className="alert alert-danger">{formError}</div>}
                <div className="form-group">
                  <label className="form-label">N° Badge <small className="text-muted">(auto-généré si vide)</small></label>
                  <input type="text" className="form-control" placeholder="Ex : F0042" value={form.numerobadge} onChange={e => setForm({...form, numerobadge: e.target.value})} />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Nom *</label>
                    <input type="text" className="form-control" required value={form.nom} onChange={e => setForm({...form, nom: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Prénom *</label>
                    <input type="text" className="form-control" required value={form.prenom} onChange={e => setForm({...form, prenom: e.target.value})} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Spécialité</label>
                  <input type="text" className="form-control" value={form.specialite} onChange={e => setForm({...form, specialite: e.target.value})} />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Adresse e-mail</label>
                    <input type="email" className="form-control" value={form.email} onChange={e => setForm({...form, email: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Téléphone</label>
                    <input type="text" className="form-control" value={form.telephone} onChange={e => setForm({...form, telephone: e.target.value})} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Organisation</label>
                  <input type="text" className="form-control" value={form.organisation} onChange={e => setForm({...form, organisation: e.target.value})} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-dfrc" disabled={saving}>{saving ? 'Enregistrement...' : (editingId ? 'Enregistrer' : 'Créer')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
