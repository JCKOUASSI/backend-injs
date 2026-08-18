import { useEffect, useMemo, useState } from 'react'
import { FiSettings, FiUsers, FiShield } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import ExportButtons from '../../components/common/ExportButtons'
import { useFetch } from '../../hooks/useFetch'
import { fetchUsers } from '../../api/users'
import { ROLES_SYSTEME } from '../../data/mockData'
import SettingsInstitution from './settings/SettingsInstitution'
import SettingsUsers from './settings/SettingsUsers'
import SettingsPermissions from './settings/SettingsPermissions'

const SECTIONS = [
  { id: 'institution', label: 'Institution', icon: FiSettings },
  { id: 'utilisateurs', label: 'Utilisateurs', icon: FiUsers },
  { id: 'permissions', label: 'Rôles & permissions', icon: FiShield },
]

function getRoleLabel(roleId) {
  return ROLES_SYSTEME.find((r) => r.id === roleId)?.label ?? roleId
}

export default function AdminSettings() {
  const [section, setSection] = useState('utilisateurs')
  const [createNonce, setCreateNonce] = useState(0)
  const [filteredCount, setFilteredCount] = useState(null)

  const { data: usersData, loading: usersLoading, error: usersError, reload: reloadUsers } = useFetch(
    () => fetchUsers({ page_size: 500 }),
    [],
  )

  const users = usersData?.results || []
  const stats = useMemo(() => {
    const actifs = users.filter((u) => u.statut === 'Actif').length
    const byRole = {}
    for (const u of users) {
      byRole[u.role] = (byRole[u.role] || 0) + 1
    }
    return {
      total: usersData?.count ?? users.length,
      actifs,
      inactifs: Math.max(0, (usersData?.count ?? users.length) - actifs),
      roles: ROLES_SYSTEME.length,
      byRole,
    }
  }, [users, usersData?.count])

  useEffect(() => {
    if (section !== 'utilisateurs') setFilteredCount(null)
  }, [section])

  const exportRows = users.map((u) => [
    u.id,
    u.nom,
    u.prenom,
    u.email,
    getRoleLabel(u.role),
    u.statut,
  ])

  return (
    <>
      <PageHeader
        title="Paramètres"
        subtitle={`Configuration plateforme — ${stats.total} utilisateur(s)`}
        action={
          <div className="widget-actions">
            <ExportButtons
              title="Utilisateurs INJS"
              filename="utilisateurs_injs"
              headers={['ID', 'Nom', 'Prénom', 'Email', 'Rôle', 'Statut']}
              rows={exportRows}
              resourcePath="/auth/users"
            />
            {section === 'utilisateurs' && (
              <button
                type="button"
                className="btn btn-injs-primary"
                onClick={() => setCreateNonce((n) => n + 1)}
              >
                + Créer un utilisateur
              </button>
            )}
          </div>
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{stats.total}</div>
            <div className="small text-muted">Utilisateurs</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-success">{stats.actifs}</div>
            <div className="small text-muted">Comptes actifs</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{stats.roles}</div>
            <div className="small text-muted">Rôles système</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{filteredCount ?? stats.total}</div>
            <div className="small text-muted">Résultats filtrés</div>
          </div>
        </div>
      </div>

      <div className="card-injs p-3 mb-3">
        <div className="d-flex flex-wrap gap-2 align-items-center">
          <span className="small text-muted me-1">Section :</span>
          {SECTIONS.map((s) => {
            const Icon = s.icon
            const count = s.id === 'utilisateurs'
              ? stats.total
              : s.id === 'permissions'
                ? stats.roles
                : 1
            return (
              <button
                key={s.id}
                type="button"
                className={`btn btn-sm ${section === s.id ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
                onClick={() => setSection(s.id)}
              >
                <Icon className="me-1" size={14} style={{ verticalAlign: '-2px' }} />
                {s.label} <span className="opacity-75">({count})</span>
              </button>
            )
          })}
        </div>
      </div>

      {section === 'institution' && <SettingsInstitution />}
      {section === 'utilisateurs' && (
        <SettingsUsers
          users={users}
          totalCount={stats.total}
          byRole={stats.byRole}
          loading={usersLoading}
          error={usersError}
          onReload={reloadUsers}
          createNonce={createNonce}
          onFilteredCountChange={setFilteredCount}
          hideCreateButton
        />
      )}
      {section === 'permissions' && <SettingsPermissions />}
    </>
  )
}
