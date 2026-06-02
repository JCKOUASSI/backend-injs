import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'
import { useDebounce } from '../hooks/useDebounce'
import { formatMoney } from '../components/FinanceStatsGrid'
import FinancePageShell, { FinanceNavActions } from '../components/finance/FinancePageShell'
import FinanceDetailModal from '../components/finance/FinanceDetailModal'
import {
  buildFinanceListSearchParams,
  buildFinanceQuery,
  FINANCE_QUERY_STORAGE_KEY,
  loadFinancePeriod,
  loadFinanceFilters,
  readFinanceStateFromSearchParams,
  saveFinancePeriod,
  saveFinanceFilters,
} from '../utils/financePeriod'
import {
  buildFormateursListSearchParams,
  LIST_STORAGE_KEYS,
  parseListPage,
  readFormateursListExtras,
} from '../utils/listFilters'
import { usePersistedListQuery } from '../hooks/usePersistedListQuery'
import Pagination from '../components/Pagination'

const emptyForm = { numerobadge: '', nom: '', prenom: '', email: '', telephone: '', specialite: '', organisation: '', secretariats: [] }

const financeStatsForGrid = (detail) => ({
  ...(detail?.statistiques || {}),
  sessions_count: detail?.sessions_count,
  total_duree_minutes: detail?.total_duree_minutes,
  total_duree_realisee_minutes: detail?.total_duree_realisee_minutes,
})

