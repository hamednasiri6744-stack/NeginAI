import type { ReactNode } from 'react'

type AuthPatternProps = {
  title: string
  description?: string
  eyebrow?: string
  brandTitle?: string
  brandSubtitle?: string
  children: ReactNode
  footer?: ReactNode
}

export function AuthPattern({
  title,
  description,
  eyebrow = 'Secure Enterprise Workspace',
  brandTitle = 'Negin AI',
  brandSubtitle = 'پلتفرم عملیاتی و هوشمند نگین پخش',
  children,
  footer,
}: AuthPatternProps) {
  return (
    <main className="ng-auth-pattern" dir="rtl">
      <div className="ng-auth-pattern__ambient" aria-hidden="true" />
      <section className="ng-auth-pattern__shell">
        <aside className="ng-auth-pattern__brand" aria-label="Negin AI">
          <div className="ng-auth-pattern__logo-wrap">
            <img src="/brand/neginai-logo-canonical.webp" alt="Negin AI" />
          </div>
          <span className="ng-auth-pattern__eyebrow">{eyebrow}</span>
          <h1>{brandTitle}</h1>
          <p>{brandSubtitle}</p>
          <div className="ng-auth-pattern__brand-line" aria-hidden="true" />
          <small>امن · سازمانی · RTL-first</small>
        </aside>

        <section className="ng-auth-pattern__panel">
          <header className="ng-auth-pattern__header">
            <span>ورود امن سازمانی</span>
            <h2>{title}</h2>
            {description ? <p>{description}</p> : null}
          </header>
          <div className="ng-auth-pattern__body">{children}</div>
          {footer ? <footer className="ng-auth-pattern__footer">{footer}</footer> : null}
        </section>
      </section>
    </main>
  )
}

export function AuthStatusPattern({ children }: { children: ReactNode }) {
  return (
    <main className="ng-auth-pattern ng-auth-pattern--status" dir="rtl">
      <div className="ng-auth-pattern__ambient" aria-hidden="true" />
      <section className="ng-auth-pattern__status">{children}</section>
    </main>
  )
}
