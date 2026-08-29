import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getAnneeCourante,
  getStatsAdmissions,
  getStatsCandidatures,
  getStatsInscriptions,
  messageErreur,
  statutVariant,
} from '../../services/scolarite'

const LIBELLES_CANDIDATURE = {
  BROUILLON: 'Brouillon',
  SOUMISE: 'Soumise',
  EN_ATTENTE_DE_VERIFICATION: 'À vérifier',
  PIECES_INCOMPLETES: 'Pièces incomplètes',
  PIECES_VALIDEES: 'Pièces validées',
  EN_ETUDE: 'En étude',
  ADMISSIBLE: 'Admissible',
  ADMIS: 'Admis',
  ADMIS_SOUS_RESERVE: 'Admis sous réserve',
  LISTE_ATTENTE: "Liste d'attente",
  REFUSE: 'Refusé',
  ANNULE: 'Annulé',
}

const LIBELLES_INSCRIPTION = {
  BROUILLON: 'Brouillon',
  EN_ATTENTE: 'En attente',
  A_VALIDER: 'À valider',
  VALIDEE: 'Validée',
  REJETEE: 'Rejetée',
  ANNULEE: 'Annulée',
  SUSPENDUE: 'Suspendue',
  TERMINEE: 'Terminée',
}

function CarteChiffre({ titre, valeur, icone, couleur, lien }) {
  const contenu = (
    <div className="card h-100">
      <div className="card-body d-flex align-items-center gap-3">
        <div className={`rounded p-3 bg-${couleur} bg-opacity-10`}>
          <i className={`bi ${icone} fs-4 text-${couleur}`}></i>
        </div>
        <div>
          <div className="fs-3 fw-semibold">{valeur}</div>
          <small className="text-muted">{titre}</small>
        </div>
      </div>
    </div>
  )
  return lien ? <Link to={lien} className="text-decoration-none text-reset">{contenu}</Link> : contenu
}

function Repartition({ titre, donnees, libelles }) {
  const entrees = Object.entries(donnees || {}).sort((a, b) => b[1] - a[1])
  const total = entrees.reduce((somme, [, valeur]) => somme + valeur, 0)
  return (
    <div className="card h-100">
      <div className="card-header"><strong>{titre}</strong></div>
      <div className="card-body">
        {entrees.length === 0 && <p className="text-muted mb-0">Aucune donnée.</p>}
        {entrees.map(([cle, valeur]) => (
          <div key={cle} className="mb-2">
            <div className="d-flex justify-content-between small">
              <span>{libelles?.[cle] || cle}</span>
              <span className="fw-semibold">{valeur}</span>
            </div>
            <div className="progress" style={{ height: '0.35rem' }}>
              <div
                className={`progress-bar bg-${libelles === LIBELLES_CANDIDATURE || libelles === LIBELLES_INSCRIPTION ? statutVariant(cle) : 'primary'}`}
                style={{ width: `${total ? (valeur * 100) / total : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ScolariteDashboard() {
  const [annee, setAnnee] = useState(null)
  const [candidatures, setCandidatures] = useState(null)
  const [admissions, setAdmissions] = useState(null)
  const [inscriptions, setInscriptions] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erreur, setErreur] = useState('')

  const charger = useCallback(async () => {
    setLoading(true)
    setErreur('')
    try {
      const anneeCourante = await getAnneeCourante()
      setAnnee(anneeCourante)
      const params = anneeCourante?.id ? { annee_academique_id: anneeCourante.id } : undefined
      const [candRes, admRes, inscRes] = await Promise.all([
        getStatsCandidatures(params),
        getStatsAdmissions(params),
        getStatsInscriptions(params),
      ])
      setCandidatures(candRes.data)
      setAdmissions(admRes.data)
      setInscriptions(inscRes.data)
    } catch (err) {
      setErreur(messageErreur(err, 'Impossible de charger le tableau de bord de la scolarité.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { charger() }, [charger])

  if (loading) return <div className="loading"><div className="spinner"></div></div>

  const admis = (admissions?.par_decision?.ADMIS || 0) + (admissions?.par_decision?.ADMIS_SOUS_RESERVE || 0)
  const aTraiter = (candidatures?.par_statut?.EN_ATTENTE_DE_VERIFICATION || 0)
    + (candidatures?.par_statut?.PIECES_INCOMPLETES || 0)

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <div>
          <h4 className="mb-0">Scolarité</h4>
          <small className="text-muted">
            {annee ? `Année académique ${annee.libelle}` : 'Aucune année académique courante définie'}
          </small>
        </div>
        <button className="btn btn-outline-secondary btn-sm" onClick={charger}>
          <i className="bi bi-arrow-clockwise me-1"></i>Actualiser
        </button>
      </div>

      {erreur && <div className="alert alert-danger">{erreur}</div>}

      <div className="row g-3 mb-3">
        <div className="col-md-3 col-sm-6">
          <CarteChiffre
            titre="Candidatures" valeur={candidatures?.total ?? 0}
            icone="bi-file-earmark-person" couleur="primary" lien="/scolarite/candidatures"
          />
        </div>
        <div className="col-md-3 col-sm-6">
          <CarteChiffre
            titre="Dossiers à traiter" valeur={aTraiter}
            icone="bi-hourglass-split" couleur="warning" lien="/scolarite/candidatures"
          />
        </div>
        <div className="col-md-3 col-sm-6">
          <CarteChiffre
            titre="Admis" valeur={admis}
            icone="bi-check2-circle" couleur="success" lien="/scolarite/admissions"
          />
        </div>
        <div className="col-md-3 col-sm-6">
          <CarteChiffre
            titre="Étudiants inscrits" valeur={inscriptions?.inscrits ?? 0}
            icone="bi-mortarboard" couleur="info" lien="/scolarite/inscriptions"
          />
        </div>
      </div>

      <div className="row g-3">
        <div className="col-lg-4">
          <Repartition
            titre="Candidatures par statut"
            donnees={candidatures?.par_statut}
            libelles={LIBELLES_CANDIDATURE}
          />
        </div>
        <div className="col-lg-4">
          <Repartition
            titre="Inscriptions par statut"
            donnees={inscriptions?.par_statut}
            libelles={LIBELLES_INSCRIPTION}
          />
        </div>
        <div className="col-lg-4">
          <Repartition titre="Effectifs par niveau" donnees={inscriptions?.par_niveau} />
        </div>
        <div className="col-lg-6">
          <Repartition titre="Effectifs par formation" donnees={inscriptions?.par_formation} />
        </div>
        <div className="col-lg-6">
          <Repartition titre="Effectifs par catégorie" donnees={inscriptions?.par_categorie} />
        </div>
      </div>
    </div>
  )
}
