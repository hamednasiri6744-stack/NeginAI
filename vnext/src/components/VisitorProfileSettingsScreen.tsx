import { useState, type FormEvent } from 'react'
import {
  BellIcon,
  ChartIcon,
  ChevronLeftIcon,
  DeviceIcon,
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
import { useVisitorNotifications } from '../state/VisitorNotificationsContext'

type Props = {
  onNavigate: (path: string) => void
  onLogout: () => void | Promise<void>
}

type ToggleKey = 'notifications' | 'offline' | 'autosync'

const settingsKeys: Record<ToggleKey, string> = {
  notifications: 'neginai.settings.notifications',
  offline: 'neginai.settings.offline',
  autosync: 'neginai.settings.autosync',
}

function initialToggle(key: ToggleKey, fallback = true) {
  const stored = localStorage.getItem(settingsKeys[key])
  return stored === null ? fallback : stored === 'true'
}

export function VisitorProfileSettingsScreen({ onNavigate, onLogout, onClose }: Props) {
  const { unreadCount } = useVisitorNotifications()
  const { profile, changePassword } = useVisitorAuth()
  const { activeRouteTitle, loading, reload } = useVisitorLiveData()
  const [notifications, setNotifications] = useState(() => initialToggle('notifications'))
  const [offline, setOffline] = useState(() => initialToggle('offline'))
  const [autosync, setAutosync] = useState(() => initialToggle('autosync'))
  const [notice, setNotice] = useState<string | null>(null)
  const [logoutOpen, setLogoutOpen] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordBusy, setPasswordBusy] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2200)
  }

  function updateToggle(key: ToggleKey, value: boolean) {
    localStorage.setItem(settingsKeys[key], String(value))
    if (key === 'notifications') setNotifications(value)
    if (key === 'offline') setOffline(value)
    if (key === 'autosync') setAutosync(value)
  }

  async function refreshLiveData() {
    await reload()
    flash('ظ…ط³غŒط± ظˆ ظ…ط´طھط±غŒط§ظ† ط§ط² Backend ط¯ظˆط¨ط§ط±ظ‡ ط®ظˆط§ظ†ط¯ظ‡ ط´ط¯ظ†ط¯')
  }

  async function submitPassword(event: FormEvent) {
    event.preventDefault()
    setPasswordError(null)
    if (newPassword.length < 8) {
      setPasswordError('ط±ظ…ط² ط¬ط¯غŒط¯ ط¨ط§غŒط¯ ط­ط¯ط§ظ‚ظ„ غ¸ ع©ط§ط±ط§ع©طھط± ط¨ط§ط´ط¯.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('طھع©ط±ط§ط± ط±ظ…ط² ط¬ط¯غŒط¯ غŒع©ط³ط§ظ† ظ†غŒط³طھ.')
      return
    }
    setPasswordBusy(true)
    try {
      await changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordOpen(false)
      flash('ط±ظ…ط² ط¹ط¨ظˆط± ط¨ط§ ظ…ظˆظپظ‚غŒطھ طھط؛غŒغŒط± ع©ط±ط¯')
    } catch (caught) {
      setPasswordError(caught instanceof Error ? caught.message : 'طھط؛غŒغŒط± ط±ظ…ط² ط§ظ†ط¬ط§ظ… ظ†ط´ط¯.')
    } finally {
      setPasswordBusy(false)
    }
  }

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vp-shell">
        <header className="vh-header">
          <button className="vh-profile active" type="button" aria-current="page" onClick={onClose} aria-label="بستن پروفایل و بازگشت به صفحه قبل">
            <span className="vh-avatar">ظˆ</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || 'ظˆغŒط²غŒطھظˆط±'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || 'ط­ط³ط§ط¨ ط³ط§ط²ظ…ط§ظ†غŒ'}</small>
            </span>
            <ChevronLeftIcon />
          </button>

          <button className="vh-bell" type="button" aria-label="ط§ط¹ظ„ط§ظ†â€Œظ‡ط§" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr"><img src="/assets/neginai-logo-transparent.png" alt="Negin AI" /><div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div></div>
        </header>

        <section className="vp-heading"><div><span>ط­ط³ط§ط¨ ظˆ طھظ†ط¸غŒظ…ط§طھ</span><h1>ظ¾ط±ظˆظپط§غŒظ„ ظ…ظ†</h1></div><SettingsIcon /></section>

        <section className="vp-identity">
          <span className="vp-avatar-large">ظˆ</span>
          <div>
            <strong>{profile?.full_name || profile?.username || 'ع©ط§ط±ط¨ط± ط³ط§ط²ظ…ط§ظ†غŒ'}</strong>
            <span>ع©ط¯ ظ¾ط±ط³ظ†ظ„غŒ: {profile?.personnel_id?.toLocaleString('fa-IR') || 'â€”'}</span>
            <small>{profile?.branch || 'ط´ط¹ط¨ظ‡ ط«ط¨طھ ظ†ط´ط¯ظ‡'}{profile?.sales_line ? ` آ· ${profile.sales_line}` : ''}</small>
          </div>
          <span className="vp-status">{profile?.active ? 'ظپط¹ط§ظ„' : 'ظ†ط§ظ…ط´ط®طµ'}</span>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><UserIcon /><strong>ط§ط·ظ„ط§ط¹ط§طھ ط­ط³ط§ط¨</strong></div>
          <div className="vp-rows">
            <div className="vp-row"><span>ظ†ط§ظ… ع©ط§ط±ط¨ط±غŒ</span><strong dir="ltr">{profile?.username || 'â€”'}</strong></div>
            <div className="vp-row"><span>ط´ظ…ط§ط±ظ‡ ظ‡ظ…ط±ط§ظ‡</span><strong dir="ltr">{profile?.phone || 'â€”'}</strong></div>
            <div className="vp-row"><span>ظ†ظ‚ط´ ط³ط§ط²ظ…ط§ظ†غŒ</span><strong>{profile?.role || 'â€”'}</strong></div>
            <div className="vp-row"><span>ظ…ط³غŒط± ظپط¹ط§ظ„</span><strong>{activeRouteTitle || 'â€”'}</strong></div>
          </div>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><SyncIcon /><strong>ط¯ط§ط¯ظ‡ ظˆ ظ‡ظ…ع¯ط§ظ…â€Œط³ط§ط²غŒ</strong></div>
          <button className="vp-action-row" type="button" disabled={loading} onClick={() => void refreshLiveData()}>
            <span className="vp-row-icon"><SyncIcon /></span>
            <span><strong>{loading ? 'ط¯ط± ط­ط§ظ„ ط¨ط§ط²ط®ظˆط§ظ†غŒâ€¦' : 'ط¨ط§ط²ط®ظˆط§ظ†غŒ ط¯ط§ط¯ظ‡ ط²ظ†ط¯ظ‡'}</strong><small>Route ظˆ Customer ط§ط² Seller Workspace</small></span>
            <ChevronLeftIcon />
          </button>
          <ToggleRow icon={<DeviceIcon />} title="طھط±ط¬غŒط­ ط°ط®غŒط±ظ‡ ط¢ظپظ„ط§غŒظ†" description="ظپظ‚ط· طھط±ط¬غŒط­ UIط› Cache/Queue ط¹ظ…ظ„غŒط§طھغŒ ظ‡ظ†ظˆط² ظپط¹ط§ظ„ ظ†ط´ط¯ظ‡" checked={offline} onChange={(value) => updateToggle('offline', value)} />
          <ToggleRow icon={<SyncIcon />} title="طھط±ط¬غŒط­ ظ‡ظ…ع¯ط§ظ…â€Œط³ط§ط²غŒ ط®ظˆط¯ع©ط§ط±" description="ظپظ‚ط· طھط±ط¬غŒط­ UIط› Sync Queue ط¯ط± Slice ط¨ط¹ط¯غŒ ظ…طھطµظ„ ظ…غŒâ€Œط´ظˆط¯" checked={autosync} onChange={(value) => updateToggle('autosync', value)} />
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><SettingsIcon /><strong>طھظ†ط¸غŒظ…ط§طھ ط¨ط±ظ†ط§ظ…ظ‡</strong></div>
          <ToggleRow icon={<BellIcon />} title="ط§ط¹ظ„ط§ظ†â€Œظ‡ط§غŒ ط¯ط±ظˆظ† ط¨ط±ظ†ط§ظ…ظ‡" description="ظ‡ط´ط¯ط§ط±ظ‡ط§غŒ ظ…ظ‡ظ… ظپط±ظˆط´ ظˆ ظ…ط³غŒط± ظ†ظ…ط§غŒط´ ط¯ط§ط¯ظ‡ ط´ظˆظ†ط¯" checked={notifications} onChange={(value) => updateToggle('notifications', value)} />
          <div className="vp-static-row"><span>ط²ط¨ط§ظ† ط±ط§ط¨ط·</span><strong>ظپط§ط±ط³غŒ</strong></div>
          <div className="vp-static-row"><span>ظ†ظ…ط§غŒط´ ط§ط¹ط¯ط§ط¯</span><strong>ظپط§ط±ط³غŒ</strong></div>
          <div className="vp-static-row"><span>ظ¾ظˆط³طھظ‡</span><strong>طھغŒط±ظ‡ ط³ط§ط²ظ…ط§ظ†غŒ</strong></div>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><ShieldIcon /><strong>ط§ظ…ظ†غŒطھ ظˆ ظ¾ط´طھغŒط¨ط§ظ†غŒ</strong></div>
          <button className="vp-action-row" type="button" onClick={() => setPasswordOpen(true)}>
            <span className="vp-row-icon"><ShieldIcon /></span>
            <span><strong>طھط؛غŒغŒط± ط±ظ…ط² ط¹ط¨ظˆط±</strong><small>ظ…طھطµظ„ ط¨ظ‡ Auth Service ظˆط§ظ‚ط¹غŒ</small></span>
            <ChevronLeftIcon />
          </button>
          <button className="vp-action-row" type="button" onClick={() => flash('Endpoint ط«ط¨طھ طھغŒع©طھ ظ¾ط´طھغŒط¨ط§ظ†غŒ ظ‡ظ†ظˆط² ط¯ط± Backend طھط¹ط±غŒظپ ظ†ط´ط¯ظ‡ ط§ط³طھ')}>
            <span className="vp-row-icon"><HelpIcon /></span>
            <span><strong>ظ¾ط´طھغŒط¨ط§ظ†غŒ</strong><small>ط¯ط± ط§غŒظ† ظ†ط³ط®ظ‡ ظپظ‚ط· ظˆط¶ط¹غŒطھ ط§طھطµط§ظ„ ظ…ط´ط®طµ ط§ط³طھ</small></span>
            <ChevronLeftIcon />
          </button>
          <div className="vp-info-row"><InfoIcon /><span>ظ†ط³ط®ظ‡ Visitor</span><strong>غ°.غ±غ·.غ°</strong></div>
        </section>

        <button className="vp-logout" type="button" onClick={() => setLogoutOpen(true)}><LogoutIcon /><span>ط®ط±ظˆط¬ ط§ط² ط­ط³ط§ط¨</span></button>
        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        {passwordOpen ? (
          <div className="vp-modal-backdrop" role="presentation" onClick={() => setPasswordOpen(false)}>
            <form className="vp-modal vp-password-modal" role="dialog" aria-modal="true" aria-label="طھط؛غŒغŒط± ط±ظ…ط²" onSubmit={submitPassword} onClick={(event) => event.stopPropagation()}>
              <span className="vp-modal-icon"><ShieldIcon /></span>
              <h2>طھط؛غŒغŒط± ط±ظ…ط² ط¹ط¨ظˆط±</h2>
              <p>ط±ظ…ط² ط¬ط¯غŒط¯ ظ¾ط³ ط§ط² طھط£غŒغŒط¯طŒ ظ†ط´ط³طھâ€Œظ‡ط§غŒ ظ‚ط¨ظ„غŒ ط­ط³ط§ط¨ ط±ط§ ط¨ط§ط·ظ„ ظ…غŒâ€Œع©ظ†ط¯.</p>
              <label><span>ط±ظ…ط² ظپط¹ظ„غŒ</span><input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
              <label><span>ط±ظ…ط² ط¬ط¯غŒط¯</span><input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} required /></label>
              <label><span>طھع©ط±ط§ط± ط±ظ…ط² ط¬ط¯غŒط¯</span><input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} required /></label>
              {passwordError ? <div className="login-message login-error" role="alert">{passwordError}</div> : null}
              <div><button type="button" className="secondary" onClick={() => setPasswordOpen(false)}>ط§ظ†طµط±ط§ظپ</button><button type="submit" className="danger" disabled={passwordBusy}>{passwordBusy ? 'ط¯ط± ط­ط§ظ„ ط«ط¨طھâ€¦' : 'طھط؛غŒغŒط± ط±ظ…ط²'}</button></div>
            </form>
          </div>
        ) : null}

        {logoutOpen ? (
          <div className="vp-modal-backdrop" role="presentation" onClick={() => setLogoutOpen(false)}>
            <section className="vp-modal" role="dialog" aria-modal="true" aria-label="طھط£غŒغŒط¯ ط®ط±ظˆط¬" onClick={(event) => event.stopPropagation()}>
              <span className="vp-modal-icon"><LogoutIcon /></span><h2>ط§ط² ط­ط³ط§ط¨ ط®ط§ط±ط¬ ظ…غŒâ€Œط´ظˆغŒطں</h2><p>ظ†ط´ط³طھ Backend ط¨ط§ط·ظ„ ظ…غŒâ€Œط´ظˆط¯ ظˆ ط¨ط±ط§غŒ ظˆط±ظˆط¯ ط¯ظˆط¨ط§ط±ظ‡ ط¨ط§غŒط¯ ط§ط·ظ„ط§ط¹ط§طھ ط­ط³ط§ط¨ ط±ط§ ظˆط§ط±ط¯ ع©ظ†غŒ.</p>
              <div><button type="button" className="secondary" onClick={() => setLogoutOpen(false)}>ط§ظ†طµط±ط§ظپ</button><button type="button" className="danger" onClick={() => { setLogoutOpen(false); void onLogout() }}>ط®ط±ظˆط¬</button></div>
            </section>
          </div>
        ) : null}

        <nav className="vh-nav" aria-label="ظ†ط§ظˆط¨ط±غŒ ظˆغŒط²غŒطھظˆط±">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>ط®ط§ظ†ظ‡</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>ظ…ط³غŒط±</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>ط³ظپط§ط±ط´</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>ظ…ط´طھط±غŒط§ظ†</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>ع¯ط²ط§ط±ط´â€Œظ‡ط§</span></button>
        </nav>
      </div>
    </main>
  )
}

type ToggleRowProps = {
  icon: React.ReactNode
  title: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}

function ToggleRow({ icon, title, description, checked, onChange }: ToggleRowProps) {
  return (
    <div className="vp-toggle-row">
      <span className="vp-row-icon">{icon}</span>
      <span><strong>{title}</strong><small>{description}</small></span>
      <button type="button" className={checked ? 'vp-switch active' : 'vp-switch'} aria-pressed={checked} aria-label={title} onClick={() => onChange(!checked)}><span /></button>
    </div>
  )
}
