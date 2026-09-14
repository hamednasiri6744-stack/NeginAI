import { useMemo, useState, type CSSProperties } from 'react'
import {
  BellIcon,
  CartIcon,
  ChartIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  HomeIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  StoreIcon,
  UserGroupIcon,
} from './Icons'

import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'

type Props = { onNavigate: (path: string) => void }
type Period = 'today' | 'week' | 'month'

type ReportSnapshot = {
  sales: number
  orders: number
  visits: number
  target: number
  conversion: number
  avgOrder: number
  returned: number
  newCustomers: number
}

const snapshots: Record<Period, ReportSnapshot> = {
  today: { sales: 12_450_000, orders: 28, visits: 7, target: 78, conversion: 64, avgOrder: 445_000, returned: 320_000, newCustomers: 2 },
  week: { sales: 74_820_000, orders: 156, visits: 41, target: 84, conversion: 69, avgOrder: 479_600, returned: 1_840_000, newCustomers: 9 },
  month: { sales: 318_600_000, orders: 642, visits: 168, target: 91, conversion: 73, avgOrder: 496_300, returned: 6_420_000, newCustomers: 31 },
}

const weeklySales = [
  { label: 'ش', value: 7.2 },
  { label: 'ی', value: 9.8 },
  { label: 'د', value: 8.4 },
  { label: 'س', value: 11.1 },
  { label: 'چ', value: 10.2 },
  { label: 'پ', value: 12.45 },
]

const topCustomers = [
  { name: 'سوپر مارکت رضایی', area: 'گوهردشت', amount: 4_850_000, orders: 5 },
  { name: 'داروخانه نادری', area: 'رجایی‌شهر', amount: 3_740_000, orders: 4 },
  { name: 'فروشگاه سعیدی', area: 'عظیمیه', amount: 2_980_000, orders: 3 },
]

function money(value: number) {
  return new Intl.NumberFormat('fa-IR').format(value)
}

function compactMoney(value: number) {
  const millions = value / 1_000_000
  return `${new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 }).format(millions)} م`
}

