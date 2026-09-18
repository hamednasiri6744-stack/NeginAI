import { useMemo, useState } from 'react'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import type { NotificationSeverity } from '../api/neginApi'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import '../design-system/living/index.css'
import '../styles/living-ui-pilot.css'
import '../styles/design-system-atlas-notifications.css'
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

const severityRank: Record<NotificationSeverity, number> = { critical: 4, high: 3, medium: 2, info: 1 }
const severityLabel: Record<NotificationSeverity, string> = {
  critical: 'بحرانی',
  high: 'مهم',
  medium: 'متوسط',
  info: 'اطلاع',
}

const categoryLabel: Record<string, string> = {
  pricing: 'قیمت فروش',
  promotion: 'تخفیف / جایزه',
  finance: 'ریسک مالی',
  credit: 'کنترل اعتبار',
  route: 'مسیر',
  customer: 'مشتری',
  distribution: 'توزیع',
  return: 'برگشت',
  general: 'عملیاتی',
}

function notificationCategory(value: string) {
  return categoryLabel[value] || value || 'عملیاتی'
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

  return (
    <main className="vh-page ng-living-root vh-live-ui" dir="rtl" data-live-ui="unified" data-living-ui="on" data-design-system="atlas-v1" data-screen="notifications">
      <div className="vh-shell vn-shell">
        <header className="vh-header">
          <button className="vh-profile ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">{profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || 'کاربر'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || 'حساب سازمانی'}</small>
            </span>
            <ChevronLeftIcon />
          </button>

          <button className={`vh-bell active ng-living-interactive ${highestSeverity ? `severity-${highestSeverity}` : ''}`} data-severity={highestSeverity ?? 'none'} type="button" aria-label="\u0628\u0633\u062a\u0646 \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627" onClick={onClose}>
            <BellIcon />
            {attentionCount ? <b key={`${attentionCount}-${highestSeverity ?? 'none'}`} className="ng-living-reactive">{attentionCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vn-heading ng-living-surface" aria-live="polite">
          <div>
            <h1>{'\u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627'}</h1>
            <p>
              {attentionCount
                ? `${attentionCount.toLocaleString('fa-IR')} هشدار نیازمند توجه${highestSeverity ? ` · سطح ${severityLabel[highestSeverity]}` : ''}`
                : '\u0647\u0645\u0647 \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627\u06cc \u0641\u0639\u0644\u06cc \u062e\u0648\u0627\u0646\u062f\u0647 \u0634\u062f\u0647\u200c\u0627\u0646\u062f.'}
            </p>
            <span className={`vn-live-link ${liveConnected ? 'connected' : 'reconnecting'}`}>
              <i />{liveConnected ? 'اتصال زنده برقرار' : 'در حال اتصال زنده'}
            </span>
          </div>
          <button className="ng-living-interactive" type="button" disabled={!unreadCount} onClick={markAllRead}>
            {'\u062e\u0648\u0627\u0646\u062f\u0646 \u0647\u0645\u0647'}
          </button>
        </section>

        {error ? (
          <section className="vh-live-state error" role="alert">
            <div>
              <strong>{'\u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc \u0646\u0634\u062f\u0646\u062f'}</strong>
              <span>{liveConnected ? 'اتصال زنده برقرار است؛ همگام‌سازی فهرست اعلان‌ها دوباره تلاش می‌شود.' : error}</span>
            </div>
            <button type="button" onClick={() => void reload()}>{'\u062a\u0644\u0627\u0634 \u062f\u0648\u0628\u0627\u0631\u0647'}</button>
          </section>
        ) : null}

        <section className="vn-tabs" role="tablist" aria-label="\u0641\u06cc\u0644\u062a\u0631 \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627">
          <button
            className={`${filter === 'all' ? 'active ' : ''}ng-living-interactive`}
            type="button"
            role="tab"
            aria-selected={filter === 'all'}
            onClick={() => setFilter('all')}
          >
            <span>{'\u0647\u0645\u0647'}</span><b>{items.length.toLocaleString('fa-IR')}</b>
          </button>
          <button
            className={`${filter === 'unread' ? 'active ' : ''}ng-living-interactive`}
            type="button"
            role="tab"
            aria-selected={filter === 'unread'}
            onClick={() => setFilter('unread')}
          >
            <span>{'\u062e\u0648\u0627\u0646\u062f\u0647\u200c\u0646\u0634\u062f\u0647'}</span><b key={unreadCount} className="ng-living-reactive">{unreadCount.toLocaleString('fa-IR')}</b>
          </button>
          <button
            className={`${filter === 'read' ? 'active ' : ''}ng-living-interactive`}
            type="button"
            role="tab"
            aria-selected={filter === 'read'}
            onClick={() => setFilter('read')}
          >
            <span>{'\u062e\u0648\u0627\u0646\u062f\u0647\u200c\u0634\u062f\u0647'}</span><b>{readCount.toLocaleString('fa-IR')}</b>
          </button>
        </section>

        <section key={filter} className="vn-list ng-living-panel-change" aria-label="\u0641\u0647\u0631\u0633\u062a \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627">
          {visibleItems.length ? visibleItems.map((item) => (
            <article
              className={`vn-card ${item.read ? 'read' : 'unread'} severity-${item.severity} ng-living-surface`}
              data-severity={item.severity}
              data-living-state={item.requires_ack && !item.acknowledged ? 'attention' : item.read ? 'settled' : 'live'}
              key={item.id}
            >
              <button className="vn-card-main ng-living-interactive" type="button" onClick={() => { markRead(item.id); if (item.action_path) onNavigate(item.action_path) }}>
                <span className="vn-icon"><BellIcon /></span>
                <span className="vn-copy">
                  <span className="vn-meta"><b className={`vn-severity ${item.severity}`}>{severityLabel[item.severity]}</b><i className="vn-category" data-category={item.category}>{notificationCategory(item.category)}</i><time>{notificationTime(item.occurred_at || item.created_at)}</time></span>
                  <strong>{item.title}</strong>
                  <small>{item.body}</small>
                  <em>{item.source === 'NGT' || item.source === 'varanegar' ? 'منبع: ورانگر / NGT' : item.source}</em>
                </span>
                {!item.read || (item.requires_ack && !item.acknowledged) ? <span className="vn-unread-dot ng-living-reactive" aria-label="نیازمند توجه" /> : <ChevronLeftIcon />}
              </button>
              {item.requires_ack && !item.acknowledged ? (
                <div className="vn-card-foot critical-ack"><span>این هشدار نیازمند تأیید است</span><button type="button" onClick={() => markAcknowledged(item.id)}>تأیید اطلاع</button></div>
              ) : null}
            </article>
          )) : loading ? (
            <div className="vn-loading-list" role="status" aria-live="polite">
              <div className="vn-skeleton-row"><i /><span><b /><em /></span></div>
              <div className="vn-skeleton-row"><i /><span><b /><em /></span></div>
              <div className="vn-skeleton-row"><i /><span><b /><em /></span></div>
              <small>در حال همگام‌سازی اعلان‌ها…</small>
            </div>
          ) : error ? null : (
            <div className="vn-empty">
              <BellIcon />
              <strong>{'\u0627\u0639\u0644\u0627\u0646\u06cc \u0628\u0631\u0627\u06cc \u0646\u0645\u0627\u06cc\u0634 \u0646\u06cc\u0633\u062a'}</strong>
              <span>{filter === 'unread'
                ? '\u0627\u0639\u0644\u0627\u0646 \u062e\u0648\u0627\u0646\u062f\u0647\u200c\u0646\u0634\u062f\u0647\u200c\u0627\u06cc \u0648\u062c\u0648\u062f \u0646\u062f\u0627\u0631\u062f.'
                : '\u0628\u0631\u0627\u06cc \u0627\u06cc\u0646 \u06a9\u0627\u0631\u0628\u0631 \u0647\u0646\u0648\u0632 \u0627\u0639\u0644\u0627\u0646\u06cc \u062b\u0628\u062a \u0646\u0634\u062f\u0647 \u0627\u0633\u062a.'}</span>
            </div>
          )}
        </section>

        <nav className="vh-nav" aria-label="\u0646\u0627\u0648\u0628\u0631\u06cc">
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>{'\u062e\u0627\u0646\u0647'}</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>{'\u0645\u0633\u06cc\u0631'}</span></button>
          <button className="vh-order ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>{'\u0633\u0641\u0627\u0631\u0634'}</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>{'\u0645\u0634\u062a\u0631\u06cc\u0627\u0646'}</span></button>
          <button className="vh-nav-item ng-living-interactive" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>{"\u06af\u0632\u0627\u0631\u0634\u200c\u0647\u0627"}</span></button>
        </nav>
      </div>
    </main>
  )
}
