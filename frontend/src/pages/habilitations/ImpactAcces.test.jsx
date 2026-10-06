/** Tests couche IMPACT (F4–F7) : vues d'impact, accès effectifs, dashboard,
 * badges de sensibilité. Aucun framework de test supplémentaire.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { AllProviders } from '@/test/utils/renderWithProviders'
import { makeUser } from '@/test/utils/factories'
import ImpactPermission from './ImpactPermission'
import ImpactRole from './ImpactRole'
import ImpactUtilisateur from './ImpactUtilisateur'
import AccesEffectifs from './AccesEffectifs'
import Dashboard from './Dashboard'
import SensibleBadge from './SensibleBadge'

function monter(element, chemin = '/administration/comptes') {
  const user = makeUser('ADMIN')
  apiController.setMe(user)
  apiController.setRoute('/auth/capabilities/', {
    capacites: { habilitations_admin: ['gerer'] },
  })
  return render(element, {
    wrapper: ({ children }) => (
      <AllProviders authUser={user} routePattern={chemin}
                    initialEntries={[chemin]}>{children}</AllProviders>
    ),
  })
}

const impactPerm = {
  type: 'permission', code: 'evaluations.note.modifier',
  module: 'evaluations', module_libelle: 'Évaluations et notes',
  ressource: 'note', action: 'modifier', niveau: 2,
  criticite: 'CRITIQUE', sensible: true,
  necessite_motif: true, necessite_double_validation: true,
  journalisee: true, portee_maximale: 'INJS_ENTIER',
  roles: [{ code: 'SCOLARITE', libelle: 'Scolarité', sensible: false,
            disponible: true, niveau_defaut: 'N3', comptes_titulaires: 2 }],
  total_roles: 1, total_comptes_roles: 2, total_comptes_derogation: 1,
  total_comptes: 3,
  comptes_roles: [{ id: 1, user_id: 11, username: 'scol1', nom: 'Diop',
                    prenoms: 'Awa', statut: 'ACTIF' }],
  comptes_derogation: [{ id: 2, user_id: 12, username: 'dir1', nom: 'Ba',
                         prenoms: 'Modou', statut: 'ACTIF' }],
}

const impactRole = {
  type: 'role', code: 'SCOLARITE', libelle: 'Scolarité',
  description: 'Coordonne les inscriptions.', domaine: 'ADMINISTRATION',
  niveau_defaut: 'N3', perimetre_defaut: 'SECRETARIAT', canal_impose: '',
  sensible: false, disponible: true, actif: true, cumulable: true,
  total_permissions: 2,
  permissions_par_module: [
    { module: 'scolarite', module_libelle: 'Scolarité',
      permissions: ['scolarite.annee.consulter', 'scolarite.annee.creer'] },
  ],
  modules_impactes: ['scolarite'],
  permissions_sensibles: [],
  total_titulaires: 1,
  titulaires: [{ id: 1, user_id: 11, username: 'scol1', nom: 'Diop',
                 prenoms: 'Awa', statut: 'ACTIF' }],
}

function impactUser_roles() {
  return [{
    code: 'SCOLARITE', libelle: 'Scolarité', sensible: false,
    niveau_effectif: 'N3',
    perimetres: [{ id: 3, type: 'SECRETARIAT', libelle: 'Secrétariat A',
                   object_id: 5 }],
    date_debut: '2026-09-01', date_fin: null,
    modules: [{ module: 'scolarite', module_libelle: 'Scolarité',
                permissions: ['scolarite.annee.consulter'] }],
    permissions: ['scolarite.annee.consulter'],
  }]
}

const impactUser = {
  type: 'utilisateur', user_id: 11, compte_id: 1, username: 'scol1',
  nom: 'Diop', prenoms: 'Awa', statut: 'ACTIF', motif_statut: '',
  canal: 'WEB', mfa_actif: true,
  roles: impactUser_roles(),
  total_roles: 1,
  permissions_directes: [],
  permissions_retraits: [{ code: 'scolarite.annee.creer',
                           motif: 'Consigne RSSI.' }],
  total_directes: 0, total_heritees: 1, total_effectives: 1,
  total_retraits: 1,
  modules_effectifs: [{ module: 'scolarite', module_libelle: 'Scolarité' }],
  actions_sensibles_effectives: [],
  delegations_recues: [],
  arbre: {
    roles: impactUser_roles(),
    derogations: [], retraits: ['scolarite.annee.creer'],
  },
  octrois_directs: [], retraits: ['scolarite.annee.creer'],
}

const dashboard = {
  comptes: { total: 10, par_statut: { ACTIF: 8, SUSPENDU: 2 },
             actifs: 8, non_actifs: 2 },
  roles: { total: 35, actifs: 34, sensibles: 11, disponibles: 33 },
  permissions: {
    total: 1155, actives: 1155, sensibles: 15, avec_motif: 19,
    par_module: [{ module: 'scolarite', total: 210 },
                 { module: 'evaluations', total: 90 }],
  },
  comptes_privileges: 4,
  derogations: { octrois: 3, retraits: 1 },
  delegations: { actives: 2, expirant_prochainement: 1 },
  provisionnement: { propositions_en_attente: 5 },
  dernieres_actions: [
    { numero: 42, horodatage: '2026-10-05T10:00:00',
      type: 'ROLE_ATTRIBUE', type_libelle: 'Attribution de rôle',
      acteur: 'admin5', objet_libelle: 'SCOLARITE' },
  ],
  date_reference: '2026-10-05',
}

beforeEach(() => {
  cleanup()
  apiController.reset()
  window.localStorage.clear()
})

describe('SensibleBadge — classification CURP uniquement', () => {
  it("n'affiche rien pour une valeur NORMALE", () => {
    render(<SensibleBadge type="permission" niveau="NORMALE" />)
    expect(screen.queryByTestId('sensible-badge-permission')).toBeNull()
  })

  it('signale SENSIBLE et CRITIQUE avec le bon libellé', () => {
    render(<>
      <SensibleBadge type="role" niveau={true} />
      <SensibleBadge type="permission" niveau="CRITIQUE" />
    </>)
    expect(screen.getByTestId('sensible-badge-role'))
      .toHaveTextContent('Sensible')
    expect(screen.getByTestId('sensible-badge-permission'))
      .toHaveTextContent('Critique')
  })
})

describe('ImpactPermission', () => {
  it('affiche rôles porteurs et comptes impactés', async () => {
    apiController.setRoute(/impact\/permission\/.+\/$/, impactPerm)
    monter(<ImpactPermission codeInitial="evaluations.note.modifier" />)
    expect(await screen.findByTestId('impact-permission-resultat'))
      .toBeInTheDocument()
    expect(screen.getByTestId('impact-permission-roles'))
      .toHaveTextContent('SCOLARITE')
    expect(screen.getByTestId('impact-permission-comptes'))
      .toHaveTextContent('scol1')
    expect(screen.getByTestId('impact-permission-comptes'))
      .toHaveTextContent('dir1')
  })

  it("affiche l'état vide quand aucun rôle ne porte la permission", async () => {
    apiController.setRoute(/impact\/permission\/.+\/$/, {
      ...impactPerm, roles: [], total_roles: 0, total_comptes: 0,
      total_comptes_roles: 0, total_comptes_derogation: 0,
      comptes_roles: [], comptes_derogation: [],
    })
    monter(<ImpactPermission codeInitial="diplomation.diplome.valider" />)
    expect(await screen.findByTestId('impact-permission-vide'))
      .toBeInTheDocument()
  })

  it("affiche l'erreur API (404 permission inconnue)", async () => {
    apiController.setRoute(/impact\/permission\/.+\/$/, () => {
      throw {
        response: {
          status: 404,
          data: { detail: 'Permission inconnue.',
                  code: 'PERMISSION_INCONNUE' },
        },
      }
    })
    monter(<ImpactPermission codeInitial="n.importe.quoi" />)
    expect(await screen.findByTestId('impact-permission-erreur'))
      .toBeInTheDocument()
  })
})

describe('ImpactRole', () => {
  it('affiche permissions groupées par module et titulaires', async () => {
    apiController.setRoute(/impact\/role\/.+\/$/, impactRole)
    monter(<ImpactRole codeInitial="SCOLARITE" />)
    expect(await screen.findByTestId('impact-role-resultat')).toBeInTheDocument()
    expect(screen.getByTestId('impact-role-permissions'))
      .toHaveTextContent('scolarite.annee.consulter')
    expect(screen.getByTestId('impact-role-comptes'))
      .toHaveTextContent('scol1')
  })

  it('signale les actes sensibles portés par le rôle', async () => {
    apiController.setRoute(/impact\/role\/.+\/$/, {
      ...impactRole,
      permissions_sensibles: ['diplomation.diplome.valider'],
    })
    monter(<ImpactRole codeInitial="RESPONSABLE_CONCOURS" />)
    expect(await screen.findByTestId('impact-role-sensibles'))
      .toHaveTextContent('diplomation.diplome.valider')
  })
})

describe('ImpactUtilisateur — attribué ≠ effectif', () => {
  it('distingue rôles attribués, retraits et accès effectifs', async () => {
    apiController.setRoute(/impact\/utilisateur\/\d+\/$/, impactUser)
    monter(<ImpactUtilisateur userIdInitial="11" />)
    expect(await screen.findByTestId('impact-utilisateur-identite'))
      .toBeInTheDocument()
    expect(screen.getByTestId('impact-utilisateur-effectives'))
      .toHaveTextContent('1')
    expect(screen.getByTestId('impact-utilisateur-retraits'))
      .toHaveTextContent('scolarite.annee.creer')
    expect(screen.getByTestId('impact-utilisateur-arbre'))
      .toHaveTextContent('scolarite.annee.consulter')
  })

  it("affiche l'arbre vide pour un compte sans rôle", async () => {
    apiController.setRoute(/impact\/utilisateur\/\d+\/$/, {
      ...impactUser, roles: [], total_roles: 0, total_effectives: 0,
      total_heritees: 0, total_retraits: 0,
      permissions_retraits: [], modules_effectifs: [],
      actions_sensibles_effectives: [],
      arbre: { roles: [], derogations: [], retraits: [] },
      retraits: [],
    })
    monter(<ImpactUtilisateur userIdInitial="11" />)
    expect(await screen.findByTestId('impact-utilisateur-arbre-vide'))
      .toBeInTheDocument()
  })

  it("affiche l'erreur 404 pour un compte inconnu", async () => {
    apiController.setRoute(/impact\/utilisateur\/\d+\/$/, () => {
      throw {
        response: {
          status: 404,
          data: { detail: 'Aucun compte CURP.',
                  code: 'COMPTE_INCONNU' },
        },
      }
    })
    monter(<ImpactUtilisateur userIdInitial="999999" />)
    expect(await screen.findByTestId('impact-utilisateur-erreur'))
      .toBeInTheDocument()
  })
})

describe('AccesEffectifs — arbre repliable', () => {
  it('rend les bascules rôle → module → permission', async () => {
    apiController.setRoute(/impact\/utilisateur\/\d+\/$/, impactUser)
    monter(<AccesEffectifs userIdInitial="11" />)
    expect(await screen.findByTestId('arbre-acces')).toBeInTheDocument()
    expect(screen.getByTestId('arbre-bascule-role-SCOLARITE')).toBeInTheDocument()
    expect(screen.getAllByText('scolarite.annee.consulter').length)
      .toBeGreaterThan(0)
  })
})

describe('Dashboard habilitations', () => {
  it('affiche les indicateurs dérivés du backend', async () => {
    apiController.setRoute(/dashboard\/$/, dashboard)
    monter(<Dashboard />)
    expect(await screen.findByTestId('dash-comptes')).toHaveTextContent('10')
    expect(screen.getByTestId('dash-roles-sensibles'))
      .toHaveTextContent('11')
    expect(screen.getByTestId('dash-permissions-sensibles'))
      .toHaveTextContent('15')
    expect(screen.getByTestId('dash-privileges')).toHaveTextContent('4')
    expect(screen.getByTestId('dash-journal'))
      .toHaveTextContent('Attribution de rôle')
  })

  it("affiche l'erreur API sans tuile", async () => {
    apiController.setRoute(/dashboard\/$/, () => {
      throw {
        response: { status: 403, data: { detail: 'Console indisponible.' } },
      }
    })
    monter(<Dashboard />)
    expect(await screen.findByTestId('dashboard-erreur'))
      .toHaveTextContent('Console indisponible.')
  })
})
