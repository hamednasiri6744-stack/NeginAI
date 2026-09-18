import { useMemo, useState } from 'react'
import type { NotificationSeverity } from '../api/neginApi'
import {
  AppHeader,
  BottomDock,
  Button,
  FeedbackState,
  LiveIndicator,
  NotificationItem,
  SegmentedControl,
  Surface,
} from '../design-system/components'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import '../design-system/living/index.css'
import '../styles/living-ui-pilot.css'
import '../styles/design-system-atlas-notifications.css'
import '../styles/visitor-notifications-semantic.css'
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

type Props = { onNavigate: (path: string) => void; onClose: () => void }
type Filter = 'all' | 'unread' | 'read'

function notificationTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return value
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

const severityRank: Record<NotificationSeverity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  info: 1,
}

const severityLabel: Record<NotificationSeverity, string> = {
  critical: 'بحرانی',
  high: 'بالا',
  medium: 'متوسط',
  info: 'اطلاعاتی',
}

const categoryLabel: Record<string, string> = {
  pricing: 'قیمت‌گذاری',
  promotion: 'پروموشن / جایزه',
  finance: 'مالی',
  credit: 'اعتباری',
  route: 'مسیر',
  customer: 'مشتری',
  distribution: 'توزیع',
  return: 'مرجوعی',
  general: 'عمومی',
}

function notificationCategory(value: string) {
  return categoryLabel[value] || value || 'عمومی'
}

export function VisitorNotificationsScreen({ onNavigate, onClose }: Props) {
  const { profile } = useVisitorAuth()
  const {
    items,
    unreadCount,
    attentionCount,
    highestSeverity,
    loading,
    error,
    liveConnected,
    reload,
    markRead,
    markAcknowledged,
    markAllRead,
  } = useVisitorNotifications()
  const [filter, setFilter] = useState<Filter>('all')

  const visibleItems = useMemo(() => {
    const filtered = filter === 'unread'
      ? items.filter((item) => !item.read || (item.requires_ack && !item.acknowledged))
      : filter === 'read'
        ? items.filter((item) => item.read && (!item.requires_ack || item.acknowledged))
        : items

    return [...filtered].sort((a, b) => {
      const aAttention = !a.read || (a.requires_ack && !a.acknowledged) ? 1 : 0
      const bAttention = !b.read || (b.requires_ack && !b.acknowledged) ? 1 : 0
      if (aAttention !== bAttention) return bAttention - aAttention
      const severityDiff = severityRank[b.severity] - severityRank[a.severity]
      if (severityDiff) return severityDiff
      return new Date(b.occurred_at || b.created_at).valueOf() - new Date(a.occurred_at || a.created_at).valueOf()
    })
  }, [filter, items])

  const readCount = items.filter((item) => item.read && (!item.requires_ack || item.acknowledged)).length
  const tabs = [
    { value: 'all' as const, label: 'همه', count: items.length },
    { value: 'unread' as const, label: 'خوانده‌نشده', count: unreadCount },
    { value: 'read' as const, label: 'خوانده‌شده', count: readCount },
  ]

  return (
    <main
      className="vh-page ng-living-root vh-live-ui"
      dir="rtl"
      data-live-ui="unified"
      data-living-ui="on"
      data-design-system="atlas-v1"
      data-screen="notifications"
    >
      <div className="vh-shell vn-shell">
        <AppHeader
          avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'ن'}
          title={profile?.full_name || profile?.username || 'کاربر'}
          subtitle={profile?.branch || profile?.sales_line || 'دفتر فروش'}
          subtitleIcon={<PinIcon />}
          profileTrailing={<ChevronLeftIcon />}
          onProfileClick={() => onNavigate('/visitor/profile')}
          action={(
            <button
              className={`vh-bell active ng-living-interactive ${highestSeverity ? `severity-${highestSeverity}` : ''}`}
              data-severity={highestSeverity ?? 'none'}
              type="button"
              aria-label="بستن اعلان‌ها"
              onClick={onClose}
            >
              <BellIcon />
              {attentionCount ? (
                <b key={`${attentionCount}-${highestSeverity ?? 'none'}`} className="ng-living-reactive">
                  {attentionCount}
                </b>
              ) : null}
            </button>
          )}
        />

        <Surface as="section" tone="stage" className="vn-heading" aria-live="polite">
          <div>
            <h1>اعلان‌ها</h1>
            <p>
              {attentionCount
                ? `${attentionCount.toLocaleString('fa-IR')} هشدار نیازمند توجه${highestSeverity ? ` · سطح ${severityLabel[highestSeverity]}` : ''}`
                : 'همه اعلان‌های فعلی خوانده شده‌اند.'}
            </p>
            <LiveIndicator state={liveConnected ? 'connected' : 'reconnecting'} />
          </div>
          <Button variant="ghost" disabled={!unreadCount} onClick={markAllRead}>
            خواندن همه
          </Button>
        </Surface>

        {error ? (
          <FeedbackState
            kind="error"
            title="اعلان‌ها بارگذاری نشدند"
            description={liveConnected ? 'اتصال زنده برقرار است؛ همگام‌سازی فهرست اعلان‌ها دوباره تلاش می‌شود.' : error}
            actionLabel="تلاش دوباره"
            onAction={() => void reload()}
          />
        ) : null}

        <SegmentedControl
          value={filter}
          items={tabs}
          onChange={setFilter}
          ariaLabel="فیلتر اعلان‌ها"
          className="vn-tabs"
        />

        <Surface as="section" tone="detail" className="vn-list ng-living-panel-change" aria-label="فهرست اعلان‌ها">
          {visibleItems.length ? visibleItems.map((item) => (
            <NotificationItem
              key={item.id}
              icon={<BellIcon />}
              tone={item.severity}
              toneLabel={severityLabel[item.severity]}
              categoryLabel={notificationCategory(item.category)}
              timeLabel={notificationTime(item.occurred_at || item.created_at)}
              title={item.title}
              body={item.body}
              sourceLabel={item.source === 'NGT' || item.source === 'varanegar' ? 'منبع: وارانگر / NGT' : item.source}
              unread={!item.read}
              attention={item.requires_ack && !item.acknowledged}
              acknowledgeHint="این اعلان نیازمند تأیید شماست"
              acknowledgeLabel="تأیید کردم"
              onOpen={() => {
                markRead(item.id)
                if (item.action_path) onNavigate(item.action_path)
              }}
              onAcknowledge={item.requires_ack && !item.acknowledged ? () => markAcknowledged(item.id) : undefined}
              trailing={item.read && (!item.requires_ack || item.acknowledged) ? <ChevronLeftIcon /> : undefined}
            />
          )) : loading ? (
            <FeedbackState kind="loading" rows={3} description="در حال همگام‌سازی اعلان‌ها…" />
          ) : error ? null : (
            <FeedbackState
              kind="empty"
              icon={<BellIcon />}
              title="اعلانی برای نمایش نیست"
              description={filter === 'unread'
                ? 'اعلان خوانده‌نشده‌ای وجود ندارد.'
                : 'برای این کاربر هنوز اعلانی ثبت نشده است.'}
            />
          )}
        </Surface>

        <BottomDock
          ariaLabel="ناوبری"
          items={[
            { key: 'home', label: 'خانه', icon: <HomeIcon />, onClick: () => onNavigate('/visitor/home') },
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
