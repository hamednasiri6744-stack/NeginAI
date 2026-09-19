import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { neginApi, prefetchVisitorTour, type RouteCustomersResponse, type SellerCustomer, type SellerRoute, type SellerRoutesResponse, type SellerTargetPulse, type SellerWorkCalendar } from '../api/neginApi'
import { useVisitorAuth } from './VisitorAuthContext'
import { useVisitorWorkflowActions } from './VisitorWorkflowContext'
import { loadVisitorOfflineSnapshot, saveVisitorOfflineSnapshot } from './visitorOfflineSnapshotStore'

type VisitorLiveDataValue = {
  loading: boolean
  error: string | null
  routes: SellerRoute[]
  activeRouteId: string | null
  activeRouteTitle: string
  customers: SellerCustomer[]
  customerCount: number
  liveAssignment: boolean
  workCalendar: SellerWorkCalendar | null
  dayRouteStatus: string
  offDay: boolean
  targetPulse: SellerTargetPulse | null
  stale: boolean
  lastSyncedAt: string | null
  reload: () => Promise<void>
  customerById: (customerId: string) => SellerCustomer | undefined
}

const VisitorLiveDataContext = createContext<VisitorLiveDataValue | null>(null)

export function VisitorLiveDataProvider({ children }: { children: ReactNode }) {
  const { authenticated, restoringSession, profile } = useVisitorAuth()
  const { hydrateLiveRoute, resetWorkflow } = useVisitorWorkflowActions()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [routesData, setRoutesData] = useState<SellerRoutesResponse | null>(null)
  const [customersData, setCustomersData] = useState<RouteCustomersResponse | null>(null)
  const [targetPulse, setTargetPulse] = useState<SellerTargetPulse | null>(null)
  const [stale, setStale] = useState(false)
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!authenticated) return
    const username = profile?.username?.trim() ?? ''
    setLoading(true)
    setError(null)
    try {
      const targetPromise = neginApi.targetPulse().catch(() => null)
      const bootstrap = await neginApi.tourBootstrap()
      const routes = bootstrap.routes
      const customers = bootstrap.route_customers
      setRoutesData(routes)

      const liveTarget = await targetPromise
      const syncedAt = new Date().toISOString()
      setCustomersData(customers)
      setTargetPulse(liveTarget)
      setStale(false)
      setLastSyncedAt(syncedAt)

      if (customers) {
        hydrateLiveRoute(customers.route.id, customers.customers)
        void prefetchVisitorTour(customers.route.id).catch(() => undefined)
      } else {
        hydrateLiveRoute('', [])
      }

      if (username) {
        void saveVisitorOfflineSnapshot({
          version: 1,
          username,
          savedAt: syncedAt,
          routesData: routes,
          customersData: customers,
          targetPulse: liveTarget,
        }).catch(() => undefined)
      }

      if (!customers) {
        setError(routes.work_calendar?.is_working_day === false ? null : 'برای امروز مسیر فعالی در NGT تعیین نشده است.')
      }
    } catch (caught) {
      const snapshot = username
        ? await loadVisitorOfflineSnapshot(username).catch(() => null)
        : null
      if (snapshot) {
        setRoutesData(snapshot.routesData)
        setCustomersData(snapshot.customersData)
        setTargetPulse(snapshot.targetPulse)
        setStale(true)
        setLastSyncedAt(snapshot.savedAt)
        const snapshotRouteId = snapshot.customersData?.route.id ?? snapshot.routesData.day_route?.id ?? ''
        hydrateLiveRoute(snapshotRouteId, snapshot.customersData?.customers ?? [])
        setError('آفلاین — آخرین اطلاعات ذخیره‌شده نمایش داده می‌شود.')
      } else {
        const message = caught instanceof Error ? caught.message : 'دریافت اطلاعات زنده ویزیتور انجام نشد.'
        setRoutesData(null)
        setCustomersData(null)
        setTargetPulse(null)
        setStale(false)
        setLastSyncedAt(null)
        hydrateLiveRoute('', [])
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }, [authenticated, hydrateLiveRoute, profile?.username])

  useEffect(() => {
    if (restoringSession) return
    if (!authenticated) {
      setRoutesData(null)
      setCustomersData(null)
      setTargetPulse(null)
      setStale(false)
      setLastSyncedAt(null)
      setError(null)
      setLoading(false)
      resetWorkflow()
      return
    }

    let cancelled = false
    const bootstrap = async () => {
      const username = profile?.username?.trim() ?? ''
      if (username) {
        const snapshot = await loadVisitorOfflineSnapshot(username).catch(() => null)
        if (!cancelled && snapshot) {
          setRoutesData(snapshot.routesData)
          setCustomersData(snapshot.customersData)
          setTargetPulse(snapshot.targetPulse)
          setStale(true)
          setLastSyncedAt(snapshot.savedAt)
          setError(null)
          const snapshotRouteId = snapshot.customersData?.route.id ?? snapshot.routesData.day_route?.id ?? ''
          hydrateLiveRoute(snapshotRouteId, snapshot.customersData?.customers ?? [])
        }
      }
      if (!cancelled) void load()
    }

    void bootstrap()
    return () => { cancelled = true }
  }, [authenticated, hydrateLiveRoute, load, profile?.username, resetWorkflow, restoringSession])

  const activeRouteId = customersData?.route.id ?? routesData?.day_route?.id ?? null
  const activeRouteTitle = customersData?.route.title ?? routesData?.day_route?.title ?? ''
  const customers = customersData?.customers ?? []
  const offDay = routesData?.work_calendar?.is_working_day === false && !activeRouteId

  const customerById = useCallback((customerId: string) => (
    customers.find((customer) => String(customer.id) === String(customerId))
  ), [customers])

  const value = useMemo<VisitorLiveDataValue>(() => ({
    loading,
    error,
    routes: routesData?.routes ?? [],
    activeRouteId,
    activeRouteTitle,
    customers,
    customerCount: customersData?.customer_count ?? customers.length,
    liveAssignment: Boolean(customersData?.live_assignment ?? routesData?.live_assignment),
    workCalendar: routesData?.work_calendar ?? null,
    dayRouteStatus: routesData?.day_route_status ?? 'unknown',
    offDay,
    targetPulse,
    stale,
    lastSyncedAt,
    reload: load,
    customerById,
  }), [activeRouteId, activeRouteTitle, customerById, customers, customersData?.customer_count, customersData?.live_assignment, error, lastSyncedAt, load, loading, routesData?.live_assignment, routesData?.routes, routesData?.work_calendar, routesData?.day_route_status, offDay, stale, targetPulse])

  return <VisitorLiveDataContext.Provider value={value}>{children}</VisitorLiveDataContext.Provider>
}

export function useVisitorLiveData() {
  const value = useContext(VisitorLiveDataContext)
  if (!value) throw new Error('useVisitorLiveData must be used inside VisitorLiveDataProvider')
  return value
}


