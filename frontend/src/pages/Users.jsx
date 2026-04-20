import { useState, useEffect } from 'react'
import api from '../services/api'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'
import { useDebounce } from '../hooks/useDebounce'
import { useAuth } from '../context/AuthContext'

const ROLE_HIERARCHY = ['ADMIN', 'DIRECTION', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'AUDITEUR']
const ALL_ROLES = ['DIRECTION', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'AUDITEUR']

function getSubordinateRoles(role) {
  const idx = ROLE_HIERARCHY.indexOf(role)
  if (idx === -1) return []
  return ROLE_HIERARCHY.slice(idx + 1)
}

function getCreatableRoles(role) {
  const subordinates = getSubordinateRoles(role)
  if (role === 'CHEF_CPFAE_ADMIN' && !subordinates.includes('DIRECTION')) {
    return ['DIRECTION', ...subordinates]
  }
  return subordinates
}
const ROLE_LABELS = { DIRECTION: 'Direction', CHEF_CPFAE_ADMIN: 'Chef CPFAE Admin', CPFAE_ADMIN: 'CPFAE Admin', CHEF_SECRETARIAT: 'Chef Secrétariat', SECRETARIAT: 'Secrétariat', ENCADRANT: 'Encadrant', AUDITEUR: 'Auditeur' }
const emptyForm = { username: '', first_name: '', last_name: '', email: '', role: 'ENCADRANT', password: '', telephone: '', secretariat: '', new_secretariat_nom: '', new_secretariat_type: '' }
const emptyEditForm = { username: '', first_name: '', last_name: '', email: '', role: '', telephone: '', is_active: true, password: '', secretariat: '' }

