import { useEffect, useState } from 'react'
import { FiEdit2 } from 'react-icons/fi'
import Modal from '../../../components/common/Modal'
import IconActionButtons from '../../../components/common/IconActionButtons'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import {
  fetchPrimaryInstitution,
  updateInstitution,
  uploadInstitutionLogo,
} from '../../../api/academics'
import { mediaUrl } from '../../../utils/labels'

const DEFAULT_INJS_LOGO = '/logo-INJS-ABIDJAN-1.png'

const EMPTY = {
  code: '',
  name: '',
  acronym: '',
  address: '',
  city: '',
  country: '',
  phone: '',
  email: '',
  website: '',
  is_active: true,
}

export default function SettingsInstitution() {
  const { showToast } = useToast()
  const { data: institution, loading, error, reload } = useFetch(() => fetchPrimaryInstitution())

  const [showDetail, setShowDetail] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [logoFile, setLogoFile] = useState(null)
  const [logoPreview, setLogoPreview] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    return () => {
      if (logoPreview) URL.revokeObjectURL(logoPreview)
    }
  }, [logoPreview])

  const logoSrc = mediaUrl(institution?.logo_url) || logoPreview || DEFAULT_INJS_LOGO

  const openDetail = () => setShowDetail(true)

  const openEdit = () => {
    if (!institution) return
    setForm({
      code: institution.code || '',
      name: institution.name || '',
      acronym: institution.acronym || '',
      address: institution.address || '',
      city: institution.city || '',
      country: institution.country || '',
      phone: institution.phone || '',
      email: institution.email || '',
      website: institution.website || '',
      is_active: institution.is_active !== false,
    })
    setLogoFile(null)
    setLogoPreview(null)
    setShowEdit(true)
  }

  const onLogoChange = (ev) => {
    const file = ev.target.files?.[0]
    if (!file) return
    if (logoPreview) URL.revokeObjectURL(logoPreview)
    setLogoFile(file)
    setLogoPreview(URL.createObjectURL(file))
  }

  const handleEdit = async (ev) => {
    ev.preventDefault()
    if (!institution?.id) return
    setSaving(true)
    try {
      await updateInstitution(institution.id, {
        code: form.code,
        name: form.name,
        acronym: form.acronym,
        address: form.address,
        city: form.city,
        country: form.country,
        phone: form.phone,
        email: form.email,
        website: form.website?.trim() || null,
        is_active: form.is_active,
      })
      if (logoFile) {
        await uploadInstitutionLogo(institution.id, logoFile)
      }
      showToast('Fiche institution mise à jour', 'success')
      setShowEdit(false)
      setLogoFile(null)
      setLogoPreview(null)
      reload()
    } catch (err) {
      showToast(err.message || 'Échec de la modification', 'danger')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="text-center py-4"><div className="spinner-border text-primary" /></div>
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>
  }

  if (!institution) {
    return <div className="alert alert-warning mb-0">Aucune institution configurée sur le serveur.</div>
  }

  return (
    <div className="card-injs p-4">
      <div className="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-3">
        <div>
          <h6 className="fw-bold mb-1">Institution</h6>
          <p className="text-muted small mb-0">
            Informations affichées sur la plateforme et les documents officiels.
          </p>
        </div>
        <IconActionButtons
          actions={[
            { type: 'view', title: 'Voir la fiche', onClick: openDetail },
            { type: 'edit', title: 'Modifier la fiche', onClick: openEdit },
          ]}
        />
      </div>

      <div className="border rounded-3 p-4">
        <div className="d-flex flex-wrap gap-4 align-items-center">
          {logoSrc ? (
            <img
              src={logoSrc}
              alt={`Logo ${institution.acronym || institution.name}`}
              className="institution-logo"
            />
          ) : (
            <div className="institution-logo institution-logo-placeholder">
              {(institution.acronym || institution.name || '?').slice(0, 4)}
            </div>
          )}
          <div>
            <h5 className="fw-bold mb-1">{institution.name}</h5>
            <div className="text-muted small mb-2">
              <span className="badge-injs me-2">{institution.code}</span>
              {institution.acronym}
              {institution.city ? ` — ${institution.city}` : ''}
            </div>
            <p className="small mb-0 text-muted">
              {institution.email || '—'} {institution.phone ? `· ${institution.phone}` : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Visualisation */}
      <Modal
        show={showDetail}
        onClose={() => setShowDetail(false)}
        title={`Fiche institution — ${institution.acronym || institution.code}`}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowDetail(false)}>Fermer</button>
            <button
              type="button"
              className="btn btn-outline-primary btn-icon-action"
              title="Modifier"
              aria-label="Modifier"
              onClick={() => {
                setShowDetail(false)
                openEdit()
              }}
            >
              <FiEdit2 size={16} />
            </button>
          </>
        }
      >
        <div className="text-center mb-4">
          {logoSrc ? (
            <img
              src={logoSrc}
              alt=""
              className="institution-logo institution-logo-lg mb-3"
            />
          ) : (
            <div className="institution-logo institution-logo-lg institution-logo-placeholder mx-auto mb-3">
              {(institution.acronym || '?').slice(0, 4)}
            </div>
          )}
          <h5 className="fw-bold">{institution.name}</h5>
        </div>
        <dl className="detail-view mb-0">
          <div className="detail-row"><dt>Code</dt><dd><code>{institution.code}</code></dd></div>
          <div className="detail-row"><dt>Acronyme</dt><dd>{institution.acronym || '—'}</dd></div>
          <div className="detail-row"><dt>Adresse</dt><dd>{institution.address || '—'}</dd></div>
          <div className="detail-row"><dt>Ville</dt><dd>{institution.city || '—'}</dd></div>
          <div className="detail-row"><dt>Pays</dt><dd>{institution.country || '—'}</dd></div>
          <div className="detail-row"><dt>Téléphone</dt><dd>{institution.phone || '—'}</dd></div>
          <div className="detail-row"><dt>Email</dt><dd>{institution.email || '—'}</dd></div>
          <div className="detail-row"><dt>Site web</dt><dd>{institution.website || '—'}</dd></div>
          <div className="detail-row">
            <dt>Statut</dt>
            <dd>
              <span className={`grade-badge ${institution.is_active !== false ? 'grade-valid' : 'grade-fail'}`}>
                {institution.is_active !== false ? 'Active' : 'Inactive'}
              </span>
            </dd>
          </div>
        </dl>
      </Modal>

      {/* Modification */}
      <Modal
        show={showEdit}
        onClose={() => {
          setShowEdit(false)
          setLogoFile(null)
          setLogoPreview(null)
        }}
        title={`Modifier — ${institution.name}`}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowEdit(false)}>Annuler</button>
            <button type="submit" form="institution-edit-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="institution-edit-form" onSubmit={handleEdit}>
          <div className="d-flex align-items-center gap-3 mb-4">
            {(logoPreview || mediaUrl(institution.logo_url) || DEFAULT_INJS_LOGO) ? (
              <img
                src={logoPreview || mediaUrl(institution.logo_url) || DEFAULT_INJS_LOGO}
                alt=""
                className="institution-logo"
              />
            ) : (
              <div className="institution-logo institution-logo-placeholder">
                {(form.acronym || '?').slice(0, 4)}
              </div>
            )}
            <div className="flex-grow-1">
              <label className="form-label">Logo de l&apos;institution</label>
              <input type="file" accept="image/*" className="form-control" onChange={onLogoChange} />
              <small className="text-muted">PNG / JPG — affiché sur la fiche et la plateforme</small>
            </div>
          </div>

          <div className="row g-3">
            <div className="col-md-4">
              <label className="form-label">Code *</label>
              <input className="form-control" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </div>
            <div className="col-md-4">
              <label className="form-label">Acronyme *</label>
              <input className="form-control" required value={form.acronym} onChange={(e) => setForm({ ...form, acronym: e.target.value })} />
            </div>
            <div className="col-md-4">
              <label className="form-label">Statut</label>
              <select
                className="form-select"
                value={form.is_active ? '1' : '0'}
                onChange={(e) => setForm({ ...form, is_active: e.target.value === '1' })}
              >
                <option value="1">Active</option>
                <option value="0">Inactive</option>
              </select>
            </div>
            <div className="col-12">
              <label className="form-label">Nom *</label>
              <input className="form-control" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="col-12">
              <label className="form-label">Adresse</label>
              <textarea className="form-control" rows={2} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Ville</label>
              <input className="form-control" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Pays</label>
              <input className="form-control" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Téléphone</label>
              <input className="form-control" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">Email</label>
              <input type="email" className="form-control" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="col-12">
              <label className="form-label">Site web</label>
              <input type="url" className="form-control" placeholder="https://" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
            </div>
          </div>
        </form>
      </Modal>
    </div>
  )
}
