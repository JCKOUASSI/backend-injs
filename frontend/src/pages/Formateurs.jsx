import { useState, useEffect } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'
import { useDebounce } from '../hooks/useDebounce'

const emptyForm = { numerobadge: '', nom: '', prenom: '', email: '', telephone: '', specialite: '', organisation: '', secretariats: [] }

export default function Formateurs() {
  const { user } = useAuth()
  const canViewFinanceData = ['FINANCE', 'DIRECTION'].includes(user?.role)
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
  const [financeDetail, setFinanceDetail] = useState(null)
  const [financeDetailLoading, setFinanceDetailLoading] = useState(false)

  const debouncedSearch = useDebounce(search)
  useEffect(() => { loadFormateurs() }, [page, debouncedSearch])
  useEffect(() => {
    if (canViewFinanceData) return
    api.get('/formations/secretariats/')
      .then(res => setSecretariats(Array.isArray(res.data) ? res.data : (res.data.results || [])))
      .catch(() => {})
  }, [canViewFinanceData])

  const loadFormateurs = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page })
      if (debouncedSearch) params.set('search', debouncedSearch)
      const endpoint = canViewFinanceData
        ? '/formations/formateurs/finance-report/'
        : '/formations/formateurs/list/'
      if (canViewFinanceData) params.set('include_sessions', '0')
      const response = await api.get(`${endpoint}?${params}`)
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

  const canEdit = !canViewFinanceData && ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT'].includes(user?.role)
  const canDelete = !canViewFinanceData && ['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT'].includes(user?.role)
  const formatDuration = (minutes) => {
    const value = Number(minutes || 0)
    const hours = Math.floor(value / 60)
    const remaining = Math.round(value % 60)
    return `${hours}h ${remaining}min`
  }

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const exportFinanceSummary = async (f, format) => {
    const ext = format === 'pdf' ? 'pdf' : 'xlsx'
    const path = format === 'pdf' ? `/exports/formateur/${f.id}/pdf/` : `/exports/formateur/${f.id}/excel/`
    try {
      const blob = await api.getBlob(path)
      const safeName = `${f.nom || 'formateur'}_${f.prenom || ''}`.trim().replace(/\s+/g, '_')
      downloadBlob(blob, `fiche_resume_${safeName || f.id}.${ext}`)
      showToast(`Fiche résumé exportée (${ext.toUpperCase()})`)
    } catch (err) {
      showToast(err.response?.data?.detail || 'Erreur export fiche résumé', 'error')
    }
  }

  const openFinanceDetail = async (f) => {
    setFinanceDetail({ id: f.id, nom: f.nom, prenom: f.prenom, numerobadge: f.numerobadge, sessions: [], total_duree_minutes: f.total_duree_minutes })
    setFinanceDetailLoading(true)
    try {
      const res = await api.get(`/formations/formateurs/finance-report/?formateur_id=${f.id}`)
      const rows = Array.isArray(res.data) ? res.data : (res.data.results || [])
      const row = rows[0]
      if (row) setFinanceDetail(row)
    } catch {
      showToast('Impossible de charger le détail', 'error')
      setFinanceDetail(null)
    } finally {
      setFinanceDetailLoading(false)
    }
  }

  return (
    <div>
      {/* Search bar */}
      <div className="card">
        <div className="card-body">
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ flex: '1 1 250px' }}>
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-search"></i></span>
                <input type="text" className="form-control" placeholder={canViewFinanceData ? 'Rechercher un formateur...' : 'Rechercher par nom, prénom ou spécialité...'}
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
          <span>
            <i className={`bi ${canViewFinanceData ? 'bi-calculator' : 'bi-person-video3'} me-2`}></i>
            {canViewFinanceData ? 'Suivi des temps de cours formateurs' : 'Liste des formateurs'}
          </span>
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
                      {!canViewFinanceData && <th>Adresse e-mail</th>}
                      {!canViewFinanceData && <th>Téléphone</th>}
                      {!canViewFinanceData && <th>Modules</th>}
                      {canViewFinanceData && <th>Nombre de séances</th>}
                      {canViewFinanceData && <th>Temps total</th>}
                      {(canEdit || canViewFinanceData) && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {formateurs.length > 0 ? formateurs.map((f) => (
                      <tr key={f.id}>
                        <td><span className="badge-bg-info">{f.numerobadge || '-'}</span></td>
                        <td><strong>{f.nom}</strong></td>
                        <td>{f.prenom}</td>
                        <td>{f.specialite || '-'}</td>
                        {!canViewFinanceData && <td>{f.email || '-'}</td>}
                        {!canViewFinanceData && <td>{f.telephone || '-'}</td>}
                        {!canViewFinanceData && <td><span className="badge-bg-success">{f.nb_formations || 0}</span></td>}
                        {canViewFinanceData && (
                          <td><span className="badge-bg-secondary">{f.sessions_count ?? 0}</span></td>
                        )}
                        {canViewFinanceData && (
                          <td>
                            <span className="badge-bg-success">{formatDuration(f.total_duree_minutes)}</span>
                          </td>
                        )}
                        {canViewFinanceData && (
                          <td>
                            <div className="btn-group" role="group">
                              <button type="button" onClick={() => openFinanceDetail(f)} className="btn btn-outline-primary btn-sm" title="Voir le détail par séance">
                                <i className="bi bi-eye me-1"></i>Détail
                              </button>
                              <button type="button" onClick={() => exportFinanceSummary(f, 'excel')} className="btn btn-outline-success btn-sm" title="Exporter en Excel">
                                <i className="bi bi-file-earmark-spreadsheet me-1"></i>Excel
                              </button>
                              <button type="button" onClick={() => exportFinanceSummary(f, 'pdf')} className="btn btn-outline-danger btn-sm" title="Exporter en PDF">
                                <i className="bi bi-file-earmark-pdf me-1"></i>PDF
                              </button>
                            </div>
                          </td>
                        )}
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
                      <tr><td colSpan={canViewFinanceData ? 7 : (canEdit ? 8 : 7)} className="text-center py-4 text-muted">Aucun formateur trouvé</td></tr>
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

      {financeDetail && (
        <div className="modal-overlay" onClick={() => !financeDetailLoading && setFinanceDetail(null)}>
          <div className="modal-content" style={{ width: 'min(96vw, 1100px)', maxWidth: '1100px', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h5>
                <i className="bi bi-clock-history me-2"></i>
                Détail — {financeDetail.prenom} {financeDetail.nom}
                {financeDetail.numerobadge ? <small className="text-muted ms-2">({financeDetail.numerobadge})</small> : null}
              </h5>
              <button type="button" className="btn-close" disabled={financeDetailLoading} onClick={() => setFinanceDetail(null)}>&times;</button>
            </div>
            <div className="modal-body" style={{ overflowY: 'auto', flex: 1 }}>
              {financeDetailLoading ? (
                <div className="loading py-4"><div className="spinner"></div></div>
              ) : (
                <>
                  <p className="text-muted small mb-3">Temps de cours par séance pour ce formateur.</p>
                  <div className="mb-3 p-2 rounded" style={{ background: 'var(--bs-light, #f8f9fa)', border: '1px solid #e2e8f0' }}>
                    <strong>Temps total séance :</strong>{' '}
                    <span className="badge-bg-success">{formatDuration(financeDetail.total_duree_minutes)}</span>
                    <span className="ms-2"><strong>Temps réalisé :</strong>{' '}
                      <span className="badge-bg-info" style={{ display: 'inline-block', whiteSpace: 'nowrap' }}>
                        {formatDuration(financeDetail.total_duree_realisee_minutes)}
                      </span>
                    </span>
                    <span className="text-muted ms-2">({financeDetail.sessions_count ?? (financeDetail.sessions?.length || 0)} séance(s))</span>
                  </div>
                  {Array.isArray(financeDetail.sessions) && financeDetail.sessions.length > 0 ? (
                    <div className="table-container" style={{ overflowX: 'auto' }}>
                      <table className="table table-sm mb-0">
                        <thead>
                          <tr>
                            <th style={{ whiteSpace: 'nowrap' }}>Date</th>
                            <th style={{ whiteSpace: 'nowrap' }}>Séance</th>
                            <th style={{ whiteSpace: 'nowrap' }}>Module</th>
                            <th style={{ whiteSpace: 'nowrap' }}>Durée séance</th>
                            <th style={{ whiteSpace: 'nowrap' }}>Temps réalisé</th>
                          </tr>
                        </thead>
                        <tbody>
                          {financeDetail.sessions.map((s) => (
                            <tr key={s.session_id}>
                              <td style={{ whiteSpace: 'nowrap' }}>{s.date_journee || '—'}</td>
                              <td style={{ whiteSpace: 'nowrap' }}>{s.intitule || `Session ${s.numero ?? ''}`}</td>
                              <td style={{ whiteSpace: 'nowrap' }}>{s.module_intitule || '—'}</td>
                              <td style={{ whiteSpace: 'nowrap' }}>
                                <span className="badge-bg-info" style={{ display: 'inline-block', whiteSpace: 'nowrap' }}>
                                  {formatDuration(s.duree_minutes)}
                                </span>
                              </td>
                              <td style={{ whiteSpace: 'nowrap' }}>
                                <span className="badge-bg-success" style={{ display: 'inline-block', whiteSpace: 'nowrap' }}>
                                  {formatDuration(s.duree_realisee_minutes)}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-muted text-center py-3 mb-0">Aucune séance enregistrée pour ce formateur.</p>
                  )}
                </>
              )}
            </div>
            <div className="modal-footer">
              {!financeDetailLoading && (
                <div className="btn-group me-auto" role="group">
                  <button
                    type="button"
                    className="btn btn-outline-success"
                    onClick={() => exportFinanceSummary(financeDetail, 'excel')}
                  >
                    <i className="bi bi-file-earmark-spreadsheet me-1"></i>Excel
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-danger"
                    onClick={() => exportFinanceSummary(financeDetail, 'pdf')}
                  >
                    <i className="bi bi-file-earmark-pdf me-1"></i>PDF
                  </button>
                </div>
              )}
              <button type="button" className="btn btn-secondary" disabled={financeDetailLoading} onClick={() => setFinanceDetail(null)}>Fermer</button>
            </div>
          </div>
        </div>
      )}

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
