import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { LiveIndicator, QuantityStepper, SegmentedControl } from './index'

describe('NeginAI shared design-system components', () => {
  it('changes a segmented selection through one canonical control', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()

    render(
      <SegmentedControl
        value="all"
        ariaLabel="فیلتر"
        onChange={onChange}
        items={[
          { value: 'all', label: 'همه', count: 4 },
          { value: 'unread', label: 'خوانده‌نشده', count: 2 },
        ]}
      />,
    )

    expect(screen.getByRole('tab', { name: /همه/ })).toHaveAttribute('aria-selected', 'true')
    await user.click(screen.getByRole('tab', { name: /خوانده‌نشده/ }))
    expect(onChange).toHaveBeenCalledWith('unread')
  })

  it('exposes live connection state accessibly', () => {
    render(<LiveIndicator state="connected" />)
    expect(screen.getByRole('status')).toHaveTextContent('اتصال زنده برقرار')
    expect(screen.getByRole('status')).toHaveClass('is-connected')
  })

  it('routes quantity actions through the shared stepper', async () => {
    const onDecrease = vi.fn()
    const onIncrease = vi.fn()
    const user = userEvent.setup()

    render(
      <QuantityStepper
        value="۳"
        unit="کارتن"
        onDecrease={onDecrease}
        onIncrease={onIncrease}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'افزایش' }))
    await user.click(screen.getByRole('button', { name: 'کاهش' }))
    expect(onIncrease).toHaveBeenCalledTimes(1)
    expect(onDecrease).toHaveBeenCalledTimes(1)
  })
})
