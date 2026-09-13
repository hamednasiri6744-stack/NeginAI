import { Navigate, Outlet, useParams, useSearchParams } from 'react-router'
import { LoginScreen } from './components/LoginScreen'
import { VisitorHomeScreen } from './components/VisitorHomeScreen'
import { VisitorCustomersScreen } from './components/VisitorCustomersScreen'
import { VisitorCustomer360Screen } from './components/VisitorCustomer360Screen'
import { VisitorRouteVisitScreen } from './components/VisitorRouteVisitScreen'
import { VisitorOrdersScreen } from './components/VisitorOrdersScreen'
import { VisitorOrderArchiveScreen } from './components/VisitorOrderArchiveScreen'
import { VisitorReportsScreen } from './components/VisitorReportsScreen'
import { VisitorNotificationsScreen } from './components/VisitorNotificationsScreen'
import { VisitorProfileSettingsScreen } from './components/VisitorProfileSettingsScreen'
import { VisitorAiScreen } from './components/VisitorAiScreen'
import { VisitorNavigationProvider, clearVisitorNavigationState, useVisitorNavigation } from './navigation/VisitorNavigationContext'
import { VisitorWorkflowProvider, useVisitorWorkflow } from './state/VisitorWorkflowContext'
import { VisitorLiveDataProvider } from './state/VisitorLiveDataContext'
import { VisitorAuthProvider, useVisitorAuth } from './state/VisitorAuthContext'
import { VisitorNotificationsProvider, useVisitorNotifications } from './state/VisitorNotificationsContext'
import { clearPrototypeDrafts } from './state/visitorDraftStore'
import { clearVisitorOrderWorkspace } from './state/visitorOrderWorkspaceStore'

function protectedView(authenticated: boolean, node: React.ReactNode) {
  return authenticated ? node : <Navigate to="/" replace />
}

export function AppShellRoute() {
  return (
    <VisitorAuthProvider>
      <VisitorNavigationProvider>
        <VisitorWorkflowProvider>
          <VisitorLiveDataProvider>
            <VisitorNotificationsProvider>
              <Outlet />
            </VisitorNotificationsProvider>
          </VisitorLiveDataProvider>
        </VisitorWorkflowProvider>
      </VisitorNavigationProvider>
    </VisitorAuthProvider>
  )
}

export function LoginRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, signIn } = useVisitorAuth()
  const { resetWorkflow } = useVisitorWorkflow()
  const { resetNotifications } = useVisitorNotifications()

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
  const { authenticated } = useVisitorAuth()
  return protectedView(authenticated, <VisitorHomeScreen onNavigate={(path) => go(path)} />)
}

export function VisitorAiRoute() {
  const { go, back } = useVisitorNavigation()
  const { authenticated } = useVisitorAuth()
  const [searchParams] = useSearchParams()
  return protectedView(authenticated,
    <VisitorAiScreen
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
  const { authenticated } = useVisitorAuth()
  const [searchParams] = useSearchParams()
  return protectedView(authenticated,
    <VisitorRouteVisitScreen
      onNavigate={(path) => go(path)}
      requestedCustomerId={searchParams.get('customer') ?? undefined}
      intent={searchParams.get('intent') ?? undefined}
    />,
  )
}

export function VisitorOrdersRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated } = useVisitorAuth()
  const [searchParams] = useSearchParams()
  return protectedView(authenticated,
    <VisitorOrdersScreen
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
  const { authenticated } = useVisitorAuth()
  return protectedView(authenticated, <VisitorOrderArchiveScreen onNavigate={(path) => go(path)} />)
}

export function VisitorReportsRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated } = useVisitorAuth()
  return protectedView(authenticated, <VisitorReportsScreen onNavigate={(path) => go(path)} />)
}

export function VisitorNotificationsRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated } = useVisitorAuth()
  return protectedView(authenticated, <VisitorNotificationsScreen onNavigate={(path) => go(path)} />)
}

export function VisitorCustomersRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated } = useVisitorAuth()
  return protectedView(authenticated, <VisitorCustomersScreen onNavigate={(path) => go(path)} />)
}

export function VisitorCustomer360Route() {
  const { go, back } = useVisitorNavigation()
  const { authenticated } = useVisitorAuth()
  const { customerId } = useParams()
  return protectedView(authenticated,
    <VisitorCustomer360Screen
      customerId={customerId ?? '1'}
      onNavigate={(path) => go(path)}
      onBack={() => back('/visitor/customers')}
    />,
  )
}

export function VisitorProfileSettingsRoute() {
  const { go } = useVisitorNavigation()
  const { authenticated, signOut } = useVisitorAuth()
  const { resetWorkflow } = useVisitorWorkflow()
  const { resetNotifications } = useVisitorNotifications()
  return protectedView(authenticated,
    <VisitorProfileSettingsScreen
      onNavigate={(path) => go(path)}
      onLogout={async () => {
        clearPrototypeDrafts()
        clearVisitorOrderWorkspace()
        clearVisitorNavigationState()
        resetWorkflow()
        resetNotifications()
        await signOut()
        go('/', { replace: true })
      }}
    />,
  )
}

export function NotFoundRoute() {
  const { authenticated } = useVisitorAuth()
  return <Navigate to={authenticated ? '/visitor/home' : '/'} replace />
}
