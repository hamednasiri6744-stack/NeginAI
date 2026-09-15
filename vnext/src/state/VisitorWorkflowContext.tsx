import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { PrevisitVisitDraftResponse, SellerCustomer } from '../api/neginApi'

const WORKFLOW_STORAGE_KEY = 'neginai.visitor.workflow.v2'

type StopStatus = 'visited' | 'active' | 'pending' | 'unlocated' | 'skipped'
export type VisitOutcome = 'no-order' | 'no-visit' | 'order-draft'

export type VisitorRouteStop = {
  stopId: number
  customerId: string
  name: string
  area: string
  distance: string
  eta: string
  priority: 'A' | 'B' | 'C'
  debtWarning?: boolean
  score: number
  status: StopStatus
  outcome?: VisitOutcome
}

type ActiveVisit = {
  id: string
  routeId: string
  customerId: string
  startedAt: number
}

type VisitorWorkflowState = {
  version: 2
  routeId: string
  activeCustomerId: string | null
  activeVisit: ActiveVisit | null
  activeDraftId: string | null
  routeStops: VisitorRouteStop[]
}

type VisitorWorkflowValue = VisitorWorkflowState & {
  routeSummary: {
    visited: number
    remaining: number
    total: number
    progress: number
  }
  hydrateLiveRoute: (routeId: string, customers: SellerCustomer[]) => void
  selectCustomer: (customerId: string | null) => void
  adoptServerVisit: (draft: PrevisitVisitDraftResponse) => ActiveVisit
  completeVisit: (customerId: string, outcome: VisitOutcome) => void
  attachDraft: (draftId: string | null) => void
  resetWorkflow: () => void
}

function freshInitialState(): VisitorWorkflowState {
  return {
    version: 2,
    routeId: '',
    activeCustomerId: null,
    activeVisit: null,
    activeDraftId: null,
    routeStops: [],
  }
}

function readState(): VisitorWorkflowState {
  try {
    const raw = sessionStorage.getItem(WORKFLOW_STORAGE_KEY)
    if (!raw) return freshInitialState()
    const parsed = JSON.parse(raw) as VisitorWorkflowState
    if (parsed?.version !== 2 || !Array.isArray(parsed.routeStops)) return freshInitialState()
    return parsed
  } catch {
    return freshInitialState()
  }
}

function persistState(value: VisitorWorkflowState) {
  try {
    sessionStorage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify(value))
  } catch {
    // Server state is authoritative once the write-side integration is enabled.
  }
}

function stopOutcome(customer: SellerCustomer): VisitOutcome | undefined {
  const outcome = String(customer.visit_resolution?.outcome ?? '')
  if (outcome === 'no_visit' || outcome === 'skipped') return 'no-visit'
  if (outcome === 'no_order') return 'no-order'
  if (outcome === 'order') return 'order-draft'
  return undefined
}

function liveStops(customers: SellerCustomer[]): VisitorRouteStop[] {
  let firstOpenAssigned = false
  return customers.map((customer, index) => {
    const resolution = customer.visit_resolution
    const resolved = resolution?.status === 'completed'
    const noVisit = resolved && ['no_visit', 'skipped'].includes(String(resolution?.outcome ?? ''))
    const hasLocation = customer.latitude !== null && customer.longitude !== null
    let status: StopStatus
    if (resolved) status = noVisit ? 'skipped' : 'visited'
    else if (!hasLocation) status = 'unlocated'
    else if (!firstOpenAssigned) {
      firstOpenAssigned = true
      status = 'active'
    } else status = 'pending'

    const returnedCheques = Number(customer.financial_snapshot?.returned_cheque_count ?? 0)
    const address = customer.address.trim()
    const resolvedOutcome = stopOutcome(customer)
    const base: VisitorRouteStop = {
      stopId: index + 1,
      customerId: String(customer.id),
      name: customer.store_name || customer.name || `مشتری ${customer.code}`,
      area: address || 'نشانی ثبت نشده',
      distance: '—',
      eta: status === 'visited' || status === 'skipped' ? 'انجام شده' : status === 'unlocated' ? 'موقعیت ندارد' : 'در انتظار',
      priority: returnedCheques > 0 ? 'A' : 'B',
      score: 0,
      status,
    }
    if (returnedCheques > 0) base.debtWarning = true
    if (resolvedOutcome) base.outcome = resolvedOutcome
    return base
  })
}

