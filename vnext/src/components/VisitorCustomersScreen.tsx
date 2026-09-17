import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import {
  BellIcon,
  CartIcon,
  ChartIcon,
  ChevronLeftIcon,
  ClockIcon,
  HomeIcon,
  MapIcon,
  PhoneIcon,
  PinIcon,
  PlusIcon,
  SearchIcon,
  StoreIcon,
  UserGroupIcon,
} from './Icons'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import { neginApi, type SellerCustomer } from '../api/neginApi'

type Props = { onNavigate: (path: string) => void }
type CustomerFilter = 'همه' | 'فعال' | 'پیگیری' | 'انجام شده'

function customerTitle(customer: SellerCustomer) {
  return customer.store_name || customer.name || `مشتری ${customer.code}`
}

function customerStatus(customer: SellerCustomer): Exclude<CustomerFilter, 'همه'> {
  if (customer.visit_resolution?.status === 'completed') return 'انجام شده'
  if (Number(customer.financial_snapshot?.returned_cheque_count ?? 0) > 0) return 'پیگیری'
  return 'فعال'
}

function statusClass(status: Exclude<CustomerFilter, 'همه'>) {
  if (status === 'فعال') return 'active'
  if (status === 'انجام شده') return 'new'
  return 'follow'
}

function visitDate(customer: SellerCustomer) {
  const raw = customer.visit_resolution?.ended_at
  if (!raw) return '—'
  const value = new Date(raw)
  if (Number.isNaN(value.valueOf())) return 'ثبت شده'
  return value.toLocaleDateString('fa-IR')
}

function money(value: number) {
  return `${Number(value || 0).toLocaleString('fa-IR')} ریال`
}

function callCustomer(customer: SellerCustomer) {
  const phone = (customer.mobile || customer.phone || '').replace(/[^\d+]/g, '')
  if (phone) window.location.href = `tel:${phone}`
}

function navigateCustomer(customer: SellerCustomer) {
  if (customer.latitude === null || customer.longitude === null) return
  const label = encodeURIComponent(customerTitle(customer))
  window.location.href = `geo:${customer.latitude},${customer.longitude}?q=${customer.latitude},${customer.longitude}(${label})`
}

