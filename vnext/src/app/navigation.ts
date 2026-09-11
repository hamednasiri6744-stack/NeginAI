import {
  BarChart3,
  Bot,
  Boxes,
  CalendarDays,
  ClipboardList,
  Database,
  Home,
  MoreHorizontal,
  PackageSearch,
  Route,
  ShieldCheck,
  Users,
  Warehouse,
  Workflow,
} from 'lucide-react'

export type PrimaryDestination = 'home' | 'modules' | 'ai' | 'reports' | 'more'

export const primaryNavigation = [
  { id: 'home', label: '\u062e\u0627\u0646\u0647', icon: Home, traceId: 'NAV-001' },
  { id: 'modules', label: '\u0645\u0627\u0698\u0648\u0644\u200c\u0647\u0627', icon: Boxes, traceId: 'NAV-002' },
  { id: 'ai', label: 'Negin AI', icon: Bot, traceId: 'NAV-003', emphasized: true },
  { id: 'reports', label: '\u06af\u0632\u0627\u0631\u0634\u200c\u0647\u0627', icon: BarChart3, traceId: 'NAV-004' },
  { id: 'more', label: '\u0628\u06cc\u0634\u062a\u0631', icon: MoreHorizontal, traceId: 'NAV-005' },
] as const

export const moduleCatalog = [
  { id: 'MOD-04', label: '\u0645\u0633\u06cc\u0631 \u0648 \u0648\u06cc\u0632\u06cc\u062a', icon: Route, description: '\u0645\u0633\u06cc\u0631\u0647\u0627\u060c \u0645\u0634\u062a\u0631\u06cc\u200c\u0647\u0627 \u0648 \u0627\u0648\u0644\u0648\u06cc\u062a \u0648\u06cc\u0632\u06cc\u062a' },
  { id: 'MOD-06', label: 'Customer 360', icon: Users, description: '\u067e\u0631\u0648\u0641\u0627\u06cc\u0644 \u062c\u0627\u0645\u0639 \u0645\u0634\u062a\u0631\u06cc' },
  { id: 'MOD-09', label: '\u06a9\u0627\u062a\u0627\u0644\u0648\u06af \u0648 \u0645\u0648\u062c\u0648\u062f\u06cc', icon: PackageSearch, description: '\u06a9\u0627\u0644\u0627\u060c \u0642\u06cc\u0645\u062a\u060c \u0645\u0648\u062c\u0648\u062f\u06cc \u0648 \u062a\u062e\u0641\u06cc\u0641' },
  { id: 'MOD-10', label: '\u0633\u0641\u0627\u0631\u0634\u200c\u06af\u06cc\u0631\u06cc', icon: ClipboardList, description: '\u0633\u0628\u062f\u060c \u067e\u06cc\u0634\u200c\u0646\u0648\u06cc\u0633 \u0648 \u0627\u0631\u0633\u0627\u0644 \u0633\u0641\u0627\u0631\u0634' },
  { id: 'MOD-15', label: '\u06af\u0632\u0627\u0631\u0634\u200c\u0647\u0627', icon: BarChart3, description: 'KPI \u0648 \u06af\u0632\u0627\u0631\u0634\u200c\u0647\u0627\u06cc \u0639\u0645\u0644\u06cc\u0627\u062a\u06cc' },
  { id: 'MOD-18', label: '\u0628\u0631\u0646\u0627\u0645\u0647\u200c\u0631\u06cc\u0632\u06cc', icon: CalendarDays, description: '\u0633\u0646\u0627\u0631\u06cc\u0648 \u0648 \u0628\u0631\u0646\u0627\u0645\u0647\u200c\u0631\u06cc\u0632\u06cc' },
  { id: 'MOD-19', label: '\u06a9\u0646\u062a\u0631\u0644 \u062f\u0633\u062a\u0631\u0633\u06cc', icon: ShieldCheck, description: '\u0646\u0642\u0634\u060c \u0645\u062c\u0648\u0632 \u0648 \u0633\u0627\u062e\u062a\u0627\u0631 \u0633\u0627\u0632\u0645\u0627\u0646\u06cc' },
  { id: 'MOD-21', label: '\u0627\u0646\u0628\u0627\u0631', icon: Warehouse, description: '\u0645\u0648\u062c\u0648\u062f\u06cc \u0648 \u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u0633\u0641\u0627\u0631\u0634' },
  { id: 'MOD-23', label: '\u0627\u062a\u0648\u0645\u0627\u0633\u06cc\u0648\u0646', icon: Workflow, description: '\u06af\u0631\u062f\u0634\u200c\u06a9\u0627\u0631 \u0648 \u0647\u0634\u062f\u0627\u0631\u0647\u0627' },
  { id: 'MOD-16', label: '\u062f\u0627\u062f\u0647 \u0648 Schema', icon: Database, description: '\u06a9\u0627\u062a\u0627\u0644\u0648\u06af \u062f\u0627\u062f\u0647 \u0648 Entity' },
] as const
