import { useMemo, useState } from 'react'
import { readPrototypeDrafts, removePrototypeDraft, type PrototypeOrderDraft } from '../state/visitorDraftStore'
import {
  BellIcon,
  ChartIcon,
  ChevronLeftIcon,
  ClipboardIcon,
  HomeIcon,
  InvoiceIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  SearchIcon,
  StoreIcon,
  TrashIcon,
  UserGroupIcon,
} from './Icons'

import { useVisitorNotifications } from '../state/VisitorNotificationsContext'

type Props = {
  onNavigate: (path: string) => void
}

type Draft = {
  id: string
  customerId: string
  customer: string
  area: string
  items: number
  units: number
  amount: number
  updated: string
}

type OrderStatus = 'ثبت شده' | 'در انتظار تایید' | 'فاکتور شده'

type Order = {
  id: string
  customerId: string
  customer: string
  date: string
  time: string
  items: number
  payment: string
  status: OrderStatus
  amount: number
  invoice?: string
}

type InvoiceLine = { name: string; qty: number; unitPrice: number; discount: number }

function draftToView(draft: PrototypeOrderDraft): Draft {
  const quantities = Object.values(draft.cart)
  const minutes = Math.max(0, Math.round((Date.now() - draft.updatedAt) / 60000))
  const updated = minutes < 1 ? 'همین الان' : minutes < 60 ? `${minutes} دقیقه پیش` : minutes < 1440 ? `${Math.round(minutes / 60)} ساعت پیش` : `${Math.round(minutes / 1440)} روز پیش`
  return {
    id: draft.id,
    customerId: draft.customerId,
    customer: draft.customer,
    area: draft.area,
    items: quantities.length,
    units: quantities.reduce((sum, value) => sum + value, 0),
    amount: draft.amount,
    updated,
  }
}


const orders: Order[] = [
  { id: 'ORD-260912-184', customerId: '1', customer: 'سوپر مارکت رضایی', date: '۱۴۰۵/۰۶/۲۱', time: '۱۴:۲۸', items: 3, payment: 'اعتباری', status: 'ثبت شده', amount: 3_381_400 },
  { id: 'ORD-260912-176', customerId: '2', customer: 'داروخانه نادری', date: '۱۴۰۵/۰۶/۲۱', time: '۱۲:۵۴', items: 5, payment: 'نقدی', status: 'فاکتور شده', amount: 5_942_000, invoice: 'INV-802894' },
  { id: 'ORD-260911-149', customerId: '3', customer: 'فروشگاه سعیدی', date: '۱۴۰۵/۰۶/۲۰', time: '۱۶:۲۱', items: 4, payment: 'چک', status: 'در انتظار تایید', amount: 4_776_500 },
  { id: 'ORD-260911-138', customerId: '1', customer: 'سوپر مارکت رضایی', date: '۱۴۰۵/۰۶/۲۰', time: '۱۳:۰۶', items: 2, payment: 'اعتباری', status: 'فاکتور شده', amount: 2_654_300, invoice: 'INV-802845' },
]

const invoiceLines: InvoiceLine[] = [
  { name: 'مایع ظرفشویی ۷۵۰ گرمی', qty: 2, unitPrice: 685_000, discount: 5 },
  { name: 'دستمال کاغذی ۲۰۰ برگ', qty: 2, unitPrice: 910_000, discount: 3 },
  { name: 'کیسه زباله رولی بزرگ', qty: 1, unitPrice: 830_000, discount: 6 },
]

function money(value: number) {
  return new Intl.NumberFormat('fa-IR').format(value)
}

