/** Fiche d'une séance : informations, cycle de vie, émargement. */
import { useCallback, useEffect, useState } from 'react'
import { FiEdit2, FiPlay, FiSquare, FiTrash2, FiXCircle } from 'react-icons/fi'
import Modal from '@app/components/common/Modal'
import {
  annulerSeance,
  demarrerSeance,
  deleteSeance,
  fetchSeance,
  terminerSeance,
} from '../api/eptinjs'
import EmargementPanel from './EmargementPanel'
import { Chargement, StatutBadge } from './Badges'

function Ligne({ libelle, valeur }) {
  return (
    <div className="col-md-6 mb-2">
      <div className="text-muted small text-uppercase" style={{ fontSize: '0.72rem' }}>{libelle}</div>
      <div className="fw-semibold">{valeur || '—'}</div>
    </div>
  )
}

export default function SeanceDetailModal({
  show,
  seanceId,
  onClose,
  onChange,
  onEdit,
  onOuvrirQr,
  peutGerer = false,
}) {
  const [seance, setSeance] = useState(null)
  const [onglet, setOnglet] = useState('infos')
  const [erreur, setErreur] = useState('')
  const [occupe, setOccupe] = useState(false)

  const charger = useCallback(async () => {
    if (!seanceId) return
    try {
      setSeance(await fetchSeance(seanceId))
    } catch (err) {
      setErreur(err.message || 'Séance introuvable.')
    }
  }, [seanceId])

  useEffect(() => {
    if (!show) {
      setSeance(null)
      setOnglet('infos')
      setErreur('')
      return
    }
    charger()
  }, [show, charger])

  const executer = async (action, { ferme = false } = {}) => {
    setErreur('')
    setOccupe(true)
    try {
      await action()
      await charger()
      onChange?.()
      if (ferme) onClose?.()
    } catch (err) {
      setErreur(err.message || 'Opération impossible.')
    } finally {
      setOccupe(false)
    }
  }

  const demarrer = () =>
    executer(async () => {
      await demarrerSeance(seanceId)
      onOuvrirQr?.(seanceId)
    })

  const terminer = () => executer(() => terminerSeance(seanceId))

  const annuler = () => {
    const motif = window.prompt('Motif de l’annulation :', '')
    if (motif === null) return
    executer(() => annulerSeance(seanceId, motif))
  }

  const supprimer = () => {
    if (!window.confirm('Supprimer définitivement cette séance ?')) return
    executer(() => deleteSeance(seanceId), { ferme: true })
  }

  const titre = seance ? `${seance.course_code} — ${seance.course_name}` : 'Séance'

  return (
    <Modal
      show={show}
      onClose={onClose}
      size="lg"
      title={titre}
      footer={
        peutGerer && seance && (
          <div className="d-flex flex-wrap gap-2 justify-content-between w-100">
            <div className="d-flex flex-wrap gap-2">
              {seance.statut === 'planifiee' && (
                <button type="button" className="btn btn-sm btn-success" onClick={demarrer} disabled={occupe}>
                  <FiPlay className="me-1" /> Démarrer
                </button>
              )}
              {seance.statut === 'en_cours' && (
                <>
                  <button
                    type="button" className="btn btn-sm btn-injs-primary"
                    onClick={() => onOuvrirQr?.(seanceId)}
                  >
                    Afficher le QR
                  </button>
                  <button type="button" className="btn btn-sm btn-secondary" onClick={terminer} disabled={occupe}>
                    <FiSquare className="me-1" /> Terminer
                  </button>
                </>
              )}
              {!['annulee', 'terminee'].includes(seance.statut) && (
                <button type="button" className="btn btn-sm btn-outline-danger" onClick={annuler} disabled={occupe}>
                  <FiXCircle className="me-1" /> Annuler
                </button>
              )}
            </div>
            <div className="d-flex gap-2">
              <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => onEdit?.(seance)}>
                <FiEdit2 className="me-1" /> Modifier
              </button>
              <button
                type="button" className="btn btn-sm btn-outline-danger"
                onClick={supprimer} disabled={occupe} title="Supprimer"
              >
                <FiTrash2 />
              </button>
            </div>
          </div>
        )
      }
    >
      {erreur && <div className="alert alert-danger py-2">{erreur}</div>}

      {!seance ? <Chargement /> : (
        <>
          <div className="ept-tabs">
            <button
              type="button"
              className={`btn btn-sm ${onglet === 'infos' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => setOnglet('infos')}
            >
              Informations
            </button>
            <button
              type="button"
              className={`btn btn-sm ${onglet === 'presences' ? 'btn-injs-primary' : 'btn-outline-secondary'}`}
              onClick={() => setOnglet('presences')}
            >
              Présences ({seance.presents_count}/{seance.attendus_count})
            </button>
          </div>

          {onglet === 'infos' ? (
            <div className="row">
              <Ligne libelle="Statut" valeur={<StatutBadge statut={seance.statut} label={seance.statut_display} />} />
              <Ligne libelle="Nature" valeur={seance.session_kind_display} />
              <Ligne libelle="Période" valeur={seance.periode_libelle || seance.periode_code} />
              <Ligne libelle="Promotion" valeur={seance.promotion_name} />
              <Ligne libelle="Groupe" valeur={seance.groupe_code || 'Promotion entière'} />
              <Ligne libelle="Date" valeur={`${seance.day_display} ${seance.date}`} />
              <Ligne libelle="Horaire" valeur={`${seance.heure_debut}–${seance.heure_fin}`} />
              <Ligne libelle="Durée" valeur={`${seance.duree_heures} h`} />
              <Ligne
                libelle="Salle"
                valeur={seance.room_code ? `${seance.room_code} — ${seance.room_name || ''}` : null}
              />
              <Ligne libelle="Enseignant" valeur={seance.teacher_name} />
              <Ligne libelle="Encadrant" valeur={seance.supervisor_name} />
              <Ligne libelle="Origine" valeur={seance.origine} />
              {seance.intitule && <Ligne libelle="Intitulé" valeur={seance.intitule} />}
              {seance.notes && <Ligne libelle="Notes" valeur={seance.notes} />}
            </div>
          ) : (
            <EmargementPanel seanceId={seanceId} editable={peutGerer} onChange={onChange} />
          )}
        </>
      )}
    </Modal>
  )
}
