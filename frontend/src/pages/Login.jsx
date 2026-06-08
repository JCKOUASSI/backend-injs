import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ADMIN_URL } from '../services/api'
import logo from '../assets/logo.png'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  if (isAuthenticated) return <Navigate to="/" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Identifiants incorrects')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-brand">
          <img src={logo} alt="MEMFPMA" style={{ width: '120px', marginBottom: '1rem' }} />
          <h3>SYGEP-CPFAE</h3>
          <p className="subtitle">Ministère d'Etat, Ministère de la Fonction Publique et de la Modernisation de l'Administration</p>
          <p>DFRC - CPFAE — Gestion des présences</p>
        </div>

        

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label fw-semibold">Nom d'utilisateur</label>
            <div className="input-group">
              <span className="input-group-text"><i className="bi bi-person"></i></span>
              <input
                type="text"
                className="form-control"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                placeholder="Entrez votre identifiant"
                autoComplete="username"
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label className="form-label fw-semibold">Mot de passe</label>
            <div className="input-group">
              <span className="input-group-text"><i className="bi bi-lock"></i></span>
              <input
                type={showPassword ? 'text' : 'password'}
                className="form-control"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Entrez votre mot de passe"
                autoComplete="current-password"
              />
              <button
                type="button"
                className="input-group-text"
                onClick={() => setShowPassword(v => !v)}
                title={showPassword ? 'Masquer le mot de passe' : 'Voir le mot de passe'}
                style={{ cursor: 'pointer', background: '#f8fafc', border: '1px solid #cbd5e1', borderLeft: 'none' }}
              >
                <i className={`bi ${showPassword ? 'bi-eye-slash' : 'bi-eye'}`}></i>
              </button>
            </div>
          </div>

          {error && (
            <div style={{
              background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 6,
              color: '#b91c1c', padding: '0.6rem 0.85rem', marginBottom: '1rem',
              fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '0.5rem'
            }}>
              <i className="bi bi-exclamation-triangle-fill"></i>
              {error}
            </div>
          )}

          <button type="submit" className="btn-login" disabled={loading}>
            <i className="bi bi-box-arrow-in-right me-1"></i>
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>

        <div className="text-center" style={{ marginTop: '1.25rem' }}>
          <a
            href={ADMIN_URL}
            className="login-admin-link"
            title="Interface d'administration"
          >
            administration
          </a>
        </div>

        <div className="text-center mt-3">
          <small className="text-muted">MEMFPMA — DFRC — SYGEP-CPFAE</small>
        </div>

        <div style={{ textAlign: 'center', marginTop: '1.25rem', paddingTop: '0.75rem', borderTop: '1px solid #e2e8f0' }}>
          <small style={{ fontSize: '0.7rem', color: '#94a3b8', letterSpacing: '0.01em' }}>
            Developpé par <span style={{ fontWeight: 600, color: '#64748b' }}>Ophir Technologies </span>
          </small>
        </div>
      </div>
    </div>
  )
}
