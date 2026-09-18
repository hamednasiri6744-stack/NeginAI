import { cx } from './utils'

export type LiveIndicatorState = 'connected' | 'reconnecting' | 'offline'

type LiveIndicatorProps = {
  state: LiveIndicatorState
  connectedLabel?: string
  reconnectingLabel?: string
  offlineLabel?: string
  className?: string
}

export function LiveIndicator({
  state,
  connectedLabel = 'اتصال زنده برقرار',
  reconnectingLabel = 'در حال اتصال زنده',
  offlineLabel = 'آفلاین',
  className,
}: LiveIndicatorProps) {
  const label = state === 'connected'
    ? connectedLabel
    : state === 'reconnecting'
      ? reconnectingLabel
      : offlineLabel

  return (
    <span className={cx('ng-live-indicator', `is-${state}`, className)} role="status">
      <i aria-hidden="true" />
      {label}
    </span>
  )
}
