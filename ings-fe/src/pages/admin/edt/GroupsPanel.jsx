import { useState } from 'react'
import { FiPlus, FiTrash2 } from 'react-icons/fi'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import { createStudentGroup, deleteStudentGroup, fetchStudentGroups } from '../../../api/faculty'

export default function GroupsPanel({ filters }) {
  const { showToast } = useToast()
  const promotion = filters.promotion
  const { data, loading, error, reload } = useFetch(
    () => fetchStudentGroups({ promotion: promotion || undefined, page_size: 100 }),
    [promotion],
  )
  const groups = data?.results || []
  const [name, setName] = useState('')
  const [maxStudents, setMaxStudents] = useState(25)
  const [saving, setSaving] = useState(false)

  const create = async (event) => {
    event.preventDefault()
    if (!promotion) {
      showToast('Choisissez une promotion dans la barre du haut.', 'warning')
      return
    }
    setSaving(true)
    try {
      await createStudentGroup({
        promotion,
        name: name.trim(),
        max_students: Number(maxStudents) || 25,
        is_active: true,
      })
      showToast('Groupe créé', 'success')
      setName('')
      reload()
    } catch (err) {
      showToast(err.message || 'Création impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (group) => {
    if (!window.confirm(`Supprimer le groupe « ${group.name} » ?`)) return
    setSaving(true)
    try {
      await deleteStudentGroup(group.id)
      showToast('Groupe supprimé', 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Suppression impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card-injs p-4">
      <h2 className="h6 mb-2">Groupes pédagogiques (TD / TP)</h2>
      <p className="small text-muted">
        Optionnels. Deux groupes d’une même promotion peuvent avoir cours en même temps.
        Une séance sans groupe bloque toute la promotion.
      </p>

      <form className="row g-2 align-items-end mb-4" onSubmit={create}>
        <div className="col-md-5">
          <label className="form-label">Nom</label>
          <input className="form-control" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Groupe A" />
        </div>
        <div className="col-md-3">
          <label className="form-label">Effectif max</label>
          <input type="number" min={1} className="form-control" value={maxStudents} onChange={(e) => setMaxStudents(e.target.value)} />
        </div>
        <div className="col-md-4">
          <button type="submit" className="btn btn-injs-primary w-100" disabled={saving}>
            <FiPlus className="me-1" /> Créer
          </button>
        </div>
      </form>

      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {!loading && groups.length === 0 && (
        <p className="text-muted mb-0">
          {promotion ? 'Aucun groupe pour cette promotion.' : 'Filtrez une promotion pour lister et créer des groupes.'}
        </p>
      )}
      {groups.length > 0 && (
        <div className="table-responsive">
          <table className="table align-middle mb-0">
            <thead>
              <tr>
                <th>Groupe</th>
                <th>Promotion</th>
                <th>Effectif</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.id}>
                  <td>{group.name}</td>
                  <td>{group.promotion_name}</td>
                  <td>{group.headcount} / {group.max_students}</td>
                  <td className="text-end">
                    <button type="button" className="btn btn-outline-danger btn-sm" disabled={saving} onClick={() => remove(group)}>
                      <FiTrash2 />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
