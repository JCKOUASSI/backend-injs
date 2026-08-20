import { useEffect, useMemo, useState } from 'react'
import { FiAlertTriangle, FiCalendar, FiDatabase, FiLayers } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import Modal from '../../components/common/Modal'
import PaginationBar from '../../components/common/PaginationBar'
import ExportButtons from '../../components/common/ExportButtons'
import IconActionButtons from '../../components/common/IconActionButtons'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchUsers } from '../../api/users'
import {
  createReferentialEntry,
  deleteReferentialEntry,
  fetchReferentialPage,
  fetchReferentielDependencies,
  fetchReferentielsOverview,
  fetchReferentielsSnapshot,
  referentialErrorMessage,
  updateReferentialEntry,
} from '../../api/referentiels'
import {
  HEALTH_CHECKS,
  RESOURCE_CONFIG,
  RESOURCE_ENDPOINTS,
} from './referentielsConfig'

const EMPTY_SNAPSHOT = {
  institutions: [],
  academic_years: [],
  semesters: [],
  departments: [],
  programs: [],
  promotions: [],
  specializations: [],
  teaching_units: [],
  courses: [],
}

const STATUS_LABELS = {
  is_active: { on: 'Actif', off: 'Inactif' },
  is_current: { on: 'Courant', off: 'Non courant' },
}

