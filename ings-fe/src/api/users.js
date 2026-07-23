import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from './client'
import { mapBackendRole } from './mappers'

function mapUser(user) {
  const role = mapBackendRole(user)
  return {
    id: user.id,
    prenom: user.first_name,
    nom: user.last_name,
    email: user.email,
    role,
    statut: user.is_active ? 'Actif' : 'Inactif',
    lastLogin: user.last_login ? new Date(user.last_login).toLocaleDateString('fr-FR') : '—',
    title: user.groups_detail?.[0]?.name || role,
    raw: user,
  }
}

export async function fetchUsers(params = {}) {
  const data = await apiGet('/auth/users/', { page_size: 100, ...params })
  return {
    count: data.count,
    results: data.results.map(mapUser),
  }
}

export async function createUser(payload) {
  return apiPost('/auth/users/', payload)
}

export async function updateUser(userId, payload) {
  return apiPatch(`/auth/users/${userId}/`, payload)
}

export async function uploadUserPhoto(userId, file) {
  const form = new FormData()
  form.append('photo', file)
  return apiUpload(`/auth/users/${userId}/`, form, 'PATCH')
}

export async function deleteUser(userId) {
  return apiDelete(`/auth/users/${userId}/`)
}

export async function findUserByEmail(email) {
  const data = await apiGet('/auth/users/', { search: email, page_size: 100 })
  const match = data.results.find((u) => u.email?.toLowerCase() === email.toLowerCase())
  if (!match) throw new Error(`Utilisateur introuvable pour ${email}`)
  return match
}

export async function fetchGroups() {
  const data = await apiGet('/auth/groups/', { page_size: 100 })
  return data.results
}

export async function fetchPermissions() {
  const data = await apiGet('/auth/permissions/', { page_size: 200 })
  return data.results
}
