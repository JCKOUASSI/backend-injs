/** Grille d'emploi du temps : une colonne par jour, séances empilées. */
import { EtatVide } from './Badges'

function formaterDate(iso) {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}

export default function PlanningGrid({ jours = [], onSelect, afficherPresences = false, message }) {
  if (!jours.length) {
    return <EtatVide message={message || 'Aucune séance sur ce périmètre.'} />
  }

  return (
    <div className="ept-grid">
      {jours.map((jour) => (
        <div className="ept-day" key={jour.date}>
          <div className="ept-day-header">
            <span>{jour.day_display || jour.seances[0]?.day_display}</span>
            <span className="ept-day-date">{formaterDate(jour.date)}</span>
          </div>
          <div className="ept-day-body">
            {jour.seances.map((seance) => (
              <div
                key={seance.id}
                className={`ept-block ept-block-${seance.session_kind} is-${seance.statut}`}
                onClick={() => onSelect?.(seance)}
                onKeyDown={(event) => event.key === 'Enter' && onSelect?.(seance)}
                role="button"
                tabIndex={0}
              >
                <div className="ept-block-time">
                  {seance.heure_debut}–{seance.heure_fin}
                </div>
                <div className="ept-block-title">
                  <code className="me-1">{seance.course_code}</code>
                  {seance.course_name}
                </div>
                <div className="ept-block-meta">
                  {seance.promotion_name}
                  {seance.groupe_code && ` · ${seance.groupe_code}`}
                  <br />
                  {seance.session_kind_display}
                  {seance.room_code && ` · ${seance.room_code}`}
                  {seance.teacher_name && (
                    <>
                      <br />
                      {seance.teacher_name}
                    </>
                  )}
                  {afficherPresences && seance.attendus_count > 0 && (
                    <>
                      <br />
                      <strong>{seance.presents_count}</strong> / {seance.attendus_count} présents
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
