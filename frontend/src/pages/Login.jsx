import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ADMIN_URL } from '../services/api'
import logo from '../assets/logo-injs.svg'

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
      <div className="login-orb login-orb-a" aria-hidden="true" />
      <div className="login-orb login-orb-b" aria-hidden="true" />
      <div className="login-orb login-orb-c" aria-hidden="true" />
      <div className="login-shell">
        <aside className="login-panel-brand">
          <div className="login-logo-frame">
            <img src={logo} alt="INJS Abidjan" />
          </div>
          <h1>INJS UFR STAPS-JL</h1>
          <p className="login-brand-org">Institut National de la Jeunesse et des Sports</p>
          <p className="login-brand-place">Marcory — Abidjan, Côte d'Ivoire</p>
          <div className="login-brand-footer">
            <p>Système Licence — Master — Doctorat (LMD)</p>
            <p>Année académique 2025-2026</p>
          </div>
        </aside>

        <section className="login-panel-form">
          <h2>Connexion</h2>
          <p className="login-form-lead">Connectez-vous avec votre compte INJS-LMD</p>

          <form onSubmit={handleSubmit}>
            <div className="login-field">
              <label htmlFor="login-username">Nom d'utilisateur</label>
              <div className="login-input">
                <i className="bi bi-person"></i>
                <input
                  id="login-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                  placeholder="Entrez votre identifiant"
                  autoComplete="username"
                />
              </div>
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Mot de passe</label>
              <div className="login-input">
                <i className="bi bi-lock"></i>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="Entrez votre mot de passe"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-password-toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  title={showPassword ? 'Masquer le mot de passe' : 'Voir le mot de passe'}
                  aria-label={showPassword ? 'Masquer le mot de passe' : 'Voir le mot de passe'}
                >
                  <i className={`bi ${showPassword ? 'bi-eye-slash' : 'bi-eye'}`}></i>
                </button>
              </div>
            </div>

            {error && (
              <div className="login-error" role="alert">
                <i className="bi bi-exclamation-triangle-fill"></i>
                {error}
              </div>
            )}

            <button type="submit" className="btn-login" disabled={loading}>
              <i className="bi bi-box-arrow-in-right"></i>
              {loading ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>

          <div className="text-center" style={{ marginTop: '1rem' }}>
            <a href={ADMIN_URL} className="login-admin-link" title="Interface d'administration">
              administration
            </a>
          </div>

          <div className="login-demo">
            <strong>Comptes démo</strong>
            <p>
              Administrateur : compte créé/configuré localement
              {' · '}
              Secrétariat : compte créé/configuré localement
              {' · '}
              INJS : compte créé/configuré localement
            </p>
          </div>

          <div className="login-form-footer">
            <a href={ADMIN_URL} className="login-admin-link" title="Interface d'administration">
              administration
            </a>
            <span>Développé par Ophir Technologies</span>
          </div>
        </section>
      </div>
    </div>
  )
}
