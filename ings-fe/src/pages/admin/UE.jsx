import { useState, useCallback } from 'react'
import { FiEdit2 } from 'react-icons/fi'
import PageHeader from '../../components/common/PageHeader'
import Modal from '../../components/common/Modal'
import IconActionButtons from '../../components/common/IconActionButtons'
import { useToast } from '../../context/ToastContext'
import { useFetch } from '../../hooks/useFetch'
import {
  fetchDepartments,
  fetchTeachingUnits,
  saveTeachingUnitWithCourses,
  deleteTeachingUnit,
} from '../../api/academics'
import { SEMESTRES } from '../../data/mockData'

const EMPTY_UE = { code: '', name: '', credits_ects: 6, description: '' }
const EMPTY_ECUE = { code: '', name: '', hours_cm: 0, hours_td: 0, hours_tp: 0 }

/** Couleur distincte par semestre (S1 → S6). */
const SEM_TAB_COLORS = {
  1: { bg: '#3349A1', soft: 'rgba(51, 73, 161, 0.12)', border: '#3349A1' },
  2: { bg: '#0D9488', soft: 'rgba(13, 148, 136, 0.12)', border: '#0D9488' },
  3: { bg: '#C2410C', soft: 'rgba(194, 65, 12, 0.12)', border: '#C2410C' },
  4: { bg: '#7C3AED', soft: 'rgba(124, 58, 237, 0.12)', border: '#7C3AED' },
  5: { bg: '#B45309', soft: 'rgba(180, 83, 9, 0.12)', border: '#B45309' },
  6: { bg: '#BE185D', soft: 'rgba(190, 24, 93, 0.12)', border: '#BE185D' },
}

function mapUeForForm(ue) {
  return {
    id: ue.id,
    code: ue.code,
    name: ue.name,
    credits_ects: ue.credits_ects,
    description: ue.description || '',
    courses: (ue.courses || []).map((c) => ({
      id: c.id,
      code: c.code,
      name: c.name,
      hours_cm: c.hours_cm || 0,
      hours_td: c.hours_td || 0,
      hours_tp: c.hours_tp || 0,
    })),
  }
}

function suggestEcueCode(ueCode, index) {
  return `${ueCode}${index + 1}`
}

