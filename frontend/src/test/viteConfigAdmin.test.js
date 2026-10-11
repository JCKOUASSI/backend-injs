// @vitest-environment node
// (vite.config.js importe @vitejs/plugin-react → esbuild : indisponible sous jsdom)
/**
 * GARDE-FOU PERMANENT (2026-10-10) — passerelle de l'admin Django.
 *
 * Le bouton « administration » de la page de connexion doit fonctionner :
 * vite doit proxifier le segment exact « /admin » vers l'API (8000) en dev
 * ET en preview, ne JAMAIS re-bloquer /admin (plugin injs-blocage-admin),
 * et ne JAMAIS happer la route SPA /administration/… (route métier React).
 *
 * Source verrouillée : frontend/vite.config.js (partagé dev + preview).
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import configFactory from '../../vite.config.js'

const racineFront = fileURLToPath(new URL('../..', import.meta.url))
const conf = typeof configFactory === 'function' ? configFactory({ mode: 'production' }) : configFactory

// Sémantique Vite pour une clé de proxy (node_modules/vite/dist/node/chunks/config.js) :
//   context[0] === '^' && new RegExp(context).test(url) || url.startsWith(context)
const matchVite = (context, url) =>
  (context[0] === '^' && new RegExp(context).test(url)) || url.startsWith(context)

const cleAdmin = (proxy) => Object.keys(proxy || {}).find((k) => matchVite(k, '/admin/'))

describe('vite.config.js — proxy de l’admin Django (garde-fou)', () => {
  it('proxifie /admin en dev ET en preview', () => {
    expect(cleAdmin(conf.server?.proxy)).toBeTruthy()
    expect(cleAdmin(conf.preview?.proxy)).toBeTruthy()
  })

  it('la clé admin couvre /admin et /admin/… mais pas /administration/…', () => {
    const cle = cleAdmin(conf.server.proxy)
    expect(matchVite(cle, '/admin')).toBe(true)
    expect(matchVite(cle, '/admin/')).toBe(true)
    expect(matchVite(cle, '/admin/login/')).toBe(true)
    expect(matchVite(cle, '/administration/comptes')).toBe(false)
  })

  it('ne contient plus le plugin de blocage injs-blocage-admin', () => {
    const source = readFileSync(`${racineFront}/vite.config.js`, 'utf8')
    expect(source).not.toContain('injs-blocage-admin')
    const noms = (conf.plugins || []).map((p) => p && p.name).filter(Boolean)
    expect(noms).not.toContain('injs-blocage-admin')
  })
})

describe('vite.config.js — en-tête Host du proxy vers Django (garde-fou)', () => {
  // Régression 2026-10-11 : changeOrigin: true remplaçait Host par 127.0.0.1:8000,
  // ce qui désynchronisait Origin/Referer (CSRF) et les URL absolues de Django.
  it('conserve Host (changeOrigin: false) pour /api et /admin', () => {
    for (const cle of ['/api', cleAdmin(conf.server.proxy)]) {
      expect(conf.server.proxy[cle].changeOrigin).toBe(false)
      expect(conf.preview.proxy[cle].changeOrigin).toBe(false)
    }
  })
})
