import { useState } from 'react'
import { useFetch } from '../../hooks/useFetch'
import { fetchTeacherFullDetail } from '../../api/faculty'

const GRADE_LABELS = {
  assistant: 'Assistant',
  maitre_assistant: 'Maître-Assistant',
  maitre_conferences: 'Maître de Conférences',
  professeur: 'Professeur',
  vacataire: 'Vacataire',
}

const DAY_ORDER = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']

export default function TeacherDetailPanel({ teacherUuid }) {
  const [activeTab, setActiveTab] = useState('info')
  const { data, loading, error } = useFetch(
    () => (teacherUuid ? fetchTeacherFullDetail(teacherUuid) : Promise.resolve(null)),
    [teacherUuid],
  )

  if (loading) {
    return <div className="text-center py-4"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>
  }

  if (!data) return null

  const {
    teacher, user, assignments, schedules, schedulesByDay,
    courseMap, ueMap, promotionMap, yearMap,
  } = data

  const tabs = [
    { id: 'info', label: 'Informations' },
    { id: 'courses', label: `Cours assignés (${assignments.length})` },
    { id: 'schedule', label: `Emploi du temps (${schedules.length})` },
  ]

  const sortedDays = Object.keys(schedulesByDay).sort(
    (a, b) => DAY_ORDER.indexOf(a) - DAY_ORDER.indexOf(b),
  )

  return (
    <div>
      <ul className="nav nav-tabs mb-3">
        {tabs.map((t) => (
          <li key={t.id} className="nav-item">
            <button
              type="button"
              className={`nav-link ${activeTab === t.id ? 'active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          </li>
        ))}
      </ul>

      {activeTab === 'info' && (
        <div className="row g-3">
          <div className="col-md-4 text-center">
            {teacher.photo_url ? (
              <img
                src={teacher.photo_url}
                alt={user.full_name}
                className="rounded-circle mb-3"
                style={{ width: 120, height: 120, objectFit: 'cover' }}
              />
            ) : (
              <div
                className="user-avatar mx-auto mb-3"
                style={{ width: 120, height: 120, fontSize: '2rem' }}
              >
                {(user.first_name?.[0] || '') + (user.last_name?.[0] || '')}
              </div>
            )}
          </div>
          <div className="col-md-4">
            <h6 className="fw-bold text-muted mb-2">Identité</h6>
            <dl className="detail-view">
              <div className="detail-row"><dt>ID employé</dt><dd><code>{teacher.employee_id}</code></dd></div>
              <div className="detail-row"><dt>Nom complet</dt><dd>{user.full_name}</dd></div>
              <div className="detail-row"><dt>Email</dt><dd>{user.email}</dd></div>
              <div className="detail-row"><dt>Téléphone</dt><dd>{user.phone || '—'}</dd></div>
            </dl>
          </div>
          <div className="col-md-4">
            <h6 className="fw-bold text-muted mb-2">Fonction</h6>
            <dl className="detail-view">
              <div className="detail-row"><dt>Grade</dt><dd>{GRADE_LABELS[teacher.grade] || teacher.grade}</dd></div>
              <div className="detail-row"><dt>Département</dt><dd>{teacher.department_name}</dd></div>
              <div className="detail-row"><dt>Spécialisation</dt><dd>{teacher.specialization || '—'}</dd></div>
              <div className="detail-row"><dt>Date d'embauche</dt><dd>{teacher.hire_date || '—'}</dd></div>
              <div className="detail-row">
                <dt>Statut</dt>
                <dd>
                  <span className={`grade-badge ${teacher.is_active ? 'grade-valid' : 'grade-pending'}`}>
                    {teacher.is_active ? 'Actif' : 'Inactif'}
                  </span>
                </dd>
              </div>
              {user.groups_detail?.length > 0 && (
                <div className="detail-row">
                  <dt>Groupe</dt>
                  <dd>{user.groups_detail.map((g) => g.name).join(', ')}</dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      )}

      {activeTab === 'courses' && (
        <div>
          {assignments.length === 0 ? (
            <p className="text-muted">Aucun cours assigné à cet enseignant.</p>
          ) : assignments.map((a) => {
            const course = courseMap[a.course]
            const ue = course ? ueMap[course.teaching_unit] : null
            const promo = promotionMap[a.promotion]
            const year = yearMap[a.academic_year]
            return (
              <div key={a.id} className="card-injs p-3 mb-2">
                <div className="d-flex justify-content-between align-items-start flex-wrap gap-2">
                  <div>
                    {course ? (
                      <>
                        <code>{course.code}</code> — <strong>{course.name}</strong>
                      </>
                    ) : (
                      <strong>{a.course_name}</strong>
                    )}
                    {a.is_primary && <span className="badge bg-success ms-2">Responsable</span>}
                  </div>
                  {ue && <span className="badge-injs">UE {ue.code}</span>}
                </div>
                <div className="small text-muted mt-2">
                  {ue && <span className="me-3">UE : {ue.name}</span>}
                  {promo && <span className="me-3">Promotion : {promo.name}</span>}
                  {year && <span>Année : {year.label || year.name}</span>}
                </div>
                {course && (
                  <p className="small text-muted mb-0 mt-1">
                    CM {course.hours_cm}h / TD {course.hours_td}h / TP {course.hours_tp}h
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}

      {activeTab === 'schedule' && (
        <div>
          {schedules.length === 0 ? (
            <p className="text-muted">Aucun créneau dans l'emploi du temps.</p>
          ) : (
            <div className="row g-3">
              {sortedDays.map((day) => (
                <div key={day} className="col-md-6">
                  <div className="card-injs p-3 h-100">
                    <h6 className="fw-bold text-success mb-3">{day}</h6>
                    {schedulesByDay[day]
                      .sort((a, b) => (a.start_time || '').localeCompare(b.start_time || ''))
                      .map((s) => (
                        <div key={s.id} className="mb-3 pb-2 border-bottom">
                          <div className="fw-semibold small">
                            {s.start_time?.slice(0, 5)} – {s.end_time?.slice(0, 5)}
                          </div>
                          <div>{s.course_name}</div>
                          <small className="text-muted">
                            {s.room_code ? `${s.room_code} — ` : ''}{s.room_name || 'Salle non définie'}
                          </small>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
