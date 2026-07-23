export default function StatCard({ icon: Icon, label, value, change, color = 'green' }) {
  return (
    <div className="card-injs p-4 h-100">
      <div className="d-flex justify-content-between align-items-start">
        <div>
          <p className="text-muted mb-1 small text-uppercase fw-semibold">{label}</p>
          <h3 className="mb-1 fw-bold">{value}</h3>
          {change && (
            <small className={change.startsWith('+') ? 'text-success' : 'text-danger'}>
              {change} vs année précédente
            </small>
          )}
        </div>
        <div className={`stat-icon ${color}`}>
          <Icon />
        </div>
      </div>
    </div>
  )
}
