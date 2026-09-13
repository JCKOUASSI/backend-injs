import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { hasAppRole } from '../../utils/roles'

/**
 * Écran de changement de mot de passe obligatoire. Un compte dont
 * `must_change_password` est vrai (compte badge créé par l'administration,
 * première connexion) ne peut accéder à aucune autre page tant que le mot de
 * passe n'a pas été changé (§10.1, corrigé au LOT 46).
 */
export const FORCED_PASSWORD_PATH = '/changement-mot-de-passe-obligatoire'

export default function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, loading, user } = useAuth()
  const location = useLocation()

  if (loading) return <div className="loading"><div className="spinner"></div></div>
  if (!isAuthenticated) return <Navigate to="/login" replace />

  // Quelle que soit la page demandée, un changement de mot de passe obligatoire
  // renvoie vers l'écran dédié (sauf cet écran lui-même, pour éviter une boucle).
  if (user?.must_change_password && location.pathname !== FORCED_PASSWORD_PATH) {
    return <Navigate to={FORCED_PASSWORD_PATH} replace state={{ from: location }} />
  }

  if (allowedRoles && !hasAppRole(user, allowedRoles)) return <Navigate to="/" replace />
  return children
}
