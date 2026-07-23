import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiEdit2, FiCheckSquare } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import IconActionButtons from '../../components/common/IconActionButtons'
import { useFetch } from '../../hooks/useFetch'
import { fetchMyTeacherProfile } from '../../api/faculty'
import { apiGet } from '../../api/client'
import { INSTITUTION } from '../../data/mockData'

export default function ProfCourses() {
  const navigate = useNavigate()
  const { data: teacher, loading } = useFetch(() => fetchMyTeacherProfile().catch(() => null))
  const { data: assignments } = useFetch(
    () => (teacher?.id
      ? apiGet('/faculty/assignments/', { teacher: teacher.id, page_size: 100 }).then((r) => r.results)
      : Promise.resolve([])),
    [teacher?.id],
  )

  const [selected, setSelected] = useState(null)

  const rows = (assignments || []).map((a) => [
    a.course_code || a.course || '—',
    a.course_name || a.promotion_name || '—',
    a.academic_year_name || '—',
    a.promotion_name || '—',
  ])

  if (loading) return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>

  return (
    <>
      <PageHeader
        title="Mes cours & UE"
        subtitle={`Affectations pédagogiques — ${INSTITUTION.academicYear}`}
        action={
          <div className="widget-actions">
            <ExportButtons title="Mes affectations" filename="mes_cours" headers={['Cours', 'Libellé', 'Année', 'Promotion']} rows={rows} />
            <IconActionButtons
              actions={[
                {
                  key: 'presence',
                  title: 'Présences QR',
                  icon: FiCheckSquare,
                  className: 'btn-injs-primary',
                  onClick: () => navigate('/professeur/presence'),
                },
              ]}
            />
          </div>
        }
      />

      {!(assignments || []).length ? (
        <div className="card-injs p-4 text-muted">Aucune affectation trouvée pour votre profil enseignant.</div>
      ) : (assignments || []).map((c) => (
        <div key={c.id} className="card-injs p-4 mb-3">
          <div className="d-flex justify-content-between flex-wrap gap-2">
            <div>
              <code className="me-2">{c.course_code || c.course}</code>
              <strong>{c.course_name || 'Cours affecté'}</strong>
              <div className="text-muted small mt-1">
                {c.promotion_name || 'Promotion'} — {c.academic_year_name || INSTITUTION.academicYear}
              </div>
            </div>
            <span className="badge-injs">{c.hours || 'CM/TD/TP'}</span>
          </div>
          <div className="mt-3">
            <IconActionButtons
              actions={[
                { type: 'view', title: 'Détails', onClick: () => setSelected(c) },
                { type: 'edit', title: 'Saisir notes', icon: FiEdit2, onClick: () => navigate('/professeur/evaluations') },
                {
                  key: 'presence',
                  title: 'Présences QR',
                  icon: FiCheckSquare,
                  className: 'btn-outline-success',
                  onClick: () => navigate('/professeur/presence'),
                },
              ]}
            />
          </div>
          {selected?.id === c.id && (
            <div className="mt-3 p-3 rounded glass-strong small">
              <div>ID affectation : {c.id}</div>
              <div>Cours : {c.course}</div>
              <div>Promotion : {c.promotion}</div>
              <button type="button" className="btn btn-sm btn-link" onClick={() => setSelected(null)}>Fermer</button>
            </div>
          )}
        </div>
      ))}
    </>
  )
}
