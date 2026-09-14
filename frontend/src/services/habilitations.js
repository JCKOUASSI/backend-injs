/**
 * Console CURP d'administration des comptes (unité U4, prompt C2).
 *
 * Toutes les routes sont gardées côté Django par le drapeau
 * ``flag.curp_ui_admin`` ET le trio d'administration ; ce module ne fait que
 * les appeler. La visibilité de l'interface dérive de la capacité
 * ``habilitations_admin.gerer`` servie par /api/auth/capabilities/ : aucune
 * liste de rôles n'est codée en dur dans l'interface.
 */
import api from './api'

const BASE = '/habilitations'

export const HAB_KEYS = {
  comptes: ['habilitations', 'comptes'],
  roles: ['habilitations', 'roles'],
  roleDetail: (code) => ['habilitations', 'roles', code],
  matrice: ['habilitations', 'matrice'],
  journal: ['habilitations', 'journal'],
  integrite: ['habilitations', 'journal', 'integrite'],
  derogations: ['habilitations', 'derogations'],
  delegations: ['habilitations', 'delegations'],
  revue: ['habilitations', 'revue'],
}

const urlParams = (filtres = {}) => {
  const params = new URLSearchParams()
  Object.entries(filtres).forEach(([cle, valeur]) => {
    if (valeur !== '' && valeur !== null && valeur !== undefined) {
      params.append(cle, valeur)
    }
  })
  const chaine = params.toString()
  return chaine ? `?${chaine}` : ''
}

// ── Comptes ────────────────────────────────────────────────────────────
export const listerComptes = (filtres) =>
  api.get(`${BASE}/comptes/${urlParams(filtres)}`).then((r) => r.data)

export const recupererCompte = (id) =>
  api.get(`${BASE}/comptes/${id}/`).then((r) => r.data)

export const creerCompte = (payload) =>
  api.post(`${BASE}/comptes/`, payload).then((r) => r.data)

export const simulerModification = (id, payload) =>
  api.post(`${BASE}/comptes/${id}/simuler-modification/`, payload).then((r) => r.data)

export const modifierCompte = (id, payload) =>
  api.patch(`${BASE}/comptes/${id}/modifier/`, payload).then((r) => r.data)

export const changerStatutCompte = (id, transition, motif) =>
  api.post(`${BASE}/comptes/${id}/statut/`, { transition, motif }).then((r) => r.data)

export const rechercherPersonnes = (q) =>
  api.get(`${BASE}/personnes/${urlParams({ q })}`).then((r) => r.data.resultats || [])

export const simulerImport = (lignes) =>
  api.post(`${BASE}/comptes/import-simuler/`, { lignes }).then((r) => r.data)

export const recupererRevue = () =>
  api.get(`${BASE}/comptes/revue/`).then((r) => r.data)

// ── Référentiel ─────────────────────────────────────────────────────────
export const listerRolesCurp = () =>
  api.get(`${BASE}/roles/`).then((r) => {
    const data = r.data
    return data.results || data
  })

export const recupererRole = (code) =>
  api.get(`${BASE}/roles/${encodeURIComponent(code)}/`).then((r) => r.data)

export const recupererMatrice = () =>
  api.get(`${BASE}/matrice/`).then((r) => r.data)

// ── Journal ─────────────────────────────────────────────────────────────
export const listerJournal = (filtres) =>
  api.get(`${BASE}/journal/${urlParams(filtres)}`).then((r) => r.data)

export const integriteJournal = () =>
  api.get(`${BASE}/journal/integrite/`).then((r) => r.data)

// ── Dérogations / délégations ───────────────────────────────────────────
export const listerDerogations = (filtres = {}) =>
  api.get(`${BASE}/derogations/${urlParams(filtres)}`).then((r) => r.data)

export const creerDerogation = (payload) =>
  api.post(`${BASE}/derogations/`, payload).then((r) => r.data)

export const revoquerDerogation = (id, motif) =>
  api.post(`${BASE}/derogations/${id}/revoquer/`, { motif }).then((r) => r.data)

export const listerDelegations = (filtres = {}) =>
  api.get(`${BASE}/delegations/${urlParams(filtres)}`).then((r) => r.data)

export const creerDelegation = (payload) =>
  api.post(`${BASE}/delegations/`, payload).then((r) => r.data)

export const terminerDelegation = (id, motif) =>
  api.post(`${BASE}/delegations/${id}/terminer/`, { motif }).then((r) => r.data)

/** Extrait le message français d'une erreur DRF (403, 409, 400). */
export function messageErreur(erreur, repli = 'Une erreur est survenue.') {
  const data = erreur?.response?.data
  if (data?.detail) return data.detail
  if (data && typeof data === 'object') {
    const champs = Object.entries(data)
      .map(([champ, valeur]) => {
        const texte = Array.isArray(valeur) ? valeur.join(' ') : String(valeur)
        return champ === 'non_field_errors' ? texte : `${champ} : ${texte}`
      })
      .join(' — ')
    if (champs) return champs
  }
  return repli
}
