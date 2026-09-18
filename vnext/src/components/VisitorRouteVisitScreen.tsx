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
import { completeServerVisit, getVisitPolicy, getVisitWorkspace, startServerVisit, type SellerVisitPolicyResponse, type SellerVisitWorkspaceResponse } from '../api/neginApi'
import { VisitorNeshanMap } from './VisitorNeshanMap'
import { VisitorPicker } from './VisitorPicker'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import '../design-system/living/index.css'
import '../styles/living-ui-pilot.css'

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
  const { unreadCount } = useVisitorNotifications()
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
  const [selectedCustomerId, setSelectedCustomerId] = useState(() => requestedCustomerId ?? activeVisit?.customerId ?? activeCustomerId ?? routeStops[0]?.customerId ?? '1')
  const [visitState, setVisitState] = useState<VisitState>(() => activeVisit ? 'active' : 'idle')
  const [elapsed, setElapsed] = useState(() => activeVisit ? Math.max(0, Math.floor((Date.now() - activeVisit.startedAt) / 1000)) : 0)
  const [outcome, setOutcome] = useState<'sale' | 'no-order' | 'no-visit'>('sale')
  const [notice, setNotice] = useState<string | null>(null)
  const [policy, setPolicy] = useState<SellerVisitPolicyResponse | null>(null)
  const [workspace, setWorkspace] = useState<SellerVisitWorkspaceResponse | null>(null)
  const [selectedReasonId, setSelectedReasonId] = useState('')
  const [actionBusy, setActionBusy] = useState<'start' | 'complete' | ''>('')
  const [mapRecenterNonce, setMapRecenterNonce] = useState(0)
  const [planOrderCustomerIds, setPlanOrderCustomerIds] = useState<string[]>([])
  const outcomeDialogRef = useRef<HTMLElement | null>(null)

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
  const displayedScore = Number(workspace?.analytics.visit_score ?? activeStop?.score ?? 0)

  useEffect(() => {
    if (!activeRouteId || !activeStop?.customerId) {
      setPolicy(null)
      setWorkspace(null)
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

    void getVisitWorkspace(activeRouteId, activeStop.customerId)
      .then((nextWorkspace) => {
        if (!cancelled) setWorkspace(nextWorkspace)
      })
      .catch(() => {
        if (!cancelled) setWorkspace(null)
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
      if (visitState === 'active') setVisitState('idle')
      setElapsed(0)
      return
    }
    setSelectedCustomerId(activeVisit.customerId)
    setVisitState((current) => current === 'outcome' ? current : 'active')
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - activeVisit.startedAt) / 1000)))
    tick()
    const interval = window.setInterval(tick, 1000)
    return () => window.clearInterval(interval)
  }, [activeVisit, visitState])

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
      setElapsed(0)
      flash('ویزیت با تأیید Backend شروع شد.')
      void getVisitWorkspace(activeRouteId, activeStop.customerId).then(setWorkspace).catch(() => undefined)
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
      <main className="vh-page vh-live-ui ng-living-root vr-app-page" dir="rtl" data-live-ui="unified">
        <div className="vh-shell vr-shell">
          <header className="vh-header">
            <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
              <span className="vh-avatar">و</span>
              <span className="vh-profile-copy"><strong>{profile?.full_name || profile?.username || 'ویزیتور'}</strong><small><PinIcon /> {profile?.branch || profile?.sales_line || 'حساب سازمانی'}</small></span>
              <ChevronLeftIcon />
            </button>
            <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}><BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}</button>
            <div className="vh-brand" dir="ltr"><img src="/assets/neginai-logo-transparent.png" alt="Negin AI" /><div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div></div>
          </header>

          {offDay ? (
            <section className="vr-offday-card ng-living-surface" data-living-state="ambient">
              <div className="vr-offday-icon"><ClockIcon /></div>
              <div className="vr-offday-copy"><span>تقویم رسمی NGT</span><h1>امروز روز کاری نیست</h1><p>{workCalendar?.date ? `${workCalendar.date} · ` : ''}برای امروز DayPath یا Tour فعالی تعریف نشده و این وضعیت خطا محسوب نمی‌شود.</p></div>
              <div className="vr-offday-rail"><span><small>مسیرهای تخصیص‌یافته</small><strong>{routes.length.toLocaleString('fa-IR')}</strong></span><span><small>روز کاری سپری‌شده</small><strong>{Number(workCalendar?.elapsed_working_days ?? 0).toLocaleString('fa-IR')}</strong></span><span><small>روز کاری باقی‌مانده</small><strong>{Number(workCalendar?.remaining_working_days ?? 0).toLocaleString('fa-IR')}</strong></span></div>
              <div className="vr-offday-actions"><button type="button" className="primary" onClick={() => onNavigate('/visitor/customers')}>مرور مشتریان</button><button type="button" onClick={() => onNavigate('/visitor/home')}>بازگشت به خانه</button></div>
            </section>
          ) : (
            <section className={error ? 'vh-live-state error' : 'vh-live-state'} role={error ? 'alert' : 'status'}>
              <div><strong>{loading ? 'در حال دریافت مسیر واقعی…' : error ? 'مسیر امروز دریافت نشد' : 'برای امروز ایستگاهی وجود ندارد'}</strong><span>{error || 'اطلاعات Seller Workspace در حال بررسی است.'}</span></div>
              {error ? <button type="button" onClick={() => void reload()}>تلاش دوباره</button> : null}
            </section>
          )}

          <nav className="vh-nav" aria-label="ناوبری ویزیتور">
            <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
            <button className="vh-nav-item active" type="button" aria-current="page"><MapIcon /><span>مسیر</span></button>
            <button className="vh-order" type="button" disabled={offDay} onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
            <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
            <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
          </nav>
        </div>
      </main>
    )
  }

  return (
    <main className="vh-page vh-live-ui ng-living-root vr-app-page" dir="rtl" data-live-ui="unified">
      <div className="vh-shell vr-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy"><strong>{profile?.full_name || profile?.username || 'ویزیتور'}</strong><small><PinIcon /> {profile?.branch || profile?.sales_line || 'حساب سازمانی'}</small></span>
            <ChevronLeftIcon />
          </button>
          <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}><BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}</button>
          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vr-route-bar ng-living-surface">
          <div><span>مسیر فعال · {activeRouteTitle || 'NGT'}</span><strong>{routeSummary.resolved} تعیین‌تکلیف · {routeSummary.remaining} باقی‌مانده</strong></div>
          <div className="vr-route-bar-actions"><button type="button" className="vr-ai-open" onClick={() => onNavigate(`/visitor/ai?context=route&customer=${activeStop.customerId}${activeVisit ? `&visit=${activeVisit.id}` : ``}`)}>Negin AI</button><div className="vr-progress"><strong>{routeSummary.progress}٪</strong><small>پیشرفت</small></div></div>
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
              <div><span>{activeDraftId ? 'بازدید فعال · پیش‌نویس سفارش موجود' : 'بازدید در حال انجام'}</span><strong>{formatTimer(elapsed)}</strong></div>
              {activeDraftId ? (
                <button type="button" onClick={() => onNavigate(`/visitor/orders?customer=${activeStop.customerId}&visit=${encodeURIComponent(activeVisit?.id ?? '')}&draft=${encodeURIComponent(activeDraftId)}&returnTo=${encodeURIComponent(`/visitor/route?customer=${activeStop.customerId}`)}`)}>ادامه سفارش</button>
              ) : <button type="button" onClick={() => setVisitState('outcome')}>توقف و ثبت نتیجه</button>}
            </div>
          ) : null}
        </section>

        <section className={`vr-stops ng-living-surface ${showStops ? 'expanded' : 'collapsed'}`}>
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
              <p>{activeStop.name} · زمان {formatTimer(elapsed)}</p>
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

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item active" type="button" aria-current="page" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate(`/visitor/orders?customer=${activeStop.customerId}${activeVisit ? `&visit=${encodeURIComponent(activeVisit.id)}` : ''}`)}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
