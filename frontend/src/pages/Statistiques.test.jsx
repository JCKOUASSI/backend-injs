import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { makeUser } from '@/test/utils/factories'
import { useAuth } from '@/context/AuthContext'
import Statistiques from '@/pages/Statistiques'

// Reproduit la garde ProtectedRoute de production : la page ne se monte
// qu'une fois l'utilisateur courant résolu (GET /auth/me), comme en vrai.
function WaitForAuth({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading || !isAuthenticated) return <div className="loading"><div className="spinner" /></div>
  return children
}

const SECRETARIATS = [
  { id: 1, nom: 'INJS Centre' },
  { id: 2, nom: 'INJS Marcory' },
  { id: 3, nom: 'INJS Yopougon' },
]
const FORMATIONS = [
  { id: 10, formation: 'Licence 1 LSF' },
  { id: 11, formation: 'Licence 2 LSF' },
]

const BASE = 'http://testserver'
const paramsOf = (url) => new URL(url, BASE).searchParams
const callsTo = (pathOnly) =>
  apiMock.get.mock.calls
    .filter(([p]) => p.split('?')[0] === pathOnly)
    .map(([p]) => paramsOf(p))
const lastParams = (pathOnly) => callsTo(pathOnly).at(-1) ?? null

/** Distingue l'appel « méta-listes » (React Query) des chargements d'onglets. */
const isMetaCall = (q) => (q.get('sections') || '').includes('secretariats_liste')

const mountStats = (me, initialEntry = '/statistiques') => {
  apiController.setMe(me)
  return renderWithProviders(
    <WaitForAuth><Statistiques /></WaitForAuth>,
    { authUser: me, initialEntries: [initialEntry], routePattern: '/statistiques' },
  )
}

const adminMe = () => makeUser('ADMIN', { username: 'admin' })

const selectGlobalSecretariat = async (nom) => {
  const option = await screen.findByRole('option', { name: nom })
  const select = option.closest('select')
  fireEvent.change(select, { target: { value: String(SECRETARIATS.find((s) => s.nom === nom).id) } })
  return select
}
const resetGlobalSecretariat = async () => {
  const option = await screen.findByRole('option', { name: 'Tous les secrétariats' })
  const select = option.closest('select')
  fireEvent.change(select, { target: { value: '' } })
}

