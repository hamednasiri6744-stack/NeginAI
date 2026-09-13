import { useState } from 'react'
import { MapPin, Package, PlayCircle, ShieldCheck, WalletCards } from 'lucide-react'
import { navigateWithParams } from '../../app/router'
import { AsyncState } from '../../components/AsyncState'
import {
  Alert,
  Button,
  Card,
  Cluster,
  KeyValue,
  MetricCard,
  PageHeader,
  ResponsivePageContainer,
  Stack,
  StatusBadge,
} from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import {
  customerDisplayName,
  isReviewMode,
  routeQueryValue,
  type PrevisitVisitDraftResponse,
  type SellerVisitPolicyResponse,
  type SellerVisitWorkspaceResponse,
} from './contracts'

const reviewWorkspace: SellerVisitWorkspaceResponse = {
  route: { id: 'R-01', title: 'مسیر مرکزی' },
  customer: {
    id: 1,
    code: 'C-1021',
    name: 'علی رضایی',
    store_name: 'فروشگاه بهار',
    address: 'کرج، بلوار اصلی',
    mobile: '0912•••1842',
    visit_count: 18,
    order_count: 11,
    open_invoice_count: 2,
    open_invoice_remaining: 12_500_000,
    cardex_balance: 3_200_000,
    editable: {},
  },
  analytics: {
    company_invoice_count_12m: 14,
    company_net_sales_12m: 740_000_000,
    seller_invoice_count_12m: 11,
    seller_net_sales_12m: 610_000_000,
    visit_score: 42,
    last_invoice_date: '1405/06/18',
  },
  open_invoices: {
    customer_id: 1,
    invoice_count: 2,
    invoices: [],
    source: 'review',
  },
  cheques: {
    customer_id: 1,
    summary: { active_returned_count: 0, active_returned_amount: 0 },
    cheques: [],
    source: 'review',
  },
  sources: {},
  read_only: true,
}

const reviewPolicy: SellerVisitPolicyResponse = {
  route: { id: 'R-01', title: 'مسیر مرکزی' },
  customer: {
    id: 1,
    name: 'علی رضایی',
    store_name: 'فروشگاه بهار',
    has_location: true,
    location_check_exempt: false,
  },
  controls: {
    enabled: true,
    enforced: true,
    max_distance_meters: 100,
    mode: 'review',
  },
  missing_required_fields: [],
  start_blockers: [],
  order_blockers: [],
  can_start_visit: true,
  reasons: {},
  visit_status_ids: {},
  source: 'review',
}

const reviewVisit: PrevisitVisitDraftResponse = {
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
  start_distance_meters: 24,
  ngt_send_enabled: false,
  ngt_status: 'not_sent',
}

function formatNumber(value: number | null | undefined) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(Number(value ?? 0))
}

function currentCoordinates(): Promise<{ latitude: number; longitude: number; accuracy: number | null }> {
  if (!navigator.geolocation) {
    return Promise.reject(new Error('دسترسی موقعیت مکانی در این دستگاه یا مرورگر موجود نیست.'))
  }
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null,
      }),
      () => reject(new Error('موقعیت فعلی دریافت نشد. دسترسی GPS را بررسی کنید و دوباره تلاش کنید.')),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 12000 },
    )
  })
}

