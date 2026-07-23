import { apiGet, apiPost, apiPatch, apiDelete } from './client'
import { mapTeacher, mapRoom } from './mappers'
import { fetchDepartments } from './academics'
import { createUser, fetchGroups, findUserByEmail, updateUser, uploadUserPhoto, deleteUser } from './users'

const DEFAULT_PASSWORD = 'Change@INJS2026!'

export const TEACHER_GRADES = [
  { value: 'assistant', label: 'Assistant' },
  { value: 'maitre_assistant', label: 'Maître-Assistant' },
  { value: 'maitre_conferences', label: 'Maître de Conférences' },
  { value: 'professeur', label: 'Professeur' },
  { value: 'vacataire', label: 'Vacataire' },
]

function generateEmployeeId(existing = []) {
  const year = new Date().getFullYear().toString().slice(-2)
  const prefix = `ENS${year}`
  const same = existing.filter((id) => String(id).startsWith(prefix))
  return `${prefix}${String(same.length + 1).padStart(3, '0')}`
}

function splitFullName(nom = '') {
  const parts = nom.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return { first_name: '', last_name: '' }
  if (parts.length === 1) return { first_name: parts[0], last_name: parts[0] }
  return { first_name: parts.slice(1).join(' '), last_name: parts[0] }
}

export async function fetchTeachers(params = {}) {
  const data = await apiGet('/faculty/teachers/', { page_size: 100, ...params })
  return {
    count: data.count,
    results: data.results.map(mapTeacher),
  }
}

export async function fetchTeacher(id) {
  const data = await apiGet(`/faculty/teachers/${id}/`)
  return mapTeacher(data)
}

/**
 * Création enseignant : POST /auth/users/ puis POST /faculty/teachers/
 */
export async function createTeacher(payload) {
  const [groups, departments, teachersList] = await Promise.all([
    fetchGroups(),
    fetchDepartments(),
    fetchTeachers(),
  ])

  const enseignantGroup = groups.find((g) => g.profile?.code === 'enseignant' || g.name?.toLowerCase().includes('enseignant'))
  const departmentId = payload.department || departments.results?.[0]?.id
  if (!departmentId) throw new Error('Aucun département configuré.')

  const { first_name, last_name } = payload.first_name
    ? { first_name: payload.first_name, last_name: payload.last_name }
    : splitFullName(payload.nom)

  const email = payload.email?.trim()
  if (!email) throw new Error('Email obligatoire.')

  await createUser({
    email,
    password: payload.password || DEFAULT_PASSWORD,
    first_name,
    last_name,
    phone: payload.tel || payload.phone || '',
    group_ids: enseignantGroup ? [enseignantGroup.id] : [],
    department: departmentId,
  })

  const user = await findUserByEmail(email)
  const employeeId = payload.employee_id || generateEmployeeId(teachersList.results.map((t) => t.employeeId))

  const teacher = await apiPost('/faculty/teachers/', {
    user: user.id,
    employee_id: employeeId,
    department: departmentId,
    grade: payload.grade || 'assistant',
    specialization: payload.specialization || payload.ue || '',
    hire_date: payload.hire_date || null,
    is_active: true,
  })

  return mapTeacher(teacher)
}

export async function updateTeacher(teacherUuid, { teacherPatch = {}, userPatch = {}, photoFile = null } = {}) {
  const current = await apiGet(`/faculty/teachers/${teacherUuid}/`)
  const userId = current.user_detail?.id || current.user

  if (userId && Object.keys(userPatch).length) {
    await updateUser(userId, userPatch)
  }
  if (userId && photoFile) {
    await uploadUserPhoto(userId, photoFile)
  }

  let teacher = current
  if (Object.keys(teacherPatch).length) {
    teacher = await apiPatch(`/faculty/teachers/${teacherUuid}/`, teacherPatch)
  } else {
    teacher = await apiGet(`/faculty/teachers/${teacherUuid}/`)
  }
  return mapTeacher(teacher)
}

export async function deleteTeacher(teacherUuid) {
  const current = await apiGet(`/faculty/teachers/${teacherUuid}/`)
  const userId = current.user_detail?.id || current.user
  await apiDelete(`/faculty/teachers/${teacherUuid}/`)
  if (userId) {
    try {
      await deleteUser(userId)
    } catch {
      try {
        await updateUser(userId, { is_active: false })
      } catch {
        // compte déjà orphelin / non supprimable
      }
    }
  }
  return true
}

