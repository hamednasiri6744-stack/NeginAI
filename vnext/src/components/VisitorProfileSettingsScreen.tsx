import { useState, type FormEvent } from 'react'
import {
  BellIcon,
  ChartIcon,
  ChevronLeftIcon,
  HelpIcon,
  HomeIcon,
  InfoIcon,
  LogoutIcon,
  MapIcon,
  PinIcon,
  PlusIcon,
  SettingsIcon,
  ShieldIcon,
  SyncIcon,
  UserGroupIcon,
  UserIcon,
} from './Icons'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorNotificationBadge } from '../state/VisitorNotificationsContext'

type Props = {
  onNavigate: (path: string) => void
  onLogout: () => void | Promise<void>
  onClose: () => void
}

export function VisitorProfileSettingsScreen({ onNavigate, onLogout, onClose }: Props) {
  const { unreadCount } = useVisitorNotificationBadge()
  const { profile, changePassword } = useVisitorAuth()
  const { activeRouteTitle, loading, reload } = useVisitorLiveData()
  const [notice, setNotice] = useState<string | null>(null)
  const [logoutOpen, setLogoutOpen] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordBusy, setPasswordBusy] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [styleLabEnabled, setStyleLabEnabled] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem('negin-style-lab-enabled') === '1'
  })

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }

  function toggleStyleLab() {
    const next = !styleLabEnabled
    setStyleLabEnabled(next)
    window.localStorage.setItem('negin-style-lab-enabled', next ? '1' : '0')
    window.dispatchEvent(new Event('negin-style-lab-toggle'))
    flash(next ? 'Style Lab فعال شد' : 'Style Lab غیرفعال شد')
  }

  async function refreshLiveData() {
    await reload()
    flash('مسیر و مشتریان از Backend دوباره خوانده شدند')
  }

  async function submitPassword(event: FormEvent) {
    event.preventDefault()
    setPasswordError(null)
    if (newPassword.length < 8) {
      setPasswordError('رمز جدید باید حداقل ۸ کاراکتر باشد.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('تکرار رمز جدید یکسان نیست.')
      return
    }
    setPasswordBusy(true)
    try {
      await changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordOpen(false)
      flash('رمز عبور با موفقیت تغییر کرد')
    } catch (caught) {
      setPasswordError(caught instanceof Error ? caught.message : 'تغییر رمز انجام نشد.')
    } finally {
      setPasswordBusy(false)
    }
  }

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vp-shell">
        <header className="vh-header">
          <button className="vh-profile active" type="button" aria-current="page" onClick={onClose}>
            <span className="vh-avatar">و</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || 'ویزیتور'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || 'حساب سازمانی'}</small>
            </span>
            <ChevronLeftIcon />
          </button>

          <button className="vh-bell" type="button" aria-label="اعلان‌ها" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr"><img src="/assets/neginai-logo-transparent.png" alt="Negin AI" /><div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div></div>
        </header>

        <section className="vp-heading"><div><span>حساب و تنظیمات</span><h1>پروفایل من</h1></div><SettingsIcon /></section>

        <section className="vp-identity">
          <span className="vp-avatar-large">و</span>
          <div>
            <strong>{profile?.full_name || profile?.username || 'کاربر سازمانی'}</strong>
            <span>کد پرسنلی: {profile?.personnel_id?.toLocaleString('fa-IR') || '—'}</span>
            <small>{profile?.branch || 'شعبه ثبت نشده'}{profile?.sales_line ? ` · ${profile.sales_line}` : ''}</small>
          </div>
          <span className="vp-status">{profile?.active ? 'فعال' : 'نامشخص'}</span>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><UserIcon /><strong>اطلاعات حساب</strong></div>
          <div className="vp-rows">
            <div className="vp-row"><span>نام کاربری</span><strong dir="ltr">{profile?.username || '—'}</strong></div>
            <div className="vp-row"><span>شماره همراه</span><strong dir="ltr">{profile?.phone || '—'}</strong></div>
            <div className="vp-row"><span>نقش سازمانی</span><strong>{profile?.role || '—'}</strong></div>
            <div className="vp-row"><span>مسیر فعال</span><strong>{activeRouteTitle || '—'}</strong></div>
          </div>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><SyncIcon /><strong>داده و همگام‌سازی</strong></div>
          <button className="vp-action-row" type="button" disabled={loading} onClick={() => void refreshLiveData()}>
            <span className="vp-row-icon"><SyncIcon /></span>
            <span><strong>{loading ? 'در حال بازخوانی…' : 'بازخوانی داده زنده'}</strong><small>Route و Customer از Seller Workspace</small></span>
            <ChevronLeftIcon />
          </button>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><SettingsIcon /><strong>تنظیمات برنامه</strong></div>
          <div className="vp-static-row"><span>Alert Center</span><strong>فعال · داده عملیاتی زنده</strong></div>
          <div className="vp-static-row"><span>زبان رابط</span><strong>فارسی</strong></div>
          <div className="vp-static-row"><span>نمایش اعداد</span><strong>فارسی</strong></div>
          <div className="vp-static-row"><span>پوسته</span><strong>تیره سازمانی</strong></div>
          <div className="vp-toggle-row">
            <span className="vp-row-icon"><SettingsIcon /></span>
            <span>
              <strong>Style Lab</strong>
              <small>نمایش کنترل تست استایل روی صفحه Home</small>
            </span>
            <button
              type="button"
              className={`vp-switch ${styleLabEnabled ? 'active' : ''}`}
              aria-pressed={styleLabEnabled}
              aria-label={styleLabEnabled ? 'غیرفعال کردن Style Lab' : 'فعال کردن Style Lab'}
              onClick={toggleStyleLab}
            >
              <span />
            </button>
          </div>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><ShieldIcon /><strong>امنیت و پشتیبانی</strong></div>
          <button className="vp-action-row" type="button" onClick={() => setPasswordOpen(true)}>
            <span className="vp-row-icon"><ShieldIcon /></span>
            <span><strong>تغییر رمز عبور</strong><small>متصل به Auth Service واقعی</small></span>
            <ChevronLeftIcon />
          </button>
          <div className="vp-action-row vp-action-static" aria-label="پشتیبانی سازمانی">
            <span className="vp-row-icon"><HelpIcon /></span>
            <span><strong>پشتیبانی سازمانی</strong><small>برای ثبت درخواست با مدیر سیستم تماس بگیرید</small></span>
            <span className="vp-static-state">بدون تیکت آنلاین</span>
          </div>
          <div className="vp-info-row"><InfoIcon /><span>نسخه رابط</span><strong>vNext</strong></div>
        </section>

        <button className="vp-logout" type="button" onClick={() => setLogoutOpen(true)}><LogoutIcon /><span>خروج از حساب</span></button>
        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        {passwordOpen ? (
          <div className="vp-modal-backdrop" role="presentation" onClick={() => setPasswordOpen(false)}>
            <form className="vp-modal vp-password-modal" role="dialog" aria-modal="true" aria-label="تغییر رمز" onSubmit={submitPassword} onClick={(event) => event.stopPropagation()}>
              <span className="vp-modal-icon"><ShieldIcon /></span>
              <h2>تغییر رمز عبور</h2>
              <p>رمز جدید پس از تأیید، نشست‌های قبلی حساب را باطل می‌کند.</p>
              <label><span>رمز فعلی</span><input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
              <label><span>رمز جدید</span><input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} required /></label>
              <label><span>تکرار رمز جدید</span><input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} required /></label>
              {passwordError ? <div className="login-message login-error" role="alert">{passwordError}</div> : null}
              <div><button type="button" className="secondary" onClick={() => setPasswordOpen(false)}>انصراف</button><button type="submit" className="danger" disabled={passwordBusy}>{passwordBusy ? 'در حال ثبت…' : 'تغییر رمز'}</button></div>
            </form>
          </div>
        ) : null}

        {logoutOpen ? (
          <div className="vp-modal-backdrop" role="presentation" onClick={() => setLogoutOpen(false)}>
            <section className="vp-modal" role="dialog" aria-modal="true" aria-label="تأیید خروج" onClick={(event) => event.stopPropagation()}>
              <span className="vp-modal-icon"><LogoutIcon /></span><h2>از حساب خارج می‌شوی؟</h2><p>نشست Backend باطل می‌شود و برای ورود دوباره باید اطلاعات حساب را وارد کنی.</p>
              <div><button type="button" className="secondary" onClick={() => setLogoutOpen(false)}>انصراف</button><button type="button" className="danger" onClick={() => { setLogoutOpen(false); void onLogout() }}>خروج</button></div>
            </section>
          </div>
        ) : null}

        <nav className="vh-nav" aria-label="ناوبری ویزیتور">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>مسیر</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>سفارش</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>مشتریان</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>گزارش‌ها</span></button>
        </nav>
      </div>
    </main>
  )
}