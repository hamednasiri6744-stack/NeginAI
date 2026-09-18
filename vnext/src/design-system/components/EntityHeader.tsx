import type { ReactNode } from 'react'
import { cx } from './utils'

type EntityHeaderProps = {
  icon?: ReactNode | undefined
  title: string
  subtitle?: ReactNode | undefined
  context?: ReactNode | undefined
  statuses?: ReactNode | undefined
  onBack?: (() => void) | undefined
  backIcon?: ReactNode | undefined
  children?: ReactNode | undefined
  className?: string | undefined
}

export function EntityHeader({
  icon,
  title,
  subtitle,
  context,
  statuses,
  onBack,
  backIcon,
  children,
  className,
}: EntityHeaderProps) {
  return (
    <section className={cx('ng-entity-header', className)}>
      {icon ? <span className="ng-entity-header-icon" aria-hidden="true">{icon}</span> : null}
      <div className="ng-entity-header-copy">
        <div className="ng-entity-header-title">
          <h2>{title}</h2>
          {statuses ? <span className="ng-entity-header-statuses">{statuses}</span> : null}
        </div>
        {subtitle ? <p>{subtitle}</p> : null}
        {context ? <span className="ng-entity-header-context">{context}</span> : null}
        {children}
      </div>
      {onBack ? (
        <button className="ng-entity-header-back ng-interactive" type="button" onClick={onBack} aria-label="بازگشت">
          {backIcon ?? '‹'}
        </button>
      ) : null}
    </section>
  )
}
