import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

const MENTION_LABELS = {
  TRES_BIEN:   'Très bien',
  BIEN:        'Bien',
  ASSEZ_BIEN:  'Assez bien',
  PASSABLE:    'Passable',
  INSUFFISANT: 'Insuffisant',
  '':          '—',
}
const MENTION_COLORS = {
  TRES_BIEN:   { background: '#e8f5e9', color: '#1b5e20' },
  BIEN:        { background: '#e3f2fd', color: '#0d47a1' },
  ASSEZ_BIEN:  { background: '#e8eaf6', color: '#283593' },
  PASSABLE:    { background: '#fff8e1', color: '#f57f17' },
  INSUFFISANT: { background: '#ffebee', color: '#b71c1c' },
  '':          { background: '#f5f5f5', color: '#9e9e9e' },
}

function mentionAuto(note) {
  if (note === null || note === '' || isNaN(parseFloat(note))) return ''
  const n = parseFloat(note)
  if (n >= 16) return 'TRES_BIEN'
  if (n >= 14) return 'BIEN'
  if (n >= 12) return 'ASSEZ_BIEN'
  if (n >= 10) return 'PASSABLE'
  return 'INSUFFISANT'
}

function MentionBadge({ mention }) {
  const style = MENTION_COLORS[mention] || MENTION_COLORS['']
  return (
    <span style={{ ...style, fontSize: '0.72rem', fontWeight: 700, padding: '2px 9px', borderRadius: '20px', whiteSpace: 'nowrap' }}>
      {MENTION_LABELS[mention] || '—'}
    </span>
  )
}

