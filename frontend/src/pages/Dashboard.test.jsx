import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor, within, fireEvent } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { makeUser } from '@/test/utils/factories'
import { dashboardStatsWithPeriods } from '@/test/fixtures/dashboard'
import { useAuth } from '@/context/AuthContext'
import Dashboard from '@/pages/Dashboard'

function WaitForAuth({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading || !isAuthenticated) return <div className="loading"><div className="spinner" /></div>
  return children
}

const BASE = 'http://testserver'
const paramsOf = (url) => new URL(url, BASE).searchParams
const callsTo = (pathOnly) =>
  apiMock.get.mock.calls
    .filter(([p]) => p.split('?')[0] === pathOnly)
    .map(([p]) => paramsOf(p))

const mountDashboard = (me, entry = '/') => {
  apiController.setMe(me)
  return renderWithProviders(
    <WaitForAuth><Dashboard /></WaitForAuth>,
    { authUser: me, initialEntries: [entry], routePattern: '/' },
  )
}

// ADMIN : peut filtrer par secrétariat → le groupe de boutons période est
// celui de la barre latérale (« Jour spécifique / Semaine / Mois / Année »).
const adminMe = () => makeUser('ADMIN', { username: 'admin' })

const periodGroup = () => screen.getByRole('group', { name: /filtre de période dashboard/i })
const clickPeriod = (label) =>
  fireEvent.click(within(periodGroup()).getByRole('button', { name: label }))

describe('pages/Dashboard.jsx — chargement et période de présence', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    apiController.setRoute('/formations/stats/', () => dashboardStatsWithPeriods())
    apiController.setRoute('/formations/list/', () => ({ results: [], count: 0 }))
    apiController.setRoute('/formations/secretariats/', () => [])
  })

  it('appelle les statistiques et les formations en cours au chargement', async () => {
    mountDashboard(adminMe())

    await waitFor(() => expect(callsTo('/formations/stats/').length).toBeGreaterThan(0))
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(0))
    const list = callsTo('/formations/list/').at(-1)
    expect(list.get('statut')).toBe('EN_COURS')
    expect(list.get('page_size')).toBe('10')
    // Date = aujourd'hui : on reste sur « séance en cours ».
    expect(list.get('seance_en_cours')).toBe('true')
    expect(list.has('date_mode')).toBe(false)
  })

  it('avec un jour spécifique dans le passé, la liste utilise le mode date', async () => {
    mountDashboard(adminMe(), '/?reference_date=2026-01-15&presence_period=jour')
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(0))
    const list = callsTo('/formations/list/').at(-1)
    expect(list.get('date_mode')).toBe('date')
    expect(list.get('date')).toBe('2026-01-15')
    expect(list.has('seance_en_cours')).toBe(false)
  })

  it('bascule les indicateurs affichés selon la période (Jour → Année)', async () => {
    mountDashboard(adminMe())
    await waitFor(() => expect(callsTo('/formations/stats/').length).toBeGreaterThan(0))

    // Le titre de la carte de présence reflète la période courante.
    expect(screen.getByText(/présences du /i)).toBeInTheDocument()
    clickPeriod('Année')
    await waitFor(() => expect(screen.getByText(/présences de l.année/i)).toBeInTheDocument())
  })

  // Régression pour le bug de closure périmée (docs §10.5), corrigé au LOT 4 :
  // loadDashboardData listait presencePeriod dans l'effet déclencheur mais pas
  // dans ses propres dépendances de useCallback. Les bascules de période
  // rappelaient une closure figée sur l'ancienne valeur.
  it('Jour(date passée) → Semaine : la liste revient aux séances en cours', async () => {
    mountDashboard(adminMe(), '/?reference_date=2026-01-15&presence_period=jour')
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(0))
    expect(callsTo('/formations/list/').at(-1).get('date_mode')).toBe('date')

    const nBefore = callsTo('/formations/list/').length
    clickPeriod('Semaine')
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(nBefore))

    const q = callsTo('/formations/list/').at(-1)
    expect(q.has('date_mode')).toBe(false)
    expect(q.has('date')).toBe(false)
    expect(q.get('seance_en_cours')).toBe('true')
  })

  it('Semaine(date passée) → Jour : la liste passe en mode date épinglé', async () => {
    mountDashboard(adminMe(), '/?reference_date=2026-01-15&presence_period=semaine')
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(0))
    // En « Semaine », même avec une date passée, on reste sur le temps réel.
    expect(callsTo('/formations/list/').at(-1).get('seance_en_cours')).toBe('true')

    const nBefore = callsTo('/formations/list/').length
    clickPeriod('Jour spécifique')
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(nBefore))

    const q = callsTo('/formations/list/').at(-1)
    expect(q.get('date_mode')).toBe('date')
    expect(q.get('date')).toBe('2026-01-15')
    expect(q.has('seance_en_cours')).toBe(false)
  })
})

describe('pages/Dashboard.jsx — gestion des erreurs de chargement (§10.6)', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    apiController.setRoute('/formations/secretariats/', () => [])
  })

  const boom = () => {
    throw Object.assign(new Error('réseau'), { response: { data: { detail: 'indisponible' } } })
  }

  it('échec des DEUX requêtes → message d’erreur totale', async () => {
    apiController.setRoute('/formations/stats/', boom)
    apiController.setRoute('/formations/list/', boom)

    mountDashboard(adminMe())
    expect(await screen.findByText('Erreur lors du chargement des données')).toBeInTheDocument()
    expect(screen.queryByText(/certaines données/i)).not.toBeInTheDocument()
  })

  it('une seule requête échoue → message d’erreur partielle', async () => {
    apiController.setRoute('/formations/stats/', () => dashboardStatsWithPeriods())
    apiController.setRoute('/formations/list/', boom)

    mountDashboard(adminMe())
    expect(await screen.findByText(/certaines données/i)).toBeInTheDocument()
    expect(screen.queryByText('Erreur lors du chargement des données')).not.toBeInTheDocument()
  })
})
