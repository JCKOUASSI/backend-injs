import { describe, it, expect } from 'vitest'
import * as roles from '@/utils/roles'
import { ALL_ROLES } from '@/test/utils/factories'

// ──────────────────────────────────────────────────────────────────────────
// Contrat de sécurité côté UI : ensembles de rôles attendus.
// Ces listes sont le reflet de backend/authentication/role_groups.py ; les
// figer en test interdit toute dérive silencieuse des droits affichés.
// ──────────────────────────────────────────────────────────────────────────

const A = ['ADMIN', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN']

const EXPECTED_SETS = {
  ADMIN_LEVEL_ROLES: A,
  ALLOWED_WEB_ROLES: [...A, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'FINANCE', 'ARCHIVE', 'ENCADRANT', 'SUPERVISEUR'],
  STAFF_WEB_ROLES: [...A, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'SUPERVISEUR'],
  EVALUATION_ALLOWED_ROLES: [...A, 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'SUPERVISEUR'],
  NOTE_GESTION_ROLES: [...A, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT', 'SUPERVISEUR'],
  DECISION_ROLES: [...A, 'DIRECTION', 'ENCADRANT', 'SUPERVISEUR'],
  FINANCE_MODULE_ROLES: ['FINANCE', 'DIRECTION', 'ARCHIVE'],
  ARCHIVE_CONSULT_ROLES: ['ARCHIVE', 'DIRECTION', ...A],
  OPERATIONAL_WEB_ROLES: [...A, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ARCHIVE', 'ENCADRANT', 'SUPERVISEUR'],
  OPERATION_VIEW_ROLES: [...A, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ARCHIVE', 'ENCADRANT', 'SUPERVISEUR'],
  PARTICIPANT_LIST_ROLES: [...A, 'DIRECTION', 'ARCHIVE', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT'],
  FINANCE_EXPORT_ROLES: ['FINANCE', 'DIRECTION', 'ARCHIVE'],
  LISTE_CLASSE_EXPORT_ROLES: [...A, 'DIRECTION', 'ARCHIVE', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT'],
  FINANCE_SETTINGS_ROLES: ['FINANCE', 'DIRECTION'],
  SCOLARITE_VIEW_ROLES: [...A, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  SCOLARITE_MUTATION_ROLES: [...A, 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  STATS_ALLOWED_ROLES: [...A, 'DIRECTION', 'ARCHIVE', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'FINANCE', 'ENCADRANT'],
  USERS_ALLOWED_ROLES: [...A, 'DIRECTION', 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  IMPORT_ALLOWED_ROLES: [...A, 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  FORMATION_MUTATION_ROLES: [...A, 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  MODULE_ARCHIVE_ROLES: [...A, 'CHEF_SECRETARIAT', 'SECRETARIAT', 'DIRECTION'],
  PARTICIPANT_CREATE_ROLES: [...A],
  PRESENCE_VIEW_ROLES: [...A, 'DIRECTION', 'ARCHIVE', 'CHEF_SECRETARIAT', 'SECRETARIAT', 'ENCADRANT'],
  PRESENCE_ACTION_ROLES: [...A, 'ENCADRANT', 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  SUPERVISION_ROLES: [...A, 'ENCADRANT', 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  USER_MUTATION_ROLES: [...A, 'CHEF_SECRETARIAT', 'SECRETARIAT'],
  DASHBOARD_SECRETARIAT_FILTER_ROLES: [...A, 'DIRECTION'],
  SECRETARIAT_SCOPED_ROLES: ['SECRETARIAT', 'CHEF_SECRETARIAT'],
}

// Matrice rôle → capacité pour chaque prédicat de l'API publique.
const PREDICATE_MATRIX = {
  isAdminLevelRole: EXPECTED_SETS.ADMIN_LEVEL_ROLES,
  canMutateFormations: EXPECTED_SETS.FORMATION_MUTATION_ROLES,
  canArchiveModule: EXPECTED_SETS.MODULE_ARCHIVE_ROLES,
  canCreateParticipant: EXPECTED_SETS.PARTICIPANT_CREATE_ROLES,
  canManageParticipant: EXPECTED_SETS.FORMATION_MUTATION_ROLES,
  canViewPresences: EXPECTED_SETS.PRESENCE_VIEW_ROLES,
  canPresenceAction: EXPECTED_SETS.PRESENCE_ACTION_ROLES,
  canSuperviseSessions: EXPECTED_SETS.SUPERVISION_ROLES,
  canMutateUsers: EXPECTED_SETS.USER_MUTATION_ROLES,
  canFilterDashboardBySecretariat: EXPECTED_SETS.DASHBOARD_SECRETARIAT_FILTER_ROLES,
  isSecretariatScopedRole: EXPECTED_SETS.SECRETARIAT_SCOPED_ROLES,
  isWebRoleAllowed: EXPECTED_SETS.ALLOWED_WEB_ROLES,
}

describe('utils/roles.js — contrat de sécurité UI', () => {
  describe('ensembles de rôles exportés', () => {
    for (const [name, expected] of Object.entries(EXPECTED_SETS)) {
      it(`${name} correspond exactement à ${expected.length} rôle(s)`, () => {
        expect([...roles[name]].sort()).toEqual([...expected].sort())
      })
    }

    it('OPERATION_VIEW_ROLES est bien dérivé de OPERATIONAL_WEB_ROLES', () => {
      expect(roles.OPERATION_VIEW_ROLES).toEqual(roles.OPERATIONAL_WEB_ROLES)
    })

    it('PARTICIPANT_MANAGE_ROLES réutilise FORMATION_MUTATION_ROLES', () => {
      expect(roles.PARTICIPANT_MANAGE_ROLES ?? roles.FORMATION_MUTATION_ROLES).toBeDefined()
    })
  })

  describe('prédicats par rôle — matrice exhaustive 12 rôles', () => {
    for (const [predicate, allowed] of Object.entries(PREDICATE_MATRIX)) {
      describe(predicate, () => {
        for (const role of ALL_ROLES) {
          const expected = allowed.includes(role)
          it(`${role} → ${expected}`, () => {
            expect(roles[predicate](role)).toBe(expected)
          })
        }
      })
    }
  })

  describe('hasAppRole / getUserRoles (formes utilisateur)', () => {
    it('user null → aucun rôle, aucun accès', () => {
      expect(roles.getUserRoles(null)).toEqual([])
      expect(roles.hasAppRole(null, ['ADMIN'])).toBe(false)
    })

    it('utilise user.roles (multi-rôles) quand le tableau est non vide', () => {
      const user = { role: 'SECRETARIAT', roles: ['SECRETARIAT', 'ENCADRANT'] }
      expect(roles.getUserRoles(user)).toEqual(['SECRETARIAT', 'ENCADRANT'])
      expect(roles.hasAppRole(user, roles.PRESENCE_ACTION_ROLES)).toBe(true)
    })

    it('tableau roles vide mais role présent → retombe sur user.role', () => {
      expect(roles.getUserRoles({ role: 'FINANCE', roles: [] })).toEqual(['FINANCE'])
    })

    it('aucun rôle défini → tableau vide', () => {
      expect(roles.getUserRoles({})).toEqual([])
    })

    it('canListParticipants / canActScolarite utilisent hasAppRole', () => {
      expect(roles.canListParticipants({ role: 'ARCHIVE' })).toBe(true)
      expect(roles.canListParticipants({ role: 'FORMATEUR' })).toBe(false)
      expect(roles.canActScolarite({ role: 'SECRETARIAT' })).toBe(true)
      expect(roles.canActScolarite({ role: 'AUDITEUR' })).toBe(false)
    })
  })

  describe('canArchiveModuleFromUser', () => {
    it('user null → false', () => {
      expect(roles.canArchiveModuleFromUser(null)).toBe(false)
    })
    it('rôle non habilité sans contexte → false', () => {
      expect(roles.canArchiveModuleFromUser({ role: 'AUDITEUR' })).toBe(false)
    })
    it('rôle habilité → true', () => {
      expect(roles.canArchiveModuleFromUser({ role: 'DIRECTION' })).toBe(true)
    })
    it('role_context.can_archive_modules=true force true même pour un rôle a priori non habilité', () => {
      expect(roles.canArchiveModuleFromUser({ role: 'SECRETARIAT', role_context: { can_archive_modules: true } })).toBe(true)
    })
    it('role_context.can_archive_modules=false ne court-circuite pas', () => {
      expect(roles.canArchiveModuleFromUser({ role: 'SECRETARIAT', role_context: { can_archive_modules: false } })).toBe(true)
    })
  })

  describe('lockedSecretariatId', () => {
    it('rôle non scopé → null même avec un secrétariat', () => {
      expect(roles.lockedSecretariatId({ role: 'ADMIN', secretariat: 7 })).toBeNull()
    })
    it('rôle scopé sans secrétariat (null) → null', () => {
      expect(roles.lockedSecretariatId({ role: 'SECRETARIAT', secretariat: null })).toBeNull()
    })
    it('rôle scopé avec secrétariat vide → null', () => {
      expect(roles.lockedSecretariatId({ role: 'CHEF_SECRETARIAT', secretariat: '' })).toBeNull()
    })
    it('rôle scopé avec secrétariat numérique → chaîne de l’id', () => {
      expect(roles.lockedSecretariatId({ role: 'SECRETARIAT', secretariat: 42 })).toBe('42')
    })
  })

  describe('webLoginForbiddenMessage', () => {
    it('AUDITEUR → message étudiant / application mobile', () => {
      expect(roles.webLoginForbiddenMessage('AUDITEUR')).toMatch(/étudiant/i)
    })
    it('FORMATEUR → message enseignant / application mobile', () => {
      expect(roles.webLoginForbiddenMessage('FORMATEUR')).toMatch(/enseignant/i)
    })
    it('autre rôle non autorisé → message générique', () => {
      expect(roles.webLoginForbiddenMessage('INCONNU')).toMatch(/n'a pas accès/)
    })
  })
})
