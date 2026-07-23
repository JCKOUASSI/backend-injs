import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import { useFetch } from '../../hooks/useFetch'
import { fetchCampaigns, fetchPreRegistrations } from '../../api/admissions'
import { StatusBadge } from '../../utils/statusBadge'
import { translateStatus } from '../../utils/labels'

export default function AdminAdmissions() {
  const { data: campaigns, loading } = useFetch(() => fetchCampaigns())
  const { data: prereg } = useFetch(() => fetchPreRegistrations())

  const rows = (prereg?.results || []).map((p) => [
    p.email || p.candidate_email || '—',
    p.first_name || p.prenom || '—',
    p.last_name || p.nom || '—',
    translateStatus(p.status),
    p.desired_program || p.program || '—',
  ])

  if (loading) return <div className="text-center py-5"><div className="spinner-border text-primary" /></div>

  return (
    <>
      <PageHeader
        title="Admissions & préinscriptions"
        subtitle="Campagnes et dossiers candidats (API admissions)"
        action={
          <ExportButtons
            title="Préinscriptions"
            filename="preinscriptions"
            headers={['Email', 'Prénom', 'Nom', 'Statut', 'Filière']}
            rows={rows}
          />
        }
      />

      <div className="row g-4 mb-4">
        <div className="col-md-4"><div className="card-injs p-4 text-center"><h6 className="text-muted">Campagnes</h6><h2 className="fw-bold">{(campaigns || []).length}</h2></div></div>
        <div className="col-md-4"><div className="card-injs p-4 text-center"><h6 className="text-muted">Dossiers</h6><h2 className="fw-bold">{prereg?.count || 0}</h2></div></div>
        <div className="col-md-4"><div className="card-injs p-4 text-center"><h6 className="text-muted">À instruire</h6><h2 className="fw-bold">{(prereg?.results || []).filter((p) => p.status === 'submitted' || p.status === 'pending').length}</h2></div></div>
      </div>

      <div className="card-injs p-4 mb-4">
        <h5 className="fw-bold mb-3">Campagnes</h5>
        {(campaigns || []).length === 0 ? (
          <p className="text-muted mb-0">Aucune campagne — créez-en via l&apos;API / l&apos;administration serveur.</p>
        ) : (campaigns || []).map((c) => (
          <div key={c.id} className="d-flex justify-content-between py-2 border-bottom">
            <span>{c.name || c.title}</span>
            <span className="badge-injs">{c.is_active || c.status ? 'Ouverte' : 'Fermée'}</span>
          </div>
        ))}
      </div>

      <div className="card-injs overflow-hidden">
        <div className="p-3 border-bottom fw-bold">Préinscriptions</div>
        <table className="table table-injs mb-0">
          <thead><tr><th>Email</th><th>Nom</th><th>Statut</th><th>Filière</th></tr></thead>
          <tbody>
            {(prereg?.results || []).map((p) => (
              <tr key={p.id}>
                <td>{p.email || p.candidate_email || '—'}</td>
                <td>{p.first_name || p.prenom || ''} {p.last_name || p.nom || ''}</td>
                <td><StatusBadge statut={p.status || '—'} /></td>
                <td>{p.desired_program || p.program || '—'}</td>
              </tr>
            ))}
            {!(prereg?.results || []).length && (
              <tr><td colSpan={4} className="text-center text-muted py-4">Aucun dossier</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
