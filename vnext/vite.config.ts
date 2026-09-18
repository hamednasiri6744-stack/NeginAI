import babel from '@rolldown/plugin-babel'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

const backendTarget = process.env.NEGINAI_BACKEND_TARGET?.trim() || 'http://127.0.0.1:8007'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    babel({
      presets: [reactCompilerPreset()],
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: 4183,
    strictPort: true,
    proxy: {
      '/auth': backendTarget,
      '/automations': backendTarget,
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
    proxy: {
      '/auth': backendTarget,
      '/automations': backendTarget,
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
  build: {
    target: 'baseline-widely-available',
  },
})