const VisitorWorkflowContext = createContext<VisitorWorkflowValue | null>(null)

export function VisitorWorkflowProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<VisitorWorkflowState>(readState)

  const update = useCallback((recipe: (current: VisitorWorkflowState) => VisitorWorkflowState) => {
    setState((current) => {
      const next = recipe(current)
      persistState(next)
      return next
    })
  }, [])

  const hydrateLiveRoute = useCallback((routeId: string, customers: SellerCustomer[]) => {
    update((current) => {
      const routeStops = liveStops(customers)
      const preservedActive = current.activeVisit && current.routeId === routeId
        && routeStops.some((stop) => stop.customerId === current.activeVisit?.customerId)
        ? current.activeVisit
        : null
      const preferredCustomer = preservedActive?.customerId
        ?? (current.routeId === routeId && current.activeCustomerId && routeStops.some((stop) => stop.customerId === current.activeCustomerId)
          ? current.activeCustomerId
          : routeStops.find((stop) => stop.status === 'active')?.customerId
            ?? routeStops.find((stop) => stop.status === 'pending')?.customerId
            ?? routeStops.find((stop) => stop.status === 'unlocated')?.customerId
            ?? routeStops[0]?.customerId
            ?? null)
      return {
        version: 2,
        routeId,
        activeCustomerId: preferredCustomer,
        activeVisit: preservedActive,
        activeDraftId: preservedActive ? current.activeDraftId : null,
        routeStops,
      }
    })
  }, [update])

  const selectCustomer = useCallback((customerId: string | null) => {
    update((current) => ({ ...current, activeCustomerId: customerId }))
  }, [update])

  const adoptServerVisit = useCallback((draft: PrevisitVisitDraftResponse) => {
    const parsedStartedAt = Date.parse(draft.started_at)
    const visit: ActiveVisit = {
      id: draft.visit_id,
      routeId: draft.route_id,
      customerId: String(draft.customer_id),
      startedAt: Number.isFinite(parsedStartedAt) ? parsedStartedAt : Date.now(),
    }
    update((current) => ({
      ...current,
      routeId: draft.route_id,
      activeCustomerId: String(draft.customer_id),
      activeVisit: visit,
      activeDraftId: null,
    }))
    return visit
  }, [update])


  const completeVisit = useCallback((customerId: string, outcome: VisitOutcome) => {
    update((current) => {
      const routeStops = current.routeStops.map((stop) => stop.customerId === customerId
        ? { ...stop, status: outcome === 'no-visit' ? 'skipped' as const : 'visited' as const, outcome }
        : stop)
      const next = routeStops.find((stop) => ['active', 'pending'].includes(stop.status))
      return {
        ...current,
        activeCustomerId: next?.customerId ?? null,
        activeVisit: null,
        activeDraftId: null,
        routeStops,
      }
    })
  }, [update])

  const attachDraft = useCallback((draftId: string | null) => {
    update((current) => ({ ...current, activeDraftId: draftId }))
  }, [update])

  const resetWorkflow = useCallback(() => {
    try { sessionStorage.removeItem(WORKFLOW_STORAGE_KEY) } catch { /* no-op */ }
    setState(freshInitialState())
  }, [])

  const routeSummary = useMemo(() => {
    const completed = state.routeStops.filter((stop) => ['visited', 'skipped'].includes(stop.status)).length
    const total = state.routeStops.length
    const remaining = Math.max(0, total - completed)
    return {
      visited: completed,
      remaining,
      total,
      progress: total ? Math.round((completed / total) * 100) : 0,
    }
  }, [state.routeStops])

  const value = useMemo<VisitorWorkflowValue>(() => ({
    ...state,
    routeSummary,
    hydrateLiveRoute,
    selectCustomer,
    adoptServerVisit,
    completeVisit,
    attachDraft,
    resetWorkflow,
  }), [adoptServerVisit, attachDraft, completeVisit, hydrateLiveRoute, resetWorkflow, routeSummary, selectCustomer, state])

  return <VisitorWorkflowContext.Provider value={value}>{children}</VisitorWorkflowContext.Provider>
}

export function useVisitorWorkflow() {
  const value = useContext(VisitorWorkflowContext)
  if (!value) throw new Error('useVisitorWorkflow must be used inside VisitorWorkflowProvider')
  return value
}
