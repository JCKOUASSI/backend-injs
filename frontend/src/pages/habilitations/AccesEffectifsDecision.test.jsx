/** Carte « Décision backend » de l'écran Accès effectifs.
 * La décision vient de la route acces-effectifs/ (moteur d'autorisation) ;
 * l'arbre existant reste inchangé et ne dépend pas de cette carte.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import { apiController } from '@/test/utils/mockApi'
import { AllProviders } from '@/test/utils/renderWithProviders'
import { makeUser } from '@/test/utils/factories'
import AccesEffectifs from './AccesEffectifs'

const CHEMIN = '/administration/comptes/acces-effectifs'

function monter() {
  const user = makeUser('ADMIN')
  apiController.setMe(user)
  apiController.setRoute('/auth/capabilities/', {
    capacites: { habilitations_admin: ['gerer'] },
  })
  return render(<AccesEffectifs userIdInitial="140" />, {
    wrapper: ({ children }) => (
      <AllProviders authUser={user} routePattern={CHEMIN} initialEntries={[CHEMIN]}>
        {children}
      </AllProviders>
    ),
  })
}

const impact = {
  type: 'utilisateur', user_id: 140, compte_id: 14, username: 'curp.agent',
  statut: 'SUSPENDU', total_effectives: 0, modules_effectifs: [],
  actions_sensibles_effectives: [], delegations_recues: [],
  arbre: { roles: [], derogations: [], retraits: [] },
}

const decision = {
  compte_id: 14, username: 'curp.agent', statut_compte: 'SUSPENDU',
  synthese: { candidates: 2, autorisees: 0, refusees: 2 },
  roles_actifs: [],
  roles_hors_periode: [{ code: 'SCOLARITE', libelle: 'Scolarité' }],
  permissions: [
    { code: 'scolarite.annee.consulter', autorise: false,
      motifs: ['COMPTE_SUSPENDU'] },
    { code: 'evaluations.note.modifier', autorise: false,
      motifs: ['PERMISSION_RETIREE', 'COMPTE_SUSPENDU'] },
  ],
  modules_accessibles: [],
}

beforeEach(() => {
  cleanup()
  apiController.reset()
  window.localStorage.clear()
})

describe('AccesEffectifs — décision backend', () => {
  it('affiche la décision du moteur avec motifs lisibles', async () => {
    apiController.setRoute(/impact\/utilisateur\/140\//, impact)
    apiController.setRoute(/comptes\/14\/acces-effectifs\//, decision)
    monter()
    expect(await screen.findByTestId('acces-decision-backend')).toBeInTheDocument()
    expect(screen.getByTestId('decision-perm-scolarite.annee.consulter'))
      .toHaveTextContent('refusée')
    expect(screen.getByTestId('decision-perm-evaluations.note.modifier'))
      .toHaveTextContent('permission retirée explicitement ; compte suspendu')
    expect(screen.getByTestId('acces-roles-hors-periode')).toHaveTextContent('SCOLARITE')
  })

  it("une erreur de la décision n'empêche pas l'arbre d'afficher", async () => {
    apiController.setRoute(/impact\/utilisateur\/140\//, impact)
    apiController.setRoute(/comptes\/14\/acces-effectifs\//, () => {
      throw { response: { status: 500 } }
    })
    monter()
    expect(await screen.findByTestId('arbre-acces')).toBeInTheDocument()
    expect(screen.queryByTestId('acces-decision-backend')).toBeNull()
  })
})
