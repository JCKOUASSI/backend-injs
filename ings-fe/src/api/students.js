import { apiGet, apiPost, apiPatch, apiDelete } from './client'
import { mapStudent } from './mappers'
import {
  fetchPrograms, fetchPromotions, fetchSpecializations, fetchAcademicYears,
} from './academics'
import { createUser, fetchGroups, findUserByEmail, updateUser, uploadUserPhoto, deleteUser } from './users'

const DEFAULT_PASSWORD = 'Change@INJS2026!'

function generateEmail(prenom, nom, existingEmails = []) {
  const base = `${nom.toLowerCase().replace(/\s/g, '')}.${prenom.toLowerCase().replace(/\s/g, '')}@injs.ci`
  let email = base
  let suffix = 1
  while (existingEmails.includes(email)) {
    email = base.replace('@', `${suffix}@`)
    suffix += 1
  }
  return email
}

function generateMatricule(existingMatricules = []) {
  const year = new Date().getFullYear()
  const prefix = `INJS${year}`
  const sameYear = existingMatricules.filter((m) => m.startsWith(prefix))
  return `${prefix}${String(sameYear.length + 1).padStart(4, '0')}`
}

function resolveProgram(programs, niveau) {
  const degree = niveau[0]
  const withPromo = programs.filter((p) => p.degree_type === degree && p.is_active !== false)
  return (
    withPromo.find((p) => p.track === 'PL')
    || withPromo[0]
    || null
  )
}

function resolvePromotion(promotions, programId, niveau) {
  const programPromos = promotions.filter((p) => p.program === programId && p.is_active !== false)
  return (
    programPromos.find((p) => p.name?.toUpperCase().startsWith(niveau))
    || programPromos.sort((a, b) => (b.entry_year || 0) - (a.entry_year || 0))[0]
    || null
  )
}

function resolveSpecialization(specializations, code) {
  if (!code || code === 'Tronc commun') return null
  return specializations.find((s) => s.code?.toUpperCase() === code.toUpperCase()) || null
}

export async function fetchStudents(params = {}) {
  const data = await apiGet('/students/', { page_size: 15, ...params })
  return {
    count: data.count,
    results: data.results.map(mapStudent),
  }
}

export async function fetchStudentsMeta() {
  return apiGet('/students/meta/')
}

export async function fetchStudent(id) {
  const data = await apiGet(`/students/${id}/`)
  return mapStudent(data)
}

export async function fetchStudentFullDetail(studentUuid) {
  const student = await apiGet(`/students/${studentUuid}/`)

  let semestre = 1
  let promotionDetail = null
  if (student.promotion) {
    promotionDetail = await apiGet(`/academics/promotions/${student.promotion}/`)
    semestre = promotionDetail.current_semester || 1
  }

  const [enrollments, programCourses, grades, card] = await Promise.all([
    apiGet('/students/enrollments/', { student: studentUuid, page_size: 20 }).then((r) => r.results),
    student.program
      ? apiGet('/academics/program-courses/', { program: student.program, page_size: 200 }).then((r) => r.results)
      : Promise.resolve([]),
    apiGet('/exams/grades/', { student: studentUuid, page_size: 100 }).then((r) => r.results),
    apiGet(`/students/${studentUuid}/card/`).catch(() => null),
  ])

  const user = student.user_detail || {}
  const specialization = student.specialization
    ? await apiGet(`/academics/specializations/${student.specialization}/`).catch(() => null)
    : null

  const coursesBySemester = {}
  for (const pc of programCourses) {
    const sem = pc.semester_number
    if (!coursesBySemester[sem]) coursesBySemester[sem] = []
    coursesBySemester[sem].push(pc)
  }

  return {
    student,
    user,
    semestre,
    promotionDetail,
    specialization,
    enrollments,
    programCourses,
    coursesBySemester,
    grades,
    card,
    mapped: mapStudent({ ...student, _semestre: semestre }),
  }
}

