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
import { LIST_STORAGE_KEYS } from '@/utils/listFilters'
import Users from '@/pages/Users'

const PAGE_SIZE = 50
const LABELS = {
  ADMIN: 'Administrateur', DIRECTION: 'Direction', CHEF_CPFAE_ADMIN: 'Chef INJS Admin',
  CPFAE_ADMIN: 'INJS Admin', CHEF_SECRETARIAT: 'Chef Secrétariat', SECRETARIAT: 'Secrétariat',
  FINANCE: 'Finance', ARCHIVE: 'Archiviste', ENCADRANT: 'Encadrant', SUPERVISEUR: 'Superviseur',
  FORMATEUR: 'Formateur', AUDITEUR: 'Étudiant',
}

/* Jeu de données simulé, tel que renverrait le backend DRF (50/page). */
const mk = (id, role, { first, last, username, matricule }) => ({
  id, role, first_name: first, last_name: last, username,
  matricule: matricule || null, email: `${username}@injs.test`,
  telephone: '0700000000', is_active: true, secretariat_nom: null,
})

const staff = [
  ...Array.from({ length: 52 }, (_, i) =>
    mk(1000 + i, 'ENCADRANT', {
      first: `Encadrant ${i + 1}`, last: 'Kouassi', username: `enc${i + 1}`, matricule: `E${1000 + i}`,
    })),
  mk(2000, 'FINANCE', { first: 'Régis', last: 'Trésor', username: 'finance1', matricule: 'F2000' }),
  mk(2001, 'FINANCE', { first: 'Awa', last: 'Budget', username: 'finance2', matricule: 'F2001' }),
  mk(2002, 'FINANCE', { first: 'Karim', last: 'Solde', username: 'finance3', matricule: 'F2002' }),
]
const auditeurs = Array.from({ length: 5 }, (_, i) =>
  mk(3000 + i, 'AUDITEUR', { first: `Étudiant ${i + 1}`, last: 'Lmd', username: `aud${i + 1}`, matricule: `A${3000 + i}` }))
const formateurs = Array.from({ length: 4 }, (_, i) =>
  mk(4000 + i, 'FORMATEUR', { first: `Formateur ${i + 1}`, last: 'Peda', username: `form${i + 1}`, matricule: `FB${4000 + i}` }))

/** Endpoint paginé : reproduit le filtrage serveur selon la query string. */
const usersHandler = (path) => {
  const q = new URL(path, 'http://testserver').searchParams
  const page = Number(q.get('page') || 1)
  const search = (q.get('search') || '').toLowerCase()
  const role = q.get('role')

  let rows
  if (role === 'AUDITEUR') rows = auditeurs
  else if (role === 'FORMATEUR') rows = formateurs
  else {
    rows = staff // l'onglet personnel exclut déjà AUDITEUR/FORMATEUR (exclude_role)
    if (role) rows = rows.filter((u) => u.role === role)
  }
  if (search) {
    rows = rows.filter((u) =>
      [u.first_name, u.last_name, u.username, u.matricule, u.email]
        .filter(Boolean).some((v) => String(v).toLowerCase().includes(search)),
    )
  }

  const count = rows.length
  const start = (page - 1) * PAGE_SIZE
  const results = rows.slice(start, start + PAGE_SIZE)
  return { count, total_pages: Math.max(1, Math.ceil(count / PAGE_SIZE)), results }
}

const adminMe = () =>
  makeUser('ADMIN', {
    username: 'admin',
    role_context: {
      labels: LABELS,
      badge_account_roles: ['AUDITEUR', 'FORMATEUR'],
      can_mutate_users: true,
      manageable_roles: [
        'DIRECTION', 'CHEF_CPFAE_ADMIN', 'CPFAE_ADMIN', 'CHEF_SECRETARIAT', 'SECRETARIAT',
        'FINANCE', 'ARCHIVE', 'ENCADRANT', 'SUPERVISEUR', 'FORMATEUR', 'AUDITEUR',
      ],
      staff_filter_roles: ['FINANCE', 'ENCADRANT'],
    },
  })

const viewerMe = () => makeUser('SECRETARIAT', { username: 'sec', role_context: {} })

const mountUsers = (me = adminMe(), initialEntry = '/users') => {
  apiController.setMe(me)
  return renderWithProviders(<Users />, {
    authUser: me,
    initialEntries: [initialEntry],
    routePattern: '/users',
  })
}

const usersParams = () =>
  apiMock.get.mock.calls
    .filter(([p]) => p.startsWith('/auth/users/'))
    .map(([p]) => new URL(p, 'http://testserver').searchParams)
const lastUsersParams = () => usersParams().at(-1)
const waitForTable = () => waitFor(() => expect(screen.getByText(/sur \d+/)).toBeInTheDocument())

