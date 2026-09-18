import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cx } from './utils'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  icon?: ReactNode
}

export function Button({
  variant = 'secondary',
  icon,
  className,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx('ng-button', `ng-action-${variant}`, 'ng-interactive', className)}
      {...props}
    >
      {icon ? <span className="ng-button-icon" aria-hidden="true">{icon}</span> : null}
      {children}
    </button>
  )
}
