import { apiGet, apiPost, apiPatch, setTokens, clearTokens } from './client'
import { mapBackendUser } from './mappers'

export const DEMO_ACCOUNTS = {
  admin: { email: 'admin@demo.injs.ci', password: 'Demo@INJS2026!' },
  professeur: { email: 'prof.martin@demo.injs.ci', password: 'Demo@INJS2026!' },
  etudiant: { email: 'etudiant1@demo.injs.ci', password: 'Demo@INJS2026!' },
}

export async function login(email, password) {
  const data = await apiPost('/auth/login/', { email, password }, { auth: false, retry: false })

  if (data.mfa_required) {
    return { mfaRequired: true, email }
  }

  setTokens({ access: data.access, refresh: data.refresh })
  const user = mapBackendUser(data.user, data.permissions || [])
  return { user, permissions: data.permissions || [] }
}

export async function verifyMfa(email, code) {
  const data = await apiPost('/auth/mfa/verify/', { email, code }, { auth: false, retry: false })
  setTokens({ access: data.access, refresh: data.refresh })
  const user = mapBackendUser(data.user, data.permissions || [])
  return { user, permissions: data.permissions || [] }
}

export async function fetchMe() {
  const data = await apiGet('/auth/me/')
  return mapBackendUser(data, data.permissions || [])
}

export async function updateMe(payload) {
  const data = await apiPatch('/auth/me/', payload)
  return mapBackendUser(data, data.permissions || [])
}

export function logout() {
  clearTokens()
}
