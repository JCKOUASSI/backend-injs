/**
 * Smoke de démarrage RÉEL : monte l'application comme main.jsx (API non
 * mockée, réseau simulé en 401) et garantit qu'un premier rendu visible
 * apparaît. Une erreur de rendu ou un import cassé ferait écran blanc :
 * ce test échoue alors au lieu de passer silencieusement.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import React from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import App from '@/App.jsx'
import { queryClient } from '@/lib/queryClient.js'

describe('boot réel (anti écran blanc)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(
      new Response(JSON.stringify({ detail: 'non authentifié' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    )))
    window.history.pushState({}, '', '/')
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    cleanup()
  })

  it('affiche la page de connexion sans planter sur /', async () => {
    render(
      <React.StrictMode>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </React.StrictMode>
    )
    // Premier rendu visible : la page de connexion (session absente).
    const titre = await screen.findByRole('heading', { name: 'Connexion' }, { timeout: 5000 })
    expect(titre).toBeTruthy()
  }, 10000)
})
