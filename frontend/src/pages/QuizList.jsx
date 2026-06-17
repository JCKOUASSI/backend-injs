import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useToast } from '../context/ToastContext'

export default function QuizList() {
  const { showToast } = useToast()
  const [quizzes, setQuizzes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      setLoading(true)
      try {
        const { data } = await api.get('/evaluations/mes-quiz/')
        setQuizzes(data)
      } catch (err) {
        showToast(err?.response?.data?.detail || 'Erreur chargement quiz', 'error')
      } finally { setLoading(false) }
    }
    fetch()
  }, [])

  if (loading) return <div className="loading"><div className="spinner"></div></div>
  if (!quizzes || quizzes.length === 0) return <div className="empty-state">Aucun quiz disponible</div>

  return (
    <div>
      <h2>Quiz disponibles</h2>
      <p style={{ color: 'var(--text-muted)', margin: '0.35rem 0 1rem' }}>
        Passez le quiz pour valider la lecture des manuels ou l’évaluation pédagogique.
      </p>
      <div style={{ display: 'grid', gap: '0.75rem' }}>
        {quizzes.map(q => (
          <div key={q.id} className="card" style={{ padding: '0.9rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{ minWidth: '240px' }}>
              <div style={{ fontWeight: 700, marginBottom: '0.35rem' }}>{q.titre}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{q.module_intitule}</div>
              {q.date_ouverture && <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>Ouverture: {q.date_ouverture.slice(0, 10)}</div>}
              {q.date_fermeture && <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Fermeture: {q.date_fermeture.slice(0, 10)}</div>}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <Link to={`/quiz/${q.id}`} className="btn btn-primary btn-sm">Passer</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
