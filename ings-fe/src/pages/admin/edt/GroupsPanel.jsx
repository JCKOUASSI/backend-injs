import { useEffect, useMemo, useState } from 'react'
import { FiPlus, FiTrash2, FiUsers } from 'react-icons/fi'
import Modal from '../../../components/common/Modal'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import {
  addGroupMember,
  createStudentGroup,
  deleteStudentGroup,
  fetchGroupMembers,
  fetchStudentGroups,
  removeGroupMember,
} from '../../../api/faculty'
import { fetchStudents } from '../../../api/students'

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
  const [active, setActive] = useState(null)

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
      if (active?.id === group.id) setActive(null)
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
                    <button type="button" className="btn btn-outline-primary btn-sm me-2" onClick={() => setActive(group)}>
                      <FiUsers className="me-1" /> Étudiants
                    </button>
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

      <GroupMembersModal
        group={active}
        promotion={promotion}
        onClose={() => setActive(null)}
        onChanged={reload}
      />
    </div>
  )
}

function GroupMembersModal({ group, promotion, onClose, onChanged }) {
  const { showToast } = useToast()
  const { data: membersData, reload: reloadMembers } = useFetch(
    () => (group ? fetchGroupMembers(group.id) : Promise.resolve({ results: [] })),
    [group?.id],
  )
  const { data: studentsData } = useFetch(
    () => (promotion
      ? fetchStudents({ promotion, status: 'active', page_size: 200 })
      : Promise.resolve({ results: [] })),
    [promotion],
  )
  const members = membersData?.results || []
  const memberStudentIds = useMemo(() => new Set(members.map((row) => row.student)), [members])
  const available = (studentsData?.results || []).filter((row) => !memberStudentIds.has(row.uuid))
  const [selectedIds, setSelectedIds] = useState([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setSelectedIds([])
  }, [group?.id])

  const addSelected = async () => {
    if (!group || !selectedIds.length) return
    setSaving(true)
    try {
      await Promise.all(selectedIds.map((student) => addGroupMember({ group: group.id, student })))
      showToast(`${selectedIds.length} étudiant(s) ajouté(s)`, 'success')
      setSelectedIds([])
      reloadMembers()
      onChanged?.()
    } catch (err) {
      showToast(err.message || 'Ajout impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (member) => {
    setSaving(true)
    try {
      await removeGroupMember(member.id)
      showToast('Étudiant retiré', 'success')
      reloadMembers()
      onChanged?.()
    } catch (err) {
      showToast(err.message || 'Retrait impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      show={Boolean(group)}
      onClose={onClose}
      title={group ? `Étudiants — ${group.name}` : ''}
      size="lg"
      footer={(
        <>
          <button type="button" className="btn btn-injs-primary" disabled={saving || !selectedIds.length} onClick={addSelected}>
            Ajouter ({selectedIds.length})
          </button>
          <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Fermer</button>
        </>
      )}
    >
      {group && (
        <div className="row g-3">
          <div className="col-md-6">
            <h6 className="fw-bold">Dans le groupe ({members.length})</h6>
            {!members.length && <p className="small text-muted">Aucun membre pour l’instant.</p>}
            <ul className="list-group list-group-flush" style={{ maxHeight: 280, overflow: 'auto' }}>
              {members.map((member) => (
                <li key={member.id} className="list-group-item px-0 d-flex justify-content-between align-items-center">
                  <span className="small">
                    <code className="me-2">{member.matricule}</code>
                    {member.student_name}
                  </span>
                  <button type="button" className="btn btn-outline-danger btn-sm" disabled={saving} onClick={() => remove(member)}>
                    <FiTrash2 />
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="col-md-6">
            <h6 className="fw-bold">Disponibles ({available.length})</h6>
            {!available.length && <p className="small text-muted">Tous les étudiants actifs de la promotion sont déjà affectés.</p>}
            <ul className="list-group list-group-flush" style={{ maxHeight: 280, overflow: 'auto' }}>
              {available.map((student) => (
                <li key={student.uuid} className="list-group-item px-0">
                  <label className="small d-flex align-items-center gap-2 mb-0">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(student.uuid)}
                      onChange={(e) => {
                        setSelectedIds((prev) => (
                          e.target.checked
                            ? [...prev, student.uuid]
                            : prev.filter((id) => id !== student.uuid)
                        ))
                      }}
                    />
                    <code>{student.id}</code> {student.prenom} {student.nom}
                  </label>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </Modal>
  )
}
