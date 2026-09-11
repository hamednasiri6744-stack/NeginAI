import { Bell, Download, KeyRound, Settings, Smartphone, UserRound } from 'lucide-react'

const items = [
  { icon: UserRound, title: 'پروفایل و حساب', detail: 'هویت و زمینه کاربر' },
  { icon: Bell, title: 'اعلان‌ها', detail: 'Notification / Push states' },
  { icon: Settings, title: 'تنظیمات', detail: 'Preferenceهای مجاز' },
  { icon: KeyRound, title: 'دسترسی‌ها', detail: 'Presentation از permissionهای واقعی' },
  { icon: Download, title: 'PWA و به‌روزرسانی', detail: 'Install / Update / Offline' },
  { icon: Smartphone, title: 'Android Integration', detail: 'Native bridge و SellerNavigator' },
]

export function MoreScreen() {
  return (
    <div className="ng-screen" data-trace-id="SCR-S4-03">
      <section className="ng-page-heading">
        <span className="ng-eyebrow">More</span>
        <h1>بیشتر</h1>
        <p>Overflow و Capabilityهای کم‌تکرار بدون حذف Feature یا ساخت Shell جدا برای Roleها.</p>
      </section>
      <div className="ng-list-card">
        {items.map(({ icon: Icon, title, detail }) => (
          <button type="button" className="ng-list-row" key={title}>
            <span className="ng-list-icon"><Icon size={20} /></span>
            <span><strong>{title}</strong><small>{detail}</small></span>
            <span aria-hidden="true">‹</span>
          </button>
        ))}
      </div>
    </div>
  )
}
