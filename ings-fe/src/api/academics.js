import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from './client'
import { mapDepartment } from './mappers'

export async function fetchDepartments(params = {}) {
  const data = await apiGet('/academics/departments/', { page_size: 100, ...params })
  return {
    count: data.count,
    results: data.results.map(mapDepartment),
  }
}

export async function fetchDepartment(id) {
  const data = await apiGet(`/academics/departments/${id}/`)
  return mapDepartment(data)
}

export async function createDepartment(payload) {
  const body = {
    code: payload.code,
    name: payload.name,
    description: payload.description || '',
    institution: payload.institution,
    head: payload.head || null,
  }
  const data = await apiPost('/academics/departments/', body)
  return mapDepartment(data)
}

export async function updateDepartment(id, payload) {
  const data = await apiPatch(`/academics/departments/${id}/`, payload)
  return mapDepartment(data)
}

export async function deleteDepartment(id) {
  await apiDelete(`/academics/departments/${id}/`)
  return true
}

export async function fetchPrograms(params = {}) {
  const data = await apiGet('/academics/programs/', { page_size: 100, ...params })
  return data.results
}

export async function fetchPromotions(params = {}) {
  const data = await apiGet('/academics/promotions/', { page_size: 100, ...params })
  return data.results
}

export async function fetchSpecializations(params = {}) {
  const data = await apiGet('/academics/specializations/', { page_size: 100, ...params })
  return data.results
}

export async function fetchAcademicYears(params = {}) {
  const data = await apiGet('/academics/academic-years/', { page_size: 20, ...params })
  return data.results
}

export async function fetchTeachingUnits(params = {}) {
  const data = await apiGet('/academics/teaching-units/', { page_size: 200, ...params })
  return {
    count: data.count,
    results: data.results,
  }
}

export async function fetchProgramCourses(params = {}) {
  const data = await apiGet('/academics/program-courses/', { page_size: 200, ...params })
  return data.results
}

export async function createTeachingUnit(payload) {
  return apiPost('/academics/teaching-units/', payload)
}

export async function updateTeachingUnit(id, payload) {
  return apiPatch(`/academics/teaching-units/${id}/`, payload)
}

export async function deleteTeachingUnit(id) {
  return apiDelete(`/academics/teaching-units/${id}/`)
}

export async function fetchCourses(params = {}) {
  const data = await apiGet('/academics/courses/', { page_size: 300, ...params })
  return data.results || []
}

export async function createCourse(payload) {
  return apiPost('/academics/courses/', payload)
}

export async function updateCourse(id, payload) {
  return apiPatch(`/academics/courses/${id}/`, payload)
}

export async function deleteCourse(id) {
  return apiDelete(`/academics/courses/${id}/`)
}

async function syncCourses(teachingUnitId, existingCourses, nextCourses) {
  const keptIds = new Set()

  for (const course of nextCourses) {
    const body = {
      teaching_unit: teachingUnitId,
      code: course.code,
      name: course.name,
      hours_cm: Number(course.hours_cm) || 0,
      hours_td: Number(course.hours_td) || 0,
      hours_tp: Number(course.hours_tp) || 0,
    }

    if (course.id) {
      await updateCourse(course.id, body)
      keptIds.add(course.id)
    } else {
      await createCourse(body)
    }
  }

  for (const existing of existingCourses) {
    if (!keptIds.has(existing.id)) {
      await deleteCourse(existing.id)
    }
  }
}

export async function saveTeachingUnitWithCourses({ ue, courses, departmentId, semesterNumber, existingCourses = [] }) {
  const ueBody = {
    code: ue.code,
    name: ue.name,
    credits_ects: Number(ue.credits_ects),
    semester_number: semesterNumber,
    department: departmentId,
    description: ue.description || '',
  }

  let savedUe
  if (ue.id) {
    savedUe = await updateTeachingUnit(ue.id, ueBody)
  } else {
    savedUe = await createTeachingUnit(ueBody)
  }

  await syncCourses(savedUe.id, existingCourses, courses)
  return savedUe
}

export async function fetchInstitutions() {
  const data = await apiGet('/academics/institutions/', { page_size: 10 })
  return data.results
}

export async function fetchInstitution(id) {
  return apiGet(`/academics/institutions/${id}/`)
}

/** Première institution active (INJS). */
export async function fetchPrimaryInstitution() {
  const list = await fetchInstitutions()
  return list.find((i) => i.is_active !== false) || list[0] || null
}

export async function updateInstitution(id, payload) {
  return apiPatch(`/academics/institutions/${id}/`, payload)
}

export async function uploadInstitutionLogo(id, file) {
  const form = new FormData()
  form.append('logo', file)
  return apiUpload(`/academics/institutions/${id}/`, form, 'PATCH')
}
