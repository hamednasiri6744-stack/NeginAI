import { useEffect, useState } from 'react'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import {
  AiSparkIcon,
  BellIcon,
  BoxIcon,
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

import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import '../design-system/living/index.css'
import '../styles/living-ui-pilot.css'

type Props = { onNavigate: (path: string) => void }

type Kpi = {
  label: string
  value: string
  hint: string
  icon: React.ReactNode
  tone?: 'gold' | 'mint' | 'danger'
}

function LiveSeconds() {
  const [second, setSecond] = useState(() => new Date())
  useEffect(() => {
    const timer = window.setInterval(() => setSecond(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const value = new Intl.DateTimeFormat('fa-IR', { second: '2-digit', timeZone: 'Asia/Tehran' }).format(second)
  return <small className="vh-live-seconds" aria-hidden="true">:{value}</small>
}


export function VisitorHomeScreen({ onNavigate }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const { profile } = useVisitorAuth()
  const { loading, error, activeRouteTitle, liveAssignment, workCalendar, targetPulse, reload } = useVisitorLiveData()
  const [notice, setNotice] = useState<string | null>(null)
  const [now, setNow] = useState(() => new Date())
  const { routeStops, routeSummary } = useVisitorWorkflow()
  const livingUiEnabled = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('liveui') !== '0' && localStorage.getItem('neginai.pilot.living-ui') !== '0'
  const liveState = loading ? 'syncing' : error ? 'error' : 'ready'
  const commandLivingState = loading ? 'updating' : error ? 'attention' : liveAssignment ? 'live' : 'ambient'
  const routeAngle = `${Math.max(0, Math.min(100, routeSummary.progress)) * 3.6}deg`

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  const weekday = new Intl.DateTimeFormat('fa-IR', { weekday: 'long', timeZone: 'Asia/Tehran' }).format(now)
  const persianDate = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'Asia/Tehran',
  }).format(now)
  const currentTime = new Intl.DateTimeFormat('fa-IR', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Tehran',
  }).format(now)
  const targetSemanticStatus = targetPulse?.semantic_status?.toUpperCase() ?? ''
  const targetSemanticReady = ['CANONICAL', 'VALIDATED', 'FACT'].includes(targetSemanticStatus)
  const targetAchievement = targetSemanticReady && targetPulse?.configured && targetPulse.achievement_percent != null
    ? Math.max(0, Math.min(100, targetPulse.achievement_percent))
    : null
  const targetStateLabel = !targetSemanticReady
    ? 'در حال اعتبارسنجی KPI'
    : !targetPulse?.configured
      ? 'هدف ماه تنظیم نشده'
      : targetPulse.status === 'ahead'
        ? 'جلوتر از ریتم هدف'
        : targetPulse.status === 'behind'
          ? 'عقب‌تر از ریتم هدف'
          : targetPulse.status === 'on_track'
            ? 'هم‌ریتم با هدف'
            : 'هدف فروش فعال'
  const nextStop = routeStops.find((stop) => ['active', 'pending'].includes(stop.status)) ?? routeStops.find((stop) => stop.status === 'unlocated')
  const nextStopMeta = nextStop
    ? [nextStop.distance, nextStop.eta]
      .map((value) => value.trim())
      .filter((value) => value.length > 0 && !/^[-\u2013\u2014]+$/.test(value))
      .join(' · ') || nextStop.eta
    : '—'
  const unlocatedCount = routeStops.filter((stop) => stop.status === 'unlocated').length
  const kpis: Kpi[] = [
    { label: 'مسیر امروز', value: activeRouteTitle || '—', hint: liveAssignment ? 'NGT زنده' : 'بدون تخصیص', icon: <MapIcon />, tone: 'gold' },
    { label: 'مشتریان مسیر', value: String(routeSummary.total), hint: `${routeSummary.remaining} باقی‌مانده`, icon: <StoreIcon />, tone: 'mint' },
    { label: 'بازدیدها', value: `${routeSummary.visited} / ${routeSummary.total}`, hint: `${routeSummary.progress}٪ مسیر`, icon: <CheckCircleIcon />, tone: 'gold' },
    { label: 'نیازمند موقعیت', value: String(unlocatedCount), hint: unlocatedCount ? 'برای مسیریابی ثبت شود' : 'همه آماده مسیریابی', icon: <PinIcon />, tone: unlocatedCount ? 'danger' : 'mint' },
  ]
  const tasks = routeStops.filter((stop) => !['visited', 'skipped'].includes(stop.status)).slice(0, 3).map((stop, index) => ({
    customerId: stop.customerId,
    time: stop.eta,
    title: stop.name,
    meta: index === 0 ? 'بازدید بعدی' : stop.status === 'unlocated' ? 'نیازمند ثبت موقعیت' : 'در مسیر امروز',
    icon: index === 0 ? <StoreIcon /> : index === 1 ? <CartIcon /> : <PhoneIcon />,
  }))

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }

  return (
    <main className={`vh-page ng-living-root${livingUiEnabled ? ' vh-live-ui' : ''}`} dir="rtl" data-live-ui={livingUiEnabled ? 'pilot' : 'off'} data-living-ui={livingUiEnabled ? 'on' : 'off'}>
      <div className="vh-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || 'ویزیتور'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || 'حساب سازمانی'}</small>
            </span>
            <ChevronLeftIcon />
          </button>

          <button className="vh-bell ng-living-interactive" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />
            {unreadCount ? <b key={unreadCount} className="ng-living-reactive">{unreadCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div>
              <strong>Negin <span>AI</span></strong>
              <small>VISITOR</small>
            </div>
          </div>
        </header>

        <section className="vh-command ng-living-surface ng-living-live" aria-labelledby="visitor-greeting" data-live-state={liveState} data-living-state={commandLivingState}>
          <div className="vh-command-head">
            <div>
              <span className="vh-eyebrow">امروز</span>
              <h1 id="visitor-greeting">سلام {profile?.full_name ? `، ${profile.full_name}` : ''}</h1>
              <p>{loading ? 'در حال دریافت مسیر واقعی امروز…' : error ? 'داده زنده مسیر در دسترس نیست.' : `${routeSummary.visited} بازدید تعیین‌تکلیف شده و ${routeSummary.remaining} ایستگاه باقی مانده.`}</p>
            </div>
            <div className="vh-progress ng-living-live" style={{ '--route-progress': `${routeSummary.progress}%`, '--route-angle': routeAngle } as React.CSSProperties} aria-label={`${routeSummary.progress} درصد مسیر انجام شده`}>
              <i className="vh-progress-beacon" aria-hidden="true" />
              <span key={routeSummary.progress} className="ng-living-reactive">{routeSummary.progress}٪</span>
            </div>
          </div>

          <div className="vh-day-status" aria-label="زمان و تقویم کاری">
            <div className="vh-day-datetime">
              <ClockIcon />
              <span><strong>{weekday}</strong><small>{persianDate}</small></span>
              <span className="vh-live-clock"><time dateTime={now.toISOString()}>{currentTime}</time><LiveSeconds /></span>
            </div>
            <div className="vh-day-metric vh-day-calendar">
              <span>تقویم کاری</span>
              <strong key={workCalendar ? `${workCalendar.elapsed_working_days}-${workCalendar.remaining_working_days}` : 'loading'} className="ng-living-reactive">
                <b>{workCalendar ? workCalendar.elapsed_working_days.toLocaleString('fa-IR') : '—'}</b><i>/</i><b>{workCalendar ? workCalendar.remaining_working_days.toLocaleString('fa-IR') : '—'}</b>
              </strong>
              <small>{workCalendar ? `سپری‌شده / مانده · ${workCalendar.total_working_days.toLocaleString('fa-IR')} روز` : 'در حال دریافت از NGT'}</small>
            </div>
            <div
              className="vh-day-metric vh-target-pulse"
              data-target-state={targetSemanticReady ? (targetPulse?.status ?? 'configured') : 'validation'}
              style={{ '--target-progress': `${targetAchievement ?? 0}%` } as React.CSSProperties}
            >
              <span>هدف فروش</span>
              <strong key={targetPulse?.achievement_percent ?? targetStateLabel} className="ng-living-reactive">
                {targetAchievement != null && targetPulse?.achievement_percent != null ? `${targetPulse.achievement_percent.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪` : '—'}
              </strong>
              <small>{targetStateLabel}</small>
              <em aria-hidden="true"><i /></em>
            </div>
          </div>

          <div className="vh-command-actions">
            <button className="vh-primary ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/route')}>
              <RouteArrowIcon />
              شروع مسیر
            </button>
            <button className="vh-secondary ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/ai?context=home')}>
              <AiSparkIcon />
              Negin AI
            </button>
          </div>
        </section>

        {error ? (
          <section className="vh-live-state error" role="alert">
            <div><strong>اتصال داده زنده برقرار نشد</strong><span>{error}</span></div>
            <button type="button" onClick={() => void reload()}>تلاش دوباره</button>
          </section>
        ) : loading ? (
          <section className="vh-live-state" role="status"><strong>در حال همگام‌سازی با NGT…</strong><span>مسیر و مشتریان واقعی در حال دریافت هستند.</span></section>
        ) : null}

        <section className="vh-kpis" aria-label="خلاصه امروز">
          {kpis.map((kpi, index) => (
            <article className={`vh-kpi vh-kpi-${kpi.tone ?? 'gold'} ng-living-surface`} key={kpi.label} data-live={index === 0 && liveAssignment ? 'true' : undefined} data-living-state={index === 0 && liveAssignment ? 'live' : 'idle'}>
              <span className="vh-kpi-icon">{kpi.icon}</span>
              <span className="vh-kpi-label">{kpi.label}</span>
              <strong key={`${kpi.label}-${kpi.value}`} className={`${index === 0 ? 'vh-kpi-route-value ' : ''}ng-living-reactive`}>{kpi.value}</strong>
              <small key={`${kpi.label}-${kpi.hint}`} className="ng-living-reactive-soft">{kpi.hint}</small>
            </article>
          ))}
        </section>

        <section className="vh-next-card ng-living-surface ng-living-live" data-live={nextStop ? 'true' : undefined} data-living-state={nextStop ? 'active' : 'idle'}>
          <div className="vh-section-title">
            <div><PinIcon /><strong>بازدید بعدی</strong></div>
            <span>{nextStop?.eta ?? '—'}</span>
          </div>

          <div key={nextStop?.customerId ?? 'none'} className="vh-next-body ng-living-panel-change">
            <span className="vh-store-icon"><StoreIcon /></span>
            <div className="vh-next-copy">
              <strong>{nextStop?.name ?? 'مسیر امروز تکمیل شده'}</strong>
              <span>{nextStop ? nextStop.area : 'ایستگاه فعالی باقی نمانده'}</span>
              <small>{nextStopMeta}</small>
            </div>
            <button className="vh-mini-action ng-living-interactive" type="button" aria-label="شروع مسیریابی" onClick={() => nextStop ? onNavigate(`/visitor/route?customer=${nextStop.customerId}`) : flash('ایستگاه فعالی باقی نمانده')}>
              <RouteArrowIcon />
            </button>
          </div>
        </section>

        <section className="vh-two-col">
          <article className="vh-panel">
            <div className="vh-section-title">
              <div><ClockIcon /><strong>برنامه امروز</strong></div>
              <button type="button" onClick={() => onNavigate('/visitor/route')}>همه</button>
            </div>
            <div className="vh-task-list">
              {tasks.map((task, index) => (
                <button className="vh-task ng-living-interactive" type="button" key={`${task.time}-${task.title}`} onClick={() => onNavigate(`/visitor/route?customer=${task.customerId}`)}>
                  <span className={`vh-task-state ${index === 0 ? 'active' : ''}`}>{task.icon}</span>
                  <span className="vh-task-copy"><strong>{task.title}</strong><small>{task.meta}</small></span>
                  <time>{task.time}</time>
                </button>
              ))}
            </div>
          </article>

          <article className="vh-panel vh-ai-panel">
            <div className="vh-section-title">
              <div><AiSparkIcon /><strong>پیشنهادها</strong></div>
            </div>
            <button className="vh-insight ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/ai?context=home&prompt=sales-opportunity')}>
              <span className="vh-insight-icon"><ChartIcon /></span>
              <span><strong>فرصت فروش</strong><small>تحلیل زنده را از Negin AI بپرس.</small></span>
              <ChevronLeftIcon />
            </button>
            <button className="vh-insight ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/ai?context=home&prompt=stock')}>
              <span className="vh-insight-icon"><BoxIcon /></span>
              <span><strong>تأمین موجودی</strong><small>هشدارهای موجودی را از داده زنده بررسی کن.</small></span>
              <ChevronLeftIcon />
            </button>
          </article>
        </section>

        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item active ng-living-interactive" type="button" aria-current="page" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
