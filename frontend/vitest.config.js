import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Configuration des tests frontend (Vitest + Testing Library).
// L'alias '@' reste strictement identique à celui de vite.config.js.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    css: false,
    // Les tests sont volontairement séquentiels : ils manipulent un même
    // localStorage/jsdom et des modules mono-flight (rafraîchissement JWT).
    pool: 'threads',
    poolOptions: { threads: { singleThread: true } },
    restoreMocks: true,
    clearMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'html', 'json-summary'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{js,jsx}'],
      exclude: [
        'src/main.jsx',
        'src/test/**',
        'src/**/*.test.{js,jsx}',
        'src/**/*.spec.{js,jsx}',
        'src/assets/**',
      ],
      // Seuils du « filet de sécurité » (P00-04). Ils ne peuvent que monter :
      //  - matrice de rôles = contrat de sécurité UI, couverture à 100 % ;
      //  - services/ et context/ ≥ 80 % (authentification, JWT, refresh) ;
      //  - hooks/ ≥ 70 % (logique de pagination/liste réutilisable) ;
      //  - un plancher GLOBAL est fixé sous le niveau mesuré au lot 0 (32 %
      //    de lignes / 57 % de branches mesurés le 2026-09-11) pour interdire
      //    toute régression nette, même sur des zones non encore ciblées.
      // Les valeurs ont été calibrées sur la première mesure puis arrondies
      // VERS LE BAS pour absorber la volatilité du maillage par branches ;
      // les lots suivants doivent les relever, jamais les baisser.
      thresholds: {
        // Plancher global (filet anti-régression toutes zones confondues).
        statements: 28,
        branches: 48,
        functions: 16,
        lines: 28,
        perFile: false,
        'src/utils/roles.js': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'src/services/**': {
          statements: 80,
          branches: 75,
          functions: 85,
          lines: 80,
        },
        'src/context/**': {
          statements: 80,
          branches: 75,
          functions: 85,
          lines: 80,
        },
        'src/hooks/**': {
          statements: 70,
          branches: 60,
          functions: 60,
          lines: 70,
        },
      },
    },
  },
})
