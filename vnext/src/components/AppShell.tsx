import { Bell, ChevronDown, Search } from 'lucide-react'
import type { ReactNode } from 'react'
import { primaryNavigation, type PrimaryDestination } from '../app/navigation'
import { NeginAIBrandMark } from '../design-system/components/NeginAIBrandMark'

type AppShellProps = {
  active: PrimaryDestination
  onNavigate: (destination: PrimaryDestination) => void
  children: ReactNode
}

export function AppShell({ active, onNavigate, children }: AppShellProps) {
  return (
    <div className="ng-shell ng-v2" dir="rtl" data-trace-id="SHL-001">
      <header className="ng-topbar" data-trace-id="SHL-001">
        <div className="ng-brand">
          <NeginAIBrandMark className="ng-brand-symbol--shell" />
          <div>
            <strong>NeginAI</strong>
            <span>Enterprise Operational &amp; AI Platform</span>
          </div>
        </div>

        <div className="ng-user-context">
          <button className="ng-icon-button" type="button" aria-label="اعلان‌ها">
            <Bell size={19} />
            <span className="ng-notification-dot" aria-hidden="true" />
          </button>
          <button className="ng-profile-button" type="button" aria-label="تغییر زمینه کاربر">
            <span className="ng-avatar" aria-hidden="true">NR</span>
            <span className="ng-profile-copy">
              <strong>کاربر NeginAI</strong>
              <small>زمینه و نقش فعال</small>
            </span>
            <ChevronDown size={16} />
          </button>
        </div>
      </header>

      <section className="ng-context-bar" data-trace-id="SHL-002" aria-label="جستجو و اقدام زمینه‌ای">
        <Search size={18} aria-hidden="true" />
        <span>جستجو در ماژول‌ها، مشتری، گزارش یا عملیات مجاز…</span>
        <kbd>⌘ K</kbd>
      </section>

      <main className="ng-main" data-trace-id="SHL-003">
        {children}
      </main>

      <nav className="ng-bottom-nav" aria-label="ناوبری اصلی" data-trace-id="CMP-SPEC-001">
        {primaryNavigation.map((item) => {
          const Icon = item.icon
          const selected = active === item.id
          return (
            <button
              key={item.id}
              type="button"
              className={`ng-nav-item ${item.id === 'ai' ? 'ng-nav-item--ai' : ''} ${selected ? 'is-active' : ''}`}
              aria-current={selected ? 'page' : undefined}
              data-trace-id={item.traceId}
              onClick={() => onNavigate(item.id)}
            >
              <span className="ng-nav-icon"><Icon size={21} strokeWidth={1.8} /></span>
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
