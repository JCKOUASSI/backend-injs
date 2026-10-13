import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const showToast = vi.fn()
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ showToast }) }))
vi.mock('@/services/habilitations', () => ({
  listerComptes: vi.fn(async () => ({ results: [] })),
  listerRolesCurp: vi.fn(async () => []),
  listerDelegations: vi.fn(),
  creerDelegation: vi.fn(),
  terminerDelegation: vi.fn(),
  activerDelegation: vi.fn(),
  actionParDelegation: vi.fn(),
  messageErreur: (e) => e?.message || 'Erreur',
}))

import * as api from '@/services/habilitations'
import Delegations from './Delegations'

const delegationSensible = (extra = {}) => ({
  id: 7, delegant: 'chef', delegataire: 'remplacant', roles: ['RESPONSABLE_PEDAGOGIQUE'],
  date_fin: '2026-12-31', statut: 'PROPOSEE', active: false, sensible: true,
  premiere_validation_par: null, premiere_validation_le: null, ...extra,
})

describe('Délégations — double approbation (affichage)', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('signale une délégation sensible en attente de double validation', async () => {
    api.listerDelegations.mockResolvedValue({ results: [delegationSensible()] })
    render(<Delegations />)
    expect(await screen.findByText(/double validation requise/i)).toBeInTheDocument()
  })

  it('affiche la mention « 1re validation » après une première validation', async () => {
    api.listerDelegations.mockResolvedValue({
      results: [delegationSensible({ premiere_validation_par: 'admin1' })],
    })
    render(<Delegations />)
    expect(await screen.findByText(/1re validation : admin1/)).toBeInTheDocument()
  })

  it('informe que la seconde validation reste requise quand la délégation n’est pas activée', async () => {
    api.listerDelegations.mockResolvedValue({ results: [delegationSensible()] })
    api.activerDelegation.mockResolvedValue(delegationSensible({ premiere_validation_par: 'admin1' }))
    render(<Delegations />)
    fireEvent.click(await screen.findByTestId('activer-7'))
    fireEvent.change(screen.getByTestId('motif-input'), { target: { value: 'Contrôle effectué' } })
    fireEvent.click(screen.getByTestId('motif-confirmation'))
    await waitFor(() => expect(api.activerDelegation).toHaveBeenCalled())
    await waitFor(() => expect(showToast).toHaveBeenCalledWith(
      expect.stringMatching(/seconde validation/i), 'success'))
  })
})
