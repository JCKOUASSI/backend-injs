/** Création / modification manuelle d'une séance. */
import { useEffect, useMemo, useState } from 'react'
import Modal from '@app/components/common/Modal'
import { createSeance, fetchGroupes, fetchProgrammes, updateSeance, NATURES_SEANCE } from '../api/eptinjs'
import { fetchRooms, fetchTeachers } from '@app/api/faculty'

const VIDE = {
  programme: '',
  groupe: '',
  teacher: '',
  supervisor: '',
  room: '',
  session_kind: 'cm',
  numero: 1,
  intitule: '',
  date: '',
  heure_debut: '08:00',
  heure_fin: '11:00',
  notes: '',
}

export default function SeanceFormModal({ show, seance, periode, onClose, onSaved }) {
  const [valeurs, setValeurs] = useState(VIDE)
  const [programmes, setProgrammes] = useState([])
  const [groupes, setGroupes] = useState([])
  const [salles, setSalles] = useState([])
  const [enseignants, setEnseignants] = useState([])
  const [erreur, setErreur] = useState('')
  const [envoi, setEnvoi] = useState(false)

  useEffect(() => {
    if (!show) return
    setErreur('')
    setValeurs(
      seance
        ? {
            programme: seance.programme || '',
            groupe: seance.groupe || '',
            teacher: seance.teacher || '',
            supervisor: seance.supervisor || '',
            room: seance.room || '',
            session_kind: seance.session_kind || 'cm',
            numero: seance.numero || 1,
            intitule: seance.intitule || '',
            date: seance.date || '',
            heure_debut: (seance.heure_debut || '08:00').slice(0, 5),
            heure_fin: (seance.heure_fin || '11:00').slice(0, 5),
            notes: seance.notes || '',
          }
        : { ...VIDE },
    )
  }, [show, seance])

  useEffect(() => {
    if (!show) return
    const params = periode ? { periode, page_size: 500 } : { page_size: 500 }
    Promise.all([
      fetchProgrammes(params),
      fetchRooms({ page_size: 300 }),
      fetchTeachers({ page_size: 300 }),
    ])
      .then(([listeProgrammes, listeSalles, listeEnseignants]) => {
        setProgrammes(listeProgrammes.results || [])
        setSalles(listeSalles.results || [])
        setEnseignants(listeEnseignants.results || [])
      })
      .catch((err) => setErreur(err.message || 'Chargement des référentiels impossible.'))
  }, [show, periode])

  const programmeChoisi = useMemo(
    () => programmes.find((item) => item.id === valeurs.programme),
    [programmes, valeurs.programme],
  )

  useEffect(() => {
    if (!programmeChoisi?.promotion) {
      setGroupes([])
      return
    }
    fetchGroupes({ promotion: programmeChoisi.promotion, page_size: 100 })
      .then((reponse) => setGroupes(reponse.results || reponse || []))
      .catch(() => setGroupes([]))
  }, [programmeChoisi?.promotion])

  const modifier = (champ) => (event) =>
    setValeurs((courant) => ({ ...courant, [champ]: event.target.value }))

  const enregistrer = async (event) => {
    event.preventDefault()
    setErreur('')
    setEnvoi(true)
    try {
      const corps = {
        ...valeurs,
        numero: Number(valeurs.numero) || 1,
        groupe: valeurs.groupe || null,
        teacher: valeurs.teacher || null,
        supervisor: valeurs.supervisor || null,
        room: valeurs.room || null,
      }
      const enregistree = seance ? await updateSeance(seance.id, corps) : await createSeance(corps)
      onSaved?.(enregistree)
      onClose?.()
    } catch (err) {
      setErreur(err.message || 'Enregistrement impossible.')
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <Modal
      show={show}
      onClose={onClose}
      size="lg"
      title={seance ? 'Modifier la séance' : 'Nouvelle séance'}
      footer={
        <div className="d-flex gap-2 justify-content-end w-100">
          <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Annuler</button>
          <button type="submit" form="ept-seance-form" className="btn btn-injs-primary" disabled={envoi}>
            {envoi ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      }
    >
      <form id="ept-seance-form" onSubmit={enregistrer}>
        {erreur && <div className="alert alert-danger py-2">{erreur}</div>}

        <div className="row g-3">
          <div className="col-12">
            <label className="form-label">Programme (ECUE × promotion × période)</label>
            <select className="form-select" value={valeurs.programme} onChange={modifier('programme')} required>
              <option value="">— Sélectionner —</option>
              {programmes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.periode_code} · {item.course_code} — {item.course_name} · {item.promotion_name}
                  {' '}({item.session_kind_display})
                </option>
              ))}
            </select>
          </div>

          <div className="col-md-4">
            <label className="form-label">Nature</label>
            <select className="form-select" value={valeurs.session_kind} onChange={modifier('session_kind')}>
              {NATURES_SEANCE.map((nature) => (
                <option key={nature.value} value={nature.value}>{nature.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Groupe</label>
            <select className="form-select" value={valeurs.groupe} onChange={modifier('groupe')}>
              <option value="">Promotion entière</option>
              {groupes.map((groupe) => (
                <option key={groupe.id} value={groupe.id}>{groupe.code} — {groupe.name}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Numéro de séance</label>
            <input
              type="number" min="1" className="form-control"
              value={valeurs.numero} onChange={modifier('numero')}
            />
          </div>

          <div className="col-md-4">
            <label className="form-label">Date</label>
            <input type="date" className="form-control" value={valeurs.date} onChange={modifier('date')} required />
          </div>
          <div className="col-md-4">
            <label className="form-label">Heure de début</label>
            <input
              type="time" className="form-control"
              value={valeurs.heure_debut} onChange={modifier('heure_debut')} required
            />
          </div>
          <div className="col-md-4">
            <label className="form-label">Heure de fin</label>
            <input
              type="time" className="form-control"
              value={valeurs.heure_fin} onChange={modifier('heure_fin')} required
            />
          </div>

          <div className="col-md-4">
            <label className="form-label">Salle</label>
            <select className="form-select" value={valeurs.room} onChange={modifier('room')}>
              <option value="">Non affectée</option>
              {salles.map((salle) => (
                <option key={salle.id} value={salle.id}>
                  {salle.code} — {salle.name} ({salle.capacity} pl.)
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Enseignant</label>
            <select className="form-select" value={valeurs.teacher} onChange={modifier('teacher')}>
              <option value="">Non affecté</option>
              {enseignants.map((item) => (
                <option key={item.id} value={item.id}>{item.nom}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Encadrant</label>
            <select className="form-select" value={valeurs.supervisor} onChange={modifier('supervisor')}>
              <option value="">Aucun</option>
              {enseignants.map((item) => (
                <option key={item.id} value={item.id}>{item.nom}</option>
              ))}
            </select>
          </div>

          <div className="col-12">
            <label className="form-label">Intitulé de la séance</label>
            <input
              type="text" className="form-control" placeholder="Optionnel"
              value={valeurs.intitule} onChange={modifier('intitule')}
            />
          </div>
          <div className="col-12">
            <label className="form-label">Notes</label>
            <textarea className="form-control" rows={2} value={valeurs.notes} onChange={modifier('notes')} />
          </div>
        </div>
      </form>
    </Modal>
  )
}
