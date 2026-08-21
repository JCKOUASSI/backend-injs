import { useState } from 'react'
import { FiZap, FiUpload } from 'react-icons/fi'
import { useToast } from '../../../context/ToastContext'
import {
  generatePeriodSchedule,
  expandWeeklySchedule,
  publishSeances,
} from '../../../api/faculty'

export default function GenerationPanel({ filters, onChanged }) {
  const { showToast } = useToast()
  const [saving, setSaving] = useState(false)
  const [replaceExisting, setReplaceExisting] = useState(false)
  const [autoLoads, setAutoLoads] = useState(true)
  const [result, setResult] = useState(null)

  const period = filters.period
  const promotion = filters.promotion

  const requireScope = () => {
    if (!period || !promotion) {
      showToast('Choisissez une période et une promotion dans la barre du haut.', 'warning')
      return false
    }
    return true
  }

  const runGenerate = async (dryRun) => {
    if (!requireScope()) return
    setSaving(true)
    try {
      const payload = await generatePeriodSchedule({
        period,
        promotion,
        dry_run: dryRun,
        replace_existing: replaceExisting,
        auto_create_loads: autoLoads,
      })
      setResult(payload)
      const tone = payload.failures?.length ? 'warning' : 'success'
      showToast(
        `${dryRun ? 'Prévisualisation' : 'Génération'} : ${payload.created} séance(s), ${payload.failures?.length || 0} reliquat(s)`,
        tone,
      )
      if (!dryRun) onChanged?.()
    } catch (err) {
      showToast(err.message || 'Génération impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const runExpand = async () => {
    if (!requireScope()) return
    setSaving(true)
    try {
      const payload = await expandWeeklySchedule({ period, promotion, replace_existing: replaceExisting })
      setResult(payload)
      showToast(`${payload.created} séance(s) issues de la grille hebdomadaire`, 'success')
      onChanged?.()
    } catch (err) {
      showToast(err.message || 'Extension impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  const runPublish = async () => {
    if (!requireScope()) return
    setSaving(true)
    try {
      const payload = await publishSeances({ period, promotion })
      showToast(`${payload.published} séance(s) publiée(s)`, 'success')
      onChanged?.()
    } catch (err) {
      showToast(err.message || 'Publication impossible', 'danger')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="row g-3">
      <div className="col-lg-5">
        <div className="card-injs p-4">
          <h2 className="h6 mb-3">Générer les séances d’une période</h2>
          <p className="text-muted small">
            Le moteur place les volumes horaires des ECUE sur les jours ouvrés de la période,
            en tenant compte des salles, des professeurs, des groupes et des jours fériés.
          </p>
          <div className="form-check mb-2">
            <input id="auto-loads" className="form-check-input" type="checkbox" checked={autoLoads} onChange={(e) => setAutoLoads(e.target.checked)} />
            <label className="form-check-label" htmlFor="auto-loads">Créer les charges à partir de la maquette si besoin</label>
          </div>
          <div className="form-check mb-3">
            <input id="replace" className="form-check-input" type="checkbox" checked={replaceExisting} onChange={(e) => setReplaceExisting(e.target.checked)} />
            <label className="form-check-label" htmlFor="replace">Remplacer les séances encore en brouillon / générées</label>
          </div>
          <div className="d-flex flex-wrap gap-2">
            <button type="button" className="btn btn-outline-secondary" disabled={saving} onClick={() => runGenerate(true)}>
              Prévisualiser
            </button>
            <button type="button" className="btn btn-injs-primary" disabled={saving} onClick={() => runGenerate(false)}>
              <FiZap className="me-1" /> Générer
            </button>
          </div>
          <hr />
          <p className="small text-muted">Vous avez déjà une grille hebdomadaire ? Étendez-la en séances datées.</p>
          <button type="button" className="btn btn-outline-primary btn-sm" disabled={saving} onClick={runExpand}>
            Étendre la grille hebdomadaire
          </button>
          <hr />
          <button type="button" className="btn btn-success" disabled={saving} onClick={runPublish}>
            <FiUpload className="me-1" /> Publier les séances de ce périmètre
          </button>
        </div>
      </div>
      <div className="col-lg-7">
        <div className="card-injs p-4">
          <h2 className="h6 mb-3">Dernier résultat</h2>
          {!result && <p className="text-muted mb-0">Lancez une génération pour voir le détail ici.</p>}
          {result && (
            <>
              <p className="mb-2">
                <strong>{result.created || 0}</strong> séance(s)
                {result.eligible_dates != null && <> · {result.eligible_dates} jour(s) ouvrable(s)</>}
                {result.holidays != null && <> · {result.holidays} jour(s) férié(s)</>}
              </p>
              {result.failures?.length > 0 && (
                <div className="alert alert-warning">
                  <div className="fw-semibold mb-1">Volumes non placés</div>
                  <ul className="mb-0 small">
                    {result.failures.map((row, index) => (
                      <li key={index}>{row.reason || `${row.course} (${row.kind})`}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.slots?.length > 0 && (
                <div className="table-responsive" style={{ maxHeight: 360 }}>
                  <table className="table table-sm">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Horaire</th>
                        <th>ECUE</th>
                        <th>Salle</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.slots.slice(0, 40).map((slot, index) => (
                        <tr key={slot.id || index}>
                          <td>{slot.date}</td>
                          <td>{slot.start_time}–{slot.end_time}</td>
                          <td>{slot.course_code} · {slot.kind}</td>
                          <td>{slot.room_code || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
