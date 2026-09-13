import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backend = 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: [
      'dev.hagents.ir',
      'localhost',
      '127.0.0.1'
    ],
    proxy: {
      '/auth': { target: backend, changeOrigin: false },
      '/seller-workspace': { target: backend, changeOrigin: false },
      '/audio': { target: backend, changeOrigin: false },
      '/health': { target: backend, changeOrigin: false },
    },
  },
})
