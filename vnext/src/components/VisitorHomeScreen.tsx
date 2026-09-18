import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
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
  reducedMotion: boolean | null
}

type HomeCardStyle = 'glass-neu' | 'pure-glass' | 'frosted-glass'

const HOME_CARD_STYLE: HomeCardStyle = 'frosted-glass'

const HOME_CARD_SKINS: Record<HomeCardStyle, string> = {
  'glass-neu': 'border-[rgba(156,194,220,.13)] bg-[linear-gradient(145deg,rgba(14,36,52,.72),rgba(3,13,22,.70))] shadow-[10px_12px_28px_rgba(0,0,0,.48),-7px_-7px_20px_rgba(39,83,110,.10),inset_1px_1px_0_rgba(255,255,255,.055),inset_-1px_-1px_0_rgba(0,0,0,.38)] backdrop-blur-[18px]',
  'pure-glass': 'border-[rgba(210,232,244,.16)] bg-[linear-gradient(145deg,rgba(21,49,68,.34),rgba(5,18,30,.22))] shadow-[0_14px_34px_rgba(0,0,0,.28),inset_0_1px_0_rgba(255,255,255,.09),inset_0_-1px_0_rgba(0,0,0,.18)] backdrop-blur-[24px] backdrop-saturate-[135%]',
  'frosted-glass': 'border-[rgba(222,238,247,.18)] bg-[linear-gradient(145deg,rgba(188,216,231,.10),rgba(20,42,58,.18))] shadow-[0_16px_36px_rgba(0,0,0,.30),inset_0_1px_0_rgba(255,255,255,.11),inset_0_0_28px_rgba(175,211,231,.035)] backdrop-blur-[30px] backdrop-saturate-[110%] backdrop-brightness-[108%]',
}

type HomeCardProps = {
  children: ReactNode
  ariaLabel: string
  depthKey: string
  reducedMotion: boolean | null
  className?: string
  interactive?: boolean
}

