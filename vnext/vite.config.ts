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
      '/neshan-basemap': {
        target: 'https://api.neshan.org',
        changeOrigin: true,
        rewrite: (path) => path.slice(15),
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


