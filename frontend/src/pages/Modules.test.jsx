import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { makeUser } from '@/test/utils/factories'
import Modules from '@/pages/Modules'

const LABELS = {
  ADMIN: 'Administrateur', DIRECTION: 'Direction', CHEF_CPFAE_ADMIN: 'Chef INJS Admin',
  CPFAE_ADMIN: 'INJS Admin', CHEF_SECRETARIAT: 'Chef Secrétariat', SECRETARIAT: 'Secrétariat',
  FINANCE: 'Finance', ARCHIVE: 'Archiviste', ENCADRANT: 'Encadrant', SUPERVISEUR: 'Superviseur',
  FORMATEUR: 'Formateur', AUDITEUR: 'Étudiant',
}

const adminMe = () =>
  makeUser('ADMIN', {
    username: 'admin',
    role_context: {
      labels: LABELS,
      badge_account_roles: ['AUDITEUR', 'FORMATEUR'],
      can_mutate_users: true,
      manageable_roles: ['ENCADRANT', 'FORMATEUR', 'AUDITEUR'],
      staff_filter_roles: ['FINANCE', 'ENCADRANT'],
    },
  })

/** Référentiels : les grades connus sont 1 et 2 ; toute autre valeur est invalide. */
const mountModules = (initialEntry = '/modules') => {
  apiController.setMe(adminMe())
  apiController.setRoute('/formations/referentiels/', () => ({
    formations: [],
    // formations_reelles non vide : l'effet référentiels ne lance pas le
    // chargement de secours /formations/list/?page_size=500.
    formations_reelles: [{ id: 1, formation: 'Formation 1' }],
    grades: [],
    grades_modules: [1, 2],
    categories: [],
    sites: [],
    batiments: [],
    salles: [],
    types_secretariat: [],
    vagues: [],
    groupes: [],
    modules: [],
  }))
  apiController.setRoute('/formations/list/', () => ({
    count: 0,
    total_pages: 1,
    results: [],
  }))
  return renderWithProviders(<Modules />, {
    authUser: adminMe(),
    initialEntries: [initialEntry],
    routePattern: '/modules',
  })
}

/** Appels du chargement des modules (page_size=50), hors fallback référentiels. */
const moduleCalls = () =>
  apiMock.get.mock.calls
    .map(([p]) => p)
    .filter((p) => p.startsWith('/formations/list/') && p.includes('page_size=50'))
    .map((p) => new URL(p, 'http://testserver').searchParams)

beforeEach(() => {
  apiController.reset()
  window.localStorage.clear()
  window.sessionStorage.clear()
})

describe('pages/Modules.jsx — nettoyage des filtres obsolètes (§10.2 LOT 6)', () => {
  it('écarte un filtre grade absent des référentiels, recharge sans lui et notifie', async () => {
    // Lien obsolète : grade=999 ne figure dans aucun référentiel ; statut, lui,
    // est valide (STATUT_VALUES) et doit être conservé.
    mountModules('/modules?grade=999&statut=PLANIFIEE&date_mode=all')

    // Après l'arrivée des référentiels, la dernière requête modules ne porte
    // plus le grade invalide, tout en conservant le statut valide.
    await waitFor(() => {
      const calls = moduleCalls()
      expect(calls.length).toBeGreaterThan(0)
      const last = calls.at(-1)
      expect(last.get('grade')).toBe(null)
      expect(last.get('statut')).toBe('PLANIFIEE')
    })

    // L'utilisateur est informé du filtre écarté (message complet du toast).
    expect(
      await screen.findByText(/filtre\(s\) ignoré\(s\), valeur inconnue : grade/i),
    ).toBeInTheDocument()
  })

  it('ne touche pas aux filtres valides et n’affiche aucune alerte', async () => {
    mountModules('/modules?grade=2&statut=PLANIFIEE&date_mode=all')

    await waitFor(() => {
      const calls = moduleCalls()
      expect(calls.length).toBeGreaterThan(0)
      expect(calls.at(-1).get('grade')).toBe('2')
    })
    expect(screen.queryByText(/filtre\(s\) ignoré/i)).not.toBeInTheDocument()
  })
})
