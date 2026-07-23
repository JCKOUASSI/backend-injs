import { mediaUrl } from '../utils/labels'

const TEACHER_GRADE_LABELS = {
  assistant: 'Assistant',
  maitre_assistant: 'Maître-Assistant',
  maitre_conferences: 'Maître de Conférences',
  professeur: 'Professeur',
  vacataire: 'Vacataire',
}

const STATUS_LABELS = {
  active: 'Actif',
  suspended: 'Suspendu',
  graduated: 'Diplômé',
  withdrawn: 'Retiré',
}

export function mapBackendRole(user) {
  const level = user?.group_level ?? 4
  if (level <= 2) return 'admin'
  if (level === 3) return 'professeur'
  return 'etudiant'
}

export function mapBackendUser(backendUser, permissions = []) {
  const role = mapBackendRole(backendUser)
  const avatar = `${backendUser.first_name?.[0] || ''}${backendUser.last_name?.[0] || ''}`.toUpperCase()
  const group = backendUser.groups_detail?.[0]

  return {
    id: backendUser.id,
    email: backendUser.email,
    role,
    name: backendUser.full_name,
    firstName: backendUser.first_name,
    lastName: backendUser.last_name,
    title: group?.name || '',
    groupLevel: backendUser.group_level,
    groupCode: group?.profile?.code,
    permissions,
    avatar,
    photoUrl: mediaUrl(backendUser.photo_url),
    institution: backendUser.institution,
    department: backendUser.department,
    raw: backendUser,
  }
}

export function mapStudent(student) {
  const user = student.user_detail || {}
  const niveau = student.promotion_name?.match(/L\d|M\d/)?.[0]
    || student.program_name?.match(/L\d|M\d/)?.[0]
    || 'L1'

  return {
    id: student.matricule,
    uuid: student.id,
    nom: user.last_name || '',
    prenom: user.first_name || '',
    niveau,
    specialite: student.specialization_name
      || student.specialization?.name
      || student.program_name
      || '—',
    programId: student.program || null,
    programName: student.program_name || '',
    promotionId: student.promotion || null,
    promotionName: student.promotion_name || '',
    semestre: student._semestre || 1,
    credits: 0,
    moyenne: null,
    gender: student.gender || '',
    statusKey: student.status || '',
    statut: STATUS_LABELS[student.status] || student.status,
    photoUrl: mediaUrl(student.photo_url || user.photo_url || null),
    email: user.email || '',
    userId: user.id || student.user,
    raw: student,
  }
}

export function mapTeacher(teacher) {
  const user = teacher.user_detail || {}
  return {
    id: teacher.id,
    employeeId: teacher.employee_id,
    firstName: user.first_name || '',
    lastName: user.last_name || '',
    nom: user.full_name || `${user.first_name || ''} ${user.last_name || ''}`.trim(),
    grade: TEACHER_GRADE_LABELS[teacher.grade] || user.groups_detail?.[0]?.name || 'Enseignant',
    gradeKey: teacher.grade || '',
    ue: teacher.specialization || teacher.department_name || '—',
    specialization: teacher.specialization || '',
    departmentId: teacher.department || null,
    departmentName: teacher.department_name || '',
    hireDate: teacher.hire_date || '',
    isActive: teacher.is_active !== false,
    gender: teacher.gender || '',
    email: user.email || '',
    tel: user.phone || '',
    photoUrl: mediaUrl(teacher.photo_url || user.photo_url || null),
    userId: user.id || teacher.user,
    raw: teacher,
  }
}

export function mapRoom(room) {
  return {
    id: room.id,
    code: room.code,
    name: room.name,
    capacity: room.capacity ?? 0,
    building: room.building || '',
    buildingLabel: room.building_display || room.building || '—',
    roomType: room.room_type || '',
    roomTypeLabel: room.room_type_display || room.room_type || '—',
    floor: room.floor || '',
    equipment: Array.isArray(room.equipment) ? room.equipment : [],
    status: room.status || 'available',
    statusLabel: room.status_display || room.status || '—',
    isActive: room.is_active !== false,
    latitude: room.latitude,
    longitude: room.longitude,
    notes: room.notes || '',
    schedulesCount: room.schedules_count ?? 0,
    institutionId: room.institution || null,
    raw: room,
  }
}

export function mapDepartment(dept) {
  return {
    id: dept.id,
    code: dept.code,
    label: dept.name,
    description: dept.description || '',
    institutionId: dept.institution || null,
    institutionName: dept.institution_name || '',
    headId: dept.head || null,
    responsable: dept.head_name || '—',
    raw: dept,
  }
}

export function mapGrade(grade) {
  const score = grade.score != null ? Number(grade.score) : null
  const passing = grade.passing_score != null ? Number(grade.passing_score) : 10
  return {
    id: grade.id,
    ue: grade.teaching_unit_code || '—',
    ueName: grade.teaching_unit_name || '',
    label: grade.evaluation_name || '—',
    evaluationType: grade.evaluation_type || '',
    courseId: grade.course_id || null,
    courseCode: grade.course_code || grade.teaching_unit_code || '—',
    courseName: grade.course_name || grade.teaching_unit_name || grade.evaluation_name || '—',
    studentName: grade.student_name || '',
    matricule: grade.matricule || '',
    studentId: grade.student || null,
    cc: null,
    ct: null,
    moyenne: score,
    maxScore: grade.max_score != null ? Number(grade.max_score) : 20,
    passingScore: passing,
    hasCourse: Boolean(grade.has_course ?? grade.raw?.course),
    credits: 6,
    statut: score == null ? '—' : score >= passing ? 'Validé' : 'Non validé',
    raw: grade,
  }
}
