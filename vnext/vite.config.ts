import babel from '@rolldown/plugin-babel'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    react(),
    babel({
      presets: [reactCompilerPreset()],
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: 4183,
    strictPort: true,
    proxy: {
      '/auth': 'http://127.0.0.1:8001',
      '/seller-workspace': 'http://127.0.0.1:8001',
      '/chat': 'http://127.0.0.1:8001',
      '/audio': 'http://127.0.0.1:8001',
      '/attachments': 'http://127.0.0.1:8001',
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

