import { useState } from 'react'
import { useFetch } from '../../hooks/useFetch'
import { fetchStudentFullDetail } from '../../api/students'
import { StatusBadge } from '../../utils/statusBadge'

const STATUS_LABELS = {
  active: 'Actif',
  suspended: 'Suspendu',
  graduated: 'Diplômé',
  withdrawn: 'Retiré',
  approved: 'Validée',
  pending: 'En attente',
  rejected: 'Rejetée',
}

const ENROLLMENT_TYPES = {
  administrative: 'Inscription administrative',
  pedagogical: 'Inscription pédagogique',
  pre_registration: 'Préinscription',
}

const GENDER_LABELS = { M: 'Masculin', F: 'Féminin' }

function StudentPhoto({ photoUrl, name, size = 112 }) {
  const initials = (name || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('') || '?'

  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={name || 'Photo étudiant'}
        className="student-photo"
        style={{ width: size, height: size }}
      />
    )
  }

  return (
    <div className="student-photo student-photo-placeholder" style={{ width: size, height: size }}>
      {initials}
    </div>
  )
}

export default function StudentDetailPanel({ studentUuid }) {
  const [activeTab, setActiveTab] = useState('info')
  const { data, loading, error } = useFetch(
    () => (studentUuid ? fetchStudentFullDetail(studentUuid) : Promise.resolve(null)),
    [studentUuid],
  )

  if (loading) {
    return <div className="text-center py-4"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>
  }

  if (!data) return null

  const { student, user, semestre, promotionDetail, specialization, enrollments, coursesBySemester, grades, card } = data
  const semestres = Object.keys(coursesBySemester).map(Number).sort((a, b) => a - b)
  const photoUrl = student.photo_url || user.photo_url || card?.photo_url || null
  const fullName = user.full_name || `${user.first_name || ''} ${user.last_name || ''}`.trim()

  const tabs = [
    { id: 'info', label: 'Informations' },
    { id: 'courses', label: `Cours (${data.programCourses.length} UE)` },
    { id: 'grades', label: `Notes (${grades.length})` },
    { id: 'enrollments', label: 'Inscriptions' },
  ]

  return (
    <div>
      <div className="student-fiche-header card-injs p-3 mb-3 d-flex flex-wrap align-items-center gap-3">
        <StudentPhoto photoUrl={photoUrl} name={fullName} />
        <div className="flex-grow-1">
          <h4 className="fw-bold mb-1">{fullName}</h4>
          <div className="d-flex flex-wrap gap-2 align-items-center mb-1">
            <code>{student.matricule}</code>
            <StatusBadge statut={STATUS_LABELS[student.status] || student.status} />
          </div>
          <p className="text-muted small mb-0">
            {student.program_name} — {student.promotion_name} — S{semestre}
            {specialization?.name ? ` — ${specialization.name}` : ' — Tronc commun'}
          </p>
          <p className="small mb-0">{user.email}</p>
        </div>
        {card?.qr_code_url && (
          <a href={card.qr_code_url} target="_blank" rel="noreferrer" className="text-center">
            <img src={card.qr_code_url} alt="QR étudiant" style={{ width: 72, height: 72, objectFit: 'contain' }} />
            <div className="small text-muted">QR carte</div>
          </a>
        )}
      </div>

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
          <div className="col-md-6">
            <h6 className="fw-bold text-muted mb-2">Identité</h6>
            <dl className="detail-view">
              <div className="detail-row"><dt>Matricule</dt><dd><code>{student.matricule}</code></dd></div>
              <div className="detail-row"><dt>Nom complet</dt><dd>{fullName}</dd></div>
              <div className="detail-row"><dt>Email</dt><dd>{user.email}</dd></div>
              <div className="detail-row"><dt>Téléphone</dt><dd>{user.phone || '—'}</dd></div>
              <div className="detail-row"><dt>Date de naissance</dt><dd>{student.date_of_birth || '—'}</dd></div>
              <div className="detail-row"><dt>Lieu de naissance</dt><dd>{student.place_of_birth || '—'}</dd></div>
              <div className="detail-row"><dt>Nationalité</dt><dd>{student.nationality || '—'}</dd></div>
              <div className="detail-row"><dt>Genre</dt><dd>{GENDER_LABELS[student.gender] || '—'}</dd></div>
            </dl>
          </div>
          <div className="col-md-6">
            <h6 className="fw-bold text-muted mb-2">Parcours académique</h6>
            <dl className="detail-view">
              <div className="detail-row"><dt>Programme</dt><dd>{student.program_name}</dd></div>
              <div className="detail-row"><dt>Promotion</dt><dd>{student.promotion_name}</dd></div>
              <div className="detail-row"><dt>Semestre courant</dt><dd>S{semestre}</dd></div>
              <div className="detail-row"><dt>Spécialité</dt><dd>{specialization?.name || 'Tronc commun'}</dd></div>
              <div className="detail-row"><dt>Statut</dt><dd><StatusBadge statut={STATUS_LABELS[student.status] || student.status} /></dd></div>
              <div className="detail-row"><dt>Date d&apos;inscription</dt><dd>{student.enrollment_date || '—'}</dd></div>
              <div className="detail-row"><dt>Année d&apos;entrée</dt><dd>{promotionDetail?.entry_year || '—'}</dd></div>
            </dl>
          </div>
          {(student.address || student.emergency_contact) && (
            <div className="col-12">
              <h6 className="fw-bold text-muted mb-2">Contact & urgence</h6>
              <dl className="detail-view">
                {student.address && <div className="detail-row"><dt>Adresse</dt><dd>{student.address}</dd></div>}
                {student.emergency_contact && (
                  <div className="detail-row">
                    <dt>Contact urgence</dt>
                    <dd>{student.emergency_contact} {student.emergency_phone && `— ${student.emergency_phone}`}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
        </div>
      )}

      {activeTab === 'courses' && (
        <div>
          {semestres.length === 0 ? (
            <p className="text-muted">Aucun cours associé à cette filière.</p>
          ) : semestres.map((sem) => (
            <div key={sem} className="mb-4">
              <h6 className="fw-bold mb-2">
                Semestre {sem}
                {sem === semestre && <span className="badge bg-warning text-dark ms-2">En cours</span>}
              </h6>
              {coursesBySemester[sem].map((pc) => {
                const ue = pc.teaching_unit_detail
                if (!ue) return null
                return (
                  <div key={pc.id} className="card-injs p-3 mb-2">
                    <div className="d-flex justify-content-between align-items-start">
                      <div>
                        <code>{ue.code}</code> — <strong>{ue.name}</strong>
                        {pc.is_mandatory === false && <span className="badge bg-secondary ms-2">Optionnel</span>}
                      </div>
                      <span className="badge-injs">{pc.credits || ue.credits_ects} CECT</span>
                    </div>
                    {(ue.courses || []).length > 0 && (
                      <ul className="small text-muted mb-0 mt-2 ps-3">
                        {ue.courses.map((ecue) => (
                          <li key={ecue.id}>
                            <code>{ecue.code}</code> — {ecue.name}
                            <span className="ms-2">
                              (CM {ecue.hours_cm}h / TD {ecue.hours_td}h / TP {ecue.hours_tp}h)
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'grades' && (
        <div className="table-responsive">
          {grades.length === 0 ? (
            <p className="text-muted">Aucune note enregistrée.</p>
          ) : (
            <table className="table table-injs table-sm mb-0">
              <thead>
                <tr><th>Évaluation</th><th>Note</th><th>Absent</th></tr>
              </thead>
              <tbody>
                {grades.map((g) => (
                  <tr key={g.id}>
                    <td>{g.evaluation_name || g.evaluation}</td>
                    <td className="fw-bold">{g.score != null ? `${g.score}/20` : '—'}</td>
                    <td>{g.is_absent ? 'Oui' : 'Non'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'enrollments' && (
        <div>
          {enrollments.length === 0 ? (
            <p className="text-muted">Aucune inscription.</p>
          ) : enrollments.map((e) => (
            <div key={e.id} className="card-injs p-3 mb-2">
              <strong>{ENROLLMENT_TYPES[e.enrollment_type] || e.enrollment_type}</strong>
              <span className="ms-2">
                <StatusBadge statut={STATUS_LABELS[e.status] || e.status} />
              </span>
              {e.validated_at && (
                <p className="small text-muted mb-0 mt-1">Validée le {new Date(e.validated_at).toLocaleDateString('fr-FR')}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
