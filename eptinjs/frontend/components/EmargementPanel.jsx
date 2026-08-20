/** Feuille d'émargement d'une séance : compteurs, marquage manuel, forçage. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { FiCheckSquare, FiRefreshCw, FiSquare, FiZap } from 'react-icons/fi'
import {
  constituerListe,
  fetchEmargement,
  forcerBadgeage,
  marquerPresences,
  STATUTS_POINTAGE,
} from '../api/eptinjs'
import { Chargement, EtatVide, Kpi, StatutBadge } from './Badges'

function heure(iso) {
  return iso ? new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '—'
}

export default function EmargementPanel({ seanceId, editable = true, onChange }) {
  const [donnees, setDonnees] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [selection, setSelection] = useState([])
  const [recherche, setRecherche] = useState('')
  const [filtreStatut, setFiltreStatut] = useState('')

  const charger = useCallback(async () => {
    if (!seanceId) return
    setChargement(true)
    setErreur('')
    try {
      setDonnees(await fetchEmargement(seanceId))
      setSelection([])
    } catch (err) {
      setErreur(err.message || 'Chargement de l’émargement impossible.')
    } finally {
      setChargement(false)
    }
  }, [seanceId])

  useEffect(() => { charger() }, [charger])

  const pointages = donnees?.pointages || []

  const visibles = useMemo(() => {
    const terme = recherche.trim().toLowerCase()
    return pointages.filter((item) => {
      if (filtreStatut && item.statut !== filtreStatut) return false
      if (!terme) return true
      return `${item.nom} ${item.matricule || ''}`.toLowerCase().includes(terme)
    })
  }, [pointages, recherche, filtreStatut])

  const basculer = (id) =>
    setSelection((courant) =>
      courant.includes(id) ? courant.filter((item) => item !== id) : [...courant, id],
    )

  const toutBasculer = () =>
    setSelection((courant) => (courant.length === visibles.length ? [] : visibles.map((item) => item.id)))

  const executer = async (action) => {
    setErreur('')
    try {
      await action()
      await charger()
      onChange?.()
    } catch (err) {
      setErreur(err.message || 'Opération impossible.')
    }
  }

  const appliquerStatut = (statut) => {
    const choisis = pointages.filter((item) => selection.includes(item.id))
    const students = choisis.filter((item) => item.student).map((item) => item.student)
    const teachers = choisis.filter((item) => item.teacher).map((item) => item.teacher)
    if (!students.length && !teachers.length) {
      setErreur('Sélectionnez au moins une personne.')
      return
    }
    executer(() => marquerPresences(seanceId, { statut, students, teachers }))
  }

  if (chargement && !donnees) return <Chargement />

  const compteurs = donnees?.compteurs || {}

  return (
    <div>
      {erreur && <div className="alert alert-danger py-2">{erreur}</div>}

      <div className="ept-kpis mb-3">
        <Kpi valeur={compteurs.presents ?? 0} label="Présents" />
        <Kpi valeur={compteurs.absents ?? 0} label="Absents" />
        <Kpi valeur={compteurs.non_badges ?? 0} label="Non badgés" />
        <Kpi valeur={compteurs.en_salle ?? 0} label="En salle" />
        <Kpi valeur={compteurs.taux_presence ?? 0} suffixe="%" label="Taux de présence" />
      </div>

      <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
        <input
          type="search"
          className="form-control form-control-sm"
          style={{ maxWidth: 240 }}
          placeholder="Nom ou matricule…"
          value={recherche}
          onChange={(event) => setRecherche(event.target.value)}
        />
        <select
          className="form-select form-select-sm"
          style={{ maxWidth: 180 }}
          value={filtreStatut}
          onChange={(event) => setFiltreStatut(event.target.value)}
        >
          <option value="">Tous les statuts</option>
          <option value="attendu">Attendu</option>
          {STATUTS_POINTAGE.map((statut) => (
            <option key={statut.value} value={statut.value}>{statut.label}</option>
          ))}
        </select>

        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={charger}>
          <FiRefreshCw className="me-1" /> Actualiser
        </button>

        {editable && (
          <>
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={() => executer(() => constituerListe(seanceId))}
            >
              Constituer la liste
            </button>
            <button
              type="button"
              className="btn btn-outline-warning btn-sm"
              onClick={() => executer(() => forcerBadgeage(seanceId))}
              title="Force aléatoirement 80 à 95 % de présences en cas de panne du badgeage"
            >
              <FiZap className="me-1" /> Forcer le badgeage
            </button>
          </>
        )}
      </div>

      {editable && selection.length > 0 && (
        <div className="alert alert-light border d-flex flex-wrap gap-2 align-items-center py-2">
          <strong className="me-2">{selection.length} sélectionné(s)</strong>
          {STATUTS_POINTAGE.map((statut) => (
            <button
              key={statut.value}
              type="button"
              className="btn btn-sm btn-outline-primary"
              onClick={() => appliquerStatut(statut.value)}
            >
              {statut.label}
            </button>
          ))}
        </div>
      )}

      {visibles.length === 0 ? (
        <EtatVide message="Aucune personne dans la feuille d’émargement." />
      ) : (
        <div className="table-responsive">
          <table className="table table-sm align-middle">
            <thead>
              <tr>
                {editable && (
                  <th style={{ width: 36 }}>
                    <button type="button" className="btn btn-link p-0 text-secondary" onClick={toutBasculer}>
                      {selection.length === visibles.length ? <FiCheckSquare /> : <FiSquare />}
                    </button>
                  </th>
                )}
                <th>Matricule</th>
                <th>Nom</th>
                <th>Rôle</th>
                <th>Statut</th>
                <th>Entrée</th>
                <th>Sortie</th>
                <th>Durée</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((item) => (
                <tr key={item.id}>
                  {editable && (
                    <td>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={selection.includes(item.id)}
                        onChange={() => basculer(item.id)}
                      />
                    </td>
                  )}
                  <td><code>{item.matricule || '—'}</code></td>
                  <td>{item.nom}</td>
                  <td className="small text-muted">{item.role_display}</td>
                  <td>
                    <StatutBadge statut={item.statut} label={item.statut_display} />
                    {item.en_salle && <span className="badge bg-success-subtle text-success ms-1">en salle</span>}
                  </td>
                  <td className="small">{heure(item.entree_at)}</td>
                  <td className="small">{heure(item.sortie_at)}</td>
                  <td className="small">{item.duree_minutes ? `${item.duree_minutes} min` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
