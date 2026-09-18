import babel from '@rolldown/plugin-babel'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

const backendTarget = process.env.NEGINAI_BACKEND_TARGET?.trim() || 'http://127.0.0.1:8007'

export default defineConfig({
  plugins: [
    react(),
    babel({
      presets: [reactCompilerPreset()],
    }),
    VitePWA({
      strategies: 'generateSW',
      registerType: 'autoUpdate',
      injectRegister: false,
      filename: 'sw.js',
      manifest: false,
      workbox: {
        cleanupOutdatedCaches: true,
        clientsClaim: true,
        skipWaiting: true,
        navigateFallback: '/index.html',
        globPatterns: ['**/*.{js,css,html,png,jpg,jpeg,svg,webp,woff,woff2}'],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/neshan-basemap/'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'neginai-map-basemap-v1',
              expiration: { maxEntries: 180, maxAgeSeconds: 60 * 60 * 24 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: 4183,
    strictPort: true,
    proxy: {
      '/auth': backendTarget,
      '/seller-workspace': backendTarget,
      '/chat': backendTarget,
      '/audio': backendTarget,
      '/attachments': backendTarget,
      '/neshan-basemap': {
        target: 'https://api.neshan.org',
        changeOrigin: true,
        rewrite: (path) => path.slice('/neshan-basemap'.length),
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4183,
    strictPort: true,
  },
  build: {
    target: 'baseline-widely-available',
  },
})
