import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BellIcon,
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
import {
  getSellerDistributionInProgress,
  getSellerPortfolioOpenInvoices,
  getSellerPortfolioReturnedCheques,
  getSellerVoucherReturnReport,
  type SellerDistributionInProgressResponse,
  type SellerPortfolioOpenInvoicesResponse,
  type SellerPortfolioReturnedChequesResponse,
  type SellerVoucherReturnReportResponse,
} from '../api/neginApi'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'

type Props = { onNavigate: (path: string) => void }

type ReportData = {
  openInvoices: SellerPortfolioOpenInvoicesResponse
  returnedCheques: SellerPortfolioReturnedChequesResponse
  distribution: SellerDistributionInProgressResponse
  voucherReturn: SellerVoucherReturnReportResponse
}

function number(value: number) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(value)
}

function dateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return value || '—'
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium' }).format(date)
}

export function VisitorReportsScreen({ onNavigate }: Props) {
  const { profile } = useVisitorAuth()
  const { unreadCount } = useVisitorNotifications()
  const { routeSummary } = useVisitorWorkflow()
  const [data, setData] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [openInvoices, returnedCheques, distribution, voucherReturn] = await Promise.all([
        getSellerPortfolioOpenInvoices(),
        getSellerPortfolioReturnedCheques(),
        getSellerDistributionInProgress(),
        getSellerVoucherReturnReport(),
      ])
      setData({ openInvoices, returnedCheques, distribution, voucherReturn })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'گزارش‌های واقعی در دسترس نیستند.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openInvoiceCustomers = useMemo(
    () => [...(data?.openInvoices.customers ?? [])]
      .sort((a, b) => b.open_invoice_remaining - a.open_invoice_remaining)
      .slice(0, 5),
    [data],
  )

  const recentCheques = useMemo(
    () => [...(data?.returnedCheques.cheques ?? [])]
      .sort((a, b) => String(b.status_date || b.date).localeCompare(String(a.status_date || a.date)))
      .slice(0, 5),
    [data],
  )

  const recentDistribution = useMemo(
    () => (data?.distribution.invoices ?? []).slice(0, 5),
    [data],
  )

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vrep-shell">
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
            <BellIcon />
            {unreadCount ? <b>{unreadCount}</b> : null}
          </button>
          <div className="vh-brand" dir="ltr">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
            <div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div>
          </div>
        </header>

        <section className="vrep-heading">
          <div>
            <h1>گزارش‌های واقعی فروشنده</h1>
            <p>فقط داده‌های ثبت‌شده در ERP، NGT و Seller Workspace نمایش داده می‌شوند.</p>
          </div>
          <button type="button" onClick={() => void load()} disabled={loading}>
            <ChartIcon /> {loading ? 'در حال دریافت' : 'به‌روزرسانی'}
          </button>
        </section>

        {error ? (
          <section className="vh-live-state error" role="alert">
            <div><strong>گزارش‌ها بارگذاری نشدند</strong><span>{error}</span></div>
            <button type="button" onClick={() => void load()}>تلاش دوباره</button>
          </section>
        ) : loading ? (
          <section className="vh-live-state" role="status">
            <strong>در حال دریافت گزارش‌های واقعی…</strong>
          </section>
        ) : null}

        <section className="vrep-primary-kpis" aria-label="شاخص‌های واقعی">
          <article className="vrep-kpi featured">
            <span className="vrep-kpi-icon"><ChartIcon /></span>
            <span>مانده فاکتورهای باز</span>
            <strong>{number(data?.openInvoices.open_invoice_remaining ?? 0)}</strong>
            <small>{number(data?.openInvoices.customer_count ?? 0)} مشتری دارای مانده</small>
          </article>
          <article className="vrep-kpi">
            <span className="vrep-kpi-icon"><CheckCircleIcon /></span>
            <span>چک‌های برگشتی</span>
            <strong>{number(data?.returnedCheques.cheque_count ?? 0)}</strong>
            <small>سهم فروشنده: {number(data?.returnedCheques.seller_share ?? 0)}</small>
          </article>
          <article className="vrep-kpi">
            <span className="vrep-kpi-icon"><StoreIcon /></span>
            <span>توزیع در جریان</span>
            <strong>{number(data?.distribution.invoice_count ?? 0)}</strong>
            <small>{data?.distribution.distribution_dates?.join('، ') || 'موردی ثبت نشده'}</small>
          </article>
          <article className="vrep-kpi">
            <span className="vrep-kpi-icon"><CheckCircleIcon /></span>
            <span>ویزیت‌های امروز</span>
            <strong>{number(routeSummary.visited)}</strong>
            <small>{number(routeSummary.total)} ایستگاه در مسیر فعلی</small>
          </article>
        </section>

        <section className="vrep-secondary-grid" aria-label="گزارش حواله و برگشت">
          <article>
            <span>حواله‌های ماه جاری</span>
            <strong>{number(data?.voucherReturn.voucher_count ?? 0)}</strong>
            <small>{data?.voucherReturn.report_month || '—'}</small>
          </article>
          <article>
            <span>فاکتور شده</span>
            <strong>{number(data?.voucherReturn.invoiced_count ?? 0)}</strong>
            <small>از حواله‌های ماه جاری</small>
          </article>
          <article className="warning">
            <span>برگشت کامل</span>
            <strong>{number(data?.voucherReturn.full_returned_count ?? 0)}</strong>
            <small>{number(data?.voucherReturn.return_percentage ?? 0)}٪ از حواله‌ها</small>
          </article>
          <article>
            <span>توزیع‌نشده</span>
            <strong>{number(data?.voucherReturn.undistributed_count ?? 0)}</strong>
            <small>وضعیت فعلی ERP</small>
          </article>
        </section>

        <section className="vrep-top-card">
          <div className="vrep-section-head">
            <div><StoreIcon /><strong>بیشترین مانده فاکتور باز</strong></div>
            <button type="button" onClick={() => onNavigate('/visitor/customers')}>مشتریان</button>
          </div>
          <div className="vrep-top-list">
            {openInvoiceCustomers.length ? openInvoiceCustomers.map((customer, index) => (
              <button
                type="button"
                key={String(customer.id)}
                onClick={() => onNavigate(`/visitor/customers/${customer.id}`)}
              >
                <span className="vrep-rank">{index + 1}</span>
                <span className="vrep-top-copy">
                  <strong>{customer.store_name || customer.name || customer.code}</strong>
                  <small>{customer.open_invoice_count.toLocaleString('fa-IR')} فاکتور باز · قدیمی‌ترین: {dateTime(customer.oldest_open_invoice_date)}</small>
                </span>
                <span className="vrep-top-amount">
                  <strong>{number(customer.open_invoice_remaining)}</strong>
                  <small>مانده ثبت‌شده</small>
                </span>
                <ChevronLeftIcon />
              </button>
            )) : <div className="vn-empty"><strong>مانده فاکتور بازی ثبت نشده است.</strong></div>}
          </div>
        </section>

        <section className="vrep-top-card">
          <div className="vrep-section-head">
            <div><ChartIcon /><strong>آخرین چک‌های برگشتی</strong></div>
            <span>{number(data?.returnedCheques.cheque_count ?? 0)} مورد</span>
          </div>
          <div className="vrep-top-list">
            {recentCheques.length ? recentCheques.map((cheque) => (
              <button
                type="button"
                key={cheque.id}
                onClick={() => cheque.customer_id ? onNavigate(`/visitor/customers/${cheque.customer_id}`) : undefined}
              >
                <span className="vrep-rank">•</span>
                <span className="vrep-top-copy">
                  <strong>{cheque.customer_store || cheque.customer_name || cheque.customer_code}</strong>
                  <small>{cheque.bank || 'بانک ثبت نشده'} · {cheque.status || 'وضعیت ثبت نشده'} · {dateTime(cheque.status_date || cheque.date)}</small>
                </span>
                <span className="vrep-top-amount">
                  <strong>{number(cheque.seller_share || cheque.amount)}</strong>
                  <small>سهم/مبلغ ثبت‌شده</small>
                </span>
                <ChevronLeftIcon />
              </button>
            )) : <div className="vn-empty"><strong>چک برگشتی ثبت نشده است.</strong></div>}
          </div>
        </section>

        <section className="vrep-top-card">
          <div className="vrep-section-head">
            <div><StoreIcon /><strong>توزیع در جریان</strong></div>
            <span>{number(data?.distribution.invoice_count ?? 0)} فاکتور</span>
          </div>
          <div className="vrep-top-list">
            {recentDistribution.length ? recentDistribution.map((invoice) => (
              <button type="button" key={invoice.id} onClick={() => onNavigate('/visitor/customers')}>
                <span className="vrep-rank">•</span>
                <span className="vrep-top-copy">
                  <strong>{invoice.customer_store || invoice.customer_name || invoice.customer_code}</strong>
                  <small>توزیع {invoice.distribution_number || '—'} · {invoice.distribution_date || '—'} · راننده: {invoice.driver_name || '—'}</small>
                </span>
                <span className="vrep-top-amount">
                  <strong>{number(invoice.amount)}</strong>
                  <small>مبلغ ERP</small>
                </span>
                <ChevronLeftIcon />
              </button>
            )) : <div className="vn-empty"><strong>توزیع در جریان ثبت نشده است.</strong></div>}
          </div>
        </section>

        <section className="vrep-ai-card">
          <ChartIcon />
          <div>
            <strong>تحلیل Negin AI</strong>
            <p>تحلیل هوشمند فقط با اتکا به داده‌های واقعی همین گزارش انجام می‌شود.</p>
          </div>
          <button type="button" onClick={() => onNavigate('/visitor/ai?context=report&prompt=performance')}>تحلیل گزارش</button>
        </section>

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
