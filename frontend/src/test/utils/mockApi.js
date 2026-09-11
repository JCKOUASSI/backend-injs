/**
 * Mock manuel du module `services/api` (sans réseau / sans MSW).
 *
 * Les pages et contextes reçoivent des réponses « vides mais sûres » par
 * défaut (aucun crash sur `.map()`, `.results`, `count`…). Chaque test peut
 * programmer des réponses précises par chemin (exacte ou expression régulière).
 */

/**
 * Proxy d'un tableau vide qui expose aussi n'importe quelle propriété de
 * collection (`results`, `sites`, `secretariats`…) sous forme de tableau vide
 * et les scalaires de pagination (`count` → 0, `next/previous` → null).
 */
export function safeData() {
  const target = []
  return new Proxy(target, {
    get(t, prop, receiver) {
      if (typeof prop === 'symbol') return Reflect.get(t, prop, receiver)
      if (prop === 'count' || prop === 'total') return 0
      if (prop === 'next' || prop === 'previous') return null
      if (prop === 'results' || prop === 'items') return []
      if (prop in t) return Reflect.get(t, prop, receiver)
      // Toute autre propriété de données est une collection vide.
      return []
    },
    // Respecte l'invariant des Proxy de tableau : 'length' doit être énuméré.
    ownKeys(t) {
      return Reflect.ownKeys(t)
    },
    getOwnPropertyDescriptor(t, prop) {
      return Reflect.getOwnPropertyDescriptor(t, prop)
    },
  })
}

function ok(data, status = 200) {
  return { data, status, statusText: status === 200 ? 'OK' : 'No Content' }
}

function makeApiMock() {
  const routes = []
  let meUser = null

  const matchRoute = (path) => {
    for (const route of routes) {
      if (route.match instanceof RegExp ? route.match.test(path) : route.match === path) {
        return route
      }
    }
    return null
  }

  const resolve = (path) => {
    if (path === '/auth/me/' && meUser) return ok(meUser)
    const route = matchRoute(path)
    if (route) return ok(route.data, route.status ?? 200)
    return ok(safeData())
  }

  const api = {
    get: vi.fn(async (path) => resolve(path)),
    post: vi.fn(async (path, body) => {
      const route = matchRoute(path)
      if (route) return ok(route.data ?? body ?? {}, route.status ?? 200)
      return ok({})
    }),
    patch: vi.fn(async (path, body) => {
      const route = matchRoute(path)
      if (route) return ok(route.data ?? body ?? {}, route.status ?? 200)
      return ok(body ?? {})
    }),
    put: vi.fn(async (path, body) => ok(body ?? {})),
    delete: vi.fn(async () => ok({}, 204)),
    getBlob: vi.fn(async () => ({
      blob: new Blob([''], { type: 'application/octet-stream' }),
      fileName: 'export.bin',
      contentType: 'application/octet-stream',
    })),
  }

  return {
    api,
    /** Programme une réponse GET (chemin exact ou RegExp). */
    setRoute(match, data, status = 200) {
      routes.push({ match, data, status })
    },
    /** Réinitialise les routes et l'utilisateur courant (appelé en beforeEach). */
    reset() {
      routes.length = 0
      meUser = null
      Object.values(api).forEach((fn) => fn && fn.mockClear && fn.mockClear())
    },
    /** Définit l'utilisateur renvoyé par GET /auth/me/ (AuthProvider). */
    setMe(user) {
      meUser = user
    },
    /** Trouve le premier appel dont le chemin correspond. */
    findCall(method, matcher) {
      const calls = api[method].mock.calls
      return calls.find(([path]) =>
        matcher instanceof RegExp ? matcher.test(path) : path === matcher,
      )
    },
    /** Corps JSON du dernier appel d'une méthode. */
    lastBody(method) {
      const calls = api[method].mock.calls
      return calls.length ? calls[calls.length - 1][1] : undefined
    },
  }
}

// Une instance unique partagée par les tests qui font vi.mock('@/services/api').
const controller = makeApiMock()

const apiMock = controller.api

export default apiMock
export { controller as apiController }

// Mock du module complet (utilisé via vi.mock avec une factory asynchrone).
export const apiModuleMock = {
  default: apiMock,
  API_BASE_URL: 'http://testserver/api',
  ADMIN_URL: 'http://testserver/admin/',
  setSessionExpiredCallback: vi.fn(),
}
