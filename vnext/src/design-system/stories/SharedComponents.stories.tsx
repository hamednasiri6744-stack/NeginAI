import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import {
  Button,
  FeedbackState,
  LiveIndicator,
  NotificationItem,
  SegmentedControl,
  Surface,
} from '../components'

function SharedComponentsPreview() {
  const [tab, setTab] = useState<'all' | 'unread' | 'read'>('all')
  const items = [
    { value: 'all' as const, label: 'همه', count: 12 },
    { value: 'unread' as const, label: 'خوانده‌نشده', count: 3 },
    { value: 'read' as const, label: 'خوانده‌شده', count: 9 },
  ]

  return (
    <Surface tone="stage" style={{ width: 'min(880px, 92vw)', padding: 20 }}>
      <div style={{ display: 'grid', gap: 16 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button variant="primary">اقدام اصلی</Button>
          <Button variant="secondary">ثانویه</Button>
          <Button variant="ghost">Ghost</Button>
          <LiveIndicator state="connected" />
        </div>

        <SegmentedControl value={tab} items={items} onChange={setTab} ariaLabel="نمونه فیلتر" />

        <Surface tone="detail" style={{ overflow: 'hidden' }}>
          <NotificationItem
            icon={<span>◉</span>}
            tone="high"
            toneLabel="بالا"
            categoryLabel="اعتباری"
            timeLabel="امروز · ۱۰:۴۵"
            title="اعتبار مشتری نیازمند بررسی است"
            body="پیش از ثبت سفارش بعدی، وضعیت اعتبار مشتری را بررسی کنید."
            sourceLabel="منبع: NGT"
            unread
            attention
            onAcknowledge={() => undefined}
          />
          <NotificationItem
            icon={<span>◌</span>}
            tone="info"
            toneLabel="اطلاعاتی"
            categoryLabel="مسیر"
            timeLabel="امروز · ۰۹:۲۰"
            title="برنامه مسیر همگام شد"
            body="تغییرات آخر مسیر ویزیتور دریافت شد."
            sourceLabel="منبع: NeginAI"
          />
        </Surface>

        <FeedbackState kind="loading" rows={2} description="در حال همگام‌سازی…" />
      </div>
    </Surface>
  )
}

const meta = {
  title: 'Design System/Shared Components',
  component: SharedComponentsPreview,
  tags: ['autodocs'],
} satisfies Meta<typeof SharedComponentsPreview>

export default meta
type Story = StoryObj<typeof meta>
export const Overview: Story = {}
