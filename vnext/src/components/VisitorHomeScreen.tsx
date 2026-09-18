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
import { AppHeader, BottomDock } from '../design-system/components'
import { ActionRail, AppScene, ContextStrip, FocusSurface, Pressable } from '../design-system/composition'
import '../design-system/living/index.css'
import '../styles/home-composition.css'

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
        title: 'مرور کاتالوگ و موجودی فروش',
        body: 'امروز روز غیرکاری NGT است؛ بدون شروع ویزیت، زمینه فروش روز بعد را آماده کن.',
        action: 'مرور کاتالوگ',
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
      className={'vh-page vhome-page ng-living-root' + (livingUiEnabled ? ' vhome-live' : '')}
      dir="rtl"
      data-living-ui={livingUiEnabled ? 'on' : 'off'}
      data-design-system="atlas-v1"
      data-home-composition="v1"
    >
      <div className="vh-shell vhome-shell">
        <AppHeader
          avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}
          title={profile?.full_name || profile?.username || 'ویزیتور'}
          subtitle={profile?.branch || profile?.sales_line || 'حساب سازمانی'}
          subtitleIcon={<PinIcon />}
          profileTrailing={<ChevronLeftIcon />}
          onProfileClick={() => onNavigate('/visitor/profile')}
          action={(
            <button
              className={'vh-bell ng-living-interactive' + (highestSeverity ? ' severity-' + highestSeverity : '')}
              data-severity={highestSeverity ?? 'none'}
              type="button"
              aria-label="اعلان‌ها"
              onClick={() => onNavigate('/visitor/notifications')}
            >
              <BellIcon />
              {attentionCount ? (
                <b key={attentionCount + '-' + (highestSeverity ?? 'none')}>
                  {attentionCount}
                </b>
              ) : null}
            </button>
          )}
        />

        <AppScene className="vhome-scene">
          <ContextStrip className="vhome-context" aria-label="خلاصه وضعیت روز">
            <div className="vhome-context-item">
              <ClockIcon />
              <strong>{currentTime}</strong>
              <small>{weekday}</small>
              <em>{persianDate}</em>
            </div>

            <div className="vhome-context-item">
              <RouteArrowIcon />
              <strong>
                {workCalendar
                  ? elapsedWorkingDays.toLocaleString('fa-IR') + ' / ' + totalWorkingDays.toLocaleString('fa-IR')
                  : '…'}
              </strong>
              <small>روز کاری</small>
              <em>
                {workCalendar
                  ? remainingWorkingDays.toLocaleString('fa-IR') + ' روز مانده'
                  : 'تقویم NGT'}
              </em>
            </div>

            <Pressable
              emphasis="quiet"
              className="vhome-context-item"
              onClick={() => onNavigate('/visitor/reports')}
              aria-label="وضعیت هدف فروش"
            >
              <ChartIcon />
              <strong>{targetValue}</strong>
              <small>{targetLabel}</small>
              <em>{targetSemanticReady ? 'Analysis' : 'KPI gated'}</em>
            </Pressable>

            <Pressable
              emphasis="quiet"
              className={'vhome-context-item' + (attentionCount ? ' is-alert' : '')}
              onClick={() => onNavigate('/visitor/notifications')}
              aria-label="هشدارهای فعال"
            >
              <BellIcon />
              <strong>{attentionCount.toLocaleString('fa-IR')}</strong>
              <small>هشدار فعال</small>
              <em>{highestSeverity ? 'نیازمند توجه' : 'Alert Center'}</em>
            </Pressable>
          </ContextStrip>

          <FocusSurface className="vhome-focus">
            <div className="vhome-focus-head">
              <span className="vhome-live-badge"><i /> NeginAI LIVE</span>
            </div>

            {(error || riskError) ? (
              <Pressable
                emphasis="standard"
                className="vhome-sync-alert"
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
                      ? 'آخرین همگام‌سازی ' + new Date(lastSyncedAt).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }) + ' · لمس برای تلاش دوباره'
                      : 'برای تلاش دوباره لمس کن'}
                  </small>
                </span>
                <ChevronLeftIcon />
              </Pressable>
            ) : null}

            <div className="vhome-focus-body">
              <span className="vhome-focus-icon">{operationalAction.icon}</span>
              <div className="vhome-focus-copy min-w-0">
                <small>{operationalAction.eyebrow}</small>
                <h1>{operationalAction.title}</h1>
                <p>{operationalAction.body}</p>
              </div>
            </div>

            <div className="vhome-progress" aria-label="پیشرفت عملیات امروز">
              <span className="vhome-progress-track">
                <i
                  style={{
                    width: Math.max(4, Math.min(100, offDay ? 4 : routeSummary.progress)) + '%',
                  }}
                />
              </span>
              <small>
                {offDay
                  ? 'Route امروز غیرفعال'
                  : liveAssignment
                    ? routeSummary.progress.toLocaleString('fa-IR') + '٪ مسیر تعیین‌تکلیف شده'
                    : 'Route فعالی برای امروز ثبت نشده است'}
              </small>
            </div>

            <div className="vhome-focus-footer">
              <ActionRail className="vhome-actions" aria-label="اقدام‌های زمینه‌ای">
                {(riskLoading || riskError || returnedChequeCount > 0) ? (
                  <Pressable
                    className={'vhome-action vhome-action-risk' + (returnedChequeCount ? ' is-danger' : '')}
                    onClick={() => onNavigate('/visitor/reports')}
                  >
                    <span><ChequeIcon /></span>
                    <span>
                      <strong>ریسک مالی</strong>
                      <small>
                        {riskLoading
                          ? 'در حال دریافت…'
                          : returnedChequeCount
                            ? returnedChequeCount.toLocaleString('fa-IR') + ' چک برگشتی'
                            : 'دریافت نشد'}
                      </small>
                    </span>
                  </Pressable>
                ) : null}

                {attentionCount ? (
                  <Pressable
                    className="vhome-action vhome-action-alert"
                    onClick={() => onNavigate('/visitor/notifications')}
                  >
                    <span><BellIcon /></span>
                    <span>
                      <strong>هشدارها</strong>
                      <small>{attentionCount.toLocaleString('fa-IR')} مورد نیازمند توجه</small>
                    </span>
                  </Pressable>
                ) : null}

                <Pressable
                  className="vhome-action vhome-action-ai"
                  onClick={() => onNavigate('/visitor/ai?context=home')}
                >
                  <span><AiSparkIcon /></span>
                  <span>
                    <strong>Negin AI</strong>
                    <small>تحلیل زمینه امروز</small>
                  </span>
                </Pressable>
              </ActionRail>

              <Pressable
                emphasis="primary"
                className="vhome-focus-action"
                onClick={() => onNavigate(operationalAction.path)}
              >
                <span>{operationalAction.action}</span>
                <ChevronLeftIcon />
              </Pressable>
            </div>
          </FocusSurface>
        </AppScene>

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