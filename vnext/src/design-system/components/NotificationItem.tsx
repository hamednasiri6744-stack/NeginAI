import type { ReactNode } from 'react'
import { cx } from './utils'

export type NotificationTone = 'critical' | 'high' | 'medium' | 'info'

type NotificationItemProps = {
  icon?: ReactNode
  tone: NotificationTone
  toneLabel: string
  categoryLabel: string
  timeLabel: string
  title: string
  body: string
  sourceLabel?: string
  unread?: boolean
  attention?: boolean
  acknowledgeLabel?: string
  acknowledgeHint?: string
  onOpen?: (() => void) | undefined
  onAcknowledge?: (() => void) | undefined
  trailing?: ReactNode | undefined
  className?: string | undefined
}

export function NotificationItem({
  icon,
  tone,
  toneLabel,
  categoryLabel,
  timeLabel,
  title,
  body,
  sourceLabel,
  unread = false,
  attention = false,
  acknowledgeLabel = 'تأیید کردم',
  acknowledgeHint = 'این اعلان نیازمند تأیید شماست',
  onOpen,
  onAcknowledge,
  trailing,
  className,
}: NotificationItemProps) {
  return (
    <article
      className={cx('ng-notification-item', `is-${tone}`, unread ? 'is-unread' : 'is-read', className)}
      data-state={attention ? 'attention' : unread ? 'live' : 'settled'}
    >
      <button className="ng-notification-main ng-interactive" type="button" onClick={onOpen}>
        <span className="ng-notification-icon" aria-hidden="true">{icon}</span>
        <span className="ng-notification-copy">
          <span className="ng-notification-meta">
            <b className={cx('ng-notification-tone', `is-${tone}`)}>{toneLabel}</b>
            <i>{categoryLabel}</i>
            <time>{timeLabel}</time>
          </span>
          <strong>{title}</strong>
          <small>{body}</small>
          {sourceLabel ? <em>{sourceLabel}</em> : null}
        </span>
        <span className="ng-notification-trailing">
          {trailing ?? (unread || attention ? <i className="ng-unread-dot" /> : null)}
        </span>
      </button>
      {attention && onAcknowledge ? (
        <div className="ng-notification-ack">
          <span>{acknowledgeHint}</span>
          <button className="ng-interactive" type="button" onClick={onAcknowledge}>{acknowledgeLabel}</button>
        </div>
      ) : null}
    </article>
  )
}