export default function NotesModule() {
  const { formationId, moduleId } = useParams()
  const { showToast } = useToast()

  const [module, setModule]   = useState(null)
  const [notes, setNotes]     = useState([])   // [{ participant_id, nom, prenom, ... }]
  const [draft, setDraft]     = useState({})   // { [participant_id]: { note, mention, observations } }
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [search, setSearch]   = useState('')
  const [dirty, setDirty]     = useState(false)
  const inputRefs = useRef({})

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [modRes, notesRes] = await Promise.all([
        api.get(`/formations/${formationId}/modules/${moduleId}/`),
        api.get(`/formations/${formationId}/modules/${moduleId}/notes/`),
      ])
      setModule(modRes.data)
      setNotes(notesRes.data)
      const init = {}
      notesRes.data.forEach(n => {
        init[n.participant_id] = {
          note: n.note !== null && n.note !== undefined ? String(n.note) : '',
          mention: n.mention || '',
          observations: n.observations || '',
        }
      })
      setDraft(init)
      setDirty(false)
    } catch {
      showToast('Erreur lors du chargement', 'error')
    } finally {
      setLoading(false)
    }
  }, [formationId, moduleId, showToast])

  useEffect(() => { fetchData() }, [fetchData])

  const updateDraft = (pid, field, value) => {
    setDraft(d => {
      const prev = d[pid] || { note: '', mention: '', observations: '' }
      const updated = { ...prev, [field]: value }
      if (field === 'note') {
        updated.mention = mentionAuto(value)
      }
      return { ...d, [pid]: updated }
    })
    setDirty(true)
  }

  const handleSaveAll = async () => {
    setSaving(true)
    try {
      const payload = Object.entries(draft)
        .filter(([, v]) => v.note !== '' || v.mention !== '' || v.observations !== '')
        .map(([pid, v]) => ({
          participant_id: parseInt(pid),
          note: v.note !== '' ? parseFloat(v.note) : null,
          mention: v.mention,
          observations: v.observations,
        }))
      const { data } = await api.post(
        `/formations/${formationId}/modules/${moduleId}/notes/bulk/`,
        { notes: payload },
      )
      if (data.errors && data.errors.length > 0) {
        showToast(`${data.saved} note(s) sauvegardée(s), ${data.errors.length} erreur(s)`, 'warning')
      } else {
        showToast(`${data.saved} note(s) sauvegardée(s) avec succès`, 'success')
      }
      setDirty(false)
      fetchData()
    } catch {
      showToast('Erreur lors de la sauvegarde', 'error')
    } finally {
      setSaving(false)
    }
  }

  const filtered = notes.filter(n =>
    !search ||
    n.nom.toLowerCase().includes(search.toLowerCase()) ||
    n.prenom.toLowerCase().includes(search.toLowerCase()) ||
    n.matricule.toLowerCase().includes(search.toLowerCase()) ||
    (n.grade || '').toLowerCase().includes(search.toLowerCase())
  )

  const stats = notes.reduce((acc, n) => {
    const d = draft[n.participant_id]
    const mention = d?.mention || n.mention || ''
    if (mention) acc[mention] = (acc[mention] || 0) + 1
    const noteVal = d?.note !== undefined && d?.note !== '' ? parseFloat(d.note) : n.note
    if (noteVal !== null && noteVal !== undefined && !isNaN(noteVal)) {
      acc._sum = (acc._sum || 0) + noteVal
      acc._count = (acc._count || 0) + 1
    }
    return acc
  }, {})
  const moyenne = stats._count ? (stats._sum / stats._count).toFixed(2) : null
  const nbSaisies = notes.filter(n => {
    const d = draft[n.participant_id]
    return (d?.note !== '' && d?.note !== undefined) || n.note !== null
  }).length

  if (loading) return <div className="loading"><div className="spinner"></div></div>

  return (
    <div>
      {/* En-tête */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 style={{ margin: 0, fontWeight: 700 }}>Notes — {module?.intitule}</h2>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            {notes.length} auditeur{notes.length !== 1 ? 's' : ''} inscrits · {nbSaisies} note{nbSaisies !== 1 ? 's' : ''} saisie{nbSaisies !== 1 ? 's' : ''}
            {moyenne && <> · Moyenne&nbsp;<strong>{moyenne}/20</strong></>}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <Link to={`/formations/${module?.formation ?? formationId}/modules/${moduleId}`} className="btn btn-sm btn-outline-secondary">
            <i className="bi bi-arrow-left me-1"></i>Retour au module
          </Link>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleSaveAll}
            disabled={saving || !dirty}
          >
            {saving
              ? <><span className="spinner-border spinner-border-sm me-1"></span>Sauvegarde…</>
              : <><i className="bi bi-floppy me-1"></i>Enregistrer tout</>}
          </button>
        </div>
      </div>

      {/* KPIs mentions */}
      {notes.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
          {['TRES_BIEN', 'BIEN', 'ASSEZ_BIEN', 'PASSABLE', 'INSUFFISANT'].map(m => (
            <div key={m} className="card" style={{ padding: '0.6rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MentionBadge mention={m} />
              <span style={{ fontWeight: 700 }}>{stats[m] || 0}</span>
            </div>
          ))}
        </div>
      )}

      {/* Recherche */}
      <div style={{ marginBottom: '1rem' }}>
        <input
          className="form-control"
          placeholder="Rechercher par nom, matricule, grade…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ maxWidth: 360 }}
        />
      </div>

      {notes.length === 0 ? (
        <div className="empty-state">
          <i className="bi bi-people" style={{ fontSize: '3rem', color: 'var(--text-muted)' }}></i>
          <p>Aucun auditeur inscrit à ce module</p>
        </div>
      ) : (
        <div className="card" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)', background: 'var(--bg-secondary, #f9fafb)' }}>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 700, whiteSpace: 'nowrap' }}>Auditeur</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'left', fontWeight: 700 }}>Grade</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700, minWidth: 100 }}>Note /20</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontWeight: 700 }}>Mention</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'left', fontWeight: 700 }}>Observations</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'left', fontWeight: 700, color: 'var(--text-muted)', fontSize: '0.78rem' }}>Saisi par</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((n, idx) => {
                const d = draft[n.participant_id] || { note: '', mention: '', observations: '' }
                const noteNum = d.note !== '' ? parseFloat(d.note) : null
                const isValid = d.note === '' || (noteNum !== null && !isNaN(noteNum) && noteNum >= 0 && noteNum <= 20)
                return (
                  <tr key={n.participant_id} style={{ borderBottom: '1px solid var(--border)', background: idx % 2 === 0 ? 'transparent' : 'var(--bg-secondary, #fafafa)' }}>
                    {/* Auditeur */}
                    <td style={{ padding: '0.65rem 1rem', whiteSpace: 'nowrap' }}>
                      <div style={{ fontWeight: 600 }}>{n.nom} {n.prenom}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{n.matricule}</div>
                    </td>
                    {/* Grade */}
                    <td style={{ padding: '0.65rem 0.5rem' }}>
                      {n.grade && (
                        <span style={{ fontSize: '0.78rem', background: '#e8eaf6', color: '#283593', padding: '2px 8px', borderRadius: '20px', fontWeight: 600 }}>
                          {n.grade}
                        </span>
                      )}
                    </td>
                    {/* Note */}
                    <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                      <input
                        ref={el => { inputRefs.current[n.participant_id] = el }}
                        type="number"
                        step="0.25"
                        value={d.note}
                        onChange={e => updateDraft(n.participant_id, 'note', e.target.value)}
                        style={{
                          width: 72, textAlign: 'center', padding: '4px 6px',
                          border: `1.5px solid ${isValid ? 'var(--border)' : '#e53935'}`,
                          borderRadius: 6, fontSize: '0.9rem', fontWeight: 600,
                          background: d.note !== '' && isValid ? (noteNum >= 10 ? '#f1f8e9' : '#fff8f8') : '',
                        }}
                        placeholder="—"
                        onKeyDown={e => {
                          if (e.key === 'Enter' || e.key === 'Tab') {
                            const ids = filtered.map(x => x.participant_id)
                            const cur = ids.indexOf(n.participant_id)
                            const next = ids[cur + 1]
                            if (next && inputRefs.current[next]) {
                              e.preventDefault()
                              inputRefs.current[next].focus()
                            }
                          }
                        }}
                      />
                      {!isValid && (
                        <div style={{ fontSize: '0.68rem', color: '#e53935', marginTop: 2 }}>0–20</div>
                      )}
                    </td>
                    {/* Mention */}
                    <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                      <MentionBadge mention={d.mention} />
                    </td>
                    {/* Observations */}
                    <td style={{ padding: '0.65rem 0.5rem', minWidth: 180 }}>
                      <input
                        type="text"
                        value={d.observations}
                        onChange={e => updateDraft(n.participant_id, 'observations', e.target.value)}
                        style={{ width: '100%', padding: '4px 8px', border: '1.5px solid var(--border)', borderRadius: 6, fontSize: '0.82rem' }}
                        placeholder="Observations…"
                      />
                    </td>
                    {/* Saisie par */}
                    <td style={{ padding: '0.65rem 0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {n.saisie_par || '—'}
                      {n.updated_at && (
                        <div style={{ fontSize: '0.68rem' }}>
                          {new Date(n.updated_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' })}
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Barre flottante de sauvegarde */}
      {dirty && (
        <div style={{
          position: 'fixed', bottom: '1.5rem', right: '1.5rem',
          background: 'var(--primary)', color: '#fff',
          borderRadius: 12, padding: '0.75rem 1.25rem',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
          display: 'flex', alignItems: 'center', gap: '0.75rem', zIndex: 999,
        }}>
          <i className="bi bi-exclamation-circle"></i>
          <span style={{ fontSize: '0.875rem' }}>Modifications non sauvegardées</span>
          <button className="btn btn-sm" style={{ background: '#fff', color: 'var(--primary)', fontWeight: 700 }}
            onClick={handleSaveAll} disabled={saving}>
            {saving ? 'Sauvegarde…' : 'Enregistrer'}
          </button>
        </div>
      )}
    </div>
  )
}
