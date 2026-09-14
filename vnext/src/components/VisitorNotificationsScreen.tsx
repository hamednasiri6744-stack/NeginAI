import { useMemo, useState } from 'react'
import {
  BellIcon,
  BoxIcon,
  ChartIcon,
  ChevronLeftIcon,
  HomeIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  StoreIcon,
  TagIcon,
  UserGroupIcon,
} from './Icons'
import { useVisitorNotifications, type NotificationKind, type VisitorNotificationItem } from '../state/VisitorNotificationsContext'

type Props = { onNavigate: (path: string) => void }
type Filter = 'all' | 'unread' | 'high'

function KindIcon({ kind }: { kind: NotificationKind }) {
  if (kind === 'price' || kind === 'promotion') return <TagIcon />
  if (kind === 'stock') return <BoxIcon />
  if (kind === 'customer') return <StoreIcon />
  if (kind === 'kpi') return <ChartIcon />
  if (kind === 'route') return <MapIcon />
  return <BellIcon />
}

function kindLabel(kind: NotificationKind) {
  const labels: Record<NotificationKind, string> = {
    price: 'قیمت', promotion: 'پروموشن', stock: 'موجودی', customer: 'مشتری', kpi: 'عملکرد', route: 'مسیر',
  }
  return labels[kind]
}

export function VisitorNotificationsScreen({ onNavigate }: Props) {
  const { items, unreadCount, markRead, markAllRead } = useVisitorNotifications()
  const [filter, setFilter] = useState<Filter>('all')
  const [kind, setKind] = useState<NotificationKind | 'all'>('all')
  const [notice, setNotice] = useState<string | null>(null)

  const visibleItems = useMemo(() => items.filter((item) => {
    if (filter === 'unread' && item.read) return false
    if (filter === 'high' && item.priority !== 'high') return false
    if (kind !== 'all' && item.kind !== kind) return false
    return true
  }), [items, filter, kind])

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }

  function openItem(item: VisitorNotificationItem) {
    markRead(item.id)
    onNavigate(item.target)
  }

  function readAll() {
    markAllRead()
    flash('همه اعلان‌ها خوانده‌شده شدند')
  }

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vn-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy"><strong>ویزیتور</strong><small><PinIcon /> منطقه کرج</small></span>
            <ChevronLeftIcon />
          </button>
          <button className="vh-bell active" type="button" aria-label="اعلان‌ها"><BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}</button>
          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vn-heading">
          <div>
            <h1>اعلان‌ها و هشدارها</h1>
            <p>{unreadCount ? `${unreadCount} مورد خوانده‌نشده` : 'همه اعلان‌ها بررسی شده‌اند'}</p>
          </div>
          <button type="button" disabled={!unreadCount} onClick={readAll}>خواندن همه</button>
        </section>

        <section className="vn-overview" aria-label="خلاصه اعلان‌ها">
          <article><span>خوانده‌نشده</span><strong>{unreadCount}</strong><small>نیازمند بررسی</small></article>
          <article className="danger"><span>اولویت بالا</span><strong>{items.filter((item) => item.priority === 'high').length}</strong><small>اقدام سریع</small></article>
          <article><span>امروز</span><strong>{items.length}</strong><small>اعلان دریافت‌شده</small></article>
        </section>

        <section className="vn-tabs" role="tablist" aria-label="فیلتر اعلان‌ها">
          <button className={filter === 'all' ? 'active' : ''} type="button" role="tab" aria-selected={filter === 'all'} onClick={() => setFilter('all')}>همه</button>
          <button className={filter === 'unread' ? 'active' : ''} type="button" role="tab" aria-selected={filter === 'unread'} onClick={() => setFilter('unread')}>خوانده‌نشده</button>
          <button className={filter === 'high' ? 'active' : ''} type="button" role="tab" aria-selected={filter === 'high'} onClick={() => setFilter('high')}>مهم</button>
        </section>

        <section className="vn-kind-strip" role="group" aria-label="نوع اعلان">
          {(['all', 'price', 'promotion', 'stock', 'customer', 'kpi', 'route'] as const).map((value) => (
            <button key={value} className={kind === value ? 'active' : ''} type="button" aria-pressed={kind === value} onClick={() => setKind(value)}>
              {value === 'all' ? 'همه نوع‌ها' : kindLabel(value)}
            </button>
          ))}
        </section>

        <section className="vn-list" aria-label="فهرست اعلان‌ها">
          {visibleItems.length ? visibleItems.map((item) => (
            <article className={`vn-card ${item.read ? 'read' : 'unread'} priority-${item.priority}`} key={item.id}>
              <button className="vn-card-main" type="button" onClick={() => openItem(item)}>
                <span className={`vn-icon kind-${item.kind}`}><KindIcon kind={item.kind} /></span>
                <span className="vn-copy">
                  <span className="vn-meta"><b>{kindLabel(item.kind)}</b><time>{item.time}</time></span>
                  <strong>{item.title}</strong>
                  <small>{item.body}</small>
                </span>
                {!item.read ? <span className="vn-unread-dot" aria-label="خوانده‌نشده" /> : <ChevronLeftIcon />}
              </button>
              <div className="vn-card-foot">
                <span className={`vn-priority ${item.priority}`}>{item.priority === 'high' ? 'اولویت بالا' : item.priority === 'medium' ? 'اولویت متوسط' : 'اطلاع‌رسانی'}</span>
                <button type="button" onClick={() => openItem(item)}>{item.actionLabel}<ChevronLeftIcon /></button>
              </div>
            </article>
          )) : (
            <div className="vn-empty"><BellIcon /><strong>اعلانی در این فیلتر نیست</strong><span>فیلتر دیگری را انتخاب کن.</span></div>
          )}
        </section>

        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
