import { useMemo, useState } from 'react'
import { CheckCircle2, FileText, Pencil, Printer, RefreshCw, Save, ShoppingCart } from 'lucide-react'
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
  SectionHeader,
  Stack,
  StatusBadge,
} from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import {
  isReviewMode,
  routeQueryValue,
  type PrevisitContextResponse,
  type PrevisitPreviewResponse,
  type PrevisitSavedRequest,
  type PrevisitSavedRequestsResponse,
  type PrevisitVisitDraftResponse,
  type SellerVisitPolicyResponse,
} from './contracts'

const money = (value: number | null | undefined) =>
  `${new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 }).format(Number(value ?? 0))} ریال`

const reviewDraft: PrevisitVisitDraftResponse = {
  visit_id: 'review-visit',
  route_id: 'R-01',
  customer_id: '1',
  visit_status: 'active',
  started_at: '2026-09-13T10:00:00+00:00',
  idempotency_key: 'review',
  warehouse_ref: 1,
  warehouse_name: 'انبار مرکزی',
  lines: [{ product_id: '4032', quantity: 2, unit_price: 1_930_000, discount_amount: 0, title: 'کالای نمونه' }],
  line_count: 1,
  total_amount: 3_860_000,
  payment_type: 'نقدی',
  order_type: 'ویزیت فروش',
  outcome: 'draft',
  outcome_reason: '',
  outcome_reason_id: null,
  visit_status_id: null,
  start_distance_meters: null,
  ngt_send_enabled: false,
  ngt_status: 'not_sent',
}

const reviewContext: PrevisitContextResponse = {
  seller: { personnel_id: 1, full_name: 'فروشنده نمونه' },
  route: { id: 'R-01', title: 'مسیر مرکزی' },
  customer: { id: 1, store_name: 'فروشگاه نمونه' },
  order_types: [{ id: 2, name: 'ویزیت فروش' }],
  payment_types: [{ id: '401', name: 'نقدی', buy_type_ref: 3 }],
  warehouses: [{ id: 'review-stock', ref: 1, name: 'انبار مرکزی', dc_ref: 1 }],
  warehouse_selection: { enabled: false, default_ref: 1, source: 'review' },
  products: [{ id: '4032', name: 'کالای نمونه', unit: 'عدد', available_qty: 24 }],
  grouped_catalogs: [],
  grouped_catalog_count: 0,
  catalog_count: 1,
  catalog_filters: { brands: [], groups: [] },
  inventory: { show_stock_level: true, online_refresh: false, applies_current_orders: false, source: 'review' },
  preview: { available: true, authoritative: true, creates_order: false },
  pricing: { catalog_kind: 'review', catalog_order_type_ref: 2, catalog_cache_seconds: 300, official_preview_depends_on: [], official_source: 'NGT EVC presale' },
  credit_control: { checked_on_registration: true, advanced_control: true, allow_cash_without_advanced_control: false, source: 'review' },
}

function lineTitle(context: PrevisitContextResponse | null, productId: string, fallback: string) {
  return context?.products.find((item) => String(item.id) === String(productId))?.name || fallback || productId
}

function previewBody(draft: PrevisitVisitDraftResponse, context: PrevisitContextResponse) {
  const order = context.order_types.find((item) => item.name === draft.order_type)
  const payment = context.payment_types.find((item) => item.name === draft.payment_type)
  if (!order) throw new Error('نوع سفارش فعلی در قرارداد NGT پیدا نشد.')
  if (!payment) throw new Error('روش پرداخت فعلی در قرارداد NGT پیدا نشد.')
  if (!draft.lines.length) throw new Error('سبد فعلی خالی است.')
  return {
    route_id: draft.route_id,
    customer_id: draft.customer_id,
    order_type_ref: Number(order.id),
    payment_usance_ref: String(payment.id),
    warehouse_ref: draft.warehouse_ref,
    lines: draft.lines.map((line) => ({ product_id: String(line.product_id), quantity: Number(line.quantity) })),
  }
}