export function VisitorReportsScreen({ onNavigate }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const [period, setPeriod] = useState<Period>('today')
  const [notice, setNotice] = useState<string | null>(null)
  const { routeSummary } = useVisitorWorkflow()
  const snapshot = period === 'today' ? { ...snapshots.today, visits: routeSummary.visited } : snapshots[period]

  const maxSale = useMemo(() => Math.max(...weeklySales.map((item) => item.value)), [])

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vrep-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy"><strong>ویزیتور</strong><small><PinIcon /> منطقه کرج</small></span>
            <ChevronLeftIcon />
          </button>
          <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}><BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}</button>
          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vrep-heading">
          <div>
            <h1>گزارش عملکرد</h1>
            <p>فروش، بازدید و کیفیت عملکرد شخصی</p>
          </div>
          <button type="button" onClick={() => flash('خروجی گزارش در مرحله اتصال سرویس فعال می‌شود')}><ChartIcon /> خروجی</button>
        </section>

        <section className="vrep-period" role="tablist" aria-label="بازه گزارش">
          <button type="button" role="tab" aria-selected={period === 'today'} className={period === 'today' ? 'active' : ''} onClick={() => setPeriod('today')}>امروز</button>
          <button type="button" role="tab" aria-selected={period === 'week'} className={period === 'week' ? 'active' : ''} onClick={() => setPeriod('week')}>این هفته</button>
          <button type="button" role="tab" aria-selected={period === 'month'} className={period === 'month' ? 'active' : ''} onClick={() => setPeriod('month')}>این ماه</button>
        </section>

        <section className="vrep-primary-kpis" aria-label="شاخص‌های اصلی عملکرد">
          <article className="vrep-kpi featured">
            <span className="vrep-kpi-icon"><ChartIcon /></span>
            <span>فروش</span>
            <strong>{money(snapshot.sales)}</strong>
            <small>تومان</small>
          </article>
          <article className="vrep-kpi">
            <span className="vrep-kpi-icon"><CartIcon /></span>
            <span>سفارش</span>
            <strong>{snapshot.orders}</strong>
            <small>ثبت شده</small>
          </article>
          <article className="vrep-kpi">
            <span className="vrep-kpi-icon"><CheckCircleIcon /></span>
            <span>بازدید</span>
            <strong>{snapshot.visits}</strong>
            <small>مشتری</small>
          </article>
          <article className="vrep-kpi">
            <span className="vrep-kpi-icon"><StoreIcon /></span>
            <span>مشتری جدید</span>
            <strong>{snapshot.newCustomers}</strong>
            <small>افزوده شده</small>
          </article>
        </section>

        <section className="vrep-score-card">
          <div className="vrep-score-ring" style={{ '--score': `${snapshot.target * 3.6}deg` } as CSSProperties}>
            <div><strong>{snapshot.target}٪</strong><span>هدف</span></div>
          </div>
          <div className="vrep-score-copy">
            <strong>تحقق هدف فروش</strong>
            <p>{snapshot.target >= 90 ? 'به هدف ماهانه خیلی نزدیک هستی.' : snapshot.target >= 80 ? 'روند عملکرد بالاتر از میانگین برنامه است.' : 'برای رسیدن به هدف، تمرکز روی مشتریان پتانسیل‌دار را بیشتر کن.'}</p>
            <div className="vrep-score-meta">
              <span><b>{snapshot.conversion}٪</b> تبدیل بازدید به سفارش</span>
              <span><b>{compactMoney(snapshot.avgOrder)}</b> میانگین سفارش</span>
            </div>
          </div>
        </section>

        <section className="vrep-chart-card">
          <div className="vrep-section-head">
            <div><ChartIcon /><strong>روند فروش</strong></div>
            <span>۶ روز اخیر</span>
          </div>
          <div className="vrep-bars" aria-label="نمودار فروش روزانه">
            {weeklySales.map((item, index) => (
              <div className="vrep-bar-col" key={`${item.label}-${index}`}>
                <span className="vrep-bar-value">{new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(item.value)} م</span>
                <div className="vrep-bar-track"><span style={{ height: `${Math.max(18, (item.value / maxSale) * 100)}%` }} /></div>
                <b>{item.label}</b>
              </div>
            ))}
          </div>
        </section>

        <section className="vrep-secondary-grid">
          <article><span>میانگین سفارش</span><strong>{money(snapshot.avgOrder)}</strong><small>تومان</small></article>
          <article><span>نرخ تبدیل</span><strong>{snapshot.conversion}٪</strong><small>بازدید به سفارش</small></article>
          <article className="warning"><span>مرجوعی</span><strong>{money(snapshot.returned)}</strong><small>تومان</small></article>
          <article><span>پیشرفت هدف</span><strong>{snapshot.target}٪</strong><small>برنامه فروش</small></article>
        </section>

        <section className="vrep-top-card">
          <div className="vrep-section-head">
            <div><StoreIcon /><strong>مشتریان برتر</strong></div>
            <button type="button" onClick={() => onNavigate('/visitor/customers')}>همه مشتریان</button>
          </div>
          <div className="vrep-top-list">
            {topCustomers.map((customer, index) => (
              <button type="button" key={customer.name} onClick={() => onNavigate(`/visitor/customers/${index + 1}`)}>
                <span className="vrep-rank">{index + 1}</span>
                <span className="vrep-top-copy"><strong>{customer.name}</strong><small>{customer.area} · {customer.orders} سفارش</small></span>
                <span className="vrep-top-amount"><strong>{money(customer.amount)}</strong><small>تومان</small></span>
                <ChevronLeftIcon />
              </button>
            ))}
          </div>
        </section>

        <section className="vrep-ai-card">
          <ChartIcon />
          <div><strong>جمع‌بندی عملکرد</strong><p>نرخ تبدیل بازدید مناسب است. بیشترین فرصت رشد در افزایش میانگین مبلغ سفارش مشتریان فعال دیده می‌شود.</p></div>
          <button type="button" onClick={() => onNavigate('/visitor/ai?context=report&prompt=performance')}>تحلیل بیشتر</button>
        </section>

        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item active" type="button" aria-current="page" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
