import { Bell, Home, LayoutGrid, Bot, BarChart3, MoreHorizontal } from 'lucide-react'
import type { ReactNode } from 'react'
import { BottomNavigation, Cluster, NotificationButton, ProfileChip, TopAppBar } from '../design-system/v2'
import type { PrimaryDestination } from '../app/navigation'

const items = [
  { id: 'home', label: 'خانه', icon: <Home size={20} /> },
  { id: 'modules', label: 'ماژول‌ها', icon: <LayoutGrid size={20} /> },
  { id: 'ai', label: 'Negin AI', icon: <Bot size={20} /> },
  { id: 'reports', label: 'گزارش‌ها', icon: <BarChart3 size={20} /> },
  { id: 'more', label: 'بیشتر', icon: <MoreHorizontal size={20} /> },
]

type Props = { active: PrimaryDestination; onNavigate: (id: PrimaryDestination) => void; children: ReactNode }

export function V2ReviewShell({ active, onNavigate, children }: Props) {
  return (
    <div className="ng-v2" dir="rtl" data-trace-id="NG-V2-APP-SHELL">
      <TopAppBar
        title="Negin AI"
        subtitle="Enterprise Operational & AI Platform"
        actions={
          <Cluster gap={2}>
            <NotificationButton count={3}><Bell size={18} /></NotificationButton>
            <ProfileChip name="کاربر Negin AI" subtitle="حساب فعال" avatar="NA" />
          </Cluster>
        }
      />
      <main>{children}</main>
      <BottomNavigation items={items} activeId={active} onNavigate={(id) => onNavigate(id as PrimaryDestination)} />
    </div>
  )
}
