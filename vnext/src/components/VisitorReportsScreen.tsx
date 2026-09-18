import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  BellIcon,
  ChartIcon,
  ChequeIcon,
  ChevronLeftIcon,
  HomeIcon,
  InvoiceIcon,
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
import { AppHeader, BottomDock } from '../design-system/components'
import '../design-system/living/index.css'

type Props = { onNavigate: (path: string) => void }
type ReportFocus = 'receivables' | 'cheques' | 'distribution' | 'returns'

type ReportData = {
  openInvoices: SellerPortfolioOpenInvoicesResponse
  returnedCheques: SellerPortfolioReturnedChequesResponse
  distribution: SellerDistributionInProgressResponse
  voucherReturn: SellerVoucherReturnReportResponse
}

type FocusMeta = {
  title: string
  subtitle: string
  icon: ReactNode
  tone: 'gold' | 'danger' | 'mint' | 'blue'
}

function number(value: number) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(value)
}

function compactNumber(value: number) {
  return new Intl.NumberFormat('fa-IR', { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value || 0))
}

function dateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return value || '—'
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium' }).format(date)
}

export function VisitorReportsScreen({ onNavigate }: Props) {
  const { profile } = useVisitorAuth()
  const { attentionCount, highestSeverity } = useVisitorNotifications()
  const [data, setData] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [focus, setFocus] = useState<ReportFocus | null>(null)

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

  useEffect(() => {
    const onPopState = () => setFocus(null)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const openInvoiceCustomers = useMemo(
    () => [...(data?.openInvoices.customers ?? [])]
      .sort((a, b) => b.open_invoice_remaining - a.open_invoice_remaining),
    [data],
  )

  const recentCheques = useMemo(
    () => [...(data?.returnedCheques.cheques ?? [])]
      .sort((a, b) => String(b.status_date || b.date).localeCompare(String(a.status_date || a.date))),
    [data],
  )

  const recentDistribution = useMemo(
    () => [...(data?.distribution.invoices ?? [])],
    [data],
  )

  const focusMeta: Record<ReportFocus, FocusMeta> = {
    receivables: {
      title: 'مطالبات و فاکتور باز',
      subtitle: 'چه مقدار مانده باز دارم و روی کدام مشتری‌ها؟',
      icon: <InvoiceIcon />,
      tone: 'gold',
    },
    cheques: {
      title: 'چک برگشتی',
      subtitle: 'ریسک وصول من کجاست و مربوط به چه مشتری‌هایی است؟',
      icon: <ChequeIcon />,
      tone: 'danger',
    },
    distribution: {
      title: 'توزیع در جریان',
      subtitle: 'کدام فاکتورها هنوز در فرآیند توزیع هستند؟',
      icon: <StoreIcon />,
      tone: 'blue',
    },
    returns: {
      title: 'حواله و برگشت',
      subtitle: 'وضعیت حواله، فاکتور و برگشت ماه جاری چیست؟',
      icon: <ChartIcon />,
      tone: 'mint',
    },
  }

  function openFocus(next: ReportFocus) {
    window.history.pushState({ neginReportDepth: 1 }, '', window.location.href)
    setFocus(next)
  }

  function closeFocus() {
    window.history.back()
  }

  const totalRiskSignals = Number(data?.returnedCheques.cheque_count ?? 0) + Number(data?.voucherReturn.full_returned_count ?? 0)

  return (
    <main className="vh-page vh-live-ui ng-living-root vrep-depth-page" dir="rtl" data-live-ui="unified" data-living-ui="on">
      <div className="vh-shell vrep-shell">
        <AppHeader
          avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}
          title={profile?.full_name || profile?.username || 'کاربر'}
          subtitle={profile?.branch || profile?.sales_line || '—'}
          subtitleIcon={<PinIcon />}
          profileTrailing={<ChevronLeftIcon />}
          onProfileClick={() => onNavigate('/visitor/profile')}
          action={(
            <button
              className={`vh-bell ng-living-interactive ${highestSeverity ? `severity-${highestSeverity}` : ''}`}
              data-severity={highestSeverity ?? 'none'}
              type="button"
              aria-label="اعلان‌ها"
              onClick={() => onNavigate('/visitor/notifications')}
            >
              <BellIcon />
              {attentionCount ? <b className="ng-living-reactive">{attentionCount}</b> : null}
            </button>
          )}
        />

        <section className="vrep-depth-stage ng-depth-stage" data-depth={focus ? 1 : 0}>
          <span className="ng-depth-backplane" data-plane="1" aria-hidden="true" />

          {!focus ? (
            <div className="vrep-depth-root">
              <section className="vrep-command ng-layer-surface">
                <div>
                  <span className="vrep-command-live"><i /> گزارش‌های واقعی · ERP / NGT</span>
                  <h1>کدام بخش نیاز به تحلیل دارد؟</h1>
                  <p>{loading ? 'در حال دریافت داده واقعی…' : error ? 'بخشی از گزارش‌ها در دسترس نیست.' : totalRiskSignals ? `${totalRiskSignals.toLocaleString('fa-IR')} سیگنال ریسک مالی/برگشت ثبت شده است.` : 'وضعیت فعلی بدون سیگنال بحرانی ثبت شده است.'}</p>
                </div>
                <button type="button" className="vrep-refresh ng-living-interactive" onClick={() => void load()} disabled={loading}>
                  <ChartIcon /><span>{loading ? 'در حال دریافت' : 'به‌روزرسانی'}</span>
                </button>
              </section>

              {error ? (
                <button type="button" className="vrep-depth-error ng-living-interactive" onClick={() => void load()}>
                  <span><strong>بخشی از گزارش‌ها بارگذاری نشد</strong><small>{error}</small></span>
                  <ChevronLeftIcon />
                </button>
              ) : null}

              <div className="vrep-depth-portals" aria-label="حوزه‌های تحلیل">
                <button type="button" className="vrep-depth-portal ng-portal-surface ng-living-interactive" data-tone="gold" onClick={() => openFocus('receivables')}>
                  <span className="vrep-depth-portal-icon ng-portal-accent"><InvoiceIcon /></span>
                  <span><small>مطالبات</small><strong>{loading ? '…' : compactNumber(data?.openInvoices.open_invoice_remaining ?? 0)}</strong><em>{number(data?.openInvoices.customer_count ?? 0)} مشتری دارای مانده</em></span>
                  <ChevronLeftIcon />
                </button>

                <button type="button" className="vrep-depth-portal ng-portal-surface ng-living-interactive" data-tone={Number(data?.returnedCheques.cheque_count ?? 0) ? 'danger' : 'mint'} onClick={() => openFocus('cheques')}>
                  <span className="vrep-depth-portal-icon ng-portal-accent"><ChequeIcon /></span>
                  <span><small>چک برگشتی</small><strong>{loading ? '…' : number(data?.returnedCheques.cheque_count ?? 0)}</strong><em>{Number(data?.returnedCheques.cheque_count ?? 0) ? 'نیازمند بررسی وصول' : 'مورد فعالی نیست'}</em></span>
                  <ChevronLeftIcon />
                </button>

                <button type="button" className="vrep-depth-portal ng-portal-surface ng-living-interactive" data-tone="blue" onClick={() => openFocus('distribution')}>
                  <span className="vrep-depth-portal-icon ng-portal-accent"><StoreIcon /></span>
                  <span><small>توزیع در جریان</small><strong>{loading ? '…' : number(data?.distribution.invoice_count ?? 0)}</strong><em>فاکتور در فرآیند توزیع</em></span>
                  <ChevronLeftIcon />
                </button>

                <button type="button" className="vrep-depth-portal ng-portal-surface ng-living-interactive" data-tone={Number(data?.voucherReturn.full_returned_count ?? 0) ? 'danger' : 'mint'} onClick={() => openFocus('returns')}>
                  <span className="vrep-depth-portal-icon ng-portal-accent"><ChartIcon /></span>
                  <span><small>حواله و برگشت</small><strong>{loading ? '…' : number(data?.voucherReturn.full_returned_count ?? 0)}</strong><em>برگشت کامل در ماه جاری</em></span>
                  <ChevronLeftIcon />
                </button>
              </div>
            </div>
          ) : (
            <div className="vrep-depth-layer ng-layer-surface">
              <header className="vrep-depth-head">
                <button type="button" className="vrep-depth-back ng-living-interactive" onClick={closeFocus} aria-label="بازگشت"><ChevronLeftIcon /></button>
                <span className="vrep-depth-head-icon ng-portal-accent" data-tone={focusMeta[focus].tone}>{focusMeta[focus].icon}</span>
                <span>
                  <small>گزارش‌ها · تحلیل واقعی</small>
                  <strong>{focusMeta[focus].title}</strong>
                  <em>{focusMeta[focus].subtitle}</em>
                </span>
              </header>

              <section className="vrep-depth-scroll">
                {focus === 'receivables' ? (
                  <>
                    <div className="vrep-focus-hero ng-detail-surface">
                      <span><small>مانده فاکتور باز</small><strong>{number(data?.openInvoices.open_invoice_remaining ?? 0)}</strong></span>
                      <span><small>مشتری دارای مانده</small><strong>{number(data?.openInvoices.customer_count ?? 0)}</strong></span>
                    </div>
                    <div className="vrep-focus-list">
                      {openInvoiceCustomers.length ? openInvoiceCustomers.map((customer, index) => (
                        <button type="button" key={String(customer.id)} onClick={() => onNavigate(`/visitor/customers/${customer.id}`)}>
                          <span className="vrep-focus-rank">{index + 1}</span>
                          <span><strong>{customer.store_name || customer.name || customer.code}</strong><small>{customer.open_invoice_count.toLocaleString('fa-IR')} فاکتور باز · قدیمی‌ترین: {dateTime(customer.oldest_open_invoice_date)}</small></span>
                          <b>{number(customer.open_invoice_remaining)}</b>
                          <ChevronLeftIcon />
                        </button>
                      )) : <div className="vrep-focus-empty">مانده فاکتور بازی ثبت نشده است.</div>}
                    </div>
                  </>
                ) : null}

                {focus === 'cheques' ? (
                  <>
                    <div className="vrep-focus-hero ng-detail-surface">
                      <span><small>چک برگشتی</small><strong>{number(data?.returnedCheques.cheque_count ?? 0)}</strong></span>
                      <span><small>سهم فروشنده</small><strong>{number(data?.returnedCheques.seller_share ?? 0)}</strong></span>
                    </div>
                    <div className="vrep-focus-list">
                      {recentCheques.length ? recentCheques.map((cheque) => (
                        <button type="button" key={cheque.id} onClick={() => cheque.customer_id ? onNavigate(`/visitor/customers/${cheque.customer_id}`) : undefined}>
                          <span className="vrep-focus-rank danger">!</span>
                          <span><strong>{cheque.customer_store || cheque.customer_name || cheque.customer_code}</strong><small>{cheque.bank || 'بانک ثبت نشده'} · {cheque.status || 'وضعیت ثبت نشده'} · {dateTime(cheque.status_date || cheque.date)}</small></span>
                          <b>{number(cheque.seller_share || cheque.amount)}</b>
                          <ChevronLeftIcon />
                        </button>
                      )) : <div className="vrep-focus-empty">چک برگشتی ثبت نشده است.</div>}
                    </div>
                  </>
                ) : null}

                {focus === 'distribution' ? (
                  <>
                    <div className="vrep-focus-hero ng-detail-surface">
                      <span><small>فاکتور در توزیع</small><strong>{number(data?.distribution.invoice_count ?? 0)}</strong></span>
                      <span><small>تاریخ‌های توزیع</small><strong>{data?.distribution.distribution_dates?.length ?? 0}</strong></span>
                    </div>
                    <div className="vrep-focus-list">
                      {recentDistribution.length ? recentDistribution.map((invoice) => (
                        <button type="button" key={invoice.id} onClick={() => onNavigate('/visitor/customers')}>
                          <span className="vrep-focus-rank"><StoreIcon /></span>
                          <span><strong>{invoice.customer_store || invoice.customer_name || invoice.customer_code}</strong><small>توزیع {invoice.distribution_number || '—'} · {invoice.distribution_date || '—'} · راننده: {invoice.driver_name || '—'}</small></span>
                          <b>{number(invoice.amount)}</b>
                          <ChevronLeftIcon />
                        </button>
                      )) : <div className="vrep-focus-empty">توزیع در جریان ثبت نشده است.</div>}
                    </div>
                  </>
                ) : null}

                {focus === 'returns' ? (
                  <>
                    <div className="vrep-return-grid">
                      <article><small>حواله ماه</small><strong>{number(data?.voucherReturn.voucher_count ?? 0)}</strong><em>{data?.voucherReturn.report_month || '—'}</em></article>
                      <article><small>فاکتور شده</small><strong>{number(data?.voucherReturn.invoiced_count ?? 0)}</strong><em>از حواله‌های ماه</em></article>
                      <article className="danger"><small>برگشت کامل</small><strong>{number(data?.voucherReturn.full_returned_count ?? 0)}</strong><em>{number(data?.voucherReturn.return_percentage ?? 0)}٪ از حواله‌ها</em></article>
                      <article><small>توزیع‌نشده</small><strong>{number(data?.voucherReturn.undistributed_count ?? 0)}</strong><em>وضعیت ERP</em></article>
                    </div>
                  </>
                ) : null}
              </section>
            </div>
          )}
        </section>

        <BottomDock
          ariaLabel="ناوبری ویزیتور"
          items={[
            { key: 'home', label: 'خانه', icon: <HomeIcon />, onClick: () => onNavigate('/visitor/home') },
            { key: 'route', label: 'مسیر', icon: <MapIcon />, onClick: () => onNavigate('/visitor/route') },
            { key: 'customers', label: 'مشتریان', icon: <UserGroupIcon />, onClick: () => onNavigate('/visitor/customers') },
            { key: 'reports', label: 'گزارش‌ها', icon: <ChartIcon />, active: true, onClick: () => setFocus(null) },
          ]}
          primary={{ label: 'سفارش', icon: <PlusIcon />, onClick: () => onNavigate('/visitor/orders') }}
        />
      </div>
    </main>
  )
}
