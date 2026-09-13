import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

export type NotificationKind = 'price' | 'promotion' | 'stock' | 'customer' | 'kpi' | 'route'
export type NotificationPriority = 'high' | 'medium' | 'low'

export type VisitorNotificationItem = {
  id: number
  kind: NotificationKind
  priority: NotificationPriority
  title: string
  body: string
  time: string
  read: boolean
  actionLabel: string
  target: string
}

const initialNotifications: VisitorNotificationItem[] = [
  { id: 1, kind: 'price', priority: 'high', title: 'تغییر قیمت در سبد امروز', body: 'قیمت ۴ قلم از کالاهای پرتکرار مسیر امروز به‌روزرسانی شده است. قبل از ثبت سفارش بررسی کن.', time: '۱۰ دقیقه پیش', read: false, actionLabel: 'مشاهده کالاها', target: '/visitor/orders' },
  { id: 2, kind: 'customer', priority: 'high', title: 'مشتری نیازمند پیگیری', body: 'فروشگاه سعیدی ۱۲ روز است سفارش جدید ثبت نکرده و در اولویت پیگیری امروز قرار گرفته است.', time: '۲۸ دقیقه پیش', read: false, actionLabel: 'پروفایل مشتری', target: '/visitor/customers/3' },
  { id: 3, kind: 'route', priority: 'medium', title: 'به‌روزرسانی مسیر بازدید', body: 'ترتیب دو ایستگاه مسیر امروز برای کاهش زمان رفت‌وآمد اصلاح شده است.', time: '۴۵ دقیقه پیش', read: false, actionLabel: 'مشاهده مسیر', target: '/visitor/route' },
  { id: 4, kind: 'promotion', priority: 'medium', title: 'پروموشن جدید فعال شد', body: 'برای گروه شوینده منتخب، تخفیف پلکانی جدید تا پایان امروز فعال است.', time: '۱ ساعت پیش', read: true, actionLabel: 'مشاهده کاتالوگ', target: '/visitor/orders' },
  { id: 5, kind: 'kpi', priority: 'low', title: 'نرخ تبدیل امروز بالاتر از میانگین است', body: 'نرخ تبدیل بازدید به سفارش امروز به ۶۴٪ رسیده و از میانگین هفتگی بالاتر است.', time: '۲ ساعت پیش', read: true, actionLabel: 'گزارش عملکرد', target: '/visitor/reports' },
  { id: 6, kind: 'stock', priority: 'medium', title: 'موجودی یک کالای پرفروش محدود شده', body: 'موجودی قابل فروش یک قلم در انبار البرز به محدوده هشدار رسیده است.', time: '۳ ساعت پیش', read: true, actionLabel: 'مشاهده موجودی', target: '/visitor/orders' },
]

type VisitorNotificationsValue = {
  items: VisitorNotificationItem[]
  unreadCount: number
  markRead: (id: number) => void
  markAllRead: () => void
  resetNotifications: () => void
}

const VisitorNotificationsContext = createContext<VisitorNotificationsValue | null>(null)

export function VisitorNotificationsProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<VisitorNotificationItem[]>(initialNotifications)

  const markRead = useCallback((id: number) => {
    setItems((current) => current.map((item) => item.id === id ? { ...item, read: true } : item))
  }, [])

  const markAllRead = useCallback(() => {
    setItems((current) => current.map((item) => ({ ...item, read: true })))
  }, [])

  const resetNotifications = useCallback(() => setItems(initialNotifications), [])
  const unreadCount = useMemo(() => items.filter((item) => !item.read).length, [items])
  const value = useMemo<VisitorNotificationsValue>(() => ({ items, unreadCount, markRead, markAllRead, resetNotifications }), [items, markAllRead, markRead, resetNotifications, unreadCount])

  return <VisitorNotificationsContext.Provider value={value}>{children}</VisitorNotificationsContext.Provider>
}

export function useVisitorNotifications() {
  const value = useContext(VisitorNotificationsContext)
  if (!value) throw new Error('useVisitorNotifications must be used inside VisitorNotificationsProvider')
  return value
}
