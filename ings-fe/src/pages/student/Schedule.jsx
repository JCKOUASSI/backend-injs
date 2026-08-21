import { useMemo } from 'react'
import PageHeader from '../../components/common/PageHeader'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { fetchScheduleGrid, fetchSeances } from '../../api/faculty'
import { fetchMyStudentProfile } from '../../api/students'
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

export default function StudentSchedule() {
  const { user } = useAuth()
  const { data: me } = useFetch(() => fetchMyStudentProfile(user).catch(() => null), [user?.id])
  const promotionId = me?.promotionId || null

  const { data: grid, loading, error } = useFetch(
    () => (promotionId
      ? fetchScheduleGrid({ promotion: promotionId })
      : fetchScheduleGrid()),
    [promotionId],
  )

  const today = new Date().toISOString().slice(0, 10)
  const { data: seancesData } = useFetch(
    () => (promotionId
      ? fetchSeances({ promotion: promotionId, visible: true, date_from: today, page_size: 20, ordering: 'date' })
      : Promise.resolve({ results: [] })),
    [promotionId],
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
        subtitle={`${user?.niveau || ''} — Semestre ${me?.semestre || user?.semestre || ''}`}
      />
      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}
      {!loading && !slots.length && (
        <div className="alert alert-info">Aucun créneau hebdomadaire publié pour votre promotion.</div>
      )}

      <UpcomingSeances seances={upcoming} emptyText="Aucune séance datée publiée pour le moment." />

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
                            {s.room_code || 'Salle ?'} · {s.teacher_name}
                            {s.supervisor_name ? ` · Enc. ${s.supervisor_name}` : ''}
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
