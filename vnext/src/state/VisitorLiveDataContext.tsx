import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { neginApi, type RouteCustomersResponse, type SellerCustomer, type SellerRoute, type SellerRoutesResponse } from '../api/neginApi'
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
  reload: () => Promise<void>
  customerById: (customerId: string) => SellerCustomer | undefined
}

const VisitorLiveDataContext = createContext<VisitorLiveDataValue | null>(null)

export function VisitorLiveDataProvider({ children }: { children: ReactNode }) {
  const { authenticated } = useVisitorAuth()
  const { hydrateLiveRoute, resetWorkflow } = useVisitorWorkflow()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [routesData, setRoutesData] = useState<SellerRoutesResponse | null>(null)
  const [customersData, setCustomersData] = useState<RouteCustomersResponse | null>(null)

  const load = useCallback(async () => {
    if (!authenticated) return
    setLoading(true)
    setError(null)
    try {
      const routes = await neginApi.routes()
      setRoutesData(routes)
      const selectedRoute = routes.day_route?.id
        ? routes.routes.find((route) => route.id === routes.day_route?.id)
          ?? routes.routes.find((route) => route.can_start_visit)
          ?? routes.routes[0]
        : routes.routes.find((route) => route.can_start_visit)
          ?? routes.routes[0]

      if (!selectedRoute) {
        setCustomersData(null)
        hydrateLiveRoute('', [])
        setError('ط¨ط±ط§غŒ ط§ظ…ط±ظˆط² ظ…ط³غŒط± ظپط¹ط§ظ„غŒ ط¯ط± NGT طھط¹غŒغŒظ† ظ†ط´ط¯ظ‡ ط§ط³طھ.')
        return
      }

      const customers = await neginApi.routeCustomers(selectedRoute.id)
      setCustomersData(customers)
      hydrateLiveRoute(selectedRoute.id, customers.customers)
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'ط¯ط±غŒط§ظپطھ ط§ط·ظ„ط§ط¹ط§طھ ط²ظ†ط¯ظ‡ ظˆغŒط²غŒطھظˆط± ط§ظ†ط¬ط§ظ… ظ†ط´ط¯.'
      setRoutesData(null)
      setCustomersData(null)
      hydrateLiveRoute('', [])
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [authenticated, hydrateLiveRoute])

  useEffect(() => {
    if (!authenticated) {
      setRoutesData(null)
      setCustomersData(null)
      setError(null)
      setLoading(false)
      resetWorkflow()
      return
    }
    void load()
  }, [authenticated, load, resetWorkflow])

  const activeRouteId = customersData?.route.id ?? routesData?.day_route?.id ?? null
  const activeRouteTitle = customersData?.route.title ?? routesData?.day_route?.title ?? ''
  const customers = customersData?.customers ?? []

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
    reload: load,
    customerById,
  }), [activeRouteId, activeRouteTitle, customerById, customers, customersData?.customer_count, customersData?.live_assignment, error, load, loading, routesData?.live_assignment, routesData?.routes])

  return <VisitorLiveDataContext.Provider value={value}>{children}</VisitorLiveDataContext.Provider>
}

export function useVisitorLiveData() {
  const value = useContext(VisitorLiveDataContext)
  if (!value) throw new Error('useVisitorLiveData must be used inside VisitorLiveDataProvider')
  return value
}


