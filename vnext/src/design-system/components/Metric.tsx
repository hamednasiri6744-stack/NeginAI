import type { ReactNode } from 'react'
import { cx } from './utils'

export type MetricTone = 'neutral' | 'gold' | 'success' | 'warning' | 'danger' | 'info'

type MetricProps = {
  label: string
  value: ReactNode
  meta?: ReactNode | undefined
  icon?: ReactNode | undefined
  tone?: MetricTone
  className?: string | undefined
}

export function Metric({
  label,
  value,
  meta,
  icon,
  tone = 'neutral',
  className,
}: MetricProps) {
  return (
    <div className={cx('ng-metric', `is-${tone}`, className)}>
      {icon ? <span className="ng-metric-icon" aria-hidden="true">{icon}</span> : null}
      <span className="ng-metric-copy">
        <small>{label}</small>
        <strong>{value}</strong>
        {meta ? <em>{meta}</em> : null}
      </span>
    </div>
  )
}

type ProgressBarProps = {
  value: number
  label?: string | undefined
  tone?: MetricTone
  showValue?: boolean | undefined
  className?: string | undefined
}

export function ProgressBar({
  value,
  label,
  tone = 'gold',
  showValue = false,
  className,
}: ProgressBarProps) {
  const bounded = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0))
  return (
    <div className={cx('ng-progress', `is-${tone}`, className)}>
      {(label || showValue) ? (
        <div className="ng-progress-head">
          {label ? <span>{label}</span> : <span />}
          {showValue ? <strong>{bounded.toLocaleString('fa-IR')}٪</strong> : null}
        </div>
      ) : null}
      <span className="ng-progress-track">
        <b style={{ width: `${bounded}%` }} />
      </span>
    </div>
  )
}
