import { useEffect, useMemo, useState } from 'react'
import { neginApi, type CustomerProfileEditable, type CustomerProfileResponse, type SellerCustomer } from '../api/neginApi'
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
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import '../design-system/living/index.css'
import '../styles/living-ui-pilot.css'

type Props = {
  customerId?: string
  onNavigate: (path: string) => void
  onBack: () => void
}

type Tab = 'overview' | 'financial' | 'history'
type EditableField = keyof CustomerProfileEditable

const EDIT_FIELD_LABELS: Record<EditableField, string> = {
  phone: 'تلفن',
  national_code: 'کد ملی',
  economic_code: 'کد اقتصادی',
  store_name: 'نام فروشگاه',
  address: 'آدرس',
  mobile: 'موبایل',
  customer_activity_id: 'نوع فعالیت',
  state_id: 'استان',
  city_id: 'شهر',
  county_id: 'شهرستان',
  city_zone: 'منطقه شهری',
  customer_level_id: 'سطح مشتری',
  customer_category_id: 'گروه مشتری',
  owner_type_ref: 'نوع مالکیت',
  postal_code: 'کد پستی',
  customer_code: 'کد مشتری',
  latitude: 'عرض جغرافیایی',
  longitude: 'طول جغرافیایی',
}

const LOOKUP_FIELDS: Partial<Record<EditableField, string>> = {
  customer_activity_id: 'activity',
  state_id: 'state',
  city_id: 'city',
  county_id: 'county',
  customer_level_id: 'level',
  customer_category_id: 'category',
  owner_type_ref: 'owner_type',
}

