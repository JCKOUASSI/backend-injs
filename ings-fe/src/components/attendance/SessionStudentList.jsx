import { useMemo, useState } from 'react'
import { FiCheckCircle, FiSearch, FiUserX, FiUsers } from 'react-icons/fi'
import ExportButtons from '../common/ExportButtons'

function initials(name = '') {
  const parts = String(name).trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

function statusMeta(a) {
  const isPresent = a.status && a.status !== 'absent'
  const isLate = a.status === 'late'
  if (isLate) {
    return {
      key: 'late',
      isPresent: true,
      label: 'En retard',
      rowClass: 'ssl-row--late',
      pillClass: 'ssl-pill--late',
    }
  }
  if (isPresent) {
    const label = a.status_label || (a.gender === 'F' ? 'Présente' : 'Présent')
    return {
      key: 'present',
      isPresent: true,
      label,
      rowClass: 'ssl-row--present',
      pillClass: 'ssl-pill--present',
    }
  }
  const label = a.status_label || (a.gender === 'F' ? 'Absente' : 'Absent')
  return {
    key: 'absent',
    isPresent: false,
    label,
    rowClass: 'ssl-row--absent',
    pillClass: 'ssl-pill--absent',
  }
}

/**
 * Liste des étudiants affectés à une séance.
 * Présent/Présente (vert) · Absent/Absente (rouge) · forçage admin optionnel.
 */
export default function SessionStudentList({
  roster,
  loading = false,
  allowForce = false,
  forceMotif = '',
  onForceMotifChange,
  forceIds = [],
  onForceIdsChange,
  onForceBadge,
  forcing = false,
  onRemove,
  allowMark = false,
  onMarkStudent,
  markingId = null,
  onBackToQr,
  sessionLabel = '',
  exportFilename = 'liste_etudiants_seance',
}) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all') // all | present | absent

  const assigned = roster?.assigned || []

  const counts = useMemo(() => {
    let present = 0
    let absent = 0
    let late = 0
    for (const a of assigned) {
      if (a.status === 'late') late += 1
      else if (a.status && a.status !== 'absent') present += 1
      else absent += 1
    }
    const total = assigned.length
    const rate = total ? Math.round((100 * (present + late)) / total) : 0
    return { present, absent, late, total, rate }
  }, [assigned])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return assigned
      .filter((a) => {
        const meta = statusMeta(a)
        if (filter === 'present' && !meta.isPresent) return false
        if (filter === 'absent' && meta.isPresent) return false
        if (!q) return true
        return (
          String(a.name || '').toLowerCase().includes(q)
          || String(a.matricule || '').toLowerCase().includes(q)
        )
      })
      .sort((a, b) => {
        // Absents d'abord pour faciliter le forçage / le contrôle salle
        const ap = statusMeta(a).isPresent ? 1 : 0
        const bp = statusMeta(b).isPresent ? 1 : 0
        if (ap !== bp) return ap - bp
        return String(a.name || '').localeCompare(String(b.name || ''), 'fr')
      })
  }, [assigned, filter, query])

  const toggleForce = (studentId, checked) => {
    if (!onForceIdsChange) return
    onForceIdsChange(
      checked
        ? [...forceIds, studentId]
        : forceIds.filter((id) => id !== studentId),
    )
  }

  const selectAllAbsents = () => {
    if (!onForceIdsChange) return
    const ids = assigned
      .filter((a) => !statusMeta(a).isPresent)
      .map((a) => a.student_id)
    onForceIdsChange(ids)
  }

  const exportHeaders = ['Matricule', 'Nom', 'Genre', 'Statut']
  const exportRows = useMemo(
    () => filtered.map((a) => {
      const meta = statusMeta(a)
      return [
        a.matricule || '',
        a.name || '',
        a.gender === 'F' ? 'F' : a.gender === 'M' ? 'H' : '—',
        a.status === 'late' ? 'En retard' : meta.label,
      ]
    }),
    [filtered],
  )

  const exportTitle = [
    'Liste des étudiants — présence INJS',
    sessionLabel,
    roster?.promotion,
    roster?.date,
  ].filter(Boolean).join(' · ')

  if (loading) {
    return <div className="text-center py-4"><div className="spinner-border text-primary" /></div>
  }

  if (!roster) {
    return <p className="text-muted mb-0">Aucune liste disponible.</p>
  }

  return (
    <div className="session-student-list">
      <div className="ssl-header">
        <div>
          <div className="ssl-kicker">{roster.promotion || 'Promotion'}</div>
          <h6 className="ssl-title mb-0">Liste des étudiants</h6>
        </div>
        <div className="d-flex flex-wrap align-items-center gap-2">
          <ExportButtons
            title={exportTitle}
            filename={exportFilename}
            headers={exportHeaders}
            rows={exportRows}
            size="sm"
          />
          {onBackToQr && (
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={onBackToQr}>
              Retour au QR
            </button>
          )}
        </div>
      </div>

      <div className="ssl-stats">
        <div className="ssl-stat">
          <FiUsers className="ssl-stat-icon" aria-hidden />
          <div>
            <div className="ssl-stat-value">{counts.total}</div>
            <div className="ssl-stat-label">Affectés</div>
          </div>
        </div>
        <div className="ssl-stat ssl-stat--present">
          <FiCheckCircle className="ssl-stat-icon" aria-hidden />
          <div>
            <div className="ssl-stat-value">{counts.present + counts.late}</div>
            <div className="ssl-stat-label">Présent(e)s</div>
          </div>
        </div>
        <div className="ssl-stat ssl-stat--absent">
          <FiUserX className="ssl-stat-icon" aria-hidden />
          <div>
            <div className="ssl-stat-value">{counts.absent}</div>
            <div className="ssl-stat-label">Absent(e)s</div>
          </div>
        </div>
        <div className="ssl-stat ssl-stat--rate">
          <div className="ssl-stat-value">{counts.rate}%</div>
          <div className="ssl-stat-label">Taux</div>
          <div className="ssl-rate-bar" aria-hidden>
            <span style={{ width: `${counts.rate}%` }} />
          </div>
        </div>
      </div>

      <div className="ssl-toolbar">
        <div className="ssl-search">
          <FiSearch aria-hidden />
          <input
            type="search"
            className="form-control form-control-sm"
            placeholder="Rechercher nom ou matricule…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="ssl-filters" role="group" aria-label="Filtrer par statut">
          {[
            { id: 'all', label: 'Tous', count: counts.total },
            { id: 'present', label: 'Présents', count: counts.present + counts.late },
            { id: 'absent', label: 'Absents', count: counts.absent },
          ].map((f) => (
            <button
              key={f.id}
              type="button"
              className={`ssl-filter ${filter === f.id ? 'is-active' : ''} ${f.id !== 'all' ? `ssl-filter--${f.id}` : ''}`}
              onClick={() => setFilter(f.id)}
            >
              {f.label} <span>{f.count}</span>
            </button>
          ))}
        </div>
      </div>

      {allowForce && (
        <div className="ssl-force">
          <div className="ssl-force-top">
            <div>
              <div className="fw-semibold small mb-1">Forçage administratif</div>
              <p className="small text-muted mb-0">
                Cochez les absents (ou « Tous les absents »), indiquez un motif, puis validez.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={selectAllAbsents}
              disabled={!counts.absent}
            >
              Tous les absents
            </button>
          </div>
          <div className="ssl-force-row">
            <input
              className="form-control form-control-sm"
              placeholder="Motif obligatoire (oubli téléphone, QR illisible…)"
              value={forceMotif}
              onChange={(e) => onForceMotifChange?.(e.target.value)}
            />
            <button
              type="button"
              className="btn btn-warning btn-sm text-nowrap"
              disabled={!forceIds.length || forcing}
              onClick={onForceBadge}
            >
              {forcing ? 'Forçage…' : `Forcer (${forceIds.length})`}
            </button>
          </div>
        </div>
      )}

      {!assigned.length && (
        <div className="alert alert-info mb-0 mt-3">
          Aucun étudiant affecté. Utilisez l&apos;auto-affectation de la promotion.
        </div>
      )}

      {!!assigned.length && !filtered.length && (
        <div className="ssl-empty">Aucun résultat pour ce filtre.</div>
      )}

      <ul className="ssl-list">
        {filtered.map((a) => {
          const meta = statusMeta(a)
          const checked = forceIds.includes(a.student_id)
          return (
            <li key={a.attendance_id} className={`ssl-row ${meta.rowClass}${checked ? ' is-selected' : ''}`}>
              <div className="ssl-row-main">
                {allowForce && !meta.isPresent && (
                  <label className="ssl-check">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => toggleForce(a.student_id, e.target.checked)}
                      aria-label={`Forcer ${a.name}`}
                    />
                  </label>
                )}
                <div className={`ssl-avatar ${a.gender === 'F' ? 'ssl-avatar--f' : 'ssl-avatar--m'}`}>
                  {initials(a.name)}
                </div>
                <div className="ssl-identity">
                  <div className="ssl-name">{a.name}</div>
                  <div className="ssl-meta">
                    <code>{a.matricule}</code>
                    {a.gender === 'F' ? ' · F' : a.gender === 'M' ? ' · H' : ''}
                  </div>
                </div>
              </div>
              <div className="ssl-row-actions">
                <span className={`ssl-pill ${meta.pillClass}`}>{meta.label}</span>
                {allowMark && onMarkStudent && (
                  <div className="btn-group btn-group-sm">
                    <button
                      type="button"
                      className="btn btn-outline-success"
                      disabled={markingId === a.student_id || a.status === 'present'}
                      onClick={() => onMarkStudent(a.student_id, 'present')}
                    >
                      Présent
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-danger"
                      disabled={markingId === a.student_id || a.status === 'absent'}
                      onClick={() => onMarkStudent(a.student_id, 'absent')}
                    >
                      Absent
                    </button>
                  </div>
                )}
                {onRemove && (
                  <button
                    type="button"
                    className="btn btn-link btn-sm text-danger p-0 ssl-remove"
                    onClick={() => onRemove(a.student_id)}
                  >
                    Retirer
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