export function VisitorOrderArchiveScreen({ onNavigate }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const [view, setView] = useState<'history' | 'drafts'>('history')
  const [drafts, setDrafts] = useState<Draft[]>(() => readPrototypeDrafts().map(draftToView))
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<'همه' | OrderStatus>('همه')
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const visibleOrders = useMemo(() => orders.filter((order) => {
    const q = query.trim()
    const matchesQuery = !q || `${order.id} ${order.customer} ${order.invoice ?? ''}`.includes(q)
    const matchesStatus = status === 'همه' || order.status === status
    return matchesQuery && matchesStatus
  }), [query, status])

  const todayAmount = orders.filter((order) => order.date === '۱۴۰۵/۰۶/۲۱').reduce((sum, order) => sum + order.amount, 0)

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }

  function removeDraft(id: string) {
    const next = removePrototypeDraft(id).map(draftToView)
    setDrafts(next)
    flash('پیش‌نویس حذف شد')
  }

  const invoiceGross = invoiceLines.reduce((sum, line) => sum + line.qty * line.unitPrice, 0)
  const invoiceDiscount = invoiceLines.reduce((sum, line) => sum + line.qty * line.unitPrice * line.discount / 100, 0)
  const invoiceTax = Math.round((invoiceGross - invoiceDiscount) * 0.10)
  const invoiceTotal = Math.round(invoiceGross - invoiceDiscount + invoiceTax)

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell voa-shell">
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

        <section className="voa-heading">
          <div><span>Order Center</span><h1>سفارش‌ها و پیش‌نویس‌ها</h1><p>پیگیری، ادامه سفارش و پیش‌نمایش فاکتور</p></div>
          <button type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش جدید</span></button>
        </section>

        <section className="voa-summary">
          <article><span>سفارش امروز</span><strong>۲</strong><small>{money(todayAmount)} تومان</small></article>
          <article><span>پیش‌نویس باز</span><strong>{drafts.length}</strong><small>قابل ادامه</small></article>
          <article><span>فاکتور شده</span><strong>۲</strong><small>از ۴ سفارش اخیر</small></article>
        </section>

        <section className="voa-tabs" role="tablist" aria-label="سفارش‌ها و پیش‌نویس‌ها">
          <button type="button" className={view === 'history' ? 'active' : ''} onClick={() => setView('history')}>سوابق سفارش</button>
          <button type="button" className={view === 'drafts' ? 'active' : ''} onClick={() => setView('drafts')}>پیش‌نویس‌ها <b>{drafts.length}</b></button>
        </section>

        {view === 'history' ? (
          <section className="voa-history">
            <label className="voa-search"><SearchIcon /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جستجوی مشتری، سفارش یا فاکتور" /></label>
            <div className="voa-chips">
              {(['همه', 'ثبت شده', 'در انتظار تایید', 'فاکتور شده'] as const).map((item) => <button type="button" key={item} className={status === item ? 'active' : ''} onClick={() => setStatus(item)}>{item}</button>)}
            </div>
            <div className="voa-list-head"><strong>{visibleOrders.length} سفارش</strong><span>جدیدترین ابتدا</span></div>
            <div className="voa-order-list">
              {visibleOrders.map((order) => (
                <button type="button" className="voa-order-card" key={order.id} onClick={() => setSelectedOrder(order)}>
                  <span className="voa-order-icon"><InvoiceIcon /></span>
                  <span className="voa-order-main">
                    <span className="voa-order-title"><strong>{order.customer}</strong><em className={`s-${order.status.replaceAll(' ', '-')}`}>{order.status}</em></span>
                    <small dir="ltr">{order.id}</small>
                    <span className="voa-order-meta">{order.date} · {order.time} · {order.items} قلم · {order.payment}</span>
                  </span>
                  <span className="voa-order-value"><strong>{money(order.amount)}</strong><small>تومان</small>{order.invoice ? <b dir="ltr">{order.invoice}</b> : null}</span>
                  <ChevronLeftIcon />
                </button>
              ))}
            </div>
          </section>
        ) : (
          <section className="voa-drafts">
            <div className="voa-draft-note"><ClipboardIcon /><div><strong>پیش‌نویس‌های این ورود روی دستگاه نگه داشته می‌شوند</strong><span>پس از خروج پاک می‌شوند؛ همگام‌سازی سرور هنوز متصل نیست.</span></div></div>
            {drafts.length ? <div className="voa-draft-list">
              {drafts.map((draft) => (
                <article className="voa-draft-card" key={draft.id}>
                  <span className="voa-draft-icon"><StoreIcon /></span>
                  <div className="voa-draft-copy"><strong>{draft.customer}</strong><span>{draft.area} · {draft.items} قلم · {draft.units} واحد</span><small>آخرین ویرایش: {draft.updated}</small></div>
                  <div className="voa-draft-amount"><strong>{money(draft.amount)}</strong><small>تومان</small></div>
                  <div className="voa-draft-actions">
                    <button type="button" className="resume" onClick={() => onNavigate(`/visitor/orders?customer=${draft.customerId}&draft=${draft.id}`)}>ادامه سفارش</button>
                    <button type="button" className="delete" aria-label={`حذف ${draft.id}`} onClick={() => removeDraft(draft.id)}><TrashIcon /></button>
                  </div>
                </article>
              ))}
            </div> : <div className="voa-empty"><ClipboardIcon /><strong>پیش‌نویسی باقی نمانده</strong><span>سفارش نیمه‌تمام جدید اینجا نمایش داده می‌شود.</span></div>}
          </section>
        )}

        {selectedOrder ? (
          <div className="vo-sheet-backdrop" onClick={() => setSelectedOrder(null)}>
            <section className="voa-invoice" role="dialog" aria-modal="true" aria-label="پیش نمایش فاکتور" onClick={(event) => event.stopPropagation()}>
              <div className="vo-sheet-handle" />
              <div className="voa-invoice-head">
                <div><small>Invoice Preview</small><h2>{selectedOrder.invoice ? 'پیش‌نمایش فاکتور' : 'جزئیات سفارش'}</h2><span dir="ltr">{selectedOrder.invoice ?? selectedOrder.id}</span></div>
                <span className="voa-invoice-mark"><InvoiceIcon /></span>
              </div>
              <div className="voa-invoice-customer"><StoreIcon /><div><strong>{selectedOrder.customer}</strong><span>{selectedOrder.date} · {selectedOrder.time} · {selectedOrder.payment}</span></div></div>
              <div className="voa-invoice-lines">
                {invoiceLines.slice(0, selectedOrder.items > 3 ? 3 : selectedOrder.items).map((line) => (
                  <div key={line.name}><span><strong>{line.name}</strong><small>{line.qty} × {money(line.unitPrice)}</small></span><b>{money(Math.round(line.qty * line.unitPrice * (1 - line.discount / 100)))}</b></div>
                ))}
              </div>
              <div className="voa-invoice-total">
                <div><span>جمع کالا</span><strong>{money(invoiceGross)}</strong></div>
                <div><span>تخفیف</span><strong className="mint">− {money(Math.round(invoiceDiscount))}</strong></div>
                <div><span>مالیات</span><strong>{money(invoiceTax)}</strong></div>
                <div className="total"><span>مبلغ نهایی</span><strong>{money(selectedOrder.invoice ? invoiceTotal : selectedOrder.amount)} <small>تومان</small></strong></div>
              </div>
              <div className="voa-invoice-actions">
                <button type="button" onClick={() => flash('PDF در مرحله اتصال سرویس اسناد فعال می‌شود')}>دانلود PDF</button>
                <button type="button" className="primary" onClick={() => { const customerId = selectedOrder.customerId; setSelectedOrder(null); onNavigate(`/visitor/orders?customer=${customerId}`) }}>تکرار سفارش</button>
              </div>
            </section>
          </div>
        ) : null}

        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order active" type="button" aria-current="page" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
