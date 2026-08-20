import { apiGet } from './client'
import { downloadAuthenticatedFile } from '../utils/exportFormats'

export async function fetchAnalytics() {
  return apiGet('/reports/analytics/')
}

export async function fetchAcademicStatistics(params = {}) {
  return apiGet('/reports/statistics/', params)
}

export async function downloadTranscriptPdf(studentId, params = {}) {
  const query = new URLSearchParams(params).toString()
  const path = `/reports/transcript/${studentId}/pdf/${query ? `?${query}` : ''}`
  await downloadAuthenticatedFile(path, `releve_${studentId}.pdf`)
}

export async function fetchTranscriptSummary(studentId, params = {}) {
  return apiGet(`/reports/transcript/${studentId}/summary/`, params)
}
