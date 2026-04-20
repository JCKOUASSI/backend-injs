import { useState } from 'react'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

export default function ChangePasswordModal({ onClose }) {
  const { showToast } = useToast()
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm_password: '' })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [showOld, setShowOld] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const validate = () => {
    const e = {}
    if (!form.old_password) e.old_password = 'Champ requis.'
    if (!form.new_password) e.new_password = 'Champ requis.'
    else if (form.new_password.length < 8) e.new_password = 'Minimum 8 caractères.'
    if (form.new_password !== form.confirm_password) e.confirm_password = 'Les mots de passe ne correspondent pas.'
    return e
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }
    setLoading(true)
    setErrors({})
    try {
      await api.post('/auth/me/change-password/', {
        old_password: form.old_password,
        new_password: form.new_password,
      })
      showToast('Mot de passe modifié avec succès.', 'success')
      onClose()
    } catch (err) {
      const data = err?.response?.data
      if (data?.old_password) setErrors({ old_password: data.old_password[0] || data.old_password })
      else if (data?.new_password) setErrors({ new_password: data.new_password[0] || data.new_password })
      else if (data?.detail) setErrors({ general: data.detail })
      else setErrors({ general: 'Une erreur est survenue.' })
    } finally {
      setLoading(false)
    }
  }

  const field = (key, label, show, setShow) => (
    <div className="mb-3">
      <label className="form-label">{label}</label>
      <div className="input-group">
        <input
          type={show ? 'text' : 'password'}
          className={`form-control${errors[key] ? ' is-invalid' : ''}`}
          value={form[key]}
          onChange={ev => setForm(f => ({ ...f, [key]: ev.target.value }))}
          autoComplete="new-password"
        />
        <button type="button" className="btn btn-outline-secondary" onClick={() => setShow(s => !s)} tabIndex={-1}>
          <i className={`bi bi-eye${show ? '-slash' : ''}`}></i>
        </button>
        {errors[key] && <div className="invalid-feedback">{errors[key]}</div>}
      </div>
    </div>
  )

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: 440 }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h5 className="modal-title"><i className="bi bi-shield-lock me-2"></i>Changer mon mot de passe</h5>
          <button className="btn-close" onClick={onClose}></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.general && <div className="alert alert-danger py-2">{errors.general}</div>}
            {field('old_password', 'Mot de passe actuel', showOld, setShowOld)}
            {field('new_password', 'Nouveau mot de passe', showNew, setShowNew)}
            {field('confirm_password', 'Confirmer le nouveau mot de passe', showConfirm, setShowConfirm)}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <><span className="spinner-border spinner-border-sm me-2"></span>Enregistrement…</> : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
