import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { neginApi, type AuthProfile } from '../api/neginApi'

type VisitorAuthValue = {
  authenticated: boolean
  authenticating: boolean
  restoringSession: boolean
  profile: AuthProfile | null
  signIn: (username: string, password: string) => Promise<AuthProfile>
  signOut: () => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<AuthProfile>
}

const VisitorAuthContext = createContext<VisitorAuthValue | null>(null)
const IDLE_TIMEOUT_MS = 30 * 60 * 1000
const ACTIVITY_WRITE_THROTTLE_MS = 5000
const LAST_ACTIVITY_KEY = 'neginai.auth.last-activity'
const SIGNED_OUT_KEY = 'neginai.auth.signed-out'

function readLastActivity() {
  const value = Number(localStorage.getItem(LAST_ACTIVITY_KEY) ?? 0)
  return Number.isFinite(value) && value > 0 ? value : 0
}

function writeLastActivity(value = Date.now()) {
  localStorage.setItem(LAST_ACTIVITY_KEY, String(value))
}

export function VisitorAuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<AuthProfile | null>(null)
  const [authenticating, setAuthenticating] = useState(false)
  const [restoringSession, setRestoringSession] = useState(true)

  useEffect(() => {
    let cancelled = false
    const signedOut = localStorage.getItem(SIGNED_OUT_KEY) === '1'
    const lastActivity = readLastActivity()
    const idleExpired = lastActivity > 0 && Date.now() - lastActivity >= IDLE_TIMEOUT_MS

    if (signedOut || idleExpired) {
      if (idleExpired) {
        localStorage.setItem(SIGNED_OUT_KEY, '1')
        localStorage.removeItem(LAST_ACTIVITY_KEY)
        void neginApi.logout().catch(() => undefined)
      }
      setProfile(null)
      setRestoringSession(false)
      return () => { cancelled = true }
    }

    void neginApi.me()
      .then((currentProfile) => {
        if (!cancelled && currentProfile.active !== false) {
          setProfile(currentProfile)
          writeLastActivity()
        }
      })
      .catch(() => {
        if (!cancelled) setProfile(null)
      })
      .finally(() => {
        if (!cancelled) setRestoringSession(false)
      })
    return () => { cancelled = true }
  }, [])

  const signIn = useCallback(async (username: string, password: string) => {
    setAuthenticating(true)
    try {
      await neginApi.login(username.trim(), password)
      const verified = await neginApi.me()
      if (verified.must_change_password) {
        await neginApi.logout().catch(() => undefined)
        throw new Error('\u0644\u0637\u0641\u0627\u064b \u0627\u0628\u062a\u062f\u0627 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631 \u062e\u0648\u062f \u0631\u0627 \u062a\u063a\u064a\u064a \u062f\u0647\u064c\u062f.')
      }
      localStorage.removeItem(SIGNED_OUT_KEY)
      writeLastActivity()
      setProfile(verified)
      return verified
    } finally {
      setAuthenticating(false)
    }
  }, [])

  const signOut = useCallback(async () => {
    localStorage.setItem(SIGNED_OUT_KEY, '1')
    localStorage.removeItem(LAST_ACTIVITY_KEY)
    setProfile(null)
    void neginApi.logout().catch(() => undefined)
  }, [])

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key === SIGNED_OUT_KEY && event.newValue === '1') setProfile(null)
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  useEffect(() => {
    if (!profile) return

    let lastWritten = readLastActivity() || Date.now()
    if (!readLastActivity()) writeLastActivity(lastWritten)
    let expired = false

    const expireSession = () => {
      if (expired) return
      expired = true
      void signOut()
      window.setTimeout(() => window.location.replace('/'), 0)
    }

    const checkIdle = () => {
      const lastActivity = readLastActivity() || lastWritten
      if (Date.now() - lastActivity >= IDLE_TIMEOUT_MS) {
        expireSession()
        return true
      }
      return false
    }

    const markActivity = () => {
      if (checkIdle()) return
      const now = Date.now()
      if (now - lastWritten < ACTIVITY_WRITE_THROTTLE_MS) return
      lastWritten = now
      writeLastActivity(now)
    }

    const handleVisibility = () => {
      if (document.visibilityState !== 'visible' || checkIdle()) return
      lastWritten = Date.now()
      writeLastActivity(lastWritten)
    }

    const activityEvents = ['pointerdown', 'pointermove', 'keydown', 'scroll'] as const
    activityEvents.forEach((eventName) => window.addEventListener(eventName, markActivity, { passive: true }))
    document.addEventListener('visibilitychange', handleVisibility)
    const timer = window.setInterval(checkIdle, 30_000)

    return () => {
      activityEvents.forEach((eventName) => window.removeEventListener(eventName, markActivity))
      document.removeEventListener('visibilitychange', handleVisibility)
      window.clearInterval(timer)
  }
  }, [profile, signOut])

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const updated = await neginApi.changePassword(currentPassword, newPassword)
    writeLastActivity()
    setProfile(updated)
    return updated
  }, [])

  const authenticated = profile !== null && profile.active !== false

  const value = useMemo<VisitorAuthValue>(() => ({
    authenticated,
    authenticating,
    restoringSession,
    profile,
    signIn,
    signOut,
    changePassword,
  }), [authenticated, authenticating, changePassword, profile, restoringSession, signIn, signOut])

  return <VisitorAuthContext.Provider value={value}>{children}</VisitorAuthContext.Provider>
}

export function useVisitorAuth() {
  const value = useContext(VisitorAuthContext)
  if (!value) throw new Error('useVisitorAuth must be used inside VisitorAuthProvider')
  return value
}
