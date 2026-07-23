import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchGrades } from '../../api/exams'
import { StatusBadge } from '../../utils/statusBadge'

export default function StudentGrades() {
  const { user } = useAuth()
  const { data, loading, error } = useFetch(() => fetchGrades())
  const grades = data?.results || []

  const scored = grades.filter((g) => g.moyenne != null)
  const moyenne = scored.length
    ? (scored.reduce((a, n) => a + n.moyenne, 0) / scored.length).toFixed(2)
    : '—'

  const creditsEstimes = scored.filter((g) => g.statut === 'Validé' || Number(g.moyenne) >= 10).length * 3

  const rows = grades.map((n) => [n.label, n.ue, n.moyenne ?? '—', n.statut])

  if (loading) {
    return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger m-4">Erreur de chargement : {error}</div>
  }

  return (
    <>
      <PageHeader
        title="Mes notes & crédits"
        subtitle={`${user?.niveau} — Semestre ${user?.semestre}`}
        action={
          <ExportButtons
            title="Mes notes INJS"
            filename="mes_notes"
            headers={['Évaluation', 'UE', 'Note', 'Statut']}
            rows={rows}
          />
        }
      />

      <div className="row g-4 mb-4">
        <div className="col-md-3"><div className="card-injs p-4 text-center"><h6 className="text-muted">Moyenne</h6><h2 className="fw-bold text-success">{moyenne}{moyenne !== '—' ? '/20' : ''}</h2></div></div>
        <div className="col-md-3"><div className="card-injs p-4 text-center"><h6 className="text-muted">Évaluations</h6><h2 className="fw-bold">{grades.length}</h2></div></div>
        <div className="col-md-3"><div className="card-injs p-4 text-center"><h6 className="text-muted">Notes saisies</h6><h2 className="fw-bold">{scored.length}</h2></div></div>
        <div className="col-md-3"><div className="card-injs p-4 text-center"><h6 className="text-muted">Crédits estimés</h6><h2 className="fw-bold">{creditsEstimes}</h2></div></div>
      </div>

      <div className="card-injs p-3 mb-4 small text-muted">
        Règles LMD INJS : ECUE = CC 40 % + CT 60 % (≥ 10). Compensation UE si moyenne ≥ 10 et aucun ECUE &lt; 8.
      </div>

      {grades.length === 0 ? (
        <div className="card-injs p-4 text-center text-muted">Aucune note disponible pour le moment.</div>
      ) : (
        <div className="card-injs overflow-hidden">
          <table className="table table-injs mb-0">
            <thead>
              <tr><th>Évaluation</th><th>UE</th><th>Note (/20)</th><th>Statut</th></tr>
            </thead>
            <tbody>
              {grades.map((n) => (
                <tr key={n.id}>
                  <td>{n.label}</td>
                  <td><code>{n.ue}</code></td>
                  <td className="fw-bold">{n.moyenne ?? '—'}</td>
                  <td><StatusBadge statut={n.statut} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
