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
