import { Suspense, lazy, type ComponentType } from 'react'
import { Navigate, Outlet, useParams, useSearchParams } from 'react-router'
import { LoginScreen } from './components/LoginScreen'

const CHUNK_RECOVERY_KEY = 'neginai.chunk-recovery'

function isChunkLoadFailure(error: unknown) {
  const message = error instanceof Error ? error.message : String(error)
  return /failed to fetch dynamically imported module|importing a module script failed|failed to fetch/i.test(message)
}

async function recoverStaleChunk() {
  try {
    const keys = await caches.keys()
    await Promise.all(
      keys
        .filter((key) => key.includes('workbox-precache'))
        .map((key) => caches.delete(key)),
    )
  } catch {
    // Cache cleanup is best-effort only.
  }

  try {
    const registrations = await navigator.serviceWorker?.getRegistrations()
    await Promise.all((registrations ?? []).map((registration) => registration.update()))
  } catch {
    // Service-worker update is best-effort only.
  }

  window.location.reload()
  return new Promise<never>(() => undefined)
}

function lazyWithRecovery<T extends ComponentType<any>>(loader: () => Promise<{ default: T }>) {
  return lazy(async () => {
    try {
      const loaded = await loader()
      try {
        sessionStorage.removeItem(CHUNK_RECOVERY_KEY)
      } catch {
        // Storage is non-critical.
      }
      return loaded
    } catch (error) {
      if (typeof window === 'undefined' || !isChunkLoadFailure(error)) throw error

      const fingerprint = `${window.location.pathname}${window.location.search}`
      try {
        if (sessionStorage.getItem(CHUNK_RECOVERY_KEY) === fingerprint) throw error
        sessionStorage.setItem(CHUNK_RECOVERY_KEY, fingerprint)
      } catch (storageError) {
        if (storageError === error) throw error
      }

      return recoverStaleChunk()
    }
  })
}

const VisitorHomeScreen = lazyWithRecovery(() => import('./components/VisitorHomeScreen').then((module) => ({ default: module.VisitorHomeScreen })))
const VisitorCustomersScreen = lazyWithRecovery(() => import('./components/VisitorCustomersScreen').then((module) => ({ default: module.VisitorCustomersScreen })))
const VisitorCustomer360Screen = lazyWithRecovery(() => import('./components/VisitorCustomer360Screen').then((module) => ({ default: module.VisitorCustomer360Screen })))
const VisitorRouteVisitScreen = lazyWithRecovery(() => import('./components/VisitorRouteVisitScreen').then((module) => ({ default: module.VisitorRouteVisitScreen })))
const VisitorOrdersScreen = lazyWithRecovery(() => import('./components/VisitorOrdersScreen').then((module) => ({ default: module.VisitorOrdersScreen })))
const VisitorOrderArchiveScreen = lazyWithRecovery(() => import('./components/VisitorOrderArchiveScreen').then((module) => ({ default: module.VisitorOrderArchiveScreen })))
const VisitorReportsScreen = lazyWithRecovery(() => import('./components/VisitorReportsScreen').then((module) => ({ default: module.VisitorReportsScreen })))
const VisitorNotificationsScreen = lazyWithRecovery(() => import('./components/VisitorNotificationsScreen').then((module) => ({ default: module.VisitorNotificationsScreen })))
const VisitorProfileSettingsScreen = lazyWithRecovery(() => import('./components/VisitorProfileSettingsScreen').then((module) => ({ default: module.VisitorProfileSettingsScreen })))
const FloatingNeginAi = lazyWithRecovery(() => import('./components/FloatingNeginAi').then((module) => ({ default: module.FloatingNeginAi })))
import { ProfileModalA11yBridge } from './components/ProfileModalA11yBridge'
import { VisitorNavigationProvider, clearVisitorNavigationState, useVisitorNavigation } from './navigation/VisitorNavigationContext'
import { VisitorWorkflowProvider, useVisitorWorkflow } from './state/VisitorWorkflowContext'
import { VisitorLiveDataProvider } from './state/VisitorLiveDataContext'
import { VisitorAuthProvider, useVisitorAuth } from './state/VisitorAuthContext'
import { VisitorNotificationsProvider, useVisitorNotifications } from './state/VisitorNotificationsContext'
import { clearPrototypeDrafts } from './state/visitorDraftStore'
import { clearVisitorOrderWorkspace } from './state/visitorOrderWorkspaceStore'

const LIVING_UI_PILOT_KEY = 'neginai.pilot.living-ui'

if (typeof window !== 'undefined') {
  try {
    const livingUiParam = new URLSearchParams(window.location.search).get('liveui')
    if (livingUiParam === '1') localStorage.setItem(LIVING_UI_PILOT_KEY, '1')
    if (livingUiParam === '0') localStorage.removeItem(LIVING_UI_PILOT_KEY)
  } catch {
    // Pilot flag is non-critical; storage failures must never block the app.
  }
}
function protectedView(authenticated: boolean, restoringSession: boolean, node: React.ReactNode) {
  if (restoringSession) return null
  return authenticated ? node : <Navigate to={'/'} replace />
}

