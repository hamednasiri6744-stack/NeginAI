import { cx } from './utils'

export type SegmentedItem<T extends string> = {
  value: T
  label: string
  count?: number
  disabled?: boolean
}

type SegmentedControlProps<T extends string> = {
  value: T
  items: readonly SegmentedItem<T>[]
  onChange: (value: T) => void
  ariaLabel: string
  className?: string
}

export function SegmentedControl<T extends string>({
  value,
  items,
  onChange,
  ariaLabel,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div className={cx('ng-segmented', className)} role="tablist" aria-label={ariaLabel}>
      {items.map((item) => {
        const selected = item.value === value
        return (
          <button
            key={item.value}
            className={cx('ng-segmented-item', 'ng-interactive', selected && 'is-active')}
            type="button"
            role="tab"
            aria-selected={selected}
            disabled={item.disabled}
            onClick={() => onChange(item.value)}
          >
            <span>{item.label}</span>
            {typeof item.count === 'number' ? <b>{item.count.toLocaleString('fa-IR')}</b> : null}
          </button>
        )
      })}
    </div>
  )
}
