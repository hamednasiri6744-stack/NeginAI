import { Suspense, lazy } from 'react'
import { Navigate, Outlet, useParams, useSearchParams } from 'react-router'
import { LoginScreen } from './components/LoginScreen'

const VisitorHomeScreen = lazy(() => import('./components/VisitorHomeScreen').then((module) => ({ default: module.VisitorHomeScreen })))
const VisitorCustomersScreen = lazy(() => import('./components/VisitorCustomersScreen').then((module) => ({ default: module.VisitorCustomersScreen })))
const VisitorCustomer360Screen = lazy(() => import('./components/VisitorCustomer360Screen').then((module) => ({ default: module.VisitorCustomer360Screen })))
const VisitorRouteVisitScreen = lazy(() => import('./components/VisitorRouteVisitScreen').then((module) => ({ default: module.VisitorRouteVisitScreen })))
const VisitorOrdersScreen = lazy(() => import('./components/VisitorOrdersScreen').then((module) => ({ default: module.VisitorOrdersScreen })))
const VisitorOrderArchiveScreen = lazy(() => import('./components/VisitorOrderArchiveScreen').then((module) => ({ default: module.VisitorOrderArchiveScreen })))
const VisitorReportsScreen = lazy(() => import('./components/VisitorReportsScreen').then((module) => ({ default: module.VisitorReportsScreen })))
const VisitorNotificationsScreen = lazy(() => import('./components/VisitorNotificationsScreen').then((module) => ({ default: module.VisitorNotificationsScreen })))
const VisitorProfileSettingsScreen = lazy(() => import('./components/VisitorProfileSettingsScreen').then((module) => ({ default: module.VisitorProfileSettingsScreen })))
const VisitorAiScreen = lazy(() => import('./components/VisitorAiScreen').then((module) => ({ default: module.VisitorAiScreen })))
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

export function VisitorAiRoute() {
  const { go, back } = useVisitorNavigation()
  const { authenticated, restoringSession } = useVisitorAuth()
  const [searchParams] = useSearchParams()
  return protectedView(authenticated, restoringSession, <VisitorAiScreen
      context={searchParams.get('context') ?? 'home'}
      customerId={searchParams.get('customer') ?? undefined}
      visitId={searchParams.get('visit') ?? undefined}
      draftId={searchParams.get('draft') ?? undefined}
      prompt={searchParams.get('prompt') ?? undefined}
      onNavigate={(path) => go(path)}
      onBack={() => back('/visitor/home')}
    />,
  )
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
