import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  BellIcon,
  CartIcon,
  ChartIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  ClockIcon,
  HomeIcon,
  MapIcon,
  PhoneIcon,
  PinIcon,
  PlusIcon,
  RouteArrowIcon,
  StoreIcon,
  UserGroupIcon,
} from './Icons'
import { completeServerVisit, getVisitPolicy, neginApi, startServerVisit, type SellerCustomer, type SellerVisitPolicyResponse } from '../api/neginApi'
import { VisitorNeshanMap } from './VisitorNeshanMap'
import { VisitorPicker } from './VisitorPicker'
import { AppHeader, BottomDock } from '../design-system/components'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotificationBadge } from '../state/VisitorNotificationsContext'
import '../design-system/living/index.css'
import '../styles/living-ui-pilot.css'
import '../styles/visitor-route-depth.css'

type Props = {
  onNavigate: (path: string) => void
  requestedCustomerId?: string | undefined
  intent?: string | undefined
}
type RouteMode = 'sales' | 'shortest'
type VisitState = 'idle' | 'active' | 'outcome'

function joinRouteMeta(area: string, distance: string) {
  const parts = [area, distance]
    .map((value) => value.trim())
    .filter((value) => value.length > 0 && !/^[-\u2013\u2014]+$/.test(value))
  return parts.join(' \u00b7 ')
}

