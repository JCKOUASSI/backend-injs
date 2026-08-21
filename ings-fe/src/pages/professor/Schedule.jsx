import { useMemo } from 'react'
import PageHeader from '../../components/common/PageHeader'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchMyTeacherProfile, fetchScheduleGrid, fetchSeances } from '../../api/faculty'
import UpcomingSeances from '../../components/edt/UpcomingSeances'

const DAYS = [
  { value: 0, label: 'Lundi' },
  { value: 1, label: 'Mardi' },
  { value: 2, label: 'Mercredi' },
  { value: 3, label: 'Jeudi' },
  { value: 4, label: 'Vendredi' },
  { value: 5, label: 'Samedi' },
]

const TIME_ROWS = [
  { start: '08:00', end: '10:00' },
  { start: '10:00', end: '12:00' },
  { start: '14:00', end: '16:00' },
  { start: '16:00', end: '18:00' },
]

export default function ProfessorSchedule() {
  const { user } = useAuth()
  const { data: teacher } = useFetch(() => fetchMyTeacherProfile().catch(() => null), [])
  const { data: grid, loading, error } = useFetch(
    () => (teacher?.id ? fetchScheduleGrid({ teacher: teacher.id }) : Promise.resolve({ schedules: [] })),
    [teacher?.id],
  )

  const today = new Date().toISOString().slice(0, 10)
  const { data: seancesData } = useFetch(
    () => (teacher?.id
      ? fetchSeances({ teacher: teacher.id, visible: true, date_from: today, page_size: 20, ordering: 'date' })
      : Promise.resolve({ results: [] })),
    [teacher?.id],
  )
  const upcoming = seancesData?.results || []
  const slots = grid?.schedules || []
  const cellMap = useMemo(() => {
    const map = {}
    for (const s of slots) {
      const key = `${s.day_of_week}|${s.start_time}`
      if (!map[key]) map[key] = []
      map[key].push(s)
    }
    return map
  }, [slots])

  return (
    <>
      <PageHeader
        title="Mon emploi du temps"
        subtitle={`${user?.prenom || ''} ${user?.nom || ''} — ${slots.length} créneau(x)`}
      />
      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}

      <UpcomingSeances seances={upcoming} emptyText="Aucune séance publiée à venir." />

      <div className="card-injs edt-grid-wrap">
        <div className="table-responsive">
          <table className="table edt-grid mb-0">
            <thead>
              <tr>
                <th className="edt-time-col">Horaire</th>
                {DAYS.map((d) => <th key={d.value} className="text-center">{d.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {TIME_ROWS.map((row) => (
                <tr key={row.start}>
                  <td className="edt-time-col">
                    <strong>{row.start}</strong>
                    <div className="small text-muted">{row.end}</div>
                  </td>
                  {DAYS.map((d) => (
                    <td key={`${d.value}-${row.start}`} className="edt-cell">
                      {(cellMap[`${d.value}|${row.start}`] || []).map((s) => (
                        <div key={s.id} className="edt-block" style={{ cursor: 'default' }}>
                          <div className="edt-block-code">{s.course_code} {s.session_kind ? `· ${String(s.session_kind).toUpperCase()}` : ''}</div>
                          <div className="edt-block-title">{s.course_name}</div>
                          <div className="edt-block-meta">
                            {s.promotion_name} · {s.room_code || 'Salle ?'}
                            {s.supervisor_name ? ` · Enc. ${s.supervisor_name.split(' ').slice(-1)[0]}` : ''}
                          </div>
                        </div>
                      ))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
