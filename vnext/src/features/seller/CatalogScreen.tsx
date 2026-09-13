import { useEffect, useMemo, useState } from 'react'
import { Minus, Package, Plus, ShoppingCart } from 'lucide-react'
import { navigateWithParams } from '../../app/router'
import { AsyncState } from '../../components/AsyncState'
import {
  Alert,
  Button,
  Card,
  Cluster,
  KeyValue,
  PageHeader,
  ResponsivePageContainer,
  SearchInput,
  Select,
  Stack,
  StatusBadge,
} from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import {
  isReviewMode,
  routeQueryValue,
  type PrevisitContextResponse,
  type PrevisitProduct,
  type PrevisitVisitDraftResponse,
} from './contracts'

const reviewContext: PrevisitContextResponse = {
  seller: { personnel_id: 1, full_name: 'فروشنده نمونه' },
  route: { id: 'R-01', title: 'مسیر مرکزی' },
  customer: { id: 1, store_name: 'فروشگاه بهار', name: 'علی رضایی' },
  order_types: [{ id: 2, name: 'پیش‌فروش' }],
  payment_types: [{ id: '401', name: 'نقدی', buy_type_ref: 3, is_cash: true, check_credit: true, check_debit: true }],
  warehouses: [{ id: 'review-stock', ref: 1, name: 'انبار مرکزی', dc_ref: 1 }],
  warehouse_selection: { enabled: false, default_ref: 1, source: 'review' },
  products: [
    {
      id: '4032',
      unique_id: 'review-product',
      code: 'P-4032',
      name: 'محصول نمونه',
      brand: 'Negin',
      group_id: '7',
      group: 'گروه نمونه',
      stock_name: 'انبار مرکزی',
      stock_ref: '1',
      unit: 'عدد',
      available_qty: 24,
      indicative_price: 1_930_000,
      indicative_prices: { '2': 1_930_000 },
      warehouse_inventory: { '1': { on_hand_qty: 24, reserved_qty: 0, available_qty: 24 } },
    },
  ],
  grouped_catalogs: [],
  grouped_catalog_count: 0,
  catalog_count: 1,
  catalog_filters: { brands: ['Negin'], groups: [{ id: '7', name: 'گروه نمونه' }] },
  inventory: { show_stock_level: true, online_refresh: false, applies_current_orders: false, source: 'review' },
  preview: { available: true, authoritative: true, creates_order: false },
  pricing: {
    catalog_kind: 'indicative_base_contract',
    catalog_order_type_ref: 2,
    catalog_cache_seconds: 300,
    official_preview_depends_on: ['customer', 'order_type', 'payment_type', 'warehouse', 'quantity'],
    official_source: 'NGT EVC presale',
  },
  credit_control: {
    checked_on_registration: true,
    advanced_control: true,
    allow_cash_without_advanced_control: false,
    source: 'review',
  },
}

const reviewDraft: PrevisitVisitDraftResponse = {
  visit_id: 'review-visit',
  route_id: 'R-01',
  customer_id: '1',
  visit_status: 'active',
  started_at: '2026-09-13T10:00:00+00:00',
  idempotency_key: 'review',
  warehouse_ref: null,
  warehouse_name: '',
  lines: [],
  line_count: 0,
  total_amount: 0,
  payment_type: '',
  order_type: '',
  outcome: 'draft',
  outcome_reason: '',
  outcome_reason_id: null,
  visit_status_id: null,
  start_distance_meters: null,
  ngt_send_enabled: false,
  ngt_status: 'not_sent',
}

function formatNumber(value: number | null | undefined) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(Number(value ?? 0))
}

function selectedPrice(product: PrevisitProduct, orderTypeRef: string) {
  const matrixPrice = product.indicative_prices?.[orderTypeRef]
  return Number(matrixPrice ?? product.indicative_price ?? 0)
}

function availableQuantity(product: PrevisitProduct, warehouseRef: string) {
  if (!warehouseRef) return Number(product.available_qty ?? 0)
  const warehouse = product.warehouse_inventory?.[warehouseRef]
  if (warehouse) return Number(warehouse.available_qty ?? 0)
  if (String(product.stock_ref ?? '') === warehouseRef) return Number(product.available_qty ?? 0)
  return 0
}

