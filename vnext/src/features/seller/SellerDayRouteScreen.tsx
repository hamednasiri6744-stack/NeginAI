import { Navigation } from 'lucide-react'
import { navigateWithParams } from '../../app/router'
import { AsyncState } from '../../components/AsyncState'
import { Button, PageHeader, ResponsivePageContainer, RouteStopItem, Stack, StatStrip, RouteSummaryCard } from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import { customerDisplayName, isReviewMode, routeQueryValue, type SellerRouteCustomersResponse, visitStatusLabel } from './contracts'

const reviewData: SellerRouteCustomersResponse = {
  route: { id: 'R-01', title: 'مسیر مرکزی' },
  customer_count: 4,
  customers: [
    { id: 1, code: 'C-1021', store_name: 'فروشگاه بهار', address: 'کرج', visit_resolution: { status: 'completed', outcome: 'order' } },
    { id: 2, code: 'C-1088', store_name: 'سوپرمارکت سروش', address: 'کرج', visit_resolution: { status: 'completed', outcome: 'no_order' } },
    { id: 3, code: 'C-1114', store_name: 'فروشگاه پارس', address: 'کرج', visit_resolution: null },
    { id: 4, code: 'C-1140', store_name: 'فروشگاه امید', address: 'کرج', visit_resolution: null },
  ],
}

export function SellerDayRouteScreen() {
  const review = isReviewMode()
  const pathId = routeQueryValue('pathId')
  const query = useApiQuery<SellerRouteCustomersResponse>(
    `seller:day-route:${pathId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewData)
      : pathId
        ? apiRequest<SellerRouteCustomersResponse>(`/seller-workspace/routes/${encodeURIComponent(pathId)}/customers`, { signal })
        : Promise.reject(new Error('شناسه مسیر روز در URL موجود نیست')),
  )
  const customers = query.data?.customers ?? []
  const completed = customers.filter((customer) => customer.visit_resolution?.status === 'completed').length
  const routeId = query.data?.route.id || pathId

  return (
    <div className="ng-v2" dir="rtl" data-trace-id="SEL-02">
      <ResponsivePageContainer>
        <Stack gap={5}>
          <PageHeader
            eyebrow="DAY ROUTE"
            title={query.data?.route.title || 'مسیر روز'}
            description="وضعیت ویزیت‌ها از قرارداد فعلی مشتریان مسیر محاسبه می‌شود."
            actions={
              <Button
                startIcon={<Navigation/>}
                disabled={!routeId}
                onClick={() => routeId && navigateWithParams('/seller/map', { pathId: routeId })}
              >
                نمایش مسیر روی نقشه
              </Button>
            }
          />

          {query.status === 'loading' && !query.data ? <AsyncState mode="loading" title="در حال دریافت مسیر روز" /> : null}
          {query.status === 'error' ? <AsyncState mode="error" title="دریافت مسیر روز ناموفق بود" message={query.error?.message} onRetry={query.reload} /> : null}
          {query.status === 'success' && customers.length === 0 ? <AsyncState mode="empty" title="مشتری فعالی در این مسیر وجود ندارد" /> : null}

          {query.data ? (
            <>
              <StatStrip items={[
                { label: 'مشتریان مسیر', value: query.data.customer_count.toLocaleString('fa-IR') },
                { label: 'ویزیت تکمیل‌شده', value: completed.toLocaleString('fa-IR') },
                { label: 'باقی‌مانده', value: Math.max(query.data.customer_count - completed, 0).toLocaleString('fa-IR') },
              ]}/>
              <RouteSummaryCard
                title={query.data.route.title}
                visited={completed}
                total={query.data.customer_count}
                distance="—"
                eta="—"
              />
              <Stack gap={2}>
                {customers.map((customer, index) => (
                  <RouteStopItem
                    key={String(customer.id)}
                    index={index + 1}
                    title={customerDisplayName(customer)}
                    meta={customer.address || (customer.code ? `#${customer.code}` : String(customer.id))}
                    status={visitStatusLabel(customer)}
                  />
                ))}
              </Stack>
              <Button
                size="lg"
                disabled={!routeId}
                onClick={() => routeId && navigateWithParams('/seller/customers', { pathId: routeId })}
              >
                مشاهده مشتریان مسیر
              </Button>
            </>
          ) : null}
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}