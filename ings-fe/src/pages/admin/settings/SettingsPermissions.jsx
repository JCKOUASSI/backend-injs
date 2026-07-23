import { useState } from 'react'
import { FiShield, FiLock } from 'react-icons/fi'
import { useToast } from '../../../context/ToastContext'
import { mockSubmit } from '../../../utils/mockSubmit'
import { PERMISSION_MODULES, ROLES_SYSTEME } from '../../../data/mockData'

function hasPermission(role, key) {
  if (role.permissions.includes('*')) return true
  return role.permissions.includes(key)
}

export default function SettingsPermissions() {
  const { showToast } = useToast()
  const [roles, setRoles] = useState(() =>
    ROLES_SYSTEME.map(r => ({ ...r, permissions: [...r.permissions] }))
  )
  const [selectedRoleId, setSelectedRoleId] = useState('professeur')
  const [saving, setSaving] = useState(false)

  const selectedRole = roles.find(r => r.id === selectedRoleId)
  const isFullAccess = selectedRole?.permissions.includes('*')

  const togglePermission = (key) => {
    if (!selectedRole || selectedRole.isSystem && selectedRole.id === 'admin') return
    setRoles(prev => prev.map(role => {
      if (role.id !== selectedRoleId) return role
      const has = role.permissions.includes(key)
      return {
        ...role,
        permissions: has
          ? role.permissions.filter(p => p !== key)
          : [...role.permissions, key],
      }
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    await mockSubmit(showToast, 'Permissions enregistrées pour le rôle sélectionné')
    setSaving(false)
  }

  return (
    <>
      <p className="text-muted small mb-4">
        Définissez les droits d&apos;accès par rôle. Les modifications seront appliquées au serveur lors de la connexion.
      </p>

      <div className="row g-4">
        <div className="col-lg-4">
          <div className="card-injs p-3">
            <h6 className="fw-bold mb-3">Rôles</h6>
            <div className="d-flex flex-column gap-2">
              {roles.map(role => (
                <button
                  key={role.id}
                  type="button"
                  className={`settings-role-card ${selectedRoleId === role.id ? 'active' : ''}`}
                  onClick={() => setSelectedRoleId(role.id)}
                >
                  <div className="d-flex align-items-start gap-2">
                    {role.id === 'admin' ? <FiShield className="mt-1" /> : <FiLock className="mt-1" />}
                    <div className="text-start">
                      <div className="fw-semibold">{role.label}</div>
                      <div className="small text-muted">{role.description}</div>
                      {role.isSystem && <span className="badge-injs badge-lmd-licence mt-1">Système</span>}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="col-lg-8">
          {selectedRole && (
            <div className="card-injs p-4">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
                <div>
                  <h6 className="fw-bold mb-1">Permissions — {selectedRole.label}</h6>
                  <p className="text-muted small mb-0">
                    {isFullAccess
                      ? 'Ce rôle dispose de tous les droits (accès administrateur).'
                      : `${selectedRole.permissions.length} permission(s) active(s)`}
                  </p>
                </div>
                {!isFullAccess && (
                  <button type="button" className="btn btn-injs-primary btn-sm" disabled={saving} onClick={handleSave}>
                    {saving ? 'Enregistrement...' : 'Enregistrer les permissions'}
                  </button>
                )}
              </div>

              {isFullAccess ? (
                <div className="settings-perm-notice">
                  <FiShield size={20} />
                  <span>Le rôle Administration ne peut pas être restreint depuis cette interface.</span>
                </div>
              ) : (
                PERMISSION_MODULES.map(mod => (
                  <div key={mod.id} className="settings-perm-module">
                    <h6 className="fw-semibold mb-3">{mod.label}</h6>
                    <div className="row g-2">
                      {mod.permissions.map(perm => (
                        <div key={perm.key} className="col-md-6">
                          <label className="settings-perm-check">
                            <input
                              type="checkbox"
                              checked={hasPermission(selectedRole, perm.key)}
                              onChange={() => togglePermission(perm.key)}
                              disabled={selectedRole.isSystem && selectedRole.id === 'etudiant'}
                            />
                            <span>{perm.label}</span>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}

              {selectedRole.id === 'etudiant' && (
                <p className="small text-muted mt-3 mb-0">
                  Le rôle Étudiant est verrouillé : accès limité au parcours personnel uniquement.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
