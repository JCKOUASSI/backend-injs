const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001/api'

/** URL admin Django : VITE_ADMIN_URL ou dérivée de VITE_API_URL (…/api → …/admin/). */
const ADMIN_URL = (() => {
  const explicit = (import.meta.env.VITE_ADMIN_URL || '').trim()
  if (explicit) return explicit.replace(/\/?$/, '/')
  const base = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001/api').replace(/\/api\/?$/, '')
  return `${base}/admin/`
})()

let _sessionExpiredCallback = null
export function setSessionExpiredCallback(cb) {
  _sessionExpiredCallback = cb
}

function _onSessionExpired() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  if (_sessionExpiredCallback) {
    _sessionExpiredCallback()
  } else {
    window.location.href = '/login'
  }
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('No refresh token')
  const res = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  })
  if (!res.ok) throw new Error('Refresh failed')
  const data = await res.json()
  localStorage.setItem('access_token', data.access)
  return data.access
}

const handleResponse = async (res) => {
  if (!res.ok) {
    let data
    try { data = await res.clone().json() } catch { data = null }
    const err = new Error(res.statusText)
    err.response = { status: res.status, data }
    throw err
  }
  const text = await res.text()
  return { data: text ? JSON.parse(text) : null, status: res.status }
}

const request = async (method, path, body, config = {}) => {
  const url = `${API_BASE_URL}${path}`
  const isFormData = body instanceof FormData
  const headers = {
    ...(!isFormData && body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    ...getAuthHeaders(),
    ...(config.headers || {}),
  }
  const init = {
    method,
    headers,
    ...(config.signal ? { signal: config.signal } : {}),
    ...(body !== undefined ? { body: isFormData ? body : JSON.stringify(body) } : {}),
  }

  let res = await fetch(url, init)

  const isLoginRequest = path === '/auth/login/' || path.startsWith('/auth/login?')
  if (res.status === 401 && !isLoginRequest) {
    try {
      const newToken = await refreshAccessToken()
      init.headers.Authorization = `Bearer ${newToken}`
      res = await fetch(url, init)
    } catch {
      _onSessionExpired()
      throw new Error('Session expired')
    }
  }

  return handleResponse(res)
}

const getBlob = async (path) => {
  const url = `${API_BASE_URL}${path}`
  const headers = getAuthHeaders()
  let res = await fetch(url, { method: 'GET', headers })
  if (res.status === 401) {
    try {
      const newToken = await refreshAccessToken()
      res = await fetch(url, { method: 'GET', headers: { ...headers, Authorization: `Bearer ${newToken}` } })
    } catch {
      _onSessionExpired()
      throw new Error('Session expired')
    }
  }
  if (!res.ok) {
    let data = null
    try { data = await res.clone().json() } catch { data = null }
    const err = new Error(res.statusText)
    err.response = { status: res.status, data }
    throw err
  }
  const blob = await res.blob()
  const ctype = res.headers.get('Content-Type') || ''
  if (ctype.includes('application/json')) {
    let data = null
    try { data = JSON.parse(await blob.text()) } catch { data = null }
    const err = new Error('Export failed')
    err.response = { status: res.status, data }
    throw err
  }
  const disp = res.headers.get('Content-Disposition') || ''
  const m = disp.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i)
  const fileName = m ? decodeURIComponent(m[1].replace(/"/g, '')) : null
  return { blob, fileName, contentType: ctype }
}

const api = {
  get:     (path, config = {})         => request('GET',    path, undefined, config),
  post:    (path, body, config = {})   => request('POST',   path, body,       config),
  patch:   (path, body, config = {})   => request('PATCH',  path, body,       config),
  put:     (path, body, config = {})   => request('PUT',    path, body,       config),
  delete:  (path, config = {})         => request('DELETE', path, undefined,  config),
  getBlob: (path)                      => getBlob(path),
}

export { API_BASE_URL, ADMIN_URL }
export default api
