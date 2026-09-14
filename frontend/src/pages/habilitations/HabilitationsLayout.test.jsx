import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import { apiController } from '@/test/utils/mockApi'
import { AuthProvider } from '@/context/AuthContext'
import CapabilitiesSync from '@/components/auth/CapabilitiesSync'
import { ToastProvider } from '@/context/ToastContext'
import { makeUser } from '@/test/utils/factories'
import HabilitationsLayout from './HabilitationsLayout'

function monter(capacites) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  window.localStorage.setItem('access_token', 'jeton-test')
  apiController.setMe(makeUser('ADMIN'))
  apiController.setRoute('/auth/capabilities/', { capacites })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/administration/comptes']}>
        <AuthProvider>
          <CapabilitiesSync />
          <ToastProvider>
            <Routes>
              <Route path="/administration/comptes" element={<HabilitationsLayout />}>
                <Route index element={<div data-testid="enfant-liste">liste</div>} />
              </Route>
            </Routes>
          </ToastProvider>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('HabilitationsLayout — dérivation des capacités (C2 §3)', () => {
  beforeEach(() => {
    cleanup()
    apiController.reset()
    window.localStorage.clear()
  })

  it('affiche un message d\'accès refusé explicite sans la capacité habilitations_admin.gerer', async () => {
    monter({}) // capacités chargées mais sans la clé
    expect(await screen.findByTestId('hab-403')).toBeInTheDocument()
    expect(screen.queryByTestId('enfant-liste')).not.toBeInTheDocument()
    expect(screen.getByText(/CURP_UI_ADMIN/)).toBeInTheDocument()
  })

  it('affiche la console et le bandeau de traçabilité avec la capacité', async () => {
    monter({ habilitations_admin: ['gerer'] })
    expect(await screen.findByTestId('enfant-liste')).toBeInTheDocument()
    expect(screen.getByText(/Toute action sur les habilitations est tracée/)).toBeInTheDocument()
    expect(screen.getByText('Journal')).toBeInTheDocument()
  })
})
