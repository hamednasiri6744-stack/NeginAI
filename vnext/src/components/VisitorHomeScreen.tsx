import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
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
  const reducedMotion = useReducedMotion()

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
      className="relative h-dvh min-h-dvh overflow-hidden bg-ng-bg text-ng-text"
      dir="rtl"
      data-home-ui="tailwind-v1"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(38,91,126,.20),transparent_34%)]"
      />

      <div className="relative mx-auto flex h-dvh w-full max-w-[430px] flex-col px-3 pt-[max(12px,env(safe-area-inset-top))] pb-[calc(96px+env(safe-area-inset-bottom))]">
        <AppHeader
          avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}
          title={profile?.full_name || profile?.username || 'ویزیتور'}
          subtitle={profile?.branch || profile?.sales_line || 'حساب سازمانی'}
          subtitleIcon={<PinIcon />}
          profileTrailing={<ChevronLeftIcon />}
          onProfileClick={() => onNavigate('/visitor/profile')}
          action={(
            <motion.button
              type="button"
              aria-label="اعلان‌ها"
              onClick={() => onNavigate('/visitor/notifications')}
              className="relative grid size-11 place-items-center rounded-[15px] border border-[var(--ng-border-subtle)] bg-[rgba(7,22,35,.74)] text-ng-gold shadow-[var(--ng-shadow-contact)]"
              {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.96 } })}
              transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
            >
              <BellIcon />
              {attentionCount ? (
                <b className="absolute -end-1 -top-1 grid min-w-5 place-items-center rounded-full bg-ng-danger px-1 text-[10px] font-black text-white">
                  {attentionCount}
                </b>
              ) : null}
            </motion.button>
          )}
        />

        <section
          aria-label="خلاصه وضعیت روز"
          className="mt-2 grid shrink-0 grid-cols-4 divide-x divide-[var(--ng-border-subtle)] rounded-[var(--ng-radius-stage)] border border-[var(--ng-border-subtle)] bg-[rgba(4,15,25,.56)] p-1 backdrop-blur-[var(--ng-blur)]"
        >
          <div className="flex min-h-14 min-w-0 flex-col items-center justify-center gap-0.5 px-1 text-center">
            <span className="[&>svg]:size-4 text-ng-gold-soft"><ClockIcon /></span>
            <strong className="max-w-full truncate text-xs font-extrabold">{currentTime}</strong>
            <small className="max-w-full truncate text-[9px] text-ng-muted">{weekday}</small>
          </div>

          <div className="flex min-h-14 min-w-0 flex-col items-center justify-center gap-0.5 px-1 text-center">
            <span className="[&>svg]:size-4 text-ng-gold-soft"><RouteArrowIcon /></span>
            <strong className="max-w-full truncate text-xs font-extrabold">
              {workCalendar
                ? elapsedWorkingDays.toLocaleString('fa-IR') + ' / ' + totalWorkingDays.toLocaleString('fa-IR')
                : '…'}
            </strong>
            <small className="max-w-full truncate text-[9px] text-ng-muted">
              {workCalendar ? remainingWorkingDays.toLocaleString('fa-IR') + ' روز مانده' : 'روز کاری'}
            </small>
          </div>

          <motion.button
            type="button"
            onClick={() => onNavigate('/visitor/reports')}
            aria-label="وضعیت هدف فروش"
            className="flex min-h-14 min-w-0 flex-col items-center justify-center gap-0.5 rounded-xl px-1 text-center"
            {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.97 } })}
            transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
          >
            <span className="[&>svg]:size-4 text-ng-gold-soft"><ChartIcon /></span>
            <strong className="max-w-full truncate text-xs font-extrabold">{targetValue}</strong>
            <small className="max-w-full truncate text-[9px] text-ng-muted">{targetLabel}</small>
          </motion.button>

          <motion.button
            type="button"
            onClick={() => onNavigate('/visitor/notifications')}
            aria-label="هشدارهای فعال"
            className="flex min-h-14 min-w-0 flex-col items-center justify-center gap-0.5 rounded-xl px-1 text-center"
            {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.97 } })}
            transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
          >
            <span className="[&>svg]:size-4 text-ng-gold-soft"><BellIcon /></span>
            <strong className={attentionCount ? 'max-w-full truncate text-xs font-extrabold text-ng-warning' : 'max-w-full truncate text-xs font-extrabold'}>
              {attentionCount.toLocaleString('fa-IR')}
            </strong>
            <small className="max-w-full truncate text-[9px] text-ng-muted">
              {highestSeverity ? 'نیازمند توجه' : 'هشدار فعال'}
            </small>
          </motion.button>
        </section>

        <div className="mt-2 min-h-0 flex-1 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <section className="relative overflow-hidden rounded-[var(--ng-radius-stage)] border border-[var(--ng-border-subtle)] bg-[linear-gradient(155deg,rgba(255,255,255,.035),rgba(255,255,255,.004)_46%),var(--ng-surface-stage)] p-4 shadow-[var(--ng-shadow-contact)]">
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_84%_12%,rgba(242,203,104,.09),transparent_34%)]"
            />

            <div className="relative flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-1.5 text-[10px] font-black text-ng-mint">
                <i className={'size-1.5 rounded-full bg-current ' + (livingUiEnabled && !reducedMotion ? 'animate-pulse' : '')} />
                NeginAI LIVE
              </span>
              <span className="text-[9px] text-ng-muted">{persianDate}</span>
            </div>

            <div className="relative mt-4 grid grid-cols-[48px_minmax(0,1fr)] items-center gap-3">
              <span className="grid size-12 place-items-center rounded-2xl border border-[rgba(242,203,104,.18)] bg-[rgba(242,203,104,.05)] text-ng-gold [&>svg]:size-6">
                {operationalAction.icon}
              </span>
              <div className="min-w-0">
                <small className="text-[10px] font-extrabold text-ng-gold-soft">{operationalAction.eyebrow}</small>
                <h1 className="mt-1 text-[clamp(19px,5.2vw,24px)] font-black leading-[1.45] text-ng-text">
                  {operationalAction.title}
                </h1>
                <p className="mt-1 text-[11px] leading-7 text-ng-muted">{operationalAction.body}</p>
              </div>
            </div>

            <div className="relative mt-4">
              <div className="h-1 overflow-hidden rounded-full bg-[rgba(255,255,255,.055)]">
                <i
                  className="block h-full rounded-full bg-gradient-to-l from-ng-gold to-[var(--ng-gold-4)] shadow-[0_0_12px_rgba(242,203,104,.24)]"
                  style={{
                    width: Math.max(4, Math.min(100, offDay ? 4 : routeSummary.progress)) + '%',
                  }}
                />
              </div>
              <small className="mt-1.5 block text-[9px] text-ng-muted">
                {offDay
                  ? 'Route امروز غیرفعال'
                  : liveAssignment
                    ? routeSummary.progress.toLocaleString('fa-IR') + '٪ مسیر تعیین‌تکلیف شده'
                    : 'Route فعالی برای امروز ثبت نشده است'}
              </small>
            </div>

            <motion.button
              type="button"
              onClick={() => onNavigate(operationalAction.path)}
              className="relative mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-[rgba(255,230,160,.72)] bg-gradient-to-b from-[#ffe8a3] to-[#dda22c] px-6 font-black text-[#171005] shadow-[0_10px_24px_rgba(0,0,0,.28),inset_0_1px_rgba(255,255,255,.45)]"
              {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.97, y: 1 } })}
              transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
            >
              <span>{operationalAction.action}</span>
              <span className="[&>svg]:size-3 [&>svg]:rotate-180"><ChevronLeftIcon /></span>
            </motion.button>
          </section>

          {(error || riskError) ? (
            <motion.button
              type="button"
              onClick={retryLiveData}
              className="mt-2 flex w-full items-center justify-between gap-3 border-y border-[rgba(242,184,79,.14)] bg-[rgba(242,184,79,.035)] px-3 py-2 text-start"
              {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.99 } })}
              transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
            >
              <span className="min-w-0">
                <strong className="block text-[10px] text-ng-warning">
                  {stale ? 'حالت آفلاین · آخرین داده ذخیره‌شده' : 'بخشی از داده زنده در دسترس نیست'}
                </strong>
                <small className="mt-0.5 block truncate text-[9px] text-ng-muted">
                  {stale && lastSyncedAt
                    ? 'آخرین همگام‌سازی ' + new Date(lastSyncedAt).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }) + ' · لمس برای تلاش دوباره'
                    : 'برای تلاش دوباره لمس کن'}
                </small>
              </span>
              <span className="[&>svg]:size-3 [&>svg]:rotate-180 text-ng-muted"><ChevronLeftIcon /></span>
            </motion.button>
          ) : null}

          <section className="mt-2 divide-y divide-[var(--ng-border-subtle)] border-y border-[var(--ng-border-subtle)]">
            {(riskLoading || returnedChequeCount > 0) ? (
              <motion.button
                type="button"
                onClick={() => onNavigate('/visitor/reports')}
                className="grid min-h-14 w-full grid-cols-[38px_minmax(0,1fr)_14px] items-center gap-3 px-2 text-start"
                {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.99 } })}
                transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
              >
                <span className={riskLoading
                  ? "grid size-9 place-items-center rounded-xl bg-[rgba(119,185,232,.05)] text-ng-info [&>svg]:size-4"
                  : "grid size-9 place-items-center rounded-xl bg-[rgba(255,109,120,.06)] text-ng-danger [&>svg]:size-4"
                }><ChequeIcon /></span>
                <span className="min-w-0">
                  <strong className={riskLoading ? "block text-xs text-ng-text" : "block text-xs text-ng-danger"}>ریسک مالی</strong>
                  <small className="mt-0.5 block truncate text-[9px] text-ng-muted">
                    {riskLoading ? 'در حال دریافت…' : returnedChequeCount.toLocaleString('fa-IR') + ' چک برگشتی'}
                  </small>
                </span>
                <span className="[&>svg]:size-3 [&>svg]:rotate-180 text-ng-muted"><ChevronLeftIcon /></span>
              </motion.button>
            ) : null}

            {attentionCount > 0 ? (
              <motion.button
                type="button"
                onClick={() => onNavigate('/visitor/notifications')}
                className="grid min-h-14 w-full grid-cols-[38px_minmax(0,1fr)_14px] items-center gap-3 px-2 text-start"
                {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.99 } })}
                transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
              >
                <span className="grid size-9 place-items-center rounded-xl bg-[rgba(242,184,79,.05)] text-ng-warning [&>svg]:size-4"><BellIcon /></span>
                <span className="min-w-0">
                  <strong className="block text-xs text-ng-text">هشدارها</strong>
                  <small className="mt-0.5 block truncate text-[9px] text-ng-muted">
                    {attentionCount.toLocaleString('fa-IR')} مورد نیازمند توجه
                  </small>
                </span>
                <span className="[&>svg]:size-3 [&>svg]:rotate-180 text-ng-muted"><ChevronLeftIcon /></span>
              </motion.button>
            ) : null}

            <motion.button
              type="button"
              onClick={() => onNavigate('/visitor/ai?context=home')}
              className="grid min-h-14 w-full grid-cols-[38px_minmax(0,1fr)_14px] items-center gap-3 px-2 text-start"
              {...(reducedMotion || !livingUiEnabled ? {} : { whileTap: { scale: 0.99 } })}
              transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
            >
              <span className="grid size-9 place-items-center rounded-xl bg-[rgba(242,203,104,.045)] text-ng-gold-soft [&>svg]:size-4"><AiSparkIcon /></span>
              <span className="min-w-0">
                <strong className="block text-xs text-ng-text">Negin AI</strong>
                <small className="mt-0.5 block truncate text-[9px] text-ng-muted">تحلیل زمینه امروز</small>
              </span>
              <span className="[&>svg]:size-3 [&>svg]:rotate-180 text-ng-muted"><ChevronLeftIcon /></span>
            </motion.button>
          </section>
        </div>

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