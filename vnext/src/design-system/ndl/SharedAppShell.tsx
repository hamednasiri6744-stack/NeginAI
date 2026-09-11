import type { ReactNode } from 'react'
import { AppHeader, BottomNavigation, CommandBar, type NavigationItem } from './navigation'
import './ndl.css'

export type SharedAppShellProps = {
  children: ReactNode
  navigation: NavigationItem[]
  activeNavigationId: string
  onNavigate: (id: string) => void
  header?: ReactNode
  commandBar?: ReactNode
  footer?: ReactNode
  label?: string
  preview?: boolean
}

export function SharedAppShell({ children, navigation, activeNavigationId, onNavigate, header, commandBar, footer, label = 'NeginAI', preview = false }: SharedAppShellProps) {
  return (
    <div className={`ndl-shell ${preview ? 'ndl-shell--preview' : ''}`} dir="rtl" data-ndl-component="SharedAppShell">
      {header ?? <AppHeader brand={label} subtitle="NDL-1.0" />}
      <div className="ndl-shell__command">{commandBar ?? <CommandBar />}</div>
      <main className="ndl-shell__main">{children}</main>
      {footer}
      <BottomNavigation items={navigation} activeId={activeNavigationId} onNavigate={onNavigate} />
    </div>
  )
}
