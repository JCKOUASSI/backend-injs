/** Aligné sur backend/authentication/role_groups.py */

export const ADMIN_LEVEL_ROLES = ['ADMIN', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN']

export const ALLOWED_WEB_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'FINANCE',
  'ARCHIVE',
  'ENCADRANT',
  'SUPERVISEUR',
]

export const STAFF_WEB_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'ENCADRANT',
  'SUPERVISEUR',
]

/** Module suivi-évaluation (questionnaires). */
export const EVALUATION_ALLOWED_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'ENCADRANT',
  'SUPERVISEUR',
]

/** Gestion des notes/épreuves/moyennes (aligné IsGestionNotes). */
export const NOTE_GESTION_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'ENCADRANT',
  'SUPERVISEUR',
]

/** Validation des décisions pédagogiques (aligné IsDecisionValidator). */
export const DECISION_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'ENCADRANT',
  'SUPERVISEUR',
]

/** FINANCE et ARCHIVE : module finance dédié (consultation + export). */
export const FINANCE_MODULE_ROLES = ['FINANCE', 'DIRECTION', 'ARCHIVE']

/** Consultation globale en lecture seule (fiches, données archivées). */
export const ARCHIVE_CONSULT_ROLES = ['ARCHIVE', 'DIRECTION', ...ADMIN_LEVEL_ROLES]

/** Navigation opérationnelle + consultation globale (cours, auditeurs, fiches). */
export const OPERATION_VIEW_ROLES = [...STAFF_WEB_ROLES, 'DIRECTION', 'ARCHIVE']

/** Exports finance formateurs / encadrants (sans paramétrage). */
export const FINANCE_EXPORT_ROLES = ['FINANCE', 'DIRECTION', 'ARCHIVE']

/** Export liste de classe auditeurs par groupe. */
export const LISTE_CLASSE_EXPORT_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'ARCHIVE',
  'CHEF_SECRETARIAT',
  'SECRETARIAT',
  'ENCADRANT',
]

/** Paramétrage et ajustements finance (hors archiviste). */
export const FINANCE_SETTINGS_ROLES = ['FINANCE', 'DIRECTION']

export const STATS_ALLOWED_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'ARCHIVE',
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

/** Archivage de modules (masqués des listes opérationnelles). */
export const MODULE_ARCHIVE_ROLES = [
  ...FORMATION_MUTATION_ROLES,
  'DIRECTION',
]

/** POST /formations/participants/ — secrétariat exclu (role_groups exclude add_participant). */
export const PARTICIPANT_CREATE_ROLES = [...ADMIN_LEVEL_ROLES]

/** Modification / suppression fiche auditeur — secrétariat autorisé. */
export const PARTICIPANT_MANAGE_ROLES = FORMATION_MUTATION_ROLES

export const PRESENCE_VIEW_ROLES = [
  ...ADMIN_LEVEL_ROLES,
  'DIRECTION',
  'ARCHIVE',
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

/** Comptes limités aux données de leur secrétariat (stats, dashboard opérationnel). */
export const SECRETARIAT_SCOPED_ROLES = ['SECRETARIAT', 'CHEF_SECRETARIAT']

export function isAdminLevelRole(role) {
  return ADMIN_LEVEL_ROLES.includes(role)
}

export function canMutateFormations(role) {
  return FORMATION_MUTATION_ROLES.includes(role)
}

export function canArchiveModule(role) {
  return MODULE_ARCHIVE_ROLES.includes(role)
}

/** Archivage module — role_context API en priorité, sinon rôle effectif. */
export function canArchiveModuleFromUser(user) {
  if (!user) return false
  if (user.role_context?.can_archive_modules === true) return true
  return canArchiveModule(user.role)
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

export function isSecretariatScopedRole(role) {
  return SECRETARIAT_SCOPED_ROLES.includes(role)
}

/** ID secrétariat imposé pour un compte secrétariat (null si non applicable). */
export function lockedSecretariatId(user) {
  if (!isSecretariatScopedRole(user?.role) || user?.secretariat == null || user?.secretariat === '') {
    return null
  }
  return String(user.secretariat)
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

export function hasAppRole(user, allowedRoles) {
  if (!user || !user.role) return false
  return allowedRoles.includes(user.role)
}
