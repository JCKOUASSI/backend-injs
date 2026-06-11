/** Aligné sur backend/authentication/role_groups.py */

export const ADMIN_LEVEL_ROLES = ['ADMIN', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN']

export const ALLOWED_WEB_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'FINANCE',
  'ENCADRANT',
]

export const STAFF_WEB_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'ENCADRANT',
]

/** FINANCE n'est pas du personnel opérationnel — module finance dédié uniquement. */
export const FINANCE_MODULE_ROLES = ['FINANCE', 'DIRECTION']

export const STATS_ALLOWED_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'FINANCE',
  'ENCADRANT',
]

export const USERS_ALLOWED_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
]

export const IMPORT_ALLOWED_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
]

/** Mutations formations / modules / séances / inscriptions (aligné IsSecretariatOrEncadrantOrDFRC + secrétariat). */
export const FORMATION_MUTATION_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
]

/** POST /formations/participants/ — secrétariat exclu (role_groups exclude add_participant). */
export const PARTICIPANT_CREATE_ROLES = [...ADMIN_LEVEL_ROLES]

/** Modification / suppression fiche auditeur — secrétariat autorisé. */
export const PARTICIPANT_MANAGE_ROLES = FORMATION_MUTATION_ROLES

export const PRESENCE_VIEW_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'ENCADRANT',
]

export const PRESENCE_ACTION_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'ENCADRANT',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
]

export const SUPERVISION_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'ENCADRANT',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
]

/** Mutations comptes utilisateurs (aligné IsSecretariatOrDFRC — DIRECTION lecture seule). */
export const USER_MUTATION_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
]

export const DASHBOARD_SECRETARIAT_FILTER_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
]

export function isAdminLevelRole(role) {
  return ADMIN_LEVEL_ROLES.includes(role)
}

export function canMutateFormations(role) {
  return FORMATION_MUTATION_ROLES.includes(role)
}

export function canCreateParticipant(role) {
  return PARTICIPANT_CREATE_ROLES.includes(role)
}

export function canManageParticipant(role) {
  return PARTICIPANT_MANAGE_ROLES.includes(role)
}

export function canViewPresences(role) {
  return PRESENCE_VIEW_ROLES.includes(role)
}

export function canPresenceAction(role) {
  return PRESENCE_ACTION_ROLES.includes(role)
}

export function canSuperviseSessions(role) {
  return SUPERVISION_ROLES.includes(role)
}

export function canMutateUsers(role) {
  return USER_MUTATION_ROLES.includes(role)
}

export function canFilterDashboardBySecretariat(role) {
  return DASHBOARD_SECRETARIAT_FILTER_ROLES.includes(role)
}

export function isWebRoleAllowed(role) {
  return ALLOWED_WEB_ROLES.includes(role)
}

export function webLoginForbiddenMessage(role) {
  if (role === 'AUDITEUR') {
    return 'Les comptes auditeur sont réservés à l\'application mobile.'
  }
  if (role === 'FORMATEUR') {
    return 'Les comptes formateur sont réservés à l\'application mobile.'
  }
  return 'Ce compte n\'a pas accès à la plateforme web.'
}
