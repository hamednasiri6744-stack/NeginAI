import type { ReactNode } from 'react'
import { cx } from './utils'

type AppHeaderProps = {
  avatarText: string
  title: string
  subtitle: string
  subtitleIcon?: ReactNode | undefined
  profileTrailing?: ReactNode | undefined
  onProfileClick?: (() => void) | undefined
  action?: ReactNode | undefined
  brandLogo?: string | undefined
  brandAlt?: string | undefined
  brandName?: string | undefined
  brandAccent?: string | undefined
  brandSubtitle?: string | undefined
  className?: string | undefined
}

export function AppHeader({
  avatarText,
  title,
  subtitle,
  subtitleIcon,
  profileTrailing,
  onProfileClick,
  action,
  brandLogo = '/assets/neginai-logo-transparent.png',
  brandAlt = 'Negin AI',
  brandName = 'Negin',
  brandAccent = 'AI',
  brandSubtitle = 'VISITOR',
  className,
}: AppHeaderProps) {
  return (
    <header className={cx('ng-app-header', className)}>
      <button className="ng-app-profile ng-interactive" type="button" onClick={onProfileClick}>
        <span className="ng-app-avatar">{avatarText}</span>
        <span className="ng-app-profile-copy">
          <strong>{title}</strong>
          <small>{subtitleIcon}{subtitle}</small>
        </span>
        {profileTrailing ? <span className="ng-app-profile-trailing">{profileTrailing}</span> : null}
      </button>

      <div className="ng-app-header-action">{action}</div>
      <div className="ng-app-brand" dir="ltr">
        <img src={brandLogo} alt={brandAlt} />
        <div>
          <strong>{brandName} <span>{brandAccent}</span></strong>
          <small>{brandSubtitle}</small>
        </div>
      </div>
    </header>
  )
}
