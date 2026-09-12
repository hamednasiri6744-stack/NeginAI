import { Bell } from 'lucide-react'
import type { ReactNode } from 'react'
import { primaryNavigation, type PrimaryDestination } from '../app/navigation'
import { BottomNavigation, Cluster, NotificationButton, ProfileChip } from '../design-system/v2'

type AppShellProps = {
  active: PrimaryDestination
  onNavigate: (destination: PrimaryDestination) => void
  children: ReactNode
}

export function AppShell({ active, onNavigate, children }: AppShellProps) {
  const items = primaryNavigation.map((item) => {
    const Icon = item.icon
    return { id: item.id, label: item.label, icon: <Icon size={20} strokeWidth={1.8} /> }
  })

  return (
    <div className="ng-v2 ng-app-shell-v2 ng-shell-v21" dir="rtl" data-trace-id="SHL-V2">
      <header className="ng-shell-v21__topbar">
        <div className="ng-shell-v21__brand" aria-label="Negin AI">
          <img src="/brand/neginai-logo-canonical.webp" alt="Negin AI" />
          <span>
            <strong dir="ltr">Negin AI</strong>
            <small>همراه شما در مسیر رشد</small>
          </span>
        </div>
        <Cluster gap={2}>
          <NotificationButton count={3} label="اعلان‌ها"><Bell size={19}/></NotificationButton>
          <ProfileChip name="ویزیتور Negin AI" subtitle="حساب فعال" avatar="NA"/>
        </Cluster>
      </header>
      <main className="ng-app-shell-v2__main" data-trace-id="SHL-V2-MAIN">{children}</main>
      <BottomNavigation items={items} activeId={active} onNavigate={(id)=>onNavigate(id as PrimaryDestination)} />
    </div>
  )
}
