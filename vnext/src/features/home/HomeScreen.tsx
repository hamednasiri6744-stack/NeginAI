import { ArrowLeft, Bot, ChevronLeft, MapPinned, Route, ShoppingBag, Sparkles, Target, TrendingUp, WalletCards } from 'lucide-react'
import { navigate } from '../../app/router'
import { Button, Cluster, Progress, ResponsivePageContainer, Stack, StatusBadge } from '../../design-system/v2'

const fa = new Intl.NumberFormat('fa-IR')

export function HomeScreen() {
  return (
    <div className="ng-v2 ng-home-art" dir="rtl" data-trace-id="PLT-01">
      <ResponsivePageContainer>
        <Stack gap={6}>
          <section className="ng-home-art__hero">
            <div className="ng-home-art__hero-copy">
              <span className="ng-home-art__eyebrow"><Sparkles size={15}/> Negin AI / Daily Command Center</span>
              <h1>امروز را با تمرکز روی فروش‌های باارزش شروع کنید</h1>
              <p>مسیر، مشتری و فرصت بعدی را Negin AI بر اساس وضعیت روز در یک نمای عملیاتی جمع می‌کند.</p>
              <Cluster gap={2}>
                <Button size="lg" startIcon={<Route/>} onClick={()=>navigate('/seller/routes')}>شروع مسیر امروز</Button>
                <Button size="lg" variant="secondary" startIcon={<Bot/>} onClick={()=>navigate('/ai')}>پرسش از Negin AI</Button>
              </Cluster>
            </div>

            <div className="ng-home-art__pulse" aria-label="تحقق تارگت امروز">
              <div className="ng-home-art__pulse-ring">
                <div className="ng-home-art__pulse-core">
                  <span>تحقق تارگت</span>
                  <strong>۷۲٪</strong>
                  <small>+۸٪ نسبت به دیروز</small>
                </div>
              </div>
              <div className="ng-home-art__pulse-foot">
                <span><TrendingUp size={15}/> ریتم فروش مثبت</span>
                <StatusBadge label="On Track" tone="success"/>
              </div>
            </div>
          </section>

          <section className="ng-home-art__kpis">
            <article><span>فروش امروز</span><strong>{fa.format(12450000)}</strong><small>ریال · +۱۵٪</small></article>
            <article><span>ویزیت انجام‌شده</span><strong>۳ / ۵</strong><small>۲ ویزیت باقی‌مانده</small></article>
            <article><span>فرصت داغ</span><strong>۳</strong><small>مشتری با پتانسیل بالا</small></article>
            <article><span>ریسک مالی</span><strong>۱</strong><small>نیازمند پیگیری</small></article>
          </section>

          <section className="ng-home-art__focus">
            <div className="ng-home-art__route-panel">
              <div className="ng-home-art__section-head">
                <div>
                  <span>FOCUS MISSION</span>
                  <h2>مسیر کرج مرکزی</h2>
                </div>
                <StatusBadge label="مسیر امروز" tone="premium"/>
              </div>

              <div className="ng-home-art__route-visual">
                <div className="ng-home-art__route-line"/>
                <span className="is-done">۱</span>
                <span className="is-done">۲</span>
                <span className="is-active">۳</span>
                <span>۴</span>
                <span>۵</span>
              </div>

              <div className="ng-home-art__route-meta">
                <div><small>ویزیت بعدی</small><strong>فروشگاه بهار</strong></div>
                <div><small>فاصله</small><strong>۱.۸ km</strong></div>
                <div><small>فرصت فروش</small><strong>بالا</strong></div>
              </div>
              <Progress value={60} label="پیشرفت مسیر"/>
              <button className="ng-home-art__inline-action" onClick={()=>navigate('/seller/day-route')}>
                باز کردن مأموریت امروز <ChevronLeft size={17}/>
              </button>
            </div>

            <aside className="ng-home-art__ai-panel">
              <div className="ng-home-art__ai-orb"><Bot size={26}/></div>
              <span>Negin AI Insight</span>
              <h3>سه مشتری امروز بیشترین احتمال خرید مجدد را دارند.</h3>
              <p>اولویت بازدید را بر اساس فاصله، مانده حساب و الگوی خرید مرتب کردم.</p>
              <div className="ng-home-art__chips">
                <span>Misswake</span><span>Oral Care</span><span>High Potential</span>
              </div>
              <Button variant="secondary" endIcon={<ArrowLeft size={17}/>} onClick={()=>navigate('/ai')}>دیدن تحلیل کامل</Button>
            </aside>
          </section>

          <section className="ng-home-art__actions">
            <button onClick={()=>navigate('/seller/routes')}><span><MapPinned/></span><strong>مسیرهای من</strong><small>برنامه ویزیت امروز</small></button>
            <button onClick={()=>navigate('/seller/catalog')}><span><ShoppingBag/></span><strong>سفارش جدید</strong><small>شروع سریع سفارش</small></button>
            <button onClick={()=>navigate('/seller/customer')}><span><WalletCards/></span><strong>وضعیت مالی</strong><small>مانده، اعتبار و ریسک</small></button>
            <button onClick={()=>navigate('/seller/customer')}><span><Target/></span><strong>مشتریان هدف</strong><small>اولویت‌های پیشنهادی AI</small></button>
          </section>
        </Stack>
      </ResponsivePageContainer>
    </div>
  )
}
