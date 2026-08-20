/** Programmes de période : volumes d'ECUE à planifier et affectations. */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { FiDownload, FiTrash2, FiUserCheck } from 'react-icons/fi'
import Modal from '@app/components/common/Modal'
import {
  affecterEnseignant,
  deleteProgramme,
  fetchProgrammes,
  importerMaquette,
} from '../../../api/eptinjs'
import { Chargement, EtatVide, Jauge } from '../../../components/Badges'

export default function OngletProgrammes({ referentiels, filtres, onFiltres, onRefresh }) {
  const [programmes, setProgrammes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [message, setMessage] = useState('')
  const [selection, setSelection] = useState([])
  const [affectation, setAffectation] = useState({ show: false, teacher: '' })
  const [recherche, setRecherche] = useState('')

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      const params = { page_size: 500 }
      if (filtres.periode) params.periode = filtres.periode
      if (filtres.promotion) params.promotion = filtres.promotion
      const reponse = await fetchProgrammes(params)
      setProgrammes(reponse.results || [])
      setSelection([])
    } catch (err) {
      setErreur(err.message || 'Chargement des programmes impossible.')
    } finally {
      setChargement(false)
    }
  }, [filtres.periode, filtres.promotion])

  useEffect(() => { charger() }, [charger])

  const visibles = useMemo(() => {
    const terme = recherche.trim().toLowerCase()
    if (!terme) return programmes
    return programmes.filter((item) =>
      `${item.course_code} ${item.course_name} ${item.promotion_name} ${item.teacher_name || ''}`
        .toLowerCase()
        .includes(terme),
    )
  }, [programmes, recherche])

  const importer = async () => {
    if (!filtres.periode) {
      setErreur('Choisissez d’abord une période de formation.')
      return
    }
    setErreur('')
    try {
      const corps = { periode: filtres.periode }
      if (filtres.promotion) corps.promotion = filtres.promotion
      const resultat = await importerMaquette(corps)
      setMessage(`${resultat.crees} programme(s) créé(s), ${resultat.deja_presents} déjà présent(s).`)
      await charger()
      onRefresh?.()
    } catch (err) {
      setErreur(err.message || 'Import de la maquette impossible.')
    }
  }

  const supprimer = async (programme) => {
    if (!window.confirm(`Retirer ${programme.course_code} du programme de la période ?`)) return
    try {
      await deleteProgramme(programme.id)
      await charger()
      onRefresh?.()
    } catch (err) {
      setErreur(err.message || 'Suppression impossible.')
    }
  }

  const appliquerAffectation = async () => {
    try {
      await affecterEnseignant({ programmes: selection, teacher: affectation.teacher || null })
      setAffectation({ show: false, teacher: '' })
      await charger()
      onRefresh?.()
    } catch (err) {
      setErreur(err.message || 'Affectation impossible.')
    }
  }

  const basculer = (id) =>
    setSelection((courant) =>
      courant.includes(id) ? courant.filter((item) => item !== id) : [...courant, id],
    )

  return (
    <div>
      {erreur && <div className="alert alert-danger">{erreur}</div>}
      {message && <div className="alert alert-success py-2">{message}</div>}

      <div className="ept-toolbar mb-3">
        <div className="d-flex flex-column">
          <span className="form-label">Période de formation</span>
          <select
            className="form-select form-select-sm"
            value={filtres.periode || ''}
            onChange={(event) => onFiltres({ ...filtres, periode: event.target.value })}
          >
            <option value="">Toutes les périodes</option>
            {referentiels.periodes.map((periode) => (
              <option key={periode.id} value={periode.id}>{periode.code} — {periode.libelle}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Promotion</span>
          <select
            className="form-select form-select-sm"
            value={filtres.promotion || ''}
            onChange={(event) => onFiltres({ ...filtres, promotion: event.target.value })}
          >
            <option value="">Toutes</option>
            {referentiels.promotions.map((promotion) => (
              <option key={promotion.id} value={promotion.id}>{promotion.name}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Recherche</span>
          <input
            type="search" className="form-control form-control-sm" placeholder="ECUE, promotion, enseignant…"
            value={recherche} onChange={(event) => setRecherche(event.target.value)}
          />
        </div>
        <div className="d-flex gap-2 align-items-end">
          <button type="button" className="btn btn-sm btn-outline-primary" onClick={importer}>
            <FiDownload className="me-1" /> Importer la maquette
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            disabled={!selection.length}
            onClick={() => setAffectation({ show: true, teacher: '' })}
          >
            <FiUserCheck className="me-1" /> Affecter ({selection.length})
          </button>
        </div>
      </div>

      {chargement ? <Chargement /> : visibles.length === 0 ? (
        <EtatVide message="Aucun programme sur ce périmètre. Importez la maquette LMD pour initialiser la période." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th style={{ width: 36 }} />
                  <th>Période</th><th>ECUE</th><th>Promotion</th><th>Nature</th>
                  <th>Volume cible</th><th>Planifié</th><th style={{ width: 150 }}>Couverture</th>
                  <th>Enseignant</th><th />
                </tr>
              </thead>
              <tbody>
                {visibles.map((programme) => (
                  <tr key={programme.id}>
                    <td>
                      <input
                        type="checkbox" className="form-check-input"
                        checked={selection.includes(programme.id)}
                        onChange={() => basculer(programme.id)}
                      />
                    </td>
                    <td><code>{programme.periode_code}</code></td>
                    <td>
                      <code className="me-1">{programme.course_code}</code>
                      {programme.course_name}
                    </td>
                    <td>{programme.promotion_name}</td>
                    <td>{programme.session_kind_display}</td>
                    <td>{programme.volume_horaire_heures || programme.volume_maquette_heures} h</td>
                    <td>{programme.heures_planifiees} h</td>
                    <td><Jauge valeur={programme.taux_couverture} /></td>
                    <td>{programme.teacher_name || <span className="text-danger">Non affecté</span>}</td>
                    <td className="text-end">
                      <button
                        type="button" className="btn btn-sm btn-outline-danger"
                        onClick={() => supprimer(programme)}
                      >
                        <FiTrash2 />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Modal
        show={affectation.show}
        onClose={() => setAffectation({ show: false, teacher: '' })}
        title={`Affecter un enseignant à ${selection.length} programme(s)`}
        footer={
          <div className="d-flex gap-2 justify-content-end w-100">
            <button
              type="button" className="btn btn-outline-secondary"
              onClick={() => setAffectation({ show: false, teacher: '' })}
            >
              Annuler
            </button>
            <button type="button" className="btn btn-injs-primary" onClick={appliquerAffectation}>
              Affecter
            </button>
          </div>
        }
      >
        <p className="text-muted small">
          Les séances déjà planifiées et non démarrées suivront cette affectation.
        </p>
        <select
          className="form-select"
          value={affectation.teacher}
          onChange={(event) => setAffectation({ show: true, teacher: event.target.value })}
        >
          <option value="">Retirer l’enseignant</option>
          {referentiels.enseignants.map((item) => (
            <option key={item.id} value={item.id}>{item.nom} — {item.grade}</option>
          ))}
        </select>
      </Modal>
    </div>
  )
}
