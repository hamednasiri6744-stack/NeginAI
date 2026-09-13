import { Store } from 'lucide-react'
import { navigateWithParams } from '../../app/router'
import { AsyncState } from '../../components/AsyncState'
import { Button, Card, Cluster, InsightCard, KeyValue, MetricCard, PageHeader, ResponsivePageContainer, Stack, StatusBadge } from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import { customerDisplayName, isReviewMode, routeQueryValue, type SellerCustomerProfileResponse } from './contracts'

const reviewData: SellerCustomerProfileResponse = {
  route: { id: 'R-01', title: 'مسیر مرکزی' },
  customer: {
    id: 1,
    code: 'C-1021',
    name: 'علی رضایی',
    store_name: 'فروشگاه بهار',
    address: 'کرج، بلوار اصلی',
    mobile: '0912•••1842',
    open_invoice_count: 2,
    open_invoice_remaining: 12500000,
    cardex_balance: 3200000,
    financial_snapshot: {
      remaining_bed_credit: 42000000,
      remaining_asn_credit: 8000000,
      combined_remaining: 50000000,
      returned_cheque_count: 0,
      returned_cheque_amount: 0,
      customer_remaining: 3200000,
    },
    unique_id: 'review-customer',
    activity_name: 'خرد؇‌فروشی',
    category_name: 'فعال',
    level_name: 'A',
    city_name: 'کرج',
    state_name: 'البرز',
    visit_count: 18,
    order_count: 11,
    order_line_count: 46,
    sum_order_amount: 740000000,
    avg_successful_visit: 0.61,
    ngt_updated_at: '2026-09-13',
    editable: {},
  },
  lookups: {},
  draft: null,
  draft_updated_at: null,
  visit_controls: {},
  editable_contract: { fields: [], active_fields: [], source: 'review', write_mode: 'local_draft_only' },
}

function number(value: number | null | undefined) {
  return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 2 }).format(Number(value ?? 0))
}

export function Customer360Screen() {
  const review = isReviewMode()
  const pathId = routeQueryValue('pathId')
  const customerId = routeQueryValue('customerId')
  const query = useApiQuery<SellerCustomerProfileResponse>(
    `seller:customer:${pathId || (review ? 'review' : 'missing')}:${customerId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewData)
      : pathId && customerId
        ? apiRequest<SellerCustomerProfileResponse>(
            `/seller-workspace/routes/${encodeURIComponent(pathId)}/customers/${encodeURIComponent(customerId)}/profile`,
            { signal },
          )
        : Promise.reject(new Error('شناسه مسیر یا مشتری در URL موجود نیست')),
  )

  const customer = query.data?.customer
  const financial = customer?.financial_snapshot
  const routeId = query.data?.route.id || pathId
  const resolvedCustomerId = customer?.id ?? customerId
  const hasReturnedCheque = Number(financial?.returned_cheque_count ?? 0) > 0

  return (
    <div className="ng-v2" dir="rtl" data-trace-id="CUS-01">
      <ResponsivePageContainer>
        <Stack gap={5}>
          <PageHeader
            eyebrow="CUSTOMER 360"
            title={customer ? customerDisplayName(customer) : 'نمای ۳۶۰ مشتری'}
            description={
              customer
                ? [customer.name, customer.code && `#${customer.code}`, query.data?.route.title].filter(Boolean).join(' • ')
                : 'پروفایل واقعی مشتری از Seller Workspace'
            }
          />

          {query.status === 'loading' && !query.data ? <AsyncState mode="loading" title="در حال دریافت پروفایل مشتری" /> : null}
          {query.status === 'error' ? <AsyncState mode="error" title="دریافت پروفایل مشتری ناموفق بود" message={query.error?.message} onRetry={query.reload} /> : null}

          {customer ? (
            <>
              <Card>
                <Cluster>
                  <span className="ng-product-thumb"><Store/></span>
                  <div style={{ flex: 1 }}>
                    <strong>{customerDisplayName(customer)}</strong>
                    <small>{[customer.name, customer.activity_name, customer.city_name].filter(Boolean).join(' • ')}</small>
                  </div>
                  <StatusBadge
                    label={hasReturnedCheque ? 'چک برگشتی' : 'بدون چک برگشتی'}
                    tone={hasReturnedCheque ? 'danger' : 'success'}
                  />
                </Cluster>
                <KeyValue items={[
                  { key: 'کد مشتری', value: customer.code || '—' },
                  { key: 'تلفن', value: customer.mobile || customer.phone || '—' },
                  { key: 'آدرس', value: customer.address || '—' },
                  { key: 'سطح مشتری', value: customer.level_name || '—' },
                  { key: 'دسته‌بندی', value: customer.category_name || '—' },
                ]}/>
              </Card>

              <div className="ng-pattern-metrics">
                <MetricCard label="تعداد ویزیت" value={number(customer.visit_count)} detail="NGT profile" tone="info"/>
                <MetricCard label="تعداد سفارش" value={number(customer.order_count)} detail="NGT profile" tone="success"/>
                <MetricCard label="مبلغ تجمعی سفارش" value={number(customer.sum_order_amount)} detail="مقدار ثبت‌شده در NGT" tone="premium"/>
              </div>

              <InsightCard
                title="Negin AI / Customer Context"
                description={`این نما فقط از داده واقعی مشتری ساخته شده است: ${number(customer.visit_count)} ویزیت، ${number(customer.order_count)} سفارش و ${number(customer.open_invoice_count)} فاکتور باز.`}
                action="داده زنده"
                tone="info"
              />

              <Card>
                <KeyValue items={[
                  { key: 'مانده فاکتورهای باز', value: number(customer.open_invoice_remaining) },
                  { key: 'تعداد فاکتور باز', value: number(customer.open_invoice_count) },
                  { key: 'مانده کاردکس', value: number(customer.cardex_balance) },
                  { key: 'اعتبار باقیمانده ترکیبی', value: number(financial?.combined_remaining) },
                  { key: 'تعداد چک برگشتی', value: number(financial?.returned_cheque_count) },
                  { key: 'مبلغ چک برگشتی', value: number(financial?.returned_cheque_amount) },
                ]}/>
              </Card>

              <Button
                size="lg"
                startIcon={<Store/>}
                disabled={!routeId || !resolvedCustomerId}
                onClick={() => routeId && resolvedCustomerId && navigateWithParams('/seller/visit', {
                  pathId: routeId,
                  customerId: resolvedCustomerId,
                })}
              >
                ورود به فٶای ویزیب
              </Button>
            </>
          ) : null}
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
