import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api, { setSessionExpiredCallback } from '../services/api'
import { hasAppRole, webLoginForbiddenMessage, ALLOWED_WEB_ROLES } from '../utils/roles'

const AuthContext = createContext(null)

function canAccessWeb(userData) {
  return hasAppRole(userData, ALLOWED_WEB_ROLES)
}

function normalizeUser(userData) {
  return {
    ...userData,
    role_context: userData.role_context || {},
    get_full_name: () =>
      `${userData.first_name || ''} ${userData.last_name || ''}`.trim() || userData.username,
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const _clearSession = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  useEffect(() => {
    setSessionExpiredCallback(_clearSession)
  }, [_clearSession])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.get('/auth/me/')
        .then(res => {
          if (!canAccessWeb(res.data)) {
            _clearSession()
            return
          }
          setUser(normalizeUser(res.data))
        })
        .catch(() => _clearSession())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [_clearSession])

  const login = async (username, password) => {
    const response = await api.post('/auth/login/', { username, password })
    const { access, refresh, user: userData } = response.data

    if (!canAccessWeb(userData)) {
      const err = new Error('Web access forbidden')
      err.response = { data: { detail: webLoginForbiddenMessage(userData?.role) } }
      throw err
    }

    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    setUser(normalizeUser({
      ...userData,
      role_context: response.data.role_context || userData.role_context || {},
    }))

    return response.data
  }

  const logout = () => {
    _clearSession()
  }

  const refreshUser = useCallback(async () => {
    const res = await api.get('/auth/me/')
    if (!canAccessWeb(res.data)) {
      _clearSession()
      return
    }
    setUser(normalizeUser(res.data))
  }, [_clearSession])

  const isAuthenticated = !!user

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
