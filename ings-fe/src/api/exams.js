import { apiGet, apiPost } from './client'
import { mapGrade } from './mappers'

export async function fetchGrades(params = {}) {
  const data = await apiGet('/exams/grades/', { page_size: 200, ...params })
  return {
    count: data.count,
    results: (data.results || []).map(mapGrade),
  }
}

export async function fetchExamSessions(params = {}) {
  const data = await apiGet('/exams/sessions/', { page_size: 50, ...params })
  return data.results || []
}

export async function createExamSession(payload) {
  return apiPost('/exams/sessions/', payload)
}

export async function fetchEvaluations(params = {}) {
  const data = await apiGet('/exams/evaluations/', { page_size: 200, ...params })
  return data.results || []
}

export async function createGrade(payload) {
  return apiPost('/exams/grades/', payload)
}

export async function fetchDeliberations(params = {}) {
  const data = await apiGet('/exams/deliberations/', { page_size: 50, ...params })
  return data.results || []
}

export async function runDeliberation(id) {
  return apiPost(`/exams/deliberations/${id}/run/`)
}

export async function validateDeliberation(id) {
  return apiPost(`/exams/deliberations/${id}/validate/`)
}

export async function publishDeliberation(id) {
  return apiPost(`/exams/deliberations/${id}/publish/`)
}

export async function fetchJuries(params = {}) {
  const data = await apiGet('/exams/juries/', { page_size: 50, ...params })
  return data.results || []
}
