import { ArrowLeft, MapPinned, Navigation, Route, Sparkles, Store, Users } from 'lucide-react'
import { navigateWithParams } from '../../app/router'
import { AsyncState } from '../../components/AsyncState'
import { Button, Cluster, ResponsivePageContainer, Stack, StatusBadge } from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'
import { isReviewMode, type SellerRoutesResponse } from './contracts'

const reviewData: SellerRoutesResponse = {
  seller: { personnel_id: 1, full_name: 'فروشنده نمونه' },
  visit_template: 'برنامه نمونه',
  routes: [
    { id: 'R-01', title: 'مسیر مرکزی', customer_count: 21, is_day_route: true, can_start_day_route: true, can_start_visit: true },
    { id: 'R-02', title: 'مسیر غرب', customer_count: 18, is_day_route: false, can_start_day_route: false, can_start_visit: false },
    { id: 'R-03', title: 'مسیر شرق', customer_count: 14, is_day_route: false, can_start_day_route: false, can_start_visit: false },
  ],
  day_route: { id: 'R-01', title: 'مسیر مرکزی' },
  day_route_status: 'assigned',
  live_assignment: true,
}

export function SellerRoutesScreen() {
  const review = isReviewMode()
  const query = useApiQuery<SellerRoutesResponse>(
    'seller:routes',
    (signal) => review ? Promise.resolve(reviewData) : apiRequest<SellerRoutesResponse>('/seller-workspace/routes', { signal }),
  )
  const routes = query.data?.routes ?? []
  const dayRouteId = String(query.data?.day_route?.id ?? '')
  const dayRoute = routes.find((route) => route.id === dayRouteId) ?? routes.find((route) => route.is_day_route) ?? null
  const hasAssignedDayRoute = Boolean(dayRoute?.id)
  const routeCount = routes.length

  return (
    <div className="ng-v2 ng-routes-art" dir="rtl" data-trace-id="SEL-01">
      <ResponsivePageContainer>
        <Stack gap={6}>
          <section className="ng-routes-art__hero">
            <div>
              <span className="ng-routes-art__eyebrow"><Route size={15}/> SELLER / ROUTES</span>
              <h1>مسیرهای فروش</h1>
              <p>مسیرها و تخصیص روزانه مستقیماً از قرارداد فعلی Seller Workspace دریافت می‌شوند.</p>
            </div>
            <Button
              size="lg"
              startIcon={<Navigation/>}
              disabled={!hasAssignedDayRoute}
              onClick={() => hasAssignedDayRoute && navigateWithParams('/seller/day-route', { pathId: dayRoute?.id })}
            >
              مسیر امروز
            </Button>
          </section>

          {query.status === 'loading' && !query.data ? <AsyncState mode="loading" title="در حال دریافت مسیرهای فروش" /> : null}
          {query.status === 'error' ? <AsyncState mode="error" title="دریافت مسیرهای فروش ناموفق بود" message={query.error?.message} onRetry={query.reload} /> : null}
          {query.status === 'success' && routes.length === 0 ? <AsyncState mode="empty" title="مسیر فعالی برای این فروشنده ثبت نشده است" /> : null}

          {query.data ? (
            <>
              <section className="ng-routes-art__command">
                <div className="ng-routes-art__map-surface">
                  <div className="ng-routes-art__map-grid"/>
                  <div className="ng-routes-art__path"/>
                  <span className="ng-routes-art__pin p1">1</span>
                  <span className="ng-routes-art__pin p2">2</span>
                  <span className="ng-routes-art__pin p3 is-active">3</span>
                  <span className="ng-routes-art__pin p4">4</span>
                  <div className="ng-routes-art__map-label">
                    <Sparkles size={16}/>
                    <div>
                      <small>Negin AI</small>
                      <strong>{hasAssignedDayRoute ? 'مسیر روز از تخصیص زنده خوانده شده است' : 'مسیر روز تخصیص داده نشده است'}</strong>
                    </div>
                  </div>
                </div>

                <aside className="ng-routes-art__today">
                  <span>TODAY ROUTE</span>
                  <h2>{dayRoute?.title || 'بدون مسیر روز'}</h2>
                  <div className="ng-routes-art__today-score">
                    <strong>{dayRoute?.customer_count?.toLocaleString('fa-IR') ?? '—'}</strong>
                    <span>مشتری در مسیر</span>
                  </div>
                  <div className="ng-routes-art__today-meta">
                    <div><MapPinned size={16}/><span>مسیریابی در صفحه نقشه</span></div>
                    <div><Users size={16}/><span>{routeCount.toLocaleString('fa-IR')} مسیر فعال</span></div>
                  </div>
                  <div className="ng-routes-art__progress"><i style={{ width: hasAssignedDayRoute ? '100%' : '0%' }}/></div>
                  <Button
                    size="lg"
                    disabled={!hasAssignedDayRoute}
                    onClick={() => hasAssignedDayRoute && navigateWithParams('/seller/day-route', { pathId: dayRoute?.id })}
                  >
                    مشاهده مسیر روز
                  </Button>
                  <Button
                    variant="ghost"
                    disabled={!hasAssignedDayRoute}
                    onClick={() => hasAssignedDayRoute && navigateWithParams('/seller/map', { pathId: dayRoute?.id })}
                  >
                    نمایش روی نقشه
                  </Button>
                </aside>
              </section>

              <section className="ng-routes-art__list">
                <div className="ng-routes-art__section-head">
                  <div><span>ROUTE LIBRARY</span><h2>همه مسیرها</h2></div>
                  <StatusBadge label={`${routeCount.toLocaleString('fa-IR')} مسیر`} tone="premium"/>
                </div>

                <div className="ng-routes-art__cards">
                  {routes.map((item, index) => (
                    <article key={item.id} className={item.is_day_route ? 'is-active' : ''}>
                      <div className="ng-routes-art__route-index">{String(index + 1).padStart(2, '0')}</div>
                      <div className="ng-routes-art__route-copy">
                        <Cluster gap={2}>
                          <strong>{item.title}</strong>
                          {item.is_day_route ? <StatusBadge label="مسیر روز" tone="premium"/> : null}
                        </Cluster>
                        <small>{item.customer_count.toLocaleString('fa-IR')} مشتری</small>
                      </div>
                      <div className="ng-routes-art__route-progress">
                        <span>{item.can_start_visit ? 'مجاز برای شروع ویزیت' : 'فقط مشاهده'}</span>
                        <div><i style={{ width: item.can_start_visit ? '100%' : '0%' }}/></div>
                      </div>
                      <button
                        aria-label={`باز کردن مسیر ${item.title}`}
                        onClick={() => navigateWithParams(item.is_day_route ? '/seller/day-route' : '/seller/customers', { pathId: item.id })}
                      >
                        <ArrowLeft size={19}/>
                      </button>
                    </article>
                  ))}
                </div>
              </section>

              <section className="ng-routes-art__tip">
                <Store size={20}/>
                <div>
                  <strong>اطلاعات این صفحه از تخصیص جاری NGT خوانده می‌شود.</strong>
                  <small>مقادیر فاصله، ETA و ترتیب مسیریابی تا زمان فراخوانی قرارداد نقشه نمایش داده نمی‌شوند.</small>
                </div>
                <Button
                  variant="secondary"
                  disabled={!hasAssignedDayRoute}
                  onClick={() => hasAssignedDayRoute && navigateWithParams('/seller/customers', { pathId: dayRoute?.id })}
                >
                  مشتریان مسیر روز
                </Button>
              </section>
            </>
          ) : null}
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}