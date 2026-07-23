import { useState } from 'react'
import { FiUserX, FiUserCheck } from 'react-icons/fi'
import Modal from '../../../components/common/Modal'
import DetailView from '../../../components/common/DetailView'
import IconActionButtons from '../../../components/common/IconActionButtons'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import { fetchUsers } from '../../../api/users'
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
  return ROLES_SYSTEME.find(r => r.id === roleId)?.label ?? roleId
}

function initials(prenom, nom) {
  return `${prenom?.[0] ?? ''}${nom?.[0] ?? ''}`.toUpperCase()
}

export default function SettingsUsers() {
  const { showToast } = useToast()
  const { data, loading, error } = useFetch(() => fetchUsers())
  const users = data?.results || []
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statutFilter, setStatutFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState(EMPTY)

  const filtered = users.filter(u => {
    const q = search.toLowerCase()
    const matchSearch = !q || `${u.nom} ${u.prenom} ${u.email}`.toLowerCase().includes(q)
    const matchRole = !roleFilter || u.role === roleFilter
    const matchStatut = !statutFilter || u.statut === statutFilter
    return matchSearch && matchRole && matchStatut
  })

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

  const toggleStatut = (u) => {
    showToast('Activation/désactivation via API PATCH — à implémenter', 'info')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    showToast('Création/modification utilisateur via l\'API — utilisez l\'administration serveur', 'info')
    setShowForm(false)
  }

  if (loading) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger">Erreur de chargement : {error}</div>
  }

  return (
    <>
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <p className="text-muted mb-0 small">
          Comptes d&apos;accès — {data?.count || 0} utilisateur(s) depuis l&apos;API.
        </p>
        <button type="button" className="btn btn-injs-primary btn-sm" onClick={openCreate}>
          + Créer un utilisateur
        </button>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2">
          <div className="col-md-4">
            <input
              className="form-control"
              placeholder="Rechercher par nom ou email..."
              value={search}
              onChange={ev => setSearch(ev.target.value)}
            />
          </div>
          <div className="col-md-3">
            <select className="form-select" value={roleFilter} onChange={ev => setRoleFilter(ev.target.value)}>
              <option value="">Tous les rôles</option>
              {ROLES_SYSTEME.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>
          </div>
          <div className="col-md-2">
            <select className="form-select" value={statutFilter} onChange={ev => setStatutFilter(ev.target.value)}>
              <option value="">Tous statuts</option>
              <option value="Actif">Actif</option>
              <option value="Inactif">Inactif</option>
            </select>
          </div>
          <div className="col-md-3">
            <div className="text-muted small pt-2">{filtered.length} utilisateur(s)</div>
          </div>
        </div>
      </div>

      <div className="card-injs overflow-hidden">
        <div className="table-responsive">
          <table className="table table-injs table-hover mb-0">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Statut</th>
                <th>Dernière connexion</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(u => (
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
                  <td>{u.email}</td>
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
                  <td className="text-muted small">{u.lastLogin}</td>
                  <td>
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
            </tbody>
          </table>
        </div>
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
              <input className="form-control" required value={form.prenom} onChange={ev => setForm({ ...form, prenom: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Nom *</label>
              <input className="form-control" required value={form.nom} onChange={ev => setForm({ ...form, nom: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Email *</label>
              <input type="email" className="form-control" required value={form.email} onChange={ev => setForm({ ...form, email: ev.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Rôle *</label>
              <select className="form-select" value={form.role} onChange={ev => setForm({ ...form, role: ev.target.value })}>
                {ROLES_SYSTEME.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
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
                  onChange={ev => setForm({ ...form, password: ev.target.value })}
                />
              </div>
            )}
            <div className="col-md-6">
              <label className="form-label">Statut</label>
              <select className="form-select" value={form.statut} onChange={ev => setForm({ ...form, statut: ev.target.value })}>
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
              <select className="form-select" value={form.linkedType} onChange={ev => setForm({ ...form, linkedType: ev.target.value })}>
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
                onChange={ev => setForm({ ...form, linkedId: ev.target.value })}
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
