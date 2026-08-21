import { useState } from 'react'
import { FiPlus, FiTrash2 } from 'react-icons/fi'
import Modal from '../../../components/common/Modal'
import { useToast } from '../../../context/ToastContext'
import { useFetch } from '../../../hooks/useFetch'
import {
  fetchFormationPeriods,
  createFormationPeriod,
  fetchHolidays,
  createHoliday,
  deleteHoliday,
  fetchAcademicYears,
  fetchPrograms,
} from '../../../api/academics'

const EMPTY_PERIOD = {
  label: '',
  academic_year: '',
  program: '',
  start_date: '',
  end_date: '',
  weekly_rhythm: 'full',
  is_active: true,
}

const RHYTHMS = [
  { value: 'full', label: 'Toutes les semaines' },
  { value: 'w1', label: '1re semaine du mois' },
  { value: 'w1_2', label: '2 premières semaines du mois' },
  { value: 'w1_3', label: '3 premières semaines du mois' },
]

export default function PeriodesPanel({ onChanged }) {
  const { showToast } = useToast()
  const { data: periodsData, reload } = useFetch(() => fetchFormationPeriods({ page_size: 100 }), [])
  const { data: holidaysData, reload: reloadHolidays } = useFetch(() => fetchHolidays({ page_size: 200 }), [])
  const { data: years } = useFetch(() => fetchAcademicYears(), [])
  const { data: programsData } = useFetch(() => fetchPrograms(), [])
  const programs = programsData || []
  const periods = periodsData?.results || []
  const holidays = holidaysData?.results || []

  const [showPeriod, setShowPeriod] = useState(false)
  const [form, setForm] = useState(EMPTY_PERIOD)
  const [holiday, setHoliday] = useState({ date: '', label: '' })
  const [saving, setSaving] = useState(false)

  const currentYear = (years || []).find((row) => row.is_current) || (years || [])[0]
  const institution = currentYear?.institution

  const submitPeriod = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await createFormationPeriod({
        ...form,
        academic_year: form.academic_year || currentYear?.id,
        program: form.program || null,
      })
      showToast('Période créée', 'success')
      setShowPeriod(false)
      setForm(EMPTY_PERIOD)
      reload()
      onChanged?.()
    } catch (err) {
      showToast(err.message || 'Création impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const submitHoliday = async (event) => {
    event.preventDefault()
    if (!institution) {
      showToast('Aucune institution liée à l’année académique courante', 'warning')
      return
    }
    setSaving(true)
    try {
      await createHoliday({ ...holiday, institution, is_active: true })
      showToast('Jour férié ajouté', 'success')
      setHoliday({ date: '', label: '' })
      reloadHolidays()
    } catch (err) {
      showToast(err.message || 'Ajout impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const removeHoliday = async (row) => {
    if (!window.confirm(`Supprimer ${row.label} ?`)) return
    try {
      await deleteHoliday(row.id)
      showToast('Jour férié retiré', 'success')
      reloadHolidays()
    } catch (err) {
      showToast(err.message || 'Suppression impossible', 'danger')
    }
  }

  return (
    <div className="row g-3">
      <div className="col-lg-7">
        <div className="card-injs">
          <div className="d-flex justify-content-between align-items-center p-3 border-bottom">
            <h2 className="h6 mb-0">Périodes de formation</h2>
            <button type="button" className="btn btn-injs-primary btn-sm" onClick={() => setShowPeriod(true)}>
              <FiPlus className="me-1" /> Nouvelle période
            </button>
          </div>
          <div className="table-responsive">
            <table className="table table-hover mb-0">
              <thead>
                <tr>
                  <th>Libellé</th>
                  <th>Dates</th>
                  <th>Rythme</th>
                  <th>Formation</th>
                </tr>
              </thead>
              <tbody>
                {periods.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <strong>{row.label}</strong>
                      {!row.is_active && <span className="badge bg-secondary ms-2">inactive</span>}
                    </td>
                    <td>{row.start_date} → {row.end_date}</td>
                    <td>{row.weekly_rhythm_display}</td>
                    <td>{row.program_name || 'Toutes'}</td>
                  </tr>
                ))}
                {periods.length === 0 && (
                  <tr><td colSpan={4} className="text-muted p-4">Aucune période. Créez-en une avant de générer un EDT.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="col-lg-5">
        <div className="card-injs p-3 mb-3">
          <h2 className="h6 mb-3">Ajouter un jour férié</h2>
          <form className="row g-2" onSubmit={submitHoliday}>
            <div className="col-6">
              <input type="date" className="form-control" required value={holiday.date} onChange={(e) => setHoliday({ ...holiday, date: e.target.value })} />
            </div>
            <div className="col-6">
              <input className="form-control" required placeholder="Libellé" value={holiday.label} onChange={(e) => setHoliday({ ...holiday, label: e.target.value })} />
            </div>
            <div className="col-12">
              <button type="submit" className="btn btn-outline-primary btn-sm" disabled={saving}>Enregistrer</button>
            </div>
          </form>
        </div>
        <div className="card-injs">
          <div className="p-3 border-bottom fw-semibold">Jours exclus de la génération</div>
          <ul className="list-group list-group-flush">
            {holidays.map((row) => (
              <li key={row.id} className="list-group-item d-flex justify-content-between align-items-center">
                <span>{row.date} — {row.label}</span>
                <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => removeHoliday(row)} aria-label="Supprimer">
                  <FiTrash2 />
                </button>
              </li>
            ))}
            {holidays.length === 0 && <li className="list-group-item text-muted">Aucun jour férié.</li>}
          </ul>
        </div>
      </div>

      <Modal
        show={showPeriod}
        onClose={() => setShowPeriod(false)}
        title="Nouvelle période de formation"
        footer={(
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowPeriod(false)}>Annuler</button>
            <button type="submit" form="period-form" className="btn btn-injs-primary" disabled={saving}>Créer</button>
          </>
        )}
      >
        <form id="period-form" onSubmit={submitPeriod} className="row g-3">
          <div className="col-12">
            <label className="form-label">Libellé</label>
            <input className="form-control" required value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} placeholder="Semestre 1" />
          </div>
          <div className="col-md-6">
            <label className="form-label">Début</label>
            <input type="date" className="form-control" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label">Fin</label>
            <input type="date" className="form-control" required value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label">Année académique</label>
            <select className="form-select" value={form.academic_year} onChange={(e) => setForm({ ...form, academic_year: e.target.value })}>
              <option value="">Année courante</option>
              {(years || []).map((row) => <option key={row.id} value={row.id}>{row.label}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label">Formation (optionnel)</label>
            <select className="form-select" value={form.program} onChange={(e) => setForm({ ...form, program: e.target.value })}>
              <option value="">Toutes les filières</option>
              {programs.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
            </select>
          </div>
          <div className="col-12">
            <label className="form-label">Rythme</label>
            <select className="form-select" value={form.weekly_rhythm} onChange={(e) => setForm({ ...form, weekly_rhythm: e.target.value })}>
              {RHYTHMS.map((row) => <option key={row.value} value={row.value}>{row.label}</option>)}
            </select>
          </div>
        </form>
      </Modal>
    </div>
  )
}
