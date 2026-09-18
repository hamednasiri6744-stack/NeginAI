import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
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
    <PersianDigitsLayer />
    <RouterProvider router={router} />
  </StrictMode>,
)


if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // The prototype remains usable when service workers are unavailable (for example over plain HTTP LAN/Tailscale URLs).
    })
  })
}
