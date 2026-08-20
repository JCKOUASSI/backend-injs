/** Cours (ECUE) assurés par l'enseignant connecté. */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '@app/components/common/PageHeader'
import { fetchMyTeacherProfile } from '@app/api/faculty'
import { fetchCatalogueCours } from '../../api/eptinjs'
import { Chargement, EtatVide, Jauge, Kpi, StatutBadge } from '../../components/Badges'

export default function MesCours() {
  const naviguer = useNavigate()
  const [donnees, setDonnees] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      const profil = await fetchMyTeacherProfile()
      setDonnees(await fetchCatalogueCours({ teacher: profil.id, page_size: 200 }))
    } catch (err) {
      setErreur(err.message || 'Chargement de vos cours impossible.')
    } finally {
      setChargement(false)
    }
  }, [])

  useEffect(() => { charger() }, [charger])

  if (chargement) return <Chargement />

  const lignes = donnees?.results || []

  return (
    <div>
      <PageHeader
        title="Mes cours (ECUE)"
        subtitle="Vos enseignements, séances et taux de présence sur toutes les périodes"
      />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      {donnees?.kpis && (
        <div className="ept-kpis mb-4">
          <Kpi valeur={donnees.kpis.offres} label="Cours assurés" />
          <Kpi valeur={donnees.kpis.seances} label="Séances" />
          <Kpi valeur={donnees.kpis.heures_planifiees} suffixe="h" label="Heures planifiées" />
          <Kpi valeur={donnees.kpis.taux_presence} suffixe="%" label="Taux de présence" />
        </div>
      )}

      {lignes.length === 0 ? (
        <EtatVide message="Aucun cours ne vous est affecté pour l’instant." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>ECUE</th><th>Promotion</th><th>Périodes</th><th>Séances</th>
                  <th>Volume</th><th style={{ width: 150 }}>Couverture</th><th>Présence</th><th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {lignes.map((ligne) => (
                  <tr key={ligne.id} role="button" onClick={() => naviguer(`/professeur/cours/${ligne.id}`)}>
                    <td>
                      <div className="fw-semibold"><code>{ligne.course_code}</code></div>
                      <div className="small">{ligne.course_name}</div>
                    </td>
                    <td className="small">{ligne.promotion_name}</td>
                    <td className="small">{ligne.periodes.join(', ') || '—'}</td>
                    <td>{ligne.seances_count}</td>
                    <td className="small text-nowrap">
                      {ligne.heures_planifiees} / {ligne.volume_cible_heures || ligne.volume_maquette_heures} h
                    </td>
                    <td><Jauge valeur={ligne.taux_couverture} /></td>
                    <td className="small">{ligne.attendus_count ? `${ligne.taux_presence} %` : '—'}</td>
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
