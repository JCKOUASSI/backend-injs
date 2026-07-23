export default function PageHeader({ title, subtitle, action }) {
  return (
    <div className="d-flex flex-wrap justify-content-between align-items-start mb-4 gap-3">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle mb-0">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