export function VisitorCustomersScreen({ onNavigate }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const { profile } = useVisitorAuth()
  const { customers, customerCount, activeRouteId, activeRouteTitle, loading, error, reload } = useVisitorLiveData()
  const [fullCustomers, setFullCustomers] = useState<SellerCustomer[] | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    let cancelled = false
    if (!activeRouteId) {
      setFullCustomers(null)
      return () => { cancelled = true }
    }
    setFullCustomers(null)
    void neginApi.routeCustomers(activeRouteId, 'full')
      .then((data) => {
        if (!cancelled) setFullCustomers(data.customers)
      })
      .catch(() => {
        if (!cancelled) setFullCustomers(null)
      })
    return () => { cancelled = true }
  }, [activeRouteId])

  const displayCustomers = fullCustomers ?? customers
  const query = searchParams.get('q') ?? ''
  const rawFilter = searchParams.get('status')
  const filter: CustomerFilter = ['فعال', 'پیگیری', 'انجام شده'].includes(rawFilter ?? '')
    ? rawFilter as Exclude<CustomerFilter, 'همه'>
    : 'همه'

  function updateSearch(nextQuery: string) {
    const next = new URLSearchParams(searchParams)
    if (nextQuery.trim()) next.set('q', nextQuery)
    else next.delete('q')
    setSearchParams(next, { replace: true })
  }

  function updateFilter(nextFilter: CustomerFilter) {
    const next = new URLSearchParams(searchParams)
    if (nextFilter === 'همه') next.delete('status')
    else next.set('status', nextFilter)
    setSearchParams(next, { replace: true })
  }

  const visibleCustomers = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('fa-IR')
    return displayCustomers.filter((customer) => {
      const haystack = `${customerTitle(customer)} ${customer.name} ${customer.code} ${customer.address}`.toLocaleLowerCase('fa-IR')
      const matchesQuery = !normalized || haystack.includes(normalized)
      const matchesFilter = filter === 'همه' || customerStatus(customer) === filter
      return matchesQuery && matchesFilter
    })
  }, [displayCustomers, filter, query])

  const completed = displayCustomers.filter((customer) => customer.visit_resolution?.status === 'completed').length
  const followUp = displayCustomers.filter((customer) => Number(customer.financial_snapshot?.returned_cheque_count ?? 0) > 0).length

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vc-shell">
        <header className="vh-header">
          <button className="vh-profile" type="button" onClick={() => onNavigate('/visitor/profile')}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || 'ویزیتور'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || 'حساب سازمانی'}</small>
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

        <section className="vc-heading">
          <div><span>{activeRouteTitle || 'مسیر روز NGT'}</span><h1>مشتریان</h1></div>
          <button type="button" disabled title="ثبت مشتری جدید هنوز Endpoint تأییدشده ندارد"><PlusIcon /> مشتری جدید</button>
        </section>

        {error ? (
          <section className="vh-live-state error" role="alert">
            <div><strong>لیست مشتریان دریافت نشد</strong><span>{error}</span></div>
            <button type="button" onClick={() => void reload()}>تلاش دوباره</button>
          </section>
        ) : loading ? (
          <section className="vh-live-state" role="status"><strong>در حال دریافت مشتریان واقعی…</strong><span>اطلاعات از Seller Workspace خوانده می‌شود.</span></section>
        ) : null}

        <section className="vc-summary" aria-label="خلاصه مشتریان">
          <article><span>مشتریان مسیر</span><strong>{customerCount.toLocaleString('fa-IR')}</strong><small>NGT زنده</small></article>
          <article><span>تعیین‌تکلیف امروز</span><strong>{completed.toLocaleString('fa-IR')}</strong><small>بازدیدهای پایان‌یافته</small></article>
          <article><span>نیازمند توجه مالی</span><strong>{followUp.toLocaleString('fa-IR')}</strong><small>دارای چک برگشتی</small></article>
        </section>

        <section className="vc-tools" aria-label="جستجوی مشتریان">
          <label className="vc-search">
            <SearchIcon />
            <input value={query} onChange={(event) => updateSearch(event.target.value)} placeholder="نام، کد یا آدرس مشتری" aria-label="جستجوی مشتری" />
          </label>
        </section>

        <div className="vc-chips" role="tablist" aria-label="فیلتر وضعیت مشتری">
          {(['همه', 'فعال', 'پیگیری', 'انجام شده'] as const).map((item) => (
            <button type="button" role="tab" aria-selected={filter === item} className={filter === item ? 'active' : ''} key={item} onClick={() => updateFilter(item)}>{item}</button>
          ))}
        </div>

        <section className="vc-list" aria-label="لیست مشتریان">
          <div className="vc-list-head"><strong>{visibleCustomers.length.toLocaleString('fa-IR')} مشتری</strong><span>ترتیب رسمی مسیر NGT</span></div>

          {visibleCustomers.map((customer) => {
            const status = customerStatus(customer)
            const hasPhone = Boolean(customer.mobile || customer.phone)
            const hasLocation = customer.latitude !== null && customer.longitude !== null
            return (
              <article className="vc-card" key={String(customer.id)}>
                <div className="vc-customer-icon"><StoreIcon /></div>
                <div className="vc-card-main">
                  <div className="vc-card-title"><strong>{customerTitle(customer)}</strong><span className={`vc-status vc-status-${statusClass(status)}`}>{status}</span></div>
                  <span className="vc-owner">{customer.name || `کد ${customer.code}`}</span>
                  <div className="vc-meta">
                    <span><PinIcon /> {customer.address || 'نشانی ثبت نشده'}</span>
                    <span><ClockIcon /> آخرین تعیین‌تکلیف: {visitDate(customer)}</span>
                  </div>
                  <div className="vc-commerce"><span><CartIcon /> فاکتور باز: {fullCustomers ? customer.open_invoice_count.toLocaleString('fa-IR') : '—'}</span><strong>{fullCustomers ? money(customer.open_invoice_remaining) : '—'}</strong></div>
                </div>
                <div className="vc-card-actions">
                  <button type="button" disabled={!hasPhone} aria-label={`تماس با ${customerTitle(customer)}`} onClick={() => callCustomer(customer)}><PhoneIcon /></button>
                  <button type="button" disabled={!hasLocation} aria-label={`مسیریابی ${customerTitle(customer)}`} onClick={() => navigateCustomer(customer)}><MapIcon /></button>
                  <button type="button" aria-label={`جزئیات ${customerTitle(customer)}`} onClick={() => onNavigate(`/visitor/customers/${customer.id}`)}><ChevronLeftIcon /></button>
                </div>
              </article>
            )
          })}

          {!loading && visibleCustomers.length === 0 ? (
            <div className="vc-empty"><UserGroupIcon /><strong>مشتری پیدا نشد</strong><span>{displayCustomers.length ? 'عبارت جستجو یا فیلتر را تغییر بده.' : 'برای این مسیر مشتری فعالی دریافت نشد.'}</span></div>
          ) : null}
        </section>

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item active" type="button" aria-current="page" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
