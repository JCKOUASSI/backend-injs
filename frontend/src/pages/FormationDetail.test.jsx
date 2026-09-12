/**
 * Tests de la fiche formation (niveau « formation », écran miroir de
 * ModuleDetail) — LOT 21, domaine présence/émargement.
 *
 * Ce premier lot couvre les fondations, par l'extérieur :
 * - chargement GET /formations/:id/detail/, en-tête, onglets et habilitations ;
 * - onglet Séances : regroupement par module, démarrage/fin (ConfirmModal),
 *   création inline, modification (PATCH), suppression (DELETE), erreurs ;
 * - onglet Étudiants : liste, ajout via le picker (exclusion des inscrits),
 *   retrait confirmé, lecture seule DIRECTION ;
 * - onglet Enseignants : chargement, ajout au niveau formation (picker sans
 *   module_id), retrait confirmé ;
 * - onglet Informations : assignation de l'encadrant superviseur.
 *
 * Restent pour le lot suivant : onglet Présences (dashboard, forçage de
 * pointage unitaire, jour passé), exports PDF/Excel, QR de séance,
 * archivage TripleConfirmModal depuis l'en-tête de groupe, import Excel des
 * séances (SECRETARIAT) et la pagination serveur des pickers.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, act, within, fireEvent } from '@testing-library/react'

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { flushPromises } from '@/test/utils/async'
import { makeUser } from '@/test/utils/factories'
import FormationDetail from '@/pages/FormationDetail'

const F = 10
const TODAY = new Date().toISOString().slice(0, 10)
const detailPath = `/formations/${F}/detail/`
const formateursPath = `/formations/${F}/formateurs/`

const PARTICIPANTS = [
  { id: 101, nom: 'Koné', prenom: 'Awa', matricule: 'MAT-001', email: 'awa@kone.ci', telephone: '0701010101', structure: 'INJS' },
  { id: 102, nom: 'Diop', prenom: 'Karim', matricule: 'MAT-002' },
]
const FORMATEURS = [{ id: 201, nom: 'Nguessan', prenom: 'Yao', numerobadge: 'F001', specialite: 'LSF' }]

const buildFormation = () => ({
  id: F,
  formation: 'LSF — Promotion 2026',
  statut: 'PLANIFIEE',
  site: 'Marcory', batiment: 'B', salle: 'B2',
  date_debut: '2026-09-01', date_fin: '2026-12-15',
  categorie: 'Continu', grade: 'L1', groupe: 'G1',
  superviseur: 301, superviseur_nom: 'Mariam Traoré',
  secretariat_nom: 'Secrétariat INJS Marcory',
  modules: [{ id: 77, intitule: 'LSF Niveau 1 — A1' }],
  formateurs: FORMATEURS,
  participants: PARTICIPANTS,
  sessions: [
    { id: 1, numero: 1, intitule: 'Séance du matin', module_id: 77, module_intitule: 'LSF Niveau 1 — A1', module_groupe: 'G1', date: TODAY, heure_debut: '08:00', heure_fin: '10:00', en_cours: true, terminee: false, nb_presences: 1, nb_attendus: 4 },
    { id: 2, numero: 2, intitule: 'Séance planifiée', module_id: 77, module_intitule: 'LSF Niveau 1 — A1', module_groupe: 'G1', date: TODAY, heure_debut: '10:00', heure_fin: '12:00', en_cours: false, terminee: false, nb_presences: 0, nb_attendus: 4 },
    { id: 3, numero: 1, intitule: 'Séance ancienne', module_id: 77, module_intitule: 'LSF Niveau 1 — A1', module_groupe: 'G1', date: '2026-08-01', heure_debut: '08:00', heure_fin: '10:00', en_cours: false, terminee: true, nb_presences: 4, nb_attendus: 4 },
  ],
})

const setupRoutes = () => {
  apiController.setRoute(detailPath, () => buildFormation())
  apiController.setRoute(formateursPath, () => FORMATEURS)
}

const mount = (role = 'ADMIN') => {
  const me = makeUser(role, { username: role.toLowerCase() })
  apiController.setMe(me)
  return renderWithProviders(<FormationDetail />, {
    authUser: me,
    routePattern: '/formations/:id',
    initialEntries: [`/formations/${F}`],
  })
}
const settle = async (n = 6) => { await act(async () => { await flushPromises(n) }) }
const posts = (pred) =>
  apiMock.post.mock.calls.filter(([p]) => pred(p)).map(([p, b]) => ({ path: p, body: b }))
const patches = () => apiMock.patch.mock.calls.map(([p, b]) => ({ path: p, body: b }))
const deletes = () => apiMock.delete.mock.calls.map(([p]) => p)
const modal = () => document.querySelector('.modal-content')
const sessionRow = (intitule) => screen.getByText(intitule).closest('tr')
const goTab = async (name) => {
  fireEvent.click(screen.getByRole('button', { name }))
  await settle()
}
// Les pickers passent par un setTimeout de 300 ms (debounce) : horloge réelle.
const waitReal = async (ms = 360) => { await act(async () => { await new Promise((r) => setTimeout(r, ms)) }) }
const clickConfirm = async () => {
  fireEvent.click(within(modal()).getByRole('button', { name: 'Confirmer' }))
  await settle(8)
}

beforeEach(() => {
  apiController.reset()
  window.localStorage.clear()
  setupRoutes()
})

describe('FormationDetail — chargement, en-tête et onglets', () => {
  it('affiche la formation, son statut, ses modules et les compteurs de résumé', async () => {
    mount()
    expect(await screen.findByText('LSF — Promotion 2026')).toBeInTheDocument()

    // En-tête : badge statut et nombre de modules.
    expect(screen.getAllByText('Planifié').length).toBeGreaterThan(0)
    expect(screen.getByText('1 module')).toBeInTheDocument()
    // Le module est un lien vers sa fiche détaillée.
    expect(screen.getByRole('link', { name: 'LSF Niveau 1 — A1' })).toHaveAttribute(
      'href',
      `/formations/${F}/modules/77`,
    )

    // Les quatre cartes de résumé portent bien une valeur numérique.
    for (const label of ['Séances', 'Étudiants', 'Terminées', 'Enseignants']) {
      expect(screen.getByText(label).parentElement).toHaveTextContent(/[0-9]/)
    }
    expect(screen.getByText('Mariam Traoré')).toBeInTheDocument()
  })

  it("affiche un message d'erreur et un retour si le chargement échoue", async () => {
    // La route par défaut de beforeEach est déjà enregistrée : on repart à zéro
    // (matchRoute renvoie la première correspondance, donc un reset est requis).
    apiController.reset()
    apiController.setRoute(detailPath, () => {
      // eslint-disable-next-line no-throw-literal
      throw { response: { status: 500 } }
    })
    mount()
    expect(await screen.findByText('Erreur lors du chargement de la formation')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retour/i }))
  })

  it("masque l'onglet Présences pour un rôle non habilité (SUPERVISEUR)", async () => {
    mount('SUPERVISEUR')
    expect(await screen.findByText('LSF — Promotion 2026')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Informations' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /présences/i })).not.toBeInTheDocument()
    // Les autres onglets restent accessibles.
    expect(screen.getByRole('button', { name: /séances \(3\)/i })).toBeInTheDocument()
  })
})

describe('FormationDetail — onglet Séances (cycle de vie)', () => {
  beforeEach(async () => {
    mount()
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/séances \(3\)/i)
  })

  it('regroupe les séances par module et affiche statuts et compteurs de présence', () => {
    // En-tête de groupe : lien module + nombre de séances.
    expect(screen.getAllByText('LSF Niveau 1 — A1').length).toBeGreaterThan(0)
    expect(screen.getByText('3 séances')).toBeInTheDocument()
    expect(sessionRow('Séance du matin')).toHaveTextContent('En cours')
    expect(sessionRow('Séance ancienne')).toHaveTextContent('Terminé')
    expect(sessionRow('Séance planifiée')).toHaveTextContent('Planifié')
    expect(sessionRow('Séance du matin')).toHaveTextContent('1')
  })

  it('démarre une séance planifiée après confirmation (POST start), notifie et recharge', async () => {
    fireEvent.click(within(sessionRow('Séance planifiée')).getByTitle('Démarrer'))
    expect(await screen.findByText(/démarrer la séance/i)).toBeInTheDocument()
    await clickConfirm()
    expect(posts((p) => p.endsWith('/sessions/2/start/'))).toEqual([
      { path: `/formations/${F}/sessions/2/start/`, body: undefined },
    ])
    expect(await screen.findByText('Séance démarrée')).toBeInTheDocument()
  })

  it("n'émet rien si la confirmation de démarrage est annulée", async () => {
    fireEvent.click(within(sessionRow('Séance planifiée')).getByTitle('Démarrer'))
    await screen.findByText(/démarrer la séance/i)
    fireEvent.click(within(modal()).getByRole('button', { name: 'Annuler' }))
    await settle()
    expect(posts((p) => p.includes('/start/'))).toHaveLength(0)
  })

  it('termine une séance en cours (POST stop)', async () => {
    fireEvent.click(within(sessionRow('Séance du matin')).getByTitle('Terminer'))
    expect(await screen.findByText(/terminer la séance/i)).toBeInTheDocument()
    await clickConfirm()
    expect(posts((p) => p.endsWith('/sessions/1/stop/'))).toHaveLength(1)
    expect(await screen.findByText('Séance terminée')).toBeInTheDocument()
  })

  it('supprime une séance planifiée après confirmation (DELETE), rien si annulé', async () => {
    const row = sessionRow('Séance planifiée')
    fireEvent.click(within(row).getByTitle('Supprimer'))
    expect(await screen.findByText('Supprimer cette séance ?')).toBeInTheDocument()
    // Annulation d'abord.
    fireEvent.click(within(modal()).getByRole('button', { name: 'Annuler' }))
    await settle()
    expect(deletes()).toHaveLength(0)
    // Puis confirmation.
    fireEvent.click(within(sessionRow('Séance planifiée')).getByTitle('Supprimer'))
    await screen.findByText('Supprimer cette séance ?')
    await clickConfirm()
    expect(deletes()).toContain(`/formations/${F}/sessions/2/delete/`)
    expect(await screen.findByText('Séance supprimée')).toBeInTheDocument()
  })

  it('crée une séance via le formulaire inline (POST new, numero et intitulé calculés)', async () => {
    fireEvent.click(screen.getByRole('button', { name: /ajouter une séance/i }))
    const form = screen.getByRole('button', { name: 'Créer' }).closest('form')
    fireEvent.change(form.querySelector('input[type="date"]'), { target: { value: '2026-09-20' } })
    const times = form.querySelectorAll('input[type="time"]')
    fireEvent.change(times[0], { target: { value: '14:00' } })
    fireEvent.change(times[1], { target: { value: '16:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Créer' }))
    await settle(8)

    expect(posts((p) => p.endsWith('/sessions/new/'))).toEqual([
      {
        path: `/formations/${F}/sessions/new/`,
        body: expect.objectContaining({
          date_journee: '2026-09-20',
          heure_debut_prevue: '14:00',
          heure_fin_prevue: '16:00',
          numero: 4, // sessions.length + 1
          intitule: 'Séance 4',
        }),
      },
    ])
    expect(await screen.findByText('Séance créée')).toBeInTheDocument()
  })

  it('modifie une séance (PATCH update) avec les champs saisis', async () => {
    fireEvent.click(within(sessionRow('Séance planifiée')).getByTitle('Modifier'))
    const box = await screen.findByRole('heading', { name: /modifier la séance/i })
    const form = box.closest('.modal-content')
    // Le premier champ texte est le numéro (lecture seule), le second est l'intitulé.
    fireEvent.change(form.querySelectorAll('input[type="text"]')[1], { target: { value: 'Séance reportée' } })
    fireEvent.change(form.querySelector('input[type="date"]'), { target: { value: '2026-09-21' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Enregistrer' }))
    await settle(8)

    expect(patches()).toEqual([
      {
        path: `/formations/${F}/sessions/2/update/`,
        body: expect.objectContaining({ intitule: 'Séance reportée', date_journee: '2026-09-21' }),
      },
    ])
    expect(await screen.findByText('Séance modifiée')).toBeInTheDocument()
  })

  it('notifie le détail renvoyé si le démarrage échoue', async () => {
    apiController.setRoute(/\/sessions\/2\/start\//, () => {
      // eslint-disable-next-line no-throw-literal
      throw { response: { data: { detail: 'Conflit de salle détecté.' } } }
    })
    fireEvent.click(within(sessionRow('Séance planifiée')).getByTitle('Démarrer'))
    await screen.findByText(/démarrer la séance/i)
    await clickConfirm()
    expect(await screen.findByText('Conflit de salle détecté.')).toBeInTheDocument()
  })
})

describe('FormationDetail — habilitations', () => {
  it("pour un ENCADRANT : démarrage/fin autorisés, mais pas de création/suppression/modification", async () => {
    mount('ENCADRANT')
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/séances \(3\)/i)

    expect(screen.queryByRole('button', { name: /ajouter une séance/i })).not.toBeInTheDocument()
    const planned = sessionRow('Séance planifiée')
    expect(within(planned).getByTitle('Démarrer')).toBeInTheDocument()
    expect(within(planned).queryByTitle('Supprimer')).not.toBeInTheDocument()
    expect(within(planned).queryByTitle('Modifier')).not.toBeInTheDocument()
  })

  it("pour la DIRECTION : lecture seule (pas de séance, ni d'action de supervision)", async () => {
    mount('DIRECTION')
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/séances \(3\)/i)
    expect(screen.queryByRole('button', { name: /ajouter une séance/i })).not.toBeInTheDocument()
    expect(within(sessionRow('Séance planifiée')).queryByTitle('Démarrer')).not.toBeInTheDocument()
    expect(within(sessionRow('Séance du matin')).queryByTitle('Terminer')).not.toBeInTheDocument()
  })

  it("pour la DIRECTION : pas d'ajout ni de retrait d'étudiant (lecture seule)", async () => {
    mount('DIRECTION')
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/étudiants \(2\)/i)
    expect(screen.queryByRole('button', { name: /ajouter un étudiant/i })).not.toBeInTheDocument()
    expect(within(screen.getByText('Koné').closest('tr')).queryByTitle('Retirer')).not.toBeInTheDocument()
    // La liste reste consultable.
    expect(screen.getByText('Étudiants inscrits (2)')).toBeInTheDocument()
  })

  it("n'offre aucune action de vie sur une séance terminée (hors QR et exports)", async () => {
    mount()
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/séances \(3\)/i)
    const old = sessionRow('Séance ancienne')
    expect(within(old).queryByTitle('Démarrer')).not.toBeInTheDocument()
    expect(within(old).queryByTitle('Terminer')).not.toBeInTheDocument()
    expect(within(old).queryByTitle('Modifier')).not.toBeInTheDocument()
    expect(within(old).queryByTitle('Supprimer')).not.toBeInTheDocument()
    expect(within(old).queryByTitle('QR Code')).not.toBeInTheDocument()
    // Le badge « Terminé » est rendu dans la cellule statut.
    expect(within(old).getAllByText('Terminé').length).toBeGreaterThan(0)
  })
})

describe('FormationDetail — onglet Étudiants', () => {
  beforeEach(async () => {
    mount()
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/étudiants \(2\)/i)
  })

  it('liste les inscrits avec leurs coordonnées', () => {
    expect(screen.getByText('Étudiants inscrits (2)')).toBeInTheDocument()
    expect(screen.getByText('Koné')).toBeInTheDocument()
    expect(screen.getByText('awa@kone.ci')).toBeInTheDocument()
    expect(screen.getByText('MAT-001')).toBeInTheDocument()
  })

  it('ajoute un étudiant via le picker (POST add), en excluant les déjà inscrits', async () => {
    apiController.setRoute('/formations/participants/list/', () => [
      { id: 101, nom: 'Koné', prenom: 'Awa' }, // déjà inscrit → filtré
      { id: 103, nom: 'Bamba', prenom: 'Issa', numero_matricule: 'MAT-003' },
    ])
    fireEvent.click(screen.getByRole('button', { name: /ajouter un étudiant/i }))
    await waitReal()
    const box = modal()
    expect(within(box).queryByText('Awa')).not.toBeInTheDocument()
    expect(within(box).getByText('Bamba')).toBeInTheDocument()

    fireEvent.click(within(within(box).getByText('Bamba').closest('tr')).getByRole('button'))
    await settle(8)
    expect(posts((p) => p.includes('/participants/add/'))).toEqual([
      { path: `/formations/${F}/participants/add/`, body: { participant_id: 103 } },
    ])
    expect(await screen.findByText('Étudiant ajouté')).toBeInTheDocument()
  })

  it("notifie le détail backend si l'ajout échoue", async () => {
    apiController.setRoute('/formations/participants/list/', () => [
      { id: 105, nom: 'Yao', prenom: 'Kouam' },
    ])
    apiController.setRoute(/\/participants\/add\//, () => {
      // eslint-disable-next-line no-throw-literal
      throw { response: { data: { detail: 'Cet étudiant est déjà inscrit à cette formation.' } } }
    })
    fireEvent.click(screen.getByRole('button', { name: /ajouter un étudiant/i }))
    await waitReal()
    const box = modal()
    fireEvent.click(within(within(box).getByText('Yao').closest('tr')).getByRole('button'))
    expect(await screen.findByText('Cet étudiant est déjà inscrit à cette formation.')).toBeInTheDocument()
  })

  it('retire un étudiant après confirmation (DELETE)', async () => {
    fireEvent.click(within(screen.getByText('Koné').closest('tr')).getByTitle('Retirer'))
    expect(await screen.findByText('Retirer cet étudiant de la formation ?')).toBeInTheDocument()
    await clickConfirm()
    expect(deletes()).toContain(`/formations/${F}/participants/101/remove/`)
    expect(await screen.findByText('Étudiant retiré')).toBeInTheDocument()
  })
})

describe('FormationDetail — onglet Enseignants', () => {
  it('charge les enseignants assignés à l’activation de l’onglet (GET formateurs)', async () => {
    mount()
    await screen.findByText('LSF — Promotion 2026')
    expect(apiMock.get.mock.calls.some(([p]) => p === formateursPath)).toBe(false)
    await goTab(/enseignants/i)
    expect(apiMock.get.mock.calls.some(([p]) => p === formateursPath)).toBe(true)
    expect(screen.getByText('Enseignants assignés (1)')).toBeInTheDocument()
    expect(screen.getByText('Nguessan')).toBeInTheDocument()
    expect(screen.getByText('F001')).toBeInTheDocument()
  })

  it('ajoute un enseignant via le picker (POST add au niveau formation, sans module_id)', async () => {
    apiController.setRoute('/formations/formateurs/list/', (path) => {
      expect(path).not.toContain('module_id=') // périmètre formation, pas module
      return [
        { id: 201, nom: 'Nguessan', prenom: 'Yao' }, // déjà assigné → filtré
        { id: 202, nom: 'Koffi', prenom: 'Ado', specialite: 'LSF' },
      ]
    })
    mount()
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/enseignants/i)

    fireEvent.click(screen.getByRole('button', { name: /ajouter un enseignant/i }))
    await waitReal()
    const box = modal()
    expect(within(box).queryByText(/Nguessan Yao/)).not.toBeInTheDocument()
    expect(within(box).getByText(/Koffi Ado/)).toBeInTheDocument()

    fireEvent.click(within(within(box).getByText(/Koffi Ado/).closest('tr')).getByRole('button'))
    await settle(8)
    expect(posts((p) => p.includes('/formateurs/add/'))).toEqual([
      { path: `/formations/${F}/formateurs/add/`, body: { formateur_id: 202 } },
    ])
    expect(await screen.findByText('Enseignant ajouté')).toBeInTheDocument()
  })

  it('retire un enseignant après confirmation (DELETE)', async () => {
    mount()
    await screen.findByText('LSF — Promotion 2026')
    await goTab(/enseignants/i)
    fireEvent.click(within(screen.getByText('Nguessan').closest('tr')).getByTitle('Retirer'))
    expect(await screen.findByText('Retirer cet enseignant de la formation ?')).toBeInTheDocument()
    await clickConfirm()
    expect(deletes()).toContain(`/formations/${F}/formateurs/201/remove/`)
    expect(await screen.findByText('Enseignant retiré')).toBeInTheDocument()
  })
})

describe('FormationDetail — onglet Informations (encadrant)', () => {
  it('assigne un encadrant superviseur (GET users ENCADRANT puis POST assign-superviseur)', async () => {
    apiController.setRoute('/auth/users/', () => [
      { id: 302, first_name: 'Issa', last_name: 'Bamba', username: 'ibamba', matricule: 'ENC-2' },
    ])
    mount()
    await screen.findByText('LSF — Promotion 2026')
    // Le petit crayon près du nom de l'encadrant ouvre la modale.
    const encadrantRow = screen.getByText('Encadrant').closest('div')
    fireEvent.click(within(encadrantRow).getByRole('button'))
    await waitReal()
    const box = await screen.findByRole('heading', { name: 'Assigner un encadrant' })
    const form = box.closest('.modal-content')
    expect(within(form).getByText('ibamba')).toBeInTheDocument()

    fireEvent.click(within(form).getByText('ibamba').closest('tr'))
    fireEvent.click(within(form).getByRole('button', { name: 'Assigner' }))
    await settle(8)

    expect(posts((p) => p.includes('/assign-superviseur/'))).toEqual([
      { path: `/formations/${F}/assign-superviseur/`, body: { superviseur_id: '302' } },
    ])
    expect(document.querySelector('.modal-overlay')).toBeNull()
  })

  it("refuse l'enregistrement sans sélection (message dans la modale)", async () => {
    // Variante sans encadrant assigné (selectedSup initial vide).
    apiController.reset()
    apiController.setRoute(detailPath, () => ({ ...buildFormation(), superviseur: null, superviseur_nom: null }))
    apiController.setRoute(formateursPath, () => FORMATEURS)
    apiController.setRoute('/auth/users/', () => [
      { id: 302, first_name: 'Issa', last_name: 'Bamba', username: 'ibamba' },
    ])
    const me = makeUser('ADMIN', { username: 'admin' })
    apiController.setMe(me)
    renderWithProviders(<FormationDetail />, {
      authUser: me,
      routePattern: '/formations/:id',
      initialEntries: [`/formations/${F}`],
    })
    await screen.findByText('LSF — Promotion 2026')
    const encadrantRow = screen.getByText('Encadrant').closest('div')
    fireEvent.click(within(encadrantRow).getByRole('button'))
    await waitReal()
    const box = await screen.findByRole('heading', { name: 'Assigner un encadrant' })
    const form = box.closest('.modal-content')
    fireEvent.click(within(form).getByRole('button', { name: 'Assigner' }))
    await settle()
    expect(within(form).getByText('Veuillez sélectionner un encadrant')).toBeInTheDocument()
    expect(posts((p) => p.includes('/assign-superviseur/'))).toHaveLength(0)
  })

  it("la DIRECTION ne voit pas le crayon d'assignation", async () => {
    mount('DIRECTION')
    await screen.findByText('LSF — Promotion 2026')
    const encadrantRow = screen.getByText('Encadrant').closest('div')
    expect(within(encadrantRow).queryByRole('button')).not.toBeInTheDocument()
  })
})
