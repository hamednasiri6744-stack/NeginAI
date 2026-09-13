import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { CheckCircle2, Download, Eye, EyeOff, LockKeyhole, LogIn, UserRound, WifiOff } from 'lucide-react'
import { apiRequest, ApiError } from '../../lib/api/client'
import { clearApiQueryCache } from '../../lib/api/useApiQuery'
import { NeginAIBrandMark } from '../../design-system/components/NeginAIBrandMark'
import { AuthContext, type AuthProfile } from './auth-context'

export function AuthGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<'checking' | 'anonymous' | 'success' | 'authenticated'>('checking')
  const [profile, setProfile] = useState<AuthProfile | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isOnline, setIsOnline] = useState(() => typeof navigator === 'undefined' || navigator.onLine)
  const showAndroidDownload = typeof navigator !== 'undefined'
    && /Android/i.test(navigator.userAgent)
    && !/NeginSellerAndroid\//i.test(navigator.userAgent)

  useEffect(() => {
    const syncNetworkState = () => setIsOnline(navigator.onLine)
    window.addEventListener('online', syncNetworkState)
    window.addEventListener('offline', syncNetworkState)
    return () => {
      window.removeEventListener('online', syncNetworkState)
      window.removeEventListener('offline', syncNetworkState)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    apiRequest<AuthProfile>('/auth/me', { signal: controller.signal })
      .then((value) => {
        if (controller.signal.aborted) return
        setProfile(value)
        setState('authenticated')
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        if (!(reason instanceof ApiError && reason.status === 401)) {
          console.error('NeginAI session check failed', reason)
        }
        setState('anonymous')
      })
    return () => controller.abort()
  }, [])

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!isOnline) {
      setError('\u0627\u062a\u0635\u0627\u0644 \u0627\u06cc\u0646\u062a\u0631\u0646\u062a \u0628\u0631\u0642\u0631\u0627\u0631 \u0646\u06cc\u0633\u062a. \u067e\u0633 \u0627\u0632 \u0627\u062a\u0635\u0627\u0644 \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f.')
      return
    }
    const cleanUsername = username.trim()
    if (!cleanUsername || !password) {
      setError('\u0646\u0627\u0645 \u06a9\u0627\u0631\u0628\u0631\u06cc \u0648 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631 \u0631\u0627 \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.')
      return
    }
    setPending(true)
    setError('')
    try {
      const value = await apiRequest<AuthProfile>('/auth/login', {
        method: 'POST',
        body: { username: cleanUsername, password },
      })
      clearApiQueryCache()
      setProfile(value)
      setState('success')
      window.setTimeout(() => setState('authenticated'), 360)
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 401
          ? '\u0646\u0627\u0645 \u06a9\u0627\u0631\u0628\u0631\u06cc \u06cc\u0627 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631 \u0627\u0634\u062a\u0628\u0627\u0647 \u0627\u0633\u062a.'
          : reason instanceof ApiError && (reason.kind === 'network' || reason.kind === 'timeout')
            ? '\u0627\u0631\u062a\u0628\u0627\u0637 \u0628\u0627 \u0633\u0631\u0648\u0631 \u0628\u0631\u0642\u0631\u0627\u0631 \u0646\u0634\u062f. \u0644\u0637\u0641\u0627\u064b \u0627\u062a\u0635\u0627\u0644 \u0631\u0627 \u0628\u0631\u0631\u0633\u06cc \u06a9\u0646\u06cc\u062f.'
          : reason instanceof Error
            ? reason.message
            : '\u062e\u0637\u0627 \u062f\u0631 \u0648\u0631\u0648\u062f. \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f.',
      )
    } finally {
      setPending(false)
    }
  }

  async function logout() {
    try {
      await apiRequest('/auth/logout', { method: 'POST' })
    } finally {
      clearApiQueryCache()
      setProfile(null)
      setPassword('')
      setState('anonymous')
    }
  }

  const context = useMemo(() => ({ profile, logout }), [profile])

  if (state === 'checking') {
    return (
      <main className="ng-auth-shell" dir="rtl" data-trace-id="ST-G-AUTH-CHECKING">
        <section className="ng-login-card ng-login-card--status" aria-live="polite" aria-busy="true">
          <span className="ng-loading-orb" aria-hidden="true" />
          <strong>{'\u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc \u0646\u0634\u0633\u062a...'}</strong>
          <span>{'\u0627\u062a\u0635\u0627\u0644 \u0628\u0647 '}<bdi dir="ltr">Negin AI</bdi>{' \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc \u0627\u0633\u062a.'}</span>
        </section>
      </main>
    )
  }

  if (state === 'success') {
    return (
      <main className="ng-auth-shell" dir="rtl" data-trace-id="ST-AUTH-SUCCESS">
        <section className="ng-login-card ng-login-card--status ng-login-card--success" role="status" aria-live="polite">
          <CheckCircle2 aria-hidden="true" />
          <strong>{'ورود موفق بود'}</strong>
          <span>{'در حال آماده‌سازی فضای کاری شما...'}</span>
        </section>
      </main>
    )
  }

  if (state === 'anonymous') {
    return (
      <main className="ng-auth-shell" dir="rtl" data-trace-id="SCR-AUTH-LOGIN">
        <section id="keyDialog" className="ng-login-card" data-auth-state={pending ? 'loading' : error ? 'error' : isOnline ? 'default' : 'offline'}>
          <aside className="ng-login-identity" aria-hidden="true">
            <span className="ng-login-identity__name" dir="ltr">Negin AI</span>
            <div>
              <strong>{'هوشمندی سازمانی، در یک تجربه واحد'}</strong>
              <span>{'ورود امن به فضای کاری نگین پخش'}</span>
            </div>
            <small>{'پلتفرم عملیاتی سازمانی'}</small>
          </aside>
          <div className="ng-login-panel">
            <div className="ng-login-brand">
              <NeginAIBrandMark />
              <div>
                <span className="ng-brand-name" dir="ltr">Negin AI</span>
                <p>{'دستیار هوشمند کسب‌وکار شما'}</p>
              </div>
            </div>
            <header className="ng-login-welcome">
              <h1>{'خوش آمدید'}</h1>
              <p>{'برای ورود به فضای کاری سازمانی، اطلاعات حساب خود را وارد کنید.'}</p>
            </header>
            <div className="ng-login-form-card">
              <form className="ng-login-form" onSubmit={login} aria-busy={pending}>
            {!isOnline ? (
              <div className="ng-offline-notice" role="status">
                <WifiOff size={18} aria-hidden="true" />
                <span>{'آفلاین هستید؛ برای ورود به اینترنت متصل شوید.'}</span>
              </div>
            ) : null}
            <label htmlFor="username">
              <span>{'نام کاربری'}</span>
              <div className="ng-field">
                <UserRound size={18} aria-hidden="true" />
                <input id="username" name="username" value={username} onChange={(event) => { setUsername(event.target.value); if (error) setError('') }} autoComplete="username" inputMode="text" spellCheck={false} aria-invalid={Boolean(error)} aria-describedby={error ? 'loginError' : undefined} disabled={pending} />
              </div>
            </label>
            <label htmlFor="password">
              <span>{'\u0631\u0645\u0632 \u0639\u0628\u0648\u0631'}</span>
              <div className="ng-field">
                <LockKeyhole size={18} aria-hidden="true" />
                <input id="password" name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => { setPassword(event.target.value); if (error) setError('') }} autoComplete="current-password" aria-invalid={Boolean(error)} aria-describedby={error ? 'loginError' : undefined} disabled={pending} />
                <button
                  id="togglePasswordVisibility"
                  className="ng-field-action"
                  type="button"
                  aria-label={showPassword ? '\u067e\u0646\u0647\u0627\u0646 \u06a9\u0631\u062f\u0646 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631' : '\u0646\u0645\u0627\u06cc\u0634 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631'}
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((value) => !value)}
                  disabled={pending}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>
            {error ? <div id="loginError" className="ng-form-error" role="alert">{error}</div> : null}
            <button className="ng-primary-button ng-login-submit" type="submit" disabled={pending || !isOnline} aria-disabled={pending || !isOnline}>
              {pending ? <span className="ng-button-spinner" aria-hidden="true" /> : <LogIn size={18} aria-hidden="true" />}
              <span>{pending ? 'در حال ورود...' : 'ورود به Negin AI'}</span>
            </button>
            {showAndroidDownload ? (
              <a id="androidDownloadLogin" className="ng-android-download" href="/download/android">
                <Download size={17} aria-hidden="true" />
                <span>{'دانلود نسخه اندروید'}</span>
              </a>
            ) : null}
              </form>
            </div>
            <p className="ng-login-trust">{'اتصال امن؛ دسترسی بر اساس نقش سازمانی'}</p>
          </div>
        </section>
      </main>
    )
  }

  return <AuthContext.Provider value={context}>{children}</AuthContext.Provider>
}
