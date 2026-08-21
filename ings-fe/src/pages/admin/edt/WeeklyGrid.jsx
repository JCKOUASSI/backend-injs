import { useMemo, useState } from 'react'
import { FiAlertTriangle, FiRefreshCw, FiZap } from 'react-icons/fi'
import Modal from '../../../components/common/Modal'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import {
  fetchScheduleGrid,
  fetchScheduleConflicts,
  generateSchedule,
  createSchedule,
  deleteSchedule,
  autoAssignRoom,
  fetchAssignments,
  createAssignment,
  fetchTeachers,
  fetchScheduleRoster,
  seedScheduleRoster,
  addScheduleStudents,
  removeScheduleStudents,
} from '../../../api/faculty'
import { fetchCourses, fetchPromotions, fetchAcademicYears } from '../../../api/academics'

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

const EMPTY_ASSIGN = { teacher: '', supervisor: '', course: '', academic_year: '', promotion: '' }
const EMPTY_SLOT = {
  assignment: '',
  day_of_week: 0,
  start_time: '08:00',
  end_time: '10:00',
  auto_room: true,
}

const KIND_COLORS = [
  '#3349A1', '#F58220', '#198754', '#6f42c1', '#0dcaf0', '#dc3545', '#20c997', '#fd7e14',
]

function colorForCode(code = '') {
  let h = 0
  for (let i = 0; i < code.length; i += 1) h = (h + code.charCodeAt(i) * (i + 1)) % KIND_COLORS.length
  return KIND_COLORS[h]
}

