import { useState } from 'react'
import type { Meta, StoryObj } from '@storybook/react-vite'
import {
  AppHeader,
  BottomDock,
  BottomSheet,
  Button,
  EntityHeader,
  InsightCard,
  Metric,
  ProgressBar,
  QuantityStepper,
  StatusChip,
  Surface,
} from '../components'
import {
  BellIcon,
  ChartIcon,
  ChevronLeftIcon,
  HomeIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  UserGroupIcon,
} from '../../components/Icons'

function NavigationAndStatesPreview() {
  const [sheetOpen, setSheetOpen] = useState(false)
  return (
    <Surface tone="stage" style={{ width: 'min(920px, 94vw)', minHeight: 560, padding: 20, paddingBottom: 110 }}>
      <div style={{ display: 'grid', gap: 16 }}>
        <AppHeader
          avatarText="ن"
          title="نمونه کاربر"
          subtitle="دفتر فروش البرز"
          subtitleIcon={<PinIcon />}
          profileTrailing={<ChevronLeftIcon />}
          action={<button type="button" aria-label="اعلان‌ها"><BellIcon /></button>}
        />

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <StatusChip tone="success" dot>زنده</StatusChip>
          <StatusChip tone="gold">هدف فعال</StatusChip>
          <StatusChip tone="danger">ریسک</StatusChip>
          <StatusChip tone="info">هوشمند</StatusChip>
        </div>

        <Surface tone="detail" style={{ padding: 16, display: 'grid', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
            <Metric label="فروش امروز" value="۱۲.۴ م" meta="ریال" tone="gold" />
            <Metric label="مسیر" value="۷۲٪" meta="پیشرفت" tone="success" />
            <Metric label="هشدار" value="۳" meta="نیازمند توجه" tone="danger" />
          </div>
          <ProgressBar value={72} label="پیشرفت مسیر امروز" tone="success" showValue />
        </Surface>

        <EntityHeader
          icon={<span>◆</span>}
          title="داروخانه نمونه"
          subtitle="کد ۱۲۳۴"
          context="کرج · مسیر امروز"
          statuses={<><StatusChip tone="success" dot>زنده</StatusChip><StatusChip tone="danger">ریسک</StatusChip></>}
        />

        <InsightCard
          icon={<BellIcon />}
          eyebrow="Next Best Action"
          title="اعتبار مشتری را بررسی کن"
          body="پیش از ثبت سفارش بعدی وضعیت اعتبار نیازمند توجه است."
          tone="warning"
          actionLabel="بررسی"
          onAction={() => undefined}
        />

        <QuantityStepper value="۳" unit="کارتن" onDecrease={() => undefined} onIncrease={() => undefined} />
        <Button variant="secondary" onClick={() => setSheetOpen(true)}>باز کردن Bottom Sheet</Button>
      </div>

      <BottomDock
        items={[
          { key: 'home', label: 'خانه', icon: <HomeIcon />, active: true, onClick: () => undefined },
          { key: 'route', label: 'مسیر', icon: <MapIcon />, onClick: () => undefined },
          { key: 'customers', label: 'مشتریان', icon: <UserGroupIcon />, onClick: () => undefined },
          { key: 'reports', label: 'گزارش‌ها', icon: <ChartIcon />, onClick: () => undefined },
        ]}
        primary={{ label: 'سفارش', icon: <PlusIcon />, onClick: () => undefined }}
      />

      <BottomSheet
        open={sheetOpen}
        title="جزئیات"
        description="نمونه لایه عمقی مشترک"
        onClose={() => setSheetOpen(false)}
        footer={<Button variant="primary" onClick={() => setSheetOpen(false)}>تأیید</Button>}
      >
        <p style={{ margin: 0, color: 'var(--ng-muted)', lineHeight: 1.8 }}>
          این Bottom Sheet از لایه مشترک Design System می‌آید و صفحه‌ها نباید نسخه مستقل خودشان را بسازند.
        </p>
      </BottomSheet>
    </Surface>
  )
}

const meta = {
  title: 'Design System/Navigation & States',
  component: NavigationAndStatesPreview,
  tags: ['autodocs'],
} satisfies Meta<typeof NavigationAndStatesPreview>

export default meta
type Story = StoryObj<typeof meta>
export const Overview: Story = {}
