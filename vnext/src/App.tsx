import './design-system/v2/styles.css'
import './design-system/v2/lab/canonical-swatches.css'
import './design-system/v2/v21.css'
import './design-system/v2/v21-responsive.css'
import { AppShell } from './components/AppShell'
import { NetworkStatus } from './components/NetworkStatus'
import { navigate, pathForPrimary, primaryForPath, routeForPath, useAppPath } from './app/router'
import { AuthGate } from './features/auth/AuthGate'

function ScreenRouter({ path }: { path: string }) {
  const route = routeForPath(path)
  const Screen = route.screen
  return <Screen />
}

function AuthenticatedApp({ path }: { path: string }) {
  return (
    <>
      <NetworkStatus />
      <AppShell active={primaryForPath(path)} onNavigate={(destination) => navigate(pathForPrimary(destination))}>
        <ScreenRouter path={path} />
      </AppShell>
    </>
  )
}

export default function App() {
  const path = useAppPath()
  const reviewHost = import.meta.env.DEV || ['dev.hagents.ir', 'localhost', '127.0.0.1'].includes(window.location.hostname)
  const isDesignSystem = path === '/design-system'
  const isWaveReview = reviewHost && new URLSearchParams(window.location.search).get('review') === '1'

  if (isDesignSystem && reviewHost) return <ScreenRouter path={path} />
  if (isWaveReview) return <AuthenticatedApp path={path} />
  return <AuthGate><AuthenticatedApp path={isDesignSystem ? '/' : path} /></AuthGate>
}
