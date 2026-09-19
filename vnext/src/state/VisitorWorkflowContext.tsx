import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { NeshanRouteLeg, NeshanRouteMapPlanResponse, PrevisitVisitDraftResponse, SellerCustomer } from '../api/neginApi'

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
  priorityKnown: boolean
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
    resolved: number
    remaining: number
    total: number
    progress: number
  }
  hydrateLiveRoute: (routeId: string, customers: SellerCustomer[]) => void
  applyRoutePlan: (plan: NeshanRouteMapPlanResponse) => void
  updateNavigationMetrics: (customerId: string, leg: NeshanRouteLeg | null) => void
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
      priorityKnown: false,
      score: 0,
      status,
    }
    if (returnedCheques > 0) base.debtWarning = true
    if (resolvedOutcome) base.outcome = resolvedOutcome
    return base
  })
}

type VisitorWorkflowActionsValue = Pick<
  VisitorWorkflowValue,
  'hydrateLiveRoute' | 'applyRoutePlan' | 'updateNavigationMetrics' | 'selectCustomer' | 'adoptServerVisit' | 'completeVisit' | 'attachDraft' | 'resetWorkflow'
>

type VisitorWorkflowVisitValue = Pick<
  VisitorWorkflowState,
  'activeCustomerId' | 'activeVisit' | 'activeDraftId'
>

type VisitorWorkflowSummaryValue = {
  routeSummary: VisitorWorkflowValue['routeSummary']
}

const VisitorWorkflowContext = createContext<VisitorWorkflowValue | null>(null)
const VisitorWorkflowActionsContext = createContext<VisitorWorkflowActionsValue | null>(null)
const VisitorWorkflowVisitContext = createContext<VisitorWorkflowVisitValue | null>(null)
const VisitorWorkflowSummaryContext = createContext<VisitorWorkflowSummaryValue | null>(null)

