import { useEffect, useMemo, useState } from 'react'
import { neginApi, type CustomerProfileResponse, type SellerCustomer } from '../api/neginApi'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import {
  BellIcon,
  CartIcon,
  ChartIcon,
  CheckCircleIcon,
  ChequeIcon,
  ChevronLeftIcon,
  HomeIcon,
  InvoiceIcon,
  MapIcon,
  PhoneIcon,
  PinIcon,
  PlusIcon,
  RouteArrowIcon,
  StoreIcon,
  UserGroupIcon,
  WalletIcon,
} from './Icons'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'

type Props = {
  customerId?: string
  onNavigate: (path: string) => void
  onBack: () => void
}

type Tab = 'overview' | 'financial' | 'history'

function titleOf(customer: SellerCustomer) {
  return customer.store_name || customer.name || `مشتری ${customer.code}`
}

function money(value: number | undefined) {
  return `${Number(value || 0).toLocaleString('fa-IR')} ریال`
}

function callCustomer(customer: SellerCustomer) {
  const phone = (customer.mobile || customer.phone || '').replace(/[^\d+]/g, '')
  if (phone) window.location.href = `tel:${phone}`
}

function navigateCustomer(customer: SellerCustomer) {
  if (customer.latitude === null || customer.longitude === null) return
  const label = encodeURIComponent(titleOf(customer))
  window.location.href = `geo:${customer.latitude},${customer.longitude}?q=${customer.latitude},${customer.longitude}(${label})`
}