export async function fetchTeacherFullDetail(teacherUuid) {
  const teacher = await apiGet(`/faculty/teachers/${teacherUuid}/`)
  const user = teacher.user_detail || {}

  const assignments = await apiGet('/faculty/assignments/', {
    teacher: teacherUuid,
    page_size: 100,
  }).then((r) => r.results)

  const assignmentIds = new Set(assignments.map((a) => a.id))
  const schedules = assignments.length > 0
    ? await apiGet('/faculty/schedules/', { page_size: 200 }).then((r) =>
      r.results.filter((s) => assignmentIds.has(s.assignment)),
    )
    : []

  const courseIds = [...new Set(assignments.map((a) => a.course))]
  const promotionIds = [...new Set(assignments.map((a) => a.promotion))]
  const yearIds = [...new Set(assignments.map((a) => a.academic_year))]

  const [courses, promotions, academicYears] = await Promise.all([
    Promise.all(courseIds.map((id) => apiGet(`/academics/courses/${id}/`).catch(() => null))),
    Promise.all(promotionIds.map((id) => apiGet(`/academics/promotions/${id}/`).catch(() => null))),
    Promise.all(yearIds.map((id) => apiGet(`/academics/academic-years/${id}/`).catch(() => null))),
  ])

  const courseMap = Object.fromEntries(courses.filter(Boolean).map((c) => [c.id, c]))
  const promotionMap = Object.fromEntries(promotions.filter(Boolean).map((p) => [p.id, p]))
  const yearMap = Object.fromEntries(academicYears.filter(Boolean).map((y) => [y.id, y]))

  const ueIds = [...new Set(courses.filter(Boolean).map((c) => c.teaching_unit))]
  const teachingUnits = await Promise.all(
    ueIds.map((id) => apiGet(`/academics/teaching-units/${id}/`).catch(() => null)),
  )
  const ueMap = Object.fromEntries(teachingUnits.filter(Boolean).map((u) => [u.id, u]))

  const schedulesByDay = {}
  for (const s of schedules) {
    const day = s.day_display || `Jour ${s.day_of_week}`
    if (!schedulesByDay[day]) schedulesByDay[day] = []
    schedulesByDay[day].push(s)
  }

  return {
    teacher,
    user,
    assignments,
    schedules,
    schedulesByDay,
    courseMap,
    ueMap,
    promotionMap,
    yearMap,
    mapped: mapTeacher(teacher),
  }
}

export async function fetchSchedules(params = {}) {
  const data = await apiGet('/faculty/schedules/', { page_size: 200, ...params })
  return data.results || []
}

export async function createSchedule(payload) {
  return apiPost('/faculty/schedules/', payload)
}

export async function updateSchedule(id, payload) {
  return apiPatch(`/faculty/schedules/${id}/`, payload)
}

export async function deleteSchedule(id) {
  await apiDelete(`/faculty/schedules/${id}/`)
  return true
}

export async function autoAssignRoom(scheduleId, payload = {}) {
  return apiPost(`/faculty/schedules/${scheduleId}/auto-assign-room/`, payload)
}

export async function fetchScheduleConflicts(params = {}) {
  return apiGet('/faculty/schedules/conflicts/', params)
}

export async function fetchScheduleGrid(params = {}) {
  return apiGet('/faculty/schedules/grid/', params)
}

export async function generateSchedule(payload) {
  return apiPost('/faculty/schedules/generate/', payload)
}

export async function fetchAssignments(params = {}) {
  const data = await apiGet('/faculty/assignments/', { page_size: 200, ...params })
  return data.results || []
}

export async function createAssignment(payload) {
  return apiPost('/faculty/assignments/', payload)
}

export async function deleteAssignment(id) {
  await apiDelete(`/faculty/assignments/${id}/`)
  return true
}

export async function seedSessionRoster(sessionId, payload = {}) {
  return apiPost(`/faculty/attendance-sessions/${sessionId}/seed-roster/`, payload)
}

export async function fetchSessionRoster(sessionId) {
  return apiGet(`/faculty/attendance-sessions/${sessionId}/roster/`)
}

export async function addSessionStudents(sessionId, studentIds, payload = {}) {
  return apiPost(`/faculty/attendance-sessions/${sessionId}/add-students/`, {
    student_ids: studentIds,
    ...payload,
  })
}

export async function removeSessionStudents(sessionId, { studentIds, attendanceIds } = {}) {
  return apiPost(`/faculty/attendance-sessions/${sessionId}/remove-students/`, {
    student_ids: studentIds,
    attendance_ids: attendanceIds,
  })
}

export async function fetchScheduleRoster(scheduleId, date) {
  return apiGet(`/faculty/schedules/${scheduleId}/roster/`, date ? { date } : {})
}

export async function seedScheduleRoster(scheduleId, payload = {}) {
  return apiPost(`/faculty/schedules/${scheduleId}/seed-roster/`, payload)
}

export async function addScheduleStudents(scheduleId, studentIds, payload = {}) {
  return apiPost(`/faculty/schedules/${scheduleId}/add-students/`, {
    student_ids: studentIds,
    ...payload,
  })
}

export async function removeScheduleStudents(scheduleId, { studentIds, attendanceIds, date } = {}) {
  return apiPost(`/faculty/schedules/${scheduleId}/remove-students/`, {
    student_ids: studentIds,
    attendance_ids: attendanceIds,
    date,
  })
}

export async function fetchReservations(params = {}) {
  const data = await apiGet('/faculty/reservations/', { page_size: 100, ...params })
  return { count: data.count, results: data.results || [] }
}

export async function createReservation(payload) {
  return apiPost('/faculty/reservations/', payload)
}

export async function approveReservation(id) {
  return apiPost(`/faculty/reservations/${id}/approve/`)
}

