import type { ReactNode } from 'react'
import { Button } from './Button'
import { cx } from './utils'

export type FeedbackKind = 'loading' | 'empty' | 'error'

type FeedbackStateProps = {
  kind: FeedbackKind
  title?: string
  description?: string
  icon?: ReactNode
  actionLabel?: string
  onAction?: () => void
  rows?: number
  className?: string
}

export function FeedbackState({
  kind,
  title,
  description,
  icon,
  actionLabel,
  onAction,
  rows = 3,
  className,
}: FeedbackStateProps) {
  if (kind === 'loading') {
    return (
      <div className={cx('ng-feedback', 'ng-feedback-loading', className)} role="status" aria-live="polite">
        {Array.from({ length: rows }, (_, index) => (
          <div className="ng-skeleton-row" key={index}>
            <i />
            <span><b /><em /></span>
          </div>
        ))}
        {description ? <small>{description}</small> : null}
      </div>
    )
  }

  return (
    <div
      className={cx('ng-feedback', `ng-feedback-${kind}`, className)}
      role={kind === 'error' ? 'alert' : 'status'}
    >
      {icon ? <span className="ng-feedback-icon" aria-hidden="true">{icon}</span> : null}
      {title ? <strong>{title}</strong> : null}
      {description ? <span>{description}</span> : null}
      {actionLabel && onAction ? (
        <Button variant={kind === 'error' ? 'secondary' : 'ghost'} onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  )
}
