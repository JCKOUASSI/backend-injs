/**
 * Tests de l'espace étudiant MonEspace — ciblés sur la robustesse du
 * chargement initial (régression §10.10, LOT 13).
 *
 * Cet écran lance sa requête de fiche directement dans un `useEffect` dont la
 * dépendance est l'objet `toast` du contexte. Avant la stabilisation de la
 * valeur du ToastContext.Provider, un échec de chargement (toast d'erreur)
 * faisait re-rendre le provider, changeait la référence de `toast` et relançait
 * l'effet en boucle. On vérifie ici qu'il n'y a qu'une seule requête et un seul
 * toast, et que l'écran se contente d'afficher la fiche par défaut.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, act } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { flushPromises } from '@/test/utils/async'
import MonEspace from '@/pages/scolarite/MonEspace'

const settle = async (n = 6) => {
  await act(async () => { await flushPromises(n) })
}
const ficheCalls = () =>
  apiMock.get.mock.calls.filter(([p]) => p === '/scan/me/fiche/')

beforeEach(() => {
  apiController.reset()
  window.localStorage.clear()
})

describe('pages/scolarite/MonEspace — chargement de la fiche', () => {
  it('affiche la fiche quand le service répond', async () => {
    apiController.setRoute('/scan/me/fiche/', () => ({
      profil: { prenom: 'Awa', nom: 'Koné', numero: 'MAT-001' },
      stats: { nb_modules_inscrits: 8, taux_presence: 92 },
    }))
    renderWithProviders(<MonEspace />, { routePattern: '*', initialEntries: ['/mon-espace'] })

    expect(await screen.findByText(/Awa Koné/)).toBeInTheDocument()
    expect(screen.getByText(/matricule MAT-001/)).toBeInTheDocument()
    expect(screen.getByText(/8 module\(s\) inscrit\(s\)/)).toBeInTheDocument()
    expect(ficheCalls()).toHaveLength(1)
  })

  it('ne relance pas la requête quand la fiche est indisponible (régression §10.10)', async () => {
    // Deux échecs programmés puis un succès : un écran sain ne doit consommer
    // que le premier appel (l'échec), sans mécanisme de réessai.
    let n = 0
    apiController.setRoute('/scan/me/fiche/', () => {
      n += 1
      if (n <= 2) {
        // eslint-disable-next-line no-throw-literal
        throw { response: { status: 500 } }
      }
      return { profil: { prenom: 'Awa', nom: 'Koné' } }
    })

    renderWithProviders(<MonEspace />, { routePattern: '*', initialEntries: ['/mon-espace'] })

    expect(await screen.findByText('Fiche personnelle indisponible.')).toBeInTheDocument()
    await settle()
    // Un seul appel et un seul toast : pas de boucle de rechargement.
    expect(ficheCalls()).toHaveLength(1)
    expect(screen.getAllByText('Fiche personnelle indisponible.')).toHaveLength(1)
    // L'écran se contente de la fiche par défaut (prénom/nom vides), sans crasher.
    expect(screen.getByRole('heading', { name: /mon espace étudiant/i })).toBeInTheDocument()
  })
})