function RouteLoadingFallback() {
  return (
    <main className="ng-stage" style={{ minHeight: '100dvh', display: 'grid', placeItems: 'center', borderRadius: 0 }}>
      <div className="ng-surface" role="status" aria-live="polite" style={{ padding: '18px 22px', minWidth: 220, textAlign: 'center' }}>
        <strong style={{ display: 'block', marginBottom: 6 }}>در حال آماده‌سازی صفحه…</strong>
        <small style={{ color: 'var(--ng-muted)' }}>NeginAI · Lazy Route</small>
      </div>
    </main>
  )
}

export function AppShellRoute() {
  return (
    <VisitorAuthProvider>
      <VisitorNavigationProvider>
        <VisitorWorkflowProvider>
          <VisitorLiveDataProvider>
            <VisitorNotificationsProvider>
              <ProfileModalA11yBridge />
              <Suspense fallback={<RouteLoadingFallback />}>
                <Outlet />
              </Suspense>
              <Suspense fallback={null}><FloatingNeginAi /></Suspense>
            </VisitorNotificationsProvider>
          </VisitorLiveDataProvider>
        </VisitorWorkflowProvider>
      </VisitorNavigationProvider>
    </VisitorAuthProvider>
  )
}

export function LoginRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, restoringSession, signIn } = useVisitorAuth()
  const { resetWorkflow } = useVisitorWorkflow()
  const { resetNotifications } = useVisitorNotifications()

  if (restoringSession) return null
  if (authenticated) return <Navigate to="/visitor/home" replace />

  return (
    <LoginScreen
      onLogin={async (username, password) => {
        // Start every named user in a clean browser workspace, then establish
        // and verify the signed HttpOnly session with the real backend.
        clearPrototypeDrafts()
        clearVisitorOrderWorkspace()
        clearVisitorNavigationState()
        resetWorkflow()
        resetNotifications()
        await signIn(username, password)
        go('/visitor/home', { replace: true })
      }}
    />
  )
}

export function VisitorHomeRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  return protectedView(authenticated, restoringSession, <VisitorHomeScreen onNavigate={(path) => go(path)} />)
}

export function VisitorRouteVisitRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  const [searchParams] = useSearchParams()
  return protectedView(authenticated, restoringSession, <VisitorRouteVisitScreen
      onNavigate={(path) => go(path)}
      requestedCustomerId={searchParams.get('customer') ?? undefined}
      intent={searchParams.get('intent') ?? undefined}
    />,
  )
}

export function VisitorOrdersRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  const [searchParams] = useSearchParams()
  return protectedView(authenticated, restoringSession, <VisitorOrdersScreen
      customerId={searchParams.get('customer') ?? undefined}
      draftId={searchParams.get('draft') ?? undefined}
      visitId={searchParams.get('visit') ?? undefined}
      returnTo={searchParams.get('returnTo') ?? undefined}
      onNavigate={(path) => go(path)}
    />,
  )
}

export function VisitorOrderArchiveRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  return protectedView(authenticated, restoringSession, <VisitorOrderArchiveScreen onNavigate={(path) => go(path)} />)
}

export function VisitorReportsRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  return protectedView(authenticated, restoringSession, <VisitorReportsScreen onNavigate={(path) => go(path)} />)
}

export function VisitorNotificationsRoute() {
  const { go, back } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  return protectedView(authenticated, restoringSession, <VisitorNotificationsScreen
      onNavigate={(path) => go(path)}
      onClose={() => back('/visitor/home')}
    />)
}

export function VisitorCustomersRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  return protectedView(authenticated, restoringSession, <VisitorCustomersScreen onNavigate={(path) => go(path)} />)
}

export function VisitorCustomer360Route() {
  const { go, back } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  const { customerId } = useParams()
  return protectedView(authenticated, restoringSession, <VisitorCustomer360Screen
      customerId={customerId ?? '1'}
      onNavigate={(path) => go(path)}
      onBack={() => back('/visitor/customers')}
    />,
  )
}

export function VisitorProfileSettingsRoute() {
  const { go, back } = useVisitorNavigation()
  const { authenticated, restoringSession, signOut } = useVisitorAuth()
  const { resetWorkflow } = useVisitorWorkflow()
  const { resetNotifications } = useVisitorNotifications()
  return protectedView(authenticated, restoringSession, <VisitorProfileSettingsScreen
      onNavigate={(path) => go(path)}
      onClose={() => back('/visitor/home')}
      onLogout={() => {
        void signOut()
        try { clearPrototypeDrafts() } catch { /* no-op */ }
        try { clearVisitorOrderWorkspace() } catch { /* no-op */ }
        try { clearVisitorNavigationState() } catch { /* no-op */ }
        try { resetWorkflow() } catch { /* no-op */ }
        try { resetNotifications() } catch { /* no-op */ }
        window.location.replace('/?signedout=1')
      }}
    />,
  )
}

export function NotFoundRoute() {
  const { authenticated, restoringSession } = useVisitorAuth()
  if (restoringSession) return null
  return <Navigate to={authenticated ? '/visitor/home' : '/'} replace />
}
