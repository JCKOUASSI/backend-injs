import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      // Aligne le frontend sur le backend réellement écouté (127.0.0.1:8000).
      // Les appels via chemin relatif /api contournent aussi les restrictions CORS.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: mode !== 'production',
  },
}))