export default function AdminReferentiels() {
  const { showToast } = useToast()

  const [family, setFamily] = useState('calendar')
  const [resourceKey, setResourceKey] = useState('academicYear')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [ordering, setOrdering] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const [users, setUsers] = useState([])
  const [form, setForm] = useState(null)
  const [editingItem, setEditingItem] = useState(null)
  const [saving, setSaving] = useState(false)
  const [deleteState, setDeleteState] = useState(null)

  const config = RESOURCE_CONFIG[resourceKey]
  const endpoint = RESOURCE_ENDPOINTS[resourceKey]

  const snapshotQuery = useFetch(() => fetchReferentielsSnapshot(), [])
  const overviewQuery = useFetch(() => fetchReferentielsOverview(), [])

  const snapshot = snapshotQuery.data || EMPTY_SNAPSHOT
  const overview = overviewQuery.data
  const resourceMeta = useMemo(
    () => overview?.resources?.find((item) => item.key === resourceKey),
    [overview, resourceKey],
  )
  const statusField = resourceMeta?.status_field || null
  const readOnly = resourceMeta ? !resourceMeta.manageable : resourceKey === 'jobNomenclature'

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const listQuery = useFetch(
    () => fetchReferentialPage(endpoint, {
      search: search || undefined,
      ordering: ordering || config.defaultOrdering || undefined,
      page,
      page_size: pageSize,
      ...(statusField && statusFilter ? { [statusField]: statusFilter } : {}),
    }),
    [endpoint, search, ordering, page, pageSize, statusField, statusFilter],
  )

  const rows = listQuery.data?.results || []
  const total = listQuery.data?.count || 0

  const lookups = useMemo(() => ({
    institutions: new Map(snapshot.institutions.map((item) => [item.id, item])),
    departments: new Map(snapshot.departments.map((item) => [item.id, item])),
    programs: new Map(snapshot.programs.map((item) => [item.id, item])),
    years: new Map(snapshot.academic_years.map((item) => [item.id, item])),
    specializations: new Map(snapshot.specializations.map((item) => [item.id, item])),
    teachingUnits: new Map(snapshot.teaching_units.map((item) => [item.id, item])),
  }), [snapshot])

  const alerts = useMemo(() => {
    const health = overview?.health
    if (!health) return []
    return HEALTH_CHECKS
      .map((check) => {
        const value = health[check.key]
        if (!value) return null
        return {
          ...check,
          text: check.countable ? `${value} ${check.message}` : check.message,
        }
      })
      .filter(Boolean)
  }, [overview])

  const selectResource = (key) => {
    setResourceKey(key)
    setSearchInput('')
    setSearch('')
    setStatusFilter('')
    setOrdering('')
    setPage(1)
  }

  const selectFamily = (key) => {
    setFamily(key)
    const first = overview?.families?.find((item) => item.key === key)?.resources?.[0]
    if (first) selectResource(first.key)
  }

  const refreshAll = async () => {
    await Promise.all([snapshotQuery.reload(), overviewQuery.reload(), listQuery.reload()])
  }

  const toggleSort = (sortKey) => {
    if (!sortKey) return
    setOrdering((current) => (current === sortKey ? `-${sortKey}` : sortKey))
    setPage(1)
  }

  const ensureUsers = async () => {
    if (!config.needsUsers || users.length) return
    try {
      const data = await fetchUsers({ page_size: 200 })
      setUsers(data?.results || [])
    } catch {
      showToast('Liste des responsables indisponible', 'warning')
    }
  }

  const openCreate = async () => {
    await ensureUsers()
    setEditingItem(null)
    setForm({ ...config.emptyForm, ...(config.prefill ? config.prefill(snapshot) : {}) })
  }

  const openEdit = async (item) => {
    await ensureUsers()
    setEditingItem(item)
    setForm(config.toForm(item))
  }

  const closeForm = () => {
    setForm(null)
    setEditingItem(null)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = config.toPayload(form)
      if (editingItem) await updateReferentialEntry(endpoint, editingItem.id, payload)
      else await createReferentialEntry(endpoint, payload)
      showToast(editingItem ? `${config.singular} mis à jour` : `${config.singular} créé`, 'success')
      closeForm()
      await refreshAll()
    } catch (err) {
      showToast(referentialErrorMessage(err, 'Enregistrement impossible'), 'danger')
    } finally {
      setSaving(false)
    }
  }

  const toggleStatus = async (item) => {
    if (!statusField || readOnly) return
    try {
      await updateReferentialEntry(endpoint, item.id, { [statusField]: !item[statusField] })
      showToast('Statut mis à jour', 'success')
      await refreshAll()
    } catch (err) {
      showToast(referentialErrorMessage(err, 'Changement de statut impossible'), 'danger')
    }
  }

  const openDelete = async (item) => {
    setDeleteState({ item, loading: true, dependencies: null })
    try {
      const dependencies = await fetchReferentielDependencies(resourceKey, item.id)
      setDeleteState({ item, loading: false, dependencies })
    } catch (err) {
      setDeleteState(null)
      showToast(referentialErrorMessage(err, 'Analyse des dépendances impossible'), 'danger')
    }
  }

  const confirmDelete = async () => {
    if (!deleteState?.item) return
    setSaving(true)
    try {
      await deleteReferentialEntry(endpoint, deleteState.item.id)
      showToast(`${config.singular} supprimé`, 'success')
      setDeleteState(null)
      await refreshAll()
    } catch (err) {
      showToast(referentialErrorMessage(err, 'Suppression impossible'), 'danger')
    } finally {
      setSaving(false)
    }
  }

  const exportHeaders = config.columns.map((column) => column.label)
  const exportRows = rows.map((row) => config.columns.map((column) => {
    const value = column.render ? column.render(row, lookups) : row[column.key]
    return value ?? '—'
  }))

  const families = overview?.families || []
  const familyResources = families.find((item) => item.key === family)?.resources || []

  return (
    <>
      <PageHeader
        title="Référentiels"
        subtitle="Catalogue académique LMD : calendrier, structure, maquette et nomenclatures"
        action={(
          <div className="d-flex gap-2 flex-wrap">
            <ExportButtons
              title={`Référentiels — ${config.singular}`}
              filename={`referentiels_${resourceKey}`}
              headers={exportHeaders}
              rows={exportRows}
            />
            <button type="button" className="btn btn-outline-primary" onClick={refreshAll}>Actualiser</button>
            {!readOnly && (
              <button type="button" className="btn btn-injs-primary" onClick={openCreate}>+ Ajouter</button>
            )}
          </div>
        )}
      />

      <div className="row g-2 mb-3">
        <div className="col-md-3">
          <StatCard compact icon={FiDatabase} label="Entrées référentielles" value={overview?.totals?.entries ?? '—'} color="blue" />
        </div>
        <div className="col-md-3">
          <StatCard compact icon={FiLayers} label="Tables gérées" value={overview?.totals?.manageable ?? '—'} color="green" />
        </div>
        <div className="col-md-3">
          <StatCard compact icon={FiCalendar} label="Année courante" value={overview?.health?.current_academic_year || 'Non définie'} color="orange" />
        </div>
        <div className="col-md-3">
          <StatCard compact icon={FiAlertTriangle} label="Points de vigilance" value={alerts.length} />
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="card-injs p-3 mb-4">
          <h6 className="fw-bold mb-2">Cohérence du référentiel</h6>
          <ul className="list-unstyled mb-0 d-grid gap-2">
            {alerts.map((alert) => (
              <li key={alert.key} className="d-flex align-items-center gap-2 flex-wrap">
                <span className={`badge bg-${alert.level}-subtle text-${alert.level === 'info' ? 'primary' : alert.level === 'warning' ? 'warning-emphasis' : 'danger'}`}>
                  {alert.level === 'danger' ? 'Bloquant' : alert.level === 'warning' ? 'À corriger' : 'Info'}
                </span>
                <span className="small">{alert.text}</span>
                {alert.resource && RESOURCE_CONFIG[alert.resource] && (
                  <button
                    type="button"
                    className="btn btn-link btn-sm p-0"
                    onClick={() => {
                      const target = families.find((item) => item.resources.some((r) => r.key === alert.resource))
                      if (target) setFamily(target.key)
                      selectResource(alert.resource)
                    }}
                  >
                    Ouvrir {RESOURCE_CONFIG[alert.resource].singular}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card-injs p-3 mb-3">
        <div className="d-flex flex-nowrap align-items-center justify-content-center gap-1 overflow-auto">
          {families.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`btn btn-sm py-1 px-2 text-nowrap ${family === item.key ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => selectFamily(item.key)}
            >
              {item.label}
              <span className="badge bg-light text-dark ms-1">
                {item.resources.reduce((sum, resource) => sum + resource.count, 0)}
              </span>
            </button>
          ))}
          <span className="border-start mx-1 align-self-stretch" aria-hidden="true" />
          {familyResources.map((resource) => (
            <button
              key={resource.key}
              type="button"
              className={`btn btn-sm py-1 px-2 text-nowrap ${resourceKey === resource.key ? 'btn-dark' : 'btn-outline-dark'}`}
              onClick={() => selectResource(resource.key)}
            >
              {resource.label}
              <span className="badge bg-light text-dark ms-1">{resource.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="card-injs p-3 mb-3">
        <div className="row g-3 align-items-end">
          <div className="col-md-6">
            <label className="form-label">Recherche</label>
            <input
              className="form-control"
              placeholder={config.searchPlaceholder}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>
          {statusField && (
            <div className="col-md-3">
              <label className="form-label">Statut</label>
              <select
                className="form-select"
                value={statusFilter}
                onChange={(event) => { setStatusFilter(event.target.value); setPage(1) }}
              >
                <option value="">Tous</option>
                <option value="true">{STATUS_LABELS[statusField]?.on || 'Actif'}</option>
                <option value="false">{STATUS_LABELS[statusField]?.off || 'Inactif'}</option>
              </select>
            </div>
          )}
          <div className="col-md-3">
            <div className="text-muted small">
              {total} entrée{total > 1 ? 's' : ''} · {config.singular}
              {readOnly && <span className="badge bg-secondary-subtle text-secondary ms-2">Lecture seule</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="card-injs overflow-hidden">
        {listQuery.loading ? (
          <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
        ) : listQuery.error ? (
          <div className="p-4 text-danger">{listQuery.error}</div>
        ) : !rows.length ? (
          <div className="p-4 text-muted">
            Aucune entrée pour ce périmètre.
            {!readOnly && ' Utilisez « + Ajouter » pour créer la première.'}
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  {config.columns.map((column) => (
                    <th
                      key={column.key}
                      role={column.sortKey ? 'button' : undefined}
                      onClick={() => toggleSort(column.sortKey)}
                    >
                      {column.label}
                      {column.sortKey && ordering === column.sortKey && ' ▲'}
                      {column.sortKey && ordering === `-${column.sortKey}` && ' ▼'}
                    </th>
                  ))}
                  {statusField && <th style={{ width: 130 }}>Statut</th>}
                  <th style={{ width: 110 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    {config.columns.map((column) => (
                      <td key={column.key}>
                        {column.render ? column.render(row, lookups) : (row[column.key] ?? '—')}
                      </td>
                    ))}
                    {statusField && (
                      <td>
                        <button
                          type="button"
                          className={`badge border-0 ${row[statusField] ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'}`}
                          disabled={readOnly}
                          title={readOnly ? 'Lecture seule' : 'Changer le statut'}
                          onClick={() => toggleStatus(row)}
                        >
                          {row[statusField]
                            ? (STATUS_LABELS[statusField]?.on || 'Actif')
                            : (STATUS_LABELS[statusField]?.off || 'Inactif')}
                        </button>
                      </td>
                    )}
                    <td>
                      {readOnly ? (
                        <span className="text-muted small">—</span>
                      ) : (
                        <IconActionButtons
                          actions={[
                            { type: 'edit', title: 'Modifier', onClick: () => openEdit(row) },
                            { type: 'delete', title: 'Supprimer', onClick: () => openDelete(row) },
                          ]}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="p-3">
          <PaginationBar
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
            onPageSizeChange={(size) => { setPageSize(size); setPage(1) }}
            disabled={listQuery.loading}
          />
        </div>
      </div>

      <Modal
        show={!!form}
        onClose={closeForm}
        title={`${editingItem ? 'Modifier' : 'Ajouter'} — ${config.singular}`}
        size="lg"
        footer={(
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={closeForm}>Annuler</button>
            <button type="submit" form="referential-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </>
        )}
      >
        {form && (
          <form id="referential-form" className="row g-3" onSubmit={handleSubmit}>
            {config.fields.map((field) => (
              <FormField
                key={field.name}
                field={field}
                value={form[field.name]}
                onChange={(value) => setForm((prev) => ({ ...prev, [field.name]: value }))}
                snapshot={snapshot}
                context={{ users }}
              />
            ))}
          </form>
        )}
      </Modal>

      <DeleteModal
        state={deleteState}
        singular={config.singular}
        softDeleted={resourceMeta?.soft_deleted}
        saving={saving}
        onClose={() => setDeleteState(null)}
        onConfirm={confirmDelete}
      />
    </>
  )
}

function DeleteModal({ state, singular, softDeleted, saving, onClose, onConfirm }) {
  const dependencies = state?.dependencies
  const blocked = !!dependencies?.blocking?.length

  return (
    <Modal
      show={!!state}
      onClose={onClose}
      title={`Supprimer — ${singular}`}
      footer={(
        <>
          <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Annuler</button>
          <button
            type="button"
            className="btn btn-danger"
            disabled={saving || blocked || state?.loading}
            onClick={onConfirm}
          >
            {saving ? 'Suppression…' : 'Confirmer'}
          </button>
        </>
      )}
    >
      {state?.loading ? (
        <div className="text-center py-3"><div className="spinner-border text-primary" /></div>
      ) : (
        <>
          <p>
            Supprimer <strong>{dependencies?.object_repr || state?.item?.name || state?.item?.code}</strong> ?
          </p>

          {blocked && (
            <div className="alert alert-danger">
              <div className="fw-bold mb-2">Suppression bloquée : cette entrée est utilisée.</div>
              <ul className="mb-2">
                {dependencies.blocking.map((item) => (
                  <li key={item.accessor}>{item.count} {item.label}</li>
                ))}
              </ul>
              <div className="small mb-0">
                Désactivez l’entrée ou traitez d’abord les données liées.
              </div>
            </div>
          )}

          {!blocked && !!dependencies?.warnings?.length && (
            <div className="alert alert-warning">
              <div className="fw-bold mb-2">Éléments impactés :</div>
              <ul className="mb-0">
                {dependencies.warnings.map((item) => (
                  <li key={item.accessor}>
                    {item.count} {item.label} — {item.on_delete === 'CASCADE' ? 'seront supprimés' : 'seront détachés'}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!blocked && (
            <p className="text-muted small mb-0">
              {softDeleted
                ? 'L’entrée sera archivée (suppression logique) et retirée des listes.'
                : 'Cette action est définitive.'}
            </p>
          )}
        </>
      )}
    </Modal>
  )
}

function FormField({ field, value, onChange, snapshot, context }) {
  const columnClass = field.full ? 'col-12' : 'col-md-6'
  const label = `${field.label}${field.required ? ' *' : ''}`

  if (field.type === 'check') {
    return (
      <div className={`${columnClass} d-flex align-items-end`}>
        <div className="form-check">
          <input
            className="form-check-input"
            type="checkbox"
            id={`field-${field.name}`}
            checked={!!value}
            onChange={(event) => onChange(event.target.checked)}
          />
          <label className="form-check-label" htmlFor={`field-${field.name}`}>{field.label}</label>
          {field.hint && <div className="form-text">{field.hint}</div>}
        </div>
      </div>
    )
  }

  if (field.type === 'select') {
    const options = field.options ? field.options(snapshot, context) : []
    return (
      <div className={columnClass}>
        <label className="form-label" htmlFor={`field-${field.name}`}>{label}</label>
        <select
          id={`field-${field.name}`}
          className="form-select"
          required={field.required}
          value={value ?? ''}
          onChange={(event) => onChange(event.target.value)}
        >
          {field.allowEmpty !== false && <option value="">{field.emptyLabel || '—'}</option>}
          {options.map((option) => (
            <option key={`${field.name}-${option.value}`} value={option.value}>{option.label}</option>
          ))}
        </select>
        {field.hint && <div className="form-text">{field.hint}</div>}
      </div>
    )
  }

  if (field.type === 'textarea') {
    return (
      <div className="col-12">
        <label className="form-label" htmlFor={`field-${field.name}`}>{label}</label>
        <textarea
          id={`field-${field.name}`}
          className="form-control"
          rows={3}
          value={value ?? ''}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
    )
  }

  return (
    <div className={columnClass}>
      <label className="form-label" htmlFor={`field-${field.name}`}>{label}</label>
      <input
        id={`field-${field.name}`}
        className="form-control"
        type={field.type}
        required={field.required}
        min={field.min}
        max={field.max}
        step={field.step}
        placeholder={field.placeholder || ''}
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
      />
      {field.hint && <div className="form-text">{field.hint}</div>}
    </div>
  )
}
