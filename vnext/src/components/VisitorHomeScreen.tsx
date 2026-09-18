import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import {
  getSellerDistributionInProgress,
  getSellerPortfolioOpenInvoices,
  getSellerPortfolioReturnedCheques,
  getSellerVoucherReturnReport,
  type SellerDistributionInProgressResponse,
  type SellerPortfolioOpenInvoicesResponse,
  type SellerPortfolioReturnedChequesResponse,
  type SellerVoucherReturnReportResponse,
} from '../api/neginApi'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import {
  AiSparkIcon,
  BellIcon,
  ChartIcon,
  ChequeIcon,
  ChevronLeftIcon,
  ClockIcon,
  HomeIcon,
  InvoiceIcon,
  MapIcon,
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

type HomePerformance = {
  openInvoices: SellerPortfolioOpenInvoicesResponse | null
  returnedCheques: SellerPortfolioReturnedChequesResponse | null
  distribution: SellerDistributionInProgressResponse | null
  voucherReturn: SellerVoucherReturnReportResponse | null
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

function compactRial(value: number | null | undefined) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '—'
  return `${new Intl.NumberFormat('fa-IR', { notation: 'compact', maximumFractionDigits: 1 }).format(amount)} ریال`
}

export function VisitorHomeScreen({ onNavigate }: Props) {
  const { attentionCount, highestSeverity } = useVisitorNotifications()
  const { profile } = useVisitorAuth()
  const {
    error,
    liveAssignment,
    workCalendar,
    targetPulse,
    offDay,
    reload,
  } = useVisitorLiveData()
  const { routeStops, routeSummary } = useVisitorWorkflow()
  const [now, setNow] = useState(() => new Date())
  const [performance, setPerformance] = useState<HomePerformance>({
    openInvoices: null,
    returnedCheques: null,
    distribution: null,
    voucherReturn: null,
  })
  const [performanceLoading, setPerformanceLoading] = useState(true)
  const [performanceError, setPerformanceError] = useState<string | null>(null)
  const [performanceRevision, setPerformanceRevision] = useState(0)

  const livingUiEnabled = typeof window !== 'undefined'
    && new URLSearchParams(window.location.search).get('liveui') !== '0'
    && localStorage.getItem('neginai.pilot.living-ui') !== '0'

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    let cancelled = false
    setPerformanceLoading(true)
    setPerformanceError(null)
    void Promise.allSettled([
      getSellerPortfolioOpenInvoices(),
      getSellerPortfolioReturnedCheques(),
      getSellerDistributionInProgress(),
      getSellerVoucherReturnReport(),
    ]).then((results) => {
      if (cancelled) return
      const [openInvoices, returnedCheques, distribution, voucherReturn] = results
      const next: HomePerformance = {
        openInvoices: openInvoices.status === 'fulfilled' ? openInvoices.value : null,
        returnedCheques: returnedCheques.status === 'fulfilled' ? returnedCheques.value : null,
        distribution: distribution.status === 'fulfilled' ? distribution.value : null,
        voucherReturn: voucherReturn.status === 'fulfilled' ? voucherReturn.value : null,
      }
      setPerformance(next)
      if (results.every((result) => result.status === 'rejected')) {
        setPerformanceError('خلاصه عملکرد از ERP دریافت نشد.')
      }
    }).finally(() => {
      if (!cancelled) setPerformanceLoading(false)
    })
    return () => { cancelled = true }
  }, [performanceRevision])

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
    ? 'KPI هدف در حال اعتبارسنجی'
    : !targetPulse?.configured
      ? 'هدف ماه تنظیم نشده'
      : targetPulse.status === 'ahead'
        ? 'جلوتر از ریتم هدف'
        : targetPulse.status === 'behind'
          ? 'عقب‌تر از ریتم هدف'
          : targetPulse.status === 'on_track'
            ? 'هم‌ریتم با هدف'
            : 'هدف فروش فعال'

  const nextStop = routeStops.find((stop) => ['active', 'pending'].includes(stop.status))
    ?? routeStops.find((stop) => stop.status === 'unlocated')

  const performanceItems = useMemo(() => ([
    {
      label: 'فاکتور ماه',
      value: targetPulse ? targetPulse.actual_invoice_count.toLocaleString('fa-IR') : '—',
      hint: 'ثبت‌شده در ERP',
      icon: <InvoiceIcon />,
      tone: 'gold',
    },
    {
      label: 'مانده فاکتور باز',
      value: performance.openInvoices ? compactRial(performance.openInvoices.open_invoice_remaining) : '—',
      hint: performance.openInvoices ? `${performance.openInvoices.customer_count.toLocaleString('fa-IR')} مشتری` : 'در حال دریافت',
      icon: <ChartIcon />,
      tone: performance.openInvoices?.open_invoice_remaining ? 'attention' : 'mint',
    },
    {
      label: 'چک برگشتی',
      value: performance.returnedCheques ? performance.returnedCheques.cheque_count.toLocaleString('fa-IR') : '—',
      hint: performance.returnedCheques?.cheque_count ? 'نیازمند توجه' : 'بدون مورد فعال',
      icon: <ChequeIcon />,
      tone: performance.returnedCheques?.cheque_count ? 'danger' : 'mint',
    },
    {
      label: 'توزیع در جریان',
      value: performance.distribution ? performance.distribution.invoice_count.toLocaleString('fa-IR') : '—',
      hint: performance.distribution?.invoice_count ? 'فاکتور در توزیع' : 'موردی ثبت نشده',
      icon: <StoreIcon />,
      tone: 'mint',
    },
  ]), [performance, targetPulse])

  const fullReturnCount = performance.voucherReturn?.full_returned_count ?? 0

  const nextAction = attentionCount > 0
    ? {
        eyebrow: 'نیازمند توجه',
        title: `${attentionCount.toLocaleString('fa-IR')} هشدار عملیاتی`,
        meta: highestSeverity === 'critical' ? 'حداقل یک مورد بحرانی نیازمند تأیید است.' : 'موارد مهم را قبل از ادامه روز بررسی کن.',
        icon: <BellIcon />,
        action: 'بررسی هشدارها',
        path: '/visitor/notifications',
        tone: 'danger',
      }
    : offDay
      ? {
          eyebrow: 'اقدام پیشنهادی',
          title: 'مرور عملکرد و مشتریان',
          meta: 'امروز طبق تقویم NGT روز کاری نیست؛ از زمان آزاد برای مرور عملکرد استفاده کن.',
          icon: <ChartIcon />,
          action: 'مشاهده گزارش‌ها',
          path: '/visitor/reports',
          tone: 'calm',
        }
      : nextStop
        ? {
            eyebrow: 'اقدام بعدی',
            title: nextStop.name,
            meta: `پیشرفت مسیر ${routeSummary.progress.toLocaleString('fa-IR')}٪ · ${routeSummary.remaining.toLocaleString('fa-IR')} ایستگاه باقی‌مانده`,
            icon: <RouteArrowIcon />,
            action: 'ادامه کار',
            path: `/visitor/route?customer=${nextStop.customerId}`,
            tone: 'gold',
          }
        : {
            eyebrow: 'وضعیت روز',
            title: liveAssignment ? 'برنامه عملیاتی امروز تکمیل شده' : 'مسیر فعالی برای امروز نیست',
            meta: liveAssignment ? 'برای تحلیل نتیجه امروز گزارش عملکرد را ببین.' : 'وضعیت تخصیص روز را در ماژول مسیر بررسی کن.',
            icon: <MapIcon />,
            action: liveAssignment ? 'گزارش عملکرد' : 'بررسی مسیر',
            path: liveAssignment ? '/visitor/reports' : '/visitor/route',
            tone: 'calm',
          }

  const targetAngle = `${(targetAchievement ?? 0) * 3.6}deg`
  const workingDayText = workCalendar
    ? `${workCalendar.elapsed_working_days.toLocaleString('fa-IR')} از ${workCalendar.total_working_days.toLocaleString('fa-IR')} روز کاری`
    : 'تقویم کاری در حال دریافت'

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

          <button className={`vh-bell ng-living-interactive ${highestSeverity ? `severity-${highestSeverity}` : ''}`} data-severity={highestSeverity ?? 'none'} type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />
            {attentionCount ? <b key={`${attentionCount}-${highestSeverity ?? 'none'}`} className="ng-living-reactive">{attentionCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vh-performance-hero ng-living-surface" data-state={performanceLoading ? 'loading' : performanceError ? 'attention' : 'ready'}>
          <div className="vh-performance-head">
            <div>
              <span className="vh-performance-eyebrow"><i /> عملکرد من · زنده</span>
              <h1>سلام{profile?.full_name ? `، ${profile.full_name}` : ''}</h1>
              <p>{targetSemanticReady && targetPulse?.configured ? targetStateLabel : 'نمای کلی عملکرد فروش، ریسک و فعالیت‌های مهم'}</p>
            </div>
            <button className="vh-performance-ring ng-living-live" type="button" onClick={() => onNavigate('/visitor/reports')} style={{ '--performance-angle': targetAngle } as CSSProperties} aria-label="مشاهده گزارش عملکرد">
              <span className="vh-performance-orbit" aria-hidden="true" />
              <strong>{targetAchievement != null ? `${targetAchievement.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪` : 'KPI'}</strong>
              <small>{targetAchievement != null ? 'تحقق هدف' : 'در اعتبارسنجی'}</small>
            </button>
          </div>

          <div className="vh-performance-time">
            <ClockIcon />
            <span><strong>{weekday}</strong><small>{persianDate}</small></span>
            <span className="vh-live-clock"><time dateTime={now.toISOString()}>{currentTime}</time><LiveSeconds /></span>
            <em>{workingDayText}</em>
          </div>

          <div className="vh-target-strip" data-ready={targetSemanticReady ? 'true' : 'false'}>
            <span>
              <small>هدف فروش</small>
              <strong>{targetAchievement != null && targetPulse?.achievement_percent != null ? `${targetPulse.achievement_percent.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪` : 'در حال اعتبارسنجی'}</strong>
            </span>
            <span>
              <small>فروش ماه</small>
              <strong>{targetSemanticReady ? compactRial(targetPulse?.actual_sales_rial) : 'نمایش پس از تأیید KPI'}</strong>
            </span>
            <span>
              <small>باقی‌مانده هدف</small>
              <strong>{targetSemanticReady && targetPulse?.remaining_target_rial != null ? compactRial(targetPulse.remaining_target_rial) : '—'}</strong>
            </span>
          </div>
        </section>

        {(error || performanceError) ? (
          <section className="vh-live-state error" role="alert">
            <div><strong>بخشی از داده زنده در دسترس نیست</strong><span>{error || performanceError}</span></div>
            <button type="button" onClick={() => { void reload(); setPerformanceRevision((value) => value + 1) }}>تلاش دوباره</button>
          </section>
        ) : null}

        <section className="vh-performance-rail ng-living-surface" aria-label="خلاصه عملکرد">
          <div className="vh-performance-section-head">
            <div><ChartIcon /><strong>خلاصه عملکرد</strong></div>
            <button type="button" onClick={() => onNavigate('/visitor/reports')}>جزئیات <ChevronLeftIcon /></button>
          </div>
          <div className="vh-performance-metrics">
            {performanceItems.map((item) => (
              <button key={item.label} type="button" className={`vh-performance-metric tone-${item.tone} ng-living-interactive`} onClick={() => onNavigate('/visitor/reports')}>
                <span className="vh-performance-metric-icon">{item.icon}</span>
                <span><small>{item.label}</small><strong className="ng-living-reactive">{performanceLoading ? '…' : item.value}</strong><em>{item.hint}</em></span>
              </button>
            ))}
          </div>
          {fullReturnCount > 0 ? (
            <button className="vh-performance-alert ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/reports')}>
              <span><strong>{fullReturnCount.toLocaleString('fa-IR')} برگشت کامل</strong><small>در گزارش ماه جاری ثبت شده است.</small></span><ChevronLeftIcon />
            </button>
          ) : null}
        </section>

        <section className={`vh-next-action ng-living-surface tone-${nextAction.tone}`} data-living-state="active">
          <span className="vh-next-action-icon">{nextAction.icon}</span>
          <span className="vh-next-action-copy">
            <small>{nextAction.eyebrow}</small>
            <strong>{nextAction.title}</strong>
            <em>{nextAction.meta}</em>
          </span>
          <button className="ng-living-interactive" type="button" onClick={() => onNavigate(nextAction.path)}>
            {nextAction.action}<ChevronLeftIcon />
          </button>
        </section>

        <section className="vh-home-intelligence ng-living-surface">
          <div>
            <span className="vh-home-intelligence-icon"><AiSparkIcon /></span>
            <span><small>Negin AI Coach</small><strong>تحلیل عملکرد و اقدام پیشنهادی</strong><em>از داده‌های واقعی همین حساب برای پیدا کردن فرصت و ریسک استفاده کن.</em></span>
          </div>
          <button type="button" className="ng-living-interactive" onClick={() => onNavigate('/visitor/ai?context=home&prompt=performance')}>تحلیل عملکرد <ChevronLeftIcon /></button>
        </section>

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
