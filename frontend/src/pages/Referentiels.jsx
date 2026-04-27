import { useState, useEffect } from 'react'
import api from '../services/api'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'

const TABS = [
  { key: 'formations', label: 'Formations', icon: 'bi-mortarboard' },
  { key: 'modules', label: 'Modules', icon: 'bi-journal-bookmark' },
  { key: 'categories', label: 'Catégories', icon: 'bi-tags' },
  { key: 'grades', label: 'Grades', icon: 'bi-award' },
  { key: 'vagues', label: 'Vagues', icon: 'bi-layers' },
  { key: 'sites', label: 'Sites', icon: 'bi-geo-alt' },
  { key: 'batiments', label: 'Bâtiments', icon: 'bi-building' },
  { key: 'salles', label: 'Salles', icon: 'bi-door-open' },
  { key: 'types_secretariat', label: 'Types secrétariat', icon: 'bi-building-gear' },
]

function RefTable({ columns, rows, onEdit, onDelete, onToggle }) {
  if (rows.length === 0) return (
    <div className="text-center py-5 text-muted">
      <i className="bi bi-inbox" style={{ fontSize: '2rem' }}></i>
      <p className="mt-2">Aucune entrée — cliquez sur « Ajouter » pour commencer.</p>
    </div>
  )
  return (
    <div className="table-responsive">
      <table className="table" style={{ width: '100%' }}>
        <thead>
          <tr>
            {columns.map(c => <th key={c.key}>{c.label}</th>)}
            <th style={{ width: 120 }}>Statut</th>
            <th style={{ width: 110 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.id}>
              {columns.map(c => <td key={c.key}>{c.render ? c.render(row) : (row[c.key] ?? '—')}</td>)}
              <td>
                <button
                  className={`badge ${row.actif ? 'badge-planifiee' : 'badge-suspendue'}`}
                  style={{ border: 'none', cursor: 'pointer', fontSize: '0.78rem' }}
                  onClick={() => onToggle(row)}
                  title={row.actif ? 'Désactiver' : 'Activer'}
                >
                  {row.actif ? 'Actif' : 'Inactif'}
                </button>
              </td>
              <td>
                <div className="btn-group">
                  <button className="btn btn-outline-primary btn-sm" onClick={() => onEdit(row)} title="Modifier">
                    <i className="bi bi-pencil"></i>
                  </button>
                  <button className="btn btn-outline-danger btn-sm" onClick={() => onDelete(row)} title="Supprimer">
                    <i className="bi bi-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Modal({ title, onClose, onSubmit, saving, children }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: 480 }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h5>{title}</h5>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="modal-body">{children}</div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-dfrc" disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Referentiels() {
  const [tab, setTab] = useState('formations')
  const { showToast } = useToast()
  const [confirmDialog, setConfirmDialog] = useState(null)

  // Data for all tabs
  const [data, setData] = useState({
    formations: [], modules: [], categories: [], grades: [], vagues: [], sites: [], batiments: [], salles: [], types_secretariat: []
  })
  const [loading, setLoading] = useState(true)

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingRow, setEditingRow] = useState(null)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)

  const URL_MAP = {
    formations: '/formations/ref/formations/',
    modules: '/formations/ref/modules/',
    categories: '/formations/ref/categories/',
    grades: '/formations/ref/grades/',
    vagues: '/formations/ref/vagues/',
    sites: '/formations/ref/sites/',
    batiments: '/formations/ref/batiments/',
    salles: '/formations/ref/salles/',
    types_secretariat: '/formations/ref/types-secretariat/',
  }

  const loadAll = async () => {
    setLoading(true)
    try {
      const results = await Promise.all(Object.entries(URL_MAP).map(([k, url]) =>
        api.get(url).then(r => [k, r.data])
      ))
      const next = {}
      results.forEach(([k, v]) => { next[k] = v })
      setData(next)
    } catch { showToast('Erreur de chargement', 'error') }
    finally { setLoading(false) }
  }

  useEffect(() => { loadAll() }, [])

  const openCreate = () => {
    setEditingRow(null)
    setForm(defaultForm(tab))
    setShowModal(true)
  }

  const openEdit = (row) => {
    setEditingRow(row)
    setForm({ ...row })
    setShowModal(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const url = URL_MAP[tab]
      if (editingRow) {
        await api.put(`${url}${editingRow.id}/`, form)
        showToast('Modifié avec succès')
      } else {
        await api.post(url, form)
        showToast('Ajouté avec succès')
      }
      setShowModal(false)
      await loadAll()
    } catch (err) {
      const msg = err.response?.data ? JSON.stringify(err.response.data) : 'Erreur'
      showToast(msg, 'error')
    } finally { setSaving(false) }
  }

  const handleDelete = (row) => {
    setConfirmDialog({
      message: `Supprimer cet élément ?`,
      detail: 'Cette action est irréversible.',
      onConfirm: async () => {
        try {
          await api.delete(`${URL_MAP[tab]}${row.id}/`)
          showToast('Supprimé')
          await loadAll()
        } catch { showToast('Erreur lors de la suppression', 'error') }
      }
    })
  }

  const handleToggle = async (row) => {
    try {
      await api.put(`${URL_MAP[tab]}${row.id}/`, { ...row, actif: !row.actif })
      showToast(row.actif ? 'Désactivé' : 'Activé')
      await loadAll()
    } catch { showToast('Erreur', 'error') }
  }

  const defaultForm = (t) => {
    if (t === 'formations') return { intitule: '', actif: true }
    if (t === 'modules') return { intitule: '', volume_horaire: '', actif: true }
    if (t === 'categories') return { libelle: '', actif: true }
    if (t === 'grades') return { libelle: '', categorie_id: '', actif: true }
    if (t === 'sites') return { nom: '', actif: true }
    if (t === 'batiments') return { nom: '', site_id: '', actif: true }
    if (t === 'salles') return { nom: '', site_id: '', batiment_id: '', actif: true }
    if (t === 'vagues') return { libelle: '', ordre: 1, actif: true }
    if (t === 'types_secretariat') return { libelle: '', actif: true }
    return {}
  }

  const COLUMNS = {
    formations: [{ key: 'intitule', label: 'Intitulé' }],
    modules: [
      { key: 'intitule', label: 'Intitulé' },
      { key: 'volume_horaire', label: 'Volume horaire (h)', render: r => r.volume_horaire ?? '—' },
    ],
    categories: [
      { key: 'libelle', label: 'Libellé' },
    ],
    grades: [
      { key: 'libelle', label: 'Libellé' },
      { key: 'categorie_id', label: 'Catégorie', render: r => {
        const cat = data.categories.find(c => c.id === r.categorie_id)
        return cat ? cat.libelle : '—'
      }},
    ],
    vagues: [
      { key: 'libelle', label: 'Libellé' },
      { key: 'ordre', label: 'Ordre', render: r => r.ordre ?? '—' },
    ],
    types_secretariat: [
      { key: 'libelle', label: 'Libellé' },
    ],
    sites: [{ key: 'nom', label: 'Nom' }],
    batiments: [
      { key: 'nom', label: 'Nom' },
      { key: 'site_id', label: 'Site', render: r => {
        const s = data.sites.find(x => x.id === r.site_id)
        return s ? s.nom : '—'
      }},
    ],
    salles: [
      { key: 'nom', label: 'Nom' },
      { key: 'site_id', label: 'Site', render: r => {
        const s = data.sites.find(x => x.id === r.site_id)
        return s ? s.nom : '—'
      }},
      { key: 'batiment_id', label: 'Bâtiment', render: r => {
        const b = data.batiments.find(x => x.id === r.batiment_id)
        return b ? b.nom : '—'
      }},
    ],
  }

  const renderForm = () => {
    const f = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target.value }))
    const check = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target.checked }))

    if (tab === 'formations') return (
      <div className="form-group">
        <label className="form-label">Intitulé *</label>
        <input className="form-control" required value={form.intitule || ''} onChange={f('intitule')} placeholder="Ex: FORMATION EN ADMINISTRATION DE BASE" />
      </div>
    )

    if (tab === 'modules') return (<>
      <div className="form-group">
        <label className="form-label">Intitulé *</label>
        <input className="form-control" required value={form.intitule || ''} onChange={f('intitule')} placeholder="Ex: Déontologie de la Fonction Publique" />
      </div>
      <div className="form-group">
        <label className="form-label">Volume horaire (h)</label>
        <input type="number" className="form-control" min="0" step="0.5" value={form.volume_horaire || ''} onChange={f('volume_horaire')} placeholder="Ex: 30" />
      </div>
    </>)

    if (tab === 'categories') return (
      <div className="form-group">
        <label className="form-label">Libellé *</label>
        <input className="form-control" required value={form.libelle || ''} onChange={f('libelle')} placeholder="Ex: Catégorie A" />
      </div>
    )

    if (tab === 'grades') return (<>
      <div className="form-group">
        <label className="form-label">Libellé *</label>
        <input className="form-control" required value={form.libelle || ''} onChange={f('libelle')} placeholder="Ex: Attaché d'Administration" />
      </div>
      <div className="form-group">
        <label className="form-label">Catégorie</label>
        <select className="form-control" value={form.categorie_id || ''} onChange={f('categorie_id')}>
          <option value="">— Aucune —</option>
          {data.categories.map(c => <option key={c.id} value={c.id}>{c.libelle}</option>)}
        </select>
      </div>
    </>)

    if (tab === 'vagues') return (<>
      <div className="form-group">
        <label className="form-label">Libellé *</label>
        <input className="form-control" required value={form.libelle || ''} onChange={f('libelle')} placeholder="Ex: PREMIERE VAGUE" />
      </div>
      <div className="form-group">
        <label className="form-label">Ordre d'affichage</label>
        <input type="number" className="form-control" min="1" value={form.ordre || 1} onChange={f('ordre')} placeholder="Ex: 1" />
      </div>
    </>)

    if (tab === 'types_secretariat') return (
      <div className="form-group">
        <label className="form-label">Libellé *</label>
        <input className="form-control" required value={form.libelle || ''} onChange={f('libelle')} placeholder="Ex: Secrétariat de type A" />
      </div>
    )

    if (tab === 'sites') return (
      <div className="form-group">
        <label className="form-label">Nom *</label>
        <input className="form-control" required value={form.nom || ''} onChange={f('nom')} placeholder="Ex: CPFAE" />
      </div>
    )

    if (tab === 'batiments') return (<>
      <div className="form-group">
        <label className="form-label">Nom *</label>
        <input className="form-control" required value={form.nom || ''} onChange={f('nom')} placeholder="Ex: Bâtiment A" />
      </div>
      <div className="form-group">
        <label className="form-label">Site *</label>
        <select className="form-control" required value={form.site_id || ''} onChange={f('site_id')}>
          <option value="">— Choisir —</option>
          {data.sites.map(s => <option key={s.id} value={s.id}>{s.nom}</option>)}
        </select>
      </div>
    </>)

    if (tab === 'salles') return (<>
      <div className="form-group">
        <label className="form-label">Nom *</label>
        <input className="form-control" required value={form.nom || ''} onChange={f('nom')} placeholder="Ex: Salle A" />
      </div>
      <div className="form-group">
        <label className="form-label">Site *</label>
        <select className="form-control" required value={form.site_id || ''} onChange={e => setForm(prev => ({ ...prev, site_id: e.target.value, batiment_id: '' }))}>
          <option value="">— Choisir —</option>
          {data.sites.map(s => <option key={s.id} value={s.id}>{s.nom}</option>)}
        </select>
      </div>
      <div className="form-group">
        <label className="form-label">Bâtiment</label>
        <select className="form-control" value={form.batiment_id || ''} onChange={f('batiment_id')}>
          <option value="">— Aucun —</option>
          {data.batiments
            .filter(b => !form.site_id || String(b.site_id) === String(form.site_id))
            .map(b => <option key={b.id} value={b.id}>{b.nom}</option>)}
        </select>
      </div>
    </>)

    return null
  }

  const currentTab = TABS.find(t => t.key === tab)
  const rows = data[tab] || []

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title"><i className="bi bi-sliders me-2"></i>Référentiels</h1>
          <p className="page-subtitle">Gérez les données de référence utilisées dans les formulaires</p>
        </div>
        <button className="btn btn-dfrc" onClick={openCreate}>
          <i className="bi bi-plus-lg me-1"></i> Ajouter
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', marginBottom: '1.5rem', borderBottom: '2px solid var(--border-color)', paddingBottom: '0' }}>
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setShowModal(false) }}
            style={{
              padding: '0.5rem 1.1rem',
              border: 'none',
              borderRadius: '6px 6px 0 0',
              background: tab === t.key ? 'var(--ci-green-dark)' : 'transparent',
              color: tab === t.key ? '#fff' : 'var(--text-secondary)',
              fontWeight: tab === t.key ? 600 : 400,
              cursor: 'pointer',
              fontSize: '0.9rem',
              transition: 'all 0.15s',
            }}
          >
            <i className={`bi ${t.icon} me-1`}></i>{t.label}
            <span style={{
              marginLeft: '0.4rem',
              background: tab === t.key ? 'rgba(255,255,255,0.25)' : 'var(--border-color)',
              color: tab === t.key ? '#fff' : 'var(--text-secondary)',
              borderRadius: '10px',
              padding: '0 6px',
              fontSize: '0.75rem',
            }}>
              {(data[t.key] || []).length}
            </span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span><i className={`bi ${currentTab?.icon} me-2`}></i>{currentTab?.label}</span>
          <span className="text-muted small">{rows.length} entrée{rows.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="text-center py-5"><div className="spinner"></div></div>
          ) : (
            <RefTable
              columns={COLUMNS[tab] || []}
              rows={rows}
              onEdit={openEdit}
              onDelete={handleDelete}
              onToggle={handleToggle}
            />
          )}
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <Modal
          title={editingRow ? `Modifier — ${currentTab?.label}` : `Ajouter — ${currentTab?.label}`}
          onClose={() => setShowModal(false)}
          onSubmit={handleSubmit}
          saving={saving}
        >
          {renderForm()}
        </Modal>
      )}

      {confirmDialog && (
        <ConfirmModal
          message={confirmDialog.message}
          detail={confirmDialog.detail}
          onConfirm={() => { setConfirmDialog(null); confirmDialog.onConfirm() }}
          onCancel={() => setConfirmDialog(null)}
        />
      )}
    </div>
  )
}