function HomeCard({
  children,
  ariaLabel,
  depthKey,
  reducedMotion,
  className = '',
  interactive = true,
}: HomeCardProps) {
  const cardClass = `group relative block w-full overflow-hidden rounded-[24px] border p-3 text-start ${HOME_CARD_SKINS[HOME_CARD_STYLE]} ${interactive ? 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(242,203,104,.34)]' : ''} ${className}`

  const content = (
    <>
      <span
        aria-hidden="true"
        className={HOME_CARD_STYLE === 'frosted-glass'
          ? "pointer-events-none absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-white/38 to-transparent"
          : HOME_CARD_STYLE === 'pure-glass'
            ? "pointer-events-none absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent"
            : "pointer-events-none absolute inset-x-3 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent"}
      />
      <span
        aria-hidden="true"
        className={HOME_CARD_STYLE === 'frosted-glass'
          ? "pointer-events-none absolute -end-14 -top-16 size-40 rounded-full bg-[radial-gradient(circle,rgba(220,241,250,.12),rgba(145,196,220,.05)_38%,transparent_72%)]"
          : HOME_CARD_STYLE === 'pure-glass'
            ? "pointer-events-none absolute -end-12 -top-14 size-36 rounded-full bg-[radial-gradient(circle,rgba(147,211,242,.14),transparent_70%)]"
            : "pointer-events-none absolute -end-10 -top-12 size-32 rounded-full bg-[radial-gradient(circle,rgba(93,166,205,.09),transparent_68%)]"}
      />
      <span className="relative z-[1] block">{children}</span>
    </>
  )

  if (!interactive) {
    return (
      <motion.div data-depth-target={depthKey} data-card-style={HOME_CARD_STYLE} className={cardClass}>
        {content}
      </motion.div>
    )
  }

  return (
    <motion.button
      type="button"
      aria-label={ariaLabel}
      data-depth-target={depthKey}
      data-card-style={HOME_CARD_STYLE}
      onClick={() => undefined}
      className={cardClass}
      {...(reducedMotion ? {} : { whileTap: { scale: 0.985, y: 1.5 } })}
      transition={{ type: 'spring', stiffness: 520, damping: 34, mass: 0.45 }}
    >
      {content}
    </motion.button>
  )
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

function TargetCard({
  title,
  target,
  actual,
  percent,
  remaining,
  reducedMotion,
}: TargetCardProps) {
  const progress = Math.max(0, Math.min(100, percent ?? 0))
  const ringBackground = percent == null
    ? 'conic-gradient(rgba(255,255,255,.06) 0 100%)'
    : `conic-gradient(var(--ng-gold-2) ${progress}%, rgba(255,255,255,.06) 0)`

  return (
    <HomeCard
      ariaLabel={`جزئیات هدف فروش ${title}`}
      depthKey={title === 'ماه جاری' ? 'target-month' : 'target-today'}
      reducedMotion={reducedMotion}
      className="h-full"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 pe-1">
          <small className="block text-[12px] font-bold text-ng-gold-soft">هدف فروش</small>
          <h2 className="mt-0.5 truncate text-[17px] font-black text-ng-text">{title}</h2>
        </div>

        <div
          aria-label={percent == null ? 'درصد تحقق نامشخص' : `درصد تحقق ${formatPercent(percent)}`}
          className="grid size-[72px] shrink-0 place-items-center rounded-full p-[5px] shadow-[inset_0_0_0_1px_rgba(255,255,255,.025)]"
          style={{ background: ringBackground }}
        >
          <div className="grid size-full place-items-center rounded-full bg-[rgba(2,10,18,.92)] text-center shadow-[inset_2px_2px_8px_rgba(0,0,0,.55),inset_-1px_-1px_5px_rgba(45,87,112,.08)]">
            <strong className="text-[16px] font-black text-ng-text">{formatPercent(percent)}</strong>
          </div>
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2">
        <div className="min-w-0">
          <dt className="text-[12px] text-ng-muted">تارگت ریالی</dt>
          <dd className="mt-0.5 truncate text-[15px] font-extrabold text-ng-text">{formatRial(target)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-[12px] text-ng-muted">تحقق ریالی</dt>
          <dd className="mt-0.5 truncate text-[15px] font-extrabold text-ng-text">{formatRial(actual)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-[12px] text-ng-muted">تحقق درصدی</dt>
          <dd className="mt-0.5 truncate text-[15px] font-extrabold text-ng-gold-soft">{formatPercent(percent)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-[12px] text-ng-muted">مانده از تارگت</dt>
          <dd className="mt-0.5 truncate text-[15px] font-extrabold text-ng-text">{formatRial(remaining)}</dd>
        </div>
      </dl>
    </HomeCard>
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
      data-home-ui="home-card-style-lab-v1" data-home-card-style={HOME_CARD_STYLE}
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

        <HomeCard
          ariaLabel="جزئیات زمان و تقویم کاری"
          depthKey="calendar"
          reducedMotion={reducedMotion}
          interactive={false}
          className="mt-2 shrink-0"
        >
          <div className="grid grid-cols-3">
            <div className="min-w-0 border-b border-e border-[var(--ng-border-subtle)] px-2 py-2 text-center">
              <small className="block text-[12px] text-ng-muted">تاریخ</small>
              <strong className="mt-1 block truncate text-[14px] font-extrabold">{persianDate}</strong>
            </div>
            <div className="min-w-0 border-b border-e border-[var(--ng-border-subtle)] px-2 py-2 text-center">
              <small className="block text-[12px] text-ng-muted">ساعت</small>
              <strong className="mt-1 block text-[17px] font-black text-ng-gold-soft">{currentTime}</strong>
            </div>
            <div className="min-w-0 border-b border-[var(--ng-border-subtle)] px-2 py-2 text-center">
              <small className="block text-[12px] text-ng-muted">روز هفته</small>
              <strong className="mt-1 block truncate text-[14px] font-extrabold">{weekday}</strong>
            </div>

            <div className="min-w-0 border-e border-[var(--ng-border-subtle)] px-2 py-2 text-center">
              <small className="block text-[12px] text-ng-muted">روز کاری ماه</small>
              <strong className="mt-1 block text-[17px] font-black">{workCalendar ? totalWorkingDays.toLocaleString('fa-IR') : '—'}</strong>
            </div>
            <div className="min-w-0 border-e border-[var(--ng-border-subtle)] px-2 py-2 text-center">
              <small className="block text-[12px] text-ng-muted">سپری‌شده</small>
              <strong className="mt-1 block text-[17px] font-black">{workCalendar ? elapsedWorkingDays.toLocaleString('fa-IR') : '—'}</strong>
            </div>
            <div className="min-w-0 px-2 py-2 text-center">
              <small className="block text-[12px] text-ng-muted">روز مانده</small>
              <strong className="mt-1 block text-[17px] font-black text-ng-gold-soft">{workCalendar ? remainingWorkingDays.toLocaleString('fa-IR') : '—'}</strong>
            </div>
          </div>
        </HomeCard>

        <div className="mt-2 grid grid-cols-2 gap-2">
          <TargetCard
            title="ماه جاری"
            target={monthlyTarget}
            actual={monthlyActual}
            percent={monthlyPercent}
            remaining={monthlyRemaining}
            reducedMotion={reducedMotion}
          />
          <TargetCard
            title="تا امروز"
            target={todayTarget}
            actual={todayActual}
            percent={todayPercent}
            remaining={todayRemaining}
            reducedMotion={reducedMotion}
          />
        </div>

        <HomeCard
          ariaLabel="جزئیات فروش موردنیاز تا پایان ماه"
          depthKey="required-sales"
          reducedMotion={reducedMotion}
          className="mt-2"
        >
          <div className="flex items-center justify-between gap-3 px-1">
            <div className="min-w-0 pe-1">
              <small className="block text-[12px] font-bold text-ng-gold-soft">برای رسیدن به ۱۰۰٪</small>
              <h2 className="mt-0.5 text-[17px] font-black">فروش موردنیاز تا پایان ماه</h2>
            </div>
            <span className="grid size-10 shrink-0 place-items-center rounded-[14px] border border-[rgba(242,203,104,.08)] bg-[rgba(242,203,104,.04)] text-ng-gold-soft shadow-[inset_1px_1px_0_rgba(255,255,255,.035),3px_4px_12px_rgba(0,0,0,.24)] [&>svg]:size-4">
              <ChartIcon />
            </span>
          </div>

          <div className="mt-3 grid grid-cols-2 divide-x divide-[var(--ng-border-subtle)]">
            <div className="min-w-0 px-3 text-center">
              <small className="block text-[11px] leading-5 text-ng-muted">کل فروش موردنیاز در روزهای کاری باقی‌مانده</small>
              <strong className="mt-1 block truncate text-[16px] font-black text-ng-text">{formatRial(requiredTotal)}</strong>
            </div>
            <div className="min-w-0 px-3 text-center">
              <small className="block text-[11px] leading-5 text-ng-muted">فروش روزانه موردنیاز تا پایان ماه</small>
              <strong className="mt-1 block truncate text-[17px] font-black text-ng-gold-soft">{formatRial(requiredDaily)}</strong>
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between border-t border-[var(--ng-border-subtle)] px-1 pt-2 text-[12px] text-ng-muted">
            <span>{remainingWorkingDays.toLocaleString('fa-IR')} روز کاری باقی مانده</span>
            <span>{targetStateLabel}</span>
          </div>
        </HomeCard>

        {error ? (
          <motion.button
            type="button"
            onClick={() => void reload()}
            className="mt-2 flex w-full items-center justify-between gap-3 rounded-[18px] border border-[rgba(242,184,79,.12)] bg-[rgba(242,184,79,.025)] px-3 py-2 text-start shadow-[inset_1px_1px_0_rgba(255,255,255,.025),5px_6px_16px_rgba(0,0,0,.22)]"
            {...(reducedMotion ? {} : { whileTap: { scale: 0.99 } })}
          >
            <span className="min-w-0">
              <strong className="block text-[11px] text-ng-warning">
                {stale ? 'حالت آفلاین · آخرین داده ذخیره‌شده' : 'بخشی از داده زنده در دسترس نیست'}
              </strong>
              <small className="mt-0.5 block truncate text-[12px] text-ng-muted">
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
