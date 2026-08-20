import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const resoudre = (chemin) => fileURLToPath(new URL(chemin, import.meta.url))

// Le module EPT-INJS vit hors de ings-fe/ : ses sources sont montées via alias.
const eptinjs = resoudre('../eptinjs/frontend')

// Situées hors de l'arborescence de ings-fe, ces sources ne remontent pas
// jusqu'à node_modules/ : les dépendances partagées sont résolues explicitement.
const DEPENDANCES_PARTAGEES = ['react', 'react-dom', 'react-router-dom', 'react-icons', 'html5-qrcode']

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@app': resoudre('./src'),
      '@eptinjs': eptinjs,
      ...Object.fromEntries(
        DEPENDANCES_PARTAGEES.map((paquet) => [paquet, resoudre(`./node_modules/${paquet}`)]),
      ),
    },
  },
  server: {
    port: 5173,
    open: true,
    fs: {
      allow: [resoudre('./'), eptinjs],
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
      '/media': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
    },
  },
})
