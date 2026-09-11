import { Bell } from 'lucide-react'
import type { ReactNode } from 'react'
import { primaryNavigation, type PrimaryDestination } from '../app/navigation'
import { BottomNavigation, Cluster, NotificationButton, ProfileChip, TopAppBar } from '../design-system/v2'

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
    <div className="ng-v2 ng-app-shell-v2" dir="rtl" data-trace-id="SHL-V2">
      <TopAppBar
        title="Negin AI"
        subtitle={'\u0633\u0627\u0645\u0627\u0646\u0647 \u0639\u0645\u0644\u06cc\u0627\u062a\u06cc \u0648 \u0647\u0648\u0634\u0645\u0646\u062f \u0646\u06af\u06cc\u0646 \u067e\u062e\u0634'}
        actions={
          <Cluster gap={2}>
            <NotificationButton count={3} label={'\u0627\u0639\u0644\u0627\u0646\u200c\u0647\u0627'}><Bell size={19}/></NotificationButton>
            <ProfileChip name={'\u0648\u06cc\u0632\u06cc\u062a\u0648\u0631 Negin AI'} subtitle={'\u062d\u0633\u0627\u0628 \u0641\u0639\u0627\u0644'} avatar="NA"/>
          </Cluster>
        }
      />
      <main className="ng-app-shell-v2__main" data-trace-id="SHL-V2-MAIN">{children}</main>
      <BottomNavigation items={items} activeId={active} onNavigate={(id)=>onNavigate(id as PrimaryDestination)} />
    </div>
  )
}
