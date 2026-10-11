// @vitest-environment node
/**
 * GARDE-FOU PERMANENT (2026-10-11) — comptes démo hors production.
 * Les identifiants de démonstration ne doivent jamais être servis par un build
 * de production : ils ne sont activés que par VITE_DEMO_ACCOUNTS=1 (dev/test/sandbox).
 */
import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const racine = fileURLToPath(new URL('../..', import.meta.url))
const lire = (f) => readFileSync(`${racine}/${f}`, 'utf8')

describe('comptes démo — isolés du build de production (garde-fou)', () => {
  it('aucun fichier .env de production n’active les comptes démo', () => {
    if (existsSync(`${racine}/.env.production`)) {
      expect(lire('.env.production')).not.toMatch(/^\s*VITE_DEMO_ACCOUNTS\s*=\s*1/m)
    }
  })

  it('dev, test et sandbox activent les comptes démo', () => {
    for (const f of ['.env.development', '.env.test', '.env.sandbox']) {
      expect(lire(f)).toMatch(/^VITE_DEMO_ACCOUNTS=1$/m)
    }
  })

  it('la page de connexion conditionne le bloc démo au drapeau de build', () => {
    const source = lire('src/pages/Login.jsx')
    expect(source).toContain("const DEMO_ACTIF = import.meta.env.VITE_DEMO_ACCOUNTS === '1'")
    expect(source).toMatch(/\{DEMO_ACTIF && \(/)
  })
})
