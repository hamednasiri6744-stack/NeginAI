import {
  ArrowLeft,
  BarChart3,
  Bot,
  Clock3,
  FileText,
  Lightbulb,
  MapPinned,
  PackageSearch,
  Route,
  ShoppingBag,
  Sparkles,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'
import { navigate } from '../../app/router'
import { Button, Cluster, Progress, ResponsivePageContainer, Stack, StatusBadge } from '../../design-system/v2'

const fa = new Intl.NumberFormat('fa-IR')

const kpis = [
  { label: 'فروش امروز', value: fa.format(12450000), detail: '+۱۵٪', icon: ShoppingBag, tone: 'positive' },
  { label: 'سفارش‌ها', value: '۳۲۸', detail: '+۸٪', icon: FileText, tone: 'positive' },
  { label: 'مشتریان فعال', value: fa.format(1284), detail: '+۱۲٪', icon: Users, tone: 'positive' },
  { label: 'موجودی کالا', value: '۳۴۸', detail: '-۵٪', icon: PackageSearch, tone: 'negative' },
] as const

export function HomeScreen() {
  return (
    <div className="ng-v2 ng-home-v21" dir="rtl" data-trace-id="PLT-01">
      <ResponsivePageContainer>
        <Stack gap={5}>
          <section className="ng-home-v21__hero">
            <div className="ng-home-v21__hero-copy">
              <span className="ng-home-v21__eyebrow"><Sparkles size={15}/> Negin AI / Daily Command Center</span>
              <h1>هر مسیر، فرصتی برای رشد است.</h1>
              <p>فروش، مسیر و فرصت بعدی را در یک نمای هوشمند و عملیاتی دنبال کنید.</p>
              <Cluster gap={2}>
                <Button size="lg" startIcon={<Route/>} onClick={()=>navigate('/seller/routes')}>شروع مسیر امروز</Button>
                <Button size="lg" variant="secondary" startIcon={<Bot/>} onClick={()=>navigate('/ai')}>پرسش از Negin AI</Button>
              </Cluster>
            </div>
          </section>

          <section className="ng-home-v21__kpis" aria-label="شاخص‌های امروز">
            {kpis.map(({ label, value, detail, icon: Icon, tone }) => (
              <article key={label}>
                <div className="ng-home-v21__kpi-icon"><Icon size={22}/></div>
                <span>{label}</span>
                <strong dir="auto">{value}</strong>
                <small className={tone === 'negative' ? 'is-negative' : 'is-positive'}>{detail}</small>
                <div className="ng-home-v21__spark" aria-hidden="true"><i/><i/><i/><i/></div>
              </article>
            ))}
          </section>

          <section className="ng-home-v21__quick-actions" aria-label="دسترسی سریع">
            <button onClick={()=>navigate('/seller/catalog')}><ShoppingBag/><strong>سفارش جدید</strong><small>ثبت سریع سفارش</small></button>
            <button onClick={()=>navigate('/seller/customer')}><Users/><strong>مشتریان</strong><small>Customer 360</small></button>
            <button onClick={()=>navigate('/reports')}><BarChart3/><strong>گزارش‌ها</strong><small>KPI و تحلیل</small></button>
            <button onClick={()=>navigate('/seller/routes')}><MapPinned/><strong>مسیرها</strong><small>برنامه ویزیت</small></button>
          </section>

          <section className="ng-home-v21__route-card">
            <div className="ng-home-v21__section-head">
              <div>
                <span>FOCUS MISSION</span>
                <h2>مسیر ویزیت امروز</h2>
              </div>
              <StatusBadge label="۳ / ۵ ویزیت" tone="premium"/>
            </div>

            <div className="ng-home-v21__route-layout">
              <div className="ng-home-v21__map">
                <svg viewBox="0 0 520 250" role="img" aria-label="نمای مسیر امروز">
                  <defs>
                    <linearGradient id="ng-route-gold" x1="0" x2="1">
                      <stop offset="0" stopColor="#f7e3a0"/>
                      <stop offset="1" stopColor="#b67629"/>
                    </linearGradient>
                  </defs>
                  <path d="M58 194 C126 166 130 112 208 123 S294 196 360 143 S438 80 478 60" fill="none" stroke="url(#ng-route-gold)" strokeWidth="5" strokeLinecap="round"/>
                  {[['58','194','1'],['208','123','2'],['360','143','3'],['478','60','4']].map(([cx,cy,n])=><g key={n}><circle cx={cx} cy={cy} r="14" fill="#e8bf5a"/><text x={cx} y={Number(cy)+5} textAnchor="middle" fontSize="13" fontWeight="800" fill="#04111f">{n}</text></g>)}
                </svg>
                <div className="ng-home-v21__next-stop"><Target size={16}/><span><small>مشتری بعدی</small><strong>فروشگاه بهار</strong></span></div>
              </div>

              <aside className="ng-home-v21__route-stats">
                <div><Route size={18}/><span><small>مسافت باقی‌مانده</small><strong>۲۴ km</strong></span></div>
                <div><Clock3 size={18}/><span><small>زمان تقریبی</small><strong>۴۵ دقیقه</strong></span></div>
                <Progress value={60} label="پیشرفت مسیر"/>
                <Button variant="secondary" endIcon={<ArrowLeft size={17}/>} onClick={()=>navigate('/seller/day-route')}>باز کردن مسیر امروز</Button>
              </aside>
            </div>
          </section>

          <section className="ng-home-v21__lower-grid">
            <article className="ng-home-v21__suggestions">
              <div className="ng-home-v21__section-head">
                <div><span>AI SUGGESTIONS</span><h2>پیشنهادهای هوشمند</h2></div>
                <Lightbulb size={22}/>
              </div>
              <button onClick={()=>navigate('/ai')}><TrendingUp/><span><strong>افزایش فروش در منطقه شما</strong><small>یک فرصت فروش با اولویت بالا شناسایی شده است.</small></span><ArrowLeft/></button>
              <button onClick={()=>navigate('/seller/customer')}><Users/><span><strong>۳ مشتری بالقوه جدید</strong><small>در مسیر امروز شناسایی شده‌اند.</small></span><ArrowLeft/></button>
              <button onClick={()=>navigate('/seller/catalog')}><PackageSearch/><span><strong>موجودی در حال کاهش</strong><small>سه قلم نیاز به پیگیری دارند.</small></span><ArrowLeft/></button>
            </article>

            <article className="ng-home-v21__activity">
              <div className="ng-home-v21__section-head">
                <div><span>TODAY</span><h2>آخرین فعالیت‌ها</h2></div>
                <Clock3 size={22}/>
              </div>
              <ol>
                <li><i className="is-success"/><span><strong>سفارش ثبت شد</strong><small>فروشگاه بهار · ۰۹:۱۷</small></span></li>
                <li><i/><span><strong>ویزیت انجام شد</strong><small>مشتری مسیر ۲ · ۰۸:۳۰</small></span></li>
                <li><i/><span><strong>مشتری جدید</strong><small>فرصت شناسایی‌شده · ۰۸:۱۰</small></span></li>
                <li><i/><span><strong>حرکت مسیر آغاز شد</strong><small>شروع برنامه روز · ۰۷:۴۵</small></span></li>
              </ol>
            </article>
          </section>
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
