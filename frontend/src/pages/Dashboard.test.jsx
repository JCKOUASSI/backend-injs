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

  // [écart] BUG CONFIRMÉ — closure périmée sur la période de présence.
  // Contexte : loadDashboardData (useCallback, Dashboard.jsx ~L55) omet
  // `presencePeriod` de ses dépendances, alors que l'effet déclencheur (L103)
  // l'inclut. Quand on passe de « Jour spécifique » (avec une date passée) à
  // « Semaine », l'effet rappelle une ANCIENNE closure encore en mode `jour` :
  // la liste /formations/list/ reste épinglée sur la date (date_mode=date)
  // au lieu de revenir à « séance en cours » (seance_en_cours=true).
  // Comportement ATTENDU (à rétablir lors d'un lot correctif) :
  //   la requête après bascule ne doit plus contenir ni date_mode ni date,
  //   et doit porter seance_en_cours=true.
  // On fige ici le comportement OBSERVÉ pour ne pas corriger la logique en
  // silence ; voir docs/TESTS_FRONTEND.md §10.5.
  it('[écart] garde le mode date après Jour(date passée) → Semaine (closure périmée)', async () => {
    mountDashboard(adminMe(), '/?reference_date=2026-01-15&presence_period=jour')
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(0))
    expect(callsTo('/formations/list/').at(-1).get('date_mode')).toBe('date')

    const nBefore = callsTo('/formations/list/').length
    clickPeriod('Semaine')
    // Une nouvelle requête est bien émise après la bascule…
    await waitFor(() => expect(callsTo('/formations/list/').length).toBeGreaterThan(nBefore))
    // …mais elle porte ENCORE l'ancien mode date (bug de closure constaté).
    const q = callsTo('/formations/list/').at(-1)
    expect(q.get('date_mode')).toBe('date')
    expect(q.get('date')).toBe('2026-01-15')
    expect(q.has('seance_en_cours')).toBe(false)
  })
})