export async function rejectReservation(id, reason = '') {
  return apiPost(`/faculty/reservations/${id}/reject/`, { reason })
}

export async function cancelReservation(id) {
  return apiPost(`/faculty/reservations/${id}/cancel/`)
}

export async function fetchMaintenanceTickets(params = {}) {
  const data = await apiGet('/faculty/maintenance-tickets/', { page_size: 100, ...params })
  return { count: data.count, results: data.results || [] }
}

export async function createMaintenanceTicket(payload) {
  return apiPost('/faculty/maintenance-tickets/', payload)
}

export async function updateMaintenanceTicket(id, payload) {
  return apiPatch(`/faculty/maintenance-tickets/${id}/`, payload)
}

export async function fetchEquipment(params = {}) {
  const data = await apiGet('/faculty/equipment/', { page_size: 200, ...params })
  return { count: data.count, results: data.results || [] }
}

export async function createEquipment(payload) {
  return apiPost('/faculty/equipment/', payload)
}

export async function updateEquipment(id, payload) {
  return apiPatch(`/faculty/equipment/${id}/`, payload)
}

export async function deleteEquipment(id) {
  await apiDelete(`/faculty/equipment/${id}/`)
  return true
}

export async function syncEquipmentRoomTags(roomId = null) {
  return apiPost('/faculty/equipment/sync-room-tags/', roomId ? { room: roomId } : {})
}

export async function fetchRoomsGeo(params = {}) {
  return apiGet('/faculty/rooms/geo/', params)
}

export async function fetchRooms(params = {}) {
  const { page = 1, page_size = 25, ...rest } = params
  const data = await apiGet('/faculty/rooms/', { page, page_size, ...rest })
  return {
    count: data.count ?? 0,
    next: data.next || null,
    previous: data.previous || null,
    page: Number(page),
    pageSize: Number(page_size),
    results: (data.results || []).map(mapRoom),
  }
}

export async function fetchRoom(id) {
  const data = await apiGet(`/faculty/rooms/${id}/`)
  return mapRoom(data)
}

export async function fetchRoomsMeta() {
  return apiGet('/faculty/rooms/meta/')
}

export async function fetchAvailableRooms(params = {}) {
  const data = await apiGet('/faculty/rooms/available/', { page_size: 100, ...params })
  const results = data.results || data
  return Array.isArray(results) ? results.map(mapRoom) : []
}

export async function createRoom(payload) {
  const data = await apiPost('/faculty/rooms/', payload)
  return mapRoom(data)
}

export async function updateRoom(id, payload) {
  const data = await apiPatch(`/faculty/rooms/${id}/`, payload)
  return mapRoom(data)
}

export async function deleteRoom(id) {
  await apiDelete(`/faculty/rooms/${id}/`)
  return true
}

export async function fetchMyTeacherProfile() {
  return apiGet('/faculty/teachers/me/')
}

export async function fetchMyTeacherSchedules(sessionDate) {
  const teacher = await fetchMyTeacherProfile()
  const assignments = await apiGet('/faculty/assignments/', {
    teacher: teacher.id,
    page_size: 100,
  }).then((r) => r.results)

  const assignmentIds = new Set(assignments.map((a) => a.id))
  const allSchedules = await fetchSchedules({ page_size: 200 })
  const teacherSchedules = allSchedules.filter((s) => assignmentIds.has(s.assignment))

  if (!sessionDate) return teacherSchedules

  const djangoDay = toDjangoWeekday(sessionDate)
  if (djangoDay == null) return []
  return teacherSchedules.filter((s) => s.day_of_week === djangoDay)
}

export async function fetchSessionSummary(scheduleId, sessionDate) {
  return apiGet('/faculty/attendances/session-summary/', {
    schedule: scheduleId,
    date: sessionDate,
  })
}

export async function fetchAttendanceSessions(params = {}) {
  const data = await apiGet('/faculty/attendance-sessions/', { page_size: 100, ...params })
  return data.results
}

export async function fetchAttendanceSessionQr(sessionId) {
  return apiGet(`/faculty/attendance-sessions/${sessionId}/qr/`)
}

export async function closeAttendanceSession(sessionId) {
  return apiPost(`/faculty/attendance-sessions/${sessionId}/close/`)
}

export async function checkInSession(sessionToken) {
  return apiPost('/faculty/attendances/check-in/', { session_token: sessionToken })
}

export async function fetchAttendanceDashboardStats(params = {}) {
  return apiGet('/faculty/attendances/dashboard-stats/', params)
}

export async function fetchMyAttendanceHistory() {
  return apiGet('/faculty/attendances/my-history/')
}

export async function forceSessionBadge(sessionId, studentIds, payload = {}) {
  return apiPost(`/faculty/attendance-sessions/${sessionId}/force-badge/`, {
    student_ids: studentIds,
    ...payload,
  })
}

/** Convertit une date ISO en index jour Django (0=Lundi … 5=Samedi). */
export function toDjangoWeekday(dateStr) {
  const d = new Date(`${dateStr}T12:00:00`)
  const jsDay = d.getDay()
  if (jsDay === 0) return null
  return jsDay - 1
}
