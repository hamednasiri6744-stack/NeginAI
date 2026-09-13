import { useMemo, useState } from 'react'
import { MapPin, Phone, Store } from 'lucide-react'
import { navigateWithParams } from '../../app/router'
import { Button, Card, Cluster, PageHeader, ResponsivePageContainer, SearchInput, Stack, StatusBadge } from '../../design-system/v2'
import { AsyncState } from '../../components/AsyncState'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import { customerDisplayName, isReviewMode, routeQueryValue, type SellerRouteCustomersResponse, visitStatusLabel } from './contracts'

const reviewData: SellerRouteCustomersResponse = {
  route: { id: 'R-01', title: 'مسیر مرکزی' },
  customer_count: 3,
  customers: [
    { id: 1, code: 'C-1021', store_name: 'فروشگاه بهار', name: 'علی رضایی', mobile: '0912•••1842', address: 'کرج، بلوار اصلی', latitude: 35.83, longitude: 50.97, open_invoice_count: 2 },
    { id: 2, code: 'C-1088', store_name: 'سوپرمارکت سروش', name: 'محمد حسینی', mobile: '0912•••5120', address: 'گوهردشت', latitude: 35.80, longitude: 50.99, open_invoice_count: 0 },
    { id: 3, code: 'C-1114', store_name: 'فروشگاه پارس', name: 'رضا کریمی', mobile: '0935•••2401', address: 'کرج، میدان اصلی', latitude: 35.82, longitude: 50.95, open_invoice_count: 1 },
  ],
}

export function SellerRouteCustomersScreen() {
  const [search, setSearch] = useState('')
  const review = isReviewMode()
  const pathId = routeQueryValue('pathId')
  const query = useApiQuery<SellerRouteCustomersResponse>(
    `seller:customers:${pathId || (review ? 'review' : 'missing')}`,
    (signal) => review
      ? Promise.resolve(reviewData)
      : pathId
        ? apiRequest<SellerRouteCustomersResponse>(`/seller-workspace/routes/${encodeURIComponent(pathId)}/customers`, { signal })
        : Promise.reject(new Error('شناسه مسیر در URL موجود نیست')),
  )
  const customers = useMemo(() => query.data?.customers ?? [], [query.data?.customers])
  const normalizedSearch = search.trim().toLocaleLowerCase('fa-IR')
  const visibleCustomers = useMemo(
    () => normalizedSearch
      ? customers.filter((customer) => [customer.store_name, customer.name, customer.code, customer.mobile, customer.phone, customer.address]
          .some((value) => String(value ?? '').toLocaleLowerCase('fa-IR').includes(normalizedSearch)))
      : customers,
    [customers, normalizedSearch],
  )
  const routeId = query.data?.route.id || pathId

  return (
    <div className="ng-v2" dir="rtl" data-trace-id="SEL-03">
      <ResponsivePageContainer>
        <Stack gap={5}>
          <PageHeader
            eyebrow="ROUTE / CUSTOMERS"
            title={query.data?.route?.title || 'مشتریان مسیر'}
            description="فهرست مشتریان، وضعیت ویزیت و خلاصه مالی از قرارداد فعلی Seller Workspace دریافت می‌شود."
            actions={
              <Button
                variant="secondary"
                disabled={!routeId}
                onClick={() => routeId && navigateWithParams('/seller/map', { pathId: routeId })}
              >
                نمایش نقشه
              </Button>
            }
          />
          <SearchInput
            label="جستجوی مشتری"
            placeholder="نام فروشگاه، مشتری، کد، تلفن یا آدرس"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          {query.status === 'loading' && !query.data ? <AsyncState mode="loading" title="در حال دریافت مشتریان" /> : null}
          {query.status === 'error' ? <AsyncState mode="error" title="دریافت مشتریان ناموفق بود" message={query.error?.message} onRetry={query.reload} /> : null}
          {query.status === 'success' && customers.length === 0 ? <AsyncState mode="empty" title="مشتری فعالی در این مسیر وجود ندارد" /> : null}
          {query.data && customers.length > 0 && visibleCustomers.length === 0 ? <AsyncState mode="empty" title="نتیجه‌ای برای این جستجو پیدا نشد" /> : null}

          {query.data && visibleCustomers.length > 0 ? (
            <Stack gap={3}>
              <StatusBadge label={`${new Intl.NumberFormat('fa-IR').format(query.data.customer_count ?? customers.length)} مشتری`} tone="premium"/>
              {visibleCustomers.map((customer) => {
                const completed = customer.visit_resolution?.status === 'completed'
                const hasOpenInvoice = Number(customer.open_invoice_count ?? 0) > 0
                return (
                  <Card key={String(customer.id)} interactive>
                    <Cluster>
                      <span className="ng-product-thumb"><Store/></span>
                      <div style={{ flex: 1 }}>
                        <strong>{customerDisplayName(customer)}</strong>
                        <small>{[customer.code && `#${customer.code}`, customer.name].filter(Boolean).join(' • ')}</small>
                      </div>
                      <StatusBadge
                        label={completed ? visitStatusLabel(customer) : hasOpenInvoice ? 'فاکتور باز' : 'در انتظار'}
                        tone={completed ? 'success' : hasOpenInvoice ? 'warning' : 'info'}
                      />
                    </Cluster>
                    <Cluster>
                      {customer.address ? <span><MapPin size={15}/> {customer.address}</span> : null}
                      {customer.mobile || customer.phone ? <span><Phone size={15}/> {customer.mobile || customer.phone}</span> : null}
                      <Button
                        disabled={!routeId}
                        onClick={() => routeId && navigateWithParams('/seller/customer', { pathId: routeId, customerId: customer.id })}
                      >
                        Customer 360
                      </Button>
                    </Cluster>
                  </Card>
                )
              })}
            </Stack>
          ) : null}
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}