export default function AdminUE() {
  const { showToast } = useToast()
  const [activeSem, setActiveSem] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [selectedUe, setSelectedUe] = useState(null)
  const [form, setForm] = useState({ ...EMPTY_UE, courses: [{ ...EMPTY_ECUE }] })
  const [saving, setSaving] = useState(false)

  const { data: departments } = useFetch(() => fetchDepartments())
  const stapsDept = departments?.results?.find((d) => d.code === 'STAPS') || departments?.results?.[0]

  const loadUnits = useCallback(
    () => fetchTeachingUnits({ semester_number: activeSem }),
    [activeSem],
  )
  const { data, loading, error, reload } = useFetch(loadUnits)
  const ues = data?.results || []
  const semColor = SEM_TAB_COLORS[activeSem] || SEM_TAB_COLORS[1]

  const openCreate = () => {
    setForm({ ...EMPTY_UE, courses: [{ ...EMPTY_ECUE }] })
    setShowForm(true)
  }

  const openDetail = (ue) => {
    setSelectedUe(ue)
    setShowDetail(true)
  }

  const openEdit = (ue) => {
    const mapped = mapUeForForm(ue)
    setForm(mapped.courses.length ? mapped : { ...mapped, courses: [{ ...EMPTY_ECUE }] })
    setShowForm(true)
  }

  const addEcueRow = () => {
    setForm((prev) => ({
      ...prev,
      courses: [...prev.courses, {
        ...EMPTY_ECUE,
        code: prev.code ? suggestEcueCode(prev.code, prev.courses.length) : '',
      }],
    }))
  }

  const removeEcueRow = (index) => {
    setForm((prev) => ({
      ...prev,
      courses: prev.courses.filter((_, i) => i !== index),
    }))
  }

  const updateEcue = (index, field, value) => {
    setForm((prev) => ({
      ...prev,
      courses: prev.courses.map((c, i) => (i === index ? { ...c, [field]: value } : c)),
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.code?.trim() || !form.name?.trim()) {
      showToast('Code et intitulé UE obligatoires', 'warning')
      return
    }
    if (!stapsDept) {
      showToast('Aucun département STAPS configuré sur le serveur', 'danger')
      return
    }

    const courses = form.courses
      .filter((c) => c.name?.trim())
      .map((c, i) => ({
        ...c,
        code: c.code?.trim() || suggestEcueCode(form.code.trim(), i),
        name: c.name.trim(),
      }))

    if (!courses.length) {
      showToast('Ajoutez au moins un ECUE', 'warning')
      return
    }

    setSaving(true)
    try {
      const existingCourses = form.id
        ? (ues.find((u) => u.id === form.id)?.courses || [])
        : []

      await saveTeachingUnitWithCourses({
        ue: form,
        courses,
        departmentId: stapsDept.id,
        semesterNumber: activeSem,
        existingCourses,
      })

      showToast(form.id ? 'UE et ECUE mis à jour' : 'UE et ECUE créés', 'success')
      setShowForm(false)
      reload()
    } catch (err) {
      const detail = err.data ? JSON.stringify(err.data) : err.message
      showToast(detail || 'Erreur lors de l\'enregistrement', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (ue) => {
    if (!window.confirm(`Supprimer l'UE ${ue.code} et ses ECUE ?`)) return
    try {
      await deleteTeachingUnit(ue.id)
      showToast('UE supprimée', 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Erreur lors de la suppression', 'danger')
    }
  }

  const activeSemInfo = SEMESTRES.find((s) => s.id === activeSem)

  return (
    <>
      <PageHeader
        title="Unités d'Enseignement (UE)"
        subtitle={`Maquette pédagogique LMD — ${data?.count ?? 0} UE au S${activeSem}`}
        action={<button type="button" className="btn btn-injs-primary" onClick={openCreate}>+ Créer une UE</button>}
      />

      <div className="ue-sem-tabs mb-4">
        {SEMESTRES.map((s) => {
          const colors = SEM_TAB_COLORS[s.id]
          const active = activeSem === s.id
          return (
            <button
              key={s.id}
              type="button"
              className={`ue-sem-tab ${active ? 'active' : ''}`}
              style={{
                '--sem-bg': colors.bg,
                '--sem-soft': colors.soft,
                '--sem-border': colors.border,
              }}
              onClick={() => setActiveSem(s.id)}
            >
              <span className="ue-sem-tab-code">{s.label}</span>
              <span className="ue-sem-tab-meta">{s.niveau} · {s.type}</span>
            </button>
          )
        })}
      </div>

      {activeSemInfo && (
        <div
          className="ue-sem-banner mb-4"
          style={{
            '--sem-bg': semColor.bg,
            '--sem-soft': semColor.soft,
            '--sem-border': semColor.border,
          }}
        >
          Semestre {activeSemInfo.label} — {activeSemInfo.niveau} — {activeSemInfo.credits} CECT — {activeSemInfo.type}
          {stapsDept ? ` | Département : ${stapsDept.label}` : ''}
        </div>
      )}

      {loading && <div className="text-center py-5"><div className="spinner-border text-primary" /></div>}
      {error && <div className="alert alert-danger">Erreur : {error}</div>}

      {!loading && !error && (
        ues.length === 0 ? (
          <div className="card-injs p-4 text-muted text-center">
            Aucune UE pour ce semestre — créez-en une.
          </div>
        ) : (
          <div className="row g-3">
            {ues.map((ue) => (
              <div key={ue.id} className="col-md-6 col-xl-4">
                <div
                  className="ue-plaque h-100"
                  style={{
                    '--sem-bg': semColor.bg,
                    '--sem-soft': semColor.soft,
                    '--sem-border': semColor.border,
                  }}
                >
                  <div className="ue-plaque-header">
                    <div>
                      <code className="ue-plaque-code">{ue.code}</code>
                      <div className="ue-plaque-title">{ue.name}</div>
                      <span className="ue-plaque-credits">{ue.credits_ects} CECT</span>
                    </div>
                    <IconActionButtons
                      actions={[
                        { type: 'view', title: 'Voir', onClick: () => openDetail(ue) },
                        { type: 'edit', title: 'Modifier', onClick: () => openEdit(ue) },
                        { type: 'delete', title: 'Supprimer', onClick: () => handleDelete(ue) },
                      ]}
                    />
                  </div>

                  <div className="ue-plaque-ecue-label">
                    ECUE ({(ue.courses || []).length})
                  </div>
                  <div className="ue-ecue-list">
                    {(ue.courses || []).length === 0 ? (
                      <span className="text-muted small">Aucun ECUE</span>
                    ) : (ue.courses || []).map((c) => (
                      <div key={c.id || c.code} className="ue-ecue-chip">
                        <div className="ue-ecue-main">
                          <code>{c.code}</code>
                          <span className="ue-ecue-name">{c.name}</span>
                        </div>
                        <span className="ue-ecue-hours">
                          CM {c.hours_cm || 0}h · TD {c.hours_td || 0}h · TP {c.hours_tp || 0}h
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      <Modal
        show={showDetail}
        onClose={() => { setShowDetail(false); setSelectedUe(null) }}
        title={selectedUe ? `Fiche UE — ${selectedUe.code}` : 'Fiche UE'}
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
                if (selectedUe) openEdit(selectedUe)
              }}
            >
              <FiEdit2 size={16} />
            </button>
          </>
        }
      >
        {selectedUe && (
          <>
            <dl className="detail-view mb-4">
              <div className="detail-row"><dt>Code</dt><dd><code>{selectedUe.code}</code></dd></div>
              <div className="detail-row"><dt>Intitulé</dt><dd>{selectedUe.name}</dd></div>
              <div className="detail-row"><dt>Semestre</dt><dd>S{activeSem}</dd></div>
              <div className="detail-row"><dt>CECT</dt><dd>{selectedUe.credits_ects}</dd></div>
              <div className="detail-row"><dt>Description</dt><dd>{selectedUe.description || '—'}</dd></div>
            </dl>
            <h6 className="fw-bold mb-2">ECUE ({(selectedUe.courses || []).length})</h6>
            {(selectedUe.courses || []).length === 0 ? (
              <p className="text-muted mb-0">Aucun ECUE associé.</p>
            ) : (
              <div className="ue-ecue-list">
                {(selectedUe.courses || []).map((c) => (
                  <div key={c.id || c.code} className="ue-ecue-chip">
                    <div className="ue-ecue-main">
                      <code>{c.code}</code>
                      <span className="ue-ecue-name">{c.name}</span>
                    </div>
                    <span className="ue-ecue-hours">
                      CM {c.hours_cm || 0}h · TD {c.hours_td || 0}h · TP {c.hours_tp || 0}h
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </Modal>

      <Modal
        show={showForm}
        onClose={() => setShowForm(false)}
        title={form.id ? `Modifier l'UE — S${activeSem}` : `Créer une UE — S${activeSem}`}
        size="lg"
        footer={
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            <button type="submit" form="ue-form" className="btn btn-injs-primary" disabled={saving}>
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="ue-form" onSubmit={handleSubmit}>
          <div className="row g-3 mb-4">
            <div className="col-md-4">
              <label className="form-label">Code UE *</label>
              <input
                className="form-control"
                required
                value={form.code}
                onChange={(ev) => setForm({ ...form, code: ev.target.value.toUpperCase() })}
                disabled={!!form.id}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label">Crédits (CECT)</label>
              <input
                type="number"
                min="1"
                max="30"
                className="form-control"
                value={form.credits_ects}
                onChange={(ev) => setForm({ ...form, credits_ects: ev.target.value })}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label">Semestre</label>
              <input className="form-control" value={`S${activeSem}`} disabled />
            </div>
            <div className="col-12">
              <label className="form-label">Intitulé UE *</label>
              <input
                className="form-control"
                required
                value={form.name}
                onChange={(ev) => setForm({ ...form, name: ev.target.value })}
              />
            </div>
            <div className="col-12">
              <label className="form-label">Description</label>
              <textarea
                className="form-control"
                rows={2}
                value={form.description}
                onChange={(ev) => setForm({ ...form, description: ev.target.value })}
              />
            </div>
          </div>

          <div className="d-flex justify-content-between align-items-center mb-2">
            <h6 className="fw-bold mb-0">ECUE (éléments constitutifs)</h6>
            <button type="button" className="btn btn-sm btn-outline-primary" onClick={addEcueRow}>+ ECUE</button>
          </div>

          {form.courses.map((course, index) => (
            <div key={course.id || `new-${index}`} className="border rounded p-3 mb-2">
              <div className="row g-2">
                <div className="col-md-3">
                  <label className="form-label small">Code ECUE</label>
                  <input
                    className="form-control form-control-sm"
                    value={course.code}
                    placeholder={form.code ? suggestEcueCode(form.code, index) : ''}
                    onChange={(ev) => updateEcue(index, 'code', ev.target.value.toUpperCase())}
                  />
                </div>
                <div className="col-md-9">
                  <label className="form-label small">Intitulé ECUE *</label>
                  <input
                    className="form-control form-control-sm"
                    required
                    value={course.name}
                    onChange={(ev) => updateEcue(index, 'name', ev.target.value)}
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label small">CM (h)</label>
                  <input type="number" min="0" className="form-control form-control-sm" value={course.hours_cm} onChange={(ev) => updateEcue(index, 'hours_cm', ev.target.value)} />
                </div>
                <div className="col-md-4">
                  <label className="form-label small">TD (h)</label>
                  <input type="number" min="0" className="form-control form-control-sm" value={course.hours_td} onChange={(ev) => updateEcue(index, 'hours_td', ev.target.value)} />
                </div>
                <div className="col-md-3">
                  <label className="form-label small">TP (h)</label>
                  <input type="number" min="0" className="form-control form-control-sm" value={course.hours_tp} onChange={(ev) => updateEcue(index, 'hours_tp', ev.target.value)} />
                </div>
                <div className="col-md-1 d-flex align-items-end">
                  {form.courses.length > 1 && (
                    <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => removeEcueRow(index)}>×</button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </form>
      </Modal>
    </>
  )
}
