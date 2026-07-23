import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiShield, FiUser, FiBookOpen } from 'react-icons/fi'
import { useAuth, DEMO_ACCOUNTS } from '../../context/AuthContext'
import { INSTITUTION } from '../../data/mockData'

const ROLE_HINTS = [
  { id: 'admin', label: 'Administration', icon: FiShield, account: DEMO_ACCOUNTS.admin },
  { id: 'professeur', label: 'Professeur', icon: FiUser, account: DEMO_ACCOUNTS.professeur },
  { id: 'etudiant', label: 'Étudiant', icon: FiBookOpen, account: DEMO_ACCOUNTS.etudiant },
]

export default function Login() {
  const [hint, setHint] = useState('admin')
  const [email, setEmail] = useState(DEMO_ACCOUNTS.admin.email)
  const [password, setPassword] = useState(DEMO_ACCOUNTS.admin.password)
  const [mfaCode, setMfaCode] = useState('')
  const [mfaEmail, setMfaEmail] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { login, verifyMfa } = useAuth()
  const navigate = useNavigate()

  const handleHintChange = (roleId) => {
    const role = ROLE_HINTS.find((r) => r.id === roleId)
    setHint(roleId)
    setEmail(role.account.email)
    setPassword(role.account.password)
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')

    const result = mfaEmail
      ? await verifyMfa(mfaEmail, mfaCode)
      : await login(email, password)

    setSubmitting(false)

    if (result.mfaRequired) {
      setMfaEmail(result.email)
      setError('Authentification MFA requise — saisissez votre code')
      return
    }

    if (result.success) {
      navigate(`/${result.role}`)
    } else {
      setError(result.message)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="row g-0">
          <div className="col-lg-5 login-brand">
            <img src="/logo-INJS-ABIDJAN-1.png" alt="INJS Abidjan" />
            <p className="mb-1 opacity-90">{INSTITUTION.ufr}</p>
            <p className="small opacity-75 mb-3">{INSTITUTION.university}</p>
            <p className="small opacity-75">{INSTITUTION.city}, {INSTITUTION.country}</p>
            <hr className="border-light opacity-25 my-3" />
            <p className="small mb-0">Système Licence — Master — Doctorat (LMD)</p>
            <p className="small mb-0">Année académique {INSTITUTION.academicYear}</p>
          </div>
          <div className="col-lg-7 p-4 p-lg-5">
            <h4 className="fw-bold mb-1">Connexion</h4>
            <p className="text-muted mb-4">Connectez-vous avec votre compte INJS-LMD</p>

            {!mfaEmail && (
              <div className="row g-2 mb-4">
                {ROLE_HINTS.map((r) => (
                  <div key={r.id} className="col-4">
                    <div
                      className={`role-card ${hint === r.id ? 'active' : ''}`}
                      onClick={() => handleHintChange(r.id)}
                    >
                      <r.icon size={24} className="mb-2" style={{ color: 'var(--injs-primary)' }} />
                      <div className="fw-semibold small">{r.label}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {!mfaEmail ? (
                <>
                  <div className="mb-3">
                    <label className="form-label fw-semibold">Email</label>
                    <input type="email" className="form-control" value={email} onChange={(e) => setEmail(e.target.value)} required />
                  </div>
                  <div className="mb-3">
                    <label className="form-label fw-semibold">Mot de passe</label>
                    <input type="password" className="form-control" value={password} onChange={(e) => setPassword(e.target.value)} required />
                  </div>
                </>
              ) : (
                <div className="mb-3">
                  <label className="form-label fw-semibold">Code MFA</label>
                  <input type="text" className="form-control" value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} required autoFocus />
                </div>
              )}
              {error && <div className="alert alert-danger py-2">{error}</div>}
              <button type="submit" className="btn btn-injs-primary w-100 py-2 mt-2" disabled={submitting}>
                {submitting ? 'Connexion...' : mfaEmail ? 'Valider le code MFA' : 'Se connecter'}
              </button>
            </form>

            <div className="mt-4 p-3 rounded" style={{ background: 'var(--injs-bg)' }}>
              <small className="text-muted d-block mb-1"><strong>Comptes démo :</strong></small>
              <small className="text-muted">Admin: admin@demo.injs.ci</small><br />
              <small className="text-muted">Prof: prof.martin@demo.injs.ci</small><br />
              <small className="text-muted">Étudiant: etudiant1@demo.injs.ci</small><br />
              <small className="text-muted">Mot de passe: Demo@INJS2026!</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