export default function Formateurs() {
  const { user } = useAuth()
  const canViewFinanceData = ['FINANCE', 'DIRECTION'].includes(user?.role)
  const [searchParams] = useSearchParams()
  const urlFinance = readFinanceStateFromSearchParams(searchParams)
  const listExtras = readFormateursListExtras(searchParams)
  const [formateurs, setFormateurs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(() => parseListPage(searchParams))
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState(listExtras.search)
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
  const [financeDetailTab, setFinanceDetailTab] = useState('statistiques')
  const [financePeriod, setFinancePeriod] = useState(
    () => urlFinance?.period ?? loadFinancePeriod(),
  )
  const [financeFilters, setFinanceFilters] = useState(
    () => urlFinance?.filters ?? loadFinanceFilters(),
  )
  const [financePeriodeInfo, setFinancePeriodeInfo] = useState(null)
  const [financeSecretariatFiltre, setFinanceSecretariatFiltre] = useState(null)

  const debouncedSearch = useDebounce(search)
  const [appliedFinancePeriod, setAppliedFinancePeriod] = useState(
    () => urlFinance?.period ?? loadFinancePeriod(),
  )
  const [appliedFinanceFilters, setAppliedFinanceFilters] = useState(
    () => urlFinance?.filters ?? loadFinanceFilters(),
  )

  const syncFormateursQuery = () => buildFormateursListSearchParams(
    page,
    debouncedSearch,
    appliedFinancePeriod,
    appliedFinanceFilters,
    canViewFinanceData,
    buildFinanceListSearchParams,
  )

  usePersistedListQuery(
    canViewFinanceData ? FINANCE_QUERY_STORAGE_KEY : LIST_STORAGE_KEYS.formateurs,
    syncFormateursQuery,
    [page, debouncedSearch, appliedFinancePeriod, appliedFinanceFilters, canViewFinanceData],
  )

  useEffect(() => { loadFormateurs() }, [page, debouncedSearch, appliedFinancePeriod, appliedFinanceFilters])
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
      const endpoint = canViewFinanceData
        ? '/formations/formateurs/finance-report/'
        : '/formations/formateurs/list/'
      if (canViewFinanceData) {
        params.set('include_sessions', '0')
        buildFinanceQuery(appliedFinancePeriod, appliedFinanceFilters).forEach((v, k) => params.set(k, v))
      }
      const response = await api.get(`${endpoint}?${params}`)
      const data = Array.isArray(response.data) ? response.data : (response.data.results || [])
      setFormateurs(data)
      setTotalPages(response.data.total_pages || 1)
      if (canViewFinanceData) {
        if (response.data?.periode) setFinancePeriodeInfo(response.data.periode)
        setFinanceSecretariatFiltre(response.data?.secretariat_filtre || null)
      }
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

  const formatDate = (value) => {
    if (!value) return '-'
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return '-'
    return d.toLocaleDateString('fr-FR')
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
    const qs = buildFinanceQuery(appliedFinancePeriod, appliedFinanceFilters).toString()
    const base = format === 'pdf'
      ? `/exports/formateur/${f.id}/pdf/`
      : `/exports/formateur/${f.id}/excel/`
    const path = qs ? `${base}?${qs}` : base
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
    setFinanceDetailTab('statistiques')
    setFinanceDetail({
      id: f.id,
      nom: f.nom,
      prenom: f.prenom,
      numerobadge: f.numerobadge,
      email: f.email,
      telephone: f.telephone,
      specialite: f.specialite,
      organisation: f.organisation,
      secretariats_noms: f.secretariats_noms,
      nb_formations: f.nb_formations,
      sessions: [],
      total_duree_minutes: f.total_duree_minutes,
    })
    setFinanceDetailLoading(true)
    try {
      const periodQs = buildFinanceQuery(appliedFinancePeriod, appliedFinanceFilters).toString()
      const res = await api.get(
        `/formations/formateurs/finance-report/?formateur_id=${f.id}${periodQs ? `&${periodQs}` : ''}`
      )
      const rows = Array.isArray(res.data) ? res.data : (res.data.results || [])
      const row = rows[0]
      if (row) setFinanceDetail(row)
      if (res.data?.periode) setFinancePeriodeInfo(res.data.periode)
    } catch {
      showToast('Impossible de charger le détail', 'error')
      setFinanceDetail(null)
    } finally {
      setFinanceDetailLoading(false)
    }
  }

  const financeListContent = (
    <>
      <div className="finance-section" style={{ marginBottom: '0.75rem' }}>
        <div className="finance-section-body">
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ flex: '1 1 280px' }}>
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-search"></i></span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Rechercher par nom, prénom ou spécialité…"
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1) }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <section className="finance-section">
        <div className="finance-section-header">
          <h2><i className="bi bi-people"></i>Suivi des formateurs</h2>
          <span className="badge-bg-secondary">{formateurs.length} résultat(s)</span>
        </div>
        <div className="finance-table-wrap">
          {loading ? (
            <div className="loading py-5"><div className="spinner"></div></div>
          ) : (
            <>
              <table className="finance-table">
                <thead>
                  <tr>
                    <th>N°</th>
                    <th>Nom</th>
                    <th>Prénom</th>
                    <th>Spécialité</th>
                    <th>Séances</th>
                    <th>Planifié</th>
                    <th>Réalisé</th>
                    <th>Taux</th>
                    <th>Montant</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {formateurs.length > 0 ? formateurs.map((f) => {
                    const taux = f.statistiques?.taux_realisation_pct ?? 0
                    return (
                      <tr key={f.id}>
                        <td><span className="badge-bg-info">{f.numerobadge || '-'}</span></td>
                        <td><strong>{f.nom}</strong></td>
                        <td>{f.prenom}</td>
                        <td className="small text-muted">{f.specialite || '—'}</td>
                        <td><span className="badge-bg-secondary">{f.sessions_count ?? 0}</span></td>
                        <td style={{ whiteSpace: 'nowrap' }}>{formatDuration(f.total_duree_minutes)}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>{formatDuration(f.total_duree_realisee_minutes)}</td>
                        <td>
                          <div>{taux}%</div>
                          <div className="finance-taux-bar">
                            <div className="finance-taux-bar-fill" style={{ width: `${Math.min(100, taux)}%` }} />
                          </div>
                        </td>
                        <td style={{ whiteSpace: 'nowrap', fontWeight: 700, color: 'var(--fin-green)' }}>
                          {formatMoney(f.montant_total_realise)} F
                        </td>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <button
                            type="button"
                            onClick={() => openFinanceDetail(f)}
                            className="btn btn-dfrc btn-sm"
                          >
                            <i className="bi bi-eye me-1"></i>Fiche
                          </button>
                        </td>
                      </tr>
                    )
                  }) : (
                    <tr>
                      <td colSpan="10">
                        <div className="finance-empty"><i className="bi bi-inbox"></i>Aucun formateur</div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
              <Pagination
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                className="p-3"
              />
            </>
          )}
        </div>
      </section>
    </>
  )

  if (canViewFinanceData) {
    return (
      <FinancePageShell
        title="Suivi Finance"
        subtitle="Temps de cours et rémunération par formateur"
        icon="bi-cash-stack"
        actions={<FinanceNavActions active="formateurs" />}
        period={financePeriod}
        onPeriodChange={setFinancePeriod}
        onPeriodApply={() => {
          saveFinancePeriod(financePeriod)
          saveFinanceFilters(financeFilters)
          setAppliedFinancePeriod({ ...financePeriod })
          setAppliedFinanceFilters({ ...financeFilters })
          setPage(1)
        }}
        periodApplying={loading}
        periodeInfo={financePeriodeInfo}
        filters={financeFilters}
        onFiltersChange={setFinanceFilters}
        secretariats={secretariats}
        secretariatFiltre={financeSecretariatFiltre}
      >
        {financeListContent}
        {financeDetail && (
          <FinanceDetailModal
            financeDetail={financeDetail}
            financeDetailLoading={financeDetailLoading}
            financeDetailTab={financeDetailTab}
            setFinanceDetailTab={setFinanceDetailTab}
            onClose={() => !financeDetailLoading && setFinanceDetail(null)}
            formatDuration={formatDuration}
            formatDate={formatDate}
            exportFinanceSummary={exportFinanceSummary}
            financeStatsForGrid={financeStatsForGrid}
          />
        )}
      </FinancePageShell>
    )
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
                      {canViewFinanceData && <th>Séances</th>}
                      {canViewFinanceData && <th>Temps planifié</th>}
                      {canViewFinanceData && <th>Temps réalisé</th>}
                      {canViewFinanceData && <th>Taux réal.</th>}
                      {canViewFinanceData && <th>Montant</th>}
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
                          <td><span className="badge-bg-info">{formatDuration(f.total_duree_minutes)}</span></td>
                        )}
                        {canViewFinanceData && (
                          <td><span className="badge-bg-success">{formatDuration(f.total_duree_realisee_minutes)}</span></td>
                        )}
                        {canViewFinanceData && (
                          <td>{(f.statistiques?.taux_realisation_pct ?? 0)}%</td>
                        )}
                        {canViewFinanceData && (
                          <td style={{ whiteSpace: 'nowrap', fontWeight: 600 }}>{formatMoney(f.montant_total_realise)} FCFA</td>
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
                      <tr><td colSpan={canViewFinanceData ? 10 : (canEdit ? 8 : 7)} className="text-center py-4 text-muted">Aucun formateur trouvé</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
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
