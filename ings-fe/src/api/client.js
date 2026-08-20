const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const TOKEN_KEY = 'injs_access_token'
const REFRESH_KEY = 'injs_refresh_token'

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(TOKEN_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

async function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) return null

  const res = await fetch(`${API_BASE}/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })

  if (!res.ok) return null

  const data = await res.json()
  setTokens({ access: data.access, refresh: data.refresh || refresh })
  return data.access
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

export async function apiRequest(path, options = {}) {
  const { auth = true, retry = true, ...fetchOptions } = options
  const headers = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  }

  if (auth) {
    const token = getAccessToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  let res
  try {
    res = await fetch(url, { ...fetchOptions, headers })
  } catch {
    throw new ApiError(
      'API indisponible. Vérifiez que le backend INJS tourne sur le port 8002 (le 8001 est souvent pris par SYGEP).',
      0,
      null,
    )
  }

  if (res.status === 401 && auth && retry) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`
      res = await fetch(url, { ...fetchOptions, headers })
    }
  }

  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    const detail = data?.detail || data?.error || data?.message
    let message = typeof detail === 'string' ? detail : `Erreur ${res.status}`
    if (res.status === 404 && String(url).includes('login')) {
      message = 'Service de connexion introuvable. Démarrez le backend INJS sur le port 8002 (le 8001 est souvent occupé par SYGEP).'
    }
    throw new ApiError(message, res.status, data)
  }

  return data
}

export function apiGet(path, params) {
  let query = ''
  if (params && typeof params === 'object') {
    const cleaned = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    )
    const qs = new URLSearchParams(cleaned).toString()
    if (qs) query = `?${qs}`
  }
  return apiRequest(`${path}${query}`)
}

export function apiPost(path, body, options = {}) {
  return apiRequest(path, { method: 'POST', body: JSON.stringify(body), ...options })
}

export function apiPatch(path, body) {
  return apiRequest(path, { method: 'PATCH', body: JSON.stringify(body) })
}

export function apiDelete(path) {
  return apiRequest(path, { method: 'DELETE' })
}

/** PATCH/POST multipart (ex. upload photo). */
export async function apiUpload(path, formData, method = 'PATCH') {
  const token = getAccessToken()
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  let res = await fetch(url, {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })

  if (res.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${newToken}` },
        body: formData,
      })
    }
  }

  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    const message = data?.detail || data?.error || data?.message || `Erreur ${res.status}`
    throw new ApiError(message, res.status, data)
  }

  return data
}
