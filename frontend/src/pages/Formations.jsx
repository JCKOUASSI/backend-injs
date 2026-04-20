import { Navigate } from 'react-router-dom'

export default function Formations() {
  return <Navigate to="/modules" replace />
}

function _unused() {
  const { user } = useAuth()
  const [formations, setFormations] = useState([])
  const [refs, setRefs] = useState(emptyRefs)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [filters, setFilters] = useState({ statut: '', search: '', secretariat_type: '', module: '' })

  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({ ...emptyForm })
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState(null)
  const { showToast } = useToast()

  const debouncedSearch = useDebounce(filters.search)
  useEffect(() => { loadFormations() }, [page, filters.statut, filters.secretariat_type, filters.module, debouncedSearch])
  useEffect(() => {
    api.get('/formations/referentiels/').then(r => setRefs(r.data)).catch(() => {})
  }, [])

  const loadFormations = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page })
      if (filters.statut) params.set('statut', filters.statut)
      if (debouncedSearch) params.set('search', debouncedSearch)
      if (filters.secretariat_type) params.set('secretariat_type', filters.secretariat_type)
      if (filters.module) params.set('module', filters.module)
      const response = await api.get(`/formations/list/?${params}`)
      const data = Array.isArray(response.data) ? response.data : (response.data.results || [])
      setFormations(data)
      setTotalPages(response.data.total_pages || 1)
    } catch (err) {
      setError('Erreur lors du chargement des formations')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const openCreate = () => {
    setEditingId(null)
    setForm({ ...emptyForm })
    setFormError('')
    setShowModal(true)
  }

  const openEdit = (f) => {
    setEditingId(f.id)
    setForm({
      formation: (f.formation || '').trim(),
      module: (f.module || '').trim(),
    })
    setFormError('')
    setShowModal(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError('')
    setSaving(true)
    try {
      const payload = { formation: form.formation, module_input: form.module }

      if (editingId) {
        await api.patch(`/formations/${editingId}/`, payload)
      } else {
        await api.post('/formations/', payload)
      }
      setShowModal(false)
      loadFormations()
      showToast(editingId ? 'Formation modifiée' : 'Formation créée')
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const msgs = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        setFormError(msgs.join('\n'))
      } else {
        setFormError('Erreur lors de la sauvegarde')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = (id) => {
    setConfirmDialog({
      message: 'Supprimer cette formation ?',
      detail: 'Cette action est définitive.',
      onConfirm: async () => {
        try { await api.delete(`/formations/${id}/`); loadFormations(); showToast('Formation supprimée') }
        catch { showToast('Erreur lors de la suppression', 'error') }
      }
    })
  }

  const getStatutBadge = (s) => {
    const map = { 'PLANIFIEE': 'badge-planifiee', 'EN_COURS': 'badge-en-cours', 'TERMINEE': 'badge-terminee', 'SUSPENDUE': 'badge-suspendue' }
    return map[s] || 'badge-info'
  }

  const getStatutLabel = (s) => {
    const map = { 'PLANIFIEE': 'Planifiée', 'EN_COURS': 'En cours', 'TERMINEE': 'Terminée', 'SUSPENDUE': 'Suspendue' }
    return map[s] || s
  }

  const canManage = ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT'].includes(user?.role)

  return (
    <div>
      {/* Search + Filter bar */}
      <div className="card">
        <div className="card-body">
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: '1 1 220px' }}>
              <select
                className="form-control"
                value={filters.module}
                onChange={(e) => { setFilters({ ...filters, module: e.target.value }); setPage(1) }}
              >
                <option value="">Tous les modules</option>
                {(refs.modules_actifs || []).map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div>
              <select
                className="form-control"
                value={filters.statut}
                onChange={(e) => { setFilters({ ...filters, statut: e.target.value }); setPage(1) }}
              >
                <option value="">Tous les statuts</option>
                <option value="PLANIFIEE">Planifiée</option>
                <option value="EN_COURS">En cours</option>
                <option value="TERMINEE">Terminée</option>
                <option value="SUSPENDUE">Suspendue</option>
              </select>
            </div>
            {!['SECRETARIAT', 'CHEF_SECRETARIAT', 'ENCADRANT'].includes(user?.role) && (
            <div>
              <select
                className="form-control"
                value={filters.secretariat_type}
                onChange={(e) => { setFilters({ ...filters, secretariat_type: e.target.value }); setPage(1) }}
              >
                <option value="">Tous les secrétariats</option>
                <option value="A">Secrétariat A</option>
                <option value="B">Secrétariat B</option>
                <option value="C">Secrétariat C</option>
              </select>
            </div>
            )}
            {canManage && (
              <button onClick={openCreate} className="btn btn-dfrc">
                <i className="bi bi-plus-lg me-1"></i>Nouvelle formation
              </button>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Table */}
      <div className="card">
        <div className="card-header-bar">
          <span><i className="bi bi-mortarboard me-2"></i>Liste des formations</span>
          <span className="badge-bg-secondary">{formations.reduce((acc, f) => acc + Math.max(f.modules_list?.length || 0, 1), 0)} résultat(s)</span>
        </div>
        <div className="card-body-flush">
          {loading ? (
            <div className="loading"><div className="spinner"></div></div>
          ) : (
            <>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Module</th>
                      <th>Grade</th>
                      <th>Secrétariat</th>
                      <th>Groupe</th>
                      <th>Dates</th>
                      <th>Auditeurs</th>
                      <th>Statut</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {formations.length > 0 ? formations.map((m) => (
                        <tr key={m.module_id || m.id}>
                          <td><strong style={{color:'#805ad5'}}>{m.module}</strong></td>
                          <td><span style={{fontSize:'0.82rem',background:'#f0fff4',color:'#276749',padding:'2px 7px',borderRadius:4}}>{m.grade||'—'}</span></td>
                          <td>
                            {m.secretariat_nom
                              ? <span className="text-muted" style={{ fontSize: '0.82rem' }}>{m.secretariat_nom}</span>
                              : <span className="text-muted">-</span>}
                          </td>
                          <td>{m.groupe || '-'}</td>
                          <td>
                            <small>{formatDate(m.date_debut)}</small>
                            <br/><small>{formatDate(m.date_fin)}</small>
                          </td>
                          <td>
                            {m.nb_participants || 0} <small className="text-muted">attendus</small>
                          </td>
                          <td>
                            <span className={`badge ${getStatutBadge(m.statut)}`}>{getStatutLabel(m.statut)}</span>
                          </td>
                          <td>
                            <div className="btn-group">
                              <Link to={`/formations/${m.id}/modules/${m.module_id}`} className="btn btn-outline-primary btn-sm" title="Détail">
                                <i className="bi bi-eye"></i>
                              </Link>
                              {canManage && (
                                <Link to={`/formations/${m.id}/modules/${m.module_id}`} className="btn btn-outline-secondary btn-sm" title="Modifier">
                                  <i className="bi bi-pencil"></i>
                                </Link>
                              )}
                              {canManage && (
                                <button onClick={() => handleDelete(m.id)} className="btn btn-outline-danger btn-sm" title="Supprimer">
                                  <i className="bi bi-trash"></i>
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                    )) : (
                      <tr>
                        <td colSpan="8" className="text-center py-4 text-muted">
                          Aucune formation trouvée
                        </td>
                      </tr>
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

      {/* Create / Edit Formation Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" style={{ maxWidth: '640px' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h5><i className="bi bi-mortarboard me-2"></i>{editingId ? 'Modifier la formation' : 'Nouvelle formation'}</h5>
              <button className="btn-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                {formError && <div className="alert alert-danger" style={{ whiteSpace: 'pre-line' }}>{formError}</div>}
                <div className="form-group">
                  <label className="form-label">Formation (cycle) *</label>
                  {refs.formations.length > 0 ? (
                    <select className="form-control" required value={form.formation}
                      onChange={e => setForm({ ...form, formation: e.target.value })}>
                      <option value="">-- Choisir --</option>
                      {refs.formations.map(f => <option key={f.id} value={f.intitule}>{f.intitule}</option>)}
                    </select>
                  ) : (
                    <input type="text" className="form-control" required value={form.formation}
                      onChange={e => setForm({ ...form, formation: e.target.value })} />
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label">Module (intitulé) *</label>
                  <input type="text" className="form-control" required value={form.module}
                    placeholder="Ex : Droit Administratif"
                    onChange={e => setForm({ ...form, module: e.target.value })} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-dfrc" disabled={saving}>
                  {saving ? 'Enregistrement...' : (editingId ? 'Enregistrer' : 'Créer')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
