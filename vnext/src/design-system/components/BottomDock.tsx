import type { ReactNode } from 'react'
import { cx } from './utils'

export type BottomDockItem = {
  key: string
  label: string
  icon: ReactNode
  active?: boolean | undefined
  disabled?: boolean | undefined
  onClick: () => void
}

export type BottomDockPrimary = {
  label: string
  icon: ReactNode
  active?: boolean | undefined
  disabled?: boolean | undefined
  onClick: () => void
}

type BottomDockProps = {
  items: readonly BottomDockItem[]
  primary: BottomDockPrimary
  ariaLabel?: string | undefined
  className?: string | undefined
}

function DockItem({ item }: { item: BottomDockItem }) {
  return (
    <button
      className={cx('ng-bottom-dock-item', 'ng-interactive', item.active && 'is-active')}
      type="button"
      disabled={item.disabled}
      onClick={item.onClick}
    >
      {item.icon}
      <span>{item.label}</span>
    </button>
  )
}

export function BottomDock({
  items,
  primary,
  ariaLabel = 'ناوبری اصلی',
  className,
}: BottomDockProps) {
  const split = Math.ceil(items.length / 2)
  const before = items.slice(0, split)
  const after = items.slice(split)

  return (
    <nav className={cx('ng-bottom-dock', className)} aria-label={ariaLabel}>
      {before.map((item) => <DockItem item={item} key={item.key} />)}
      <button
        className={cx('ng-bottom-dock-primary', 'ng-interactive', primary.active && 'is-active')}
        type="button"
        disabled={primary.disabled}
        onClick={primary.onClick}
      >
        <span className="ng-bottom-dock-primary-icon">{primary.icon}</span>
        <span>{primary.label}</span>
      </button>
      {after.map((item) => <DockItem item={item} key={item.key} />)}
    </nav>
  )
}
