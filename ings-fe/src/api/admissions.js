import { apiGet, apiPost } from './client'

export async function fetchCampaigns(params = {}) {
  const data = await apiGet('/admissions/campaigns/', { page_size: 50, ...params })
  return data.results || []
}

export async function fetchPreRegistrations(params = {}) {
  const data = await apiGet('/admissions/pre-registrations/', { page_size: 100, ...params })
  return {
    count: data.count || 0,
    results: data.results || [],
  }
}

export async function createPreRegistration(payload) {
  return apiPost('/admissions/pre-registrations/', payload)
}
