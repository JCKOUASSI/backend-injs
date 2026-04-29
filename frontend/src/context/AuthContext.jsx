import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api, { setSessionExpiredCallback } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const _clearSession = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  // Enregistrer le callback dans api.js pour gérer l'expiration de session
  useEffect(() => {
    setSessionExpiredCallback(_clearSession)
  }, [_clearSession])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.get('/auth/me/')
        .then(res => {
          const userData = {
            ...res.data,
            get_full_name: () => `${res.data.first_name || ''} ${res.data.last_name || ''}`.trim() || res.data.username,
          }
          setUser(userData)
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
    
    if (userData?.role === 'ADMIN') {
      const err = new Error('Admin access forbidden')
      err.response = { data: { detail: 'Les administrateurs doivent utiliser l\'interface d\'administration.' } }
      throw err
    }

    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    
    // Add get_full_name method to user
    const userWithMethod = {
      ...userData,
      get_full_name: () => `${userData.first_name || ''} ${userData.last_name || ''}`.trim() || userData.username,
    }
    setUser(userWithMethod)
    
    return response.data
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }

  const refreshUser = useCallback(async () => {
    const res = await api.get('/auth/me/')
    const userData = {
      ...res.data,
      get_full_name: () => `${res.data.first_name || ''} ${res.data.last_name || ''}`.trim() || res.data.username,
    }
    setUser(userData)
  }, [])

  const isAuthenticated = !!user

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
