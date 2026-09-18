import { useEffect, useState } from 'react'
import {
  getSellerPortfolioReturnedCheques,
  type SellerPortfolioReturnedChequesResponse,
} from '../api/neginApi'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import {
  AiSparkIcon,
  BellIcon,
  ChartIcon,
  ChequeIcon,
  ChevronLeftIcon,
  ClockIcon,
  HomeIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  RouteArrowIcon,
  StoreIcon,
  UserGroupIcon,
} from './Icons'
import { AppHeader, BottomDock, InsightCard } from '../design-system/components'
import '../design-system/living/index.css'
import '../styles/living-ui-pilot.css'
import '../styles/design-system-atlas-home.css'

type Props = { onNavigate: (path: string) => void }

export function VisitorHomeScreen({ onNavigate }: Props) {
  const { attentionCount, highestSeverity } = useVisitorNotifications()
  const { profile } = useVisitorAuth()
  const {
    error,
    liveAssignment,
    workCalendar,
    targetPulse,
    offDay,
    stale,
    lastSyncedAt,
    reload,
  } = useVisitorLiveData()
  const { routeStops, routeSummary } = useVisitorWorkflow()

  const [now, setNow] = useState(() => new Date())
  const [returnedCheques, setReturnedCheques] = useState<SellerPortfolioReturnedChequesResponse | null>(null)
  const [riskLoading, setRiskLoading] = useState(true)
  const [riskError, setRiskError] = useState<string | null>(null)
  const [riskRevision, setRiskRevision] = useState(0)

  const livingUiEnabled = typeof window !== 'undefined'
    && new URLSearchParams(window.location.search).get('liveui') !== '0'
    && localStorage.getItem('neginai.pilot.living-ui') !== '0'

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    let cancelled = false
    setRiskLoading(true)
    setRiskError(null)

    void getSellerPortfolioReturnedCheques()
      .then((result) => {
        if (!cancelled) setReturnedCheques(result)
      })
      .catch((caught) => {
        if (!cancelled) {
          setReturnedCheques(null)
          setRiskError(caught instanceof Error ? caught.message : 'وضعیت ریسک مالی دریافت نشد.')
        }
      })
      .finally(() => {
        if (!cancelled) setRiskLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [riskRevision])

  const weekday = new Intl.DateTimeFormat('fa-IR', {
    weekday: 'long',
    timeZone: 'Asia/Tehran',
  }).format(now)

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

  const targetValue = !targetSemanticReady
    ? '—'
    : targetAchievement != null
      ? `${targetAchievement.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪`
      : targetPulse?.configured
        ? 'فعال'
        : '—'

  const targetLabel = !targetSemanticReady
    ? 'هدف · در اعتبارسنجی'
    : !targetPulse?.configured
      ? 'هدف · تنظیم نشده'
      : targetPulse?.status === 'ahead'
        ? 'هدف · جلوتر از ریتم'
        : targetPulse?.status === 'behind'
          ? 'هدف · عقب‌تر از ریتم'
          : targetPulse?.status === 'on_track'
            ? 'هدف · هم‌ریتم'
            : 'هدف ماه'

  const nextStop = routeStops.find((stop) => ['active', 'pending'].includes(stop.status))
    ?? routeStops.find((stop) => stop.status === 'unlocated')

  const operationalAction = offDay
    ? {
        eyebrow: 'آماده‌سازی روز کاری بعد',
        title: 'کاتالوگ و موجودی فروش را مرور کن',
        body: 'امروز روز غیرکاری NGT است؛ بدون شروع ویزیت، زمینه فروش روز بعد را آماده کن.',
        action: 'مرور فروش',
        path: '/visitor/orders',
        tone: 'info' as const,
        icon: <StoreIcon />,
      }
    : liveAssignment && nextStop
      ? {
          eyebrow: 'گام عملیاتی',
          title: `حرکت به ${nextStop.name}`,
          body: `${routeSummary.remaining.toLocaleString('fa-IR')} ایستگاه باقی مانده · ${routeSummary.progress.toLocaleString('fa-IR')}٪ مسیر تعیین‌تکلیف شده`,
          action: 'ادامه مسیر',
          path: '/visitor/route',
          tone: 'gold' as const,
          icon: <RouteArrowIcon />,
        }
      : liveAssignment
        ? {
            eyebrow: 'وضعیت مسیر',
            title: 'مسیر امروز تعیین‌تکلیف شده است',
            body: 'جزئیات مسیر و نتایج ویزیت‌ها در Field Execution باقی می‌ماند.',
            action: 'مشاهده مسیر',
            path: '/visitor/route',
            tone: 'success' as const,
            icon: <MapIcon />,
          }
        : {
            eyebrow: 'برنامه امروز',
            title: 'مسیر فعالی برای امروز ثبت نشده است',
            body: 'مشتریان تخصیص‌یافته را مرور کن؛ Route فقط در ماژول Field Execution مدیریت می‌شود.',
            action: 'مشتریان',
            path: '/visitor/customers',
            tone: 'info' as const,
            icon: <UserGroupIcon />,
          }

  const elapsedWorkingDays = Number(workCalendar?.elapsed_working_days ?? 0)
  const totalWorkingDays = Number(workCalendar?.total_working_days ?? 0)
  const remainingWorkingDays = Number(workCalendar?.remaining_working_days ?? 0)
  const returnedChequeCount = Number(returnedCheques?.cheque_count ?? 0)

  const retryLiveData = () => {
    void reload()
    setRiskRevision((value) => value + 1)
  }

  return (
    <main
      className={`vh-page vh-depth-page ng-living-root${livingUiEnabled ? ' vh-live-ui' : ''}`}
      dir="rtl"
      data-live-ui={livingUiEnabled ? 'pilot' : 'off'}
      data-living-ui={livingUiEnabled ? 'on' : 'off'}
      data-design-system="atlas-v1"
      data-home-depth="0"
    >
      <div className="vh-shell">
        <AppHeader
          avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}
          title={profile?.full_name || profile?.username || 'ویزیتور'}
          subtitle={profile?.branch || profile?.sales_line || 'حساب سازمانی'}
          subtitleIcon={<PinIcon />}
          profileTrailing={<ChevronLeftIcon />}
          onProfileClick={() => onNavigate('/visitor/profile')}
          action={(
            <button
              className={`vh-bell ng-living-interactive ${highestSeverity ? `severity-${highestSeverity}` : ''}`}
              data-severity={highestSeverity ?? 'none'}
              type="button"
              aria-label="اعلان‌ها"
              onClick={() => onNavigate('/visitor/notifications')}
            >
              <BellIcon />
              {attentionCount ? (
                <b
                  key={`${attentionCount}-${highestSeverity ?? 'none'}`}
                  className="ng-living-reactive"
                >
                  {attentionCount}
                </b>
              ) : null}
            </button>
          )}
        />

        <section className="vhd-stage vhd-mission-stage" data-depth="0">
          <div className="vhd-layer vhd-layer-root vhd-cockpit-root">
            <section className="vhd-cockpit ng-layer-surface ng-living-surface" data-tone="gold">
              <span className="vhd-cockpit-ambient" aria-hidden="true" />

              <div className="vhd-cockpit-head">
                <div>
                  <span className="vhd-live"><i /> NeginAI LIVE</span>
                  <h1>سلام{profile?.full_name ? `، ${profile.full_name}` : ''}</h1>
                  <p>
                    {offDay
                      ? 'امروز روز غیرکاری است؛ اپ در حالت آماده‌سازی فروش قرار دارد.'
                      : liveAssignment
                        ? `${routeSummary.remaining.toLocaleString('fa-IR')} اقدام مسیر هنوز باز است.`
                        : 'Route فعالی برای امروز ثبت نشده است.'}
                  </p>
                </div>

                <div className="vhd-date vhd-date-live">
                  <strong>{currentTime}</strong>
                  <span>{weekday}</span>
                  <small>{persianDate}</small>
                </div>
              </div>

              <div className="vhd-mission-meta" aria-label="وضعیت روز کاری و هدف">
                <span className="vhd-mission-chip">
                  <ClockIcon />
                  <span>
                    <small>روز کاری</small>
                    <strong>
                      {workCalendar
                        ? `${elapsedWorkingDays.toLocaleString('fa-IR')} / ${totalWorkingDays.toLocaleString('fa-IR')}`
                        : 'در حال دریافت'}
                    </strong>
                    <em>{workCalendar ? `${remainingWorkingDays.toLocaleString('fa-IR')} روز باقی‌مانده` : 'NGT Calendar'}</em>
                  </span>
                </span>

                <button
                  type="button"
                  className={`vhd-mission-chip vhd-target-chip ng-living-interactive${targetSemanticReady ? '' : ' is-gated'}`}
                  onClick={() => onNavigate('/visitor/reports')}
                >
                  <ChartIcon />
                  <span>
                    <small>{targetLabel}</small>
                    <strong>{targetValue}</strong>
                    <em>{targetSemanticReady ? 'جزئیات در Analysis' : 'تا تأیید Semantic KPI منتشر نمی‌شود'}</em>
                  </span>
                </button>
              </div>

              <div className="vhd-route-energy" aria-label="پیشرفت عملیات امروز">
                <span>
                  <b style={{ width: `${Math.max(4, Math.min(100, offDay ? 4 : routeSummary.progress))}%` }} />
                </span>
                <small>
                  {offDay
                    ? 'Route امروز غیرفعال'
                    : liveAssignment
                      ? `${routeSummary.progress.toLocaleString('fa-IR')}٪ مسیر تکمیل شده`
                      : 'بدون Route فعال'}
                </small>
              </div>
            </section>

            {(error || riskError) ? (
              <button
                type="button"
                className="vhd-inline-alert ng-living-interactive"
                onClick={retryLiveData}
              >
                <span>
                  <strong>
                    {stale
                      ? 'حالت آفلاین · آخرین داده ذخیره‌شده'
                      : 'بخشی از داده زنده در دسترس نیست'}
                  </strong>
                  <small>
                    {stale && lastSyncedAt
                      ? `آخرین همگام‌سازی ${new Date(lastSyncedAt).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })} · برای تلاش دوباره لمس کن`
                      : 'برای تلاش دوباره لمس کن'}
                  </small>
                </span>
                <ChevronLeftIcon />
              </button>
            ) : null}

            <InsightCard
              className="vhd-next-insight"
              icon={operationalAction.icon}
              eyebrow={operationalAction.eyebrow}
              title={operationalAction.title}
              body={operationalAction.body}
              actionLabel={operationalAction.action}
              tone={operationalAction.tone}
              onAction={() => onNavigate(operationalAction.path)}
            />

            <section className="vhd-pulse-deck ng-layer-surface" aria-label="سیگنال‌های امروز">
              <div className="vhd-pulse-title">
                <span><i /> سیگنال‌های امروز</span>
                <small>NGT · Varanegar · Alert Center</small>
              </div>

              <div className="vhd-pulse-grid">
                <button
                  type="button"
                  className="vhd-pulse-cell ng-living-interactive"
                  onClick={() => onNavigate('/visitor/route')}
                >
                  <span><MapIcon /></span>
                  <strong>{offDay ? '—' : routeSummary.remaining.toLocaleString('fa-IR')}</strong>
                  <small>ایستگاه باز</small>
                </button>

                <button
                  type="button"
                  className={`vhd-pulse-cell ng-living-interactive${targetSemanticReady ? '' : ' gated'}`}
                  onClick={() => onNavigate('/visitor/reports')}
                >
                  <span><ChartIcon /></span>
                  <strong>{targetValue}</strong>
                  <small>هدف ماه</small>
                </button>

                <button
                  type="button"
                  className={`vhd-pulse-cell ng-living-interactive ${attentionCount ? 'attention' : ''}`}
                  onClick={() => onNavigate('/visitor/notifications')}
                >
                  <span><BellIcon /></span>
                  <strong>{attentionCount.toLocaleString('fa-IR')}</strong>
                  <small>هشدار فعال</small>
                </button>

                <button
                  type="button"
                  className={`vhd-pulse-cell ng-living-interactive ${returnedChequeCount ? 'danger' : ''}`}
                  onClick={() => onNavigate('/visitor/reports')}
                >
                  <span><ChequeIcon /></span>
                  <strong>{riskLoading ? '…' : returnedChequeCount.toLocaleString('fa-IR')}</strong>
                  <small>چک برگشتی</small>
                </button>
              </div>
            </section>

            <button
              type="button"
              className="vhd-ai-entry ng-layer-surface ng-living-interactive"
              onClick={() => onNavigate('/visitor/ai?context=home')}
            >
              <span className="vhd-ai-entry-icon"><AiSparkIcon /></span>
              <span>
                <small>Negin AI</small>
                <strong>تحلیل زمینه امروز</strong>
                <em>Workspace عمیق AI · بدون ایجاد Workflow موازی</em>
              </span>
              <ChevronLeftIcon />
            </button>
          </div>
        </section>

        <BottomDock
          ariaLabel="ناوبری ویزیتور"
          items={[
            { key: 'home', label: 'خانه', icon: <HomeIcon />, active: true, onClick: () => onNavigate('/visitor/home') },
            { key: 'route', label: 'مسیر', icon: <MapIcon />, onClick: () => onNavigate('/visitor/route') },
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
