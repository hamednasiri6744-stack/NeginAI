import { ArrowLeft, Clock3, MapPinned, Navigation, Route, Sparkles, Store, Users } from 'lucide-react'
import { navigate } from '../../app/router'
import { Button, Cluster, ResponsivePageContainer, Stack, StatusBadge } from '../../design-system/v2'

const routes = [
  { id:'R-01', title:'کرج مرکزی', customers:21, done:13, distance:'24 km', eta:'۲ ساعت و ۴۵ دقیقه', active:true },
  { id:'R-02', title:'گوهردشت', customers:18, done:0, distance:'19 km', eta:'۲ ساعت و ۱۰ دقیقه' },
  { id:'R-03', title:'مهرشهر', customers:14, done:0, distance:'16 km', eta:'۱ ساعت و ۵۰ دقیقه' },
]

export function SellerRoutesScreen(){
  return (
    <div className="ng-v2 ng-routes-art" dir="rtl" data-trace-id="SEL-01">
      <ResponsivePageContainer>
        <Stack gap={6}>
          <section className="ng-routes-art__hero">
            <div>
              <span className="ng-routes-art__eyebrow"><Route size={15}/> SELLER / ROUTES</span>
              <h1>مسیرهای من</h1>
              <p>مسیر امروز از قبل اولویت‌بندی شده؛ از همینجا ویزیت، نقشه و فرصت‌های مهم را کنترل کنید.</p>
            </div>
            <Button size="lg" startIcon={<Navigation/>} onClick={()=>navigate('/seller/day-route')}>ادامه مسیر امروز</Button>
          </section>

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
                <div><small>پیشنهاد Negin AI</small><strong>فروشگاه بهار، توقف بعدی</strong></div>
              </div>
            </div>

            <aside className="ng-routes-art__today">
              <span>TODAY ROUTE</span>
              <h2>کرج مرکزی</h2>
              <div className="ng-routes-art__today-score">
                <strong>۱۳</strong><span>از ۲۱ ویزیت</span>
              </div>
              <div className="ng-routes-art__today-meta">
                <div><MapPinned size={16}/><span>۲۴ km</span></div>
                <div><Clock3 size={16}/><span>۲:۴۵</span></div>
                <div><Users size={16}/><span>۸ باقی‌مانده</span></div>
              </div>
              <div className="ng-routes-art__progress"><i style={{width:'62%'}}/></div>
              <Button size="lg" onClick={()=>navigate('/seller/day-route')}>باز کردن مسیر</Button>
              <Button variant="ghost" onClick={()=>navigate('/seller/map')}>مشاهده روی نقشه</Button>
            </aside>
          </section>

          <section className="ng-routes-art__list">
            <div className="ng-routes-art__section-head">
              <div><span>ROUTE LIBRARY</span><h2>همه مسیرها</h2></div>
              <StatusBadge label="۳ مسیر فعال" tone="premium"/>
            </div>

            <div className="ng-routes-art__cards">
              {routes.map((item,index)=>(
                <article key={item.id} className={item.active?'is-active':''}>
                  <div className="ng-routes-art__route-index">{String(index+1).padStart(2,'0')}</div>
                  <div className="ng-routes-art__route-copy">
                    <Cluster gap={2}>
                      <strong>{item.title}</strong>
                      {item.active?<StatusBadge label="امروز" tone="premium"/>:null}
                    </Cluster>
                    <small>{item.customers.toLocaleString('fa-IR')} مشتری · {item.distance} · {item.eta}</small>
                  </div>
                  <div className="ng-routes-art__route-progress">
                    <span>{item.done?`${item.done.toLocaleString('fa-IR')} انجام شده`:'آماده شروع'}</span>
                    <div><i style={{width:item.done?`${Math.round(item.done/item.customers*100)}%`:'0%'}}/></div>
                  </div>
                  <button aria-label={`باز کردن مسیر ${item.title}`} onClick={()=>navigate(item.active?'/seller/day-route':'/seller/customers')}>
                    <ArrowLeft size={19}/>
                  </button>
                </article>
              ))}
            </div>
          </section>

          <section className="ng-routes-art__tip">
            <Store size={20}/>
            <div><strong>۸ مشتری در مسیر امروز نیازمند پیگیری هستند.</strong><small>۲ مورد دارای مانده باز و ۳ مورد با احتمال خرید مجدد بالا.</small></div>
            <Button variant="secondary" onClick={()=>navigate('/seller/customers')}>دیدن مشتری‌ها</Button>
          </section>
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
