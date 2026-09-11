import {
  Eye,
  EyeOff,
  LoaderCircle,
  Search,
} from 'lucide-react'
import {
  forwardRef,
  useId,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from 'react'
import './ndl.css'

function classes(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ')
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'small' | 'medium' | 'large'
  loading?: boolean
  startIcon?: ReactNode
  endIcon?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'medium', loading = false, startIcon, endIcon, className, children, disabled, type = 'button', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={classes('ndl-button', `ndl-button--${variant}`, `ndl-button--${size}`, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <LoaderCircle className="ndl-spin" size={18} aria-hidden="true" /> : startIcon}
      <span>{children}</span>
      {!loading && endIcon}
    </button>
  )
})

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string
  variant?: 'default' | 'premium' | 'danger'
  size?: 'medium' | 'large'
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, variant = 'default', size = 'medium', className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={classes('ndl-icon-button', `ndl-icon-button--${variant}`, `ndl-icon-button--${size}`, className)}
      aria-label={label}
      title={props.title ?? label}
      {...props}
    >
      {children}
    </button>
  )
})

export type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> & {
  label: string
  hint?: string
  error?: string
  leading?: ReactNode
  trailing?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, leading, trailing, className, id: providedId, ...props },
  ref,
) {
  const generatedId = useId()
  const id = providedId ?? generatedId
  const messageId = `${id}-message`
  return (
    <label className={classes('ndl-field', error && 'ndl-field--error', className)} htmlFor={id}>
      <span className="ndl-field__label">{label}</span>
      <span className="ndl-field__control">
        {leading ? <span className="ndl-field__adornment" aria-hidden="true">{leading}</span> : null}
        <input
          ref={ref}
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={hint || error ? messageId : undefined}
          {...props}
        />
        {trailing ? <span className="ndl-field__adornment">{trailing}</span> : null}
      </span>
      {error || hint ? (
        <span id={messageId} className="ndl-field__message" role={error ? 'alert' : undefined}>
          {error ?? hint}
        </span>
      ) : null}
    </label>
  )
})

export function PasswordInput(props: Omit<InputProps, 'type' | 'trailing'>) {
  const [visible, setVisible] = useState(false)
  return (
    <Input
      {...props}
      type={visible ? 'text' : 'password'}
      trailing={(
        <IconButton
          className="ndl-field__action"
          label={visible ? 'پنهان‌کردن رمز عبور' : 'نمایش رمز عبور'}
          aria-pressed={visible}
          onClick={() => setVisible((value) => !value)}
        >
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </IconButton>
      )}
    />
  )
}

export function SearchInput(props: Omit<InputProps, 'type' | 'leading'>) {
  return <Input {...props} type="search" leading={<Search size={18} />} />
}

export type Tone = 'neutral' | 'premium' | 'info' | 'success' | 'warning' | 'danger'

export function Badge({ tone = 'neutral', children, className, ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return <span className={classes('ndl-badge', `ndl-tone--${tone}`, className)} {...props}>{children}</span>
}

export function Chip({ selected = false, children, className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { selected?: boolean }) {
  return (
    <button
      type="button"
      className={classes('ndl-chip', selected && 'is-selected', className)}
      aria-pressed={selected}
      {...props}
    >
      {children}
    </button>
  )
}

export function Surface({ level = 1, glass = false, className, ...props }: HTMLAttributes<HTMLDivElement> & { level?: 1 | 2 | 3; glass?: boolean }) {
  return <div className={classes('ndl-surface', `ndl-surface--${level}`, glass && 'ndl-surface--glass', className)} {...props} />
}

export function Card({ interactive = false, className, ...props }: HTMLAttributes<HTMLElement> & { interactive?: boolean }) {
  return <article className={classes('ndl-card', interactive && 'ndl-card--interactive', className)} {...props} />
}

export function Metric({ label, value, detail, trend, tone = 'neutral' }: { label: string; value: ReactNode; detail?: ReactNode; trend?: ReactNode; tone?: Tone }) {
  return (
    <div className="ndl-metric">
      <span className="ndl-metric__label">{label}</span>
      <strong className="ndl-metric__value">{value}</strong>
      {(detail || trend) && <span className="ndl-metric__meta">{detail}{trend ? <Badge tone={tone}>{trend}</Badge> : null}</span>}
    </div>
  )
}

export function Progress({ value, label }: { value: number; label: string }) {
  const bounded = Math.max(0, Math.min(100, value))
  return (
    <div className="ndl-progress">
      <span className="ndl-progress__label"><span>{label}</span><span dir="ltr">{bounded}%</span></span>
      <div className="ndl-progress__track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={bounded}>
        <span className="ndl-progress__bar" style={{ inlineSize: `${bounded}%` }} />
      </div>
    </div>
  )
}

export function Spinner({ label = 'در حال بارگذاری' }: { label?: string }) {
  return <span className="ndl-spinner" role="status"><LoaderCircle className="ndl-spin" aria-hidden="true" /><span className="ndl-visually-hidden">{label}</span></span>
}

export function Skeleton({ lines = 3, label = 'در حال بارگذاری محتوا' }: { lines?: number; label?: string }) {
  return (
    <div className="ndl-skeleton" role="status" aria-label={label}>
      {Array.from({ length: Math.max(1, lines) }, (_, index) => <span key={index} />)}
    </div>
  )
}

export function Avatar({ name, src, size = 'medium' }: { name: string; src?: string; size?: 'small' | 'medium' | 'large' }) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  return (
    <span className={classes('ndl-avatar', `ndl-avatar--${size}`)} aria-label={name} role="img">
      {src ? <img src={src} alt="" /> : initials}
    </span>
  )
}
