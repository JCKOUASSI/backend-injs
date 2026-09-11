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
      // Seuils du « filet de sécurité » (P00-04). Ils ne peuvent que monter.
      // Rehaussés au LOT 1 (moteur de listes + Décisions pédagogiques) puis
      // au LOT 2 (page serveur Users : recherche debounced, onglets/rôles,
      // pagination, création/édition/suppression). Mesure au LOT 2 :
      //   services 97 % l. / 91 % br. ; context 99 % l. / 91 % br. ;
      //   hooks 94 % l. / 91 % br. ; utils 77 % l. / 86 % br. ;
      //   Users 89 % l. ; global 33 % l. / 62 % br. / 24 % fn.
      // Chaque seuil est arrondi SOUS la mesure pour absorber la volatilité
      // du maillage par branches ; les lots suivants doivent les relever,
      // jamais les baisser.
      thresholds: {
        // Plancher global (filet anti-régression toutes zones confondues).
        statements: 32,
        branches: 58,
        functions: 22,
        lines: 32,
        perFile: false,
        'src/utils/roles.js': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'src/utils/**': {
          statements: 70,
          branches: 78,
          functions: 72,
          lines: 70,
        },
        'src/services/**': {
          statements: 90,
          branches: 85,
          functions: 90,
          lines: 90,
        },
        'src/context/**': {
          statements: 95,
          branches: 85,
          functions: 85,
          lines: 95,
        },
        'src/hooks/**': {
          statements: 88,
          branches: 85,
          functions: 80,
          lines: 88,
        },
      },
    },
  },
})
