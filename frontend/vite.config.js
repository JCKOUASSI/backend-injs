import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Alias partagé entre l'application et les tests (vitest.config.js doit rester aligné).
const alias = { '@': fileURLToPath(new URL('./src', import.meta.url)) }

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Aperçu derrière un reverse proxy TLS (ex: https://<port>-<sandbox>.e2b.app) :
  // forcer le WebSocket HMR en WSS. En local simple, on laisse Vite décider.
  const hmr = process.env.VITE_HMR_PROTOCOL
    ? {
        protocol: process.env.VITE_HMR_PROTOCOL,
        clientPort: Number(process.env.VITE_HMR_CLIENT_PORT || 443),
      }
    : undefined

  // Transmet au backend les en-têtes du proxy d'origine (hôte public, proto https)
  // afin que Django génère les bonnes URL absolues et les bons cookies CSRF.
  const forwardHeaders = (proxyReq, req) => {
    const host = req.headers['x-forwarded-host'] || req.headers.host
    // Le proxy de l'aperçu est toujours exposé en HTTPS (e2b.app, arena.site,
    // trycloudflare.com), meme s'il ne propage pas (ou propage mal)
    // X-Forwarded-Proto : on force https dès que l'hôte public transmis est
    // un hôte de passerelle. Un override explicite par variable d'environnement
    // reste possible.
    const protoRecu = req.headers['x-forwarded-proto']
    const hotePublic = String(host || '')
    const forceHttps =
      process.env.VITE_FORCE_HTTPS === '1' ||
      /\.(e2b\.app|arena\.site|trycloudflare\.com)$/i.test(hotePublic)
    const proto = forceHttps ? 'https' : protoRecu || 'http'
    proxyReq.setHeader('X-Forwarded-Host', host || '')
    proxyReq.setHeader('X-Forwarded-Proto', proto)
    proxyReq.setHeader('X-Forwarded-For', req.socket.remoteAddress || '')
  }
  const proxyOpts = {
    target: 'http://127.0.0.1:8000',
    // changeOrigin: false — on conserve l'en-tête Host d'origine (hôte public
    // de l'aperçu). Avec true, Django voyait « 127.0.0.1:8000 » : Origin/Referer
    // ne correspondaient plus à l'hôte reçu et les URL générées étaient fausses.
    changeOrigin: false,
    configure: (proxy) => {
      proxy.on('proxyReq', forwardHeaders)
    },
  }

  // Proxy commun dev/preview : l'API Django reste sur 8000, le front sur 3000.
  const proxy = {
    // Aligne le frontend sur le backend réellement écouté (127.0.0.1:8000).
    // Les appels via chemin relatif /api contournent aussi les restrictions CORS.
    '/api': proxyOpts,
    // Interface d'administration Django : le bouton « administration » de la
    // page de connexion doit fonctionner (décision produit du 2026-10-10).
    // Clé regex pour cibler le segment exact « /admin » uniquement : la route
    // SPA /administration/… ne doit PAS être happée par le proxy.
    '^/admin(/|\\?|$)': proxyOpts,
    // Fichiers servis par le backend (dont /static/admin/… de l'admin Django).
    '/static': proxyOpts,
    '/media': proxyOpts,
  }

  // Hôtes publics de l'aperçu intégré (iframe Arena) acceptés en dev comme
  // en preview (build de production servi par `vite preview`).
  const allowedHosts = ['.e2b.app', '.arena.site', '.trycloudflare.com', 'localhost', '127.0.0.1']

  return {
    plugins: [
      react(),
    ],
    resolve: { alias },
    server: {
      // Ports du projet : l'API Django sur 8000, le front sur 3000 (règle projet).
      port: 3000,
      strictPort: true,
      host: true,
      allowedHosts,
      hmr,
      proxy,
    },
    // `vite preview` sert dist/ (build de production auto-cohérent) sur le
    // même port 3000 avec le même proxy API — utilisé pour l'aperçu intégré.
    preview: {
      port: 3000,
      strictPort: true,
      host: true,
      allowedHosts,
      proxy,
    },
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
    },
  }
})
