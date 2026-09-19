import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import {
  BellIcon,
  CartIcon,
  ChartIcon,
  ChequeIcon,
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
import { VisitorPicker } from './VisitorPicker'
import { AppHeader, BottomDock } from '../design-system/components'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotificationBadge } from '../state/VisitorNotificationsContext'
import { neginApi, type SellerCustomer } from '../api/neginApi'
import '../design-system/living/index.css'
import '../styles/visitor-customers-depth.css'

type Props = { onNavigate: (path: string) => void }
type CustomerFocus = 'pending' | 'risk' | 'completed' | 'all'

type FocusMeta = {
  title: string
  subtitle: string
  icon: ReactNode
  tone: 'gold' | 'danger' | 'mint' | 'blue'
}

function customerTitle(customer: SellerCustomer) {
  return customer.store_name || customer.name || `مشتری ${customer.code}`
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

function isCompleted(customer: SellerCustomer) {
  return customer.visit_resolution?.status === 'completed'
}

function hasFinancialRisk(customer: SellerCustomer) {
  return Number(customer.financial_snapshot?.returned_cheque_count ?? 0) > 0
}

export function VisitorCustomersScreen({ onNavigate }: Props) {
  const { attentionCount, highestSeverity } = useVisitorNotificationBadge()
  const { profile } = useVisitorAuth()
  const { customers, customerCount, activeRouteId, activeRouteTitle, routes, offDay, loading, error, reload } = useVisitorLiveData()
  const [fullCustomers, setFullCustomers] = useState<SellerCustomer[] | null>(null)
  const [browseRouteId, setBrowseRouteId] = useState('')
  const [focus, setFocus] = useState<CustomerFocus | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  const effectiveRouteId = activeRouteId || browseRouteId
  const effectiveRouteTitle = activeRouteTitle || routes.find((route) => route.id === browseRouteId)?.title || ''

  useEffect(() => {
    const firstRoute = routes[0]
    if (!activeRouteId && offDay && firstRoute && !browseRouteId) setBrowseRouteId(firstRoute.id)
  }, [activeRouteId, browseRouteId, offDay, routes])

  useEffect(() => {
    let cancelled = false
    if (!effectiveRouteId) {
      setFullCustomers(null)
      return () => { cancelled = true }
    }
    setFullCustomers(null)
    void neginApi.routeCustomers(effectiveRouteId, 'full')
      .then((data) => {
        if (!cancelled) setFullCustomers(data.customers)
      })
      .catch(() => {
        if (!cancelled) setFullCustomers(null)
      })
    return () => { cancelled = true }
  }, [effectiveRouteId])

  useEffect(() => {
    const onPopState = () => setFocus(null)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const displayCustomers = fullCustomers ?? customers
  const total = fullCustomers?.length ?? customerCount
  const completed = displayCustomers.filter(isCompleted).length
  const pending = Math.max(0, total - completed)
  const financialRisk = displayCustomers.filter(hasFinancialRisk).length
  const completionPercent = total > 0 ? Math.round((completed / total) * 100) : 0
  const query = searchParams.get('q') ?? ''

  const focusMeta: Record<CustomerFocus, FocusMeta> = {
    pending: {
      title: 'در انتظار بازدید',
      subtitle: 'مشتریانی که هنوز تعیین‌تکلیف نشده‌اند',
      icon: <ClockIcon />,
      tone: 'gold',
    },
    risk: {
      title: 'نیازمند توجه مالی',
      subtitle: 'مشتریان دارای چک برگشتی ثبت‌شده',
      icon: <ChequeIcon />,
      tone: 'danger',
    },
    completed: {
      title: 'تعیین‌تکلیف‌شده',
      subtitle: 'بازدیدهای پایان‌یافته این Route',
      icon: <ChartIcon />,
      tone: 'mint',
    },
    all: {
      title: 'همه مشتریان',
      subtitle: 'فهرست کامل Route انتخاب‌شده',
      icon: <UserGroupIcon />,
      tone: 'blue',
    },
  }

  const visibleCustomers = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('fa-IR')
    return displayCustomers.filter((customer) => {
      const matchesFocus = !focus
        || focus === 'all'
        || (focus === 'pending' && !isCompleted(customer))
        || (focus === 'risk' && hasFinancialRisk(customer))
        || (focus === 'completed' && isCompleted(customer))
      if (!matchesFocus) return false
      if (!normalized) return true
      const haystack = `${customerTitle(customer)} ${customer.name} ${customer.code} ${customer.address}`.toLocaleLowerCase('fa-IR')
      return haystack.includes(normalized)
    })
  }, [displayCustomers, focus, query])

  function updateSearch(nextQuery: string) {
    const next = new URLSearchParams(searchParams)
    if (nextQuery.trim()) next.set('q', nextQuery)
    else next.delete('q')
    setSearchParams(next, { replace: true })
  }

  function openFocus(nextFocus: CustomerFocus) {
    const next = new URLSearchParams(searchParams)
    next.delete('q')
    setSearchParams(next, { replace: true })
    window.history.pushState({ neginCustomerDepth: 1 }, '', window.location.href)
    setFocus(nextFocus)
  }

  function closeFocus() {
    window.history.back()
  }

  const routeOptions = routes.map((route) => ({
    value: route.id,
    label: route.title,
    meta: `${Number(route.customer_count ?? 0).toLocaleString('fa-IR')} مشتری`,
  }))

  return (
    <main className="vh-page vh-live-ui ng-living-root vc-depth-page" dir="rtl" data-live-ui="unified" data-living-ui="on">
      <div className="vh-shell vc-shell">
        <AppHeader
          avatarText={profile?.full_name?.charAt(0) || profile?.username?.charAt(0) || 'و'}
          title={profile?.full_name || profile?.username || 'ویزیتور'}
          subtitle={profile?.branch || profile?.sales_line || 'حساب سازمانی'}
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

        <section className="vc-depth-stage ng-depth-stage" data-depth={focus ? 1 : 0}>
          <span className="ng-depth-backplane" data-plane="1" aria-hidden="true" />

          {!focus ? (
            <div className="vc-depth-layer vc-depth-root">
              <section className="vc-command ng-layer-surface">
                <div className="vc-command-copy">
                  <span className="vc-command-live"><i /> مشتریان · داده زنده</span>
                  <h1>{pending.toLocaleString('fa-IR')} مشتری هنوز بازدید نشده</h1>
                  <p>{offDay ? 'حالت مرور؛ Customer 360 فقط خواندنی است.' : `${completionPercent.toLocaleString('fa-IR')}٪ مشتریان این مسیر تعیین‌تکلیف شده‌اند.`}</p>
                </div>
                <div className="vc-command-progress" aria-label={`پیشرفت ${completionPercent} درصد`}>
                  <strong>{completionPercent.toLocaleString('fa-IR')}٪</strong>
                  <small>تکمیل</small>
                </div>
              </section>

              {offDay && routeOptions.length ? (
                <VisitorPicker
                  className="vc-depth-route-picker"
                  label="مسیر مرور"
                  value={effectiveRouteId || ''}
                  options={routeOptions}
                  onChange={(value) => setBrowseRouteId(value)}
                  sheetTitle="انتخاب مسیر مشتریان"
                />
              ) : null}

              {error && !offDay ? (
                <button type="button" className="vc-depth-error ng-living-interactive" onClick={() => void reload()}>
                  <span><strong>داده مشتریان دریافت نشد</strong><small>{error}</small></span>
                  <ChevronLeftIcon />
                </button>
              ) : null}

              <div className="vc-depth-portals" aria-label="دسته‌های مشتریان">
                <button type="button" className="vc-depth-portal ng-portal-surface ng-living-interactive" data-tone="gold" onClick={() => openFocus('pending')}>
                  <span className="vc-depth-portal-icon ng-portal-accent"><ClockIcon /></span>
                  <span><small>در انتظار بازدید</small><strong>{pending.toLocaleString('fa-IR')}</strong><em>اقدام باز امروز</em></span>
                  <ChevronLeftIcon />
                </button>

                <button type="button" className="vc-depth-portal ng-portal-surface ng-living-interactive" data-tone={financialRisk ? 'danger' : 'mint'} onClick={() => openFocus('risk')}>
                  <span className="vc-depth-portal-icon ng-portal-accent"><ChequeIcon /></span>
                  <span><small>توجه مالی</small><strong>{financialRisk.toLocaleString('fa-IR')}</strong><em>{financialRisk ? 'دارای چک برگشتی' : 'مورد فعالی نیست'}</em></span>
                  <ChevronLeftIcon />
                </button>

                <button type="button" className="vc-depth-portal ng-portal-surface ng-living-interactive" data-tone="mint" onClick={() => openFocus('completed')}>
                  <span className="vc-depth-portal-icon ng-portal-accent"><ChartIcon /></span>
                  <span><small>تعیین‌تکلیف‌شده</small><strong>{completed.toLocaleString('fa-IR')}</strong><em>بازدید پایان‌یافته</em></span>
                  <ChevronLeftIcon />
                </button>

                <button type="button" className="vc-depth-portal ng-portal-surface ng-living-interactive" data-tone="blue" onClick={() => openFocus('all')}>
                  <span className="vc-depth-portal-icon ng-portal-accent"><UserGroupIcon /></span>
                  <span><small>همه مشتریان</small><strong>{total.toLocaleString('fa-IR')}</strong><em>{effectiveRouteTitle || 'Route انتخاب‌شده'}</em></span>
                  <ChevronLeftIcon />
                </button>
              </div>
            </div>
          ) : (
            <div className="vc-depth-layer vc-depth-list ng-layer-surface">
              <header className="vc-depth-head">
                <button type="button" className="vc-depth-back ng-living-interactive" onClick={closeFocus} aria-label="بازگشت"><ChevronLeftIcon /></button>
                <span className="vc-depth-head-icon ng-portal-accent" data-tone={focusMeta[focus].tone}>{focusMeta[focus].icon}</span>
                <span>
                  <small>مشتریان · {effectiveRouteTitle || 'Route'}</small>
                  <strong>{focusMeta[focus].title}</strong>
                  <em>{focusMeta[focus].subtitle}</em>
                </span>
              </header>

              <label className="vc-depth-search">
                <SearchIcon />
                <input value={query} onChange={(event) => updateSearch(event.target.value)} placeholder="نام، کد یا آدرس مشتری" aria-label="جستجوی مشتری" />
                <b>{visibleCustomers.length.toLocaleString('fa-IR')}</b>
              </label>

              <section className="vc-depth-customer-list" aria-label={focusMeta[focus].title}>
                {loading && !fullCustomers ? (
                  <div className="vc-depth-loading"><strong>در حال دریافت مشتریان واقعی…</strong><span>Seller Workspace</span></div>
                ) : null}

                {visibleCustomers.map((customer) => {
                  const hasPhone = Boolean(customer.mobile || customer.phone)
                  const hasLocation = customer.latitude !== null && customer.longitude !== null
                  const risk = hasFinancialRisk(customer)
                  return (
                    <article className="vc-depth-customer ng-detail-surface" key={String(customer.id)}>
                      <span className={`vc-depth-customer-icon ${risk ? 'risk' : ''}`}><StoreIcon /></span>
                      <button type="button" className="vc-depth-customer-main" onClick={() => onNavigate(`/visitor/customers/${customer.id}`)}>
                        <span className="vc-depth-customer-title"><strong>{customerTitle(customer)}</strong>{risk ? <b>ریسک مالی</b> : null}</span>
                        <small>{customer.name || `کد ${customer.code}`}</small>
                        <em>{customer.address || 'نشانی ثبت نشده'}</em>
                        <span className="vc-depth-customer-meta">
                          <i><ClockIcon /> {isCompleted(customer) ? `تعیین‌تکلیف ${visitDate(customer)}` : 'بازدید باز'}</i>
                          {fullCustomers && customer.open_invoice_remaining > 0 ? <i><CartIcon /> مانده {money(customer.open_invoice_remaining)}</i> : null}
                        </span>
                      </button>
                      <div className="vc-depth-customer-actions">
                        <button type="button" disabled={!hasPhone} aria-label="تماس" onClick={() => callCustomer(customer)}><PhoneIcon /></button>
                        <button type="button" disabled={!hasLocation} aria-label="مسیریابی" onClick={() => navigateCustomer(customer)}><MapIcon /></button>
                        <button type="button" aria-label="Customer 360" onClick={() => onNavigate(`/visitor/customers/${customer.id}`)}><ChevronLeftIcon /></button>
                      </div>
                    </article>
                  )
                })}

                {!loading && visibleCustomers.length === 0 ? (
                  <div className="vc-depth-empty"><UserGroupIcon /><strong>مشتری‌ای در این دسته نیست</strong><span>دسته یا جستجو را تغییر بده.</span></div>
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
            { key: 'customers', label: 'مشتریان', icon: <UserGroupIcon />, active: true, onClick: () => setFocus(null) },
            { key: 'reports', label: 'گزارش‌ها', icon: <ChartIcon />, onClick: () => onNavigate('/visitor/reports') },
          ]}
          primary={{ label: 'سفارش', icon: <PlusIcon />, onClick: () => onNavigate('/visitor/orders') }}
        />
      </div>
    </main>
  )
}
