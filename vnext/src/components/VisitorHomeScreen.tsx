import { useEffect, useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import {
  BellIcon,
  ChartIcon,
  ChevronLeftIcon,
  HomeIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  UserGroupIcon,
} from './Icons'
import { AppHeader, BottomDock } from '../design-system/components'

type Props = { onNavigate: (path: string) => void }

type TargetCardProps = {
  title: string
  target: number | null
  actual: number | null
  percent: number | null
  remaining: number | null
}

function formatRial(value: number | null) {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${new Intl.NumberFormat('fa-IR', {
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(Math.max(0, value))} ریال`
}

function formatPercent(value: number | null) {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${value.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪`
}

function TargetCard({ title, target, actual, percent, remaining }: TargetCardProps) {
  const progress = Math.max(0, Math.min(100, percent ?? 0))
  const ringBackground = percent == null
    ? 'conic-gradient(rgba(255,255,255,.06) 0 100%)'
    : `conic-gradient(var(--ng-gold-2) ${progress}%, rgba(255,255,255,.06) 0)`

  return (
    <section className="min-w-0 border-y border-[var(--ng-border-subtle)] py-3">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <small className="block text-[9px] font-bold text-ng-gold-soft">هدف فروش</small>
          <h2 className="mt-0.5 truncate text-[13px] font-black text-ng-text">{title}</h2>
        </div>

        <div
          aria-label={percent == null ? 'درصد تحقق نامشخص' : `درصد تحقق ${formatPercent(percent)}`}
          className="grid size-[66px] shrink-0 place-items-center rounded-full p-[5px]"
          style={{ background: ringBackground }}
        >
          <div className="grid size-full place-items-center rounded-full bg-ng-bg text-center">
            <strong className="text-[12px] font-black text-ng-text">{formatPercent(percent)}</strong>
          </div>
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2">
        <div className="min-w-0">
          <dt className="text-[8px] text-ng-muted">تارگت ریالی</dt>
          <dd className="mt-0.5 truncate text-[11px] font-extrabold text-ng-text">{formatRial(target)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-[8px] text-ng-muted">تحقق ریالی</dt>
          <dd className="mt-0.5 truncate text-[11px] font-extrabold text-ng-text">{formatRial(actual)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-[8px] text-ng-muted">تحقق درصدی</dt>
          <dd className="mt-0.5 truncate text-[11px] font-extrabold text-ng-gold-soft">{formatPercent(percent)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-[8px] text-ng-muted">مانده از تارگت</dt>
          <dd className="mt-0.5 truncate text-[11px] font-extrabold text-ng-text">{formatRial(remaining)}</dd>
        </div>
      </dl>
    </section>
  )
}

export function VisitorHomeScreen({ onNavigate }: Props) {
  const { attentionCount } = useVisitorNotifications()
  const { profile } = useVisitorAuth()
  const {
    error,
    workCalendar,
    targetPulse,
    stale,
    lastSyncedAt,
    reload,
  } = useVisitorLiveData()

  const [now, setNow] = useState(() => new Date())
  const reducedMotion = useReducedMotion()

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

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

  const elapsedWorkingDays = Number(workCalendar?.elapsed_working_days ?? 0)
  const totalWorkingDays = Number(workCalendar?.total_working_days ?? 0)
  const remainingWorkingDays = Number(workCalendar?.remaining_working_days ?? 0)

  const semanticStatus = targetPulse?.semantic_status?.toUpperCase() ?? ''
  const semanticReady = ['CANONICAL', 'VALIDATED', 'FACT'].includes(semanticStatus)
  const targetConfigured = Boolean(targetPulse?.configured && targetPulse.target_rial != null)

  const monthlyTarget = semanticReady && targetConfigured ? Number(targetPulse?.target_rial ?? 0) : null
  const monthlyActual = semanticReady && targetConfigured ? Number(targetPulse?.actual_sales_rial ?? 0) : null
  const monthlyPercent = semanticReady && targetConfigured && targetPulse?.achievement_percent != null
    ? Number(targetPulse.achievement_percent)
    : null
  const monthlyRemaining = semanticReady && targetConfigured && targetPulse?.remaining_target_rial != null
    ? Number(targetPulse.remaining_target_rial)
    : null

  const todayTarget = useMemo(() => {
    if (monthlyTarget == null || totalWorkingDays <= 0) return null
    return monthlyTarget * (elapsedWorkingDays / totalWorkingDays)
  }, [monthlyTarget, totalWorkingDays, elapsedWorkingDays])

  const todayActual = monthlyActual
  const todayPercent = todayTarget != null && todayTarget > 0 && todayActual != null
    ? (todayActual / todayTarget) * 100
    : null
  const todayRemaining = todayTarget != null && todayActual != null
    ? Math.max(todayTarget - todayActual, 0)
    : null

  const requiredTotal = monthlyRemaining
  const requiredDaily = semanticReady && targetConfigured && targetPulse?.daily_required_rial != null
    ? Number(targetPulse.daily_required_rial)
    : null

  const targetStateLabel = !semanticReady
    ? 'منطق تارگت در اعتبارسنجی'
    : !targetConfigured
      ? 'تارگت ماه هنوز تنظیم نشده'
      : 'داده زنده'

  return (
    <main
      className="relative h-dvh min-h-dvh overflow-hidden bg-ng-bg text-ng-text"
      dir="rtl"
      data-home-ui="tailwind-v2"
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
              {...(reducedMotion ? {} : { whileTap: { scale: 0.96 } })}
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
          aria-label="زمان و تقویم کاری"
          className="mt-2 grid shrink-0 grid-cols-3 border-y border-[var(--ng-border-subtle)]"
        >
          <div className="min-w-0 border-b border-e border-[var(--ng-border-subtle)] px-2 py-2.5 text-center">
            <small className="block text-[8px] text-ng-muted">تاریخ</small>
            <strong className="mt-1 block truncate text-[10px] font-extrabold">{persianDate}</strong>
          </div>
          <div className="min-w-0 border-b border-e border-[var(--ng-border-subtle)] px-2 py-2.5 text-center">
            <small className="block text-[8px] text-ng-muted">ساعت</small>
            <strong className="mt-1 block text-[12px] font-black text-ng-gold-soft">{currentTime}</strong>
          </div>
          <div className="min-w-0 border-b border-[var(--ng-border-subtle)] px-2 py-2.5 text-center">
            <small className="block text-[8px] text-ng-muted">روز هفته</small>
            <strong className="mt-1 block truncate text-[10px] font-extrabold">{weekday}</strong>
          </div>

          <div className="min-w-0 border-e border-[var(--ng-border-subtle)] px-2 py-2.5 text-center">
            <small className="block text-[8px] text-ng-muted">روز کاری ماه</small>
            <strong className="mt-1 block text-[12px] font-black">{workCalendar ? totalWorkingDays.toLocaleString('fa-IR') : '—'}</strong>
          </div>
          <div className="min-w-0 border-e border-[var(--ng-border-subtle)] px-2 py-2.5 text-center">
            <small className="block text-[8px] text-ng-muted">سپری‌شده</small>
            <strong className="mt-1 block text-[12px] font-black">{workCalendar ? elapsedWorkingDays.toLocaleString('fa-IR') : '—'}</strong>
          </div>
          <div className="min-w-0 px-2 py-2.5 text-center">
            <small className="block text-[8px] text-ng-muted">روز مانده</small>
            <strong className="mt-1 block text-[12px] font-black text-ng-gold-soft">{workCalendar ? remainingWorkingDays.toLocaleString('fa-IR') : '—'}</strong>
          </div>
        </section>

        <div className="mt-2 grid grid-cols-2 gap-3">
          <TargetCard
            title="ماه جاری"
            target={monthlyTarget}
            actual={monthlyActual}
            percent={monthlyPercent}
            remaining={monthlyRemaining}
          />
          <TargetCard
            title="تا امروز"
            target={todayTarget}
            actual={todayActual}
            percent={todayPercent}
            remaining={todayRemaining}
          />
        </div>

        <section className="mt-2 border-y border-[var(--ng-border-subtle)] py-3">
          <div className="flex items-center justify-between gap-3 px-1">
            <div className="min-w-0">
              <small className="block text-[9px] font-bold text-ng-gold-soft">برای رسیدن به ۱۰۰٪</small>
              <h2 className="mt-0.5 text-[13px] font-black">فروش موردنیاز تا پایان ماه</h2>
            </div>
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-[rgba(242,203,104,.045)] text-ng-gold-soft [&>svg]:size-4">
              <ChartIcon />
            </span>
          </div>

          <div className="mt-3 grid grid-cols-2 divide-x divide-[var(--ng-border-subtle)]">
            <div className="min-w-0 px-3 text-center">
              <small className="block text-[8px] leading-4 text-ng-muted">کل فروش موردنیاز در روزهای کاری باقی‌مانده</small>
              <strong className="mt-1 block truncate text-[12px] font-black text-ng-text">{formatRial(requiredTotal)}</strong>
            </div>
            <div className="min-w-0 px-3 text-center">
              <small className="block text-[8px] leading-4 text-ng-muted">فروش روزانه موردنیاز تا پایان ماه</small>
              <strong className="mt-1 block truncate text-[12px] font-black text-ng-gold-soft">{formatRial(requiredDaily)}</strong>
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between border-t border-[var(--ng-border-subtle)] px-1 pt-2 text-[8px] text-ng-muted">
            <span>{remainingWorkingDays.toLocaleString('fa-IR')} روز کاری باقی مانده</span>
            <span>{targetStateLabel}</span>
          </div>
        </section>

        {error ? (
          <motion.button
            type="button"
            onClick={() => void reload()}
            className="mt-2 flex w-full items-center justify-between gap-3 border-y border-[rgba(242,184,79,.14)] bg-[rgba(242,184,79,.025)] px-2 py-2 text-start"
            {...(reducedMotion ? {} : { whileTap: { scale: 0.99 } })}
          >
            <span className="min-w-0">
              <strong className="block text-[9px] text-ng-warning">
                {stale ? 'حالت آفلاین · آخرین داده ذخیره‌شده' : 'بخشی از داده زنده در دسترس نیست'}
              </strong>
              <small className="mt-0.5 block truncate text-[8px] text-ng-muted">
                {stale && lastSyncedAt
                  ? 'آخرین همگام‌سازی ' + new Date(lastSyncedAt).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
                  : 'برای تلاش دوباره لمس کن'}
              </small>
            </span>
            <span className="[&>svg]:size-3 [&>svg]:rotate-180 text-ng-muted"><ChevronLeftIcon /></span>
          </motion.button>
        ) : null}

        <div className="min-h-0 flex-1" />

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
