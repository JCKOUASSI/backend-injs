import { fmtDuration, formatMoney } from '../FinanceStatsGrid'

const DRILL_CONFIG = {
  planifie: {
    title: 'Volume horaire planifié par module',
    icon: 'bi-clock',
    valueKey: 'total_duree_minutes',
    format: 'duration',
    sortKey: 'total_duree_minutes',
  },
  realise: {
    title: 'Volume horaire réalisé par module',
    icon: 'bi-clock-history',
    valueKey: 'total_duree_realisee_minutes',
    format: 'duration',
    sortKey: 'total_duree_realisee_minutes',
  },
  taux: {
    title: 'Taux de réalisation par module',
    icon: 'bi-percent',
    valueKey: 'taux_realisation_pct',
    format: 'pct',
    sortKey: 'taux_realisation_pct',
  },
  cout: {
    title: 'Coût du volume horaire réalisé par module',
    icon: 'bi-cash-stack',
    valueKey: 'montant_realise',
    format: 'money',
    sortKey: 'montant_realise',
  },
}

function formatDetailValue(mod, cfg) {
  const v = mod[cfg.valueKey]
  if (cfg.format === 'duration') return fmtDuration(v)
  if (cfg.format === 'pct') return `${v ?? 0} %`
  if (cfg.format === 'money') return `${formatMoney(v ?? 0)} FCFA`
  return v ?? '—'
}

export default function FinanceModuleBreakdownModal({ drillType, modules, onClose }) {
  const cfg = DRILL_CONFIG[drillType]
  if (!cfg) return null

  const rows = [...(modules || [])].sort(
    (a, b) => Number(b[cfg.sortKey] || 0) - Number(a[cfg.sortKey] || 0),
  )

  return (
    <div className="modal-overlay finance-modal" onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '920px', width: '95%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h5 className="modal-title">
            <i className={`bi ${cfg.icon} me-2`}></i>
            {cfg.title}
          </h5>
          <button type="button" className="btn-close" aria-label="Fermer" onClick={onClose}></button>
        </div>
        <div className="modal-body" style={{ overflowY: 'auto', flex: 1, padding: '1rem 1.25rem' }}>
          {rows.length === 0 ? (
            <div className="finance-empty">
              <i className="bi bi-inbox"></i>
              Aucun module sur cette période
            </div>
          ) : (
            <>
              {drillType === 'cout' && (
                <p className="text-muted small mb-2">
                  <i className="bi bi-info-circle me-1"></i>
                  Chaque ligne est facturée au tarif horaire du cycle de formation associé au module.
                </p>
              )}
              <div className="finance-table-wrap">
              <table className="finance-table">
                <thead>
                  <tr>
                    <th>Module</th>
                    <th>Formation (cycle)</th>
                    <th>Grade</th>
                    <th>Groupe</th>
                    <th>Séances</th>
                    {drillType === 'cout' && <th style={{ textAlign: 'right' }}>Tarif / h</th>}
                    <th style={{ textAlign: 'right' }}>
                      {drillType === 'planifie' && 'Planifié'}
                      {drillType === 'realise' && 'Réalisé'}
                      {drillType === 'taux' && 'Taux'}
                      {drillType === 'cout' && 'Coût'}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((m) => (
                    <tr key={m.module_id}>
                      <td>
                        <strong>{m.module_intitule || '—'}</strong>
                        {m.secretariat_nom && (
                          <div className="text-muted small">{m.secretariat_nom}</div>
                        )}
                      </td>
                      <td className="small">{m.formation_intitule || '—'}</td>
                      <td className="small">{m.grade || '—'}</td>
                      <td className="small">{m.groupe || '—'}</td>
                      <td><span className="badge-bg-secondary">{m.sessions_count ?? 0}</span></td>
                      {drillType === 'cout' && (
                        <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                          {m.prix_heure_realisee != null
                            ? `${formatMoney(m.prix_heure_realisee)} F`
                            : '—'}
                        </td>
                      )}
                      <td style={{ textAlign: 'right', fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {formatDetailValue(m, cfg)}
                        {drillType === 'planifie' && (m.total_duree_heures ?? 0) > 0 && (
                          <div className="text-muted small fw-normal">
                            {Number(m.total_duree_heures).toFixed(2)} h
                          </div>
                        )}
                        {drillType === 'realise' && (m.total_duree_realisee_heures ?? 0) > 0 && (
                          <div className="text-muted small fw-normal">
                            {Number(m.total_duree_realisee_heures).toFixed(2)} h
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ background: 'var(--fin-light-orange, #fff3e0)' }}>
                    <td colSpan={drillType === 'cout' ? 6 : 5}><strong>TOTAL</strong></td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>
                      {drillType === 'planifie' && fmtDuration(rows.reduce((s, m) => s + Number(m.total_duree_minutes || 0), 0))}
                      {drillType === 'realise' && fmtDuration(rows.reduce((s, m) => s + Number(m.total_duree_realisee_minutes || 0), 0))}
                      {drillType === 'taux' && (() => {
                        const planned = rows.reduce((s, m) => s + Number(m.total_duree_minutes || 0), 0)
                        const realized = rows.reduce((s, m) => s + Number(m.total_duree_realisee_minutes || 0), 0)
                        const pct = planned > 0 ? Math.min(100, Math.round((realized / planned) * 1000) / 10) : 0
                        return `${pct} %`
                      })()}
                      {drillType === 'cout' && `${formatMoney(rows.reduce((s, m) => s + Number(m.montant_realise || 0), 0))} FCFA`}
                    </td>
                  </tr>
                </tfoot>
              </table>
              </div>
            </>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Fermer
          </button>
        </div>
      </div>
    </div>
  )
}