function formatTimer(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0')
  const seconds = (totalSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

export function VisitorRouteVisitScreen({ onNavigate, requestedCustomerId, intent: _intent }: Props) {
  const { unreadCount } = useVisitorNotificationBadge()
  const { profile } = useVisitorAuth()
  const { loading, error, activeRouteId, activeRouteTitle, customerById, reload, workCalendar, routes, offDay } = useVisitorLiveData()
  const {
    routeStops,
    routeSummary,
    activeCustomerId,
    activeVisit,
    activeDraftId,
    applyRoutePlan,
    updateNavigationMetrics,
    selectCustomer,
    adoptServerVisit,
    completeVisit,
  } = useVisitorWorkflow()
  const [mode, setMode] = useState<RouteMode>('sales')
  const [showStops, setShowStops] = useState(false)
  const [offDayLayer, setOffDayLayer] = useState<'overview' | 'routes' | 'customers'>('overview')
  const [browseRouteId, setBrowseRouteId] = useState('')
  const [browseRouteCustomers, setBrowseRouteCustomers] = useState<SellerCustomer[]>([])
  const [browseRouteRevision, setBrowseRouteRevision] = useState(0)
  const [browseRouteLoading, setBrowseRouteLoading] = useState(false)
  const [browseRouteError, setBrowseRouteError] = useState<string | null>(null)
  const [selectedCustomerId, setSelectedCustomerId] = useState(() => requestedCustomerId ?? activeVisit?.customerId ?? activeCustomerId ?? routeStops[0]?.customerId ?? '1')
  const [visitState, setVisitState] = useState<VisitState>(() => activeVisit ? 'active' : 'idle')
  const [outcome, setOutcome] = useState<'sale' | 'no-order' | 'no-visit'>('sale')
  const [notice, setNotice] = useState<string | null>(null)
  const [policy, setPolicy] = useState<SellerVisitPolicyResponse | null>(null)
  const [selectedReasonId, setSelectedReasonId] = useState('')
  const [actionBusy, setActionBusy] = useState<'start' | 'complete' | ''>('')
  const [mapRecenterNonce, setMapRecenterNonce] = useState(0)
  const [planOrderCustomerIds, setPlanOrderCustomerIds] = useState<string[]>([])
  const outcomeDialogRef = useRef<HTMLElement | null>(null)
  const visitTimerRef = useRef<HTMLElement | null>(null)
  const outcomeTimerRef = useRef<HTMLElement | null>(null)

  const browseRoute = useMemo(
    () => routes.find((route) => route.id === browseRouteId),
    [browseRouteId, routes],
  )

  useEffect(() => {
    if (!offDay || offDayLayer !== 'customers' || !browseRouteId) return
    let cancelled = false
    setBrowseRouteLoading(true)
    setBrowseRouteError(null)
    void neginApi.routeCustomers(browseRouteId, 'basic')
      .then((result) => {
        if (!cancelled) setBrowseRouteCustomers(result.customers ?? [])
      })
      .catch((caught) => {
        if (!cancelled) {
          setBrowseRouteCustomers([])
          setBrowseRouteError(caught instanceof Error ? caught.message : 'مشتریان Route دریافت نشدند.')
        }
      })
      .finally(() => {
        if (!cancelled) setBrowseRouteLoading(false)
      })
    return () => { cancelled = true }
  }, [browseRouteId, browseRouteRevision, offDay, offDayLayer])

  const sortedRouteStops = useMemo(() => {
    if (!planOrderCustomerIds.length) return routeStops
    const rank = new Map(planOrderCustomerIds.map((customerId, index) => [customerId, index]))
    return routeStops
      .map((stop, originalIndex) => ({ stop, originalIndex }))
      .sort((left, right) => {
        const leftRank = rank.get(left.stop.customerId)
        const rightRank = rank.get(right.stop.customerId)
        if (leftRank !== undefined && rightRank !== undefined) return leftRank - rightRank
        if (leftRank !== undefined) return -1
        if (rightRank !== undefined) return 1
        return left.originalIndex - right.originalIndex
      })
      .map(({ stop }) => stop)
  }, [routeStops, planOrderCustomerIds])

  const activeStop = useMemo(
    () => routeStops.find((stop) => stop.customerId === selectedCustomerId) ?? sortedRouteStops[0],
    [routeStops, sortedRouteStops, selectedCustomerId],
  )

  const outcomeKey = outcome === 'no-order' ? 'no_order' : outcome === 'no-visit' ? 'no_visit' : null
  const outcomeReasons = outcomeKey ? policy?.reasons?.[outcomeKey] ?? [] : []
  // Route map scoring is parity-validated against the full workspace analytics
  // and avoids loading the heavy intelligence payload just to render one score.
  const displayedScore = Number(activeStop?.score ?? 0)

  useEffect(() => {
    if (!activeRouteId || !activeStop?.customerId) {
      setPolicy(null)
      return
    }

    let cancelled = false
    setSelectedReasonId('')

    void getVisitPolicy(activeRouteId, activeStop.customerId)
      .then((nextPolicy) => {
        if (!cancelled) setPolicy(nextPolicy)
      })
      .catch((caught) => {
        if (!cancelled) {
          setPolicy(null)
          setNotice(caught instanceof Error ? caught.message : 'دریافت سیاست ویزیت ناموفق بود.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [activeRouteId, activeStop?.customerId])

  useEffect(() => {
    const target = requestedCustomerId ?? activeVisit?.customerId
    if (!target || !routeStops.some((stop) => stop.customerId === target)) return
    setSelectedCustomerId(target)
    selectCustomer(target)
  }, [activeVisit?.customerId, requestedCustomerId, routeStops, selectCustomer])

  useEffect(() => {
    if (!activeVisit) {
      setVisitState((current) => current === 'active' ? 'idle' : current)
      return
    }
    setSelectedCustomerId(activeVisit.customerId)
    setVisitState((current) => current === 'outcome' ? current : 'active')
  }, [activeVisit])

  useEffect(() => {
    const writeElapsed = () => {
      if (!activeVisit) {
        if (visitTimerRef.current) visitTimerRef.current.textContent = '00:00'
        if (outcomeTimerRef.current) outcomeTimerRef.current.textContent = '00:00'
        return
      }
      if (document.visibilityState !== 'visible') return
      const elapsed = Math.max(0, Math.floor((Date.now() - activeVisit.startedAt) / 1000))
      const formatted = formatTimer(elapsed)
      if (visitTimerRef.current) visitTimerRef.current.textContent = formatted
      if (outcomeTimerRef.current) outcomeTimerRef.current.textContent = formatted
    }

    writeElapsed()
    if (!activeVisit) return

    const interval = window.setInterval(writeElapsed, 1000)
    document.addEventListener('visibilitychange', writeElapsed)
    window.addEventListener('focus', writeElapsed)
    return () => {
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', writeElapsed)
      window.removeEventListener('focus', writeElapsed)
    }
  }, [activeVisit])

  useEffect(() => {
    if (visitState !== 'outcome') return
    const dialog = outcomeDialogRef.current
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialog?.focus()
    const handleOutcomeKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setVisitState('active')
        return
      }
      if (event.key !== 'Tab' || !dialog) return
      const controls = Array.from(dialog.querySelectorAll<HTMLElement>('button:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex=-1])'))
        .filter((element) => element.offsetParent !== null)
      if (!controls.length) { event.preventDefault(); return }
      const first = controls[0]!
      const last = controls[controls.length - 1]!
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', handleOutcomeKeyDown)
    return () => {
      document.removeEventListener('keydown', handleOutcomeKeyDown)
      previous?.focus()
    }
  }, [visitState])
  const flash = useCallback((message: string) => {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }, [])

  const handlePlanOrder = useCallback((customerIds: string[]) => {
    setPlanOrderCustomerIds((current) =>
      current.length === customerIds.length && current.every((customerId, index) => customerId === customerIds[index])
        ? current
        : customerIds,
    )
  }, [])

  useEffect(() => {
    setPlanOrderCustomerIds([])
  }, [activeRouteId, mode])

  const selectPlanPrimary = useCallback((customerId: string) => {
    if (activeVisit) return
    if (!routeStops.some((stop) => stop.customerId === customerId)) return
    setSelectedCustomerId(customerId)
    selectCustomer(customerId)
  }, [activeVisit, routeStops, selectCustomer])

  const selectStop = useCallback((customerId: string) => {
    if (activeVisit && activeVisit.customerId !== customerId) {
      flash('ابتدا بازدید فعال را تکمیل یا متوقف کن')
      return
    }
    setSelectedCustomerId(customerId)
    selectCustomer(customerId)
  }, [activeVisit, flash, selectCustomer])

  function readCurrentPosition(required: boolean) {
    if (!required) return Promise.resolve<GeolocationCoordinates | null>(null)
    if (!('geolocation' in navigator)) {
      return Promise.reject(new Error('برای شروع این ویزیت دسترسی GPS لازم است.'))
    }
    return new Promise<GeolocationCoordinates>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => resolve(position.coords),
        () => reject(new Error('موقعیت GPS دریافت نشد؛ مجوز Location و GPS دستگاه را بررسی کنید.')),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 },
      )
    })
  }

  async function startVisit() {
    if (!activeStop || !activeRouteId || actionBusy) return
    if (['visited', 'skipped'].includes(activeStop.status)) {
      flash('این مشتری امروز تعیین تکلیف شده است.')
      return
    }

    setActionBusy('start')
    try {
      const latestPolicy = await getVisitPolicy(activeRouteId, activeStop.customerId)
      setPolicy(latestPolicy)
      if (!latestPolicy.can_start_visit) {
        throw new Error(latestPolicy.start_blockers[0] || 'Backend اجازه شروع ویزیت را نداد.')
      }

      const needsLocation = Boolean(latestPolicy.controls.enforced) && !latestPolicy.customer.location_check_exempt
      const coords = await readCurrentPosition(needsLocation)
      const draft = await startServerVisit({
        route_id: activeRouteId,
        customer_id: activeStop.customerId,
        ...(coords ? { latitude: coords.latitude, longitude: coords.longitude, accuracy: coords.accuracy } : {}),
      })

      adoptServerVisit(draft)
      setVisitState('active')
      flash('ویزیت با تأیید Backend شروع شد.')
    } catch (caught) {
      flash(caught instanceof Error ? caught.message : 'شروع ویزیت ناموفق بود.')
    } finally {
      setActionBusy('')
    }
  }

  async function confirmOutcome() {
    if (!activeStop || !activeVisit || actionBusy) return

    if (outcome === 'sale') {
      setVisitState('active')
      onNavigate(`/visitor/orders?customer=${activeStop.customerId}&visit=${encodeURIComponent(activeVisit.id)}&returnTo=${encodeURIComponent(`/visitor/route?customer=${activeStop.customerId}`)}`)
      return
    }

    const backendOutcome = outcome === 'no-order' ? 'no_order' : 'no_visit'
    if (!selectedReasonId) {
      flash('یک دلیل معتبر NGT را انتخاب کنید.')
      return
    }

    setActionBusy('complete')
    try {
      const result = await completeServerVisit(activeVisit.id, {
        outcome: backendOutcome,
        reason_id: selectedReasonId,
      })
      if (result.visit_status !== 'completed') {
        throw new Error('Backend پایان ویزیت را تأیید نکرد.')
      }

      completeVisit(activeStop.customerId, outcome === 'no-visit' ? 'no-visit' : 'no-order')
      setSelectedReasonId('')
      setVisitState('idle')
      await reload()
      flash('نتیجه ویزیت در Backend ثبت شد.')
    } catch (caught) {
      flash(caught instanceof Error ? caught.message : 'ثبت نتیجه ویزیت ناموفق بود.')
    } finally {
      setActionBusy('')
    }
  }

  function callActiveCustomer() {
    if (!activeStop) return
    const customer = customerById(activeStop.customerId)
    const phone = (customer?.mobile || customer?.phone || '').replace(/[^\d+]/g, '')
    if (!phone) { flash('شماره تماس معتبری برای این مشتری دریافت نشد'); return }
    window.location.href = `tel:${phone}`
  }

  if (!activeStop) {
    return (
      <main className="vh-page vh-live-ui ng-living-root vr-app-page vr-depth-page" dir="rtl" data-live-ui="unified" data-living-ui="on">
        <div className="vh-shell vr-shell">
          <AppHeader
            avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}
            title={profile?.full_name || profile?.username || 'ویزیتور'}
            subtitle={profile?.branch || profile?.sales_line || 'حساب سازمانی'}
            subtitleIcon={<PinIcon />}
            profileTrailing={<ChevronLeftIcon />}
            onProfileClick={() => onNavigate('/visitor/profile')}
            action={(
              <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
                <BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}
              </button>
            )}
          />

          {offDay ? (
            <section className="vr-offday-stage ng-depth-stage" data-depth={offDayLayer === 'overview' ? 0 : offDayLayer === 'routes' ? 1 : 2}>
              <span className="ng-depth-backplane" data-plane="1" aria-hidden="true" />
              <span className="ng-depth-backplane" data-plane="2" aria-hidden="true" />

              {offDayLayer === 'overview' ? (
                <div className="vr-offday-layer vr-offday-overview">
                  <div className="vr-offday-command ng-layer-surface">
                    <span className="vr-offday-icon"><ClockIcon /></span>
                    <span className="vr-offday-copy">
                      <small>تقویم رسمی NGT</small>
                      <strong>امروز روز کاری نیست</strong>
                      <em>{workCalendar?.date ? `${workCalendar.date} · ` : ''}مسیر فعال نداریم؛ Routeهای تخصیص‌یافته همین‌جا قابل مرورند.</em>
                    </span>
                    <span className="vr-offday-days">
                      <b>{Number(workCalendar?.remaining_working_days ?? 0).toLocaleString('fa-IR')}</b>
                      <small>روز باقی‌مانده</small>
                    </span>
                  </div>

                  <div className="vr-offday-route-deck ng-layer-surface">
                    <button type="button" className="vr-offday-route-entry ng-living-interactive" onClick={() => setOffDayLayer('routes')}>
                      <span className="vr-offday-route-entry-icon"><MapIcon /></span>
                      <span><small>عمق Route</small><strong>Routeهای تخصیص‌یافته</strong><em>{routes.length.toLocaleString('fa-IR')} مسیر · مشتریان هر مسیر را همین‌جا باز کن</em></span>
                      <ChevronLeftIcon />
                    </button>
                    <div className="vr-offday-route-metrics">
                      <span><small>مجموع مشتری</small><strong>{routes.reduce((sum, route) => sum + Number(route.customer_count ?? 0), 0).toLocaleString('fa-IR')}</strong></span>
                      <span><small>روز سپری‌شده</small><strong>{Number(workCalendar?.elapsed_working_days ?? 0).toLocaleString('fa-IR')}</strong></span>
                      <span><small>روز باقی‌مانده</small><strong>{Number(workCalendar?.remaining_working_days ?? 0).toLocaleString('fa-IR')}</strong></span>
                    </div>
                    <div className="vr-offday-route-preview" aria-label="مسیرهای تخصیص‌یافته">
                      {routes.slice(0, 4).map((route, index) => (
                        <button
                          type="button"
                          key={route.id}
                          className="ng-living-interactive"
                          onClick={() => {
                            setBrowseRouteId(route.id)
                            setOffDayLayer('customers')
                          }}
                        >
                          <b>{(index + 1).toLocaleString('fa-IR')}</b>
                          <span>
                            <strong>{route.title}</strong>
                            <small>{Number(route.customer_count ?? 0).toLocaleString('fa-IR')} مشتری · مرور Route</small>
                          </span>
                          <ChevronLeftIcon />
                        </button>
                      ))}
                      {!routes.length ? <div className="vr-offday-empty">Route تخصیص‌یافته‌ای ثبت نشده است.</div> : null}
                    </div>
                  </div>
                </div>
              ) : null}

              {offDayLayer === 'routes' ? (
                <div className="vr-offday-layer vr-offday-depth ng-layer-surface">
                  <header className="vr-offday-depth-head">
                    <button type="button" className="vr-offday-back ng-living-interactive" onClick={() => setOffDayLayer('overview')}><ChevronLeftIcon /></button>
                    <span className="vr-offday-depth-icon"><MapIcon /></span>
                    <span><small>مسیر · لایه ۱</small><strong>Routeهای تخصیص‌یافته</strong><em>بدون خروج از ماژول مسیر</em></span>
                  </header>
                  <div className="vr-offday-route-list">
                    {routes.map((route) => (
                      <button
                        type="button"
                        className="vr-offday-route-row ng-detail-surface ng-living-interactive"
                        key={route.id}
                        onClick={() => { setBrowseRouteId(route.id); setOffDayLayer('customers') }}
                      >
                        <span className="vr-offday-route-index"><RouteArrowIcon /></span>
                        <span><strong>{route.title}</strong><small>{Number(route.customer_count ?? 0).toLocaleString('fa-IR')} مشتری در Route</small></span>
                        <ChevronLeftIcon />
                      </button>
                    ))}
                    {!routes.length ? <div className="vr-offday-empty">Route تخصیص‌یافته‌ای ثبت نشده است.</div> : null}
                  </div>
                </div>
              ) : null}

              {offDayLayer === 'customers' ? (
                <div className="vr-offday-layer vr-offday-depth ng-layer-surface">
                  <header className="vr-offday-depth-head">
                    <button type="button" className="vr-offday-back ng-living-interactive" onClick={() => setOffDayLayer('routes')}><ChevronLeftIcon /></button>
                    <span className="vr-offday-depth-icon"><UserGroupIcon /></span>
                    <span><small>مسیر · لایه ۲</small><strong>{browseRoute?.title || 'مشتریان Route'}</strong><em>{browseRouteCustomers.length.toLocaleString('fa-IR')} مشتری · مرور درون‌ماژولی</em></span>
                  </header>

                  {browseRouteError ? (
                    <button type="button" className="vr-offday-error" onClick={() => setBrowseRouteRevision((value) => value + 1)}>
                      <strong>دریافت مشتریان ناموفق بود</strong><small>{browseRouteError}</small>
                    </button>
                  ) : null}

                  <div className="vr-offday-customer-list">
                    {browseRouteLoading ? <div className="vr-offday-empty">در حال دریافت مشتریان Route…</div> : null}
                    {!browseRouteLoading && browseRouteCustomers.map((customer, index) => {
                      const phone = (customer.mobile || customer.phone || '').replace(/[^\d+]/g, '')
                      const risk = Number(customer.financial_snapshot?.returned_cheque_count ?? 0) > 0
                      return (
                        <article className="vr-offday-customer ng-detail-surface" key={String(customer.id)}>
                          <span className={risk ? 'risk' : ''}>{index + 1}</span>
                          <div><strong>{customer.store_name || customer.name || customer.code}</strong><small>{customer.address || 'نشانی ثبت نشده'}</small>{risk ? <em>هشدار مالی ثبت‌شده</em> : null}</div>
                          <button type="button" disabled={!phone} onClick={() => { if (phone) window.location.href = `tel:${phone}` }}><PhoneIcon /></button>
                        </article>
                      )
                    })}
                    {!browseRouteLoading && !browseRouteCustomers.length && !browseRouteError ? <div className="vr-offday-empty">مشتری فعالی برای این Route دریافت نشد.</div> : null}
                  </div>
                </div>
              ) : null}
            </section>
          ) : (
            <section className={error ? 'vh-live-state error' : 'vh-live-state'} role={error ? 'alert' : 'status'}>
              <div><strong>{loading ? 'در حال دریافت مسیر واقعی…' : error ? 'مسیر امروز دریافت نشد' : 'برای امروز ایستگاهی وجود ندارد'}</strong><span>{error || 'اطلاعات Seller Workspace در حال بررسی است.'}</span></div>
              {error ? <button type="button" onClick={() => void reload()}>تلاش دوباره</button> : null}
            </section>
          )}

          <BottomDock
            ariaLabel="ناوبری ویزیتور"
            items={[
            { key: 'home', label: 'خانه', icon: <HomeIcon />, onClick: () => onNavigate('/visitor/home') },
            { key: 'route', label: 'مسیر', icon: <MapIcon />, active: true, onClick: () => onNavigate('/visitor/route') },
            { key: 'customers', label: 'مشتریان', icon: <UserGroupIcon />, onClick: () => onNavigate('/visitor/customers') },
            { key: 'reports', label: 'گزارش‌ها', icon: <ChartIcon />, onClick: () => onNavigate('/visitor/reports') },
            ]}
            primary={{
              label: 'سفارش',
              icon: <PlusIcon />,
              onClick: () => onNavigate('/visitor/orders'),
            }}
          />
        </div>
      </main>
    )
  }

  return (
    <main className="vh-page vh-live-ui ng-living-root vr-app-page vr-depth-page" dir="rtl" data-live-ui="unified" data-living-ui="on">
      <div className="vh-shell vr-shell">
        <AppHeader
          avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}
          title={profile?.full_name || profile?.username || 'ویزیتور'}
          subtitle={profile?.branch || profile?.sales_line || 'حساب سازمانی'}
          subtitleIcon={<PinIcon />}
          profileTrailing={<ChevronLeftIcon />}
          onProfileClick={() => onNavigate('/visitor/profile')}
          action={(
            <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
              <BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}
            </button>
          )}
        />

        <section className="vr-route-bar ng-living-surface">
          <div><span>مسیر فعال · {activeRouteTitle || 'NGT'}</span><strong>{routeSummary.resolved} تعیین‌تکلیف · {routeSummary.remaining} باقی‌مانده</strong></div>
          <div className="vr-route-bar-actions"><div className="vr-progress"><strong>{routeSummary.progress}٪</strong><small>پیشرفت</small></div></div>
        </section>

        <section className="vr-map-card vr-map-first ng-living-surface" aria-label="نقشه مسیر امروز">
          <div className="vr-map-head"><div><MapIcon /><strong>مسیر امروز</strong></div><button type="button" onClick={() => setMapRecenterNonce((value) => value + 1)}><PinIcon /> مرکز روی من</button></div>
          <div className="vr-map-modes" aria-label="حالت برنامه‌ریزی مسیر"><button type="button" aria-pressed={mode === 'sales'} className={mode === 'sales' ? 'active' : ''} onClick={() => setMode('sales')}>اولویت فروش</button><button type="button" aria-pressed={mode === 'shortest'} className={mode === 'shortest' ? 'active' : ''} onClick={() => setMode('shortest')}>کوتاه‌ترین</button></div>
          <div className="vr-map-canvas">
            <VisitorNeshanMap routeId={activeRouteId} mode={mode} selectedCustomerId={selectedCustomerId} recenterNonce={mapRecenterNonce} routeStops={routeStops} onSelectCustomer={selectStop} onPrimaryCustomer={selectPlanPrimary} onOrderChange={handlePlanOrder} onPlan={applyRoutePlan} onNavigationMetrics={updateNavigationMetrics} onNotice={flash} />
          </div>
        </section>

        <section className="vr-active-card vr-context-sheet ng-living-surface" data-visit-state={visitState}>
          <div className="vr-active-top">
            <span className="vr-store"><StoreIcon /></span>
            <div><small>ایستگاه انتخاب‌شده</small><strong>{activeStop.name}</strong><span>{joinRouteMeta(activeStop.area, activeStop.distance)}</span></div>
            {activeStop.priorityKnown ? <span className={`vr-priority p-${activeStop.priority.toLowerCase()}`}>{activeStop.priority}</span> : null}
          </div>
          <div className="vr-active-meta">
            <span><ClockIcon /> {activeStop.eta}</span>
            {displayedScore > 0 ? <span><ChartIcon /> امتیاز {displayedScore}</span> : null}
            {activeStop.debtWarning ? <span className="warning">هشدار بدهی</span> : null}
          </div>

          {visitState === 'idle' && ['visited', 'skipped'].includes(activeStop.status) ? (
            <div className="vr-resolved">
              <div><strong>{activeStop.status === 'skipped' ? 'عدم ویزیت ثبت شده' : activeStop.outcome === 'order-draft' ? 'بازدید انجام شد · سفارش پیش‌نویس' : 'بازدید انجام شده'}</strong><span>برای مشاهده جزئیات مشتری از پروفایل استفاده کن.</span></div>
              <button type="button" onClick={() => onNavigate(`/visitor/customers/${activeStop.customerId}`)}>پروفایل</button>
            </div>
          ) : visitState === 'idle' ? (
            <div className="vr-actions">
              <button type="button" className="primary" disabled={actionBusy === 'start'} onClick={() => void startVisit()}><RouteArrowIcon /> شروع بازدید</button>
              <button type="button" onClick={callActiveCustomer}><PhoneIcon /> تماس</button>
              <button type="button" onClick={() => onNavigate(`/visitor/customers/${activeStop.customerId}`)}><StoreIcon /> پروفایل</button>
            </div>
          ) : null}

          {visitState === 'active' ? (
            <div className="vr-visit-running">
              <div><span>{activeDraftId ? 'بازدید فعال · پیش‌نویس سفارش موجود' : 'بازدید در حال انجام'}</span><strong ref={visitTimerRef}>{activeVisit ? formatTimer(Math.max(0, Math.floor((Date.now() - activeVisit.startedAt) / 1000))) : '00:00'}</strong></div>
              {activeDraftId ? (
                <button type="button" onClick={() => onNavigate(`/visitor/orders?customer=${activeStop.customerId}&visit=${encodeURIComponent(activeVisit?.id ?? '')}&draft=${encodeURIComponent(activeDraftId)}&returnTo=${encodeURIComponent(`/visitor/route?customer=${activeStop.customerId}`)}`)}>ادامه سفارش</button>
              ) : <button type="button" onClick={() => setVisitState('outcome')}>توقف و ثبت نتیجه</button>}
            </div>
          ) : null}
        </section>

        <section className={`vr-stops ng-layer-surface ${showStops ? 'expanded' : 'collapsed'}`} data-depth={showStops ? '1' : '0'}>
          <button type="button" className="vr-stops-toggle" aria-expanded={showStops} onClick={() => setShowStops((value) => !value)}>
            <span><strong>ایستگاه‌های مسیر</strong><small>{sortedRouteStops.length.toLocaleString('fa-IR')} مشتری · {routeSummary.remaining.toLocaleString('fa-IR')} باقی‌مانده</small></span>
            <b>{showStops ? 'بستن' : 'نمایش همه'}</b>
          </button>
          {showStops ? (
          <div className="vr-stop-list">
            {sortedRouteStops.map((stop, index) => (
              <button type="button" key={stop.stopId} className={`vr-stop-row ${stop.status} ${selectedCustomerId === stop.customerId ? 'selected' : ''}`} onClick={() => selectStop(stop.customerId)}>
                <span className="vr-index">{stop.status === 'visited' ? <CheckCircleIcon /> : stop.status === 'skipped' ? '×' : index + 1}</span>
                <span className="vr-stop-copy"><strong>{stop.name}</strong><small>{joinRouteMeta(stop.area, stop.distance)}</small></span>
                <span className="vr-stop-state">{stop.status === 'visited' ? (stop.outcome === 'order-draft' ? 'سفارش پیش‌نویس' : 'ویزیت شد') : stop.status === 'active' ? 'بعدی' : stop.status === 'unlocated' ? 'بدون موقعیت' : stop.status === 'skipped' ? 'عدم ویزیت' : stop.eta}</span>
              </button>
            ))}
          </div>
          ) : null}
        </section>

        {visitState === 'outcome' ? (
          <div className="vr-sheet-backdrop" role="presentation" onClick={() => setVisitState('active')}>
            <section className="vr-outcome-sheet" role="dialog" aria-modal="true" aria-label="ثبت نتیجه بازدید" onClick={(event) => event.stopPropagation()}>
              <div className="vr-sheet-handle" />
              <h2>نتیجه بازدید</h2>
              <p>{activeStop.name} · زمان <span ref={outcomeTimerRef}>{activeVisit ? formatTimer(Math.max(0, Math.floor((Date.now() - activeVisit.startedAt) / 1000))) : '00:00'}</span></p>
              <div className="vr-outcomes">
                <button type="button" className={outcome === 'sale' ? 'active' : ''} onClick={() => { setOutcome('sale'); setSelectedReasonId('') }}><CartIcon /><span>فروش / سفارش</span></button>
                <button type="button" className={outcome === 'no-order' ? 'active' : ''} onClick={() => { setOutcome('no-order'); setSelectedReasonId('') }}><CheckCircleIcon /><span>بدون سفارش</span></button>
                <button type="button" className={outcome === 'no-visit' ? 'active danger' : 'danger'} onClick={() => { setOutcome('no-visit'); setSelectedReasonId('') }}><PhoneIcon /><span>عدم ویزیت</span></button>
              </div>
              {outcomeKey ? (
                <VisitorPicker
                  className="vr-reason"
                  label="دلیل ثبت در NGT"
                  value={selectedReasonId}
                  placeholder="انتخاب دلیل"
                  disabled={actionBusy === 'complete'}
                  options={outcomeReasons.map((reason) => ({ value: reason.id, label: reason.title }))}
                  onChange={setSelectedReasonId}
                />
              ) : null}

              <button

                type="button"

                className="vr-confirm"

                disabled={Boolean(actionBusy) || Boolean(outcomeKey && !selectedReasonId)}

                onClick={() => void confirmOutcome()}

              >

                {actionBusy === 'complete' ? 'در حال ثبت...' : outcome === 'sale' ? 'ادامه به سفارش' : 'ثبت نتیجه'}

              </button>
            </section>
          </div>
        ) : null}

        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        <BottomDock
          ariaLabel="ناوبری ویزیتور"
          items={[
            { key: 'home', label: 'خانه', icon: <HomeIcon />, onClick: () => onNavigate('/visitor/home') },
            { key: 'route', label: 'مسیر', icon: <MapIcon />, active: true, onClick: () => onNavigate('/visitor/route') },
            { key: 'customers', label: 'مشتریان', icon: <UserGroupIcon />, onClick: () => onNavigate('/visitor/customers') },
            { key: 'reports', label: 'گزارش‌ها', icon: <ChartIcon />, onClick: () => onNavigate('/visitor/reports') },
          ]}
          primary={{
            label: 'سفارش',
            icon: <PlusIcon />,
            onClick: () => onNavigate(`/visitor/orders?customer=${activeStop.customerId}${activeVisit ? `&visit=${encodeURIComponent(activeVisit.id)}` : ''}`),
          }}
        />
      </div>
    </main>
  )
}
