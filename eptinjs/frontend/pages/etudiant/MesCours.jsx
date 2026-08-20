/** Cours (ECUE) suivis par l'étudiant connecté. */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '@app/components/common/PageHeader'
import { useAuth } from '@app/context/AuthContext'
import { fetchMyStudentProfile } from '@app/api/students'
import { fetchCatalogueCours } from '../../api/eptinjs'
import { Chargement, EtatVide, Jauge, Kpi, StatutBadge } from '../../components/Badges'

export default function MesCours() {
  const naviguer = useNavigate()
  const { user } = useAuth()
  const [donnees, setDonnees] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      const profil = await fetchMyStudentProfile(user)
      if (!profil?.promotionId) {
        setErreur('Aucune promotion rattachée à votre compte étudiant.')
        return
      }
      setDonnees(await fetchCatalogueCours({ promotion: profil.promotionId, page_size: 200 }))
    } catch (err) {
      setErreur(err.message || 'Chargement de vos cours impossible.')
    } finally {
      setChargement(false)
    }
  }, [user])

  useEffect(() => { charger() }, [charger])

  if (chargement) return <Chargement />

  const lignes = donnees?.results || []

  return (
    <div>
      <PageHeader title="Mes cours (ECUE)" subtitle="Vos enseignements, séances programmées et assiduité" />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      {donnees?.kpis && (
        <div className="ept-kpis mb-4">
          <Kpi valeur={donnees.kpis.offres} label="Cours" />
          <Kpi valeur={donnees.kpis.seances} label="Séances" />
          <Kpi valeur={donnees.kpis.heures_planifiees} suffixe="h" label="Heures planifiées" />
          <Kpi valeur={donnees.kpis.taux_presence} suffixe="%" label="Assiduité" />
        </div>
      )}

      {lignes.length === 0 ? (
        <EtatVide message="Aucun cours n’est encore programmé pour votre promotion." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>ECUE</th><th>UE</th><th>Enseignant</th><th>Périodes</th>
                  <th>Séances</th><th style={{ width: 150 }}>Avancement</th><th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {lignes.map((ligne) => (
                  <tr key={ligne.id} role="button" onClick={() => naviguer(`/etudiant/cours/${ligne.id}`)}>
                    <td>
                      <div className="fw-semibold"><code>{ligne.course_code}</code></div>
                      <div className="small">{ligne.course_name}</div>
                    </td>
                    <td className="small">{ligne.teaching_unit_code}</td>
                    <td className="small">{ligne.teacher_name || '—'}</td>
                    <td className="small">{ligne.periodes.join(', ') || '—'}</td>
                    <td>{ligne.seances_count}</td>
                    <td><Jauge valeur={ligne.taux_couverture} /></td>
                    <td><StatutBadge statut={ligne.statut} label={ligne.statut_label} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
