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
  onClose: () => void`r`n}

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
    flash('ط¸â€¦ط·آ³ط؛إ’ط·آ± ط¸ث† ط¸â€¦ط·آ´ط·ع¾ط·آ±ط؛إ’ط·آ§ط¸â€  ط·آ§ط·آ² Backend ط·آ¯ط¸ث†ط·آ¨ط·آ§ط·آ±ط¸â€، ط·آ®ط¸ث†ط·آ§ط¸â€ ط·آ¯ط¸â€، ط·آ´ط·آ¯ط¸â€ ط·آ¯')
  }

  async function submitPassword(event: FormEvent) {
    event.preventDefault()
    setPasswordError(null)
    if (newPassword.length < 8) {
      setPasswordError('ط·آ±ط¸â€¦ط·آ² ط·آ¬ط·آ¯ط؛إ’ط·آ¯ ط·آ¨ط·آ§ط؛إ’ط·آ¯ ط·آ­ط·آ¯ط·آ§ط¸â€ڑط¸â€‍ ط؛آ¸ ط¹آ©ط·آ§ط·آ±ط·آ§ط¹آ©ط·ع¾ط·آ± ط·آ¨ط·آ§ط·آ´ط·آ¯.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('ط·ع¾ط¹آ©ط·آ±ط·آ§ط·آ± ط·آ±ط¸â€¦ط·آ² ط·آ¬ط·آ¯ط؛إ’ط·آ¯ ط؛إ’ط¹آ©ط·آ³ط·آ§ط¸â€  ط¸â€ ط؛إ’ط·آ³ط·ع¾.')
      return
    }
    setPasswordBusy(true)
    try {
      await changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordOpen(false)
      flash('ط·آ±ط¸â€¦ط·آ² ط·آ¹ط·آ¨ط¸ث†ط·آ± ط·آ¨ط·آ§ ط¸â€¦ط¸ث†ط¸ظ¾ط¸â€ڑط؛إ’ط·ع¾ ط·ع¾ط·ط›ط؛إ’ط؛إ’ط·آ± ط¹آ©ط·آ±ط·آ¯')
    } catch (caught) {
      setPasswordError(caught instanceof Error ? caught.message : 'ط·ع¾ط·ط›ط؛إ’ط؛إ’ط·آ± ط·آ±ط¸â€¦ط·آ² ط·آ§ط¸â€ ط·آ¬ط·آ§ط¸â€¦ ط¸â€ ط·آ´ط·آ¯.')
    } finally {
      setPasswordBusy(false)
    }
  }

  return (
    <main className="vh-page" dir="rtl">
      <div className="vh-shell vp-shell">
        <header className="vh-header">
          <button className="vh-profile active" type="button" aria-current="page" onClick={onClose} aria-label="ط¨ط³طھظ† ظ¾ط±ظˆظپط§غŒظ„ ظˆ ط¨ط§ط²ع¯ط´طھ ط¨ظ‡ طµظپط­ظ‡ ظ‚ط¨ظ„">
            <span className="vh-avatar">ط¸ث†</span>
            <span className="vh-profile-copy">
              <strong>{profile?.full_name || profile?.username || 'ط¸ث†ط؛إ’ط·آ²ط؛إ’ط·ع¾ط¸ث†ط·آ±'}</strong>
              <small><PinIcon /> {profile?.branch || profile?.sales_line || 'ط·آ­ط·آ³ط·آ§ط·آ¨ ط·آ³ط·آ§ط·آ²ط¸â€¦ط·آ§ط¸â€ ط؛إ’'}</small>
            </span>
            <ChevronLeftIcon />
          </button>

          <button className="vh-bell" type="button" aria-label="ط·آ§ط·آ¹ط¸â€‍ط·آ§ط¸â€ أ¢â‚¬إ’ط¸â€،ط·آ§" onClick={() => onNavigate('/visitor/notifications')}>
            <BellIcon />{unreadCount ? <b>{unreadCount}</b> : null}
          </button>

          <div className="vh-brand" dir="ltr"><img src="/assets/neginai-logo-transparent.png" alt="Negin AI" /><div><strong>Negin <span>AI</span></strong><small>VISITOR</small></div></div>
        </header>

        <section className="vp-heading"><div><span>ط·آ­ط·آ³ط·آ§ط·آ¨ ط¸ث† ط·ع¾ط¸â€ ط·آ¸ط؛إ’ط¸â€¦ط·آ§ط·ع¾</span><h1>ط¸آ¾ط·آ±ط¸ث†ط¸ظ¾ط·آ§ط؛إ’ط¸â€‍ ط¸â€¦ط¸â€ </h1></div><SettingsIcon /></section>

        <section className="vp-identity">
          <span className="vp-avatar-large">ط¸ث†</span>
          <div>
            <strong>{profile?.full_name || profile?.username || 'ط¹آ©ط·آ§ط·آ±ط·آ¨ط·آ± ط·آ³ط·آ§ط·آ²ط¸â€¦ط·آ§ط¸â€ ط؛إ’'}</strong>
            <span>ط¹آ©ط·آ¯ ط¸آ¾ط·آ±ط·آ³ط¸â€ ط¸â€‍ط؛إ’: {profile?.personnel_id?.toLocaleString('fa-IR') || 'أ¢â‚¬â€‌'}</span>
            <small>{profile?.branch || 'ط·آ´ط·آ¹ط·آ¨ط¸â€، ط·آ«ط·آ¨ط·ع¾ ط¸â€ ط·آ´ط·آ¯ط¸â€،'}{profile?.sales_line ? ` ط¢آ· ${profile.sales_line}` : ''}</small>
          </div>
          <span className="vp-status">{profile?.active ? 'ط¸ظ¾ط·آ¹ط·آ§ط¸â€‍' : 'ط¸â€ ط·آ§ط¸â€¦ط·آ´ط·آ®ط·آµ'}</span>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><UserIcon /><strong>ط·آ§ط·آ·ط¸â€‍ط·آ§ط·آ¹ط·آ§ط·ع¾ ط·آ­ط·آ³ط·آ§ط·آ¨</strong></div>
          <div className="vp-rows">
            <div className="vp-row"><span>ط¸â€ ط·آ§ط¸â€¦ ط¹آ©ط·آ§ط·آ±ط·آ¨ط·آ±ط؛إ’</span><strong dir="ltr">{profile?.username || 'أ¢â‚¬â€‌'}</strong></div>
            <div className="vp-row"><span>ط·آ´ط¸â€¦ط·آ§ط·آ±ط¸â€، ط¸â€،ط¸â€¦ط·آ±ط·آ§ط¸â€،</span><strong dir="ltr">{profile?.phone || 'أ¢â‚¬â€‌'}</strong></div>
            <div className="vp-row"><span>ط¸â€ ط¸â€ڑط·آ´ ط·آ³ط·آ§ط·آ²ط¸â€¦ط·آ§ط¸â€ ط؛إ’</span><strong>{profile?.role || 'أ¢â‚¬â€‌'}</strong></div>
            <div className="vp-row"><span>ط¸â€¦ط·آ³ط؛إ’ط·آ± ط¸ظ¾ط·آ¹ط·آ§ط¸â€‍</span><strong>{activeRouteTitle || 'أ¢â‚¬â€‌'}</strong></div>
          </div>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><SyncIcon /><strong>ط·آ¯ط·آ§ط·آ¯ط¸â€، ط¸ث† ط¸â€،ط¸â€¦ط¹آ¯ط·آ§ط¸â€¦أ¢â‚¬إ’ط·آ³ط·آ§ط·آ²ط؛إ’</strong></div>
          <button className="vp-action-row" type="button" disabled={loading} onClick={() => void refreshLiveData()}>
            <span className="vp-row-icon"><SyncIcon /></span>
            <span><strong>{loading ? 'ط·آ¯ط·آ± ط·آ­ط·آ§ط¸â€‍ ط·آ¨ط·آ§ط·آ²ط·آ®ط¸ث†ط·آ§ط¸â€ ط؛إ’أ¢â‚¬آ¦' : 'ط·آ¨ط·آ§ط·آ²ط·آ®ط¸ث†ط·آ§ط¸â€ ط؛إ’ ط·آ¯ط·آ§ط·آ¯ط¸â€، ط·آ²ط¸â€ ط·آ¯ط¸â€،'}</strong><small>Route ط¸ث† Customer ط·آ§ط·آ² Seller Workspace</small></span>
            <ChevronLeftIcon />
          </button>
          <ToggleRow icon={<DeviceIcon />} title="ط·ع¾ط·آ±ط·آ¬ط؛إ’ط·آ­ ط·آ°ط·آ®ط؛إ’ط·آ±ط¸â€، ط·آ¢ط¸ظ¾ط¸â€‍ط·آ§ط؛إ’ط¸â€ " description="ط¸ظ¾ط¸â€ڑط·آ· ط·ع¾ط·آ±ط·آ¬ط؛إ’ط·آ­ UIط·â€؛ Cache/Queue ط·آ¹ط¸â€¦ط¸â€‍ط؛إ’ط·آ§ط·ع¾ط؛إ’ ط¸â€،ط¸â€ ط¸ث†ط·آ² ط¸ظ¾ط·آ¹ط·آ§ط¸â€‍ ط¸â€ ط·آ´ط·آ¯ط¸â€،" checked={offline} onChange={(value) => updateToggle('offline', value)} />
          <ToggleRow icon={<SyncIcon />} title="ط·ع¾ط·آ±ط·آ¬ط؛إ’ط·آ­ ط¸â€،ط¸â€¦ط¹آ¯ط·آ§ط¸â€¦أ¢â‚¬إ’ط·آ³ط·آ§ط·آ²ط؛إ’ ط·آ®ط¸ث†ط·آ¯ط¹آ©ط·آ§ط·آ±" description="ط¸ظ¾ط¸â€ڑط·آ· ط·ع¾ط·آ±ط·آ¬ط؛إ’ط·آ­ UIط·â€؛ Sync Queue ط·آ¯ط·آ± Slice ط·آ¨ط·آ¹ط·آ¯ط؛إ’ ط¸â€¦ط·ع¾ط·آµط¸â€‍ ط¸â€¦ط؛إ’أ¢â‚¬إ’ط·آ´ط¸ث†ط·آ¯" checked={autosync} onChange={(value) => updateToggle('autosync', value)} />
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><SettingsIcon /><strong>ط·ع¾ط¸â€ ط·آ¸ط؛إ’ط¸â€¦ط·آ§ط·ع¾ ط·آ¨ط·آ±ط¸â€ ط·آ§ط¸â€¦ط¸â€،</strong></div>
          <ToggleRow icon={<BellIcon />} title="ط·آ§ط·آ¹ط¸â€‍ط·آ§ط¸â€ أ¢â‚¬إ’ط¸â€،ط·آ§ط؛إ’ ط·آ¯ط·آ±ط¸ث†ط¸â€  ط·آ¨ط·آ±ط¸â€ ط·آ§ط¸â€¦ط¸â€،" description="ط¸â€،ط·آ´ط·آ¯ط·آ§ط·آ±ط¸â€،ط·آ§ط؛إ’ ط¸â€¦ط¸â€،ط¸â€¦ ط¸ظ¾ط·آ±ط¸ث†ط·آ´ ط¸ث† ط¸â€¦ط·آ³ط؛إ’ط·آ± ط¸â€ ط¸â€¦ط·آ§ط؛إ’ط·آ´ ط·آ¯ط·آ§ط·آ¯ط¸â€، ط·آ´ط¸ث†ط¸â€ ط·آ¯" checked={notifications} onChange={(value) => updateToggle('notifications', value)} />
          <div className="vp-static-row"><span>ط·آ²ط·آ¨ط·آ§ط¸â€  ط·آ±ط·آ§ط·آ¨ط·آ·</span><strong>ط¸ظ¾ط·آ§ط·آ±ط·آ³ط؛إ’</strong></div>
          <div className="vp-static-row"><span>ط¸â€ ط¸â€¦ط·آ§ط؛إ’ط·آ´ ط·آ§ط·آ¹ط·آ¯ط·آ§ط·آ¯</span><strong>ط¸ظ¾ط·آ§ط·آ±ط·آ³ط؛إ’</strong></div>
          <div className="vp-static-row"><span>ط¸آ¾ط¸ث†ط·آ³ط·ع¾ط¸â€،</span><strong>ط·ع¾ط؛إ’ط·آ±ط¸â€، ط·آ³ط·آ§ط·آ²ط¸â€¦ط·آ§ط¸â€ ط؛إ’</strong></div>
        </section>

        <section className="vp-section">
          <div className="vp-section-title"><ShieldIcon /><strong>ط·آ§ط¸â€¦ط¸â€ ط؛إ’ط·ع¾ ط¸ث† ط¸آ¾ط·آ´ط·ع¾ط؛إ’ط·آ¨ط·آ§ط¸â€ ط؛إ’</strong></div>
          <button className="vp-action-row" type="button" onClick={() => setPasswordOpen(true)}>
            <span className="vp-row-icon"><ShieldIcon /></span>
            <span><strong>ط·ع¾ط·ط›ط؛إ’ط؛إ’ط·آ± ط·آ±ط¸â€¦ط·آ² ط·آ¹ط·آ¨ط¸ث†ط·آ±</strong><small>ط¸â€¦ط·ع¾ط·آµط¸â€‍ ط·آ¨ط¸â€، Auth Service ط¸ث†ط·آ§ط¸â€ڑط·آ¹ط؛إ’</small></span>
            <ChevronLeftIcon />
          </button>
          <button className="vp-action-row" type="button" onClick={() => flash('Endpoint ط·آ«ط·آ¨ط·ع¾ ط·ع¾ط؛إ’ط¹آ©ط·ع¾ ط¸آ¾ط·آ´ط·ع¾ط؛إ’ط·آ¨ط·آ§ط¸â€ ط؛إ’ ط¸â€،ط¸â€ ط¸ث†ط·آ² ط·آ¯ط·آ± Backend ط·ع¾ط·آ¹ط·آ±ط؛إ’ط¸ظ¾ ط¸â€ ط·آ´ط·آ¯ط¸â€، ط·آ§ط·آ³ط·ع¾')}>
            <span className="vp-row-icon"><HelpIcon /></span>
            <span><strong>ط¸آ¾ط·آ´ط·ع¾ط؛إ’ط·آ¨ط·آ§ط¸â€ ط؛إ’</strong><small>ط·آ¯ط·آ± ط·آ§ط؛إ’ط¸â€  ط¸â€ ط·آ³ط·آ®ط¸â€، ط¸ظ¾ط¸â€ڑط·آ· ط¸ث†ط·آ¶ط·آ¹ط؛إ’ط·ع¾ ط·آ§ط·ع¾ط·آµط·آ§ط¸â€‍ ط¸â€¦ط·آ´ط·آ®ط·آµ ط·آ§ط·آ³ط·ع¾</small></span>
            <ChevronLeftIcon />
          </button>
          <div className="vp-info-row"><InfoIcon /><span>ط¸â€ ط·آ³ط·آ®ط¸â€، Visitor</span><strong>ط؛آ°.ط؛آ±ط؛آ·.ط؛آ°</strong></div>
        </section>

        <button className="vp-logout" type="button" onClick={() => setLogoutOpen(true)}><LogoutIcon /><span>ط·آ®ط·آ±ط¸ث†ط·آ¬ ط·آ§ط·آ² ط·آ­ط·آ³ط·آ§ط·آ¨</span></button>
        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}

        {passwordOpen ? (
          <div className="vp-modal-backdrop" role="presentation" onClick={() => setPasswordOpen(false)}>
            <form className="vp-modal vp-password-modal" role="dialog" aria-modal="true" aria-label="ط·ع¾ط·ط›ط؛إ’ط؛إ’ط·آ± ط·آ±ط¸â€¦ط·آ²" onSubmit={submitPassword} onClick={(event) => event.stopPropagation()}>
              <span className="vp-modal-icon"><ShieldIcon /></span>
              <h2>ط·ع¾ط·ط›ط؛إ’ط؛إ’ط·آ± ط·آ±ط¸â€¦ط·آ² ط·آ¹ط·آ¨ط¸ث†ط·آ±</h2>
              <p>ط·آ±ط¸â€¦ط·آ² ط·آ¬ط·آ¯ط؛إ’ط·آ¯ ط¸آ¾ط·آ³ ط·آ§ط·آ² ط·ع¾ط·آ£ط؛إ’ط؛إ’ط·آ¯ط·إ’ ط¸â€ ط·آ´ط·آ³ط·ع¾أ¢â‚¬إ’ط¸â€،ط·آ§ط؛إ’ ط¸â€ڑط·آ¨ط¸â€‍ط؛إ’ ط·آ­ط·آ³ط·آ§ط·آ¨ ط·آ±ط·آ§ ط·آ¨ط·آ§ط·آ·ط¸â€‍ ط¸â€¦ط؛إ’أ¢â‚¬إ’ط¹آ©ط¸â€ ط·آ¯.</p>
              <label><span>ط·آ±ط¸â€¦ط·آ² ط¸ظ¾ط·آ¹ط¸â€‍ط؛إ’</span><input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
              <label><span>ط·آ±ط¸â€¦ط·آ² ط·آ¬ط·آ¯ط؛إ’ط·آ¯</span><input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} required /></label>
              <label><span>ط·ع¾ط¹آ©ط·آ±ط·آ§ط·آ± ط·آ±ط¸â€¦ط·آ² ط·آ¬ط·آ¯ط؛إ’ط·آ¯</span><input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} required /></label>
              {passwordError ? <div className="login-message login-error" role="alert">{passwordError}</div> : null}
              <div><button type="button" className="secondary" onClick={() => setPasswordOpen(false)}>ط·آ§ط¸â€ ط·آµط·آ±ط·آ§ط¸ظ¾</button><button type="submit" className="danger" disabled={passwordBusy}>{passwordBusy ? 'ط·آ¯ط·آ± ط·آ­ط·آ§ط¸â€‍ ط·آ«ط·آ¨ط·ع¾أ¢â‚¬آ¦' : 'ط·ع¾ط·ط›ط؛إ’ط؛إ’ط·آ± ط·آ±ط¸â€¦ط·آ²'}</button></div>
            </form>
          </div>
        ) : null}

        {logoutOpen ? (
          <div className="vp-modal-backdrop" role="presentation" onClick={() => setLogoutOpen(false)}>
            <section className="vp-modal" role="dialog" aria-modal="true" aria-label="ط·ع¾ط·آ£ط؛إ’ط؛إ’ط·آ¯ ط·آ®ط·آ±ط¸ث†ط·آ¬" onClick={(event) => event.stopPropagation()}>
              <span className="vp-modal-icon"><LogoutIcon /></span><h2>ط·آ§ط·آ² ط·آ­ط·آ³ط·آ§ط·آ¨ ط·آ®ط·آ§ط·آ±ط·آ¬ ط¸â€¦ط؛إ’أ¢â‚¬إ’ط·آ´ط¸ث†ط؛إ’ط·ع؛</h2><p>ط¸â€ ط·آ´ط·آ³ط·ع¾ Backend ط·آ¨ط·آ§ط·آ·ط¸â€‍ ط¸â€¦ط؛إ’أ¢â‚¬إ’ط·آ´ط¸ث†ط·آ¯ ط¸ث† ط·آ¨ط·آ±ط·آ§ط؛إ’ ط¸ث†ط·آ±ط¸ث†ط·آ¯ ط·آ¯ط¸ث†ط·آ¨ط·آ§ط·آ±ط¸â€، ط·آ¨ط·آ§ط؛إ’ط·آ¯ ط·آ§ط·آ·ط¸â€‍ط·آ§ط·آ¹ط·آ§ط·ع¾ ط·آ­ط·آ³ط·آ§ط·آ¨ ط·آ±ط·آ§ ط¸ث†ط·آ§ط·آ±ط·آ¯ ط¹آ©ط¸â€ ط؛إ’.</p>
              <div><button type="button" className="secondary" onClick={() => setLogoutOpen(false)}>ط·آ§ط¸â€ ط·آµط·آ±ط·آ§ط¸ظ¾</button><button type="button" className="danger" onClick={() => { setLogoutOpen(false); void onLogout() }}>ط·آ®ط·آ±ط¸ث†ط·آ¬</button></div>
            </section>
          </div>
        ) : null}

        <nav className="vh-nav" aria-label="ط¸â€ ط·آ§ط¸ث†ط·آ¨ط·آ±ط؛إ’ ط¸ث†ط؛إ’ط·آ²ط؛إ’ط·ع¾ط¸ث†ط·آ±">
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>ط·آ®ط·آ§ط¸â€ ط¸â€،</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/route')}><MapIcon /><span>ط¸â€¦ط·آ³ط؛إ’ط·آ±</span></button>
          <button className="vh-order" type="button" onClick={() => onNavigate('/visitor/orders')}><PlusIcon /><span>ط·آ³ط¸ظ¾ط·آ§ط·آ±ط·آ´</span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/customers')}><UserGroupIcon /><span>ط¸â€¦ط·آ´ط·ع¾ط·آ±ط؛إ’ط·آ§ط¸â€ </span></button>
          <button className="vh-nav-item" type="button" onClick={() => onNavigate('/visitor/reports')}><ChartIcon /><span>ط¹آ¯ط·آ²ط·آ§ط·آ±ط·آ´أ¢â‚¬إ’ط¸â€،ط·آ§</span></button>
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
