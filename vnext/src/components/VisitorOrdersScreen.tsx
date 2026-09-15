import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  completeServerVisit,
  createSavedPrevisitRequest,
  getPrevisitContext,
  getVisitDraft,
  previewPrevisit,
  type PrevisitContextResponse,
  type PrevisitPreviewResponse,
  type PrevisitProduct,
  type RouteSavedRequest,
} from '../api/neginApi'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import {
  BellIcon,
  BoxIcon,
  CartIcon,
  ChartIcon,
  CheckCircleIcon,
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

type Props = {
  onNavigate: (path: string) => void
  customerId?: string | undefined
  draftId?: string | undefined
  visitId?: string | undefined
  returnTo?: string | undefined
}

type View = 'products' | 'catalog' | 'cart'

function number(value: number) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(value)
}

export function VisitorOrdersScreen({ onNavigate, customerId, visitId, returnTo }: Props) {
  const { profile } = useVisitorAuth()
  const { unreadCount } = useVisitorNotifications()
  const { activeRouteId, activeRouteTitle, customers, customerById } = useVisitorLiveData()
  const { activeVisit, completeVisit } = useVisitorWorkflow()

  const effectiveVisitId = visitId ?? activeVisit?.id
  const [visitDraft, setVisitDraft] = useState<Awaited<ReturnType<typeof getVisitDraft>> | null>(null)
  const [selectedCustomerId, setSelectedCustomerId] = useState(
    activeVisit?.customerId ?? customerId ?? '',
  )
  const [context, setContext] = useState<PrevisitContextResponse | null>(null)
  const [contextLoading, setContextLoading] = useState(false)
  const [contextError, setContextError] = useState<string | null>(null)
  const [view, setView] = useState<View>('products')
  const [query, setQuery] = useState('')
  const [brand, setBrand] = useState('')
  const [groupId, setGroupId] = useState('')
  const [catalogId, setCatalogId] = useState('')
  const [inStockOnly, setInStockOnly] = useState(true)
  const [cart, setCart] = useState<Record<string, number>>({})
  const [orderTypeRef, setOrderTypeRef] = useState<number | null>(null)
  const [paymentRef, setPaymentRef] = useState('')
  const [warehouseRef, setWarehouseRef] = useState<number | null>(null)
  const [preview, setPreview] = useState<PrevisitPreviewResponse | null>(null)
  const [previewBusy, setPreviewBusy] = useState(false)
  const [saveBusy, setSaveBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [customerPicker, setCustomerPicker] = useState(false)
  const [savedRequest, setSavedRequest] = useState<RouteSavedRequest | null>(null)
  const hydratedVisitRef = useRef('')

  const routeId = visitDraft?.route_id ?? activeVisit?.routeId ?? activeRouteId
  const lockedCustomerId = visitDraft?.customer_id ?? activeVisit?.customerId
  const effectiveCustomerId = lockedCustomerId ?? selectedCustomerId
  const selectedCustomer = effectiveCustomerId ? customerById(effectiveCustomerId) : undefined
  const visitLocked = Boolean(effectiveVisitId && lockedCustomerId)

  const flash = useCallback((message: string) => {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2600)
  }, [])

  useEffect(() => {
    if (!effectiveVisitId) {
      setVisitDraft(null)
      return
    }
    let cancelled = false
    void getVisitDraft(effectiveVisitId)
      .then((draft) => {
        if (cancelled) return
        setVisitDraft(draft)
        setSelectedCustomerId(String(draft.customer_id))
      })
      .catch(() => {
        if (!cancelled) setVisitDraft(null)
      })
    return () => { cancelled = true }
  }, [effectiveVisitId])

  useEffect(() => {
    if (lockedCustomerId) {
      setSelectedCustomerId(String(lockedCustomerId))
      return
    }
    if (selectedCustomerId && customers.some((customer) => String(customer.id) === selectedCustomerId)) return
    const requested = customerId && customers.find((customer) => String(customer.id) === customerId)
    const first = requested ?? customers[0]
    setSelectedCustomerId(first ? String(first.id) : '')
  }, [customerId, customers, lockedCustomerId, selectedCustomerId])

  useEffect(() => {
    if (!routeId || !effectiveCustomerId) {
      setContext(null)
      setContextError(null)
      return
    }
    let cancelled = false
    setContextLoading(true)
    setContextError(null)
    setPreview(null)
    void getPrevisitContext(routeId, effectiveCustomerId)
      .then((next) => {
        if (cancelled) return
        setContext(next)
        setOrderTypeRef((current) => (
          current && next.order_types.some((item) => item.id === current)
            ? current
            : next.order_types[0]?.id ?? null
        ))
        setPaymentRef((current) => (
          current && next.payment_types.some((item) => item.id === current)
            ? current
            : next.payment_types[0]?.id ?? ''
        ))
        setWarehouseRef((current) => {
          if (current && next.warehouses.some((item) => item.ref === current)) return current
          return next.warehouse_selection.default_ref || next.warehouses[0]?.ref || null
        })
      })
      .catch((caught) => {
        if (cancelled) return
        setContext(null)
        setContextError(caught instanceof Error ? caught.message : 'اطلاعات واقعی سفارش از NGT دریافت نشد.')
      })
      .finally(() => {
        if (!cancelled) setContextLoading(false)
      })
    return () => { cancelled = true }
  }, [effectiveCustomerId, routeId])

  useEffect(() => {
    if (!context || !visitDraft || hydratedVisitRef.current === visitDraft.visit_id) return
    hydratedVisitRef.current = visitDraft.visit_id
    const quantities: Record<string, number> = {}
    visitDraft.lines.forEach((line) => {
      if (context.products.some((product) => product.id === String(line.product_id))) {
        quantities[String(line.product_id)] = Number(line.quantity)
      }
    })
    setCart(quantities)
    if (visitDraft.order_type) {
      const match = context.order_types.find((item) => item.name === visitDraft.order_type)
      if (match) setOrderTypeRef(match.id)
    }
    if (visitDraft.payment_type) {
      const match = context.payment_types.find((item) => item.name === visitDraft.payment_type)
      if (match) setPaymentRef(match.id)
    }
    if (visitDraft.warehouse_ref) setWarehouseRef(visitDraft.warehouse_ref)
  }, [context, visitDraft])

  useEffect(() => {
    setPreview(null)
    setSavedRequest(null)
  }, [cart, orderTypeRef, paymentRef, warehouseRef, effectiveCustomerId])

  const selectedCatalog = useMemo(
    () => context?.grouped_catalogs.find((item) => item.id === catalogId) ?? null,
    [catalogId, context],
  )

  const availableFor = useCallback((product: PrevisitProduct) => {
    if (warehouseRef) {
      const stock = product.warehouse_inventory[String(warehouseRef)]
      if (stock) return Number(stock.available_qty || 0)
    }
    return Number(product.available_qty || 0)
  }, [warehouseRef])

  const indicativePriceFor = useCallback((product: PrevisitProduct) => {
    if (orderTypeRef !== null) {
      const price = Number(product.indicative_prices[String(orderTypeRef)] ?? 0)
      if (price > 0) return price
    }
    return Number(product.indicative_price || 0)
  }, [orderTypeRef])

  const visibleProducts = useMemo(() => {
    const q = query.trim().toLocaleLowerCase('fa')
    const catalogProductIds = selectedCatalog ? new Set(selectedCatalog.product_ids.map(String)) : null
    return (context?.products ?? []).filter((product) => {
      if (q && !`${product.name} ${product.code} ${product.brand} ${product.group}`.toLocaleLowerCase('fa').includes(q)) return false
      if (brand && product.brand !== brand) return false
      if (groupId && product.group_id !== groupId) return false
      if (catalogProductIds && !catalogProductIds.has(product.id)) return false
      if (inStockOnly && availableFor(product) <= 0) return false
      return true
    })
  }, [availableFor, brand, context, groupId, inStockOnly, query, selectedCatalog])

  const cartLines = useMemo(
    () => (context?.products ?? [])
      .filter((product) => Number(cart[product.id] ?? 0) > 0)
      .map((product) => ({ product, quantity: Number(cart[product.id] ?? 0) })),
    [cart, context],
  )
  const cartCount = cartLines.reduce((sum, line) => sum + line.quantity, 0)
  const indicativeSubtotal = cartLines.reduce(
    (sum, line) => sum + indicativePriceFor(line.product) * line.quantity,
    0,
  )

  function setQuantity(product: PrevisitProduct, requested: number) {
    const available = availableFor(product)
    const minimum = Math.max(0, Number(product.min_order_qty || 0))
    const maximum = Number(product.max_order_qty || 0) > 0
      ? Math.min(available, Number(product.max_order_qty))
      : available
    let next = Math.max(0, requested)
    if (next > 0 && minimum > 0 && next < minimum) next = minimum
    if (maximum >= 0 && next > maximum) {
      next = maximum
      flash(`حداکثر مقدار قابل سفارش ${number(maximum)} ${product.unit} است.`)
    }
    setCart((current) => {
      const updated = { ...current }
      if (next <= 0) delete updated[product.id]
      else updated[product.id] = next
      return updated
    })
  }

  async function calculatePreview() {
    if (!routeId || !effectiveCustomerId || !context) throw new Error('مسیر یا مشتری واقعی برای سفارش مشخص نیست.')
    if (!cartLines.length) throw new Error('سبد سفارش خالی است.')
    if (!orderTypeRef) throw new Error('نوع سفارش NGT انتخاب نشده است.')
    if (!paymentRef) throw new Error('نوع پرداخت NGT انتخاب نشده است.')
    setPreviewBusy(true)
    try {
      const result = await previewPrevisit({
        route_id: routeId,
        customer_id: effectiveCustomerId,
        order_type_ref: orderTypeRef,
        payment_usance_ref: paymentRef,
        warehouse_ref: warehouseRef,
        lines: cartLines.map(({ product, quantity }) => ({ product_id: product.id, quantity })),
      })
      setPreview(result)
      if (!result.ok) {
        throw new Error(result.credit_control?.message || result.message || 'NGT این سفارش را تأیید نکرد.')
      }
      return result
    } finally {
      setPreviewBusy(false)
    }
  }

  async function handlePreview() {
    try {
      await calculatePreview()
      flash('محاسبه رسمی قیمت و تخفیف از NGT انجام شد.')
    } catch (caught) {
      flash(caught instanceof Error ? caught.message : 'پیش‌نمایش رسمی سفارش انجام نشد.')
    }
  }

  async function saveRealRequest(finishVisit: boolean) {
    if (!effectiveVisitId) {
      flash('برای ثبت درخواست واقعی، ابتدا ویزیت مشتری را از صفحه مسیر شروع کنید.')
      return
    }
    if (!context || !effectiveCustomerId) return
    setSaveBusy(true)
    try {
      const official = preview?.ok ? preview : await calculatePreview()
      if (!official.ok || official.credit_control?.allowed === false) {
        throw new Error(official.credit_control?.message || official.message || 'NGT ثبت این درخواست را مجاز نمی‌داند.')
      }
      const officialByProduct = new Map(official.items.map((item) => [String(item.product_id), item]))
      const orderType = official.order_type ?? context.order_types.find((item) => item.id === orderTypeRef)
      const payment = official.payment_type ?? context.payment_types.find((item) => item.id === paymentRef)
      const warehouse = official.warehouse ?? context.warehouses.find((item) => item.ref === warehouseRef)
      const saved = await createSavedPrevisitRequest(effectiveVisitId, {
        lines: cartLines.map(({ product, quantity }) => {
          const line = officialByProduct.get(product.id)
          return {
            product_id: product.id,
            quantity: Number(line?.quantity ?? quantity),
            unit_price: Number(line?.unit_price ?? 0),
            discount_amount: Number(line?.discount_amount ?? 0),
            title: product.name,
          }
        }),
        payment_type: payment?.name ?? '',
        order_type: orderType?.name ?? '',
        warehouse_ref: warehouse?.ref ?? warehouseRef,
        warehouse_name: warehouse?.name ?? '',
        preview: official as unknown as Record<string, unknown>,
      })
      setSavedRequest(saved)
      setCart({})
      setPreview(null)
      if (finishVisit) {
        await completeServerVisit(effectiveVisitId, { outcome: 'order' })
        completeVisit(effectiveCustomerId, 'order-draft')
        onNavigate(returnTo || `/visitor/route?customer=${encodeURIComponent(effectiveCustomerId)}`)
        return
      }
      flash(`درخواست واقعی شماره ${saved.request_number.toLocaleString('fa-IR')} ثبت شد.`)
    } catch (caught) {
      flash(caught instanceof Error ? caught.message : 'ثبت درخواست واقعی انجام نشد.')
    } finally {
      setSaveBusy(false)
    }
  }

  function chooseCustomer(id: string) {
    if (visitLocked) {
      flash('مشتری این سفارش به ویزیت فعال متصل است و قابل تغییر نیست.')
      return
    }
    setSelectedCustomerId(id)
    setCart({})
    setBrand('')
    setGroupId('')
    setCatalogId('')
    setCustomerPicker(false)
  }

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vo-shell">
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

        <section className="vo-heading">
          <div>
            <span>NGT Order Workspace</span>
            <h1>سفارش واقعی مشتری</h1>
            <p>{routeId ? `${activeRouteTitle || context?.route.title || 'مسیر فعال'} · داده زنده NGT` : 'مسیر فعال برای سفارش موجود نیست.'}</p>
          </div>
          <div className="vo-heading-actions">
            <button type="button" className="vo-history" onClick={() => onNavigate('/visitor/orders/history')}><InvoiceIcon /><span>درخواست‌ها</span></button>
          </div>
        </section>

        <button type="button" className={visitLocked ? 'vo-customer locked' : 'vo-customer'} onClick={() => visitLocked ? flash('مشتری به ویزیت فعال قفل است.') : setCustomerPicker(true)}>
          <span className="vo-customer-icon"><StoreIcon /></span>
          <span className="vo-customer-copy">
            <small>مشتری سفارش</small>
            <strong>{selectedCustomer?.store_name || selectedCustomer?.name || 'مشتری انتخاب نشده'}</strong>
            <span>{selectedCustomer ? `${selectedCustomer.code} · ${selectedCustomer.address}` : 'از مشتریان واقعی مسیر انتخاب کنید.'}</span>
          </span>
          {visitLocked ? <span className="vo-customer-lock">ویزیت فعال</span> : <ChevronLeftIcon />}
        </button>

        {contextError ? (
          <section className="vh-live-state error" role="alert">
            <div><strong>اطلاعات سفارش NGT دریافت نشد</strong><span>{contextError}</span></div>
          </section>
        ) : contextLoading ? (
          <section className="vh-live-state" role="status"><strong>در حال دریافت کاتالوگ، موجودی و قرارداد فروش از NGT…</strong></section>
        ) : null}

        {context ? (
          <>
            <section className="vo-tabs" role="tablist" aria-label="بخش سفارش">
              <button type="button" role="tab" aria-selected={view === 'products'} className={view === 'products' ? 'active' : ''} onClick={() => setView('products')}>محصولات</button>
              <button type="button" role="tab" aria-selected={view === 'catalog'} className={view === 'catalog' ? 'active' : ''} onClick={() => setView('catalog')}>کاتالوگ NGT</button>
              <button type="button" role="tab" aria-selected={view === 'cart'} className={view === 'cart' ? 'active' : ''} onClick={() => setView('cart')}>سبد <b>{number(cartCount)}</b></button>
            </section>

            {view === 'products' ? (
              <section className="vo-products-view">
                <div className="vo-toolbar">
                  <label className="vo-search"><SearchIcon /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جست‌وجوی نام، کد، برند یا گروه…" /></label>
                  <select value={brand} onChange={(event) => setBrand(event.target.value)} aria-label="برند">
                    <option value="">همه برندها</option>
                    {context.catalog_filters.brands.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                  <select value={groupId} onChange={(event) => setGroupId(event.target.value)} aria-label="گروه کالا">
                    <option value="">همه گروه‌ها</option>
                    {context.catalog_filters.groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  <label className="vo-stock-toggle"><input type="checkbox" checked={inStockOnly} onChange={(event) => setInStockOnly(event.target.checked)} /> فقط موجود</label>
                </div>

                {selectedCatalog ? (
                  <div className="vo-filter-note">
                    <span>کاتالوگ: <strong>{selectedCatalog.name}</strong></span>
                    <button type="button" onClick={() => setCatalogId('')}>حذف فیلتر</button>
                  </div>
                ) : null}

                <div className="vo-product-grid">
                  {visibleProducts.map((product) => {
                    const qty = Number(cart[product.id] ?? 0)
                    const available = availableFor(product)
                    const price = indicativePriceFor(product)
                    return (
                      <article className="vo-product-card" key={product.id}>
                        <div className="vo-product-top">
                          <span className="vo-product-icon"><BoxIcon /></span>
                          <div><strong>{product.name}</strong><small>{product.code} · {product.brand || 'بدون برند'}</small></div>
                        </div>
                        <div className="vo-product-meta">
                          <span>{product.group || 'بدون گروه'}</span>
                          <span>{product.unit}</span>
                          {context.inventory.show_stock_level ? <span>موجودی: <b>{number(available)}</b></span> : <span>کنترل موجودی: NGT</span>}
                        </div>
                        <div className="vo-product-price">
                          <strong>{price > 0 ? number(price) : '—'}</strong>
                          <small>قیمت پایه NGT · مبلغ نهایی بعد از Preview</small>
                        </div>
                        <div className="vo-stepper">
                          <button type="button" onClick={() => setQuantity(product, qty - 1)} disabled={qty <= 0}>−</button>
                          <strong>{number(qty)}</strong>
                          <button type="button" onClick={() => setQuantity(product, qty + 1)} disabled={available <= qty}>+</button>
                        </div>
                      </article>
                    )
                  })}
                  {!visibleProducts.length ? <div className="vo-empty"><BoxIcon /><strong>محصولی با فیلتر فعلی وجود ندارد.</strong></div> : null}
                </div>
              </section>
            ) : null}

            {view === 'catalog' ? (
              <section className="vo-catalog-view">
                <div className="vo-catalog-grid">
                  {context.grouped_catalogs.map((catalog) => (
                    <button type="button" className="vo-catalog-card" key={catalog.id} onClick={() => { setCatalogId(catalog.id); setView('products') }}>
                      {catalog.image_url ? <img src={catalog.image_url} alt="" loading="lazy" /> : <span className="vo-catalog-icon"><BoxIcon /></span>}
                      <span><strong>{catalog.name}</strong><small>{number(catalog.product_ids.length)} کالا · {catalog.brands.join('، ')}</small></span>
                      <ChevronLeftIcon />
                    </button>
                  ))}
                  {!context.grouped_catalogs.length ? <div className="vo-empty"><BoxIcon /><strong>کاتالوگ تصویری برای قرارداد فعلی ثبت نشده است.</strong></div> : null}
                </div>
              </section>
            ) : null}

            {view === 'cart' ? (
              <section className="vo-cart-view">
                <div className="vo-cart-head">
                  <div><strong>سبد سفارش</strong><span>{number(cartLines.length)} قلم · {number(cartCount)} واحد پایه</span></div>
                  <button type="button" onClick={() => void handlePreview()} disabled={!cartLines.length || previewBusy}><ClipboardIcon /> {previewBusy ? 'در حال محاسبه…' : 'محاسبه رسمی NGT'}</button>
                </div>

                {cartLines.length ? (
                  <div className="vo-cart-lines">
                    {cartLines.map(({ product, quantity }) => {
                      const official = preview?.items.find((item) => String(item.product_id) === product.id)
                      return (
                        <article key={product.id} className="vo-cart-line">
                          <span className="vo-cart-icon"><BoxIcon /></span>
                          <div className="vo-cart-copy">
                            <strong>{product.name}</strong>
                            <span>{product.brand} · {product.unit}</span>
                            <small>{official ? `${number(official.unit_price)} × ${number(official.quantity)}` : `${number(indicativePriceFor(product))} × ${number(quantity)} · تقریبی`}</small>
                          </div>
                          <button type="button" className="vo-trash" onClick={() => setQuantity(product, 0)} aria-label={`حذف ${product.name}`}><TrashIcon /></button>
                          <div className="vo-cart-stepper">
                            <button type="button" onClick={() => setQuantity(product, quantity - 1)}>−</button>
                            <strong>{number(quantity)}</strong>
                            <button type="button" onClick={() => setQuantity(product, quantity + 1)}>+</button>
                          </div>
                          <strong className="vo-line-total">{official ? number(official.net_amount) : number(indicativePriceFor(product) * quantity)}</strong>
                        </article>
                      )
                    })}
                  </div>
                ) : (
                  <div className="vo-empty"><CartIcon /><strong>سبد سفارش خالی است.</strong><button type="button" onClick={() => setView('products')}>انتخاب محصول</button></div>
                )}

                <section className="vo-order-options">
                  <label><span>نوع سفارش NGT</span><select value={orderTypeRef ?? ''} onChange={(event) => setOrderTypeRef(Number(event.target.value) || null)}>{context.order_types.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                  <label><span>شرایط پرداخت NGT</span><select value={paymentRef} onChange={(event) => setPaymentRef(event.target.value)}>{context.payment_types.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                  {context.warehouses.length ? <label><span>انبار</span><select value={warehouseRef ?? ''} disabled={!context.warehouse_selection.enabled} onChange={(event) => setWarehouseRef(Number(event.target.value) || null)}>{context.warehouses.map((item) => <option key={item.ref} value={item.ref}>{item.name}</option>)}</select></label> : null}
                </section>

                <section className="vo-totals">
                  {preview ? (
                    <>
                      <div><span>جمع ناخالص رسمی</span><strong>{number(preview.totals.gross)}</strong></div>
                      <div className="discount"><span>تخفیف رسمی</span><strong>− {number(preview.totals.discount)}</strong></div>
                      <div><span>مالیات رسمی</span><strong>{number(preview.totals.tax)}</strong></div>
                      <div><span>عوارض رسمی</span><strong>{number(preview.totals.charge)}</strong></div>
                      <div className="total"><span>خالص قابل پرداخت</span><strong>{number(preview.totals.net)}</strong></div>
                    </>
                  ) : (
                    <>
                      <div><span>برآورد پایه قرارداد</span><strong>{number(indicativeSubtotal)}</strong></div>
                      <div className="total"><span>مبلغ نهایی</span><strong>پس از Preview رسمی NGT</strong></div>
                    </>
                  )}
                </section>

                {preview?.credit_control ? (
                  <section className={preview.credit_control.allowed === false ? 'vh-live-state error' : 'vh-live-state'}>
                    <div><strong>کنترل اعتبار NGT</strong><span>{preview.credit_control.message || (preview.credit_control.allowed ? 'مجاز' : 'نیازمند بررسی')}</span></div>
                  </section>
                ) : null}

                {preview?.gift_lines?.length ? (
                  <section className="vo-promo">
                    <div><strong>هدایای رسمی NGT</strong><span>{number(preview.gift_lines.length)} مورد</span></div>
                  </section>
                ) : null}

                {!effectiveVisitId ? (
                  <section className="vh-live-state">
                    <div><strong>ثبت واقعی نیازمند ویزیت فعال است</strong><span>برای ثبت Saved Request، ابتدا ویزیت همین مشتری را از صفحه مسیر شروع کنید.</span></div>
                    <button type="button" onClick={() => effectiveCustomerId && onNavigate(`/visitor/route?customer=${encodeURIComponent(effectiveCustomerId)}`)}>رفتن به مسیر</button>
                  </section>
                ) : null}

                <div className="vo-submit-row">
                  <button type="button" className="draft" onClick={() => void handlePreview()} disabled={!cartLines.length || previewBusy}>Preview رسمی</button>
                  <button type="button" className="submit" onClick={() => void saveRealRequest(false)} disabled={!effectiveVisitId || !cartLines.length || saveBusy}><CheckCircleIcon /> {saveBusy ? 'در حال ثبت…' : 'ثبت درخواست واقعی'}</button>
                </div>
                {effectiveVisitId ? (
                  <button type="button" className="vo-complete-visit" onClick={() => void saveRealRequest(true)} disabled={!cartLines.length || saveBusy}>ثبت درخواست و پایان ویزیت</button>
                ) : null}

                {savedRequest ? (
                  <section className="vh-live-state">
                    <div><strong>درخواست ثبت شد</strong><span>شماره {savedRequest.request_number.toLocaleString('fa-IR')} · مبلغ {number(savedRequest.total_amount)}</span></div>
                    <button type="button" onClick={() => onNavigate('/visitor/orders/history')}>مشاهده درخواست‌ها</button>
                  </section>
                ) : null}
              </section>
            ) : null}
          </>
        ) : null}

        {customerPicker ? (
          <div className="vo-sheet-backdrop" onClick={() => setCustomerPicker(false)}>
            <section className="vo-sheet" role="dialog" aria-modal="true" aria-label="انتخاب مشتری" onClick={(event) => event.stopPropagation()}>
              <div className="vo-sheet-handle" />
              <h2>مشتری واقعی مسیر</h2>
              <div className="vo-customer-list">
                {customers.map((customer) => (
                  <button type="button" key={String(customer.id)} className={String(customer.id) === effectiveCustomerId ? 'active' : ''} onClick={() => chooseCustomer(String(customer.id))}>
                    <StoreIcon /><span><strong>{customer.store_name || customer.name}</strong><small>{customer.code} · {customer.address}</small></span>{String(customer.id) === effectiveCustomerId ? <CheckCircleIcon /> : <ChevronLeftIcon />}
                  </button>
                ))}
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
