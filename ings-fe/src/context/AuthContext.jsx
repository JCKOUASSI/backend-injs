import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import * as authApi from '../api/auth'
import { fetchMyStudentProfile } from '../api/students'
import { getAccessToken } from '../api/client'

const AuthContext = createContext(null)
const USER_KEY = 'injs_user'

async function enrichUser(user) {
  if (user?.role !== 'etudiant') return user
  try {
    const profile = await fetchMyStudentProfile(user)
    if (!profile) return user
    return {
      ...user,
      id: profile.id,
      matricule: profile.id,
      niveau: profile.niveau,
      semestre: profile.semestre,
      specialite: profile.specialite,
      mention: profile.mention,
      credits: profile.credits,
      creditsTotal: profile.creditsTotal,
      studentId: profile.studentId,
      title: `${profile.niveau} STAPS`,
    }
  } catch {
    return user
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem(USER_KEY)
    return saved ? JSON.parse(saved) : null
  })
  const [loading, setLoading] = useState(!!getAccessToken())

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false)
      return
    }

    authApi.fetchMe()
      .then((me) => enrichUser(me))
      .then((enriched) => {
        setUser(enriched)
        localStorage.setItem(USER_KEY, JSON.stringify(enriched))
      })
      .catch(() => {
        authApi.logout()
        setUser(null)
        localStorage.removeItem(USER_KEY)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    try {
      const result = await authApi.login(email, password)
      if (result.mfaRequired) {
        return { success: false, mfaRequired: true, email: result.email }
      }
      const enriched = await enrichUser(result.user)
      setUser(enriched)
      localStorage.setItem(USER_KEY, JSON.stringify(enriched))
      return { success: true, role: enriched.role }
    } catch (err) {
      return { success: false, message: err.message || 'Identifiants incorrects' }
    }
  }, [])

  const verifyMfa = useCallback(async (email, code) => {
    try {
      const result = await authApi.verifyMfa(email, code)
      const enriched = await enrichUser(result.user)
      setUser(enriched)
      localStorage.setItem(USER_KEY, JSON.stringify(enriched))
      return { success: true, role: enriched.role }
    } catch (err) {
      return { success: false, message: err.message || 'Code MFA invalide' }
    }
  }, [])

  const logout = useCallback(() => {
    authApi.logout()
    setUser(null)
    localStorage.removeItem(USER_KEY)
  }, [])

  const hasPermission = useCallback((code) => {
    if (!user?.permissions) return false
    return user.permissions.includes(code)
  }, [user])

  return (
    <AuthContext.Provider value={{
      user,
      login,
      verifyMfa,
      logout,
      loading,
      hasPermission,
      isAuthenticated: !!user && !!getAccessToken(),
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export { DEMO_ACCOUNTS } from '../api/auth'
