import { useCallback, useState } from 'react'
import { FiMaximize2 } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import SessionQrPresenter from '../../components/attendance/SessionQrPresenter'
import SessionStudentList from '../../components/attendance/SessionStudentList'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchAttendanceSessions,
  fetchAttendanceSessionQr,
  fetchSessionSummary,
  fetchSessionRoster,
  checkInSession,
  fetchAttendanceDashboardStats,
} from '../../api/faculty'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export default function ProfAttendance() {
  const { showToast } = useToast()
  const [sessionDate, setSessionDate] = useState(todayIso())
  const [activeSession, setActiveSession] = useState(null)
  const [qrData, setQrData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [badging, setBadging] = useState(false)
  const [rosterSession, setRosterSession] = useState(null)
  const [roster, setRoster] = useState(null)
  const [rosterLoading, setRosterLoading] = useState(false)
  const [rosterReturnSession, setRosterReturnSession] = useState(null)

  const { data: sessions, loading, error, reload } = useFetch(
    () => fetchAttendanceSessions({ session_date: sessionDate, is_active: true }),
    [sessionDate],
  )
  const { data: stats, reload: reloadStats } = useFetch(
    () => fetchAttendanceDashboardStats({ date: sessionDate }),
    [sessionDate],
  )

  const refreshQr = useCallback(async () => {
    if (!activeSession) return
    try {
      const [qr, sum] = await Promise.all([
        fetchAttendanceSessionQr(activeSession.id),
        fetchSessionSummary(activeSession.schedule, activeSession.session_date),
      ])
      setQrData(qr)
      setSummary(sum)
    } catch {
      /* ignore */
    }
  }, [activeSession])

  const openSession = async (session) => {
    setActiveSession(session)
    setQrData(null)
    setSummary(null)
    try {
      const [qr, sum] = await Promise.all([
        fetchAttendanceSessionQr(session.id),
        fetchSessionSummary(session.schedule, session.session_date),
      ])
      setQrData(qr)
      setSummary(sum)
    } catch (err) {
      showToast(err.message || 'QR non disponible — contactez l\'administration', 'danger')
      setActiveSession(null)
    }
  }

  const openStudentListFromQr = async () => {
    if (!activeSession) return
    const session = activeSession
    setActiveSession(null)
    setQrData(null)
    setSummary(null)
    setRosterReturnSession(session)
    setRosterSession(session)
    setRosterLoading(true)
    try {
      setRoster(await fetchSessionRoster(session.id))
    } catch (err) {
      showToast(err.message || 'Impossible de charger la liste', 'danger')
      setRosterSession(null)
      setRosterReturnSession(null)
    } finally {
      setRosterLoading(false)
    }
  }

  const backToQrFromRoster = () => {
    const session = rosterReturnSession || rosterSession
    setRosterSession(null)
    setRoster(null)
    setRosterReturnSession(null)
    if (session) openSession(session)
  }

  const handleTeacherBadge = async () => {
    const tok = qrData?.payload || qrData?.badge_url
    if (!tok) return
    setBadging(true)
    try {
      const result = await checkInSession(tok)
      showToast(result.message || 'Badgeage enregistré', 'success')
      await refreshQr()
      reload()
      reloadStats()
    } catch (err) {
      showToast(err.message || 'Échec du badgeage', 'danger')
    } finally {
      setBadging(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Présences — Badgeage QR"
        subtitle="Affichez le QR en salle pour que vos étudiants badgeent (même principe SYGEP)"
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{stats?.sessions_open ?? '—'}</div>
            <div className="small text-muted">Mes séances ouvertes</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{stats?.present ?? '—'}</div>
            <div className="small text-muted">Étudiants présents</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{stats?.attendance_rate != null ? `${stats.attendance_rate}%` : '—'}</div>
            <div className="small text-muted">Taux</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{stats?.teachers_badged ?? '—'}</div>
            <div className="small text-muted">Formateur badgé</div>
          </div>
        </div>
      </div>

      <div className="card-injs p-3 mb-4">
        <div className="row g-2 align-items-end">
          <div className="col-md-4">
            <label className="form-label">Date</label>
            <input type="date" className="form-control" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)} />
          </div>
          <div className="col-md-3">
            <button type="button" className="btn btn-injs-secondary w-100" onClick={() => { reload(); reloadStats() }}>Actualiser</button>
          </div>
        </div>
      </div>

      {loading && <div className="text-center py-4"><div className="spinner-border text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}
      {!loading && sessions?.length === 0 && (
        <div className="alert alert-info">Aucune séance prévue ce jour dans votre emploi du temps.</div>
      )}

      {sessions?.map((s) => (
        <div key={s.id} className="card-injs p-4 mb-3">
          <div className="d-flex justify-content-between flex-wrap gap-2">
            <div>
              <code className="me-2">{s.course_code}</code>
              <strong>{s.course_name}</strong>
              <div className="text-muted small mt-1">
                {s.day_display} — {String(s.start_time).slice(0, 5)}–{String(s.end_time).slice(0, 5)}
                {(s.room_code || s.room_name) && ` — ${[s.room_code, s.room_name].filter(Boolean).join(' ')}`}
                {s.promotion_name && ` — ${s.promotion_name}`}
              </div>
              <div className="small mt-1">
                {s.teacher_checked_in
                  ? <span className="grade-badge grade-valid">Vous avez badgé</span>
                  : <span className="grade-badge grade-pending">Badgeage formateur en attente</span>}
                <span className="text-muted ms-2">{s.present_count} étudiant(s)</span>
              </div>
            </div>
            <button type="button" className="btn btn-injs-primary" onClick={() => openSession(s)}>
              <FiMaximize2 className="me-1" /> Présenter QR
            </button>
          </div>
        </div>
      ))}

      <Modal
        show={!!activeSession}
        onClose={() => { setActiveSession(null); setQrData(null); setSummary(null) }}
        title="Présentation QR — badgeage étudiants"
        size="xl"
        footer={
          <button type="button" className="btn btn-outline-secondary" onClick={() => setActiveSession(null)}>Fermer</button>
        }
      >
        <SessionQrPresenter
          qrData={qrData}
          summary={summary}
          onRefresh={refreshQr}
          onOpenStudentList={openStudentListFromQr}
          showTeacherBadge
          onTeacherBadge={handleTeacherBadge}
          teacherBadging={badging}
        />
      </Modal>

      <Modal
        show={!!rosterSession}
        onClose={() => {
          setRosterSession(null)
          setRoster(null)
          setRosterReturnSession(null)
        }}
        title={rosterSession ? `Liste des étudiants — ${rosterSession.course_code}` : ''}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-primary" onClick={backToQrFromRoster}>
              Retour au QR
            </button>
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => { setRosterSession(null); setRoster(null); setRosterReturnSession(null) }}
            >
              Fermer
            </button>
          </>
        }
      >
        <SessionStudentList
          roster={roster}
          loading={rosterLoading}
          allowForce={false}
          onBackToQr={backToQrFromRoster}
          sessionLabel={rosterSession
            ? `${rosterSession.course_code} ${rosterSession.course_name || ''} — ${rosterSession.session_date || ''}`.trim()
            : ''}
          exportFilename={rosterSession
            ? `presences_${rosterSession.course_code}_${rosterSession.session_date || 'seance'}`
            : 'liste_etudiants_seance'}
        />
      </Modal>
    </>
  )
}
