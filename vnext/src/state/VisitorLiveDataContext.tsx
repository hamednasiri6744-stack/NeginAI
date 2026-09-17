import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getRouteMapPlan, neginApi, type RouteCustomersResponse, type SellerCustomer, type SellerRoute, type SellerRoutesResponse, type SellerTargetPulse, type SellerWorkCalendar } from '../api/neginApi'
import { useVisitorAuth } from './VisitorAuthContext'
import { useVisitorWorkflow } from './VisitorWorkflowContext'

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
  reload: () => Promise<void>
  customerById: (customerId: string) => SellerCustomer | undefined
}

const VisitorLiveDataContext = createContext<VisitorLiveDataValue | null>(null)

export function VisitorLiveDataProvider({ children }: { children: ReactNode }) {
  const { authenticated, restoringSession } = useVisitorAuth()
  const { applyRoutePlan, hydrateLiveRoute, resetWorkflow } = useVisitorWorkflow()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [routesData, setRoutesData] = useState<SellerRoutesResponse | null>(null)
  const [customersData, setCustomersData] = useState<RouteCustomersResponse | null>(null)
  const [targetPulse, setTargetPulse] = useState<SellerTargetPulse | null>(null)

  const load = useCallback(async () => {
    if (!authenticated) return
    setLoading(true)
    setError(null)
    try {
      void neginApi.targetPulse().then(setTargetPulse).catch(() => setTargetPulse(null))
      const routes = await neginApi.routes()
      setRoutesData(routes)
      const selectedRoute = routes.day_route?.id
        ? routes.routes.find((route) => route.id === routes.day_route?.id)
          ?? routes.routes.find((route) => route.can_start_visit)
        : routes.routes.find((route) => route.can_start_visit)

      if (!selectedRoute) {
        setCustomersData(null)
        hydrateLiveRoute('', [])
        if (routes.work_calendar?.is_working_day === false) {
          setError(null)
        } else {
          setError('برای امروز مسیر فعالی در NGT تعیین نشده است.')
        }
        return
      }

      const customers = await neginApi.routeCustomers(selectedRoute.id)
      setCustomersData(customers)
      hydrateLiveRoute(selectedRoute.id, customers.customers)
      void getRouteMapPlan(selectedRoute.id, 'sales_priority')
        .then((plan) => applyRoutePlan(plan))
        .catch(() => undefined)
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'دریافت اطلاعات زنده ویزیتور انجام نشد.'
      setRoutesData(null)
      setCustomersData(null)
      setTargetPulse(null)
      hydrateLiveRoute('', [])
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [authenticated, applyRoutePlan, hydrateLiveRoute])

  useEffect(() => {
    if (!authenticated) {
      setRoutesData(null)
      setCustomersData(null)
      setTargetPulse(null)
      setError(null)
      setLoading(false)
      resetWorkflow()
      return
    }
    void load()
  }, [authenticated, load, resetWorkflow, restoringSession])

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
    reload: load,
    customerById,
  }), [activeRouteId, activeRouteTitle, customerById, customers, customersData?.customer_count, customersData?.live_assignment, error, load, loading, routesData?.live_assignment, routesData?.routes, routesData?.work_calendar, routesData?.day_route_status, offDay, targetPulse])

  return <VisitorLiveDataContext.Provider value={value}>{children}</VisitorLiveDataContext.Provider>
}

export function useVisitorLiveData() {
  const value = useContext(VisitorLiveDataContext)
  if (!value) throw new Error('useVisitorLiveData must be used inside VisitorLiveDataProvider')
  return value
}


