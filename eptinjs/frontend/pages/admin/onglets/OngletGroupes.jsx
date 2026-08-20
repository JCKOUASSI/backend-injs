/** Groupes pédagogiques (TD/TP) d'une promotion. */
import { useCallback, useEffect, useState } from 'react'
import { FiTrash2, FiUsers } from 'react-icons/fi'
import Modal from '@app/components/common/Modal'
import {
  createGroupe,
  deleteGroupe,
  fetchGroupeMembres,
  fetchGroupes,
  repartirGroupes,
} from '../../../api/eptinjs'
import { Chargement, EtatVide } from '../../../components/Badges'

export default function OngletGroupes({ referentiels, filtres, onFiltres }) {
  const [groupes, setGroupes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState('')
  const [membres, setMembres] = useState({ show: false, groupe: null, liste: [] })
  const [nombre, setNombre] = useState(2)
  const [nouveau, setNouveau] = useState({ code: '', name: '', effectif_max: 30 })

  const promotion = filtres.promotion || ''

  const charger = useCallback(async () => {
    setChargement(true)
    setErreur('')
    try {
      const params = { page_size: 200 }
      if (promotion) params.promotion = promotion
      const reponse = await fetchGroupes(params)
      setGroupes(reponse.results || [])
    } catch (err) {
      setErreur(err.message || 'Chargement des groupes impossible.')
    } finally {
      setChargement(false)
    }
  }, [promotion])

  useEffect(() => { charger() }, [charger])

  const repartir = async () => {
    if (!promotion) {
      setErreur('Sélectionnez une promotion.')
      return
    }
    if (!window.confirm(`Répartir automatiquement les étudiants en ${nombre} groupes ? Les groupes existants seront réinitialisés.`)) return
    try {
      await repartirGroupes({ promotion, nombre_groupes: Number(nombre) })
      await charger()
    } catch (err) {
      setErreur(err.message || 'Répartition impossible.')
    }
  }

  const creer = async (event) => {
    event.preventDefault()
    if (!promotion) {
      setErreur('Sélectionnez une promotion.')
      return
    }
    try {
      await createGroupe({ ...nouveau, promotion, effectif_max: Number(nouveau.effectif_max) })
      setNouveau({ code: '', name: '', effectif_max: 30 })
      await charger()
    } catch (err) {
      setErreur(err.message || 'Création impossible.')
    }
  }

  const supprimer = async (groupe) => {
    if (!window.confirm(`Supprimer le groupe ${groupe.code} ?`)) return
    try {
      await deleteGroupe(groupe.id)
      await charger()
    } catch (err) {
      setErreur(err.message || 'Suppression impossible.')
    }
  }

  const voirMembres = async (groupe) => {
    const liste = await fetchGroupeMembres(groupe.id)
    setMembres({ show: true, groupe, liste })
  }

  return (
    <div>
      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <div className="ept-toolbar mb-3">
        <div className="d-flex flex-column">
          <span className="form-label">Promotion</span>
          <select
            className="form-select form-select-sm"
            value={promotion}
            onChange={(event) => onFiltres({ ...filtres, promotion: event.target.value })}
          >
            <option value="">Toutes</option>
            {referentiels.promotions.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Nombre de groupes</span>
          <input
            type="number" min="1" max="12" className="form-control form-control-sm" style={{ width: 110 }}
            value={nombre} onChange={(event) => setNombre(event.target.value)}
          />
        </div>
        <div className="d-flex align-items-end">
          <button type="button" className="btn btn-sm btn-outline-primary" onClick={repartir}>
            <FiUsers className="me-1" /> Répartir automatiquement
          </button>
        </div>
      </div>

      <form className="ept-toolbar mb-4" onSubmit={creer}>
        <div className="d-flex flex-column">
          <span className="form-label">Code</span>
          <input
            type="text" className="form-control form-control-sm" style={{ width: 110 }} placeholder="G1" required
            value={nouveau.code} onChange={(event) => setNouveau({ ...nouveau, code: event.target.value })}
          />
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Nom</span>
          <input
            type="text" className="form-control form-control-sm" placeholder="Groupe 1" required
            value={nouveau.name} onChange={(event) => setNouveau({ ...nouveau, name: event.target.value })}
          />
        </div>
        <div className="d-flex flex-column">
          <span className="form-label">Effectif max.</span>
          <input
            type="number" min="1" className="form-control form-control-sm" style={{ width: 110 }}
            value={nouveau.effectif_max}
            onChange={(event) => setNouveau({ ...nouveau, effectif_max: event.target.value })}
          />
        </div>
        <div className="d-flex align-items-end">
          <button type="submit" className="btn btn-sm btn-injs-primary">Ajouter le groupe</button>
        </div>
      </form>

      {chargement ? <Chargement /> : groupes.length === 0 ? (
        <EtatVide message="Aucun groupe pédagogique. Répartissez la promotion pour créer des groupes TD/TP." />
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr><th>Code</th><th>Nom</th><th>Promotion</th><th>Effectif</th><th>Capacité</th><th /></tr>
              </thead>
              <tbody>
                {groupes.map((groupe) => (
                  <tr key={groupe.id}>
                    <td><code>{groupe.code}</code></td>
                    <td>{groupe.name}</td>
                    <td>{groupe.promotion_name}</td>
                    <td>{groupe.effectif}</td>
                    <td>{groupe.effectif_max}</td>
                    <td className="text-end text-nowrap">
                      <button
                        type="button" className="btn btn-sm btn-outline-secondary me-1"
                        onClick={() => voirMembres(groupe)}
                      >
                        Membres
                      </button>
                      <button
                        type="button" className="btn btn-sm btn-outline-danger"
                        onClick={() => supprimer(groupe)}
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
        show={membres.show}
        onClose={() => setMembres({ show: false, groupe: null, liste: [] })}
        title={`Membres — ${membres.groupe?.code || ''}`}
      >
        {membres.liste.length === 0 ? (
          <EtatVide message="Ce groupe ne contient aucun étudiant." />
        ) : (
          <table className="table table-sm">
            <thead><tr><th>Matricule</th><th>Nom</th></tr></thead>
            <tbody>
              {membres.liste.map((membre) => (
                <tr key={membre.id}><td><code>{membre.matricule}</code></td><td>{membre.nom}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Modal>
    </div>
  )
}
