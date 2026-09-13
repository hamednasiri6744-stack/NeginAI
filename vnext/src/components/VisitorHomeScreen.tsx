import { useState } from 'react'
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

type Props = { onNavigate: (path: string) => void }

type Kpi = {
  label: string
  value: string
  hint: string
  icon: React.ReactNode
  tone?: 'gold' | 'mint' | 'danger'
}


export function VisitorHomeScreen({ onNavigate }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const { profile } = useVisitorAuth()
  const { loading, error, activeRouteTitle, liveAssignment, reload } = useVisitorLiveData()
  const [notice, setNotice] = useState<string | null>(null)
  const { routeStops, routeSummary } = useVisitorWorkflow()
  const nextStop = routeStops.find((stop) => ['active', 'pending'].includes(stop.status)) ?? routeStops.find((stop) => stop.status === 'unlocated')
  const nextStopMeta = nextStop
    ? [nextStop.distance, nextStop.eta]
      .map((value) => value.trim())
      .filter((value) => value.length > 0 && !/^[-\u2013\u2014]+$/.test(value))
      .join(' \u00b7 ') || nextStop.eta
    : '\u2014'
  const kpis: Kpi[] = [
    { label: 'مسیر امروز', value: activeRouteTitle || '—', hint: liveAssignment ? 'NGT زنده' : 'بدون تخصیص', icon: <MapIcon />, tone: 'gold' },
    { label: 'مشتریان مسیر', value: String(routeSummary.total), hint: `${routeSummary.remaining} باقی‌مانده`, icon: <StoreIcon />, tone: 'mint' },
    { label: 'بازدیدها', value: `${routeSummary.visited} / ${routeSummary.total}`, hint: `${routeSummary.progress}٪ مسیر`, icon: <CheckCircleIcon />, tone: 'gold' },
    { label: 'فروش امروز', value: '—', hint: 'گزارش فروش هنوز متصل نشده', icon: <ChartIcon />, tone: 'danger' },
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
    <main className="vh-page" dir="rtl">
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

          <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />
            {unreadCount ? <b>{unreadCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div>
              <strong>Negin <span>AI</span></strong>
              <small>VISITOR</small>
            </div>
          </div>
        </header>

        <section className="vh-command" aria-labelledby="visitor-greeting">
          <div className="vh-command-head">
            <div>
              <span className="vh-eyebrow">امروز</span>
              <h1 id="visitor-greeting">سلام {profile?.full_name ? `، ${profile.full_name}` : ''}</h1>
              <p>{loading ? 'در حال دریافت مسیر واقعی امروز…' : error ? 'داده زنده مسیر در دسترس نیست.' : `${routeSummary.visited} بازدید تعیین‌تکلیف شده و ${routeSummary.remaining} ایستگاه باقی مانده.`}</p>
            </div>
            <div className="vh-progress" style={{ '--vh-progress': `${routeSummary.progress}%` } as React.CSSProperties} aria-label={`${routeSummary.progress} درصد مسیر انجام شده`}>
              <span>{routeSummary.progress}٪</span>
            </div>
          </div>

          <div className="vh-command-actions">
            <button className="vh-primary" type="button" onClick={() => onNavigate('/visitor/route')}>
              <RouteArrowIcon />
              شروع مسیر
            </button>
            <button className="vh-secondary" type="button" onClick={() => onNavigate('/visitor/ai?context=home')}>
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
            <article className={`vh-kpi vh-kpi-${kpi.tone ?? 'gold'}`} key={kpi.label}>
              <span className="vh-kpi-icon">{kpi.icon}</span>
              <span className="vh-kpi-label">{kpi.label}</span>
              <strong className={index === 0 ? 'vh-kpi-route-value' : undefined}>{kpi.value}</strong>
              <small>{kpi.hint}</small>
            </article>
          ))}
        </section>

        <section className="vh-next-card">
          <div className="vh-section-title">
            <div><PinIcon /><strong>بازدید بعدی</strong></div>
            <span>{nextStop?.eta ?? '—'}</span>
          </div>

          <div className="vh-next-body">
            <span className="vh-store-icon"><StoreIcon /></span>
            <div className="vh-next-copy">
              <strong>{nextStop?.name ?? 'مسیر امروز تکمیل شده'}</strong>
              <span>{nextStop ? nextStop.area : 'ایستگاه فعالی باقی نمانده'}</span>
              <small>{nextStopMeta}</small>
            </div>
            <button className="vh-mini-action" type="button" aria-label="شروع مسیریابی" onClick={() => nextStop ? onNavigate(`/visitor/route?customer=${nextStop.customerId}`) : flash('ایستگاه فعالی باقی نمانده')}>
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
                <button className="vh-task" type="button" key={`${task.time}-${task.title}`} onClick={() => onNavigate(`/visitor/route?customer=${task.customerId}`)}>
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
            <button className="vh-insight" type="button" onClick={() => onNavigate('/visitor/ai?context=home&prompt=sales-opportunity')}>
              <span className="vh-insight-icon"><ChartIcon /></span>
              <span><strong>فرصت فروش</strong><small>تحلیل زنده را از Negin AI بپرس.</small></span>
              <ChevronLeftIcon />
            </button>
            <button className="vh-insight" type="button" onClick={() => onNavigate('/visitor/ai?context=home&prompt=stock')}>
              <span className="vh-insight-icon"><BoxIcon /></span>
              <span><strong>تأمین موجودی</strong><small>هشدارهای موجودی را از داده زنده بررسی کن.</small></span>
              <ChevronLeftIcon />
            </button>
          </article>
        </section>

        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item active" type="button" aria-current="page" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
