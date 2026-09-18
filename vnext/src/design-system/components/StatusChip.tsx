import type { ReactNode } from 'react'
import { cx } from './utils'

export type StatusChipTone = 'neutral' | 'gold' | 'success' | 'warning' | 'danger' | 'info'

type StatusChipProps = {
  tone?: StatusChipTone
  icon?: ReactNode | undefined
  dot?: boolean | undefined
  children: ReactNode
  className?: string | undefined
}

export function StatusChip({
  tone = 'neutral',
  icon,
  dot = false,
  children,
  className,
}: StatusChipProps) {
  return (
    <span className={cx('ng-status-chip', `is-${tone}`, className)}>
      {dot ? <i className="ng-status-chip-dot" aria-hidden="true" /> : null}
      {icon ? <span className="ng-status-chip-icon" aria-hidden="true">{icon}</span> : null}
      <span>{children}</span>
    </span>
  )
}
