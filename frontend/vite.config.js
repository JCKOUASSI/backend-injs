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
    // Le proxy de l'aperçu Arena (*.e2b.app) est toujours expose en HTTPS,
    // meme s'il ne propage pas (ou propage mal) X-Forwarded-Proto : on force
    // https des que l'hote public transmis est un hote e2b.app. Un override
    // explicite par variable d'environnement reste possible.
    const protoRecu = req.headers['x-forwarded-proto']
    const hotePublic = String(host || '')
    const forceHttps =
      process.env.VITE_FORCE_HTTPS === '1' || /\.e2b\.app$/i.test(hotePublic)
    const proto = forceHttps ? 'https' : protoRecu || 'http'
    proxyReq.setHeader('X-Forwarded-Host', host || '')
    proxyReq.setHeader('X-Forwarded-Proto', proto)
    proxyReq.setHeader('X-Forwarded-For', req.socket.remoteAddress || '')
  }
  const proxyOpts = {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    configure: (proxy) => {
      proxy.on('proxyReq', forwardHeaders)
    },
  }

  return {
    plugins: [react()],
    resolve: { alias },
    server: {
      // Ports du projet : l'API Django sur 8000, le front sur 3000 (règle projet).
      port: 3000,
      strictPort: true,
      host: true,
      allowedHosts: ['.e2b.app', 'localhost', '127.0.0.1'],
      hmr,
      proxy: {
        // Aligne le frontend sur le backend réellement écouté (127.0.0.1:8000).
        // Les appels via chemin relatif /api contournent aussi les restrictions CORS.
        '/api': proxyOpts,
        // Admin Django legacy et fichiers servis par le backend.
        '/admin': proxyOpts,
        '/static': proxyOpts,
        '/media': proxyOpts,
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
    },
  }
})
