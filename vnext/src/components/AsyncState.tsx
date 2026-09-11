import { AlertTriangle, LoaderCircle, RotateCcw } from 'lucide-react'

export function AsyncState({
  mode,
  title,
  message,
  onRetry,
}: {
  mode: 'loading' | 'error' | 'empty'
  title: string
  message?: string
  onRetry?: () => void
}) {
  const Icon = mode === 'error' ? AlertTriangle : LoaderCircle
  return (
    <section className={`ng-async-state ng-async-state--${mode}`} role={mode === 'error' ? 'alert' : 'status'}>
      <Icon className={mode === 'loading' ? 'is-spinning' : ''} size={24} />
      <strong>{title}</strong>
      {message ? <span>{message}</span> : null}
      {onRetry ? (
        <button type="button" className="ng-secondary-button" onClick={onRetry}>
          تلاش دوباره <RotateCcw size={16} />
        </button>
      ) : null}
    </section>
  )
}
