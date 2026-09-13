import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { DownloadIcon, EyeIcon, EyeOffIcon, GlobeIcon, LockIcon, UserIcon } from './Icons'

type LoginScreenProps = {
  onLogin: (username: string, password: string) => Promise<void>
}

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState(() => localStorage.getItem('neginai.login.username') ?? '')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [remember, setRemember] = useState(() => Boolean(localStorage.getItem('neginai.login.username')))
  const [submitted, setSubmitted] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [isInstalled, setIsInstalled] = useState(() => window.matchMedia('(display-mode: standalone)').matches)

  useEffect(() => {
    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault()
      setInstallPrompt(event as BeforeInstallPromptEvent)
    }

    const handleAppInstalled = () => {
      setIsInstalled(true)
      setInstallPrompt(null)
      setMessage('Negin AI با موفقیت روی گوشی نصب شد.')
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    window.addEventListener('appinstalled', handleAppInstalled)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
      window.removeEventListener('appinstalled', handleAppInstalled)
    }
  }, [])

  const usernameError = submitted && username.trim().length === 0
  const passwordError = submitted && password.length === 0
  const canSubmit = useMemo(() => username.trim().length > 0 && password.length > 0, [username, password])

  async function handleInstallWebApp() {
    setMessage(null)

    if (isInstalled) {
      setMessage('Negin AI از قبل به‌صورت وب‌اپ روی این دستگاه نصب شده است.')
      return
    }

    if (installPrompt) {
      await installPrompt.prompt()
      const choice = await installPrompt.userChoice
      if (choice.outcome === 'accepted') {
        setMessage('درخواست نصب Negin AI تأیید شد.')
      } else {
        setMessage('نصب وب‌اپ لغو شد؛ هر زمان خواستید دوباره تلاش کنید.')
      }
      setInstallPrompt(null)
      return
    }

    if (!window.isSecureContext) {
      setMessage('برای نصب وب‌اپ، Negin AI را از آدرس HTTPS مثل vnext.hagents.ir باز کنید.')
      return
    }

    setMessage('اگر پنجره نصب نمایش داده نشد، در Chrome از منوی ⋮ گزینه «نصب برنامه» یا «افزودن به صفحه اصلی» را انتخاب کنید.')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitted(true)
    setMessage(null)
    setLoginError(null)

    if (!canSubmit || loading) return

    setLoading(true)
    try {
      await onLogin(username.trim(), password)
      if (remember) {
        localStorage.setItem('neginai.login.username', username.trim())
      } else {
        localStorage.removeItem('neginai.login.username')
      }
    } catch (caught) {
      setLoginError(caught instanceof Error ? caught.message : 'ورود به NeginAI انجام نشد.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page" dir="rtl">
      <section className="login-shell" aria-label="ورود به Negin AI">
        <div className="login-topline">
          <span className="secure-caption">ورود سازمانی</span>
          <div className="language-switch" aria-label="زبان رابط کاربری: فارسی">
            <GlobeIcon />
            <span>FA</span>
          </div>
        </div>

        <header className="login-brand">
          <img className="brand-logo" src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
          <div className="brand-wordmark" dir="ltr">Negin <span>AI</span></div>
          <p>سامانه هوشمند نگین پخش</p>
        </header>

        <section className="auth-panel">
          <div className="auth-heading">
            <h1>ورود</h1>
            <p>حساب سازمانی خود را وارد کنید</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="field-group">
              <label className={usernameError ? 'field has-error' : 'field'}>
                <UserIcon className="field-icon" />
                <input
                  type="text"
                  inputMode="text"
                  autoComplete="username"
                  placeholder="نام کاربری یا شماره موبایل"
                  aria-label="نام کاربری یا شماره موبایل"
                  aria-invalid={usernameError}
                  aria-describedby={usernameError ? 'username-error' : undefined}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
              </label>
              {usernameError ? <span className="field-error" id="username-error">نام کاربری را وارد کنید</span> : null}
            </div>

            <div className="field-group">
              <label className={passwordError ? 'field has-error' : 'field'}>
                <LockIcon className="field-icon" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="رمز عبور"
                  aria-label="رمز عبور"
                  aria-invalid={passwordError}
                  aria-describedby={passwordError ? 'password-error' : undefined}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="field-action"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? 'مخفی کردن رمز' : 'نمایش رمز'}
                  aria-pressed={showPassword}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </label>
              {passwordError ? <span className="field-error" id="password-error">رمز عبور را وارد کنید</span> : null}
            </div>

            <div className="auth-options">
              <button className="remember" type="button" onClick={() => setRemember((value) => !value)} aria-pressed={remember}>
                <span className={remember ? 'check checked' : 'check'} aria-hidden="true">{remember ? '✓' : ''}</span>
                <span>نام کاربری را به خاطر بسپار</span>
              </button>
              <button className="forgot" type="button" onClick={() => setMessage('بازیابی رمز عبور هنوز Endpoint عملیاتی ندارد؛ برای بازیابی با مدیر سیستم تماس بگیرید.')}>رمز را فراموش کرده‌اید؟</button>
            </div>

            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? 'در حال بررسی حساب…' : 'ورود به Negin AI'}
            </button>

            <button className="android-button" type="button" onClick={handleInstallWebApp}>
              <DownloadIcon />
              <span>{isInstalled ? 'وب‌اپ نصب شده' : 'نصب وب‌اپ روی گوشی'}</span>
            </button>
          </form>

          {loginError ? <div className="login-message login-error" role="alert">{loginError}</div> : null}
          {message ? <div className="login-message" role="status">{message}</div> : null}
        </section>

        <footer className="login-footer">Negin AI · Enterprise Access</footer>
      </section>
    </main>
  )
}
