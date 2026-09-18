import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router'
import { queryClient } from './queryClient'
import { router } from './router'
import { PersianDigitsLayer } from './components/PersianDigitsLayer'
import './design-system/core/index.css'
import './styles/global.css'

const root = document.getElementById('root')

if (!root) {
  throw new Error('NeginAI root element was not found')
}

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <PersianDigitsLayer />
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)


if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // The prototype remains usable when service workers are unavailable (for example over plain HTTP LAN/Tailscale URLs).
    })
  })
}