export function VisitorWorkflowProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<VisitorWorkflowState>(readState)

  const update = useCallback((recipe: (current: VisitorWorkflowState) => VisitorWorkflowState) => {
    setState((current) => {
      const next = recipe(current)
      if (next === current) return current
      persistState(next)
      return next
    })
  }, [])

  const updateTransient = useCallback((recipe: (current: VisitorWorkflowState) => VisitorWorkflowState) => {
    setState((current) => recipe(current))
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

  const applyRoutePlan = useCallback((plan: NeshanRouteMapPlanResponse) => {
    update((current) => {
      if (!current.routeId || String(plan.route.id) !== String(current.routeId)) return current
      const info = new Map([...plan.ordered_customers, ...plan.unlocated_customers].map((customer, index) => [String(customer.id), { customer, index }]))
      const ordered = [...current.routeStops].sort((a, b) => (info.get(a.customerId)?.index ?? 1e9) - (info.get(b.customerId)?.index ?? 1e9))
      let firstOpenAssigned = false
      const routeStops = ordered.map((stop, index) => {
        const customer = info.get(stop.customerId)?.customer
        const tier = String(customer?.priority_tier || '').toLowerCase()
        const priorityKnown = ['high', 'medium', 'low'].includes(tier)
        const priority = tier === 'high' ? 'A' : tier === 'medium' ? 'B' : tier === 'low' ? 'C' : stop.priority
        let status = stop.status
        if (!['visited', 'skipped', 'unlocated'].includes(status)) {
          if (current.activeVisit) status = stop.customerId === current.activeVisit.customerId ? 'active' : 'pending'
          else if (!firstOpenAssigned) { firstOpenAssigned = true; status = 'active' } else status = 'pending'
        }
        return { ...stop, stopId: index + 1, priority, priorityKnown, score: Number(customer?.visit_score ?? stop.score), status }
      })
      const activeCustomerId = current.activeVisit?.customerId ?? routeStops.find((stop) => stop.status === 'active')?.customerId ?? routeStops.find((stop) => stop.status === 'pending')?.customerId ?? routeStops.find((stop) => stop.status === 'unlocated')?.customerId ?? routeStops[0]?.customerId ?? current.activeCustomerId
      return { ...current, routeStops, activeCustomerId }
    })
  }, [update])

  const updateNavigationMetrics = useCallback((customerId: string, leg: NeshanRouteLeg | null) => {
    if (!leg) return
    const distance = String(leg.distance?.text || '').trim()
    const eta = String(leg.duration?.text || '').trim()
    if (!distance && !eta) return
    updateTransient((current) => {
      let changed = false
      const routeStops = current.routeStops.map((stop) => {
        if (stop.customerId !== customerId) return stop
        const nextDistance = distance || stop.distance
        const nextEta = eta || stop.eta
        if (nextDistance === stop.distance && nextEta === stop.eta) return stop
        changed = true
        return { ...stop, distance: nextDistance, eta: nextEta }
      })
      return changed ? { ...current, routeStops } : current
    })
  }, [updateTransient])

  const selectCustomer = useCallback((customerId: string | null) => {
    update((current) => current.activeCustomerId === customerId ? current : ({ ...current, activeCustomerId: customerId }))
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
    update((current) => current.activeDraftId === draftId ? current : ({ ...current, activeDraftId: draftId }))
  }, [update])

  const resetWorkflow = useCallback(() => {
    try { sessionStorage.removeItem(WORKFLOW_STORAGE_KEY) } catch { /* no-op */ }
    setState(freshInitialState())
  }, [])

  const routeSummary = useMemo(() => {
    const visited = state.routeStops.filter((stop) => stop.status === 'visited').length
    const resolved = state.routeStops.filter((stop) => ['visited', 'skipped'].includes(stop.status)).length
    const total = state.routeStops.length
    const remaining = Math.max(0, total - resolved)
    return {
      visited,
      resolved,
      remaining,
      total,
      progress: total ? Math.round((resolved / total) * 100) : 0,
    }
  }, [state.routeStops])

  const actionsValue = useMemo<VisitorWorkflowActionsValue>(() => ({
    hydrateLiveRoute,
    applyRoutePlan,
    updateNavigationMetrics,
    selectCustomer,
    adoptServerVisit,
    completeVisit,
    attachDraft,
    resetWorkflow,
  }), [adoptServerVisit, applyRoutePlan, attachDraft, completeVisit, hydrateLiveRoute, resetWorkflow, selectCustomer, updateNavigationMetrics])
  const visitValue = useMemo<VisitorWorkflowVisitValue>(() => ({
    activeCustomerId: state.activeCustomerId,
    activeVisit: state.activeVisit,
    activeDraftId: state.activeDraftId,
  }), [state.activeCustomerId, state.activeDraftId, state.activeVisit])
  const summaryValue = useMemo<VisitorWorkflowSummaryValue>(() => ({ routeSummary }), [routeSummary])
  const value = useMemo<VisitorWorkflowValue>(() => ({
    ...state,
    routeSummary,
    ...actionsValue,
  }), [actionsValue, routeSummary, state])

  return (
    <VisitorWorkflowActionsContext.Provider value={actionsValue}>
      <VisitorWorkflowVisitContext.Provider value={visitValue}>
        <VisitorWorkflowSummaryContext.Provider value={summaryValue}>
          <VisitorWorkflowContext.Provider value={value}>{children}</VisitorWorkflowContext.Provider>
        </VisitorWorkflowSummaryContext.Provider>
      </VisitorWorkflowVisitContext.Provider>
    </VisitorWorkflowActionsContext.Provider>
  )
}

export function useVisitorWorkflow() {
  const value = useContext(VisitorWorkflowContext)
  if (!value) throw new Error('useVisitorWorkflow must be used inside VisitorWorkflowProvider')
  return value
}

export function useVisitorWorkflowActions() {
  const value = useContext(VisitorWorkflowActionsContext)
  if (!value) throw new Error('useVisitorWorkflowActions must be used inside VisitorWorkflowProvider')
  return value
}

export function useVisitorWorkflowVisit() {
  const value = useContext(VisitorWorkflowVisitContext)
  if (!value) throw new Error('useVisitorWorkflowVisit must be used inside VisitorWorkflowProvider')
  return value
}

export function useVisitorWorkflowSummary() {
  const value = useContext(VisitorWorkflowSummaryContext)
  if (!value) throw new Error('useVisitorWorkflowSummary must be used inside VisitorWorkflowProvider')
  return value
}
