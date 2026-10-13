import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ADMIN_URL } from '../services/api'
import logo from '../assets/logo-injs.svg'
import '../styles/login.css'

/**
 * Comptes de démonstration (créés par backend/seed_data.py) accessibles sur le
 * web. Un clic remplit le formulaire et connecte directement — aucune saisie.
 * Les participants/formateurs (comptes badge, application mobile) sont
 * volontairement absents : leur rôle est refusé sur le web.
 * GARDE-FOU PERMANENT (2026-10-10) : aucun compte ni libellé « SygepCPFAE »,
 * « CPFAE » ou « Responsable CPFAE » — verrouillé par Login.test.jsx et
 * core/tests/test_garde_fous_permanents.py.
 */
// Comptes démo : visibles seulement si le build les active (VITE_DEMO_ACCOUNTS=1,
// via .env.development / .env.test / .env.sandbox). Le build de production les
// exclut : aucun identifiant n'est servi aux utilisateurs réels.
const DEMO_ACTIF = import.meta.env.VITE_DEMO_ACCOUNTS === '1'
const COMPTES_DEMO = [
  { username: 'admin', password: 'admin123', libelle: 'Administrateur', nom: 'Admin INJS' },
  { username: 'jckouassi', password: 'JckPcm@123', libelle: 'Chef INJS Admin', nom: 'Jean-Claude Kouassi' },
  { username: 'injs', password: 'injs123', libelle: 'INJS Admin', nom: 'Responsable INJS' },
  { username: 'secretariat', password: 'sec123', libelle: 'Secrétariat', nom: 'Secrétariat INJS' },
  { username: 'superviseur1', password: 'sup123', libelle: 'Encadrant', nom: 'Jean MARTIN' },
  { username: 'superviseur2', password: 'sup123', libelle: 'Encadrant', nom: 'Sophie BERNARD' },
]

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  // Étape MFA (CURP U6) : le backend répond 403 « MFA_REQUIRED » avec un
  // jeton court ; l'utilisateur saisit ensuite son code TOTP.
  const [etapeMfa, setEtapeMfa] = useState(null) // { token, duree, username }
  const [codeMfa, setCodeMfa] = useState('')
  const { login, verifierMfa, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  if (isAuthenticated) return <Navigate to="/" replace />

  // Connexion partagée : saisie manuelle et comptes démo cliquables.
  const connecter = async (identifiant, motDePasse) => {
    setError('')
    setLoading(true)

    try {
      await login(identifiant, motDePasse)
      navigate('/', { replace: true })
    } catch (err) {
      const data = err.response?.data || {}
      if (data.code === 'MFA_REQUIRED' && data.mfa_token) {
        setCodeMfa('')
        setEtapeMfa({ token: data.mfa_token, duree: data.mfa_duree, username: identifiant })
      } else {
        // MFA_OBLIGATOIRE, COMPTE_VERROUILLE, identifiants erronés…
        setError(data.detail || 'Identifiants incorrects')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    await connecter(username, password)
  }

  // Un clic sur un compte démo remplit les champs et connecte sans saisie.
  const choisirCompte = (compte) => {
    setUsername(compte.username)
    setPassword(compte.password)
    connecter(compte.username, compte.password)
  }

  const handleMfaSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await verifierMfa(etapeMfa.token, codeMfa)
      setEtapeMfa(null)
      navigate('/', { replace: true })
    } catch (err) {
      const data = err.response?.data || {}
      if (data.code === 'MFA_JETON_INVALIDE') {
        // Jeton expiré : retour à la saisie des identifiants.
        setEtapeMfa(null)
      }
      setError(data.detail || 'Vérification MFA impossible')
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
          <h2>{etapeMfa ? 'Deuxième étape' : 'Connexion'}</h2>
          <p className="login-form-lead">
            {etapeMfa
              ? 'Mot de passe correct : validez avec votre code de vérification.'
              : 'Connectez-vous avec votre compte INJS-LMD'}
          </p>

          {etapeMfa ? (
            <form onSubmit={handleMfaSubmit}>
              <p className="login-form-lead">
                Saisissez le code à 6 chiffres généré par votre application
                d'authentification pour <strong>{etapeMfa.username}</strong>
                {etapeMfa.duree ? ` (valable ${etapeMfa.duree} minutes).` : '.'}
              </p>
              <div className="login-field">
                <label htmlFor="login-mfa-code">Code de vérification</label>
                <div className="login-input">
                  <i className="bi bi-shield-lock"></i>
                  <input
                    id="login-mfa-code"
                    data-testid="mfa-code-input"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={codeMfa}
                    onChange={(e) => setCodeMfa(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    required
                    autoFocus
                    placeholder="000000"
                  />
                </div>
              </div>
              {error && (
                <div className="login-error" role="alert">
                  <i className="bi bi-exclamation-triangle-fill"></i>
                  {error}
                </div>
              )}
              <button type="submit" className="btn-login" disabled={loading}>
                <i className="bi bi-shield-check"></i>
                {loading ? 'Vérification…' : 'Vérifier le code'}
              </button>
              <div className="text-center" style={{ marginTop: '1rem' }}>
                <button
                  type="button"
                  className="login-admin-link"
                  data-testid="mfa-back"
                  onClick={() => { setEtapeMfa(null); setCodeMfa(''); setError('') }}
                >
                  <i className="bi bi-arrow-left me-1"></i>Modifier les identifiants
                </button>
              </div>
            </form>
          ) : (
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
          )}

          <div className="login-admin-btn-wrap">
            <a
              href={ADMIN_URL}
              className="btn-login-admin"
              title="Interface d'administration"
            >
              <i className="bi bi-gear-fill me-1"></i>
              administration
            </a>
          </div>

          {DEMO_ACTIF && (
          <div className="login-demo">
            <strong>Comptes démo</strong>
            <p>Un clic suffit : les identifiants sont saisis et la connexion s&apos;effectue automatiquement.</p>
            <div className="login-demo-liste">
              {COMPTES_DEMO.map((compte) => (
                <button
                  key={compte.username}
                  type="button"
                  className="login-demo-compte"
                  onClick={() => choisirCompte(compte)}
                  disabled={loading}
                  title={`Se connecter en tant que ${compte.nom} (${compte.libelle})`}
                >
                  <span className="login-demo-ligne1">
                    <span className="login-demo-role">{compte.libelle}</span>
                    <span className="login-demo-nom">{compte.nom}</span>
                  </span>
                  <span className="login-demo-id">{compte.username} / {compte.password}</span>
                </button>
              ))}
            </div>
          </div>
          )}

          <div className="login-form-footer">
            <span>Développé par Ophir Technologies</span>
          </div>
        </section>
      </div>
    </div>
  )
}
