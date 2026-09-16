import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// jsdom ne fournit pas ces API navigateur pourtant utilisées par certaines
// pages (graphiques, observateurs, défilement, media queries). On fournit des
// polyfils inertes mais sûrs, sans modifier le code applicatif.

if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = window.ResizeObserver || ResizeObserverStub

class IntersectionObserverStub {
  constructor(cb) {
    this.cb = cb
  }
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return []
  }
}
window.IntersectionObserver = window.IntersectionObserver || IntersectionObserverStub

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {}
}

if (!window.HTMLCanvasElement.prototype.getContext) {
  window.HTMLCanvasElement.prototype.getContext = function getContext() {
    return null
  }
}

// jsdom n'implémente pas layout : offsetWidth/Height valent 0, ce qui casse
// certains calculateurs de positionnement de menu. Valeurs déterministes.
Object.defineProperty(window.HTMLElement.prototype, 'offsetWidth', {
  configurable: true,
  get() {
    return 1000
  },
})
Object.defineProperty(window.HTMLElement.prototype, 'offsetHeight', {
  configurable: true,
  get() {
    return 800
  },
})

// Chaque test repart d'un stockage et de fetch propres.
afterEach(() => {
  cleanup()
  window.localStorage.clear()
  window.sessionStorage.clear()
  vi.restoreAllMocks()
})