const NUMERIC_FIELDS = new Set<EditableField>(['city_zone', 'owner_type_ref', 'latitude', 'longitude'])
const WIDE_EDIT_FIELDS = new Set<EditableField>(['store_name', 'address'])


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
  const { activeRouteId, customerById, offDay, loading: liveDataLoading, workCalendar } = useVisitorLiveData()
  const { activeVisit } = useVisitorWorkflow()
  const [tab, setTab] = useState<Tab>('overview')
  const [profile, setProfile] = useState<CustomerProfileResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<CustomerProfileEditable>({})
  const [saveBusy, setSaveBusy] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveNotice, setSaveNotice] = useState<string | null>(null)
  const [locationBusy, setLocationBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    if (!customerId) {
      setProfile(null)
      setError('شناسه مشتری در دسترس نیست.')
      return
    }
    if (!activeRouteId && !offDay) {
      setProfile(null)
      setError(liveDataLoading ? null : 'مسیر فعال مشتری در دسترس نیست.')
      return
    }

    setLoading(true)
    setError(null)
    const profileRequest = activeRouteId
      ? neginApi.customerProfile(activeRouteId, customerId)
      : neginApi.customerProfileAnyRoute(customerId)
    void profileRequest
      .then((data) => {
        if (cancelled) return
        setProfile(data)
        setDraft(data.draft ?? data.customer.editable ?? {})
        setEditing(false)
        setSaveError(null)
        setSaveNotice(null)
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'پروفایل مشتری دریافت نشد.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [activeRouteId, customerId, liveDataLoading, offDay])

  const customer = profile?.customer ?? customerById(customerId)
  const finance = customer?.financial_snapshot ?? {}
  const locationLabel = useMemo(() => {
    if (!customer) return '—'
    if (customer.latitude === null || customer.longitude === null) return 'موقعیت ثبت نشده'
    return `${customer.latitude.toFixed(5)} , ${customer.longitude.toFixed(5)}`
  }, [customer])

  const hasPhone = Boolean(customer?.mobile || customer?.phone)
  const hasLocation = customer?.latitude !== null && customer?.longitude !== null
  const activeVisitHere = Boolean(activeVisit && customer && String(activeVisit.customerId) === String(customer.id))
  const returnedChequeCount = Number(finance.returned_cheque_count ?? 0)
  const openInvoiceCount = Number(customer?.open_invoice_count ?? 0)
  const activeFields = profile?.editable_contract?.active_fields ?? []
  const editableFields = activeRouteId && !offDay ? activeFields.filter(
    (field): field is EditableField => Object.prototype.hasOwnProperty.call(EDIT_FIELD_LABELS, field),
  ) : []

  function cancelEditing() {
    setDraft(profile?.draft ?? profile?.customer.editable ?? {})
    setSaveError(null)
    setEditing(false)
  }

  function setDraftField(field: EditableField, rawValue: string) {
    let value: string | number | null = rawValue
    if (NUMERIC_FIELDS.has(field)) value = rawValue.trim() === '' ? null : Number(rawValue)
    setDraft((current) => {
      const next = { ...current, [field]: value } as CustomerProfileEditable
      if (field === 'state_id' && current.state_id !== rawValue) next.city_id = null
      return next
    })
  }

  function captureCurrentLocation() {
    if (!navigator.geolocation) {
      setSaveError('دسترسی GPS در این دستگاه در دسترس نیست.')
      return
    }
    setLocationBusy(true)
    setSaveError(null)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setDraft((current) => ({
          ...current,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }))
        setLocationBusy(false)
      },
      () => {
        setSaveError('موقعیت فعلی دریافت نشد. مجوز GPS و دقت موقعیت را بررسی کنید.')
        setLocationBusy(false)
      },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 },
    )
  }

  async function saveProfileDraft() {
    if (!activeRouteId || !customerId || !profile || saveBusy) return
    setSaveBusy(true)
    setSaveError(null)
    setSaveNotice(null)
    try {
      const payload = Object.fromEntries(
        editableFields.map((field) => [field, draft[field] ?? null]),
      ) as CustomerProfileEditable
      const result = await neginApi.saveCustomerProfileDraft(activeRouteId, customerId, payload)
      setDraft(result.draft)
      setProfile((current) => current ? {
        ...current,
        draft: result.draft,
        draft_updated_at: result.updated_at,
      } : current)
      setEditing(false)
      setSaveNotice('پیش‌نویس محلی ذخیره شد؛ هنوز به NGT/Varanegar ارسال نشده است.')
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'ذخیره پیش‌نویس انجام نشد.')
    } finally {
      setSaveBusy(false)
    }
  }

  return (
    <main className="vh-page vh-live-ui ng-living-root c360-app-page" dir="rtl" data-live-ui="unified">
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

        {error ? <section className="vh-live-state error" role="alert"><div><strong>پروفایل مشتری دریافت نشد</strong><span>{error}</span></div></section> : null}
        {loading ? <section className="vh-live-state" role="status"><strong>در حال دریافت Customer 360…</strong><span>اطلاعات از NGT و منابع مالی مجاز خوانده می‌شود.</span></section> : null}

        {customer ? (
          <>
            <section className="c360-identity ng-living-surface" data-state={returnedChequeCount ? 'attention' : 'live'}>
              <div className="c360-store-icon"><StoreIcon /></div>
              <div className="c360-identity-copy">
                <div className="c360-title-row"><h2>{titleOf(customer)}</h2><span className="c360-live">زنده</span>{returnedChequeCount ? <span className="c360-risk">چک برگشتی</span> : null}</div>
                <p>{customer.name || '—'} · کد {customer.code || '—'}</p>
                <span><PinIcon /> {customer.address || 'نشانی ثبت نشده'} · {profile?.route.title || 'مسیر روز'}</span>
                {profile?.customer.alarm ? <div className="c360-inline-alert"><strong>هشدار NGT</strong><span>{profile.customer.alarm}</span></div> : null}
              </div>
              <button type="button" className="c360-identity-back" onClick={onBack} aria-label="Back"><ChevronLeftIcon /></button>
            </section>

            <section className={`c360-workflow-card ng-living-surface ${offDay ? 'is-offday' : ''}`} data-visit-state={offDay ? 'offday' : activeVisitHere ? 'active' : 'ready'} aria-label="اقدام بعدی مشتری">
              {offDay ? (
                <div className="c360-offday-strip">
                  <div><span>حالت مرور</span><strong>روز غیرکاری NGT</strong><small>بازدید و سفارش در مسیر کاری بعدی فعال می‌شود.</small></div>
                  <b>{workCalendar?.date || '—'}</b>
                </div>
              ) : (
                <>
                  <div className="c360-workflow-head"><span>{activeVisitHere ? 'ویزیت فعال' : 'گام بعدی'}</span><strong>{activeVisitHere ? 'ادامه کار با همین مشتری' : 'برای این مشتری چه کاری انجام می‌دهی؟'}</strong><small>{activeVisitHere ? 'ویزیت باز است؛ سفارش و نتیجه ویزیت در همان جریان ادامه پیدا می‌کند.' : 'شروع بازدید، سفارش و اقدامات تماس بدون خروج از زمینه مشتری.'}</small></div>
                  <div className="c360-primary-actions">
                    <button type="button" className="visit ng-living-interactive" onClick={() => onNavigate(`/visitor/route?customer=${customer.id}&intent=visit`)}><RouteArrowIcon /><span>{activeVisitHere ? 'ادامه بازدید' : 'شروع بازدید'}</span></button>
                    <button type="button" className="order ng-living-interactive" onClick={() => onNavigate(`/visitor/orders?customer=${customer.id}${activeVisitHere ? `&visit=${encodeURIComponent(activeVisit?.id ?? '')}` : ''}`)}><CartIcon /><span>سفارش</span></button>
                  </div>
                </>
              )}
              <div className="c360-utility-actions"><button type="button" disabled={!hasPhone} onClick={() => callCustomer(customer)}><PhoneIcon /><span>تماس</span></button><button type="button" disabled={!hasLocation} onClick={() => navigateCustomer(customer)}><MapIcon /><span>مسیریابی</span></button></div>
              <div className="c360-pulse-rail" role="list" aria-label="وضعیت سریع مشتری">
                <span role="listitem"><small>بازدید</small><strong dir="ltr">{Number(profile?.customer.visit_count ?? 0).toLocaleString('fa-IR')}</strong></span><span role="listitem"><small>سفارش</small><strong dir="ltr">{Number(profile?.customer.order_count ?? 0).toLocaleString('fa-IR')}</strong></span><span role="listitem" className={openInvoiceCount ? 'attention' : ''}><small>فاکتور باز</small><strong dir="ltr">{openInvoiceCount.toLocaleString('fa-IR')}</strong></span><span role="listitem" className={returnedChequeCount ? 'danger' : 'safe'}><small>چک برگشتی</small><strong dir="ltr">{returnedChequeCount.toLocaleString('fa-IR')}</strong></span>
              </div>
            </section>
            <div className="c360-tabs" role="tablist" aria-label="بخش‌های پروفایل مشتری">
              <button type="button" role="tab" aria-selected={tab === 'overview'} className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>نمای کلی</button>
              <button type="button" role="tab" aria-selected={tab === 'financial'} className={tab === 'financial' ? 'active' : ''} onClick={() => setTab('financial')}>مالی</button>
              <button type="button" role="tab" aria-selected={tab === 'history'} className={tab === 'history' ? 'active' : ''} onClick={() => setTab('history')}>سوابق</button>
            </div>

            {tab === 'overview' ? (
              <section className="c360-stack">
                <article className="c360-panel">
                  <div className="c360-panel-head">
                    <strong>اطلاعات مشتری</strong>
                    {editableFields.length ? (
                      <button type="button" onClick={() => {
                        setSaveError(null)
                        setSaveNotice(null)
                        setEditing((value) => !value)
                      }}>
                        {editing ? 'بستن ویرایش' : `ویرایش ${editableFields.length.toLocaleString('fa-IR')} فیلد`}
                      </button>
                    ) : <span>فقط خواندنی</span>}
                  </div>
                  <dl className="c360-info-grid">
                    <div><dt>تلفن</dt><dd>{customer.phone || '—'}</dd></div>
                    <div><dt>موبایل</dt><dd>{customer.mobile || '—'}</dd></div>
                    <div className="wide"><dt>آدرس</dt><dd>{customer.address || 'ثبت نشده'}</dd></div>
                    {profile?.customer.activity_name ? <div><dt>فعالیت</dt><dd>{profile.customer.activity_name}</dd></div> : null}
                    {profile?.customer.level_name ? <div><dt>سطح مشتری</dt><dd>{profile.customer.level_name}</dd></div> : null}
                  </dl>
                  {editing && editableFields.length ? (
                    <div className="c360-edit-form">
                      <div className="c360-edit-grid">
                        {editableFields.map((field) => {
                          const lookupKind = LOOKUP_FIELDS[field]
                          let options = lookupKind ? (profile?.lookups?.[lookupKind] ?? []) : []
                          if (field === 'city_id' && draft.state_id) {
                            options = options.filter((item) => !item.parent_id || item.parent_id === draft.state_id)
                          }
                          const value = draft[field]
                          const displayValue = value === null || value === undefined ? '' : String(value)
                          const wide = WIDE_EDIT_FIELDS.has(field)
                          if (lookupKind) {
                            return (
                              <label className={`c360-edit-field ${wide ? 'wide' : ''}`} key={field}>
                                <span>{EDIT_FIELD_LABELS[field]}</span>
                                <select value={displayValue} onChange={(event) => setDraftField(field, event.target.value)}>
                                  <option value="">انتخاب نشده</option>
                                  {options.map((item) => (
                                    <option
                                      key={`${field}-${item.id}-${item.ref ?? ''}`}
                                      value={field === 'owner_type_ref' ? String(item.ref ?? '') : item.id}
                                    >
                                      {item.title}
                                    </option>
                                  ))}
                                </select>
                              </label>
                            )
                          }
                          if (field === 'address') {
                            return (
                              <label className="c360-edit-field wide" key={field}>
                                <span>{EDIT_FIELD_LABELS[field]}</span>
                                <textarea value={displayValue} onChange={(event) => setDraftField(field, event.target.value)} />
                              </label>
                            )
                          }
                          return (
                            <label className={`c360-edit-field ${wide ? 'wide' : ''}`} key={field}>
                              <span>{EDIT_FIELD_LABELS[field]}</span>
                              <input
                                type={NUMERIC_FIELDS.has(field) ? 'number' : 'text'}
                                inputMode={NUMERIC_FIELDS.has(field) ? 'decimal' : undefined}
                                value={displayValue}
                                onChange={(event) => setDraftField(field, event.target.value)}
                              />
                            </label>
                          )
                        })}
                      </div>
                      {editableFields.includes('latitude') && editableFields.includes('longitude') ? (
                        <button type="button" className="c360-location-capture" onClick={captureCurrentLocation} disabled={locationBusy}>
                          <PinIcon /> {locationBusy ? 'در حال دریافت موقعیت…' : 'ثبت موقعیت فعلی'}
                        </button>
                      ) : null}
                      {saveError ? <p className="c360-edit-message" role="alert">{saveError}</p> : null}
                      <div className="c360-edit-actions">
                        <button type="button" onClick={cancelEditing} disabled={saveBusy}>انصراف</button>
                        <button type="button" className="primary" onClick={() => void saveProfileDraft()} disabled={saveBusy}>
                          {saveBusy ? 'در حال ذخیره…' : 'ذخیره پیش‌نویس'}
                        </button>
                      </div>
                      <p className="c360-permission-note">این تغییرات فقط به‌صورت پیش‌نویس محلی ذخیره می‌شوند و به NGT/Varanegar ارسال نمی‌شوند.</p>
                    </div>
                  ) : null}
                  {saveNotice ? <p className="c360-permission-note" role="status">{saveNotice}</p> : null}
                </article>

                <article className="c360-panel c360-location-card">
                  <div className="c360-panel-head"><strong>موقعیت مشتری</strong><span className={hasLocation ? 'good' : ''}>{hasLocation ? <><CheckCircleIcon /> ثبت‌شده</> : 'ثبت نشده'}</span></div>
                  <div className="c360-location-body"><div className="c360-pin"><PinIcon /></div><div><strong>{locationLabel}</strong><span>{customer.location_source || 'NGT / ERP'}</span></div></div>
                </article>

                <article className="c360-panel c360-ai-card">
                  <div className="c360-panel-head"><strong>Negin AI</strong><span className="ai-dot">✦</span></div>
                  <p>برای تحلیل این مشتری، گفتگو را با زمینه همین Customer 360 باز کن. پاسخ از سرویس واقعی NeginAI دریافت می‌شود.</p>
                  <button type="button" className="c360-ai-open" onClick={() => onNavigate(`/visitor/ai?context=customer&customer=${customer.id}`)}>گفتگو با Negin AI <ChevronLeftIcon /></button>
                </article>
              </section>
            ) : null}

            {tab === 'financial' ? (
              <section className="c360-stack">
                <article className="c360-panel c360-finance-sheet ng-living-surface">
                  <div className="c360-panel-head"><strong>وضعیت مالی مشتری</strong><span>داده زنده مجاز</span></div>
                  <div className="c360-finance-list"><div><WalletIcon /><span><small>مانده کاردکس</small><strong>{money(customer.cardex_balance)}</strong></span></div><div className={openInvoiceCount ? 'attention' : ''}><InvoiceIcon /><span><small>فاکتور باز</small><strong>{customer.open_invoice_count.toLocaleString('fa-IR')} · {money(customer.open_invoice_remaining)}</strong></span></div><div><ChartIcon /><span><small>اعتبار باقیمانده</small><strong>{money(finance.combined_remaining)}</strong></span></div><div className={returnedChequeCount ? 'danger' : 'safe'}><ChequeIcon /><span><small>چک برگشتی</small><strong>{returnedChequeCount.toLocaleString('fa-IR')} · {money(finance.returned_cheque_amount)}</strong></span></div></div>
                </article>
                <p className="c360-permission-note">Frontend فقط پاسخ مجاز Seller Workspace را نمایش می‌دهد و مستقیماً به دیتابیس وصل نیست.</p>
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
          <button className="vh-order" type="button" disabled={offDay} aria-disabled={offDay} onClick={() => onNavigate(customer ? `/visitor/orders?customer=${customer.id}` : '/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item active" type="button" aria-current="page" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}
