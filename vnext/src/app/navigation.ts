import {
  Bot,
  Boxes,
  Home,
  MoreHorizontal,
  Route,
  BarChart3,
  Users,
  PackageSearch,
  ClipboardList,
  Warehouse,
  Workflow,
  Database,
  CalendarDays,
  ShieldCheck,
} from 'lucide-react'

export type PrimaryDestination = 'home' | 'modules' | 'ai' | 'reports' | 'more'

export const primaryNavigation = [
  { id: 'home', label: 'خانه', icon: Home, traceId: 'NAV-001' },
  { id: 'modules', label: 'ماژول‌ها', icon: Boxes, traceId: 'NAV-002' },
  { id: 'ai', label: 'دستیار AI', icon: Bot, traceId: 'NAV-003', emphasized: true },
  { id: 'reports', label: 'گزارش‌ها', icon: BarChart3, traceId: 'NAV-004' },
  { id: 'more', label: 'بیشتر', icon: MoreHorizontal, traceId: 'NAV-005' },
] as const

export const moduleCatalog = [
  { id: 'MOD-04', label: 'ویزیت و فروش', icon: Route, description: 'مسیر، مشتری، پیش‌ویزیت و سفارش' },
  { id: 'MOD-06', label: 'Customer 360', icon: Users, description: 'پروفایل و زمینه عملیاتی مشتری' },
  { id: 'MOD-09', label: 'کاتالوگ محصول', icon: PackageSearch, description: 'محصول، فیلتر، موجودی و انتخاب' },
  { id: 'MOD-10', label: 'سفارش‌گیری', icon: ClipboardList, description: 'سبد، Preview و ثبت درخواست' },
  { id: 'MOD-15', label: 'گزارش‌ها', icon: BarChart3, description: 'گزارش‌ها و KPIهای Semantic-aware' },
  { id: 'MOD-18', label: 'برنامه‌ریزی', icon: CalendarDays, description: 'Planning و سناریوهای عملیاتی' },
  { id: 'MOD-19', label: 'کنترل سازمانی', icon: ShieldCheck, description: 'کنترل، مجوز و نظارت سازمانی' },
  { id: 'MOD-21', label: 'دستیار انبار', icon: Warehouse, description: 'Context و عملیات مجاز انبار' },
  { id: 'MOD-23', label: 'اتوماسیون‌ها', icon: Workflow, description: 'Workflow، اجرا و وضعیت' },
  { id: 'MOD-16', label: 'داده و Schema', icon: Database, description: 'Catalog، Context و Entity' },
] as const
