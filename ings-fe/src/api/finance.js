import { apiGet, apiPost } from './client'

export async function fetchFeeTypes(params = {}) {
  const data = await apiGet('/finance/fee-types/', { page_size: 100, ...params })
  return data.results || []
}

export async function fetchStudentFees(params = {}) {
  const data = await apiGet('/finance/student-fees/', { page_size: 200, ...params })
  return {
    count: data.count || 0,
    results: data.results || [],
  }
}

export async function fetchPayments(params = {}) {
  const data = await apiGet('/finance/payments/', { page_size: 100, ...params })
  return data.results || []
}

export async function initiatePayment(payload) {
  return apiPost('/finance/payments/initiate/', payload)
}

export async function verifyPayment(paymentId) {
  return apiPost(`/finance/payments/${paymentId}/verify/`)
}

export async function fetchProviders() {
  const data = await apiGet('/finance/providers/', { page_size: 50 })
  return data.results || []
}