export default function WeeklyGrid() {
  const { showToast } = useToast()
  const [promotion, setPromotion] = useState('')
  const [year, setYear] = useState('')
  const [teacher, setTeacher] = useState('')

  const gridParams = useMemo(() => ({
    promotion: promotion || undefined,
    academic_year: year || undefined,
    teacher: teacher || undefined,
  }), [promotion, year, teacher])

  const { data: grid, loading, error, reload } = useFetch(
    () => fetchScheduleGrid(gridParams),
    [gridParams.promotion, gridParams.academic_year, gridParams.teacher],
  )
  const { data: conflictsData, reload: reloadConflicts } = useFetch(
    () => fetchScheduleConflicts(gridParams),
    [gridParams.promotion, gridParams.academic_year, gridParams.teacher],
  )
  const { data: assignments, reload: reloadAssign } = useFetch(() => fetchAssignments(), [])
  const { data: teachersData } = useFetch(() => fetchTeachers({ page_size: 200 }), [])
  const { data: courses } = useFetch(() => fetchCourses(), [])
  const { data: promotions } = useFetch(() => fetchPromotions(), [])
  const { data: years } = useFetch(() => fetchAcademicYears(), [])

  const teachers = teachersData?.results || []
  const slots = grid?.schedules || []
  const conflicts = conflictsData?.results || []

  const [showAssign, setShowAssign] = useState(false)
  const [showSlot, setShowSlot] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [selected, setSelected] = useState(null)
  const [assignForm, setAssignForm] = useState(EMPTY_ASSIGN)
  const [slotForm, setSlotForm] = useState(EMPTY_SLOT)
  const [genForm, setGenForm] = useState({
    replace_existing: false,
    dry_run: false,
    max_sessions_per_day: 3,
    auto_seed_roster: true,
    seed_weeks: 1,
    auto_assign_teachers: true,
    generate_all: false,
    open_sessions: true,
  })
  const [saving, setSaving] = useState(false)
  const [rosterDate, setRosterDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [roster, setRoster] = useState(null)
  const [rosterLoading, setRosterLoading] = useState(false)
  const [selectedAvailable, setSelectedAvailable] = useState([])

  const cellMap = useMemo(() => {
    const map = {}
    for (const s of slots) {
      const key = `${s.day_of_week}|${s.start_time}`
      if (!map[key]) map[key] = []
      map[key].push(s)
    }
    return map
  }, [slots])

  const refreshAll = () => {
    reload()
    reloadConflicts()
  }

  const handleCreateAssign = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      await createAssignment({
        ...assignForm,
        supervisor: assignForm.supervisor || null,
        is_primary: true,
      })
      showToast('Affectation créée', 'success')
      setShowAssign(false)
      setAssignForm(EMPTY_ASSIGN)
      reloadAssign()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleCreateSlot = async (ev) => {
    ev.preventDefault()
    setSaving(true)
    try {
      const created = await createSchedule({
        assignment: slotForm.assignment,
        day_of_week: Number(slotForm.day_of_week),
        start_time: `${slotForm.start_time}:00`.slice(0, 8),
        end_time: `${slotForm.end_time}:00`.slice(0, 8),
        room: null,
        is_active: true,
      })
      if (slotForm.auto_room) {
        try {
          await autoAssignRoom(created.id)
        } catch (e) {
          showToast(`Créneau créé — salle : ${e.message}`, 'warning')
          refreshAll()
          setShowSlot(false)
          return
        }
      }
      showToast('Créneau ajouté', 'success')
      setShowSlot(false)
      setSlotForm(EMPTY_SLOT)
      refreshAll()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerate = async (dryRun = false) => {
    if (!year && !currentYear) {
      showToast('Sélectionnez une année académique', 'warning')
      return
    }
    if (!genForm.generate_all && !promotion) {
      showToast('Sélectionnez une promotion, ou cochez « toutes les promotions »', 'warning')
      return
    }
    setSaving(true)
    try {
      const res = await generateSchedule({
        promotion: genForm.generate_all ? undefined : promotion,
        academic_year: year || currentYear?.id,
        generate_all: genForm.generate_all,
        replace_existing: genForm.replace_existing,
        max_sessions_per_day: genForm.max_sessions_per_day,
        dry_run: dryRun,
        auto_seed_roster: genForm.auto_seed_roster,
        auto_assign_teachers: genForm.auto_assign_teachers,
        open_sessions: genForm.open_sessions,
        seed_weeks: genForm.seed_weeks,
      })
      let msg = dryRun
        ? `Prévisualisation : ${res.created} créneau(x), ${res.failures?.length || 0} échec(s)`
        : `Génération : ${res.created} créneau(x) créés`
      if (res.assignments_created) {
        msg += ` — ${res.assignments_created} affectation(s) formateur/encadrant`
      }
      if (!dryRun && res.roster) {
        msg += ` — ${res.roster.attendances_created} affectation(s) étudiant(s)`
      }
      if (!dryRun && res.sessions?.sessions_opened) {
        msg += ` — ${res.sessions.sessions_opened} séance(s) de présence`
      }
      if (res.failed_promotions) {
        msg += ` — ${res.failed_promotions} promotion(s) en échec`
      }
      showToast(msg, res.failures?.length || res.failed_promotions ? 'warning' : 'success')
      if (!dryRun) {
        setShowGenerate(false)
        refreshAll()
      }
    } catch (err) {
      showToast(err.message || 'Génération impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (slot) => {
    if (!window.confirm(`Supprimer ${slot.course_code} (${slot.day_display} ${slot.start_time}) ?`)) return
    try {
      await deleteSchedule(slot.id)
      showToast('Créneau archivé', 'success')
      setSelected(null)
      refreshAll()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  const handleAutoRoom = async (slot) => {
    try {
      const res = await autoAssignRoom(slot.id)
      showToast(res.message || 'Salle affectée', 'success')
      refreshAll()
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  const loadRoster = async (slot, date = rosterDate) => {
    if (!slot?.id) return
    setRosterLoading(true)
    try {
      const data = await fetchScheduleRoster(slot.id, date)
      setRoster(data)
      setSelectedAvailable([])
    } catch (err) {
      showToast(err.message || 'Impossible de charger le roster', 'danger')
      setRoster(null)
    } finally {
      setRosterLoading(false)
    }
  }

  const openSlot = (slot) => {
    setSelected(slot)
    setRoster(null)
    loadRoster(slot, rosterDate)
  }

  const handleSeedRoster = async () => {
    if (!selected) return
    try {
      const res = await seedScheduleRoster(selected.id, { date: rosterDate })
      showToast(res.message || 'Étudiants affectés', 'success')
      setRoster(res)
      setSelectedAvailable([])
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  const handleAddSelected = async () => {
    if (!selected || !selectedAvailable.length) return
    try {
      const res = await addScheduleStudents(selected.id, selectedAvailable, { date: rosterDate })
      showToast(res.message || 'Ajoutés', 'success')
      setRoster(res)
      setSelectedAvailable([])
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  const handleRemoveStudent = async (studentId) => {
    if (!selected) return
    try {
      const res = await removeScheduleStudents(selected.id, {
        studentIds: [studentId],
        date: rosterDate,
      })
      showToast(res.message || 'Retiré', 'success')
      setRoster(res)
    } catch (err) {
      showToast(err.message || 'Échec', 'danger')
    }
  }

  // Préremplir année / promo si dispo
  const currentYear = (years || []).find((y) => y.is_current) || (years || [])[0]

  return (
    <>
      <div className="d-flex flex-wrap justify-content-end gap-2 mb-3">
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={refreshAll}>
              <FiRefreshCw className="me-1" /> Actualiser
            </button>
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => setShowAssign(true)}>
              + Affectation
            </button>
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => setShowSlot(true)}>
              + Créneau
            </button>
            <button
              type="button"
              className="btn btn-injs-primary btn-sm"
              onClick={() => {
                setGenForm((f) => ({
                  ...f,
                }))
                if (!year && currentYear) setYear(currentYear.id)
                setShowGenerate(true)
              }}
            >
              <FiZap className="me-1" /> Générer la grille hebdo
            </button>
      </div>

      <div className="card-injs p-3 mb-3">
        <div className="row g-2 align-items-end">
          <div className="col-md-3">
            <label className="form-label small mb-1">Promotion</label>
            <select className="form-select" value={promotion} onChange={(e) => setPromotion(e.target.value)}>
              <option value="">Toutes</option>
              {(promotions || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Année académique</label>
            <select className="form-select" value={year} onChange={(e) => setYear(e.target.value)}>
              <option value="">Toutes</option>
              {(years || []).map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label small mb-1">Enseignant</label>
            <select className="form-select" value={teacher} onChange={(e) => setTeacher(e.target.value)}>
              <option value="">Tous</option>
              {teachers.map((t) => <option key={t.id} value={t.id}>{t.nom}</option>)}
            </select>
          </div>
          <div className="col-md-3 small text-muted">
            {slots.length} créneau(x) · {conflictsData?.errors || 0} conflit(s) · {conflictsData?.warnings || 0} alerte(s)
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <div className="text-center py-3"><div className="spinner-border spinner-border-sm text-primary" /></div>}

      {/* Grille hebdo */}
      <div className="card-injs edt-grid-wrap mb-4">
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
                  {DAYS.map((d) => {
                    const items = cellMap[`${d.value}|${row.start}`] || []
                    return (
                      <td key={`${d.value}-${row.start}`} className="edt-cell">
                        {items.map((s) => (
                          <button
                            key={s.id}
                            type="button"
                            className="edt-block"
                            style={{ borderLeftColor: colorForCode(s.course_code) }}
                            onClick={() => openSlot(s)}
                          >
                            <div className="edt-block-code">
                              {s.course_code}
                              {s.session_kind && (
                                <span className="badge bg-light text-dark ms-1" style={{ fontSize: '0.6rem' }}>
                                  {(s.session_kind_display || s.session_kind).toUpperCase()}
                                </span>
                              )}
                            </div>
                            <div className="edt-block-title">{s.course_name}</div>
                            <div className="edt-block-meta">
                              {s.room_code || 'Sans salle'} · {s.teacher_name?.split(' ').slice(-1)[0]}
                              {s.supervisor_name ? ` · Enc. ${s.supervisor_name.split(' ').slice(-1)[0]}` : ''}
                              {typeof s.effectif === 'number' ? ` · ${s.effectif} étud.` : ''}
                            </div>
                          </button>
                        ))}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Conflits */}
      <div className="card-injs p-3">
        <h6 className="fw-bold mb-3">
          <FiAlertTriangle className="me-2 text-warning" />
          Contrôle des conflits
        </h6>
        {!conflicts.length && (
          <p className="text-success small mb-0">Aucun conflit détecté sur le filtre actuel.</p>
        )}
        <ul className="list-unstyled mb-0">
          {conflicts.map((c, idx) => (
            <li key={idx} className={`small mb-2 ${c.severity === 'error' ? 'text-danger' : 'text-warning'}`}>
              <span className="badge me-2 bg-secondary">{c.type}</span>
              {c.message}
            </li>
          ))}
        </ul>
      </div>

      {/* Détail créneau + roster */}
      <Modal
        show={!!selected}
        onClose={() => { setSelected(null); setRoster(null) }}
        title={selected ? `${selected.course_code} — ${selected.day_display}` : ''}
        size="lg"
        footer={
          selected && (
            <>
              <button type="button" className="btn btn-outline-info btn-sm" onClick={() => handleAutoRoom(selected)}>
                Auto-salle
              </button>
              <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => handleDelete(selected)}>
                Supprimer
              </button>
              <button type="button" className="btn btn-outline-secondary" onClick={() => { setSelected(null); setRoster(null) }}>Fermer</button>
            </>
          )
        }
      >
        {selected && (
          <>
            <dl className="detail-view mb-3">
              <div className="detail-row"><dt>Cours</dt><dd>{selected.course_name} {selected.session_kind_display ? `(${selected.session_kind_display})` : ''}</dd></div>
              <div className="detail-row"><dt>Horaire</dt><dd>{selected.start_time}–{selected.end_time}</dd></div>
              <div className="detail-row"><dt>Formateur</dt><dd>{selected.teacher_name}</dd></div>
              <div className="detail-row"><dt>Encadrant</dt><dd>{selected.supervisor_name || '—'}</dd></div>
              <div className="detail-row"><dt>Promotion</dt><dd>{selected.promotion_name} ({selected.effectif ?? '—'} étudiants)</dd></div>
              <div className="detail-row"><dt>Salle</dt><dd>{selected.room_code ? `${selected.room_code} — ${selected.room_name}` : 'Non affectée'}</dd></div>
            </dl>

            <div className="border-top pt-3">
              <div className="d-flex flex-wrap gap-2 align-items-end mb-3">
                <div>
                  <label className="form-label small mb-1">Date de séance</label>
                  <input
                    type="date"
                    className="form-control form-control-sm"
                    value={rosterDate}
                    onChange={(e) => {
                      setRosterDate(e.target.value)
                      loadRoster(selected, e.target.value)
                    }}
                  />
                </div>
                <button type="button" className="btn btn-injs-primary btn-sm" onClick={handleSeedRoster}>
                  Auto — toute la promotion
                </button>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm"
                  disabled={!selectedAvailable.length}
                  onClick={handleAddSelected}
                >
                  Ajouter sélection ({selectedAvailable.length})
                </button>
              </div>

              {rosterLoading && <div className="spinner-border spinner-border-sm text-primary" />}
              {roster && (
                <div className="row g-3">
                  <div className="col-md-6">
                    <h6 className="fw-bold">Dans la salle ({roster.roster_count})</h6>
                    {!roster.assigned?.length && <p className="small text-muted">Aucun étudiant affecté.</p>}
                    <ul className="list-group list-group-flush" style={{ maxHeight: 220, overflow: 'auto' }}>
                      {(roster.assigned || []).map((a) => (
                        <li key={a.attendance_id} className="list-group-item d-flex justify-content-between align-items-center px-0 py-1">
                          <span className="small">
                            <code className="me-1">{a.matricule}</code>{a.name}
                          </span>
                          <button type="button" className="btn btn-link btn-sm text-danger p-0" onClick={() => handleRemoveStudent(a.student_id)}>
                            Retirer
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="col-md-6">
                    <h6 className="fw-bold">Disponibles ({roster.available?.length || 0})</h6>
                    {!roster.available?.length && <p className="small text-muted">Tous les étudiants de la promo sont déjà affectés.</p>}
                    <ul className="list-group list-group-flush" style={{ maxHeight: 220, overflow: 'auto' }}>
                      {(roster.available || []).map((s) => (
                        <li key={s.student_id} className="list-group-item px-0 py-1">
                          <label className="small d-flex align-items-center gap-2 mb-0">
                            <input
                              type="checkbox"
                              checked={selectedAvailable.includes(s.student_id)}
                              onChange={(e) => {
                                setSelectedAvailable((prev) => (
                                  e.target.checked
                                    ? [...prev, s.student_id]
                                    : prev.filter((id) => id !== s.student_id)
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
            </div>
          </>
        )}
      </Modal>

      {/* Affectation */}
      <Modal
        show={showAssign}
        onClose={() => setShowAssign(false)}
        title="Affectation formateur / encadrant ↔ cours ↔ promotion"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowAssign(false)}>Annuler</button>
            <button type="submit" form="edt-assign" className="btn btn-injs-primary" disabled={saving}>{saving ? '…' : 'Créer'}</button>
          </>
        }
      >
        <form id="edt-assign" onSubmit={handleCreateAssign} className="row g-3">
          <div className="col-12">
            <label className="form-label">Enseignant *</label>
            <select className="form-select" required value={assignForm.teacher} onChange={(e) => setAssignForm({ ...assignForm, teacher: e.target.value })}>
              <option value="">—</option>
              {teachers.map((t) => <option key={t.id} value={t.id}>{t.nom}</option>)}
            </select>
          </div>
          <div className="col-12">
            <label className="form-label">Encadrant (TP / séances pratiques)</label>
            <select className="form-select" value={assignForm.supervisor} onChange={(e) => setAssignForm({ ...assignForm, supervisor: e.target.value })}>
              <option value="">Aucun</option>
              {teachers.filter((t) => t.id !== assignForm.teacher).map((t) => <option key={t.id} value={t.id}>{t.nom}</option>)}
            </select>
          </div>
          <div className="col-12">
            <label className="form-label">ECUE *</label>
            <select className="form-select" required value={assignForm.course} onChange={(e) => setAssignForm({ ...assignForm, course: e.target.value })}>
              <option value="">—</option>
              {(courses || []).map((c) => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label">Année *</label>
            <select className="form-select" required value={assignForm.academic_year} onChange={(e) => setAssignForm({ ...assignForm, academic_year: e.target.value })}>
              <option value="">—</option>
              {(years || []).map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label">Promotion *</label>
            <select className="form-select" required value={assignForm.promotion} onChange={(e) => setAssignForm({ ...assignForm, promotion: e.target.value })}>
              <option value="">—</option>
              {(promotions || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        </form>
      </Modal>

      {/* Créneau manuel */}
      <Modal
        show={showSlot}
        onClose={() => setShowSlot(false)}
        title="Ajouter un créneau"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowSlot(false)}>Annuler</button>
            <button type="submit" form="edt-slot" className="btn btn-injs-primary" disabled={saving}>{saving ? '…' : 'Ajouter'}</button>
          </>
        }
      >
        <form id="edt-slot" onSubmit={handleCreateSlot} className="row g-3">
          <div className="col-12">
            <label className="form-label">Affectation *</label>
            <select className="form-select" required value={slotForm.assignment} onChange={(e) => setSlotForm({ ...slotForm, assignment: e.target.value })}>
              <option value="">—</option>
              {(assignments || []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.course_code} — {a.teacher_name} — {a.promotion_name}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Jour</label>
            <select className="form-select" value={slotForm.day_of_week} onChange={(e) => setSlotForm({ ...slotForm, day_of_week: e.target.value })}>
              {DAYS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Début</label>
            <select className="form-select" value={slotForm.start_time} onChange={(e) => {
              const row = TIME_ROWS.find((r) => r.start === e.target.value)
              setSlotForm({ ...slotForm, start_time: e.target.value, end_time: row?.end || slotForm.end_time })
            }}>
              {TIME_ROWS.map((r) => <option key={r.start} value={r.start}>{r.start}</option>)}
            </select>
          </div>
          <div className="col-md-4 d-flex align-items-end">
            <div className="form-check">
              <input className="form-check-input" type="checkbox" id="autoR" checked={slotForm.auto_room} onChange={(e) => setSlotForm({ ...slotForm, auto_room: e.target.checked })} />
              <label className="form-check-label" htmlFor="autoR">Auto-salle</label>
            </div>
          </div>
        </form>
      </Modal>

      {/* Génération */}
      <Modal
        show={showGenerate}
        onClose={() => setShowGenerate(false)}
        title="Génération automatique de l'EDT"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowGenerate(false)}>Fermer</button>
            <button type="button" className="btn btn-outline-primary" disabled={saving} onClick={() => handleGenerate(true)}>Prévisualiser</button>
            <button type="button" className="btn btn-injs-primary" disabled={saving} onClick={() => handleGenerate(false)}>
              {saving ? 'Génération…' : 'Générer'}
            </button>
          </>
        }
      >
        <p className="small text-muted">
          Génère l&apos;EDT à partir de la maquette (volumes CM/TD/TP semestriels → créneaux hebdo),
          affecte formateurs et encadrants (TP), place les salles et ouvre les séances de présence.
        </p>
        <div className="row g-3">
          <div className="col-12">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="genAll"
                checked={genForm.generate_all}
                onChange={(e) => setGenForm({ ...genForm, generate_all: e.target.checked })}
              />
              <label className="form-check-label" htmlFor="genAll">
                Toutes les promotions actives
              </label>
            </div>
          </div>
          <div className="col-md-6">
            <label className="form-label">Promotion {genForm.generate_all ? '' : '*'}</label>
            <select
              className="form-select"
              value={promotion}
              disabled={genForm.generate_all}
              onChange={(e) => setPromotion(e.target.value)}
            >
              <option value="">—</option>
              {(promotions || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label">Année *</label>
            <select className="form-select" value={year || currentYear?.id || ''} onChange={(e) => setYear(e.target.value)}>
              <option value="">—</option>
              {(years || []).map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label">Max créneaux / jour</label>
            <input
              type="number"
              min={1}
              max={6}
              className="form-control"
              value={genForm.max_sessions_per_day}
              onChange={(e) => setGenForm({ ...genForm, max_sessions_per_day: Number(e.target.value) })}
            />
          </div>
          <div className="col-12">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="autoTeachers"
                checked={genForm.auto_assign_teachers}
                onChange={(e) => setGenForm({ ...genForm, auto_assign_teachers: e.target.checked })}
              />
              <label className="form-check-label" htmlFor="autoTeachers">
                Créer automatiquement les affectations formateur / encadrant (maquette)
              </label>
            </div>
          </div>
          <div className="col-12">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="openSess"
                checked={genForm.open_sessions}
                onChange={(e) => setGenForm({ ...genForm, open_sessions: e.target.checked })}
              />
              <label className="form-check-label" htmlFor="openSess">
                Ouvrir les séances de présence (étudiants, formateurs, encadrants)
              </label>
            </div>
          </div>
          <div className="col-12">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="replace"
                checked={genForm.replace_existing}
                onChange={(e) => setGenForm({ ...genForm, replace_existing: e.target.checked })}
              />
              <label className="form-check-label" htmlFor="replace">
                Remplacer l&apos;EDT existant de cette promotion
              </label>
            </div>
          </div>
          <div className="col-12">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="autoSeed"
                checked={genForm.auto_seed_roster}
                onChange={(e) => setGenForm({ ...genForm, auto_seed_roster: e.target.checked })}
              />
              <label className="form-check-label" htmlFor="autoSeed">
                Affecter automatiquement les étudiants de la promotion aux créneaux générés
              </label>
            </div>
          </div>
          {genForm.auto_seed_roster && (
            <div className="col-md-6">
              <label className="form-label">Semaines à pré-remplir</label>
              <input
                type="number"
                min={1}
                max={8}
                className="form-control"
                value={genForm.seed_weeks}
                onChange={(e) => setGenForm({ ...genForm, seed_weeks: Number(e.target.value) })}
              />
            </div>
          )}
        </div>
        <p className="small text-warning mt-3 mb-0">
          Les volumes CM/TD/TP de la maquette sont convertis en créneaux hebdomadaires (semestre 15 semaines).
          Un encadrant distinct est affecté aux séances TP lorsqu&apos;un second enseignant est disponible.
        </p>
      </Modal>
    </>
  )
}
