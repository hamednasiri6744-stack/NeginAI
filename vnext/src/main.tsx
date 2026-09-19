import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { router } from './router'
import { PersianDigitsLayer } from './components/PersianDigitsLayer'
import './design-system/core/index.css'
import './styles/tailwind.css'
import './design-system/components/components.css'
import './styles/global.css'
import './styles/layout-architecture-v1.css'
import './design-system/theme/visual-baseline.css'
import './styles/home-visual-parity.css'

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
  let refreshing = false

  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (refreshing) return
    refreshing = true
    window.location.reload()
  })

  window.addEventListener('load', () => {
    const serviceWorkerUrl = '/sw-vnext-v2.js?v=' + encodeURIComponent(new URL(import.meta.url).pathname)
    navigator.serviceWorker.register(serviceWorkerUrl, { updateViaCache: 'none' }).then((registration) => {
      // Always revalidate the worker itself. The new worker claims open tabs and the
      // controllerchange handler above performs one clean reload onto the new app shell.
      void registration.update()
    }).catch(() => {
      // The app remains usable when service workers are unavailable.
    })
  })
}

