import { useState } from 'react'
import { FiEdit2 } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import IconActionButtons from '../../components/common/IconActionButtons'
import { useToast } from '../../context/ToastContext'
import { mockSubmit } from '../../utils/mockSubmit'
import { STAGES } from '../../data/mockData'

export default function ProfInternships() {
  const { showToast } = useToast()
  const [showEval, setShowEval] = useState(false)
  const [form, setForm] = useState({ note: '', commentaire: '' })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    await mockSubmit(showToast, 'Évaluation de stage enregistrée')
    setSaving(false)
    setShowEval(false)
  }

  return (
    <>
      <PageHeader title="Suivi des stages" subtitle="Supervision pédagogique — Rapports de stage" />
      <div className="card-injs overflow-hidden">
        <table className="table table-injs mb-0">
          <thead><tr><th>Étudiant</th><th>Type</th><th>Lieu</th><th>Statut</th><th>Actions</th></tr></thead>
          <tbody>
            <tr>
              <td>Koné Aminata</td><td>{STAGES[0].type}</td><td>{STAGES[0].lieu}</td>
              <td><span className="grade-badge grade-pending">En cours</span></td>
              <td>
                <IconActionButtons
                  actions={[
                    { type: 'edit', title: 'Évaluer', icon: FiEdit2, onClick: () => setShowEval(true) },
                  ]}
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <Modal
        show={showEval}
        onClose={() => setShowEval(false)}
        title="Évaluer le stage — Koné Aminata"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowEval(false)}>Annuler</button>
            <button type="submit" form="eval-stage-form" className="btn btn-injs-primary" disabled={saving}>{saving ? 'Enregistrement...' : 'Valider'}</button>
          </>
        }
      >
        <form id="eval-stage-form" onSubmit={handleSubmit}>
          <div className="mb-3"><label className="form-label">Note /20</label><input type="number" min="0" max="20" step="0.5" className="form-control" required value={form.note} onChange={ev => setForm({ ...form, note: ev.target.value })} /></div>
          <div className="mb-3"><label className="form-label">Appréciation</label><textarea className="form-control" rows={4} required value={form.commentaire} onChange={ev => setForm({ ...form, commentaire: ev.target.value })} placeholder="Compétences observées, points forts, axes d'amélioration..." /></div>
        </form>
      </Modal>
    </>
  )
}
