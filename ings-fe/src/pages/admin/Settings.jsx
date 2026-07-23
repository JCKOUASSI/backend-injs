import { useState } from 'react'
import { FiSettings, FiUsers, FiShield } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import SettingsInstitution from './settings/SettingsInstitution'
import SettingsUsers from './settings/SettingsUsers'
import SettingsPermissions from './settings/SettingsPermissions'

const TABS = [
  { id: 'institution', label: 'Institution', icon: FiSettings },
  { id: 'utilisateurs', label: 'Utilisateurs', icon: FiUsers },
  { id: 'permissions', label: 'Rôles & permissions', icon: FiShield },
]

export default function AdminSettings() {
  const [activeTab, setActiveTab] = useState('institution')

  return (
    <>
      <PageHeader
        title="Paramètres"
        subtitle="Configuration de la plateforme, comptes utilisateurs et droits d'accès"
      />

      <div className="settings-tabs mb-4">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <tab.icon size={18} />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'institution' && (
        <div className="card-injs p-4">
          <SettingsInstitution />
        </div>
      )}

      {activeTab === 'utilisateurs' && (
        <div className="card-injs p-4">
          <SettingsUsers />
        </div>
      )}

      {activeTab === 'permissions' && (
        <SettingsPermissions />
      )}
    </>
  )
}
