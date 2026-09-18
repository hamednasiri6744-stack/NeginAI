const CACHE_PREFIXES = ['workbox-', 'precache-', 'neginai-']

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys()
    await Promise.all(
      names
        .filter((name) => CACHE_PREFIXES.some((prefix) => name.startsWith(prefix)))
        .map((name) => caches.delete(name)),
    )
    await self.clients.claim()
  })())
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request, { cache: 'no-store' }).catch(() => fetch('/index.html', { cache: 'no-store' })),
    )
    return
  }

  // Hashed Vite assets are versioned by filename. Do not pin application
  // bundles in a service-worker cache during active development.
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(fetch(request))
  }
})
