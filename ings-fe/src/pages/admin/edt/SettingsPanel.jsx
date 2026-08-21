import { useEffect, useState } from 'react'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import { fetchDefaultPlanningSettings, updateDefaultPlanningSettings } from '../../../api/faculty'

function hhmm(value) {
  return String(value || '').slice(0, 5)
}

export default function SettingsPanel() {
  const { showToast } = useToast()
  const { data, loading, error, reload } = useFetch(() => fetchDefaultPlanningSettings(), [])
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setForm({
      morning_start: hhmm(data.morning_start),
      morning_end: hhmm(data.morning_end),
      afternoon_start: hhmm(data.afternoon_start),
      afternoon_end: hhmm(data.afternoon_end),
      session_duration_minutes: data.session_duration_minutes ?? 120,
      max_sessions_per_day: data.max_sessions_per_day ?? 3,
      capacity_tolerance: data.capacity_tolerance ?? 0,
      late_after_minutes: data.late_after_minutes ?? 15,
      partial_under_percent: data.partial_under_percent ?? 75,
      auto_absent_after_minutes: data.auto_absent_after_minutes ?? 60,
      lock_room_per_group: Boolean(data.lock_room_per_group),
      spread_remainder: Boolean(data.spread_remainder),
    })
  }, [data])

  const setField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const save = async (event) => {
    event.preventDefault()
    if (!form) return
    setSaving(true)
    try {
      await updateDefaultPlanningSettings(form)
      showToast('Réglages enregistrés', 'success')
      reload()
    } catch (err) {
      showToast(err.message || 'Enregistrement impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !form) {
    return <div className="text-center py-4"><div className="spinner-border spinner-border-sm text-primary" /></div>
  }
  if (error) return <div className="alert alert-danger">{error}</div>
  if (!form) return null

  return (
    <form className="card-injs p-4" onSubmit={save}>
      <h2 className="h6 mb-3">Réglages par défaut de l’établissement</h2>
      <p className="small text-muted">
        Horaires du moteur, capacité des salles, et règles de présence (retard, partiel, auto-absence).
      </p>

      <div className="row g-3">
        <div className="col-6 col-md-3">
          <label className="form-label">Matin — début</label>
          <input type="time" className="form-control" value={form.morning_start} onChange={(e) => setField('morning_start', e.target.value)} />
        </div>
        <div className="col-6 col-md-3">
          <label className="form-label">Matin — fin</label>
          <input type="time" className="form-control" value={form.morning_end} onChange={(e) => setField('morning_end', e.target.value)} />
        </div>
        <div className="col-6 col-md-3">
          <label className="form-label">Après-midi — début</label>
          <input type="time" className="form-control" value={form.afternoon_start} onChange={(e) => setField('afternoon_start', e.target.value)} />
        </div>
        <div className="col-6 col-md-3">
          <label className="form-label">Après-midi — fin</label>
          <input type="time" className="form-control" value={form.afternoon_end} onChange={(e) => setField('afternoon_end', e.target.value)} />
        </div>
        <div className="col-6 col-md-4">
          <label className="form-label">Durée d’une séance (min)</label>
          <input type="number" min={30} className="form-control" value={form.session_duration_minutes} onChange={(e) => setField('session_duration_minutes', Number(e.target.value))} />
        </div>
        <div className="col-6 col-md-4">
          <label className="form-label">Séances max / jour</label>
          <input type="number" min={1} className="form-control" value={form.max_sessions_per_day} onChange={(e) => setField('max_sessions_per_day', Number(e.target.value))} />
        </div>
        <div className="col-6 col-md-4">
          <label className="form-label">Tolérance capacité salle</label>
          <input type="number" min={0} className="form-control" value={form.capacity_tolerance} onChange={(e) => setField('capacity_tolerance', Number(e.target.value))} />
        </div>
        <div className="col-6 col-md-4">
          <label className="form-label">Retard après (min)</label>
          <input type="number" min={0} className="form-control" value={form.late_after_minutes} onChange={(e) => setField('late_after_minutes', Number(e.target.value))} />
        </div>
        <div className="col-6 col-md-4">
          <label className="form-label">Présence partielle sous (%)</label>
          <input type="number" min={1} max={100} className="form-control" value={form.partial_under_percent} onChange={(e) => setField('partial_under_percent', Number(e.target.value))} />
        </div>
        <div className="col-6 col-md-4">
          <label className="form-label">Auto-absence après la fin (min)</label>
          <input type="number" min={0} className="form-control" value={form.auto_absent_after_minutes} onChange={(e) => setField('auto_absent_after_minutes', Number(e.target.value))} />
        </div>
        <div className="col-12">
          <div className="form-check">
            <input id="lock-room" className="form-check-input" type="checkbox" checked={form.lock_room_per_group} onChange={(e) => setField('lock_room_per_group', e.target.checked)} />
            <label className="form-check-label" htmlFor="lock-room">Garder la même salle pour un groupe sur toute la période</label>
          </div>
          <div className="form-check">
            <input id="spread" className="form-check-input" type="checkbox" checked={form.spread_remainder} onChange={(e) => setField('spread_remainder', e.target.checked)} />
            <label className="form-check-label" htmlFor="spread">Étaler le reliquat horaire sur les séances déjà placées</label>
          </div>
        </div>
      </div>

      <button type="submit" className="btn btn-injs-primary mt-3" disabled={saving}>
        {saving ? 'Enregistrement…' : 'Enregistrer'}
      </button>
    </form>
  )
}
