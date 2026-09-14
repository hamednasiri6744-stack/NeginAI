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
      '/auth': 'https://ai.neginpakhsh.com',
      '/seller-workspace': 'https://ai.neginpakhsh.com',
      '/chat': 'https://ai.neginpakhsh.com',
      '/audio': 'https://ai.neginpakhsh.com',
      '/attachments': 'https://ai.neginpakhsh.com',
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