export async function fetchMyStudentProfile(authUser) {
  const data = await apiGet('/students/', { search: authUser.email, page_size: 100 })
  const student = data.results.find(
    (s) => s.user_detail?.email?.toLowerCase() === authUser.email?.toLowerCase()
      || s.user_detail?.id === authUser.id,
  )
  if (!student) return null

  let semestre = 1
  if (student.promotion) {
    const promo = await apiGet(`/academics/promotions/${student.promotion}/`)
    semestre = promo.current_semester || 1
  }

  const mapped = mapStudent(student)
  return {
    ...mapped,
    semestre,
    studentId: student.id,
    programId: student.program,
    promotionId: student.promotion,
    mention: student.program_name?.includes('STAPS') ? 'STAPS' : mapped.niveau,
    creditsTotal: 180,
  }
}

export async function fetchMyEnrollments(studentId) {
  const data = await apiGet('/students/enrollments/', { student: studentId, page_size: 20 })
  return data.results
}

/**
 * Inscription étudiant via les endpoints backend existants :
 * POST /auth/users/ → POST /students/ → POST /students/enrollments/ → POST .../approve/
 */
export async function enrollStudent(payload) {
  const [programs, promotions, specializations, academicYears, groups, studentsList] = await Promise.all([
    fetchPrograms(),
    fetchPromotions(),
    fetchSpecializations(),
    fetchAcademicYears({ is_current: true }),
    fetchGroups(),
    fetchStudents(),
  ])

  const program = resolveProgram(programs, payload.niveau)
  if (!program) throw new Error('Aucune filière active trouvée pour ce niveau.')

  const promotion = resolvePromotion(promotions, program.id, payload.niveau)
  if (!promotion) throw new Error('Aucune promotion active trouvée pour cette filière.')

  const specialization = resolveSpecialization(specializations, payload.specialite)
  const academicYear = academicYears.find((y) => y.is_current) || academicYears[0]
  if (!academicYear) throw new Error('Aucune année académique courante configurée.')

  const etudiantGroup = groups.find((g) => g.profile?.code === 'etudiant')
  const email = payload.email?.trim() || generateEmail(payload.prenom, payload.nom)
  const matricule = generateMatricule(studentsList.results.map((s) => s.id))

  await createUser({
    email,
    password: payload.password || DEFAULT_PASSWORD,
    first_name: payload.prenom,
    last_name: payload.nom,
    group_ids: etudiantGroup ? [etudiantGroup.id] : [],
    department: program.department || undefined,
  })

  const user = await findUserByEmail(email)

  const studentBody = {
    user: user.id,
    matricule,
    program: program.id,
    promotion: promotion.id,
    status: 'active',
    enrollment_date: new Date().toISOString().slice(0, 10),
  }
  if (specialization) studentBody.specialization = specialization.id

  const student = await apiPost('/students/', studentBody)

  const enrollment = await apiPost('/students/enrollments/', {
    student: student.id,
    academic_year: academicYear.id,
    enrollment_type: 'administrative',
    status: 'pending',
  })

  await apiPost(`/students/enrollments/${enrollment.id}/approve/`, {})

  return mapStudent(student)
}

export async function updateStudent(studentUuid, { studentPatch = {}, userPatch = {}, photoFile = null } = {}) {
  const current = await apiGet(`/students/${studentUuid}/`)
  const userId = current.user_detail?.id || current.user

  if (userId && Object.keys(userPatch).length) {
    await updateUser(userId, userPatch)
  }
  if (userId && photoFile) {
    await uploadUserPhoto(userId, photoFile)
  }

  let student = current
  if (Object.keys(studentPatch).length) {
    student = await apiPatch(`/students/${studentUuid}/`, studentPatch)
  } else {
    student = await apiGet(`/students/${studentUuid}/`)
  }
  return mapStudent(student)
}

export async function deleteStudent(studentUuid) {
  const current = await apiGet(`/students/${studentUuid}/`)
  const userId = current.user_detail?.id || current.user
  await apiDelete(`/students/${studentUuid}/`)
  if (userId) {
    try {
      await deleteUser(userId)
    } catch {
      try {
        await updateUser(userId, { is_active: false })
      } catch {
        // utilisateur déjà orphelin / non supprimable
      }
    }
  }
  return true
}
