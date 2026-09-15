import { useMemo, useState } from 'react'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import {
  BellIcon,
  ChevronLeftIcon,
  HomeIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  UserGroupIcon,
} from './Icons'

type Props = { onNavigate: (path: string) => void }
type Filter = 'all' | 'unread'

function notificationTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return value
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function VisitorNotificationsScreen({ onNavigate }: Props) {
  const { profile } = useVisitorAuth()
  const {
    items,
    unreadCount,
    loading,
    error,
    reload,
    markRead,
    markAllRead,
  } = useVisitorNotifications()
  const [filter, setFilter] = useState<Filter>('all')

  const visibleItems = useMemo(
    () => (filter === 'unread' ? items.filter((item) => !item.read) : items),
    [filter, items],
  )

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vn-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">{profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || '\u06a9\u0627\u0631\u0628\u0631'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || '\u0646\u0634\u0627\u0646 \u062d\u0627\u0636\u0631'}</small>
            </span>
            <ChevronLeftIcon />
          </button>

          <button className="vh-bell active" type="button" aria-label="\u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627">
            <BellIcon />
            {unreadCount ? <b>{unreadCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vn-heading">
          <div>
            <h1>{'\u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627'}</h1>
            <p>
              {unreadCount
                ? `${unreadCount.toLocaleString('fa-IR')} \u0627\u0639\u0644\u0627\u0646 \u062e\u0648\u0627\u0646\u062f\u0647\u200c\u0646\u0634\u062f\u0647`
                : '\u0647\u0645\u0647 \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627\u06cc \u0641\u0639\u0644\u06cc \u062e\u0648\u0627\u0646\u062f\u0647 \u0634\u062f\u0647\u200c\u0627\u0646\u062f.'}
            </p>
          </div>
          <button type="button" disabled={!unreadCount} onClick={markAllRead}>
            {'\u062e\u0648\u0627\u0646\u062f\u0646 \u0647\u0645\u0647'}
          </button>
        </section>

        {error ? (
          <section className="vh-live-state error" role="alert">
            <div>
              <strong>{'\u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc \u0646\u0634\u062f\u0646\u062f'}</strong>
              <span>{error}</span>
            </div>
            <button type="button" onClick={() => void reload()}>{'\u062a\u0644\u0627\u0634 \u062f\u0648\u0628\u0627\u0631\u0647'}</button>
          </section>
        ) : loading ? (
          <section className="vh-live-state" role="status">
            <strong>{'\u062f\u0631 \u062d\u0627\u0644 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627\u2026'}</strong>
          </section>
        ) : null}

        <section className="vn-overview" aria-label="\u062e\u0644\u0627\u0635\u0647 \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627">
          <article>
            <span>{'\u062e\u0648\u0627\u0646\u062f\u0647\u200c\u0646\u0634\u062f\u0647'}</span>
            <strong>{unreadCount.toLocaleString('fa-IR')}</strong>
            <small>{'\u0627\u0632 Backend \u0648\u0627\u0642\u0639\u06cc'}</small>
          </article>
          <article>
            <span>{'\u06a9\u0644'}</span>
            <strong>{items.length.toLocaleString('fa-IR')}</strong>
            <small>{'\u0627\u0639\u0644\u0627\u0646 \u062b\u0628\u062a\u200c\u0634\u062f\u0647'}</small>
          </article>
        </section>

        <section className="vn-tabs" role="tablist" aria-label="\u0641\u06cc\u0644\u062a\u0631 \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627">
          <button
            className={filter === 'all' ? 'active' : ''}
            type="button"
            role="tab"
            aria-selected={filter === 'all'}
            onClick={() => setFilter('all')}
          >
            {'\u0647\u0645\u0647'}
          </button>
          <button
            className={filter === 'unread' ? 'active' : ''}
            type="button"
            role="tab"
            aria-selected={filter === 'unread'}
            onClick={() => setFilter('unread')}
          >
            {'\u062e\u0648\u0627\u0646\u062f\u0647\u200c\u0646\u0634\u062f\u0647'}
          </button>
        </section>

        <section className="vn-list" aria-label="\u0641\u0647\u0631\u0633\u062a \u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627">
          {visibleItems.length ? visibleItems.map((item) => (
            <article className={`vn-card ${item.read ? 'read' : 'unread'}`} key={item.id}>
              <button className="vn-card-main" type="button" onClick={() => markRead(item.id)}>
                <span className="vn-icon"><BellIcon /></span>
                <span className="vn-copy">
                  <span className="vn-meta"><time>{notificationTime(item.created_at)}</time></span>
                  <strong>{item.title}</strong>
                  <small>{item.body}</small>
                </span>
                {!item.read ? <span className="vn-unread-dot" aria-label="\u062e\u0648\u0627\u0646\u062f\u0647\u200c\u0646\u0634\u062f\u0647" /> : <ChevronLeftIcon />}
              </button>
            </article>
          )) : (
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
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>{'\u062e\u0627\u0646\u0647'}</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>{'\u0645\u0633\u06cc\u0631'}</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>{'\u0633\u0641\u0627\u0631\u0634'}</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>{'\u0645\u0634\u062a\u0631\u06cc\u0627\u0646'}</span></button>
        </nav>
      </div>
    </main>
  )
}
