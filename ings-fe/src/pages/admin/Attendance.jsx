import { useCallback, useState } from 'react'
import { FiMaximize2, FiUsers } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import SessionQrPresenter from '../../components/attendance/SessionQrPresenter'
import SessionStudentList from '../../components/attendance/SessionStudentList'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchAttendanceSessions,
  fetchAttendanceSessionQr,
  closeAttendanceSession,
  fetchSessionSummary,
  seedSessionRoster,
  fetchSessionRoster,
  addSessionStudents,
  removeSessionStudents,
  forceSessionBadge,
  fetchAttendanceDashboardStats,
} from '../../api/faculty'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export default function AdminAttendance() {
  const { showToast } = useToast()
  const [sessionDate, setSessionDate] = useState(todayIso())
  const [activeSession, setActiveSession] = useState(null)
  const [qrData, setQrData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [rosterSession, setRosterSession] = useState(null)
  const [roster, setRoster] = useState(null)
  const [selectedAvailable, setSelectedAvailable] = useState([])
  const [forceIds, setForceIds] = useState([])
  const [forceMotif, setForceMotif] = useState('')
  const [rosterLoading, setRosterLoading] = useState(false)
  const [forcing, setForcing] = useState(false)
  const [rosterFromQr, setRosterFromQr] = useState(false)
  const [rosterReturnSession, setRosterReturnSession] = useState(null)

  const { data: sessions, loading, error, reload } = useFetch(
    () => fetchAttendanceSessions({ session_date: sessionDate, is_active: true }),
    [sessionDate],
  )
  const { data: stats } = useFetch(
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
      /* ignore poll errors */
    }
  }, [activeSession])

  const openSession = async (session) => {
    setActiveSession(session)
    try {
      const [qr, sum] = await Promise.all([
        fetchAttendanceSessionQr(session.id),
        fetchSessionSummary(session.schedule, session.session_date),
      ])
      setQrData(qr)
      setSummary(sum)
    } catch (err) {
      showToast(err.message || 'Impossible de charger le QR', 'danger')
      setActiveSession(null)
    }
  }

  const handleClose = async () => {
    if (!activeSession) return
    try {
      await closeAttendanceSession(activeSession.id)
      showToast('Séance fermée manuellement', 'info')
      setActiveSession(null)
      setQrData(null)
      reload()
    } catch (err) {
      showToast(err.message || 'Erreur', 'danger')
    }
  }

  const handleSeedRoster = async (session) => {
    try {
      const res = await seedSessionRoster(session.id)
      showToast(res.message || 'Étudiants affectés', 'success')
      reload()
      if (rosterSession?.id === session.id) setRoster(res)
    } catch (err) {
      showToast(err.message || 'Affectation impossible', 'danger')
    }
  }

  const openRoster = async (session, { fromQr = false } = {}) => {
    setRosterFromQr(fromQr)
    setRosterReturnSession(fromQr ? session : null)
    setRosterSession(session)
    setRosterLoading(true)
    setSelectedAvailable([])
    setForceIds([])
    setForceMotif('')
    try {
      setRoster(await fetchSessionRoster(session.id))
    } catch (err) {
      showToast(err.message || 'Impossible de charger la liste', 'danger')
      setRosterSession(null)
      setRosterFromQr(false)
      setRosterReturnSession(null)
    } finally {
      setRosterLoading(false)
    }
  }

  const openStudentListFromQr = () => {
    if (!activeSession) return
    const session = activeSession
    setActiveSession(null)
    setQrData(null)
    setSummary(null)
    openRoster(session, { fromQr: true })
  }

  const backToQrFromRoster = () => {
    const session = rosterReturnSession || rosterSession
    setRosterSession(null)
    setRoster(null)
    setSelectedAvailable([])
    setForceIds([])
    setRosterFromQr(false)
    setRosterReturnSession(null)
    if (session) openSession(session)
  }

  const handleForceBadge = async () => {
    if (!rosterSession || !forceIds.length) return
    if (!forceMotif.trim()) {
      showToast('Indiquez un motif pour le forçage', 'warning')
      return
    }
    setForcing(true)
    try {
      const res = await forceSessionBadge(rosterSession.id, forceIds, { motif: forceMotif.trim() })
      showToast(res.message || 'Badgeage forcé', 'success')
      setForceIds([])
      setForceMotif('')
      setRoster(await fetchSessionRoster(rosterSession.id))
      reload()
      if (activeSession?.id === rosterSession.id) refreshQr()
    } catch (err) {
      showToast(err.message || 'Forçage impossible', 'danger')
    } finally {
      setForcing(false)
    }
  }

  const handleAddSelected = async () => {
    if (!rosterSession || !selectedAvailable.length) return
    try {
      const res = await addSessionStudents(rosterSession.id, selectedAvailable)
      showToast(res.message || 'Ajoutés', 'success')
      setRoster(res)
      setSelectedAvailable([])
      reload()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  const handleRemove = async (studentId) => {
    if (!rosterSession) return
    try {
      const res = await removeSessionStudents(rosterSession.id, { studentIds: [studentId] })
      showToast(res.message || 'Retiré', 'success')
      setRoster(res)
      reload()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  return (
    <>
      <PageHeader
        title="Badgeage — QR séances"
        subtitle="Présentez le QR aux étudiants (vidéoprojecteur) · affectation auto · contrôle live"
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold text-primary">{stats?.sessions_open ?? '—'}</div>
            <div className="small text-muted">Séances ouvertes</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{stats?.present ?? '—'}</div>
            <div className="small text-muted">Présents</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{stats?.attendance_rate != null ? `${stats.attendance_rate}%` : '—'}</div>
            <div className="small text-muted">Taux de présence</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card-injs p-3 text-center">
            <div className="fs-4 fw-bold">{stats?.teachers_badged ?? '—'}</div>
            <div className="small text-muted">Formateurs badgés</div>
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
            <button type="button" className="btn btn-injs-secondary w-100" onClick={reload}>Actualiser</button>
          </div>
        </div>
        <p className="small text-muted mb-0 mt-2">
          Les séances s&apos;ouvrent automatiquement depuis l&apos;EDT. Affichez le QR en plein écran pour que les étudiants scannent.
        </p>
      </div>

      <h6 className="fw-bold mb-3">Séances du {sessionDate}</h6>
      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
      {error && <div className="alert alert-danger">{error}</div>}
      {!loading && sessions?.length === 0 && (
        <div className="alert alert-info">Aucun cours prévu ce jour, ou séances fermées.</div>
      )}

      {sessions?.map((s) => (
        <div key={s.id} className="card-injs p-4 mb-3">
          <div className="d-flex justify-content-between flex-wrap gap-2">
            <div>
              <code className="me-2">{s.course_code}</code>
              <strong>{s.course_name}</strong>
              <div className="text-muted small mt-1">
                {s.day_display} {s.session_date} — {String(s.start_time).slice(0, 5)}–{String(s.end_time).slice(0, 5)}
                {(s.room_code || s.room_name) && ` — ${[s.room_code, s.room_name].filter(Boolean).join(' ')}`}
                {s.teacher_name && ` — ${s.teacher_name}`}
                {s.promotion_name && ` — ${s.promotion_name}`}
              </div>
              <div className="small mt-1">
                <span className="grade-badge grade-valid me-2">QR prêt</span>
                {s.teacher_checked_in && <span className="badge bg-success me-2">Formateur badgé</span>}
                <span className="text-muted">{s.roster_count ?? 0} étudiant(s) · {s.present_count} présent(s)</span>
              </div>
            </div>
            <div className="d-flex flex-wrap gap-2 align-items-start">
              <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => handleSeedRoster(s)}>
                Auto-affectation
              </button>
              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => openRoster(s)}>
                <FiUsers className="me-1" /> Liste
              </button>
              <button type="button" className="btn btn-injs-primary btn-sm" onClick={() => openSession(s)}>
                <FiMaximize2 className="me-1" /> Présenter QR
              </button>
            </div>
          </div>
        </div>
      ))}

      <Modal
        show={!!activeSession}
        onClose={() => { setActiveSession(null); setQrData(null); setSummary(null) }}
        title="Présentation QR — badgeage étudiants"
        size="xl"
        footer={
          <>
            <button type="button" className="btn btn-outline-danger" onClick={handleClose}>Fermer la séance</button>
            <button type="button" className="btn btn-injs-secondary" onClick={refreshQr}>Actualiser</button>
          </>
        }
      >
        <SessionQrPresenter
          qrData={qrData}
          summary={summary}
          onRefresh={refreshQr}
          onOpenStudentList={openStudentListFromQr}
        />
      </Modal>

      <Modal
        show={!!rosterSession}
        onClose={() => {
          setRosterSession(null)
          setRoster(null)
          setSelectedAvailable([])
          setForceIds([])
          setRosterFromQr(false)
          setRosterReturnSession(null)
        }}
        title={rosterSession ? `Liste des étudiants — ${rosterSession.course_code}` : ''}
        size="lg"
        footer={
          <>
            {rosterFromQr && (
              <button type="button" className="btn btn-outline-primary" onClick={backToQrFromRoster}>
                Retour au QR
              </button>
            )}
            <button type="button" className="btn btn-outline-primary" onClick={() => rosterSession && handleSeedRoster(rosterSession)}>
              Auto — promotion
            </button>
            <button type="button" className="btn btn-injs-primary" disabled={!selectedAvailable.length} onClick={handleAddSelected}>
              Ajouter ({selectedAvailable.length})
            </button>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setRosterSession(null)}>Fermer</button>
          </>
        }
      >
        {rosterLoading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}
        {roster && (
          <div className="row g-3">
            <div className="col-12">
              <SessionStudentList
                roster={roster}
                allowForce
                forceMotif={forceMotif}
                onForceMotifChange={setForceMotif}
                forceIds={forceIds}
                onForceIdsChange={setForceIds}
                onForceBadge={handleForceBadge}
                forcing={forcing}
                onRemove={handleRemove}
                sessionLabel={rosterSession
                  ? `${rosterSession.course_code} ${rosterSession.course_name || ''} — ${rosterSession.session_date || ''}`.trim()
                  : ''}
                exportFilename={rosterSession
                  ? `presences_${rosterSession.course_code}_${rosterSession.session_date || 'seance'}`
                  : 'liste_etudiants_seance'}
              />
            </div>
            <div className="col-12">
              <h6 className="fw-bold">Disponibles ({roster.available?.length || 0})</h6>
              <ul className="list-group list-group-flush" style={{ maxHeight: 200, overflow: 'auto' }}>
                {(roster.available || []).map((s) => (
                  <li key={s.student_id} className="list-group-item px-0 py-1">
                    <label className="small d-flex align-items-center gap-2 mb-0">
                      <input
                        type="checkbox"
                        checked={selectedAvailable.includes(s.student_id)}
                        onChange={(e) => {
                          setSelectedAvailable((prev) => (
                            e.target.checked ? [...prev, s.student_id] : prev.filter((id) => id !== s.student_id)
                          ))
                        }}
                      />
                      <code>{s.matricule}</code> {s.name}
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </Modal>
    </>
  )
}
