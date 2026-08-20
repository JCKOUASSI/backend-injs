/**
 * Couche API du module EPT-INJS.
 *
 * Réutilise le client HTTP d'INJS (JWT, refresh automatique, gestion d'erreurs)
 * et cible le préfixe /api/v1/eptinjs/.
 */
import { apiDelete, apiGet, apiPatch, apiPost } from '@app/api/client'

const BASE = '/eptinjs'

/* ------------------------------------------------------------ Périodes */

export const fetchPeriodes = (params) => apiGet(`${BASE}/periodes/`, params)
export const createPeriode = (body) => apiPost(`${BASE}/periodes/`, body)
export const updatePeriode = (id, body) => apiPatch(`${BASE}/periodes/${id}/`, body)
export const deletePeriode = (id) => apiDelete(`${BASE}/periodes/${id}/`)
export const fetchParametresPeriode = (id) => apiGet(`${BASE}/periodes/${id}/parametres/`)
export const updateParametresPeriode = (id, body) => apiPatch(`${BASE}/periodes/${id}/parametres/`, body)
export const fetchParametresDefaut = () => apiGet(`${BASE}/parametres/defaut/`)
export const updateParametresDefaut = (body) => apiPatch(`${BASE}/parametres/defaut/`, body)

/* -------------------------------------------------------- Jours fériés */

export const fetchJoursFeries = (params) => apiGet(`${BASE}/jours-feries/`, params)
export const createJourFerie = (body) => apiPost(`${BASE}/jours-feries/`, body)
export const deleteJourFerie = (id) => apiDelete(`${BASE}/jours-feries/${id}/`)

/* ------------------------------------------------------------- Groupes */

export const fetchGroupes = (params) => apiGet(`${BASE}/groupes/`, params)
export const createGroupe = (body) => apiPost(`${BASE}/groupes/`, body)
export const deleteGroupe = (id) => apiDelete(`${BASE}/groupes/${id}/`)
export const fetchGroupeMembres = (id) => apiGet(`${BASE}/groupes/${id}/membres/`)
export const ajouterEtudiantsGroupe = (id, students) =>
  apiPost(`${BASE}/groupes/${id}/ajouter-etudiants/`, { students })
export const retirerEtudiantsGroupe = (id, students) =>
  apiPost(`${BASE}/groupes/${id}/retirer-etudiants/`, { students })
export const repartirGroupes = (body) => apiPost(`${BASE}/groupes/repartir/`, body)

/* ---------------------------------------------------------- Programmes */

export const fetchProgrammes = (params) => apiGet(`${BASE}/programmes/`, params)
export const createProgramme = (body) => apiPost(`${BASE}/programmes/`, body)
export const updateProgramme = (id, body) => apiPatch(`${BASE}/programmes/${id}/`, body)
export const deleteProgramme = (id) => apiDelete(`${BASE}/programmes/${id}/`)
export const importerMaquette = (body) => apiPost(`${BASE}/programmes/importer-maquette/`, body)
export const affecterEnseignant = (body) => apiPost(`${BASE}/programmes/affecter-enseignant/`, body)

/* ------------------------------------------------------------- Séances */

export const fetchSeances = (params) => apiGet(`${BASE}/seances/`, params)
export const fetchSeance = (id) => apiGet(`${BASE}/seances/${id}/`)
export const createSeance = (body) => apiPost(`${BASE}/seances/`, body)
export const updateSeance = (id, body) => apiPatch(`${BASE}/seances/${id}/`, body)
export const deleteSeance = (id) => apiDelete(`${BASE}/seances/${id}/`)
export const fetchGrille = (params) => apiGet(`${BASE}/seances/grille/`, params)
export const fetchConflits = (params) => apiGet(`${BASE}/seances/conflits/`, params)
export const fetchStatistiquesEdt = (params) => apiGet(`${BASE}/seances/statistiques/`, params)
export const fetchMonPlanning = (params) => apiGet(`${BASE}/seances/mon-planning/`, params)
export const genererPlanning = (body) => apiPost(`${BASE}/seances/generer/`, body)

export const demarrerSeance = (id) => apiPost(`${BASE}/seances/${id}/demarrer/`, {})
export const terminerSeance = (id) => apiPost(`${BASE}/seances/${id}/terminer/`, {})
export const annulerSeance = (id, motif) => apiPost(`${BASE}/seances/${id}/annuler/`, { motif })

/* ----------------------------------------------------- Présences / QR */

export const fetchQrSeance = (id) => apiGet(`${BASE}/seances/${id}/qr/`)
export const genererQrSeance = (id, regenerer = false) =>
  apiPost(`${BASE}/seances/${id}/qr/`, { regenerer })
export const fetchEmargement = (id) => apiGet(`${BASE}/seances/${id}/emargement/`)
export const constituerListe = (id) => apiPost(`${BASE}/seances/${id}/emargement/`, {})
export const marquerPresences = (id, body) => apiPost(`${BASE}/seances/${id}/marquer/`, body)
export const forcerBadgeage = (id, body) => apiPost(`${BASE}/seances/${id}/forcer-badgeage/`, body || {})

/* --------------------------------------------------------------- Badge */

export const scannerBadge = (body) => apiPost(`${BASE}/badge/scan/`, body)
export const fetchStatutBadge = () => apiGet(`${BASE}/badge/statut/`)
export const envoyerHeartbeat = (body) => apiPost(`${BASE}/badge/heartbeat/`, body)
export const fetchMonHistoriqueBadge = () => apiGet(`${BASE}/badge/mon-historique/`)

/* --------------------------------------------------------- Cours ECUE */

export const fetchCatalogueCours = (params) => apiGet(`${BASE}/cours/`, params)
export const fetchOffreCours = (params) => apiGet(`${BASE}/cours/offering/`, params)

/* -------------------------------------------------------- Générations */

export const fetchRuns = (params) => apiGet(`${BASE}/runs/`, params)

/* ------------------------------------------------------------- Libellés */

export const NATURES_SEANCE = [
  { value: 'cm', label: 'Cours magistral' },
  { value: 'td', label: 'Travaux dirigés' },
  { value: 'tp', label: 'Travaux pratiques' },
]

export const STATUTS_SEANCE = [
  { value: 'planifiee', label: 'Planifiée' },
  { value: 'en_cours', label: 'En cours' },
  { value: 'terminee', label: 'Terminée' },
  { value: 'annulee', label: 'Annulée' },
]

export const STATUTS_OFFRE = [
  { value: 'non_programme', label: 'Non programmé' },
  { value: 'programme', label: 'Programmé' },
  { value: 'planifie', label: 'Planifié' },
  { value: 'en_cours', label: 'En cours' },
  { value: 'termine', label: 'Terminé' },
]

export const STATUTS_POINTAGE = [
  { value: 'present', label: 'Présent' },
  { value: 'retard', label: 'Retard' },
  { value: 'absent', label: 'Absent' },
  { value: 'excuse', label: 'Excusé' },
  { value: 'force', label: 'Forcé' },
]

export const JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
