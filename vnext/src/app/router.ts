import { useSyncExternalStore } from 'react'
import type { PrimaryDestination } from './navigation'
import { appRoutes, primaryForPath as resolvePrimaryForPath } from './routes'

export type AppPath =
  | '/' | '/modules' | '/ai' | '/reports' | '/more' | '/seller/routes'
  | '/seller/day-route' | '/seller/customers' | '/seller/map' | '/seller/customer'
  | '/seller/visit' | '/seller/catalog' | '/seller/cart' | '/design-system'

const primaryPaths: Record<PrimaryDestination, AppPath> = {
  home: '/',
  modules: '/modules',
  ai: '/ai',
  reports: '/reports',
  more: '/more',
}

function subscribe(listener: () => void) {
  window.addEventListener('popstate', listener)
  return () => window.removeEventListener('popstate', listener)
}

function snapshot() {
  return window.location.pathname
}

export function useAppPath() {
  return useSyncExternalStore(subscribe, snapshot, () => '/')
}

export function navigate(path: AppPath, replace = false) {
  const review = import.meta.env.DEV && new URLSearchParams(window.location.search).get('review') === '1'
  const target = review ? `${path}?review=1` : path
  if (window.location.pathname === path && (!review || window.location.search === '?review=1')) return
  if (replace) window.history.replaceState(null, '', target)
  else window.history.pushState(null, '', target)
  window.dispatchEvent(new PopStateEvent('popstate'))
  window.scrollTo({ top: 0, behavior: 'instant' })
}

export function pathForPrimary(destination: PrimaryDestination) {
  return primaryPaths[destination]
}

export function primaryForPath(pathname: string): PrimaryDestination {
  return resolvePrimaryForPath(pathname)
}

export function routeForPath(pathname: string) {
  return appRoutes.find((route) => route.path === pathname) ?? appRoutes[0]
}
