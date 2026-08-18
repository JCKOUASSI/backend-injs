import { useEffect, useMemo, useState } from 'react'
import { FiUserX, FiUserCheck } from 'react-icons/fi'
import Modal from '../../../components/common/Modal'
import DetailView from '../../../components/common/DetailView'
import IconActionButtons from '../../../components/common/IconActionButtons'
import PaginationBar from '../../../components/common/PaginationBar'
import { useToast } from '../../../context/ToastContext'
import { ROLES_SYSTEME } from '../../../data/mockData'

const EMPTY = {
  prenom: '',
  nom: '',
  email: '',
  role: 'etudiant',
  statut: 'Actif',
  password: '',
  linkedId: '',
  linkedType: '',
}

const ROLE_BADGE = {
  admin: 'badge-lmd-doctorat',
  professeur: 'badge-lmd-master',
  etudiant: 'badge-lmd-licence',
  secretaire: 'badge-injs',
}

function getRoleLabel(roleId) {
  return ROLES_SYSTEME.find((r) => r.id === roleId)?.label ?? roleId
}

function initials(prenom, nom) {
  return `${prenom?.[0] ?? ''}${nom?.[0] ?? ''}`.toUpperCase() || '?'
}

export default function SettingsUsers({
  users = [],
  totalCount = 0,
  byRole = {},
  loading = false,
  error = null,
  onReload,
  createNonce = 0,
  onFilteredCountChange,
  hideCreateButton = false,
}) {
  const { showToast } = useToast()
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statutFilter, setStatutFilter] = useState('')
  const [viewMode, setViewMode] = useState('table')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)

  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(EMPTY)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [searchInput])

  useEffect(() => {
    if (createNonce > 0) {
      setEditingId(null)
      setForm(EMPTY)
      setShowForm(true)
    }
  }, [createNonce])

  const filtered = useMemo(() => {
    return users.filter((u) => {
      const matchSearch = !search
        || `${u.nom} ${u.prenom} ${u.email} ${u.id}`.toLowerCase().includes(search)
      const matchRole = !roleFilter || u.role === roleFilter
      const matchStatut = !statutFilter || u.statut === statutFilter
      return matchSearch && matchRole && matchStatut
    })
  }, [users, search, roleFilter, statutFilter])

  useEffect(() => {
    onFilteredCountChange?.(filtered.length)
  }, [filtered.length, onFilteredCountChange])

  const total = filtered.length
  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return filtered.slice(start, start + pageSize)
  }, [filtered, page, pageSize])

  const setRoleAndReset = (value) => {
    setRoleFilter(value)
    setPage(1)
  }

  const setStatutAndReset = (value) => {
    setStatutFilter(value)
    setPage(1)
  }

  const openCreate = () => {
    setEditingId(null)
    setForm(EMPTY)
    setShowForm(true)
  }

  const openEdit = (u) => {
    setEditingId(u.id)
    setForm({
      prenom: u.prenom,
      nom: u.nom,
      email: u.email,
      role: u.role,
      statut: u.statut,
      password: '',
      linkedId: u.linkedId ?? '',
      linkedType: u.linkedType ?? '',
    })
    setShowForm(true)
  }

  const openDetail = (u) => {
    setSelected({
      Identifiant: u.id,
      Nom: `${u.prenom} ${u.nom}`,
      Email: u.email,
      Rôle: getRoleLabel(u.role),
      Statut: u.statut,
      'Dernière connexion': u.lastLogin,
      'Fiche liée': u.linkedId ? `${u.linkedType} — ${u.linkedId}` : '—',
    })
    setShowDetail(true)
  }

  const toggleStatut = () => {
    showToast('Activation/désactivation via API PATCH — à implémenter', 'info')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    showToast('Création/modification utilisateur via l\'API — utilisez l\'administration serveur', 'info')
    setShowForm(false)
    onReload?.()
  }

  if (loading && !users.length) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-0">Erreur de chargement : {error}</div>
  }

  return (
    <>
      {!hideCreateButton && (
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <p className="text-muted mb-0 small">
            Comptes d&apos;accès — {totalCount || users.length} utilisateur(s) depuis l&apos;API.
          </p>
          <button type="button" className="btn btn-injs-primary btn-sm" onClick={openCreate}>
            + Créer un utilisateur
          </button>
        </div>
      )}

      <div className="card-injs p-3 mb-3">
        <div className="d-flex flex-wrap gap-2 align-items-center">
          <span className="small text-muted me-1">Rôles :</span>
          <button
            type="button"
            className={`btn btn-sm ${!roleFilter ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
            onClick={() => setRoleAndReset('')}
          >
            Tous ({users.length})
          </button>
          {ROLES_SYSTEME.map((r) => (
            <button
              key={r.id}
              type="button"
              className={`btn btn-sm ${roleFilter === r.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => setRoleAndReset(r.id)}
            >
              {r.label} <span className="opacity-75">({byRole[r.id] || 0})</span>
            </button>
          ))}
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-4">
            <label className="form-label small mb-1">Recherche</label>
            <input
              className="form-control"
              placeholder="Nom, email, identifiant…"
              value={searchInput}
              onChange={(ev) => setSearchInput(ev.target.value)}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Statut</label>
            <select
              className="form-select"
              value={statutFilter}
              onChange={(ev) => setStatutAndReset(ev.target.value)}
            >
              <option value="">Tous</option>
              <option value="Actif">Actif</option>
              <option value="Inactif">Inactif</option>
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label small mb-1">Rôle</label>
            <select
              className="form-select"
              value={roleFilter}
              onChange={(ev) => setRoleAndReset(ev.target.value)}
            >
              <option value="">Tous</option>
              {ROLES_SYSTEME.map((r) => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Affichage</label>
            <div className="btn-group w-100" role="group">
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'table' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setViewMode('table')}
              >
                Liste
              </button>
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'cards' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setViewMode('cards')}
              >
                Cartes
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card-injs position-relative rooms-list-shell">
        {loading && (
          <div className="position-absolute top-0 end-0 m-2" style={{ zIndex: 3 }}>
            <div className="spinner-border spinner-border-sm text-primary" />
          </div>
        )}

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          disabled={loading}
          pageSizeOptions={[10, 15, 25, 50]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />

        <div className="rooms-list-body">
          {viewMode === 'table' ? (
            <div className="table-responsive">
              <table className="table table-hover mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Utilisateur</th>
                    <th>Email</th>
                    <th>Rôle</th>
                    <th>Statut</th>
                    <th>Dernière connexion</th>
                    <th className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          <span className="user-avatar">{initials(u.prenom, u.nom)}</span>
                          <div>
                            <div className="fw-semibold">{u.prenom} {u.nom}</div>
                            <code className="small text-muted">{u.id}</code>
                          </div>
                        </div>
                      </td>
                      <td className="small">{u.email}</td>
                      <td>
                        <span className={`badge-injs ${ROLE_BADGE[u.role] ?? ''}`}>
                          {getRoleLabel(u.role)}
                        </span>
                      </td>
                      <td>
                        <span className={`grade-badge ${u.statut === 'Actif' ? 'grade-valid' : 'grade-fail'}`}>
                          {u.statut}
                        </span>
                      </td>
                      <td className="text-muted small">{u.lastLogin || '—'}</td>
                      <td className="text-end">
                        <IconActionButtons
                          actions={[
                            { type: 'view', onClick: () => openDetail(u) },
                            { type: 'edit', onClick: () => openEdit(u) },
                            {
                              key: 'toggle',
                              title: u.statut === 'Actif' ? 'Désactiver' : 'Activer',
                              className: u.statut === 'Actif' ? 'btn-outline-danger' : 'btn-outline-secondary',
                              icon: u.statut === 'Actif' ? FiUserX : FiUserCheck,
                              onClick: () => toggleStatut(u),
                            },
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                  {!pageItems.length && (
                    <tr>
                      <td colSpan={6} className="text-center text-muted py-4">Aucun utilisateur trouvé</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-3">
              <div className="row g-3">
                {pageItems.map((u) => (
                  <div key={u.id} className="col-md-6 col-xl-4">
                    <div className="border rounded-3 p-3 h-100">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <code className="small">{u.id}</code>
                        <span className={`grade-badge ${u.statut === 'Actif' ? 'grade-valid' : 'grade-fail'}`}>
                          {u.statut}
                        </span>
                      </div>
                      <div className="d-flex align-items-center gap-2 mb-2">
                        <span className="user-avatar">{initials(u.prenom, u.nom)}</span>
                        <div>
                          <h6 className="fw-bold mb-0">{u.prenom} {u.nom}</h6>
                          <small className="text-muted">{u.email}</small>
                        </div>
                      </div>
                      <p className="small mb-3">
                        <span className={`badge-injs ${ROLE_BADGE[u.role] ?? ''}`}>
                          {getRoleLabel(u.role)}
                        </span>
                      </p>
                      <IconActionButtons
                        actions={[
                          { type: 'view', onClick: () => openDetail(u) },
                          { type: 'edit', onClick: () => openEdit(u) },
                          {
                            key: 'toggle',
                            title: u.statut === 'Actif' ? 'Désactiver' : 'Activer',
                            className: u.statut === 'Actif' ? 'btn-outline-danger' : 'btn-outline-secondary',
                            icon: u.statut === 'Actif' ? FiUserX : FiUserCheck,
                            onClick: () => toggleStatut(u),
                          },
                        ]}
                      />
                    </div>
                  </div>
                ))}
                {!pageItems.length && (
                  <div className="col-12 text-center text-muted py-4">Aucun utilisateur trouvé</div>
                )}
              </div>
            </div>
          )}
        </div>

        <PaginationBar
          page={page}
          pageSize={pageSize}
          total={total}
          disabled={loading}
          pageSizeOptions={[10, 15, 25, 50]}
          onPageChange={setPage}
          onPageSizeChange={(size) => {
            setPageSize(size)
            setPage(1)
          }}
        />
      </div>

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title={editingId ? 'Modifier l\'utilisateur' : 'Créer un utilisateur'}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="user-form" className="btn btn-injs-primary">
              {editingId ? 'Mettre à jour' : 'Créer le compte'}
            </button>
          </>
        }
      >
        <form id="user-form" onSubmit={handleSubmit}>
          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label">Prénom *</label>
              <input className="form-control" required value={form.prenom} onChange={(ev) => setForm({ ...form, prenom: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Nom *</label>
              <input className="form-control" required value={form.nom} onChange={(ev) => setForm({ ...form, nom: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Email *</label>
              <input type="email" className="form-control" required value={form.email} onChange={(ev) => setForm({ ...form, email: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Rôle *</label>
              <select className="form-select" value={form.role} onChange={(ev) => setForm({ ...form, role: ev.target.value })}>
                {ROLES_SYSTEME.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
              </select>
            </div>
            {!editingId && (
              <div className="col-md-6">
                <label className="form-label">Mot de passe temporaire *</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="L'utilisateur devra le changer à la 1ère connexion"
                  value={form.password}
                  onChange={(ev) => setForm({ ...form, password: ev.target.value })}
                />
              </div>
            )}
            <div className="col-md-6">
              <label className="form-label">Statut</label>
              <select className="form-select" value={form.statut} onChange={(ev) => setForm({ ...form, statut: ev.target.value })}>
                <option value="Actif">Actif</option>
                <option value="Inactif">Inactif</option>
              </select>
            </div>
            <div className="col-12">
              <hr className="my-1" />
              <p className="small text-muted mb-2">Liaison optionnelle avec une fiche académique existante</p>
            </div>
            <div className="col-md-6">
              <label className="form-label">Type de fiche</label>
              <select className="form-select" value={form.linkedType} onChange={(ev) => setForm({ ...form, linkedType: ev.target.value })}>
                <option value="">Aucune</option>
                <option value="etudiant">Étudiant</option>
                <option value="professeur">Professeur</option>
              </select>
            </div>
            <div className="col-md-6">
              <label className="form-label">Identifiant fiche (matricule / PRF)</label>
              <input
                className="form-control"
                placeholder="Ex. ETU2024001 ou PRF001"
                value={form.linkedId}
                onChange={(ev) => setForm({ ...form, linkedId: ev.target.value })}
              />
            </div>
          </div>
        </form>
      </Modal>

      <Modal show={showDetail} onClose={() => setShowDetail(false)} title="Fiche utilisateur">
        <DetailView data={selected} />
      </Modal>
    </>
  )
}