// Les libellés des modales ne sont pas reliés par htmlFor : on récupère le
// champ (input/select) appartenant au même .form-group que le <label>.
const getModal = (title) =>
  screen.getByRole('heading', { name: title }).closest('.modal-content')
const modalField = (modal, labelRegex) => {
  const label = within(modal).getByText(
    (_content, el) => el.tagName === 'LABEL' && labelRegex.test(el.textContent),
  )
  return label.closest('.form-group').querySelector('input, select, textarea')
}

describe('pages/Users.jsx — liste serveur (recherche, filtres, onglets, pagination)', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
    window.sessionStorage.clear()
    apiController.setRoute(/^\/auth\/users\//, usersHandler)
  })

  it('charge la première page du personnel : plage, onglets, titre et requête initiale', async () => {
    mountUsers()
    await waitForTable()

    expect(screen.getByText('Liste des utilisateurs')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /utilisateurs/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /étudiants/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /enseignants/i })).toBeInTheDocument()

    // Première page : 50 lignes sur 55 personnel.
    expect(screen.getByText(/1.50 sur 55/)).toBeInTheDocument()
    expect(screen.getByText('50 résultat(s)')).toBeInTheDocument()
    expect(screen.getByText('Encadrant 1 Kouassi')).toBeInTheDocument()
    expect(screen.getByText('Encadrant 50 Kouassi')).toBeInTheDocument()
    expect(screen.queryByText('Encadrant 51 Kouassi')).not.toBeInTheDocument()

    const params = lastUsersParams()
    expect(params.get('page')).toBe('1')
    expect(params.get('exclude_role')).toBe('AUDITEUR,FORMATEUR')
    expect(params.get('search')).toBe(null)
  })

  it('navigue à la page suivante puis revient, avec les bons paramètres serveur', async () => {
    mountUsers()
    await waitForTable()

    fireEvent.click(screen.getByRole('button', { name: 'Page 2' }))
    await waitFor(() => expect(lastUsersParams().get('page')).toBe('2'))

    expect(screen.getByText(/51.55 sur 55/)).toBeInTheDocument()
    expect(screen.getByText('5 résultat(s)')).toBeInTheDocument()
    expect(screen.getByText('Encadrant 51 Kouassi')).toBeInTheDocument()
    expect(screen.getByText('Karim Solde')).toBeInTheDocument()
    expect(screen.queryByText('Encadrant 1 Kouassi')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /page précédente/i }))
    await waitFor(() => expect(lastUsersParams().get('page')).toBe('1'))
    expect(screen.getByText('Encadrant 1 Kouassi')).toBeInTheDocument()
  })

  it('applique la recherche avec debounce et réémet la requête en page 1', async () => {
    mountUsers()
    await waitForTable()

    fireEvent.change(screen.getByPlaceholderText(/rechercher par nom/i), { target: { value: 'karim' } })
    expect(screen.getByDisplayValue('karim')).toBeInTheDocument()

    // La requête n'est réémise qu'après le debounce (400 ms).
    await waitFor(() => expect(lastUsersParams().get('search')).toBe('karim'))
    expect(lastUsersParams().get('page')).toBe('1')
    expect(screen.getByText('Karim Solde')).toBeInTheDocument()
    expect(screen.getByText('1 résultat(s)')).toBeInTheDocument()
    expect(screen.queryByText('Encadrant 1 Kouassi')).not.toBeInTheDocument()
  })

  it('filtre le personnel par rôle via le menu déroulant', async () => {
    mountUsers()
    await waitForTable()

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'FINANCE' } })
    await waitFor(() => expect(lastUsersParams().get('role')).toBe('FINANCE'))

    expect(screen.getByText('3 résultat(s)')).toBeInTheDocument()
    expect(screen.getByText('Régis Trésor')).toBeInTheDocument()
    expect(screen.getByText('Karim Solde')).toBeInTheDocument()
    expect(screen.queryByText('Encadrant 1 Kouassi')).not.toBeInTheDocument()
  })

  it("passe à l'onglet étudiants : reset page 1, role=AUDITEUR, pas d'exclude", async () => {
    mountUsers()
    await waitForTable()
    fireEvent.click(screen.getByRole('button', { name: 'Page 2' }))
    await waitFor(() => expect(lastUsersParams().get('page')).toBe('2'))

    fireEvent.click(screen.getByRole('tab', { name: /étudiants/i }))
    await waitFor(() => expect(lastUsersParams().get('role')).toBe('AUDITEUR'))

    expect(lastUsersParams().get('page')).toBe('1')
    expect(lastUsersParams().get('exclude_role')).toBe(null)
    expect(screen.getAllByText('Comptes étudiants').length).toBeGreaterThan(0)
    expect(screen.getByText('5 résultat(s)')).toBeInTheDocument()
    expect(screen.getByText('Étudiant 1 Lmd')).toBeInTheDocument()
    expect(screen.queryByText('Tous les rôles')).not.toBeInTheDocument()
  })

  it("passe à l'onglet enseignants et requête role=FORMATEUR", async () => {
    mountUsers()
    await waitForTable()

    fireEvent.click(screen.getByRole('tab', { name: /enseignants/i }))
    await waitFor(() => expect(lastUsersParams().get('role')).toBe('FORMATEUR'))

    expect(screen.getAllByText('Comptes enseignants').length).toBeGreaterThan(0)
    expect(screen.getByText('4 résultat(s)')).toBeInTheDocument()
    expect(screen.getByText('Formateur 1 Peda')).toBeInTheDocument()
  })

  it('persiste l’onglet courant dans l’URL / sessionStorage', async () => {
    mountUsers()
    await waitForTable()

    fireEvent.click(screen.getByRole('tab', { name: /étudiants/i }))
    await waitFor(() =>
      expect(window.sessionStorage.getItem(LIST_STORAGE_KEYS.users)).toContain('tab=auditeurs'),
    )
  })

  it('replie sur le seul onglet disponible quand l’URL demande un onglet interdit (§10.2 LOT 6)', async () => {
    // Utilisateur SANS gestion de comptes étudiants/enseignants mais avec un
    // filtre personnel : seule l'onglet « personnel » existe. Un lien obsolète
    // ?tab=auditeurs doit être ignoré (effet de repli sur les permissions).
    const personnelOnly = () =>
      makeUser('SECRETARIAT', {
        username: 'sec-limit',
        role_context: {
          labels: LABELS,
          badge_account_roles: ['AUDITEUR', 'FORMATEUR'],
          staff_filter_roles: ['FINANCE'],
        },
      })

    mountUsers(personnelOnly(), '/users?tab=auditeurs')
    await waitForTable()

    // La requête finale est bien celle du personnel : pas de `tab`, avec
    // l'exclusion des comptes à badge, et jamais role=AUDITEUR.
    expect(lastUsersParams().get('tab')).toBe(null)
    expect(lastUsersParams().get('role')).toBe(null)
    expect(lastUsersParams().get('exclude_role')).toContain('AUDITEUR')
    // La barre d'onglets (Comptes étudiants/enseignants) n'est pas rendue.
    expect(screen.queryByRole('tab', { name: /étudiants/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /enseignants/i })).not.toBeInTheDocument()
  })

  it('affiche un état vide quand aucun utilisateur ne correspond', async () => {
    mountUsers()
    await waitForTable()

    fireEvent.change(screen.getByPlaceholderText(/rechercher par nom/i), { target: { value: 'zzzz-introuvable' } })
    await waitFor(() => expect(lastUsersParams().get('search')).toBe('zzzz-introuvable'))

    expect(screen.getByText(/aucun utilisateur trouvé/i)).toBeInTheDocument()
    expect(screen.getByText('0 résultat(s)')).toBeInTheDocument()
  })

  it('affiche un message d’erreur formaté quand le chargement échoue', async () => {
    // Une route « qui lève » rejette la promesse du mock GET (async) : cela
    // simule une erreur HTTP sans toucher à l'implémentation du client.
    apiController.reset()
    const me = adminMe()
    apiController.setMe(me)
    apiController.setRoute(/^\/auth\/users\//, () => {
      throw Object.assign(new Error('boom'), { response: { data: { detail: 'Droits insuffisants' } } })
    })

    renderWithProviders(<Users />, { authUser: me, initialEntries: ['/users'], routePattern: '/users' })
    expect(await screen.findByText('Droits insuffisants')).toBeInTheDocument()
  })

  it('propose les actions de gestion à un gestionnaire (créer, modifier, supprimer)', async () => {
    mountUsers()
    await waitForTable()

    expect(screen.getByRole('button', { name: /nouvel utilisateur/i })).toBeInTheDocument()
    const row = screen.getByText('Encadrant 1 Kouassi').closest('tr')
    expect(within(row).getByTitle('Modifier')).toBeInTheDocument()
    expect(within(row).getByTitle('Supprimer')).toBeInTheDocument()
  })

  it('supprime un utilisateur après confirmation, notifie et recharge la liste', async () => {
    mountUsers()
    await waitForTable()

    const row = screen.getByText('Encadrant 1 Kouassi').closest('tr')
    fireEvent.click(within(row).getByTitle('Supprimer'))

    expect(await screen.findByText(/supprimer cet utilisateur/i)).toBeInTheDocument()
    const before = usersParams().length
    fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))

    await waitFor(() => expect(apiMock.delete).toHaveBeenCalledWith('/auth/users/1000/'))
    expect(await screen.findByText('Utilisateur supprimé')).toBeInTheDocument()
    await waitFor(() => expect(usersParams().length).toBeGreaterThan(before))
  })

  it('masque les contrôles de gestion pour un utilisateur sans permission', async () => {
    mountUsers(viewerMe())
    await waitForTable()

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /nouvel utilisateur/i })).not.toBeInTheDocument()
    expect(screen.queryByText('Tous les rôles')).not.toBeInTheDocument()
    const row = screen.getByText('Encadrant 1 Kouassi').closest('tr')
    expect(within(row).queryByTitle('Modifier')).not.toBeInTheDocument()
    expect(within(row).queryByTitle('Supprimer')).not.toBeInTheDocument()
  })

  it('crée un utilisateur personnel (POST) avec les champs requis et notifie', async () => {
    mountUsers()
    await waitForTable()

    fireEvent.click(screen.getByRole('button', { name: /nouvel utilisateur/i }))
    const modal = getModal('Nouvel utilisateur')

    fireEvent.change(modalField(modal, /nom d'utilisateur/i), { target: { value: 'newenc' } })
    fireEvent.change(modalField(modal, /^mot de passe/i), { target: { value: 'Secret-123' } })
    fireEvent.click(within(modal).getByRole('button', { name: 'Créer' }))

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        '/auth/users/',
        expect.objectContaining({ username: 'newenc', password: 'Secret-123', role: 'DIRECTION' }),
      ),
    )
    expect(await screen.findByText('Utilisateur créé')).toBeInTheDocument()
    // La modale se referme.
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Nouvel utilisateur' })).not.toBeInTheDocument())
  })

  it('affiche les erreurs de validation renvoyées par le serveur sans fermer la modale', async () => {
    mountUsers()
    await waitForTable()
    apiMock.post.mockRejectedValueOnce(
      Object.assign(new Error('bad'), { response: { data: { username: ['Ce nom d’utilisateur existe déjà.'] } } }),
    )

    fireEvent.click(screen.getByRole('button', { name: /nouvel utilisateur/i }))
    const modal = getModal('Nouvel utilisateur')
    fireEvent.change(modalField(modal, /nom d'utilisateur/i), { target: { value: 'doublon' } })
    fireEvent.change(modalField(modal, /^mot de passe/i), { target: { value: 'Secret-123' } })
    fireEvent.click(within(modal).getByRole('button', { name: 'Créer' }))

    expect(await within(modal).findByText(/ce nom d’utilisateur existe déjà/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Nouvel utilisateur' })).toBeInTheDocument()
    expect(screen.queryByText('Utilisateur créé')).not.toBeInTheDocument()
  })

  it('modifie un utilisateur (PATCH), notamment le statut, et notifie', async () => {
    mountUsers()
    await waitForTable()

    const row = screen.getByText('Encadrant 1 Kouassi').closest('tr')
    fireEvent.click(within(row).getByTitle('Modifier'))

    const modal = await screen.findByRole('heading', { name: /modifier — enc1/i }).then((h) => h.closest('.modal-content'))
    fireEvent.change(modalField(modal, /^statut/i), { target: { value: 'false' } })
    fireEvent.click(within(modal).getByRole('button', { name: 'Enregistrer' }))

    await waitFor(() =>
      expect(apiMock.patch).toHaveBeenCalledWith(
        '/auth/users/1000/',
        expect.objectContaining({ role: 'ENCADRANT', is_active: false, username: 'enc1' }),
      ),
    )
    // Mot de passe laissé vide → non transmis.
    const payload = apiMock.patch.mock.calls.at(-1)[1]
    expect(payload).not.toHaveProperty('password')
    expect(await screen.findByText('Utilisateur modifié')).toBeInTheDocument()
  })

  it("crée un compte étudiant depuis l'onglet dédié (libellé et rôle adaptés)", async () => {
    mountUsers()
    await waitForTable()

    fireEvent.click(screen.getByRole('tab', { name: /étudiants/i }))
    await waitFor(() => expect(lastUsersParams().get('role')).toBe('AUDITEUR'))

    fireEvent.click(screen.getByRole('button', { name: /nouveau compte étudiant/i }))
    const modal = getModal('Nouveau compte étudiant')
    fireEvent.change(modalField(modal, /nom d'utilisateur/i), { target: { value: 'newaud' } })
    fireEvent.change(modalField(modal, /^mot de passe/i), { target: { value: 'Secret-123' } })
    fireEvent.click(within(modal).getByRole('button', { name: 'Créer' }))

    await waitFor(() =>
      expect(apiMock.post).toHaveBeenCalledWith(
        '/auth/users/',
        expect.objectContaining({ username: 'newaud', role: 'AUDITEUR' }),
      ),
    )
    expect(await screen.findByText('Compte étudiant créé')).toBeInTheDocument()
  })
})
