import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react'
import { useLocation, useNavigate } from 'react-router'

const SCROLL_STORAGE_KEY = 'neginai.prototype.scroll.v1'

export function clearVisitorNavigationState() {
  try {
    sessionStorage.removeItem(SCROLL_STORAGE_KEY)
  } catch {
    // No-op in restrictive browser modes.
  }
}

type InternalNavigationState = {
  __neginInternal?: true
  __neginFrom?: string
  [key: string]: unknown
}

type GoOptions = {
  replace?: boolean
  state?: Record<string, unknown>
}

type VisitorNavigationValue = {
  go: (to: string, options?: GoOptions) => void
  back: (fallback: string) => void
  currentPath: string
}

const VisitorNavigationContext = createContext<VisitorNavigationValue | null>(null)

function readScrollPositions() {
  try {
    const raw = sessionStorage.getItem(SCROLL_STORAGE_KEY)
    if (!raw) return {} as Record<string, number>
    const parsed = JSON.parse(raw) as Record<string, number>
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {} as Record<string, number>
  }
}

function writeScrollPositions(value: Record<string, number>) {
  try {
    sessionStorage.setItem(SCROLL_STORAGE_KEY, JSON.stringify(value))
  } catch {
    // Scroll restoration is progressive enhancement only.
  }
}

function normalizePath(pathname: string, search: string) {
  return `${pathname}${search}`
}

export function VisitorNavigationProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const scrollPositions = useRef<Record<string, number>>(readScrollPositions())
  const currentPath = normalizePath(location.pathname, location.search)

  const saveScroll = useCallback(() => {
    scrollPositions.current[location.key] = window.scrollY
    writeScrollPositions(scrollPositions.current)
  }, [location.key])

  const go = useCallback((to: string, options: GoOptions = {}) => {
    const target = new URL(to, window.location.origin)
    const targetPath = `${target.pathname}${target.search}`

    if (!options.replace && targetPath === currentPath) return

    saveScroll()
    const state: InternalNavigationState = {
      ...(options.state ?? {}),
      __neginInternal: true,
      __neginFrom: currentPath,
    }
    if (options.replace) navigate(to, { replace: true, state })
    else navigate(to, { state })
  }, [currentPath, navigate, saveScroll])

  const back = useCallback((fallback: string) => {
    saveScroll()
    const state = location.state as InternalNavigationState | null
    if (state?.__neginInternal && state.__neginFrom) {
      navigate(-1)
      return
    }
    navigate(fallback, { replace: true, state: { __neginInternal: true } })
  }, [location.state, navigate, saveScroll])

  useLayoutEffect(() => {
    const previous = history.scrollRestoration
    history.scrollRestoration = 'manual'
    const targetY = scrollPositions.current[location.key] ?? 0
    const frame = window.requestAnimationFrame(() => window.scrollTo({ top: targetY, left: 0, behavior: 'auto' }))
    return () => {
      window.cancelAnimationFrame(frame)
      scrollPositions.current[location.key] = window.scrollY
      writeScrollPositions(scrollPositions.current)
      history.scrollRestoration = previous
    }
  }, [location.key])

  const value = useMemo<VisitorNavigationValue>(() => ({ go, back, currentPath }), [back, currentPath, go])

  return <VisitorNavigationContext.Provider value={value}>{children}</VisitorNavigationContext.Provider>
}

export function useVisitorNavigation() {
  const value = useContext(VisitorNavigationContext)
  if (!value) throw new Error('useVisitorNavigation must be used inside VisitorNavigationProvider')
  return value
}


