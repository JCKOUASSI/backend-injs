import { useMemo, useState } from 'react'
import { FiRefreshCw, FiUsers } from 'react-icons/fi'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import {
  fetchStudentGroups,
  fetchTeachingLoads,
  splitTeachingLoadsByGroups,
  updateTeachingLoad,
} from '../../../api/faculty'

const KIND_LABEL = { cm: 'CM', td: 'TD', tp: 'TP' }

export default function LoadsPanel({ filters }) {
  const { showToast } = useToast()
  const period = filters.period
  const promotion = filters.promotion
  const params = useMemo(() => ({
    period: period || undefined,
    promotion: promotion || undefined,
    is_active: true,
    page_size: 200,
  }), [period, promotion])
  const { data, loading, error, reload } = useFetch(() => fetchTeachingLoads(params), [params])
  const { data: groupsData } = useFetch(
    () => fetchStudentGroups({ promotion: promotion || undefined, page_size: 100 }),
    [promotion],
  )
  const loads = data?.results || []
  const groups = groupsData?.results || []
  const [saving, setSaving] = useState(false)

  const requireScope = () => {
    if (!period || !promotion) {
      showToast('Choisissez une période et une promotion dans la barre du haut.', 'warning')
      return false
    }
    return true
  }

  const saveHours = async (load, hours) => {
    const value = Number(hours)
    if (!value || value === load.hours_total) return
    setSaving(true)
    try {
      await updateTeachingLoad(load.id, { hours_total: value })
      showToast('Volume mis à jour', 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Modification impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const assignGroup = async (load, groupId) => {
    setSaving(true)
    try {
      await updateTeachingLoad(load.id, { group: groupId || null })
      showToast('Groupe mis à jour', 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Modification impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const split = async () => {
    if (!requireScope()) return
    setSaving(true)
    try {
      const result = await splitTeachingLoadsByGroups({ period, promotion })
      showToast(
        `${result.created} charge(s) créée(s) pour ${result.groups} groupe(s)`,
        result.created ? 'success' : 'info',
      )
      reload()
    } catch (err) {
      showToast(err.message || 'Répartition impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card-injs p-4">
      <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
        <div>
          <h2 className="h6 mb-1">Charges horaires à planifier</h2>
          <p className="small text-muted mb-0">
            Volumes CM / TD / TP de la période. Les TD et TP promotion-entière peuvent être
            répartis sur les groupes pédagogiques avant la génération.
          </p>
        </div>
        <div className="d-flex gap-2">
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={reload}>
            <FiRefreshCw className="me-1" /> Actualiser
          </button>
          <button type="button" className="btn btn-injs-primary btn-sm" disabled={saving} onClick={split}>
            <FiUsers className="me-1" /> Répartir TD/TP sur les groupes
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {!loading && loads.length === 0 && (
        <p className="text-muted mb-0">
          Aucune charge. Générez d’abord (option « créer les charges depuis la maquette ») ou créez une période / promotion.
        </p>
      )}
      {loads.length > 0 && (
        <div className="table-responsive">
          <table className="table align-middle mb-0">
            <thead>
              <tr>
                <th>ECUE</th>
                <th>Type</th>
                <th>Heures</th>
                <th>Groupe</th>
                <th>Professeur</th>
              </tr>
            </thead>
            <tbody>
              {loads.map((load) => (
                <tr key={load.id}>
                  <td>
                    <code className="me-1">{load.course_code}</code>
                    <span className="small">{load.course_name}</span>
                  </td>
                  <td><span className="badge bg-light text-dark">{KIND_LABEL[load.session_kind] || load.session_kind}</span></td>
                  <td style={{ width: 100 }}>
                    <input
                      type="number"
                      min={1}
                      className="form-control form-control-sm"
                      defaultValue={load.hours_total}
                      disabled={saving}
                      onBlur={(e) => saveHours(load, e.target.value)}
                    />
                  </td>
                  <td>
                    {load.session_kind === 'cm' ? (
                      <span className="small text-muted">Promotion entière</span>
                    ) : (
                      <select
                        className="form-select form-select-sm"
                        value={load.group || ''}
                        disabled={saving}
                        onChange={(e) => assignGroup(load, e.target.value)}
                      >
                        <option value="">Promotion entière</option>
                        {groups.map((group) => (
                          <option key={group.id} value={group.id}>{group.name}</option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td className="small">{load.teacher_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
