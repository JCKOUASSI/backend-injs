import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link, useLocation } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

const STATUT_LABELS  = { BROUILLON: 'Brouillon', PUBLIE: 'Publié', FERME: 'Fermé' }
const STATUT_COLORS  = {
  BROUILLON: { background: '#fff3e0', color: '#e65100' },
  PUBLIE:    { background: '#e8f5e9', color: '#2e7d32' },
  FERME:     { background: '#f5f5f5', color: '#616161' },
}
const CIBLE_LABELS   = { COURS: 'Évaluation du cours', FORMATEUR: 'Évaluation du formateur' }
const TYPE_LABELS    = { NOTE: 'Note (1 à 5)', CHOIX_UN: 'Choix unique', CHOIX_MUL: 'Choix multiple', TEXTE: 'Texte libre' }
const TYPE_ICONS     = { NOTE: 'bi-star', CHOIX_UN: 'bi-ui-radios', CHOIX_MUL: 'bi-ui-checks', TEXTE: 'bi-chat-left-text' }

const EMPTY_QUESTION = { intitule: '', type_question: 'NOTE', ordre: 1, obligatoire: true, choix: [] }

function StarBar({ moyenne, total }) {
  const pct = moyenne ? (moyenne / 5) * 100 : 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
      <div style={{ position: 'relative', width: '120px', height: '12px', borderRadius: '6px', background: '#e0e0e0', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg,#f9a825,#ff6f00)', borderRadius: '6px', transition: 'width .4s' }} />
      </div>
      <span style={{ fontWeight: 700, fontSize: '1.1rem', color: '#e65100' }}>{moyenne ?? '—'}<span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>/5</span></span>
      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>({total} réponse{total !== 1 ? 's' : ''})</span>
    </div>
  )
}

function ChoixBar({ libelle, nb, total }) {
  const pct = total > 0 ? Math.round((nb / total) * 100) : 0
  return (
    <div style={{ marginBottom: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', fontSize: '0.85rem' }}>
        <span>{libelle}</span>
        <span style={{ fontWeight: 600 }}>{nb} ({pct}%)</span>
      </div>
      <div style={{ height: '8px', borderRadius: '4px', background: '#e0e0e0', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'var(--primary)', borderRadius: '4px', transition: 'width .4s' }} />
      </div>
    </div>
  )
}

export default function EvaluationDetail() {
  const { id } = useParams()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [tab, setTab] = useState('questions') // 'questions' | 'resultats'

  const [questionnaire, setQuestionnaire] = useState(null)
  const [resultats, setResultats]         = useState(null)
  const [loading, setLoading]             = useState(true)
  const [loadingRes, setLoadingRes]       = useState(false)

  // Question form
  const [showQForm, setShowQForm]   = useState(false)
  const [editingQ, setEditingQ]     = useState(null) // null = nouveau
  const [qForm, setQForm]           = useState(EMPTY_QUESTION)
  const [savingQ, setSavingQ]       = useState(false)
  const [newChoixLabel, setNewChoixLabel] = useState('')

  const fetchQuestionnaire = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get(`/evaluations/questionnaires/${id}/`)
      setQuestionnaire(data)
    } catch {
      showToast('Questionnaire introuvable', 'error')
      navigate('/evaluations')
    } finally {
      setLoading(false)
    }
  }, [id, showToast, navigate])

  const fetchResultats = useCallback(async () => {
    setLoadingRes(true)
    try {
      const { data } = await api.get(`/evaluations/questionnaires/${id}/resultats/`)
      setResultats(data)
    } catch {
      showToast('Erreur chargement résultats', 'error')
    } finally {
      setLoadingRes(false)
    }
  }, [id, showToast])

  useEffect(() => { fetchQuestionnaire() }, [fetchQuestionnaire])
  useEffect(() => { if (tab === 'resultats') fetchResultats() }, [tab, fetchResultats])

  // ── Statut ──────────────────────────────────────────────────────────────────
  const handleStatut = async (statut) => {
    try {
      await api.post(`/evaluations/questionnaires/${id}/statut/`, { statut })
      showToast(`Questionnaire ${STATUT_LABELS[statut].toLowerCase()}`, 'success')
      fetchQuestionnaire()
    } catch { showToast('Erreur changement de statut', 'error') }
  }

  // ── Questions ───────────────────────────────────────────────────────────────
  const openNewQuestion = () => {
    const nextOrdre = questionnaire?.questions?.length
      ? Math.max(...questionnaire.questions.map(q => q.ordre)) + 1
      : 1
    setEditingQ(null)
    setQForm({ ...EMPTY_QUESTION, ordre: nextOrdre })
    setNewChoixLabel('')
    setShowQForm(true)
  }

  const openEditQuestion = (q) => {
    setEditingQ(q)
    setQForm({
      intitule: q.intitule,
      type_question: q.type_question,
      ordre: q.ordre,
      obligatoire: q.obligatoire,
      choix: q.choix ? q.choix.map(c => ({ ...c })) : [],
    })
    setNewChoixLabel('')
    setShowQForm(true)
  }

  const addChoix = () => {
    if (!newChoixLabel.trim()) return
    const nextOrdre = qForm.choix.length + 1
    setQForm(f => ({ ...f, choix: [...f.choix, { libelle: newChoixLabel.trim(), ordre: nextOrdre }] }))
    setNewChoixLabel('')
  }

  const removeChoix = (idx) => {
    setQForm(f => ({ ...f, choix: f.choix.filter((_, i) => i !== idx) }))
  }

  const saveQuestion = async (e) => {
    e.preventDefault()
    if (!qForm.intitule.trim()) { showToast('L\'intitulé est requis', 'error'); return }
    if (['CHOIX_UN', 'CHOIX_MUL'].includes(qForm.type_question) && qForm.choix.length < 2) {
      showToast('Ajoutez au moins 2 choix', 'error'); return
    }
    setSavingQ(true)
    try {
      if (editingQ) {
        await api.patch(`/evaluations/questionnaires/${id}/questions/${editingQ.id}/`, qForm)
        showToast('Question mise à jour', 'success')
      } else {
        await api.post(`/evaluations/questionnaires/${id}/questions/`, qForm)
        showToast('Question ajoutée', 'success')
      }
      setShowQForm(false)
      fetchQuestionnaire()
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data?.intitule?.[0] || 'Erreur lors de la sauvegarde'
      showToast(msg, 'error')
    } finally { setSavingQ(false) }
  }

  const deleteQuestion = async (qid) => {
    if (!window.confirm('Supprimer cette question ?')) return
    try {
      await api.delete(`/evaluations/questionnaires/${id}/questions/${qid}/`)
      showToast('Question supprimée', 'success')
      fetchQuestionnaire()
    } catch (err) {
      showToast(err?.response?.data?.detail || 'Erreur suppression', 'error')
    }
  }

  const isLocked = questionnaire?.statut === 'PUBLIE'

  if (loading) return <div className="loading"><div className="spinner"></div></div>
  if (!questionnaire) return null

  const totalReponses = resultats?.nb_soumissions ?? 0

  return (
    <div>
      {/* En-tête */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
              <span style={{ ...STATUT_COLORS[questionnaire.statut], fontSize: '0.72rem', fontWeight: 700, padding: '2px 10px', borderRadius: '20px', letterSpacing: '0.04em' }}>
                {STATUT_LABELS[questionnaire.statut]}
              </span>
              <span style={{ fontSize: '0.72rem', background: '#e3f2fd', color: '#1565c0', padding: '2px 10px', borderRadius: '20px', fontWeight: 600 }}>
                <i className={`bi bi-${questionnaire.cible === 'COURS' ? 'book' : 'person-video3'} me-1`}></i>
                {CIBLE_LABELS[questionnaire.cible]}
              </span>
              {(questionnaire.categories || []).map(c => (
                <span key={c} style={{ fontSize: '0.72rem', background: '#f3e5f5', color: '#6a1b9a', padding: '2px 10px', borderRadius: '20px', fontWeight: 600 }}>{c}</span>
              ))}
              {(questionnaire.grades || []).map(g => (
                <span key={g} style={{ fontSize: '0.72rem', background: '#e8eaf6', color: '#283593', padding: '2px 10px', borderRadius: '20px', fontWeight: 600 }}>{g}</span>
              ))}
            </div>
            <h2 style={{ margin: 0, fontWeight: 700 }}>{(questionnaire.titres || []).join(' · ')}</h2>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.35rem', fontSize: '0.82rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
              {questionnaire.createur_nom && <span><i className="bi bi-person me-1"></i>{questionnaire.createur_nom}</span>}
              <span><i className="bi bi-question-circle me-1"></i>{questionnaire.questions?.length || 0} question{(questionnaire.questions?.length || 0) !== 1 ? 's' : ''}</span>
            </div>
          </div>

          {/* Actions statut */}
          <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0, flexWrap: 'wrap' }}>
            {questionnaire.statut === 'BROUILLON' && (
              <button className="btn btn-success btn-sm" onClick={() => handleStatut('PUBLIE')}>
                <i className="bi bi-send me-1"></i>Publier
              </button>
            )}
            {questionnaire.statut === 'PUBLIE' && (
              <button className="btn btn-secondary btn-sm" onClick={() => handleStatut('FERME')}>
                <i className="bi bi-lock me-1"></i>Fermer
              </button>
            )}
            {questionnaire.statut === 'FERME' && (
              <button className="btn btn-outline-secondary btn-sm" onClick={() => handleStatut('BROUILLON')}>
                <i className="bi bi-arrow-counterclockwise me-1"></i>Brouillon
              </button>
            )}
            {questionnaire.statut !== 'BROUILLON' && (
              <Link to={`/evaluations/${id}/analyse`} className="btn btn-outline-primary btn-sm">
                <i className="bi bi-graph-up-arrow me-1"></i>Analyse qualitative
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Onglets */}
      <div style={{ display: 'flex', gap: '0', borderBottom: '2px solid var(--border)', marginBottom: '1.5rem' }}>
        {[
          { key: 'questions', label: 'Questions', icon: 'bi-list-check' },
          { key: 'resultats', label: `Résultats${questionnaire.statut !== 'BROUILLON' ? '' : ''}`, icon: 'bi-bar-chart-line' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              border: 'none', background: 'none', padding: '0.6rem 1.25rem',
              fontWeight: tab === t.key ? 700 : 400,
              color: tab === t.key ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: tab === t.key ? '2px solid var(--primary)' : '2px solid transparent',
              marginBottom: '-2px', cursor: 'pointer', transition: 'all .15s', fontSize: '0.9rem',
            }}
          >
            <i className={`bi ${t.icon} me-1`}></i>{t.label}
          </button>
        ))}
      </div>

      {/* ── Tab Questions ────────────────────────────────────────────────────── */}
      {tab === 'questions' && (
        <div>
          {isLocked && (
            <div className="alert alert-info" style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>
              <i className="bi bi-info-circle me-1"></i>
              Ce questionnaire est publié — les questions ne peuvent plus être modifiées.
              Fermez-le d'abord pour pouvoir l'éditer.
            </div>
          )}

          {!isLocked && (
            <div style={{ marginBottom: '1rem' }}>
              <button className="btn btn-primary btn-sm" onClick={openNewQuestion}>
                <i className="bi bi-plus-lg me-1"></i>Ajouter une question
              </button>
            </div>
          )}

          {(!questionnaire.questions || questionnaire.questions.length === 0) ? (
            <div className="empty-state">
              <i className="bi bi-question-circle" style={{ fontSize: '2.5rem', color: 'var(--text-muted)' }}></i>
              <p>Aucune question — {isLocked ? 'publiez en brouillon pour éditer' : 'ajoutez votre première question'}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {questionnaire.questions.map((q, idx) => (
                <div key={q.id} className="card" style={{ padding: '1rem', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                  <div style={{ minWidth: '28px', height: '28px', borderRadius: '50%', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.85rem', flexShrink: 0 }}>
                    {idx + 1}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.2rem', alignItems: 'center', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '0.72rem', background: '#f5f5f5', color: '#616161', padding: '1px 7px', borderRadius: '20px', fontWeight: 600 }}>
                        <i className={`bi ${TYPE_ICONS[q.type_question]} me-1`}></i>{TYPE_LABELS[q.type_question]}
                      </span>
                      {!q.obligatoire && <span style={{ fontSize: '0.72rem', background: '#fff8e1', color: '#f57f17', padding: '1px 7px', borderRadius: '20px', fontWeight: 600 }}>Optionnel</span>}
                    </div>
                    <p style={{ margin: 0, fontWeight: 500 }}>{q.intitule}</p>
                    {q.choix && q.choix.length > 0 && (
                      <ul style={{ margin: '0.4rem 0 0 0', paddingLeft: '1.2rem', fontSize: '0.83rem', color: 'var(--text-muted)' }}>
                        {q.choix.map(c => <li key={c.id}>{c.libelle}</li>)}
                      </ul>
                    )}
                  </div>
                  {!isLocked && (
                    <div style={{ display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
                      <button className="btn btn-sm btn-outline-secondary" onClick={() => openEditQuestion(q)} title="Modifier">
                        <i className="bi bi-pencil"></i>
                      </button>
                      <button className="btn btn-sm btn-outline-danger" onClick={() => deleteQuestion(q.id)} title="Supprimer">
                        <i className="bi bi-trash"></i>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Tab Résultats ────────────────────────────────────────────────────── */}
      {tab === 'resultats' && (
        <div>
          {loadingRes ? (
            <div className="loading"><div className="spinner"></div></div>
          ) : (
            <>
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                <div className="card" style={{ padding: '1rem 1.5rem', flex: '0 0 auto' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--primary)', lineHeight: 1 }}>{totalReponses}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>soumission{totalReponses !== 1 ? 's' : ''}</div>
                </div>
              </div>

              {!resultats?.questions?.length ? (
                <div className="empty-state">
                  <i className="bi bi-inbox" style={{ fontSize: '2.5rem', color: 'var(--text-muted)' }}></i>
                  <p>Aucune réponse encore</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {resultats.questions.map((q, idx) => (
                    <div key={q.id} className="card" style={{ padding: '1.25rem' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'baseline' }}>
                        <span style={{ fontWeight: 700, color: 'var(--primary)', fontSize: '0.9rem' }}>Q{idx + 1}</span>
                        <span style={{ fontSize: '0.72rem', background: '#f5f5f5', color: '#616161', padding: '1px 7px', borderRadius: '20px', fontWeight: 600 }}>
                          {TYPE_LABELS[q.type_question]}
                        </span>
                      </div>
                      <p style={{ margin: '0 0 0.75rem', fontWeight: 600 }}>{q.intitule}</p>

                      {q.type_question === 'NOTE' && (
                        <StarBar moyenne={q.moyenne} total={q.total_reponses} />
                      )}

                      {(q.type_question === 'CHOIX_UN' || q.type_question === 'CHOIX_MUL') && q.choix_stats && (
                        <div>
                          {q.choix_stats.map(c => (
                            <ChoixBar
                              key={c.id}
                              libelle={c.libelle}
                              nb={c.nb_reponses}
                              total={q.choix_stats.reduce((s, x) => s + x.nb_reponses, 0)}
                            />
                          ))}
                        </div>
                      )}

                      {q.type_question === 'TEXTE' && (
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          <i className="bi bi-chat-left-text me-1"></i>{q.nb_reponses_texte} réponse{q.nb_reponses_texte !== 1 ? 's' : ''} texte
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Modal question ──────────────────────────────────────────────────── */}
      {showQForm && (
        <div className="modal-overlay" onClick={() => setShowQForm(false)}>
          <div className="modal-box" style={{ maxWidth: '540px' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h4 className="modal-title">{editingQ ? 'Modifier la question' : 'Nouvelle question'}</h4>
              <button className="modal-close" onClick={() => setShowQForm(false)}><i className="bi bi-x-lg"></i></button>
            </div>
            <form onSubmit={saveQuestion}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="form-label">Intitulé <span style={{ color: 'red' }}>*</span></label>
                  <textarea
                    className="form-control"
                    rows={2}
                    required
                    value={qForm.intitule}
                    onChange={e => setQForm(f => ({ ...f, intitule: e.target.value }))}
                    placeholder="Ex: Comment évaluez-vous la clarté du cours ?"
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="form-label">Type</label>
                    <select className="form-select" value={qForm.type_question} onChange={e => setQForm(f => ({ ...f, type_question: e.target.value, choix: [] }))}>
                      <option value="NOTE">Note (1 à 5)</option>
                      <option value="CHOIX_UN">Choix unique</option>
                      <option value="CHOIX_MUL">Choix multiple</option>
                      <option value="TEXTE">Texte libre</option>
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Ordre</label>
                    <input type="number" min={1} className="form-control" value={qForm.ordre} onChange={e => setQForm(f => ({ ...f, ordre: parseInt(e.target.value) || 1 }))} />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.875rem', marginBottom: '0.35rem' }}>
                      <input type="checkbox" checked={qForm.obligatoire} onChange={e => setQForm(f => ({ ...f, obligatoire: e.target.checked }))} />
                      Obligatoire
                    </label>
                  </div>
                </div>

                {['CHOIX_UN', 'CHOIX_MUL'].includes(qForm.type_question) && (
                  <div>
                    <label className="form-label">Options de réponse</label>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '0.5rem' }}>
                      {qForm.choix.map((c, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#f5f5f5', borderRadius: '6px', padding: '0.35rem 0.6rem' }}>
                          <span style={{ flex: 1, fontSize: '0.875rem' }}>{c.libelle}</span>
                          <button type="button" className="btn btn-sm btn-outline-danger" style={{ padding: '1px 6px' }} onClick={() => removeChoix(i)}>
                            <i className="bi bi-x"></i>
                          </button>
                        </div>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      <input
                        className="form-control form-control-sm"
                        placeholder="Libellé du choix…"
                        value={newChoixLabel}
                        onChange={e => setNewChoixLabel(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addChoix() } }}
                      />
                      <button type="button" className="btn btn-sm btn-outline-primary" onClick={addChoix}>
                        <i className="bi bi-plus"></i>
                      </button>
                    </div>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowQForm(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary" disabled={savingQ}>
                  {savingQ ? <><span className="spinner-border spinner-border-sm me-1"></span>Enregistrement…</> : (editingQ ? 'Mettre à jour' : 'Ajouter')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
