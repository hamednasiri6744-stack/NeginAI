import { Bot, Command, Menu, Search } from 'lucide-react'
import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react'
import { Avatar, IconButton } from './components'
import './ndl.css'

type Action = { label: string; icon?: ReactNode; onClick?: () => void }

export function AppHeader({ brand = 'NeginAI', subtitle, actions = [], profileName }: { brand?: string; subtitle?: string; actions?: Action[]; profileName?: string }) {
  return (
    <header className="ndl-app-header">
      <div className="ndl-app-header__brand"><span aria-hidden="true">✦</span><div><strong>{brand}</strong>{subtitle && <small>{subtitle}</small>}</div></div>
      <div className="ndl-app-header__actions">
        {actions.map((action) => <IconButton key={action.label} label={action.label} onClick={action.onClick}>{action.icon}</IconButton>)}
        {profileName && <Avatar name={profileName} />}
      </div>
    </header>
  )
}

export function PageHeader({ eyebrow, title, description, leading, actions }: { eyebrow?: string; title: string; description?: string; leading?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="ndl-page-header">
      <div className="ndl-page-header__heading">{leading}{eyebrow && <span>{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>
      {actions && <div className="ndl-page-header__actions">{actions}</div>}
    </header>
  )
}

export function CommandBar({ label = 'جستجو یا اجرای فرمان مجاز', shortcut = 'Ctrl K', onActivate }: { label?: string; shortcut?: string; onActivate?: () => void }) {
  return (
    <button className="ndl-command-bar" type="button" onClick={onActivate} aria-label={label}>
      <Search size={18} aria-hidden="true" /><span>{label}</span><kbd dir="ltr"><Command size={13} />{shortcut}</kbd>
    </button>
  )
}

export type NavigationItem = { id: string; label: string; icon: ReactNode }

export function BottomNavigation({ items, activeId, onNavigate, label = 'ناوبری اصلی' }: { items: NavigationItem[]; activeId: string; onNavigate: (id: string) => void; label?: string }) {
  return (
    <nav className="ndl-bottom-navigation" aria-label={label}>
      {items.map((item) => (
        <button key={item.id} type="button" className={item.id === activeId ? 'is-active' : undefined} aria-current={item.id === activeId ? 'page' : undefined} onClick={() => onNavigate(item.id)}>
          <span aria-hidden="true">{item.icon}</span><span>{item.label}</span>
        </button>
      ))}
    </nav>
  )
}

export function AIAction({ label = 'دستیار هوشمند', onClick }: { label?: string; onClick?: () => void }) {
  return <button className="ndl-ai-action" type="button" onClick={onClick}><Bot size={22} aria-hidden="true" /><span>{label}</span></button>
}

export type TabItem = { id: string; label: string; panel: ReactNode; disabled?: boolean }

export function Tabs({ items, activeId, onChange, label = 'بخش‌ها' }: { items: TabItem[]; activeId: string; onChange: (id: string) => void; label?: string }) {
  const baseId = useId()
  const refs = useRef<Array<HTMLButtonElement | null>>([])
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const enabled = items.map((item, itemIndex) => ({ item, itemIndex })).filter(({ item }) => !item.disabled)
    const current = enabled.findIndex(({ itemIndex }) => itemIndex === index)
    const visualStep = event.key === 'ArrowLeft' ? 1 : -1
    const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? enabled.length - 1 : (current + visualStep + enabled.length) % enabled.length
    const target = enabled[nextIndex]
    if (target) { onChange(target.item.id); refs.current[target.itemIndex]?.focus() }
  }
  const active = items.find((item) => item.id === activeId) ?? items[0]
  return (
    <div className="ndl-tabs">
      <div className="ndl-tabs__list" role="tablist" aria-label={label}>
        {items.map((item, index) => <button key={item.id} ref={(node) => { refs.current[index] = node }} role="tab" id={`${baseId}-${item.id}-tab`} aria-controls={`${baseId}-${item.id}-panel`} aria-selected={item.id === active?.id} tabIndex={item.id === active?.id ? 0 : -1} disabled={item.disabled} onClick={() => onChange(item.id)} onKeyDown={(event) => onKeyDown(event, index)}>{item.label}</button>)}
      </div>
      {active && <div className="ndl-tabs__panel" role="tabpanel" id={`${baseId}-${active.id}-panel`} aria-labelledby={`${baseId}-${active.id}-tab`} tabIndex={0}>{active.panel}</div>}
    </div>
  )
}

export function MenuAction({ label = 'بازکردن فهرست', onClick }: { label?: string; onClick?: () => void }) {
  return <IconButton label={label} onClick={onClick}><Menu size={20} /></IconButton>
}
