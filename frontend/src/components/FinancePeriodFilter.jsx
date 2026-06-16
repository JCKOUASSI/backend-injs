import {
  FINANCE_PERIOD_PRESETS,
  TRIMESTRE_OPTIONS,
  trimestreKeyFromParts,
  currentTrimestreParts,
} from '../utils/financePeriod'

export default function FinancePeriodFilter({
  period,
  onChange,
  onApply,
  applying,
  embedded,
  autoApplyOnSelect = false,
}) {
  const set = (patch) => onChange({ ...period, ...patch })

  const maybeApply = () => {
    if (autoApplyOnSelect && onApply) onApply()
  }

  const handlePresetChange = (preset) => {
    const now = new Date()
    const patch = { preset }
    if (preset === 'mois') {
      patch.mois = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    }
    if (preset === 'annee') {
      patch.annee = String(now.getFullYear())
    }
    if (preset === 'trimestre') {
      const { annee, q } = currentTrimestreParts(now)
      patch.trimestreAnnee = annee
      patch.trimestreQ = q
      patch.trimestre = trimestreKeyFromParts(annee, q)
    }
    onChange({ ...period, ...patch })
    maybeApply()
  }

  const content = (
    <>
      <div className="finance-preset-pills">
        {FINANCE_PERIOD_PRESETS.map((pr) => (
          <button
            key={pr.id}
            type="button"
            className={`finance-preset-pill${period.preset === pr.id ? ' active' : ''}`}
            onClick={() => handlePresetChange(pr.id)}
          >
            {pr.label}
          </button>
        ))}
      </div>
      <div className="finance-filter-fields">
        {period.preset === 'mois' && (
          <div className="finance-filter-field">
            <label>Mois</label>
            <input
              type="month"
              className="form-control form-control-sm"
              value={period.mois || ''}
              onChange={(e) => set({ mois: e.target.value })}
            />
          </div>
        )}
        {period.preset === 'trimestre' && (
          <>
            <div className="finance-filter-field">
              <label>Année</label>
              <input
                type="number"
                className="form-control form-control-sm"
                min="2020"
                max="2100"
                value={period.trimestreAnnee || ''}
                onChange={(e) => {
                  const y = e.target.value
                  const q = period.trimestreQ || 1
                  set({
                    trimestreAnnee: y,
                    trimestre: trimestreKeyFromParts(y, q),
                  })
                }}
                style={{ width: '90px' }}
              />
            </div>
            <div className="finance-filter-field">
              <label>Trimestre</label>
              <div className="finance-trimestre-pills">
                {TRIMESTRE_OPTIONS.map(({ q, label }) => (
                  <button
                    key={q}
                    type="button"
                    className={`finance-trimestre-pill${Number(period.trimestreQ) === q ? ' active' : ''}`}
                    onClick={() => {
                      const y = period.trimestreAnnee || String(new Date().getFullYear())
                      set({
                        trimestreQ: q,
                        trimestreAnnee: y,
                        trimestre: trimestreKeyFromParts(y, q),
                      })
                      maybeApply()
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
        {period.preset === 'annee' && (
          <div className="finance-filter-field">
            <label>Année</label>
            <input
              type="number"
              className="form-control form-control-sm"
              min="2020"
              max="2100"
              value={period.annee || ''}
              onChange={(e) => set({ annee: e.target.value })}
              style={{ width: '100px' }}
            />
          </div>
        )}
        {period.preset === 'custom' && (
          <>
            <div className="finance-filter-field">
              <label>Du</label>
              <input
                type="date"
                className="form-control form-control-sm"
                value={period.dateDebut || ''}
                onChange={(e) => set({ dateDebut: e.target.value })}
              />
            </div>
            <div className="finance-filter-field">
              <label>Au</label>
              <input
                type="date"
                className="form-control form-control-sm"
                value={period.dateFin || ''}
                onChange={(e) => set({ dateFin: e.target.value })}
              />
            </div>
          </>
        )}

        <button
          type="button"
          className="btn btn-dfrc btn-sm"
          onClick={onApply}
          disabled={applying || (period.preset === 'custom' && (!period.dateDebut || !period.dateFin))}
          style={{ marginBottom: '1px' }}
        >
          {applying ? (
            <>
              <span className="spinner-border spinner-border-sm me-1" role="status"></span>
              Chargement…
            </>
          ) : (
            <>
              <i className="bi bi-funnel me-1"></i>Appliquer
            </>
          )}
        </button>
      </div>
    </>
  )

  if (embedded) return content

  return (
    <div className="finance-filter-panel-inner">
      {content}
    </div>
  )
}
