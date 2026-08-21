import { useMemo, useState } from 'react'
import { FiCalendar, FiAlertTriangle, FiCheckSquare, FiClock, FiLayers, FiZap, FiUsers, FiSettings, FiBookOpen } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import StatCard from '../../components/common/StatCard'
import ExportButtons from '../../components/common/ExportButtons'
import { useFetch } from '../../hooks/useFetch'
import { fetchEdtDashboard } from '../../api/faculty'
import { fetchFormationPeriods, fetchPromotions } from '../../api/academics'
import WeeklyGrid from './edt/WeeklyGrid'
import CalendarPanel from './edt/CalendarPanel'
import PeriodesPanel from './edt/PeriodesPanel'
import GenerationPanel from './edt/GenerationPanel'
import ConflictsPanel from './edt/ConflictsPanel'
import GroupsPanel from './edt/GroupsPanel'
import SettingsPanel from './edt/SettingsPanel'
import LoadsPanel from './edt/LoadsPanel'

const TABS = [
  { id: 'calendar', label: 'Calendrier', icon: FiCalendar },
  { id: 'generate', label: 'Génération', icon: FiZap },
  { id: 'loads', label: 'Charges', icon: FiBookOpen },
  { id: 'conflicts', label: 'Conflits', icon: FiAlertTriangle },
  { id: 'periods', label: 'Périodes', icon: FiLayers },
  { id: 'groups', label: 'Groupes', icon: FiUsers },
  { id: 'settings', label: 'Réglages', icon: FiSettings },
  { id: 'weekly', label: 'Grille hebdomadaire', icon: FiClock },
]

export default function AdminSchedule() {
  const [tab, setTab] = useState('calendar')
  const [period, setPeriod] = useState('')
  const [promotion, setPromotion] = useState('')

  const { data: periodsData, reload: reloadPeriods } = useFetch(
    () => fetchFormationPeriods({ page_size: 50, is_active: true }),
    [],
  )
  const { data: promotions } = useFetch(() => fetchPromotions(), [])
  const periods = periodsData?.results || []

  const dashParams = useMemo(
    () => ({ period: period || undefined, promotion: promotion || undefined }),
    [period, promotion],
  )
  const { data: dashboard, reload: reloadDash } = useFetch(
    () => fetchEdtDashboard(dashParams),
    [dashParams.period, dashParams.promotion],
  )

  const filters = { period, promotion, periods, promotions: promotions || [] }

  return (
    <>
      <PageHeader
        title="Gestion des Emplois du Temps (EDT)"
        subtitle="Périodes de formation → séances datées → publication vers les cours"
        action={(
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <select
              className="form-select form-select-sm"
              style={{ minWidth: 180 }}
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
            >
              <option value="">Toutes les périodes</option>
              {periods.map((row) => (
                <option key={row.id} value={row.id}>{row.label}</option>
              ))}
            </select>
            <select
              className="form-select form-select-sm"
              style={{ minWidth: 160 }}
              value={promotion}
              onChange={(e) => setPromotion(e.target.value)}
            >
              <option value="">Toutes les promotions</option>
              {(promotions || []).map((row) => (
                <option key={row.id} value={row.id}>{row.name}</option>
              ))}
            </select>
            <ExportButtons
              title="Emploi du temps INJS"
              filename="edt_seances"
              resourcePath="/faculty/seances"
              resourceParams={{
                period: period || undefined,
                promotion: promotion || undefined,
              }}
              size="sm"
            />
          </div>
        )}
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <StatCard icon={FiCalendar} label="Séances" value={dashboard?.total ?? '—'} color="blue" compact />
        </div>
        <div className="col-6 col-md-3">
          <StatCard icon={FiCheckSquare} label="Publiées" value={dashboard?.published ?? '—'} color="green" compact />
        </div>
        <div className="col-6 col-md-3">
          <StatCard icon={FiClock} label="À venir" value={dashboard?.upcoming ?? '—'} color="orange" compact />
        </div>
        <div className="col-6 col-md-3">
          <StatCard icon={FiAlertTriangle} label="Conflits" value={dashboard?.conflicts ?? '—'} color="orange" compact />
        </div>
      </div>

      <ul className="nav nav-pills edt-tabs mb-3 gap-1 flex-wrap">
        {TABS.map((item) => {
          const Icon = item.icon
          return (
            <li className="nav-item" key={item.id}>
              <button
                type="button"
                className={`nav-link ${tab === item.id ? 'active' : ''}`}
                onClick={() => setTab(item.id)}
              >
                <Icon className="me-1" /> {item.label}
              </button>
            </li>
          )
        })}
      </ul>

      {tab === 'calendar' && (
        <CalendarPanel filters={filters} onChanged={reloadDash} />
      )}
      {tab === 'generate' && (
        <GenerationPanel filters={filters} onChanged={reloadDash} />
      )}
      {tab === 'loads' && (
        <LoadsPanel filters={filters} />
      )}
      {tab === 'conflicts' && (
        <ConflictsPanel filters={filters} />
      )}
      {tab === 'periods' && (
        <PeriodesPanel onChanged={reloadPeriods} />
      )}
      {tab === 'groups' && (
        <GroupsPanel filters={filters} />
      )}
      {tab === 'settings' && (
        <SettingsPanel />
      )}
      {tab === 'weekly' && (
        <WeeklyGrid />
      )}
    </>
  )
}
