import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

export default function QuizTake() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [quiz, setQuiz] = useState(null)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const fetch = async () => {
      setLoading(true)
      try {
        const { data } = await api.get('/evaluations/mes-quiz/')
        const q = (data || []).find(x => String(x.id) === String(id))
        if (!q) {
          showToast('Quiz introuvable ou non disponible', 'error')
          navigate('/evaluations')
          return
        }
        setQuiz(q)
      } catch (err) {
        showToast(err?.response?.data?.detail || 'Erreur chargement quiz', 'error')
        navigate('/evaluations')
      } finally { setLoading(false) }
    }
    fetch()
  }, [id])

  const handleChange = (questionId, value) => {
    setAnswers(a => ({ ...a, [questionId]: value }))
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!quiz) return
    setSubmitting(true)
    try {
      const payload = { reponses: {} }
      for (const q of quiz.questions) {
        const v = answers[q.id]
        payload.reponses[String(q.id)] = v ?? ''
      }
      payload.temps_pris_minutes = 5
      const { data } = await api.post(`/evaluations/quiz/${quiz.id}/soumettre/`, payload)
      showToast(`Quiz soumis — score: ${data.score}% — réussi: ${data.reussi ? 'oui' : 'non'}`, 'success')
      navigate('/evaluations')
    } catch (err) {
      showToast(err?.response?.data?.detail || 'Erreur soumission', 'error')
    } finally { setSubmitting(false) }
  }

  if (loading) return <div className="loading"><div className="spinner"></div></div>
  if (!quiz) return null

  return (
    <div>
      <h2>{quiz.titre}</h2>
      <p style={{ color: 'var(--text-muted)' }}>{quiz.description}</p>
      <form onSubmit={submit}>
        {quiz.questions.map(q => (
          <div key={q.id} className="card" style={{ padding: '0.75rem', marginBottom: '0.5rem' }}>
            <div style={{ fontWeight: 700, marginBottom: '0.4rem' }}>{q.question}</div>
            {q.type_question === 'QCM' && (
              <div style={{ marginTop: '0.5rem' }}>
                {(q.options || []).map((opt, idx) => (
                  <div key={idx} style={{ marginBottom: '0.25rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <input type="radio" name={String(q.id)} value={opt} checked={answers[q.id] === opt} onChange={() => handleChange(q.id, opt)} />
                      <span>{opt}</span>
                    </label>
                  </div>
                ))}
              </div>
            )}
            {q.type_question === 'VRAI_FAUX' && (
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input type="radio" name={String(q.id)} value="vrai" checked={answers[q.id] === 'vrai'} onChange={() => handleChange(q.id, 'vrai')} /> Vrai
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input type="radio" name={String(q.id)} value="faux" checked={answers[q.id] === 'faux'} onChange={() => handleChange(q.id, 'faux')} /> Faux
                </label>
              </div>
            )}
            {q.type_question === 'OUVERTE' && (
              <div style={{ marginTop: '0.5rem' }}>
                <textarea className="form-control" rows={4} value={answers[q.id] || ''} onChange={e => handleChange(q.id, e.target.value)} />
              </div>
            )}
          </div>
        ))}
        <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-primary" disabled={submitting}>{submitting ? 'Envoi...' : 'Soumettre'}</button>
        </div>
      </form>
    </div>
  )
}