export function VisitorCustomer360Screen({ customerId = '', onNavigate, onBack }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const { profile: userProfile } = useVisitorAuth()
  const { activeRouteId, customerById } = useVisitorLiveData()
  const [tab, setTab] = useState<Tab>('overview')
  const [profile, setProfile] = useState<CustomerProfileResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    if (!activeRouteId || !customerId) {
      setProfile(null)
      setError('مسیر فعال یا شناسه مشتری در دسترس نیست.')
      return
    }

    setLoading(true)
    setError(null)
    void neginApi.customerProfile(activeRouteId, customerId)
      .then((data) => {
        if (!cancelled) setProfile(data)
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'پروفایل مشتری دریافت نشد.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [activeRouteId, customerId])

  const customer = profile?.customer ?? customerById(customerId)
  const finance = customer?.financial_snapshot ?? {}
  const locationLabel = useMemo(() => {
    if (!customer) return '—'
    if (customer.latitude === null || customer.longitude === null) return 'موقعیت ثبت نشده'
    return `${customer.latitude.toFixed(5)} , ${customer.longitude.toFixed(5)}`
  }, [customer])

  const hasPhone = Boolean(customer?.mobile || customer?.phone)
  const hasLocation = customer?.latitude !== null && customer?.longitude !== null
  const activeFields = profile?.editable_contract?.active_fields ?? []

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell c360-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy">
              <strong>{userProfile?.full_name || userProfile?.username || 'ویزیتور'}</strong>
              <small><PinIcon /> {userProfile?.branch || userProfile?.sales_line || 'حساب سازمانی'}</small>
            </span>
            <ChevronLeftIcon />
          </button>
          <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}
          </button>
          <div className="vh-brand" dir="ltr"><img src="/assets/neginai-logo-transparent.png" alt="Negin AI" /><div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div></div>
        </header>

        <section className="c360-topbar">
          <button type="button" className="c360-back" onClick={onBack} aria-label="بازگشت"><ChevronLeftIcon /></button>
          <div><span>پروفایل مشتری · داده زنده</span><h1>Customer 360</h1></div>
        </section>

        {error ? <section className="vh-live-state error" role="alert"><div><strong>پروفایل مشتری دریافت نشد</strong><span>{error}</span></div></section> : null}
        {loading ? <section className="vh-live-state" role="status"><strong>در حال دریافت Customer 360…</strong><span>اطلاعات از NGT و منابع مالی مجاز خوانده می‌شود.</span></section> : null}

        {customer ? (
          <>
            <section className="c360-identity">
              <div className="c360-store-icon"><StoreIcon /></div>
              <div className="c360-identity-copy">
                <div className="c360-title-row"><h2>{titleOf(customer)}</h2><span className="c360-live">زنده</span></div>
                <p>{customer.name || '—'} · کد {customer.code || '—'}</p>
                <span><PinIcon /> {customer.address || 'نشانی ثبت نشده'} · {profile?.route.title || 'مسیر روز'}</span>
              </div>
            </section>

            <section className="c360-actions" aria-label="اقدامات سریع مشتری">
              <button type="button" disabled={!hasPhone} onClick={() => callCustomer(customer)}><PhoneIcon /><span>تماس</span></button>
              <button type="button" disabled={!hasLocation} onClick={() => navigateCustomer(customer)}><MapIcon /><span>مسیریابی</span></button>
              <button type="button" className="primary" onClick={() => onNavigate(`/visitor/route?customer=${customer.id}&intent=visit`)}><RouteArrowIcon /><span>رفتن به بازدید</span></button>
              <button type="button" className="gold" onClick={() => onNavigate(`/visitor/orders?customer=${customer.id}`)}><CartIcon /><span>سفارش</span></button>
            </section>

            <section className="c360-kpis" aria-label="خلاصه مشتری">
              <article><span>بازدیدها</span><strong>{Number(profile?.customer.visit_count ?? 0).toLocaleString('fa-IR')}</strong><small>NGT</small></article>
              <article><span>سفارش‌ها</span><strong>{Number(profile?.customer.order_count ?? 0).toLocaleString('fa-IR')}</strong><small>NGT</small></article>
              <article><span>مانده کاردکس</span><strong>{money(customer.cardex_balance)}</strong><small>داده مالی مجاز</small></article>
            </section>

            <div className="c360-tabs" role="tablist" aria-label="بخش‌های پروفایل مشتری">
              <button type="button" role="tab" aria-selected={tab === 'overview'} className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>نمای کلی</button>
              <button type="button" role="tab" aria-selected={tab === 'financial'} className={tab === 'financial' ? 'active' : ''} onClick={() => setTab('financial')}>مالی</button>
              <button type="button" role="tab" aria-selected={tab === 'history'} className={tab === 'history' ? 'active' : ''} onClick={() => setTab('history')}>سوابق</button>
            </div>

            {tab === 'overview' ? (
              <section className="c360-stack">
                <article className="c360-panel">
                  <div className="c360-panel-head"><strong>اطلاعات مشتری</strong><span>{activeFields.length ? `${activeFields.length.toLocaleString('fa-IR')} فیلد قابل ویرایش` : 'فقط خواندنی'}</span></div>
                  <dl className="c360-info-grid">
                    <div><dt>تلفن</dt><dd>{customer.phone || '—'}</dd></div>
                    <div><dt>موبایل</dt><dd>{customer.mobile || '—'}</dd></div>
                    <div className="wide"><dt>آدرس</dt><dd>{customer.address || 'ثبت نشده'}</dd></div>
                    {profile?.customer.activity_name ? <div><dt>فعالیت</dt><dd>{profile.customer.activity_name}</dd></div> : null}
                    {profile?.customer.level_name ? <div><dt>سطح مشتری</dt><dd>{profile.customer.level_name}</dd></div> : null}
                  </dl>
                </article>

                <article className="c360-panel c360-location-card">
                  <div className="c360-panel-head"><strong>موقعیت مشتری</strong><span className={hasLocation ? 'good' : ''}>{hasLocation ? <><CheckCircleIcon /> ثبت‌شده</> : 'ثبت نشده'}</span></div>
                  <div className="c360-location-body"><div className="c360-pin"><PinIcon /></div><div><strong>{locationLabel}</strong><span>{customer.location_source || 'NGT / ERP'}</span></div></div>
                </article>

                {profile?.customer.alarm ? <article className="c360-panel"><div className="c360-panel-head"><strong>هشدار مشتری</strong></div><p>{profile.customer.alarm}</p></article> : null}

                <article className="c360-panel c360-ai-card">
                  <div className="c360-panel-head"><strong>Negin AI</strong><span className="ai-dot">✦</span></div>
                  <p>برای تحلیل این مشتری، گفتگو را با زمینه همین Customer 360 باز کن. پاسخ از سرویس واقعی NeginAI دریافت می‌شود.</p>
                  <button type="button" className="c360-ai-open" onClick={() => onNavigate(`/visitor/ai?context=customer&customer=${customer.id}`)}>گفتگو با Negin AI <ChevronLeftIcon /></button>
                </article>
              </section>
            ) : null}

            {tab === 'financial' ? (
              <section className="c360-stack">
                <div className="c360-finance-grid">
                  <article><WalletIcon /><span>مانده کاردکس</span><strong>{money(customer.cardex_balance)}</strong><small>Acc.vwCustomerBalance</small></article>
                  <article><InvoiceIcon /><span>فاکتور باز</span><strong>{customer.open_invoice_count.toLocaleString('fa-IR')}</strong><small>{money(customer.open_invoice_remaining)}</small></article>
                  <article><ChartIcon /><span>اعتبار باقیمانده</span><strong>{money(finance.combined_remaining)}</strong><small>Bed + Asn</small></article>
                  <article className={Number(finance.returned_cheque_count ?? 0) ? '' : 'safe'}><ChequeIcon /><span>چک برگشتی</span><strong>{Number(finance.returned_cheque_count ?? 0).toLocaleString('fa-IR')}</strong><small>{money(finance.returned_cheque_amount)}</small></article>
                </div>
                <p className="c360-permission-note">این مقادیر از پاسخ مجاز Seller Workspace نمایش داده می‌شوند؛ Frontend مستقیماً به دیتابیس متصل نیست.</p>
              </section>
            ) : null}

            {tab === 'history' ? (
              <section className="c360-stack">
                <article className="c360-panel">
                  <div className="c360-panel-head"><strong>سوابق تجمیعی</strong><span>زنده</span></div>
                  <dl className="c360-info-grid">
                    <div><dt>تعداد بازدید</dt><dd>{Number(profile?.customer.visit_count ?? 0).toLocaleString('fa-IR')}</dd></div>
                    <div><dt>تعداد سفارش</dt><dd>{Number(profile?.customer.order_count ?? 0).toLocaleString('fa-IR')}</dd></div>
                    <div><dt>ردیف سفارش</dt><dd>{Number(profile?.customer.order_line_count ?? 0).toLocaleString('fa-IR')}</dd></div>
                    <div><dt>جمع سفارش</dt><dd>{money(profile?.customer.sum_order_amount)}</dd></div>
                  </dl>
                  <p className="c360-permission-note">Timeline ریز فعالیت‌ها در API فعلی Customer Profile ارائه نمی‌شود؛ بنابراین رویداد ساختگی نمایش داده نشده است.</p>
                </article>
              </section>
            ) : null}
          </>
        ) : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate(customer ? `/visitor/orders?customer=${customer.id}` : '/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item active" type="button" aria-current="page" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