function htmlEscape(value: unknown) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function printSavedRequest(saved: PrevisitSavedRequest, context: PrevisitContextResponse | null) {
  const preview = saved.preview as Partial<PrevisitPreviewResponse>
  const official = new Map((preview.items ?? []).map((item) => [String(item.product_id), item]))
  const rows = saved.lines.map((line) => {
    const item = official.get(String(line.product_id))
    return {
      title: lineTitle(context, String(line.product_id), line.title),
      quantity: Number(item?.quantity ?? line.quantity),
      unitPrice: Number(item?.unit_price ?? line.unit_price),
      discount: Number(item?.discount_amount ?? line.discount_amount),
      tax: Number(item?.tax_and_charge_amount ?? 0),
      net: Number(item?.net_amount ?? 0),
    }
  })
  const totals = preview.totals
  const title = `درخواست ${saved.request_number.toLocaleString('fa-IR')}`
  const html = `<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>${htmlEscape(title)}</title><style>body{font-family:Tahoma,Arial,sans-serif;margin:24px;color:#172622}table{width:100%;border-collapse:collapse;margin-top:16px}th,td{border:1px solid #ccd7d3;padding:8px;text-align:center}th{background:#eef5f2}.total{margin-top:14px;font-weight:700}</style></head><body><h1>${htmlEscape(title)}</h1><p>${htmlEscape(saved.order_type)} · ${htmlEscape(saved.payment_type)} · ${htmlEscape(saved.warehouse_name)}</p><table><thead><tr><th>کالا</th><th>تعداد</th><th>قیمت واحد</th><th>تخفیف</th><th>مالیات/عوارض</th><th>خالص</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${htmlEscape(row.title)}</td><td>${row.quantity.toLocaleString('fa-IR')}</td><td>${money(row.unitPrice)}</td><td>${money(row.discount)}</td><td>${money(row.tax)}</td><td>${money(row.net)}</td></tr>`).join('')}</tbody></table><div class="total">مبلغ نهایی: ${money(totals?.net ?? saved.total_amount)}</div></body></html>`
  const nativeWindow = window as typeof window & { NeginAndroid?: { printHtml?: (title: string, html: string) => boolean } }
  if (typeof nativeWindow.NeginAndroid?.printHtml === 'function') {
    try {
      if (nativeWindow.NeginAndroid.printHtml(title, html)) return
    } catch {
      // Browser print is the fallback.
    }
  }
  const printWindow = window.open('', '_blank', 'noopener,noreferrer')
  if (!printWindow) throw new Error('مرورگر اجازه باز کردن پنجره چاپ را نداد.')
  printWindow.opener = null
  printWindow.document.write(html)
  printWindow.document.close()
  printWindow.focus()
  printWindow.print()
}

function currentPosition() {
  return new Promise<{ latitude: number; longitude: number; accuracy: number }>((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('GPS در این دستگاه در دسترس نیست.'))
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      }),
      () => reject(new Error('موقعیت فعلی برای پایان ویزیت دریافت نشد.')),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 12_000 },
    )
  })
}

export function CartScreen() {
  const review = isReviewMode()
  const pathId = routeQueryValue('pathId')
  const customerId = routeQueryValue('customerId')
  const visitId = routeQueryValue('visitId')
  const [editingRequestId, setEditingRequestId] = useState(routeQueryValue('requestId'))
  const [preview, setPreview] = useState<PrevisitPreviewResponse | null>(null)
  const [busy, setBusy] = useState<'preview' | 'save' | 'edit' | 'complete' | ''>('')
  const [actionError, setActionError] = useState('')
  const [actionMessage, setActionMessage] = useState('')

  const draftQuery = useApiQuery<PrevisitVisitDraftResponse>(
    `seller:cart-draft:${visitId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewDraft)
      : visitId
        ? apiRequest<PrevisitVisitDraftResponse>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}`, { signal })
        : Promise.reject(new Error('شناسه ویزیت در URL موجود نیست')),
  )
  const draft = draftQuery.data
  const resolvedPathId = draft?.route_id || pathId
  const resolvedCustomerId = draft?.customer_id || customerId

  const contextQuery = useApiQuery<PrevisitContextResponse>(
    `seller:cart-context:${resolvedPathId || 'missing'}:${resolvedCustomerId || 'missing'}`,
    (signal) => review
      ? Promise.resolve(reviewContext)
      : resolvedPathId && resolvedCustomerId
        ? apiRequest<PrevisitContextResponse>(
            `/seller-workspace/previsit/context?path_id=${encodeURIComponent(resolvedPathId)}&customer_id=${encodeURIComponent(resolvedCustomerId)}&limit=1000`,
            { signal },
          )
        : Promise.reject(new Error('شناسه مسیر یا مشتری برای محاسبه رسمی موجود نیست')),
    300_000,
  )
  const context = contextQuery.data

  const savedQuery = useApiQuery<PrevisitSavedRequestsResponse>(
    `seller:saved-requests:${visitId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve({ requests: [] })
      : visitId
        ? apiRequest<PrevisitSavedRequestsResponse>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/saved-requests`, { signal })
        : Promise.reject(new Error('شناسه ویزیت برای درخواست‌های ذخیره‌شده موجود نیست')),
  )
  const savedRequests = savedQuery.data?.requests ?? []

  const policyQuery = useApiQuery<SellerVisitPolicyResponse>(
    `seller:cart-policy:${resolvedPathId || 'missing'}:${resolvedCustomerId || 'missing'}`,
    (signal) => review
      ? Promise.resolve({
          route: { id: 'R-01', title: 'مسیر مرکزی' },
          customer: { id: 1, store_name: 'فروشگاه نمونه' },
          controls: { enabled: true, enforced: false },
          source: 'review',
        } as SellerVisitPolicyResponse)
      : resolvedPathId && resolvedCustomerId
        ? apiRequest<SellerVisitPolicyResponse>(
            `/seller-workspace/previsit/policy?path_id=${encodeURIComponent(resolvedPathId)}&customer_id=${encodeURIComponent(resolvedCustomerId)}`,
            { signal },
          )
        : Promise.reject(new Error('سیاست پایان ویزیت قابل دریافت نیست')),
  )

  const previewItems = useMemo(
    () => new Map((preview?.items ?? []).map((item) => [String(item.product_id), item])),
    [preview],
  )

  async function runPreview() {
    if (!draft || !context || busy) return
    setBusy('preview')
    setActionError('')
    setActionMessage('')
    try {
      const result = await apiRequest<PrevisitPreviewResponse>('/seller-workspace/previsit/preview', {
        method: 'POST',
        body: previewBody(draft, context),
      })
      setPreview(result)
      if (!result.ok) throw new Error(result.message || 'محاسبه رسمی NGT این سبد را رد کرد.')
      if (result.credit_control?.allowed === false) throw new Error(result.credit_control.message || 'کنترل اعتبار NGT این سبد را رد کرد.')
      setActionMessage('محاسبه رسمی NGT EVC با موفقیت انجام شد.')
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'محاسبه رسمی ناموفق بود.')
    } finally {
      setBusy('')
    }
  }

  async function saveRequest() {
    if (!draft || !preview || !visitId || busy) return
    if (!preview.ok || preview.credit_control?.allowed === false) {
      setActionError('فقط Preview رسمی تأییدشده قابل ذخیره است.')
      return
    }
    setBusy('save')
    setActionError('')
    setActionMessage('')
    try {
      const endpoint = `/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/saved-requests${editingRequestId ? `/${encodeURIComponent(editingRequestId)}` : ''}`
      const saved = await apiRequest<PrevisitSavedRequest>(endpoint, {
        method: editingRequestId ? 'PUT' : 'POST',
        body: {
          lines: draft.lines,
          payment_type: draft.payment_type,
          order_type: draft.order_type,
          warehouse_ref: draft.warehouse_ref,
          warehouse_name: draft.warehouse_name,
          preview,
        },
      })
      setPreview(null)
      setEditingRequestId('')
      draftQuery.reload()
      savedQuery.reload()
      setActionMessage(`درخواست ${saved.request_number.toLocaleString('fa-IR')} با محاسبه رسمی سرور ذخیره شد.`)
      navigateWithParams('/seller/cart', { pathId: resolvedPathId, customerId: resolvedCustomerId, visitId }, true)
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'ذخیره درخواست ناموفق بود.')
    } finally {
      setBusy('')
    }
  }

  async function editSaved(saved: PrevisitSavedRequest) {
    if (!visitId || busy) return
    setBusy('edit')
    setActionError('')
    setActionMessage('')
    try {
      await apiRequest<PrevisitVisitDraftResponse>(
        `/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/draft`,
        {
          method: 'PUT',
          body: {
            lines: saved.lines,
            payment_type: saved.payment_type,
            order_type: saved.order_type,
            warehouse_ref: saved.warehouse_ref,
            warehouse_name: saved.warehouse_name,
          },
        },
      )
      navigateWithParams('/seller/catalog', {
        pathId: saved.route_id || resolvedPathId,
        customerId: saved.customer_id || resolvedCustomerId,
        visitId,
        requestId: saved.id,
      })
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'باز کردن درخواست برای ویرایش ناموفق بود.')
      setBusy('')
    }
  }

  async function completeOrderVisit() {
    if (!draft || !visitId || busy) return
    if (draft.lines.length) return setActionError('قبل از پایان ویزیت، سبد فعلی را به درخواست ذخیره‌شده تبدیل کنید.')
    if (!savedRequests.length) return setActionError('برای پایان ویزیت سفارشی حداقل یک درخواست رسمی ذخیره‌شده لازم است.')
    if (!policyQuery.data) return setActionError('سیاست پایان ویزیت هنوز دریافت نشده است.')

    setBusy('complete')
    setActionError('')
    setActionMessage('')
    try {
      const enforced = Boolean(policyQuery.data.controls?.enforced)
      const position = enforced ? await currentPosition() : null
      const result = await apiRequest<PrevisitVisitDraftResponse>(
        `/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/complete`,
        {
          method: 'POST',
          body: {
            outcome: 'order',
            reason_id: null,
            reason: '',
            latitude: position?.latitude ?? null,
            longitude: position?.longitude ?? null,
            accuracy: position?.accuracy ?? null,
          },
        },
      )
      if (result.visit_status !== 'completed') throw new Error('Backend پایان ویزیت را تأیید نکرد.')
      navigateWithParams('/seller/customers', { pathId: result.route_id || resolvedPathId })
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'پایان ویزیت ناموفق بود.')
    } finally {
      setBusy('')
    }
  }

  const error = draftQuery.error || contextQuery.error || savedQuery.error || policyQuery.error
  const canSave = Boolean(draft?.lines.length && preview?.ok && preview.credit_control?.allowed !== false && draft?.visit_status === 'active')
  const canComplete = Boolean(draft?.visit_status === 'active' && draft.lines.length === 0 && savedRequests.length > 0 && policyQuery.data)

  return (
    <div className="ng-v2" dir="rtl" data-trace-id="ORD-04">
      <ResponsivePageContainer>
        <Stack gap={5}>
          <PageHeader
            eyebrow="ORDER / CART"
            title="سبد و محاسبه رسمی"
            description={context ? `${context.customer.store_name || context.customer.name || context.customer.id} · ${draft?.order_type || 'سفارش'}` : 'NGT EVC / Saved Requests'}
          />

          {draftQuery.status === 'loading' && !draft ? <AsyncState mode="loading" title="در حال دریافت سبد ویزیت" /> : null}
          {error ? <AsyncState mode="error" title="دریافت اطلاعات سبد ناموفق بود" message={error.message} onRetry={() => { draftQuery.reload(); contextQuery.reload(); savedQuery.reload(); policyQuery.reload() }} /> : null}

          {draft && context ? (
            <>
              <Alert title="مرجع قیمت و اعتبار، Preview رسمی NGT است" tone="info">
                ارقام Draft فقط برای نگهداری سبد هستند. پیش از ذخیره، سرور دوباره NGT EVC را اجرا و داده پایدار را canonical می‌کند.
              </Alert>

              {editingRequestId ? <Alert title="ویرایش درخواست ذخیره‌شده" tone="warning">پس از تغییر سبد، Preview رسمی جدید بگیرید و همان درخواست را دوباره ذخیره کنید.</Alert> : null}

              <Card>
                <SectionHeader
                  title="سبد جاری"
                  description={`${draft.line_count.toLocaleString('fa-IR')} ردیف · ${draft.warehouse_name || 'انبار نامشخص'}`}
                  action={<Button variant="secondary" onClick={() => navigateWithParams('/seller/catalog', { pathId: resolvedPathId, customerId: resolvedCustomerId, visitId, requestId: editingRequestId })}>بازگشت به کاتالوگ</Button>}
                />
                <Stack gap={3}>
                  {draft.lines.length ? draft.lines.map((line) => {
                    const official = previewItems.get(String(line.product_id))
                    return (
                      <Card key={String(line.product_id)}>
                        <Cluster>
                          <ShoppingCart size={18}/>
                          <div style={{ flex: 1 }}><strong>{lineTitle(context, String(line.product_id), line.title)}</strong><small>#{line.product_id} · {Number(line.quantity).toLocaleString('fa-IR')} عدد</small></div>
                          <StatusBadge label={official ? 'قیمت رسمی' : 'منتظر Preview'} tone={official ? 'success' : 'warning'}/>
                        </Cluster>
                        <KeyValue items={[
                          { key: 'قیمت واحد', value: official ? money(official.unit_price) : 'بعد از Preview رسمی' },
                          { key: 'تخفیف', value: official ? money(official.discount_amount) : '—' },
                          { key: 'مالیات و عوارض', value: official ? money(official.tax_and_charge_amount) : '—' },
                          { key: 'خالص ردیف', value: official ? money(official.net_amount) : '—' },
                        ]}/>
                      </Card>
                    )
                  }) : <AsyncState mode="empty" title="سبد جاری خالی است" />}
                </Stack>
              </Card>

              {draft.lines.length ? (
                <Card>
                  <SectionHeader title="محاسبه رسمی NGT EVC" description="Preview سفارش واقعی ایجاد نمی‌کند."/>
                  <Cluster>
                    <Button startIcon={<RefreshCw/>} loading={busy === 'preview'} disabled={Boolean(busy)} onClick={runPreview}>محاسبه رسمی</Button>
                    <StatusBadge label="creates_order = false" tone="info"/>
                  </Cluster>
                  {preview ? <KeyValue items={[
                    { key: 'جمع ناخالص', value: money(preview.totals.gross) },
                    { key: 'تخفیف', value: money(preview.totals.discount) },
                    { key: 'مالیات', value: money(preview.totals.tax + preview.totals.charge) },
                    { key: 'مبلغ خالص', value: <strong>{money(preview.totals.net)}</strong> },
                    { key: 'هدایا', value: `${(preview.gift_lines ?? []).length.toLocaleString('fa-IR')} ردیف` },
                    { key: 'اعتبار', value: <StatusBadge label={preview.credit_control.allowed ? 'تأیید' : 'رد'} tone={preview.credit_control.allowed ? 'success' : 'danger'}/> },
                  ]}/> : null}
                  {preview?.credit_control?.message ? <Alert title="کنترل اعتبار NGT" tone={preview.credit_control.allowed ? 'success' : 'danger'}>{preview.credit_control.message}</Alert> : null}
                  <Button size="lg" startIcon={<Save/>} loading={busy === 'save'} disabled={!canSave || Boolean(busy)} onClick={saveRequest}>
                    {editingRequestId ? 'ذخیره نسخه ویرایش‌شده' : 'ذخیره درخواست رسمی'}
                  </Button>
                </Card>
              ) : null}

              {actionError ? <Alert title="عملیات انجام نشد" tone="danger">{actionError}</Alert> : null}
              {actionMessage ? <Alert title="انجام شد" tone="success">{actionMessage}</Alert> : null}

              <Card>
                <SectionHeader title="درخواست‌های ذخیره‌شده" description={`${savedRequests.length.toLocaleString('fa-IR')} درخواست برای این ویزیت`}/>
                <Stack gap={3}>
                  {savedRequests.length ? savedRequests.map((saved) => (
                    <Card key={saved.id} interactive>
                      <Cluster>
                        <FileText size={18}/>
                        <div style={{ flex: 1 }}><strong>درخواست {saved.request_number.toLocaleString('fa-IR')}</strong><small>{saved.line_count.toLocaleString('fa-IR')} ردیف · {money(saved.total_amount)}</small></div>
                        <StatusBadge label="Preview رسمی ذخیره‌شده" tone="success"/>
                      </Cluster>
                      <KeyValue items={[
                        { key: 'نوع سفارش', value: saved.order_type || '—' },
                        { key: 'پرداخت', value: saved.payment_type || '—' },
                        { key: 'انبار', value: saved.warehouse_name || '—' },
                      ]}/>
                      <Cluster>
                        <Button variant="secondary" size="sm" startIcon={<Pencil/>} disabled={Boolean(busy) || draft.visit_status !== 'active'} onClick={() => void editSaved(saved)}>ویرایش</Button>
                        <Button variant="ghost" size="sm" startIcon={<Printer/>} onClick={() => {
                          try { printSavedRequest(saved, context) }
                          catch (reason) { setActionError(reason instanceof Error ? reason.message : 'چاپ ناموفق بود.') }
                        }}>چاپ / PDF</Button>
                      </Cluster>
                    </Card>
                  )) : <AsyncState mode="empty" title="هنوز درخواست رسمی ذخیره نشده است" />}
                </Stack>
              </Card>

              <Card>
                <SectionHeader title="پایان ویزیت سفارشی" description="ثبت واقعی در Varanegar در فاز نهایی پروژه فعال می‌شود."/>
                <KeyValue items={[
                  { key: 'درخواست ذخیره‌شده', value: savedRequests.length.toLocaleString('fa-IR') },
                  { key: 'سبد ذخیره‌نشده', value: draft.lines.length ? `${draft.lines.length.toLocaleString('fa-IR')} ردیف` : 'ندارد' },
                  { key: 'کنترل GPS پایان', value: policyQuery.data?.controls?.enforced ? 'فعال' : 'غیرفعال' },
                  { key: 'Varanegar Write', value: <StatusBadge label="فاز نهایی" tone="warning"/> },
                ]}/>
                <Button size="lg" startIcon={<CheckCircle2/>} loading={busy === 'complete'} disabled={!canComplete || Boolean(busy)} onClick={completeOrderVisit}>
                  پایان ویزیت با درخواست‌های ذخیره‌شده
                </Button>
              </Card>
            </>
          ) : null}
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
