export default function StatCard({ icon: Icon, label, value, change, color = 'green', compact = false }) {
  return (
    <div className={`card-injs h-100 ${compact ? 'p-2' : 'p-4'}`}>
      <div className="d-flex justify-content-between align-items-center gap-2">
        <div className="min-w-0">
          <p className={`text-muted mb-0 text-uppercase fw-semibold ${compact ? 'small' : 'mb-1 small'}`} style={compact ? { fontSize: '0.65rem', lineHeight: 1.2 } : undefined}>
            {label}
          </p>
          <h3 className={`mb-0 fw-bold ${compact ? 'fs-5' : ''}`}>{value}</h3>
          {change && (
            <small className={change.startsWith('+') ? 'text-success' : 'text-danger'}>
              {change} vs année précédente
            </small>
          )}
        </div>
        <div className={`stat-icon ${color}${compact ? ' stat-icon-sm' : ''} flex-shrink-0`}>
          <Icon />
        </div>
      </div>
    </div>
  )
}
