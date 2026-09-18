import { useEffect, useState, type ReactNode } from 'react'
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
type HomeLayer = 'performance' | 'risk' | 'today' | 'intelligence'
type DetailKey =
  | 'invoice-count'
  | 'sales'
  | 'target'
  | 'open-invoices'
  | 'returned-cheques'
  | 'returns'
  | 'working-day'
  | 'route'
  | 'distribution'
  | 'alerts'
  | 'ai'

type HomePerformance = {
  openInvoices: SellerPortfolioOpenInvoicesResponse | null
  returnedCheques: SellerPortfolioReturnedChequesResponse | null
  distribution: SellerDistributionInProgressResponse | null
  voucherReturn: SellerVoucherReturnReportResponse | null
}

type LayerItem = {
  key: DetailKey
  label: string
  value: string
  meta: string
  icon: ReactNode
  tone?: 'gold' | 'mint' | 'danger' | 'blue'
}

function compactRial(value: number | null | undefined) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '—'
  return `${new Intl.NumberFormat('fa-IR', { notation: 'compact', maximumFractionDigits: 1 }).format(amount)} ریال`
}

export function VisitorHomeScreen({ onNavigate }: Props) {
  const { attentionCount, highestSeverity } = useVisitorNotifications()
  const { profile } = useVisitorAuth()
  const { error, liveAssignment, workCalendar, targetPulse, offDay, reload } = useVisitorLiveData()
  const { routeStops, routeSummary } = useVisitorWorkflow()
  const [now, setNow] = useState(() => new Date())
  const [layer, setLayer] = useState<HomeLayer | null>(null)
  const [detail, setDetail] = useState<DetailKey | null>(null)
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
      setPerformance({
        openInvoices: openInvoices.status === 'fulfilled' ? openInvoices.value : null,
        returnedCheques: returnedCheques.status === 'fulfilled' ? returnedCheques.value : null,
        distribution: distribution.status === 'fulfilled' ? distribution.value : null,
        voucherReturn: voucherReturn.status === 'fulfilled' ? voucherReturn.value : null,
      })
      if (results.every((result) => result.status === 'rejected')) setPerformanceError('خلاصه عملکرد از ERP دریافت نشد.')
    }).finally(() => {
      if (!cancelled) setPerformanceLoading(false)
    })
    return () => { cancelled = true }
  }, [performanceRevision])

  useEffect(() => {
    const handlePop = () => {
      if (detail) {
        setDetail(null)
        return
      }
      if (layer) setLayer(null)
    }
    window.addEventListener('popstate', handlePop)
    return () => window.removeEventListener('popstate', handlePop)
  }, [detail, layer])

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
    ? targetPulse.achievement_percent
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
  const fullReturnCount = performance.voucherReturn?.full_returned_count ?? 0
  const routeSummaryLabel = offDay
    ? 'امروز روز کاری نیست'
    : liveAssignment
      ? `${routeSummary.progress.toLocaleString('fa-IR')}٪ مسیر انجام شده`
      : 'مسیر فعالی برای امروز نیست'
  const performanceSummary = targetPulse
    ? `${targetPulse.actual_invoice_count.toLocaleString('fa-IR')} فاکتور ماه`
    : performanceLoading ? 'در حال دریافت عملکرد…' : 'عملکرد در دسترس نیست'
  const performanceMeta = targetSemanticReady && targetPulse?.configured && targetAchievement != null
    ? `${targetAchievement.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪ تحقق هدف`
    : 'KPI هدف در اعتبارسنجی'
  const riskSummary = performance.openInvoices
    ? `${compactRial(performance.openInvoices.open_invoice_remaining)} مانده باز`
    : performanceLoading ? 'در حال دریافت وضعیت مالی…' : 'وضعیت مالی در دسترس نیست'
  const riskMeta = performance.returnedCheques
    ? `${performance.returnedCheques.cheque_count.toLocaleString('fa-IR')} چک برگشتی`
    : 'ریسک مالی در حال دریافت'
  const intelligenceSummary = attentionCount
    ? `${attentionCount.toLocaleString('fa-IR')} هشدار فعال`
    : 'بدون هشدار بحرانی'
  const intelligenceMeta = attentionCount
    ? (highestSeverity === 'critical' ? 'حداقل یک مورد بحرانی' : 'Alert Center نیازمند بررسی')
    : 'Negin AI آماده تحلیل'

  function openLayer(next: HomeLayer) {
    window.history.pushState({ neginHomeDepth: 1 }, '', window.location.href)
    setLayer(next)
    setDetail(null)
  }

  function openDetail(next: DetailKey) {
    window.history.pushState({ neginHomeDepth: 2 }, '', window.location.href)
    setDetail(next)
  }

  function goBack() {
    window.history.back()
  }

  const layerMeta: Record<HomeLayer, { title: string; subtitle: string; icon: ReactNode }> = {
    performance: { title: 'عملکرد', subtitle: 'فروش، هدف و خروجی ماه', icon: <ChartIcon /> },
    risk: { title: 'ریسک مالی', subtitle: 'فاکتور باز، چک و برگشت', icon: <ChequeIcon /> },
    today: { title: 'عملیات امروز', subtitle: 'روز کاری، مسیر و توزیع', icon: <ClockIcon /> },
    intelligence: { title: 'هوش و هشدار', subtitle: 'Alert Center و Negin AI', icon: <AiSparkIcon /> },
  }

  const layerItems: Record<HomeLayer, LayerItem[]> = {
    performance: [
      {
        key: 'invoice-count',
        label: 'فاکتور ماه',
        value: targetPulse ? targetPulse.actual_invoice_count.toLocaleString('fa-IR') : '—',
        meta: 'ثبت‌شده در ERP',
        icon: <InvoiceIcon />,
        tone: 'gold',
      },
      {
        key: 'sales',
        label: 'فروش ماه',
        value: targetSemanticReady ? compactRial(targetPulse?.actual_sales_rial) : 'در انتظار تأیید KPI',
        meta: targetSemanticReady ? 'فروش تأییدشده در قرارداد KPI' : 'Semantic Validation هنوز بسته نشده',
        icon: <ChartIcon />,
        tone: 'blue',
      },
      {
        key: 'target',
        label: 'هدف فروش',
        value: targetAchievement != null ? `${targetAchievement.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪` : 'در اعتبارسنجی',
        meta: targetStateLabel,
        icon: <RouteArrowIcon />,
        tone: targetAchievement != null ? 'mint' : 'gold',
      },
    ],
    risk: [
      {
        key: 'open-invoices',
        label: 'مانده فاکتور باز',
        value: performance.openInvoices ? compactRial(performance.openInvoices.open_invoice_remaining) : '—',
        meta: performance.openInvoices ? `${performance.openInvoices.customer_count.toLocaleString('fa-IR')} مشتری` : 'در حال دریافت',
        icon: <InvoiceIcon />,
        tone: 'gold',
      },
      {
        key: 'returned-cheques',
        label: 'چک برگشتی',
        value: performance.returnedCheques ? performance.returnedCheques.cheque_count.toLocaleString('fa-IR') : '—',
        meta: performance.returnedCheques?.cheque_count ? 'نیازمند توجه' : 'بدون مورد فعال',
        icon: <ChequeIcon />,
        tone: performance.returnedCheques?.cheque_count ? 'danger' : 'mint',
      },
      {
        key: 'returns',
        label: 'برگشت کامل',
        value: fullReturnCount.toLocaleString('fa-IR'),
        meta: fullReturnCount ? 'ثبت‌شده در ماه جاری' : 'موردی ثبت نشده',
        icon: <StoreIcon />,
        tone: fullReturnCount ? 'danger' : 'mint',
      },
    ],
    today: [
      {
        key: 'working-day',
        label: 'تقویم کاری',
        value: offDay ? 'روز غیرکاری' : weekday,
        meta: workCalendar
          ? `${workCalendar.elapsed_working_days.toLocaleString('fa-IR')} از ${workCalendar.total_working_days.toLocaleString('fa-IR')} روز کاری`
          : 'تقویم NGT در حال دریافت',
        icon: <ClockIcon />,
        tone: offDay ? 'blue' : 'mint',
      },
      {
        key: 'route',
        label: 'مسیر',
        value: offDay ? 'غیرفعال' : liveAssignment ? `${routeSummary.progress.toLocaleString('fa-IR')}٪` : '—',
        meta: offDay ? 'جزئیات در ماژول مسیر' : liveAssignment ? `${routeSummary.remaining.toLocaleString('fa-IR')} ایستگاه باقی‌مانده` : 'Route فعال نیست',
        icon: <MapIcon />,
        tone: 'gold',
      },
      {
        key: 'distribution',
        label: 'توزیع در جریان',
        value: performance.distribution ? performance.distribution.invoice_count.toLocaleString('fa-IR') : '—',
        meta: performance.distribution?.invoice_count ? 'فاکتور در فرآیند توزیع' : 'موردی ثبت نشده',
        icon: <StoreIcon />,
        tone: 'mint',
      },
    ],
    intelligence: [
      {
        key: 'alerts',
        label: 'هشدارهای عملیاتی',
        value: attentionCount.toLocaleString('fa-IR'),
        meta: highestSeverity === 'critical' ? 'حداقل یک مورد بحرانی نیازمند تأیید است' : 'Alert Center زنده',
        icon: <BellIcon />,
        tone: attentionCount ? 'danger' : 'mint',
      },
      {
        key: 'ai',
        label: 'Negin AI Coach',
        value: 'تحلیل زنده',
        meta: 'فرصت، ریسک و اقدام پیشنهادی',
        icon: <AiSparkIcon />,
        tone: 'gold',
      },
    ],
  }

  const detailMap: Record<DetailKey, {
    title: string
    value: string
    description: string
    meta?: string
    icon: ReactNode
    tone: 'gold' | 'mint' | 'danger' | 'blue'
    action: string
    path: string
  }> = {
    'invoice-count': {
      title: 'فاکتورهای ماه',
      value: targetPulse ? targetPulse.actual_invoice_count.toLocaleString('fa-IR') : '—',
      description: 'تعداد فاکتورهای ثبت‌شده برای این فروشنده در ماه جاری.',
      meta: 'برای تحلیل جزئی‌تر وارد گزارش‌ها شو.',
      icon: <InvoiceIcon />,
      tone: 'gold',
      action: 'گزارش فروش',
      path: '/visitor/reports',
    },
    sales: {
      title: 'فروش ماه',
      value: targetSemanticReady ? compactRial(targetPulse?.actual_sales_rial) : 'در انتظار تأیید KPI',
      description: targetSemanticReady
        ? 'فروش ماه بر اساس قرارداد معنایی تأییدشده.'
        : 'عدد رسمی فروش تا بسته‌شدن Semantic Validation در Home منتشر نمی‌شود.',
      icon: <ChartIcon />,
      tone: 'blue',
      action: 'مشاهده گزارش',
      path: '/visitor/reports',
    },
    target: {
      title: 'هدف فروش',
      value: targetAchievement != null ? `${targetAchievement.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪` : 'در اعتبارسنجی',
      description: targetStateLabel,
      meta: targetSemanticReady ? 'وضعیت نسبت به هدف ماه' : 'از نمایش KPI اثبات‌نشده جلوگیری شده است.',
      icon: <RouteArrowIcon />,
      tone: targetAchievement != null ? 'mint' : 'gold',
      action: 'جزئیات عملکرد',
      path: '/visitor/reports',
    },
    'open-invoices': {
      title: 'مانده فاکتور باز',
      value: performance.openInvoices ? compactRial(performance.openInvoices.open_invoice_remaining) : '—',
      description: performance.openInvoices
        ? `${performance.openInvoices.customer_count.toLocaleString('fa-IR')} مشتری دارای مانده فاکتور باز هستند.`
        : 'داده ERP در حال دریافت است.',
      icon: <InvoiceIcon />,
      tone: 'gold',
      action: 'تحلیل مالی',
      path: '/visitor/reports',
    },
    'returned-cheques': {
      title: 'چک‌های برگشتی',
      value: performance.returnedCheques ? performance.returnedCheques.cheque_count.toLocaleString('fa-IR') : '—',
      description: performance.returnedCheques?.cheque_count ? 'ریسک فعال مالی؛ قبل از فروش بعدی بررسی شود.' : 'چک برگشتی فعالی ثبت نشده است.',
      icon: <ChequeIcon />,
      tone: performance.returnedCheques?.cheque_count ? 'danger' : 'mint',
      action: attentionCount ? 'هشدارها' : 'گزارش مالی',
      path: attentionCount ? '/visitor/notifications' : '/visitor/reports',
    },
    returns: {
      title: 'برگشت کامل',
      value: fullReturnCount.toLocaleString('fa-IR'),
      description: fullReturnCount ? 'برگشت‌های کامل ثبت‌شده در گزارش ماه جاری.' : 'برگشت کامل فعالی ثبت نشده است.',
      icon: <StoreIcon />,
      tone: fullReturnCount ? 'danger' : 'mint',
      action: 'گزارش برگشتی',
      path: '/visitor/reports',
    },
    'working-day': {
      title: 'تقویم کاری',
      value: offDay ? 'روز غیرکاری' : weekday,
      description: workCalendar
        ? `${workCalendar.elapsed_working_days.toLocaleString('fa-IR')} روز کاری سپری شده و ${workCalendar.remaining_working_days.toLocaleString('fa-IR')} روز باقی مانده است.`
        : 'تقویم کاری NGT در حال دریافت است.',
      meta: persianDate,
      icon: <ClockIcon />,
      tone: offDay ? 'blue' : 'mint',
      action: 'بررسی مسیر',
      path: '/visitor/route',
    },
    route: {
      title: 'وضعیت مسیر',
      value: offDay ? 'روز غیرکاری' : liveAssignment ? `${routeSummary.progress.toLocaleString('fa-IR')}٪` : 'بدون Route فعال',
      description: offDay
        ? 'جزئیات مسیرهای تخصیص‌یافته در ماژول مسیر قابل مرور است.'
        : nextStop
          ? `اقدام بعدی: ${nextStop.name} · ${routeSummary.remaining.toLocaleString('fa-IR')} ایستگاه باقی مانده`
          : 'وضعیت کامل Route را در ماژول مسیر بررسی کن.',
      icon: <MapIcon />,
      tone: 'gold',
      action: 'ورود به مسیر',
      path: '/visitor/route',
    },
    distribution: {
      title: 'توزیع در جریان',
      value: performance.distribution ? performance.distribution.invoice_count.toLocaleString('fa-IR') : '—',
      description: performance.distribution?.invoice_count
        ? 'فاکتورهایی که در فرآیند توزیع قرار دارند.'
        : 'در حال حاضر فاکتوری در فرآیند توزیع ثبت نشده است.',
      icon: <StoreIcon />,
      tone: 'mint',
      action: 'گزارش عملیات',
      path: '/visitor/reports',
    },
    alerts: {
      title: 'هشدارهای عملیاتی',
      value: attentionCount.toLocaleString('fa-IR'),
      description: highestSeverity === 'critical'
        ? 'حداقل یک هشدار بحرانی نیازمند Acknowledge است.'
        : attentionCount
          ? 'هشدارهای مهم را قبل از ادامه عملیات بررسی کن.'
          : 'هشدار مهم فعالی وجود ندارد.',
      icon: <BellIcon />,
      tone: attentionCount ? 'danger' : 'mint',
      action: 'باز کردن Alert Center',
      path: '/visitor/notifications',
    },
    ai: {
      title: 'Negin AI Coach',
      value: 'تحلیل زنده',
      description: 'تحلیل فرصت فروش، ریسک مالی و Next Best Action بر اساس داده‌های همین حساب.',
      icon: <AiSparkIcon />,
      tone: 'gold',
      action: 'شروع تحلیل',
      path: '/visitor/ai?context=home&prompt=performance',
    },
  }

  const currentDetail = detail ? detailMap[detail] : null
  const depth = detail ? 2 : layer ? 1 : 0

  return (
    <main
      className={`vh-page vh-depth-page ng-living-root${livingUiEnabled ? ' vh-live-ui' : ''}`}
      dir="rtl"
      data-live-ui={livingUiEnabled ? 'pilot' : 'off'}
      data-living-ui={livingUiEnabled ? 'on' : 'off'}
      data-home-depth={depth}
    >
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

          <button
            className={`vh-bell ng-living-interactive ${highestSeverity ? `severity-${highestSeverity}` : ''}`}
            data-severity={highestSeverity ?? 'none'}
            type="button"
            aria-label="اعلان‌ها"
            onClick={() => onNavigate('/visitor/notifications')}
          >
            <BellIcon />
            {attentionCount ? <b key={`${attentionCount}-${highestSeverity ?? 'none'}`} className="ng-living-reactive">{attentionCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vhd-stage ng-depth-stage" data-depth={depth}>
          <span className="vhd-backplane vhd-backplane-one ng-depth-backplane" data-plane="1" aria-hidden="true" />
          <span className="vhd-backplane vhd-backplane-two ng-depth-backplane" data-plane="2" aria-hidden="true" />

          {depth === 0 ? (
            <div className="vhd-layer vhd-layer-root">
              <section className="vhd-overview ng-layer-surface ng-living-surface">
                <div>
                  <span className="vhd-live"><i /> وضعیت جامع · زنده</span>
                  <h1>سلام{profile?.full_name ? `، ${profile.full_name}` : ''}</h1>
                  <p>از هر بخش وارد لایه بعدی شو؛ جزئیات در سطح اول نمایش داده نمی‌شوند.</p>
                </div>
                <div className="vhd-date">
                  <strong>{currentTime}</strong>
                  <span>{weekday}</span>
                  <small>{persianDate}</small>
                </div>
              </section>

              {(error || performanceError) ? (
                <button
                  type="button"
                  className="vhd-inline-alert ng-living-interactive"
                  onClick={() => { void reload(); setPerformanceRevision((value) => value + 1) }}
                >
                  <span><strong>بخشی از داده زنده در دسترس نیست</strong><small>برای تلاش دوباره لمس کن</small></span>
                  <ChevronLeftIcon />
                </button>
              ) : null}

              <div className="vhd-portals" aria-label="دسته‌های اصلی خانه">
                <button className="vhd-portal ng-portal-surface ng-living-interactive" data-tone="gold" type="button" onClick={() => openLayer('performance')}>
                  <span className="vhd-portal-icon ng-portal-accent"><ChartIcon /></span>
                  <span className="vhd-portal-copy"><small>عملکرد</small><strong>{performanceSummary}</strong><em>{performanceMeta}</em></span>
                  <ChevronLeftIcon />
                </button>

                <button className="vhd-portal ng-portal-surface ng-living-interactive" data-tone="danger" type="button" onClick={() => openLayer('risk')}>
                  <span className="vhd-portal-icon ng-portal-accent"><ChequeIcon /></span>
                  <span className="vhd-portal-copy"><small>ریسک مالی</small><strong>{riskSummary}</strong><em>{riskMeta}</em></span>
                  <ChevronLeftIcon />
                </button>

                <button className="vhd-portal ng-portal-surface ng-living-interactive" data-tone="blue" type="button" onClick={() => openLayer('today')}>
                  <span className="vhd-portal-icon ng-portal-accent"><ClockIcon /></span>
                  <span className="vhd-portal-copy"><small>عملیات امروز</small><strong>{offDay ? 'امروز روز غیرکاری است' : routeSummaryLabel}</strong><em>{offDay ? 'مرور مسیرهای تخصیص‌یافته' : nextStop ? `بعدی: ${nextStop.name}` : 'Route و توزیع'}</em></span>
                  <ChevronLeftIcon />
                </button>

                <button className="vhd-portal ng-portal-surface ng-living-interactive" data-tone="mint" type="button" onClick={() => openLayer('intelligence')}>
                  <span className="vhd-portal-icon ng-portal-accent"><AiSparkIcon /></span>
                  <span className="vhd-portal-copy"><small>هوش و هشدار</small><strong>{intelligenceSummary}</strong><em>{intelligenceMeta}</em></span>
                  <ChevronLeftIcon />
                </button>
              </div>
            </div>
          ) : null}

          {depth === 1 && layer ? (
            <div className="vhd-layer vhd-layer-section ng-layer-surface">
              <header className="vhd-layer-head">
                <button type="button" className="vhd-back ng-living-interactive" onClick={goBack} aria-label="بازگشت"><ChevronLeftIcon /></button>
                <span className="vhd-layer-head-icon">{layerMeta[layer].icon}</span>
                <span><small>خانه · {layerMeta[layer].title}</small><strong>{layerMeta[layer].title}</strong><em>{layerMeta[layer].subtitle}</em></span>
              </header>

              <div className="vhd-layer-items">
                {layerItems[layer].map((item) => (
                  <button
                    type="button"
                    key={item.key}
                    className="vhd-layer-item ng-portal-surface ng-living-interactive" data-tone={item.tone ?? 'blue'}
                    onClick={() => openDetail(item.key)}
                  >
                    <span className="vhd-layer-item-icon ng-portal-accent">{item.icon}</span>
                    <span className="vhd-layer-item-copy"><small>{item.label}</small><strong>{performanceLoading ? '…' : item.value}</strong><em>{item.meta}</em></span>
                    <ChevronLeftIcon />
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {depth === 2 && currentDetail ? (
            <div className="vhd-layer vhd-layer-detail ng-layer-surface" data-tone={currentDetail.tone}>
              <header className="vhd-layer-head">
                <button type="button" className="vhd-back ng-living-interactive" onClick={goBack} aria-label="بازگشت"><ChevronLeftIcon /></button>
                <span className="vhd-layer-head-icon">{currentDetail.icon}</span>
                <span><small>{layer ? `${layerMeta[layer].title} · جزئیات` : 'جزئیات'}</small><strong>{currentDetail.title}</strong><em>نمای متمرکز این شاخص</em></span>
              </header>

              <section className="vhd-detail-card ng-detail-surface ng-living-surface">
                <span className="vhd-detail-icon ng-portal-accent">{currentDetail.icon}</span>
                <small>{currentDetail.title}</small>
                <strong>{currentDetail.value}</strong>
                <p>{currentDetail.description}</p>
                {currentDetail.meta ? <em>{currentDetail.meta}</em> : null}
              </section>

              <button type="button" className="vhd-detail-action ng-living-interactive" onClick={() => onNavigate(currentDetail.path)}>
                {currentDetail.action}<ChevronLeftIcon />
              </button>
            </div>
          ) : null}
        </section>

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item active ng-living-interactive" type="button" aria-current="page" onClick={() => { setLayer(null); setDetail(null) }}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