export function CatalogScreen() {
  const review = isReviewMode()
  const pathId = routeQueryValue('pathId')
  const customerId = routeQueryValue('customerId')
  const visitId = routeQueryValue('visitId')
  const [search, setSearch] = useState('')
  const [brand, setBrand] = useState('')
  const [group, setGroup] = useState('')
  const [orderTypeRef, setOrderTypeRef] = useState('')
  const [paymentId, setPaymentId] = useState('')
  const [warehouseRef, setWarehouseRef] = useState('')
  const [cart, setCart] = useState<Record<string, number>>({})
  const [hydrated, setHydrated] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  const contextQuery = useApiQuery<PrevisitContextResponse>(
    `seller:previsit-context:${pathId || (review ? 'review' : 'missing')}:${customerId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewContext)
      : pathId && customerId
        ? apiRequest<PrevisitContextResponse>(
            `/seller-workspace/previsit/context?path_id=${encodeURIComponent(pathId)}&customer_id=${encodeURIComponent(customerId)}&limit=1000`,
            { signal },
          )
        : Promise.reject(new Error('شناسه مسیر یا مشتری در URL موجود نیست')),
    300_000,
  )

  const draftQuery = useApiQuery<PrevisitVisitDraftResponse>(
    `seller:previsit-draft:${visitId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewDraft)
      : visitId
        ? apiRequest<PrevisitVisitDraftResponse>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}`, { signal })
        : Promise.reject(new Error('شناسه ویزیت در URL موجود نیست')),
  )

  const context = contextQuery.data
  const draft = draftQuery.data

  useEffect(() => {
    if (!context || !draft || hydrated) return
    let cancelled = false
    queueMicrotask(() => {
      if (cancelled) return
      const order = context.order_types.find((item) => item.name === draft.order_type) ?? context.order_types[0]
      const payment = context.payment_types.find((item) => item.name === draft.payment_type) ?? context.payment_types[0]
      const warehouse = context.warehouses.find((item) => Number(item.ref) === Number(draft.warehouse_ref))
        ?? context.warehouses.find((item) => Number(item.ref) === Number(context.warehouse_selection.default_ref))
        ?? context.warehouses[0]
      setOrderTypeRef(order ? String(order.id) : '')
      setPaymentId(payment ? String(payment.id) : '')
      setWarehouseRef(warehouse ? String(warehouse.ref) : '')
      setCart(Object.fromEntries(
        draft.lines
          .filter((line) => Number(line.quantity) > 0)
          .map((line) => [String(line.product_id), Number(line.quantity)]),
      ))
      setHydrated(true)
    })
    return () => { cancelled = true }
  }, [context, draft, hydrated])

  const visibleProducts = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase('fa-IR')
    return (context?.products ?? []).filter((product) => {
      const matchesSearch = !needle || [product.name, product.code, product.brand, product.barcode]
        .some((value) => String(value ?? '').toLocaleLowerCase('fa-IR').includes(needle))
      const matchesBrand = !brand || product.brand === brand
      const matchesGroup = !group || String(product.group_id) === group
      return matchesSearch && matchesBrand && matchesGroup
    })
  }, [context?.products, search, brand, group])

  const cartLines = useMemo(() => {
    if (!context) return []
    return Object.entries(cart).flatMap(([productId, quantity]) => {
      if (quantity <= 0) return []
      const product = context.products.find((item) => String(item.id) === productId)
      return product ? [{ product, quantity }] : []
    })
  }, [cart, context])

  const cartTotal = cartLines.reduce(
    (sum, line) => sum + line.quantity * selectedPrice(line.product, orderTypeRef),
    0,
  )

  function changeQuantity(product: PrevisitProduct, delta: number) {
    const id = String(product.id)
    const current = Number(cart[id] ?? 0)
    const available = availableQuantity(product, warehouseRef)
    const next = Math.max(0, current + delta)
    if (delta > 0 && available >= 0 && next > available) return
    setCart((previous) => {
      const updated = { ...previous }
      if (next <= 0) delete updated[id]
      else updated[id] = next
      return updated
    })
  }

  async function saveDraftAndOpenCart() {
    if (!context || !draft || !visitId || saving) return
    const order = context.order_types.find((item) => String(item.id) === orderTypeRef)
    const payment = context.payment_types.find((item) => String(item.id) === paymentId)
    const warehouse = context.warehouses.find((item) => String(item.ref) === warehouseRef)
    if (!order || !payment || !warehouse) {
      setSaveError('نوع سفارش، روش پرداخت و انبار باید از گزینه‌های مجاز Backend انتخاب شوند.')
      return
    }
    if (!cartLines.length) {
      setSaveError('حداقل یک کالا به سبد اضافه کنید.')
      return
    }

    setSaving(true)
    setSaveError('')
    try {
      await apiRequest<PrevisitVisitDraftResponse>(
        `/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/draft`,
        {
          method: 'PUT',
          body: {
            lines: cartLines.map(({ product, quantity }) => ({
              product_id: String(product.id),
              quantity,
              unit_price: selectedPrice(product, orderTypeRef),
              discount_amount: 0,
              title: product.name,
            })),
            payment_type: payment.name,
            order_type: order.name,
            warehouse_ref: Number(warehouse.ref),
            warehouse_name: warehouse.name,
          },
        },
      )
      navigateWithParams('/seller/cart', { pathId, customerId, visitId })
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : 'ذخیره پیش‌نویس انجام نشد.')
    } finally {
      setSaving(false)
    }
  }

  const selectorsReady = Boolean(context?.order_types.length && context?.payment_types.length && context?.warehouses.length)

  return (
    <div className="ng-v2" dir="rtl" data-trace-id="ORD-01">
      <ResponsivePageContainer>
        <Stack gap={5}>
          <PageHeader
            eyebrow="ORDER / CATALOG"
            title="انتخاب کالا"
            description={context ? `${context.customer.store_name || context.customer.name || context.customer.id} • ${context.catalog_count.toLocaleString('fa-IR')} کالا` : 'کاتالوگ مجاز فروشنده'}
          />

          {contextQuery.status === 'loading' && !context ? <AsyncState mode="loading" title="در حال دریافت کاتالوگ و موجودی" /> : null}
          {contextQuery.status === 'error' ? <AsyncState mode="error" title="دریافت کاتالوگ ناموفق بود" message={contextQuery.error?.message} onRetry={contextQuery.reload} /> : null}
          {draftQuery.status === 'loading' && !draft ? <AsyncState mode="loading" title="در حال بازیابی پیش‌نویس ویزیت" /> : null}
          {draftQuery.status === 'error' ? <AsyncState mode="error" title="بازیابی پیش‌نویس ناموفق بود" message={draftQuery.error?.message} onRetry={draftQuery.reload} /> : null}

          {context && draft ? (
            <>
              <Alert title="قیمت‌های این صفحه پایه و راهنما هستند" tone="info">
                قیمت رسمی، تخفیف، مالیات، جایزه و کنترل اعتبار فقط در مرحله پیش‌نمایش رسمی NGT EVC محاسبه می‌شوند.
              </Alert>

              <Card>
                <Stack gap={4}>
                  <Select
                    label="نوع سفارش"
                    value={orderTypeRef}
                    onChange={(event) => setOrderTypeRef(event.target.value)}
                    options={context.order_types.map((item) => ({ value: String(item.id), label: item.name }))}
                  />
                  <Select
                    label="روش پرداخت"
                    value={paymentId}
                    onChange={(event) => setPaymentId(event.target.value)}
                    options={context.payment_types.map((item) => ({ value: String(item.id), label: item.name }))}
                  />
                  <Select
                    label="انبار"
                    value={warehouseRef}
                    disabled={!context.warehouse_selection.enabled}
                    onChange={(event) => setWarehouseRef(event.target.value)}
                    options={context.warehouses.map((item) => ({ value: String(item.ref), label: item.name || `انبار ${item.ref}` }))}
                  />
                </Stack>
              </Card>

              {!selectorsReady ? (
                <Alert title="شرایط سفارش کامل نیست" tone="danger">
                  Backend برای این فروشنده نوع سفارش، روش پرداخت یا انبار مجاز برنگردانده است.
                </Alert>
              ) : null}

              <Card>
                <Stack gap={4}>
                  <SearchInput
                    label="جستجوی کالا"
                    placeholder="نام، کد، بارکد یا برند"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                  <Cluster>
                    <Select
                      label="برند"
                      value={brand}
                      onChange={(event) => setBrand(event.target.value)}
                      options={[{ value: '', label: 'همه برندها' }, ...context.catalog_filters.brands.map((item) => ({ value: item, label: item }))]}
                    />
                    <Select
                      label="گروه"
                      value={group}
                      onChange={(event) => setGroup(event.target.value)}
                      options={[{ value: '', label: 'همه گروه‌ها' }, ...context.catalog_filters.groups.map((item) => ({ value: String(item.id), label: item.name }))]}
                    />
                  </Cluster>
                </Stack>
              </Card>

              {visibleProducts.length === 0 ? <AsyncState mode="empty" title="کالایی با این فیلترها پیدا نشد" /> : null}

              <Stack gap={3}>
                {visibleProducts.map((product) => {
                  const quantity = Number(cart[String(product.id)] ?? 0)
                  const available = availableQuantity(product, warehouseRef)
                  const price = selectedPrice(product, orderTypeRef)
                  return (
                    <Card key={String(product.id)} interactive>
                      <Cluster>
                        <span className="ng-product-thumb"><Package/></span>
                        <div style={{ flex: 1 }}>
                          <strong>{product.name}</strong>
                          <small>{[product.code && `#${product.code}`, product.brand, product.group].filter(Boolean).join(' • ')}</small>
                        </div>
                        <StatusBadge
                          label={available > 0 ? `موجودی ${formatNumber(available)} ${product.unit || ''}` : 'ناموجود'}
                          tone={available > 0 ? 'success' : 'danger'}
                        />
                      </Cluster>
                      <KeyValue items={[
                        { key: 'قیمت پایه انتخاب‌شده', value: price > 0 ? `${formatNumber(price)} ریال` : 'نیازمند پیش‌نمایش رسمی' },
                        { key: 'انبار', value: context.warehouses.find((item) => String(item.ref) === warehouseRef)?.name || product.stock_name || '—' },
                        { key: 'واحد', value: product.unit || '—' },
                      ]}/>
                      <Cluster>
                        <Button variant="secondary" size="sm" disabled={quantity <= 0} onClick={() => changeQuantity(product, -1)} startIcon={<Minus/>}>کاهش</Button>
                        <strong>{quantity.toLocaleString('fa-IR')}</strong>
                        <Button variant="secondary" size="sm" disabled={available <= quantity} onClick={() => changeQuantity(product, 1)} startIcon={<Plus/>}>افزودن</Button>
                      </Cluster>
                    </Card>
                  )
                })}
              </Stack>

              {saveError ? <Alert title="ذخیره سبد ناموفق بود" tone="danger">{saveError}</Alert> : null}

              <Card>
                <KeyValue items={[
                  { key: 'ردیف‌های سبد', value: cartLines.length.toLocaleString('fa-IR') },
                  { key: 'تعداد کل', value: formatNumber(cartLines.reduce((sum, line) => sum + line.quantity, 0)) },
                  { key: 'جمع پایه تخمینی', value: `${formatNumber(cartTotal)} ریال` },
                  { key: 'وضعیت قیمت', value: <StatusBadge label="غیرنهایی؛ منتظر NGT Preview" tone="warning"/> },
                ]}/>
                <Button
                  size="lg"
                  loading={saving}
                  disabled={!selectorsReady || !cartLines.length}
                  startIcon={<ShoppingCart/>}
                  onClick={saveDraftAndOpenCart}
                >
                  ذخیره پیش‌نویس و مشاهده سبد
                </Button>
              </Card>
            </>
          ) : null}
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
