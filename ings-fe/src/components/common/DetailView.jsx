export default function DetailView({ data }) {
  if (!data) return null
  return (
    <dl className="detail-view">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="detail-row">
          <dt>{key}</dt>
          <dd>{value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  )
}