export default function Users() {
  const { user: currentUser } = useAuth()
  const creatableRoles = getCreatableRoles(currentUser?.role).filter(r => ALL_ROLES.includes(r))
  const visibleRoles = creatableRoles
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ ...emptyForm })
  const [formError, setFormError] = useState('')

  const [showEditModal, setShowEditModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [editForm, setEditForm] = useState({ ...emptyEditForm })
  const [editError, setEditError] = useState('')
  const [saving, setSaving] = useState(false)
  const [secretariats, setSecretariats] = useState([])
  const [confirmDialog, setConfirmDialog] = useState(null)
  const { showToast } = useToast()

  const debouncedSearch = useDebounce(search)
  useEffect(() => { loadUsers() }, [page, debouncedSearch, roleFilter])
  useEffect(() => {
    api.get('/formations/secretariats/')
      .then(res => setSecretariats(Array.isArray(res.data) ? res.data : (res.data.results || [])))
      .catch(() => {})
  }, [])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page })
      if (debouncedSearch) params.set('search', debouncedSearch)
      if (roleFilter) params.set('role', roleFilter)
      const response = await api.get(`/auth/users/?${params}`)
      const data = Array.isArray(response.data) ? response.data : (response.data.results || [])
      setUsers(Array.isArray(data) ? data : [])
      const count = response.data.count || data.length
      const pageSize = 50
      setTotalPages(response.data.total_pages || Math.ceil(count / pageSize) || 1)
    } catch (err) {
      setError('Erreur lors du chargement des utilisateurs')
      console.error(err)
    } finally { setLoading(false) }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setFormError('')
    setSaving(true)
    try {
      const { new_secretariat_nom, new_secretariat_type, ...userPayload } = form
      if (!userPayload.secretariat) delete userPayload.secretariat
      const res = await api.post('/auth/users/', userPayload)
      const newUser = res.data
      if (form.role === 'SECRETARIAT' && !form.secretariat && new_secretariat_nom) {
        const secRes = await api.post('/formations/secretariats/', {
          nom: new_secretariat_nom,
          type: new_secretariat_type || '',
          responsable: newUser.id,
        })
        await api.patch(`/auth/users/${newUser.id}/`, { secretariat: secRes.data.id })
        setSecretariats(prev => [...prev, secRes.data])
      }
      setShowModal(false)
      setForm({ ...emptyForm })
      loadUsers()
      showToast('Utilisateur créé')
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const msgs = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        setFormError(msgs.join('\n'))
      } else {
        setFormError('Erreur lors de la création')
      }
    } finally { setSaving(false) }
  }

  const handleDelete = (id) => {
    setConfirmDialog({
      message: 'Supprimer cet utilisateur ?',
      detail: 'Cette action est définitive.',
      onConfirm: async () => {
        try { await api.delete(`/auth/users/${id}/`); loadUsers(); showToast('Utilisateur supprimé') }
        catch { showToast('Erreur lors de la suppression', 'error') }
      }
    })
  }

  const openEdit = (u) => {
    setEditingUser(u)
    setEditForm({
      username: u.username || '',
      first_name: u.first_name || '',
      last_name: u.last_name || '',
      email: u.email || '',
      role: u.role || '',
      telephone: u.telephone || '',
      is_active: u.is_active !== false,
      password: '',
      secretariat: u.secretariat || '',
    })
    setEditError('')
    setShowEditModal(true)
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    setEditError('')
    setSaving(true)
    try {
      const payload = { ...editForm }
      if (!payload.password) delete payload.password
      if (!payload.secretariat) payload.secretariat = null
      await api.patch(`/auth/users/${editingUser.id}/`, payload)
      setShowEditModal(false)
      loadUsers()
      showToast('Utilisateur modifié')
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const msgs = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        setEditError(msgs.join('\n'))
      } else {
        setEditError('Erreur lors de la modification')
      }
    } finally { setSaving(false) }
  }

  const getRoleBadge = (role) => ({ 'DIRECTION': 'badge-direction', 'CHEF_CPFAE_ADMIN': 'badge-dfrc', 'CPFAE_ADMIN': 'badge-dfrc', 'CHEF_SECRETARIAT': 'badge-secretariat', 'SECRETARIAT': 'badge-secretariat', 'ENCADRANT': 'badge-encadrant', 'AUDITEUR': 'badge-auditeur' }[role] || 'badge-info')

  const getFullName = (u) => `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username
  const getInitials = (u) => `${(u.first_name || '')[0] || ''}${(u.last_name || '')[0] || ''}`.toUpperCase() || u.username[0]?.toUpperCase()

  const filteredUsers = users

  return (
    <div>
      {/* Search + filter bar */}
      <div className="card">
        <div className="card-body">
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ flex: '1 1 250px' }}>
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-search"></i></span>
                <input type="text" className="form-control" placeholder="Rechercher par nom, username..."
                  value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
              </div>
            </div>
            <div>
              <select className="form-control" value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value); setPage(1) }}>
                <option value="">Tous les rôles</option>
                {visibleRoles.map(r => <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>)}
              </select>
            </div>
            {creatableRoles.length > 0 && (
              <button onClick={() => { setForm({ ...emptyForm, role: creatableRoles[0] }); setFormError(''); setShowModal(true) }} className="btn btn-dfrc">
                <i className="bi bi-plus-lg me-1"></i>Nouvel utilisateur
              </button>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Table */}
      <div className="card">
        <div className="card-header-bar">
          <span><i className="bi bi-person-gear me-2"></i>Liste des utilisateurs</span>
          <span className="badge-bg-secondary">{filteredUsers.length} résultat(s)</span>
        </div>
        <div className="card-body-flush">
          {loading ? <div className="loading"><div className="spinner"></div></div> : (
            <>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Nom complet</th>
                      <th>Identifiant</th>
                      <th>Adresse e-mail</th>
                      <th>Rôle / Secrétariat</th>
                      <th>Téléphone</th>
                      <th>Actif</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.length > 0 ? filteredUsers.map((u) => (
                      <tr key={u.id}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--ci-green)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600, flexShrink: 0 }}>
                              {getInitials(u)}
                            </div>
                            <strong>{getFullName(u)}</strong>
                          </div>
                        </td>
                        <td>{u.username}</td>
                        <td>{u.email || '-'}</td>
                        <td>
                          <span className={`badge ${getRoleBadge(u.role)}`}>{ROLE_LABELS[u.role] || u.role}</span>
                          {u.secretariat_nom && <><br/><small className="text-muted">{u.secretariat_nom}</small></>}
                        </td>
                        <td>{u.telephone || '-'}</td>
                        <td>
                          <span className={`badge ${u.is_active ? 'badge-success' : 'badge-danger'}`}>
                            {u.is_active ? 'Actif' : 'Inactif'}
                          </span>
                        </td>
                        <td>
                          <div className="btn-group">
                            {creatableRoles.includes(u.role) && (
                              <button onClick={() => openEdit(u)} className="btn btn-outline-primary btn-sm" title="Modifier">
                                <i className="bi bi-pencil"></i>
                              </button>
                            )}
                            {creatableRoles.includes(u.role) && (
                              <button onClick={() => handleDelete(u.id)} className="btn btn-outline-danger btn-sm" title="Supprimer">
                                <i className="bi bi-trash"></i>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )) : (
                      <tr><td colSpan="7" className="text-center py-4 text-muted">Aucun utilisateur trouvé</td></tr>
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

      {/* Create User Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" style={{ maxHeight: 'calc(100vh - 3rem)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h5>Nouvel utilisateur</h5>
              <button className="btn-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden' }}>
              <div className="modal-body" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                {formError && <div className="alert alert-danger" style={{ whiteSpace: 'pre-line', fontSize: '0.85rem', padding: '0.5rem 0.75rem' }}>{formError}</div>}
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Prénom</label>
                    <input type="text" className="form-control" value={form.first_name} onChange={e => setForm({...form, first_name: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nom</label>
                    <input type="text" className="form-control" value={form.last_name} onChange={e => setForm({...form, last_name: e.target.value})} />
                  </div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Nom d'utilisateur *</label>
                    <input type="text" className="form-control" required value={form.username} onChange={e => setForm({...form, username: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Rôle *</label>
                    <select className="form-control" required value={form.role} onChange={e => setForm({...form, role: e.target.value, new_secretariat_nom: '', new_secretariat_type: ''})}>
                      {creatableRoles.map(r => <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>)}
                    </select>
                    {form.role === 'CHEF_CPFAE_ADMIN' && users.some(u => u.role === 'CHEF_CPFAE_ADMIN') && (
                      <small className="text-danger"><i className="bi bi-exclamation-triangle me-1"></i>Un Chef CPFAE Admin existe déjà. Ce rôle est unique sur la plateforme.</small>
                    )}
                  </div>
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
                  <label className="form-label">Mot de passe *</label>
                  <input type="password" className="form-control" required value={form.password} onChange={e => setForm({...form, password: e.target.value})} />
                </div>
                {!['SECRETARIAT', 'CHEF_SECRETARIAT'].includes(currentUser?.role) && !['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN'].includes(form.role) && (
                  <div className="form-group">
                    <label className="form-label">Secrétariat</label>
                    <select className="form-control" value={form.secretariat} onChange={e => setForm({...form, secretariat: e.target.value})}>
                      <option value="">-- Aucun --</option>
                      {secretariats.map(s => (
                        <option key={s.id} value={s.id}>{s.nom}</option>
                      ))}
                    </select>
                    {form.role === 'CHEF_SECRETARIAT' && form.secretariat && users.some(u => u.role === 'CHEF_SECRETARIAT' && String(u.secretariat) === String(form.secretariat)) && (
                      <small className="text-danger"><i className="bi bi-exclamation-triangle me-1"></i>Ce secrétariat a déjà un Chef Secrétariat.</small>
                    )}
                  </div>
                )}
                {!['SECRETARIAT', 'CHEF_SECRETARIAT'].includes(currentUser?.role) && form.role === 'SECRETARIAT' && !form.secretariat && (
                  <div style={{ background: '#f0f7ff', border: '1px solid #bcd', borderRadius: 6, padding: '0.6rem 0.75rem' }}>
                    <p className="text-muted small" style={{ fontWeight: 600, marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      <i className="bi bi-building-add me-1"></i>Ou créer un nouveau secrétariat
                    </p>
                    <div className="grid-2">
                      <div className="form-group">
                        <label className="form-label">Nom</label>
                        <input type="text" className="form-control" value={form.new_secretariat_nom}
                          onChange={e => setForm({...form, new_secretariat_nom: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Type</label>
                        <select className="form-control" value={form.new_secretariat_type} onChange={e => setForm({...form, new_secretariat_type: e.target.value})}>
                          <option value="">-- Sélectionner --</option>
                          <option value="A">Type A (grades A1, A2, A3…)</option>
                          <option value="B">Type B (grades B1, B2, B3…)</option>
                          <option value="C">Type C (grades C1, C2, C3…)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-dfrc" disabled={saving}>{saving ? 'Création...' : 'Créer'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && editingUser && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content" style={{ maxHeight: 'calc(100vh - 3rem)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h5><i className="bi bi-pencil-square me-2"></i>Modifier — {editingUser.username}</h5>
              <button className="btn-close" onClick={() => setShowEditModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleEdit} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden' }}>
              <div className="modal-body" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                {editError && <div className="alert alert-danger" style={{ whiteSpace: 'pre-line' }}>{editError}</div>}
                <div className="form-group">
                  <label className="form-label">Rôle</label>
                  <select
                    className="form-control"
                    value={editForm.role}
                    onChange={e => setEditForm({...editForm, role: e.target.value})}
                    disabled={!creatableRoles.includes(editingUser?.role)}
                  >
                    {creatableRoles.map(r => (
                      <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>
                    ))}
                  </select>
                  {!creatableRoles.includes(editingUser?.role) && (
                    <small className="text-warning"><i className="bi bi-lock me-1"></i>Rôle protégé — modification impossible.</small>
                  )}
                  {editForm.role === 'CHEF_CPFAE_ADMIN' && users.some(u => u.role === 'CHEF_CPFAE_ADMIN' && u.id !== editingUser?.id) && (
                    <small className="text-danger"><i className="bi bi-exclamation-triangle me-1"></i>Un Chef CPFAE Admin existe déjà. Ce rôle est unique sur la plateforme.</small>
                  )}
                  {editForm.role === 'CHEF_SECRETARIAT' && editForm.secretariat && (() => {
                    const secId = String(editForm.secretariat)
                    const hasChef = users.some(u => u.role === 'CHEF_SECRETARIAT' && String(u.secretariat) === secId && u.id !== editingUser?.id)
                    return hasChef ? (
                      <small className="text-danger"><i className="bi bi-exclamation-triangle me-1"></i>Ce secrétariat a déjà un Chef Secrétariat.</small>
                    ) : null
                  })()}
                </div>
                {currentUser?.role !== 'SECRETARIAT' && !['CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN'].includes(editForm.role) && (
                  <div className="form-group">
                    <label className="form-label">Secrétariat</label>
                    <select className="form-control" value={editForm.secretariat} onChange={e => setEditForm({...editForm, secretariat: e.target.value})}>
                      <option value="">-- Aucun --</option>
                      {secretariats.map(s => (
                        <option key={s.id} value={s.id}>{s.nom}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">Nom d'utilisateur *</label>
                  <input type="text" className="form-control" required value={editForm.username} onChange={e => setEditForm({...editForm, username: e.target.value})} />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Prénom</label>
                    <input type="text" className="form-control" value={editForm.first_name} onChange={e => setEditForm({...editForm, first_name: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nom</label>
                    <input type="text" className="form-control" value={editForm.last_name} onChange={e => setEditForm({...editForm, last_name: e.target.value})} />
                  </div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Adresse e-mail</label>
                    <input type="email" className="form-control" value={editForm.email} onChange={e => setEditForm({...editForm, email: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Téléphone</label>
                    <input type="text" className="form-control" value={editForm.telephone} onChange={e => setEditForm({...editForm, telephone: e.target.value})} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Statut</label>
                  <select className="form-control" value={editForm.is_active ? 'true' : 'false'}
                    onChange={e => setEditForm({...editForm, is_active: e.target.value === 'true'})}>
                    <option value="true">Actif</option>
                    <option value="false">Inactif</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Nouveau mot de passe <small className="text-muted">(laisser vide pour ne pas changer)</small></label>
                  <input type="password" className="form-control" value={editForm.password}
                    onChange={e => setEditForm({...editForm, password: e.target.value})} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-dfrc" disabled={saving}>{saving ? 'Enregistrement...' : 'Enregistrer'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
