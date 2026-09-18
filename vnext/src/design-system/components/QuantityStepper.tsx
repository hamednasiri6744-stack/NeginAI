import { cx } from './utils'

type QuantityStepperProps = {
  value: string | number
  unit?: string | undefined
  onDecrease: () => void
  onIncrease: () => void
  decreaseDisabled?: boolean | undefined
  increaseDisabled?: boolean | undefined
  className?: string | undefined
  ariaLabel?: string | undefined
}

export function QuantityStepper({
  value,
  unit,
  onDecrease,
  onIncrease,
  decreaseDisabled = false,
  increaseDisabled = false,
  className,
  ariaLabel = 'تعداد',
}: QuantityStepperProps) {
  return (
    <div className={cx('ng-quantity-stepper', className)} role="group" aria-label={ariaLabel}>
      <button className="ng-interactive" type="button" onClick={onDecrease} disabled={decreaseDisabled} aria-label="کاهش">−</button>
      <strong>
        <b>{value}</b>
        {unit ? <small>{unit}</small> : null}
      </strong>
      <button className="ng-interactive" type="button" onClick={onIncrease} disabled={increaseDisabled} aria-label="افزایش">+</button>
    </div>
  )
}
