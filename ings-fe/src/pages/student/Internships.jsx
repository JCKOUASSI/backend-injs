import { useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import { useToast } from '../../context/ToastContext'
import { useAuth } from '../../context/AuthContext'
import { mockSubmit } from '../../utils/mockSubmit'
import { isSemestreInNiveau } from '../../utils/studentLevel'
import { STAGES } from '../../data/mockData'

export default function StudentInternships() {
  const { showToast } = useToast()
  const { user } = useAuth()
  const stages = STAGES.filter((s) => isSemestreInNiveau(s.semestre, user?.niveau || 'L1'))
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ titre: '', fichier: null })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.titre) { showToast('Titre du rapport obligatoire', 'warning'); return }
    setSaving(true)
    await mockSubmit(showToast, 'Rapport de stage déposé')
    setSaving(false)
    setShowForm(false)
    setForm({ titre: '', fichier: null })
  }

  return (
    <>
      <PageHeader title="Mes stages" subtitle={`Stages ${user?.niveau} — ${stages.length} stage(s) dans votre parcours`} />
      <div className="row g-4">
        {stages.length === 0 ? (
          <div className="col-12"><div className="card-injs p-4 text-muted text-center">Aucun stage prévu pour votre niveau ({user?.niveau}).</div></div>
        ) : stages.map((s, i) => (
          <div key={i} className="col-md-4">
            <div className="card-injs p-4 h-100">
              <span className={`grade-badge ${s.statut === 'En cours' ? 'grade-pending' : 'grade-valid'} mb-2`}>{s.statut}</span>
              <h5 className="fw-bold">{s.type}</h5>
              <p className="small mb-1"><strong>Semestre :</strong> S{s.semestre}</p>
              <p className="small mb-1"><strong>Lieu :</strong> {s.lieu}</p>
              <p className="small mb-1"><strong>Durée :</strong> {s.duree}</p>
              <p className="small mb-3"><strong>Superviseur :</strong> {s.superviseur}</p>
              {s.statut === 'En cours' && (
                <button type="button" className="btn btn-sm btn-injs-primary" onClick={() => setShowForm(true)}>Déposer rapport</button>
              )}
            </div>
          </div>
        ))}
      </div>

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title="Déposer un rapport de stage"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="rapport-form" className="btn btn-injs-primary" disabled={saving}>{saving ? 'Envoi...' : 'Déposer'}</button>
          </>
        }
      >
        <form id="rapport-form" onSubmit={handleSubmit}>
          <div className="mb-3"><label className="form-label">Titre du rapport *</label><input className="form-control" required value={form.titre} onChange={ev => setForm({ ...form, titre: ev.target.value })} /></div>
          <div className="mb-3"><label className="form-label">Fichier PDF</label><input type="file" className="form-control" accept=".pdf,.doc,.docx" onChange={ev => setForm({ ...form, fichier: ev.target.files[0] })} /></div>
          <div className="mb-3"><label className="form-label">Résumé</label><textarea className="form-control" rows={3} placeholder="Synthèse des activités réalisées..." /></div>
        </form>
      </Modal>
    </>
  )
}
