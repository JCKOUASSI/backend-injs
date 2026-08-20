/** Catalogue « Cours (ECUE) » : une ligne par offre ECUE × promotion. */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiRefreshCw, FiSearch } from 'react-icons/fi'
import PageHeader from '@app/components/common/PageHeader'
import { fetchPrograms } from '@app/api/academics'
import { fetchCatalogueCours, STATUTS_OFFRE } from '../../api/eptinjs'
import useReferentiels from '../../hooks/useReferentiels'
import { Chargement, EtatVide, Jauge, Kpi, StatutBadge } from '../../components/Badges'

export default function Cours() {
  const naviguer = useNavigate()
  const referentiels = useReferentiels()
  const [filieres, setFilieres] = useState([])
  const [filtres, setFiltres] = useState({ page: 1, page_size: 25 })
  const [recherche, setRecherche] = useState('')
  const [donnees, setDonnees] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')

  useEffect(() => {
    fetchPrograms({ page_size: 100 })
      .then((liste) => setFilieres(Array.isArray(liste) ? liste : liste.results || []))
      .catch(() => setFilieres([]))
  }, [])

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      setDonnees(await fetchCatalogueCours(filtres))
    } catch (err) {
      setErreur(err.message || 'Chargement du catalogue impossible.')
    } finally {
      setChargement(false)
    }
  }, [filtres])

  useEffect(() => { charger() }, [charger])

  const modifier = (champ) => (event) =>
    setFiltres((courant) => ({ ...courant, [champ]: event.target.value, page: 1 }))

  const lancerRecherche = (event) => {
    event.preventDefault()
    setFiltres((courant) => ({ ...courant, search: recherche, page: 1 }))
  }

  const kpis = donnees?.kpis
  const lignes = donnees?.results || []
  const pages = donnees ? Math.max(1, Math.ceil(donnees.count / donnees.page_size)) : 1

  return (
    <div>
      <PageHeader
        title="Cours (ECUE)"
        subtitle="Offres de cours, emplois du temps de toutes les périodes, présences et badgeage"
      />

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      {kpis && (
        <div className="ept-kpis mb-4">
          <Kpi valeur={kpis.offres} label="Offres ECUE" />
          <Kpi valeur={kpis.planifiees} label="Planifiées" />
          <Kpi valeur={kpis.non_programmees} label="Non programmées" />
          <Kpi valeur={kpis.sans_enseignant} label="Sans enseignant" />
          <Kpi valeur={kpis.heures_planifiees} suffixe="h" label="Heures planifiées" />
          <Kpi valeur={kpis.taux_couverture} suffixe="%" label="Couverture maquette" />
          <Kpi valeur={kpis.taux_presence} suffixe="%" label="Taux de présence" />
        </div>
      )}

      <form className="ept-toolbar mb-3" onSubmit={lancerRecherche}>
        <div className="d-flex flex-column">
          <span className="form-label">Période de formation</span>
          <select className="form-select form-select-sm" value={filtres.periode || ''} onChange={modifier('periode')}>
            <option value="">Toutes les périodes</option>
            {referentiels.periodes.map((periode) => (
              <option key={periode.id} value={periode.id}>{periode.code} — {periode.libelle}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Filière</span>
          <select className="form-select form-select-sm" value={filtres.program || ''} onChange={modifier('program')}>
            <option value="">Toutes</option>
            {filieres.map((filiere) => (
              <option key={filiere.id} value={filiere.id}>{filiere.code} — {filiere.name}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Promotion</span>
          <select
            className="form-select form-select-sm"
            value={filtres.promotion || ''}
            onChange={modifier('promotion')}
          >
            <option value="">Toutes</option>
            {referentiels.promotions.map((promotion) => (
              <option key={promotion.id} value={promotion.id}>{promotion.name}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Enseignant</span>
          <select className="form-select form-select-sm" value={filtres.teacher || ''} onChange={modifier('teacher')}>
            <option value="">Tous</option>
            {referentiels.enseignants.map((item) => (
              <option key={item.id} value={item.id}>{item.nom}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Statut</span>
          <select className="form-select form-select-sm" value={filtres.statut || ''} onChange={modifier('statut')}>
            <option value="">Tous</option>
            {STATUTS_OFFRE.map((statut) => (
              <option key={statut.value} value={statut.value}>{statut.label}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column flex-grow-1" style={{ minWidth: 220 }}>
          <span className="form-label">Recherche</span>
          <div className="input-group input-group-sm">
            <input
              type="search" className="form-control" placeholder="Code, intitulé, promotion, enseignant…"
              value={recherche} onChange={(event) => setRecherche(event.target.value)}
            />
            <button type="submit" className="btn btn-outline-secondary"><FiSearch /></button>
          </div>
        </div>
        <div className="d-flex align-items-end">
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={charger}>
            <FiRefreshCw />
          </button>
        </div>
      </form>

      {chargement ? <Chargement /> : lignes.length === 0 ? (
        <EtatVide message="Aucune offre de cours sur ce périmètre." />
      ) : (
        <>
          <div className="card">
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>ECUE</th><th>UE</th><th>Promotion</th><th>Périodes</th>
                    <th>Séances</th><th>Volume</th><th style={{ width: 150 }}>Couverture</th>
                    <th>Enseignant</th><th>Présence</th><th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {lignes.map((ligne) => (
                    <tr key={ligne.id} role="button" onClick={() => naviguer(`/admin/cours/${ligne.id}`)}>
                      <td>
                        <div className="fw-semibold"><code className="me-1">{ligne.course_code}</code></div>
                        <div className="small">{ligne.course_name}</div>
                      </td>
                      <td className="small">{ligne.teaching_unit_code}</td>
                      <td className="small">{ligne.promotion_name}</td>
                      <td className="small">
                        {ligne.periodes.length ? ligne.periodes.join(', ') : <span className="text-muted">—</span>}
                      </td>
                      <td>{ligne.seances_count}</td>
                      <td className="text-nowrap small">
                        {ligne.heures_planifiees} / {ligne.volume_cible_heures || ligne.volume_maquette_heures} h
                      </td>
                      <td><Jauge valeur={ligne.taux_couverture} /></td>
                      <td className="small">
                        {ligne.teacher_name || <span className="text-danger">Non affecté</span>}
                      </td>
                      <td className="small">
                        {ligne.attendus_count ? `${ligne.taux_presence} %` : '—'}
                      </td>
                      <td><StatutBadge statut={ligne.statut} label={ligne.statut_label} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {pages > 1 && (
            <div className="d-flex justify-content-between align-items-center mt-3">
              <span className="text-muted small">
                {donnees.count} offres — page {donnees.page} / {pages}
              </span>
              <div className="btn-group btn-group-sm">
                <button
                  type="button" className="btn btn-outline-secondary" disabled={donnees.page <= 1}
                  onClick={() => setFiltres((courant) => ({ ...courant, page: donnees.page - 1 }))}
                >
                  Précédent
                </button>
                <button
                  type="button" className="btn btn-outline-secondary" disabled={donnees.page >= pages}
                  onClick={() => setFiltres((courant) => ({ ...courant, page: donnees.page + 1 }))}
                >
                  Suivant
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
