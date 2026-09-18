import type { ReactNode } from 'react'
import { cx } from './utils'

export type InsightTone = 'gold' | 'success' | 'warning' | 'danger' | 'info'

type InsightCardProps = {
  icon?: ReactNode | undefined
  eyebrow: string
  title: string
  body: string
  actionLabel?: string | undefined
  onAction?: (() => void) | undefined
  tone?: InsightTone
  className?: string | undefined
}

export function InsightCard({
  icon,
  eyebrow,
  title,
  body,
  actionLabel,
  onAction,
  tone = 'gold',
  className,
}: InsightCardProps) {
  return (
    <article className={cx('ng-insight-card', `is-${tone}`, className)}>
      {icon ? <span className="ng-insight-icon" aria-hidden="true">{icon}</span> : null}
      <span className="ng-insight-copy">
        <small>{eyebrow}</small>
        <strong>{title}</strong>
        <em>{body}</em>
      </span>
      {actionLabel && onAction ? (
        <button className="ng-insight-action ng-interactive" type="button" onClick={onAction}>
          {actionLabel}
          <span aria-hidden="true">‹</span>
        </button>
      ) : null}
    </article>
  )
}
