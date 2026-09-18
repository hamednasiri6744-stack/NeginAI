import { useEffect, type ReactNode } from 'react'
import { cx } from './utils'

type BottomSheetProps = {
  open: boolean
  title: string
  description?: string | undefined
  onClose: () => void
  children: ReactNode
  footer?: ReactNode | undefined
  className?: string | undefined
}

export function BottomSheet({
  open,
  title,
  description,
  onClose,
  children,
  footer,
  className,
}: BottomSheetProps) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, open])

  if (!open) return null

  return (
    <div className={cx('ng-sheet-layer', className)} role="presentation">
      <button className="ng-sheet-backdrop" type="button" aria-label="بستن" onClick={onClose} />
      <section className="ng-bottom-sheet" role="dialog" aria-modal="true" aria-label={title}>
        <div className="ng-sheet-handle" aria-hidden="true" />
        <header className="ng-sheet-header">
          <div>
            <strong>{title}</strong>
            {description ? <small>{description}</small> : null}
          </div>
          <button className="ng-sheet-close ng-interactive" type="button" onClick={onClose} aria-label="بستن">×</button>
        </header>
        <div className="ng-sheet-body">{children}</div>
        {footer ? <footer className="ng-sheet-footer">{footer}</footer> : null}
      </section>
    </div>
  )
}