describe('pages/Statistiques.jsx — périmètre secrétariat (isolation des données)', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()

    // Endpoint principal : méta-listes (React Query) vs données d'onglet.
    apiController.setRoute('/statistiques/', (path) => {
      const q = paramsOf(path)
      if (isMetaCall(q)) {
        return {
          formations_liste: FORMATIONS,
          secretariats_liste: SECRETARIATS,
          filtre_actif: { scope_locked: false },
        }
      }
      return {}
    })
    apiController.setRoute('/statistiques/point-journalier/', () => ({
      tableaux: [],
      tableaux_complets: [],
    }))
    apiController.setRoute('/statistiques/bilans/', () => ({
      bilans: [],
      tableaux_complets: [],
    }))
    apiController.setRoute('/statistiques/alertes/seuils/', () => ({
      seuils: [],
      indicateurs: [],
      synthese: {},
      seuils_vides: true,
    }))
  })

  it('charge la vue d’ensemble sans secrétariat forcé pour un administrateur', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    const params = lastParams('/statistiques/')
    expect(params.get('secretariat_id')).toBe(null)
    // Le sélecteur global de secrétariat est bien proposé (non verrouillé).
    expect(screen.getByRole('option', { name: 'Tous les secrétariats' })).toBeInTheDocument()
  })

  it('applique le filtre global de secrétariat à la requête de statistiques', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Marcory')

    await waitFor(() => expect(lastParams('/statistiques/').get('secretariat_id')).toBe('2'))
    // L'appel méta (listes) respecte aussi le périmètre.
    const meta = callsTo('/statistiques/').filter(isMetaCall).at(-1)
    expect(meta.get('secretariat_id')).toBe('2')
  })

  it('[effectiveSecretariatId] utilise le secrétariat COURANT dans l’onglet Point Journalier', async () => {
    // Régression visée : un useCallback omet effectiveSecretariatId dans ses
    // dépendances ; on vérifie qu'aucune requête n'utilise un secrétariat périmé.
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Yopougon')
    fireEvent.click(screen.getByRole('button', { name: 'Point Journalier' }))

    await waitFor(() => expect(callsTo('/statistiques/point-journalier/').length).toBeGreaterThan(0))
    const pj = callsTo('/statistiques/point-journalier/')
    expect(pj.at(-1).get('secretariat_id')).toBe('3')
    // Toutes les requêtes émises après le choix portent bien l'id courant.
    for (const q of pj) expect(q.get('secretariat_id')).toBe('3')

    // Repasser à « Tous » retire le paramètre et refait une requête.
    await resetGlobalSecretariat()
    await waitFor(() => {
      const dernier = callsTo('/statistiques/point-journalier/').at(-1)
      expect(dernier.get('secretariat_id')).toBe(null)
    })
  })

  it('[effectiveSecretariatId] porte le secrétariat courant dans l’onglet Rapports & Bilans', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Marcory')
    fireEvent.click(screen.getByRole('button', { name: 'Rapports & Bilans' }))

    await waitFor(() => expect(callsTo('/statistiques/bilans/').length).toBeGreaterThan(0))
    expect(callsTo('/statistiques/bilans/').at(-1).get('secretariat_id')).toBe('2')
  })

  it('[effectiveSecretariatId] porte le secrétariat courant dans l’onglet Alertes (seuils)', async () => {
    mountStats(adminMe())
    await screen.findByRole('option', { name: 'INJS Marcory' })

    await selectGlobalSecretariat('INJS Yopougon')
    fireEvent.click(screen.getByRole('button', { name: 'Alertes' }))

    await waitFor(() => expect(callsTo('/statistiques/alertes/seuils/').length).toBeGreaterThan(0))
    expect(callsTo('/statistiques/alertes/seuils/').at(-1).get('secretariat_id')).toBe('3')
  })

  it('verrouille TOUTES les requêtes sur le secrétariat du compte Chef Secrétariat', async () => {
    const chef = makeUser('CHEF_SECRETARIAT', {
      username: 'chefsec',
      secretariat: 77,
      secretariat_nom: 'Secrétariat Pédagogique',
    })
    mountStats(chef)

    // Onglet par défaut = Point Journalier ; dès la PREMIÈRE requête l'id
    // verrouillé est transmis (pas de fuite de données globales).
    await waitFor(() => expect(callsTo('/statistiques/point-journalier/').length).toBeGreaterThan(0))
    for (const q of callsTo('/statistiques/point-journalier/')) {
      expect(q.get('secretariat_id')).toBe('77')
    }

    // Le chargement d'onglet et les méta-listes sont aussi verrouillés.
    await waitFor(() => {
      const dataCalls = callsTo('/statistiques/').filter((q) => !isMetaCall(q))
      expect(dataCalls.length).toBeGreaterThan(0)
      for (const q of dataCalls) expect(q.get('secretariat_id')).toBe('77')
    })
    const meta = await waitFor(() => {
      const m = callsTo('/statistiques/').filter(isMetaCall)
      if (!m.length) throw new Error('pas encore de méta')
      return m.at(-1)
    })
    expect(meta.get('secretariat_id')).toBe('77')

    // Le sélecteur global est absent et le badge de périmètre est affiché.
    expect(screen.queryByRole('option', { name: 'Tous les secrétariats' })).not.toBeInTheDocument()
    expect(screen.getByText(/Secrétariat Pédagogique/)).toBeInTheDocument()

    // Onglets autorisés : Point Journalier et Rapports ; les autres sont masqués.
    expect(screen.getByRole('button', { name: 'Point Journalier' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Rapports & Bilans' }))
    await waitFor(() => expect(callsTo('/statistiques/bilans/').length).toBeGreaterThan(0))
    expect(callsTo('/statistiques/bilans/').at(-1).get('secretariat_id')).toBe('77')

    expect(screen.queryByRole('button', { name: /vue d'ensemble/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Pédagogique' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Alertes' })).not.toBeInTheDocument()
  })
})
