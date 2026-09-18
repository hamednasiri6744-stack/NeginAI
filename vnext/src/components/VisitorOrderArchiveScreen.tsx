import { useCallback, useEffect, useMemo, useState } from 'react'
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
  UserGroupIcon,
} from './Icons'
import { getRouteSavedRequests, type RouteSavedRequest } from '../api/neginApi'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'

type Props = { onNavigate: (path: string) => void }

function number(value: number) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(value)
}

function when(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return value || '—'
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function lineText(line: Record<string, unknown>, key: string) {
  const value = line[key]
  return value === null || value === undefined ? '' : String(value)
}

function lineNumber(line: Record<string, unknown>, key: string) {
  const value = Number(line[key] ?? 0)
  return Number.isFinite(value) ? value : 0
}

export function VisitorOrderArchiveScreen({ onNavigate }: Props) {
  const { profile } = useVisitorAuth()
  const { unreadCount } = useVisitorNotifications()
  const { activeRouteId, activeRouteTitle, customerById } = useVisitorLiveData()
  const [requests, setRequests] = useState<RouteSavedRequest[]>([])
  const [selected, setSelected] = useState<RouteSavedRequest | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!activeRouteId) {
      setRequests([])
      setError(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await getRouteSavedRequests(activeRouteId)
      setRequests(response.requests)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'درخواست‌های ذخیره‌شده بارگذاری نشدند.')
    } finally {
      setLoading(false)
    }
  }, [activeRouteId])

  useEffect(() => {
    void load()
  }, [load])

  const visibleRequests = useMemo(() => {
    const q = query.trim().toLocaleLowerCase('fa')
    if (!q) return requests
    return requests.filter((request) => {
      const customer = customerById(request.customer_id)
      const lineNames = request.lines.map((line) => lineText(line, 'title')).join(' ')
      const haystack = [
        request.request_number,
        request.customer_id,
        customer?.store_name,
        customer?.name,
        customer?.code,
        request.payment_type,
        request.order_type,
        request.warehouse_name,
        lineNames,
      ].join(' ').toLocaleLowerCase('fa')
      return haystack.includes(q)
    })
  }, [customerById, query, requests])

  const totalAmount = useMemo(
    () => requests.reduce((sum, request) => sum + Number(request.total_amount || 0), 0),
    [requests],
  )
  const totalLines = useMemo(
    () => requests.reduce((sum, request) => sum + Number(request.line_count || 0), 0),
    [requests],
  )

  return (
    <main className="vh-page ng-living-root vh-live-ui" dir="rtl" data-living-ui="on">
      <div className="vh-shell voa-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">{profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || 'کاربر'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || '—'}</small>
            </span>
            <ChevronLeftIcon />
          </button>
          <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}
          </button>
          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="voa-heading">
          <div>
            <span>آرشیو سفارش</span>
            <h1>درخواست‌های ذخیره‌شده واقعی</h1>
            <p>{activeRouteTitle ? `مسیر ${activeRouteTitle}` : 'مسیر فعالی ثبت نشده است'}</p>
          </div>
          <button type="button" className="voa-new-order ng-living-interactive" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش جدید</span></button>
        </section>

        {error ? (
          <section className="vh-live-state error" role="alert">
            <div><strong>درخواست‌ها بارگذاری نشدند</strong><span>{error}</span></div>
            <button type="button" onClick={() => void load()}>تلاش دوباره</button>
          </section>
        ) : loading ? (
          <section className="vh-live-state" role="status"><strong>در حال دریافت درخواست‌های ذخیره‌شده…</strong></section>
        ) : !activeRouteId ? (
          <section className="voa-no-route ng-layer-surface">
            <span className="voa-no-route-icon"><ClipboardIcon /></span>
            <div><strong>برای امروز Route فعالی وجود ندارد</strong><small>آرشیو ذخیره‌شده به Route واقعی روز وابسته است؛ مرور کاتالوگ و مشتریان همچنان در دسترس است.</small></div>
            <div><button type="button" onClick={() => onNavigate('/visitor/orders')}>مرور کاتالوگ</button><button type="button" onClick={() => onNavigate('/visitor/customers')}>مشتریان</button></div>
          </section>
        ) : null}

        {activeRouteId || requests.length ? (
          <section className="voa-summary ng-living-surface" aria-label="خلاصه درخواست‌ها">
            <article><span>درخواست</span><strong>{requests.length.toLocaleString('fa-IR')}</strong><small>ثبت‌شده</small></article>
            <article><span>ردیف کالا</span><strong>{totalLines.toLocaleString('fa-IR')}</strong><small>امروز</small></article>
            <article><span>مبلغ</span><strong>{number(totalAmount)}</strong><small>جمع ثبت‌شده</small></article>
          </section>
        ) : null}

        <section className="voa-history">
          <label className="voa-search">
            <SearchIcon />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="جست‌وجوی مشتری، کالا، نوع سفارش یا پرداخت"
            />
          </label>

          <div className="voa-list-head">
            <strong>{visibleRequests.length.toLocaleString('fa-IR')} درخواست</strong>
            <button type="button" className="voa-refresh ng-living-interactive" onClick={() => void load()} disabled={loading}><span className={loading ? 'spin' : ''}>↻</span>{loading ? 'در حال دریافت' : 'به‌روزرسانی'}</button>
          </div>

          <div className="voa-order-list">
            {visibleRequests.length ? visibleRequests.map((request) => {
              const customer = customerById(request.customer_id)
              const customerName = customer?.store_name || customer?.name || customer?.code || `مشتری ${request.customer_id}`
              return (
                <button type="button" className="voa-order-card" key={request.id} onClick={() => setSelected(request)}>
                  <span className="voa-order-icon"><ClipboardIcon /></span>
                  <span className="voa-order-main">
                    <span className="voa-order-title"><strong>{customerName}</strong><em>درخواست {request.request_number.toLocaleString('fa-IR')}</em></span>
                    <small dir="ltr">{request.id}</small>
                    <span className="voa-order-meta">
                      {when(request.updated_at)} · {request.line_count.toLocaleString('fa-IR')} ردیف
                      {request.order_type ? ` · ${request.order_type}` : ''}
                      {request.payment_type ? ` · ${request.payment_type}` : ''}
                    </span>
                  </span>
                  <span className="voa-order-value">
                    <strong>{number(request.total_amount)}</strong>
                    <small>{request.warehouse_name || 'انبار ثبت نشده'}</small>
                  </span>
                  <ChevronLeftIcon />
                </button>
              )
            }) : (
              <div className="voa-empty">
                <ClipboardIcon />
                <strong>درخواست ذخیره‌شده‌ای برای این مسیر امروز وجود ندارد.</strong>
                <span>این بخش دیگر داده نمونه یا آرشیو ساختگی نمایش نمی‌دهد.</span>
              </div>
            )}
          </div>
        </section>

        {selected ? (
          <div className="vo-sheet-backdrop" onClick={() => setSelected(null)}>
            <section className="voa-invoice" role="dialog" aria-modal="true" aria-label="جزئیات درخواست ذخیره‌شده" onClick={(event) => event.stopPropagation()}>
              <div className="vo-sheet-handle" />
              <div className="voa-invoice-head">
                <div>
                  <small>درخواست ذخیره‌شده</small>
                  <h2>درخواست {selected.request_number.toLocaleString('fa-IR')}</h2>
                  <span dir="ltr">{selected.id}</span>
                </div>
                <span className="voa-invoice-mark"><InvoiceIcon /></span>
              </div>

              <div className="voa-invoice-customer">
                <StoreIcon />
                <div>
                  <strong>{customerById(selected.customer_id)?.store_name || customerById(selected.customer_id)?.name || `مشتری ${selected.customer_id}`}</strong>
                  <span>{when(selected.updated_at)} · {selected.order_type || 'نوع سفارش ثبت نشده'} · {selected.payment_type || 'نوع پرداخت ثبت نشده'}</span>
                </div>
              </div>

              <div className="voa-invoice-lines">
                {selected.lines.map((line, index) => {
                  const title = lineText(line, 'title') || lineText(line, 'product_name') || lineText(line, 'product_id') || `ردیف ${index + 1}`
                  const quantity = lineNumber(line, 'quantity')
                  const unitPrice = lineNumber(line, 'unit_price')
                  const discountAmount = lineNumber(line, 'discount_amount')
                  return (
                    <div key={`${title}-${index}`}>
                      <span>
                        <strong>{title}</strong>
                        <small>{number(quantity)} × {number(unitPrice)}{discountAmount ? ` · تخفیف ${number(discountAmount)}` : ''}</small>
                      </span>
                      <b>{number(Math.max(0, quantity * unitPrice - discountAmount))}</b>
                    </div>
                  )
                })}
              </div>

              <div className="voa-invoice-total">
                <div><span>تعداد ردیف</span><strong>{selected.line_count.toLocaleString('fa-IR')}</strong></div>
                <div><span>انبار</span><strong>{selected.warehouse_name || 'ثبت نشده'}</strong></div>
                <div className="total"><span>مبلغ ثبت‌شده</span><strong>{number(selected.total_amount)}</strong></div>
              </div>

              <div className="voa-invoice-actions">
                <button type="button" onClick={() => setSelected(null)}>بستن</button>
                <button
                  type="button"
                  className="primary"
                  onClick={() => {
                    const customerId = selected.customer_id
                    setSelected(null)
                    onNavigate(`/visitor/customers/${customerId}`)
                  }}
                >
                  پروفایل مشتری
                </button>
              </div>
            </section>
          </div>
        ) : null}

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
