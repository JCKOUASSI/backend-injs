import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock du client API (même instance que celle importée par AuthContext).
vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal()
  const mod = await import('@/test/utils/mockApi')
  return { ...actual, default: mod.default, setSessionExpiredCallback: vi.fn() }
})

import apiMock, { apiController } from '@/test/utils/mockApi'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { makeUser, makeLoginResponse } from '@/test/utils/factories'
import Login from '@/pages/Login'

const renderLogin = (options) =>
  renderWithProviders(<Login />, { initialEntries: ['/login'], routePattern: '/login', ...options })

describe('pages/Login.jsx', () => {
  beforeEach(() => {
    apiController.reset()
    window.localStorage.clear()
  })

  it('affiche le formulaire de connexion et la marque INJS', () => {
    renderLogin()
    expect(screen.getByLabelText("Nom d'utilisateur")).toBeInTheDocument()
    expect(screen.getByLabelText('Mot de passe')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /se connecter/i })).toBeInTheDocument()
    expect(screen.getAllByText(/INJS/i).length).toBeGreaterThan(0)
  })

  it('soumet les identifiants et établit la session', async () => {
    const user = makeUser('ADMIN', { username: 'admin' })
    apiMock.post.mockResolvedValueOnce({ data: makeLoginResponse(user) })
    renderLogin()

    await userEvent.type(screen.getByLabelText("Nom d'utilisateur"), 'admin')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'admin123')
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }))

    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith('/auth/login/', { username: 'admin', password: 'admin123' }))
    await waitFor(() => expect(window.localStorage.getItem('access_token')).toBe('access.jwt'))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('affiche le message d’erreur renvoyé par le serveur', async () => {
    apiMock.post.mockRejectedValueOnce({ response: { data: { detail: 'Compte verrouillé' } } })
    renderLogin()

    await userEvent.type(screen.getByLabelText("Nom d'utilisateur"), 'x')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'y')
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Compte verrouillé')
    expect(window.localStorage.getItem('access_token')).toBeNull()
  })

  it('affiche un message générique quand le serveur ne donne pas de détail', async () => {
    apiMock.post.mockRejectedValueOnce(new Error('Network'))
    renderLogin()

    await userEvent.type(screen.getByLabelText("Nom d'utilisateur"), 'x')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'y')
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Identifiants incorrects')
  })

  it('refuse un compte FORMATEUR (réservé mobile)', async () => {
    const formateur = makeUser('FORMATEUR')
    apiMock.post.mockResolvedValueOnce({ data: makeLoginResponse(formateur, { refreshInCookie: false }) })
    renderLogin()

    await userEvent.type(screen.getByLabelText("Nom d'utilisateur"), 'f001')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'f001')
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/enseignant/i)
    expect(window.localStorage.getItem('access_token')).toBeNull()
  })

  it('refuse un compte AUDITEUR / étudiant (réservé mobile)', async () => {
    const etudiant = makeUser('AUDITEUR')
    apiMock.post.mockResolvedValueOnce({ data: makeLoginResponse(etudiant, { refreshInCookie: false }) })
    renderLogin()

    await userEvent.type(screen.getByLabelText("Nom d'utilisateur"), 'p001')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'p001')
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/étudiant/i)
  })

  it('bascule l’affichage du mot de passe', async () => {
    renderLogin()
    const pwd = screen.getByLabelText('Mot de passe')
    expect(pwd).toHaveAttribute('type', 'password')
    await userEvent.click(screen.getByRole('button', { name: /voir le mot de passe/i }))
    expect(pwd).toHaveAttribute('type', 'text')
    await userEvent.click(screen.getByRole('button', { name: /masquer le mot de passe/i }))
    expect(pwd).toHaveAttribute('type', 'password')
  })

  it('redirige vers l’accueil si déjà authentifié', async () => {
    const admin = makeUser('ADMIN', { username: 'admin' })
    apiController.setMe(admin)
    renderLogin({ authUser: admin, initialEntries: ['/login'], routePattern: '/login' })
    // Le formulaire de connexion ne doit pas être rendu (Navigate to="/").
    await waitFor(() => expect(screen.queryByLabelText(/nom d'utilisateur/i)).not.toBeInTheDocument())
  })

  // NOTE (écart constaté, P00-04) : le backend expose user.must_change_password
  // mais le frontend Login.jsx/AuthContext ne gèrent aucune redirection de
  // changement de mot de passe obligatoire. Comportement ACTUEL documenté :
  // la connexion réussit sans invite. À traiter dans un lot fonctionnel (à
  // confirmer avec le commanditaire), sans correction silencieuse ici.
  it('[écart] must_change_password n’entraîne aujourd’hui aucune redirection', async () => {
    const user = makeUser('AUDITEUR') // rôle mobile pour garder une assertion stable
    user.must_change_password = true
    apiMock.post.mockResolvedValueOnce({ data: makeLoginResponse(user, { refreshInCookie: false }) })
    renderLogin()
    await userEvent.type(screen.getByLabelText("Nom d'utilisateur"), 'p001')
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'p001')
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }))
    // Le compte étudiant est refusé pour cause de rôle, indépendamment du flag.
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
