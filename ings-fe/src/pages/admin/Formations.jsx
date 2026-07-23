import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import { useFetch } from '../../hooks/useFetch'
import { fetchPrograms, fetchSpecializations, fetchPromotions, fetchAcademicYears } from '../../api/academics'
import { GRADES_LMD } from '../../data/mockData'

export default function AdminFormations() {
  const { data: programs, loading } = useFetch(() => fetchPrograms())
  const { data: specializations } = useFetch(() => fetchSpecializations())
  const { data: promotions } = useFetch(() => fetchPromotions())
  const { data: years } = useFetch(() => fetchAcademicYears())

  const rows = (programs || []).map((p) => [
    p.code,
    p.name,
    p.degree || p.level || '—',
    p.track || '—',
    p.credits_ects || p.duration_years || '—',
  ])

  if (loading) return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>

  return (
    <>
      <PageHeader
        title="Formations LMD"
        subtitle="Filières, promotions et spécialités (référentiel API)"
        action={
          <ExportButtons
            title="Formations INJS"
            filename="injs_formations"
            headers={['Code', 'Nom', 'Grade', 'Track', 'Crédits/Durée']}
            rows={rows}
            resourcePath="/academics/programs"
          />
        }
      />

      <div className="row g-4 mb-4">
        {GRADES_LMD.map((g) => (
          <div key={g.id} className="col-md-4">
            <div className="card-injs p-4 text-center h-100">
              <span className={`badge-lmd-${g.id} badge-injs mb-3`}>{g.label}</span>
              <h3 className="fw-bold">{g.credits} ECTS</h3>
              <p className="text-muted mb-0">{g.duree}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="card-injs overflow-hidden mb-4">
        <div className="p-3 border-bottom d-flex justify-content-between align-items-center">
          <h5 className="fw-bold mb-0">Filières (Programs)</h5>
          <span className="badge-injs">{(programs || []).length} programme(s)</span>
        </div>
        <table className="table table-injs mb-0">
          <thead><tr><th>Code</th><th>Intitulé</th><th>Grade</th><th>Track</th></tr></thead>
          <tbody>
            {(programs || []).length === 0 ? (
              <tr><td colSpan={4} className="text-muted text-center py-3">Aucun programme — importer la maquette STAPS.</td></tr>
            ) : (programs || []).map((p) => (
              <tr key={p.id}>
                <td><code>{p.code}</code></td>
                <td>{p.name}</td>
                <td>{p.degree || p.level || '—'}</td>
                <td>{p.track || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row g-4">
        <div className="col-lg-6">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Spécialités STAPS</h5>
            {(specializations || []).map((s) => (
              <div key={s.id} className="d-flex justify-content-between py-2 border-bottom">
                <span><strong>{s.code}</strong> — {s.name}</span>
              </div>
            ))}
            {!(specializations || []).length && <p className="text-muted mb-0">Aucune spécialité.</p>}
          </div>
        </div>
        <div className="col-lg-6">
          <div className="card-injs p-4">
            <h5 className="fw-bold mb-3">Promotions & années</h5>
            <p className="small text-muted">Années : {(years || []).map((y) => y.name || y.label).join(', ') || '—'}</p>
            {(promotions || []).map((p) => (
              <div key={p.id} className="d-flex justify-content-between py-2 border-bottom">
                <span>{p.name || p.code}</span>
                <span className="badge-injs">{p.program_name || ''}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