export function VisitScreen() {
  const review = isReviewMode()
  const pathId = routeQueryValue('pathId')
  const customerId = routeQueryValue('customerId')
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState('')
  const [activeVisit, setActiveVisit] = useState<PrevisitVisitDraftResponse | null>(review ? reviewVisit : null)

  const workspaceQuery = useApiQuery<SellerVisitWorkspaceResponse>(
    `seller:visit-workspace:${pathId || (review ? 'review' : 'missing')}:${customerId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewWorkspace)
      : pathId && customerId
        ? apiRequest<SellerVisitWorkspaceResponse>(
            `/seller-workspace/routes/${encodeURIComponent(pathId)}/customers/${encodeURIComponent(customerId)}/visit-workspace`,
            { signal },
          )
        : Promise.reject(new Error('شناسه مسیر یا مشتری در URL موجود نیست')),
  )

  const policyQuery = useApiQuery<SellerVisitPolicyResponse>(
    `seller:visit-policy:${pathId || (review ? 'review' : 'missing')}:${customerId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewPolicy)
      : pathId && customerId
        ? apiRequest<SellerVisitPolicyResponse>(
            `/seller-workspace/previsit/policy?path_id=${encodeURIComponent(pathId)}&customer_id=${encodeURIComponent(customerId)}`,
            { signal },
          )
        : Promise.reject(new Error('شناسه مسیر یا مشتری در URL موجود نیست')),
  )

  const workspace = workspaceQuery.data
  const policy = policyQuery.data
  const customer = workspace?.customer
  const routeId = workspace?.route.id || policy?.route.id || pathId
  const resolvedCustomerId = customer?.id ?? policy?.customer.id ?? customerId
  const needsLocation = Boolean(policy?.controls.enforced) && !policy?.customer.location_check_exempt
  const startBlockers = policy?.start_blockers ?? []
  const orderBlockers = policy?.order_blockers ?? []
  const canStart = Boolean(policy?.can_start_visit) && Boolean(routeId) && Boolean(resolvedCustomerId)
  const activeReturnedCount = Number(workspace?.cheques.summary.active_returned_count ?? 0)

  async function startVisit() {
    if (!routeId || !resolvedCustomerId || !policy || starting) return
    setStarting(true)
    setStartError('')
    try {
      if (review) {
        setActiveVisit(reviewVisit)
        return
      }
      const position = needsLocation ? await currentCoordinates() : null
      const visit = await apiRequest<PrevisitVisitDraftResponse>('/seller-workspace/previsit/visits', {
        method: 'POST',
        body: {
          route_id: routeId,
          customer_id: String(resolvedCustomerId),
          ...(position ?? {}),
        },
      })
      setActiveVisit(visit)
    } catch (reason) {
      setStartError(reason instanceof Error ? reason.message : 'شروع ویزیت ناموفق بود.')
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="ng-v2" dir="rtl" data-trace-id="VIS-01">
      <ResponsivePageContainer>
        <Stack gap={5}>
          <PageHeader
            eyebrow="VISIT WORKSPACE"
            title={customer ? `ویزیت ${customerDisplayName(customer)}` : 'ویزیت مشتری'}
            description={workspace ? `${workspace.route.title} • اطلاعات عملیاتی فقط‌خواندنی قبل از شروع ویزیت` : 'در حال دریافت اطلاعات ویزیت'}
          />

          {workspaceQuery.status === 'loading' && !workspace ? <AsyncState mode="loading" title="در حال دریافت فضای ویزیت" /> : null}
          {workspaceQuery.status === 'error' ? <AsyncState mode="error" title="دریافت اطلاعات ویزیت ناموفق بود" message={workspaceQuery.error?.message} onRetry={workspaceQuery.reload} /> : null}
          {policyQuery.status === 'loading' && !policy ? <AsyncState mode="loading" title="در حال بررسی مجوز شروع ویزیت" /> : null}
          {policyQuery.status === 'error' ? <AsyncState mode="error" title="بررسی سیاست ویزیت ناموفق بود" message={policyQuery.error?.message} onRetry={policyQuery.reload} /> : null}

          {workspace ? (
            <>
              <div className="ng-pattern-metrics">
                <MetricCard
                  label="فروش شرکت در ۱۲ ماه"
                  value={formatNumber(workspace.analytics.company_net_sales_12m)}
                  detail="ریال"
                  tone="premium"
                />
                <MetricCard
                  label="فاکتور باز"
                  value={formatNumber(workspace.open_invoices.invoice_count)}
                  detail={`${formatNumber(customer?.open_invoice_remaining)} ریال مانده`}
                  tone={workspace.open_invoices.invoice_count > 0 ? 'warning' : 'success'}
                />
                <MetricCard
                  label="چک برگشتی فعال"
                  value={formatNumber(activeReturnedCount)}
                  detail={`${formatNumber(workspace.cheques.summary.active_returned_amount)} ریال`}
                  tone={activeReturnedCount > 0 ? 'danger' : 'success'}
                />
              </div>

              <Card>
                <KeyValue items={[
                  { key: 'امتیاز اولویت ویزیت', value: formatNumber(workspace.analytics.visit_score) },
                  { key: 'فروش این فروشنده در ۱۲ ماه', value: `${formatNumber(workspace.analytics.seller_net_sales_12m)} ریال` },
                  { key: 'تعداد فاکتور شرکت در ۱۲ ماه', value: formatNumber(workspace.analytics.company_invoice_count_12m) },
                  { key: 'آخرین فاکتور', value: workspace.analytics.last_invoice_date || '—' },
                  { key: 'وضعیت داده', value: <StatusBadge label={workspace.read_only ? 'فقط‌خواندنی' : 'قابل‌ویرایش'} tone={workspace.read_only ? 'info' : 'warning'} /> },
                ]}/>
              </Card>
            </>
          ) : null}

          {policy ? (
            <Card>
              <Cluster>
                <ShieldCheck/>
                <div style={{ flex: 1 }}>
                  <strong>سیاست شروع ویزیت</strong>
                  <small>{policy.source}</small>
                </div>
                <StatusBadge label={policy.can_start_visit ? 'مجاز' : 'مسدود'} tone={policy.can_start_visit ? 'success' : 'danger'} />
              </Cluster>
              <KeyValue items={[
                { key: 'کنترل موقعیت', value: policy.controls.enforced ? 'اجباری' : 'غیراجباری' },
                { key: 'حداکثر فاصله', value: policy.controls.max_distance_meters != null ? `${formatNumber(policy.controls.max_distance_meters)} متر` : '—' },
                { key: 'استثنای مکانی مشتری', value: policy.customer.location_check_exempt ? 'بله' : 'خیر' },
                { key: 'فیلدهای ضروری ناقص', value: formatNumber(policy.missing_required_fields.length) },
              ]}/>
            </Card>
          ) : null}

          {startBlockers.length > 0 ? (
            <Alert title="شروع ویزیت مجاز نیست" tone="danger">
              {startBlockers.join(' • ')}
            </Alert>
          ) : null}

          {orderBlockers.length > 0 ? (
            <Alert title="محدودیت قبل از ثبت سفارش" tone="warning">
              {orderBlockers.join(' • ')}
            </Alert>
          ) : null}

          {startError ? <Alert title="شروع ویزیت ناموفق بود" tone="danger">{startError}</Alert> : null}

          {!activeVisit && policy ? (
            <>
              <Alert title={needsLocation ? 'GPS برای شروع الزامی است' : 'شروع ویزیت آماده است'} tone={needsLocation ? 'info' : 'success'}>
                {needsLocation
                  ? 'موقعیت زنده دستگاه هنگام شروع دریافت می‌شود و کنترل فاصله در Backend انجام خواهد شد.'
                  : 'طبق سیاست فعلی Backend، شروع این ویزیت نیاز به موقعیت زنده دستگاه ندارد.'}
              </Alert>
              <Button
                size="lg"
                loading={starting}
                disabled={!canStart || startBlockers.length > 0}
                startIcon={<PlayCircle/>}
                onClick={startVisit}
              >
                شروع ویزیت
              </Button>
            </>
          ) : null}

          {activeVisit ? (
            <>
              <Card>
                <Cluster>
                  <PlayCircle/>
                  <div style={{ flex: 1 }}>
                    <strong>ویزیت فعال</strong>
                    <small>{activeVisit.visit_id}</small>
                  </div>
                  <StatusBadge label={activeVisit.visit_status} tone="success"/>
                </Cluster>
                <KeyValue items={[
                  { key: 'شروع', value: activeVisit.started_at || '—' },
                  { key: 'فاصله شروع', value: activeVisit.start_distance_meters == null ? 'کنترل نشده' : `${formatNumber(activeVisit.start_distance_meters)} متر` },
                  { key: 'اقلام سبد', value: formatNumber(activeVisit.line_count) },
                  { key: 'وضعیت ارسال NGT', value: activeVisit.ngt_status || 'not_sent' },
                ]}/>
              </Card>

              <Button
                size="lg"
                startIcon={<Package/>}
                onClick={() => navigateWithParams('/seller/catalog', {
                  pathId: activeVisit.route_id,
                  customerId: activeVisit.customer_id,
                  visitId: activeVisit.visit_id,
                })}
              >
                ادامه به کاتالوگ و سفارش
              </Button>

              <div className="ng-pattern-metrics">
                <MetricCard
                  label="موقعیت شروع"
                  value={activeVisit.start_distance_meters == null ? 'بدون کنترل' : `${formatNumber(activeVisit.start_distance_meters)} m`}
                  detail={needsLocation ? 'GPS / Backend gate' : 'Policy bypass'}
                  tone="info"
                />
                <MetricCard
                  label="سبد فعلی"
                  value={formatNumber(activeVisit.line_count)}
                  detail={`${formatNumber(activeVisit.total_amount)} ریال`}
                  tone="neutral"
                />
                <MetricCard
                  label="فاکتور باز مشتری"
                  value={formatNumber(workspace?.open_invoices.invoice_count)}
                  detail="قبل از سفارش"
                  tone="warning"
                />
              </div>

              <Alert title="پایان ویزیت هنوز در این مرحله فعال نشده است" tone="info">
                پایان ویزیت به قراردادهای outcome/reason وابسته است و در slice مربوط به completion به‌صورت مستقل متصل و تست خواهد شد.
              </Alert>
            </>
          ) : null}

          {workspace && !activeVisit ? (
            <Card>
              <Cluster>
                <WalletCards/>
                <div>
                  <strong>وضعیت مالی قبل از ویزیت</strong>
                  <small>{formatNumber(customer?.open_invoice_remaining)} ریال مانده فاکتور باز</small>
                </div>
                <MapPin/>
              </Cluster>
            </Card>
          ) : null}
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
