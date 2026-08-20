import { apiGet, apiPost, apiPatch, apiDelete } from './client'

/** Catalogue agrégé : toutes les listes déroulantes en un seul appel. */
export async function fetchReferentielsSnapshot(params = {}) {
  return apiGet('/academics/referentiels/', params)
}

/** Compteurs par onglet et contrôles de cohérence de la maquette. */
export async function fetchReferentielsOverview(params = {}) {
  return apiGet('/academics/referentiels/overview/', params)
}

/** Dépendances d'une entrée, pour avertir avant une suppression destructive. */
export async function fetchReferentielDependencies(resource, id) {
  return apiGet('/academics/referentiels/dependencies/', { resource, id })
}

/** Liste paginée d'une ressource, l'endpoint venant du registre backend. */
export async function fetchReferentialPage(endpoint, params = {}) {
  const data = await apiGet(endpoint, params)
  return {
    count: data.count ?? (data.results?.length || 0),
    results: data.results || [],
  }
}

export function createReferentialEntry(endpoint, payload) {
  return apiPost(endpoint, payload)
}

export function updateReferentialEntry(endpoint, id, payload) {
  return apiPatch(`${endpoint}${id}/`, payload)
}

export function deleteReferentialEntry(endpoint, id) {
  return apiDelete(`${endpoint}${id}/`)
}

/** Message lisible à partir d'une ApiError d'écriture référentielle. */
export function referentialErrorMessage(error, fallback = 'Opération impossible') {
  const data = error?.data
  if (!data) return error?.message || fallback
  if (data.code === 'referential_protected') return data.detail
  if (typeof data.detail === 'string') return data.detail
  const fieldErrors = Object.entries(data)
    .filter(([, value]) => Array.isArray(value))
    .map(([field, value]) => `${field} : ${value.join(', ')}`)
  return fieldErrors.length ? fieldErrors.join(' · ') : (error?.message || fallback)
}
