export default function UpcomingSeances({ seances, emptyText = 'Aucune séance publiée à venir.' }) {
  const rows = seances || []
  if (!rows.length) {
    return <div className="alert alert-info">{emptyText}</div>
  }
  return (
    <div className="card-injs mb-4">
      <div className="p-3 border-bottom fw-semibold">Prochaines séances</div>
      <div className="table-responsive">
        <table className="table table-hover mb-0">
          <thead>
            <tr>
              <th>Date</th>
              <th>Horaire</th>
              <th>Cours</th>
              <th>Salle</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((seance) => (
              <tr key={seance.id}>
                <td>
                  {new Date(`${seance.date}T12:00:00`).toLocaleDateString('fr-FR', {
                    weekday: 'short', day: '2-digit', month: 'short',
                  })}
                </td>
                <td>{(seance.start_time || '').slice(0, 5)} – {(seance.end_time || '').slice(0, 5)}</td>
                <td>
                  <strong>{seance.course_code}</strong>
                  <div className="small text-muted">{seance.course_name}</div>
                </td>
                <td>{seance.room_code || '—'}</td>
                <td>{seance.status_display || seance.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
