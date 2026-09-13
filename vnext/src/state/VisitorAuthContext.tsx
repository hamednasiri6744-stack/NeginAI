import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { neginApi, type AuthProfile } from '../api/neginApi'

type VisitorAuthValue = {
  authenticated: boolean
  authenticating: boolean
  profile: AuthProfile | null
  signIn: (username: string, password: string) => Promise<AuthProfile>
  signOut: () => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<AuthProfile>
}

const VisitorAuthContext = createContext<VisitorAuthValue | null>(null)

export function VisitorAuthProvider({ children }: { children: ReactNode }) {
  // Product rule: every full app load starts on Login. We intentionally do not
  // auto-unlock the React shell from an existing cookie. A successful Login
  // then establishes and verifies the real signed HttpOnly server session.
  const [profile, setProfile] = useState<AuthProfile | null>(null)
  const [authenticating, setAuthenticating] = useState(false)

  const signIn = useCallback(async (username: string, password: string) => {
    setAuthenticating(true)
    try {
      await neginApi.login(username.trim(), password)
      const verified = await neginApi.me()
      if (verified.must_change_password) {
        await neginApi.logout().catch(() => undefined)
        throw new Error('این حساب نیاز به تغییر رمز اولیه دارد؛ ابتدا فعال‌سازی یا تغییر رمز را تکمیل کنید.')
      }
      setProfile(verified)
      return verified
    } finally {
      setAuthenticating(false)
    }
  }, [])

  const signOut = useCallback(async () => {
    try {
      await neginApi.logout()
    } finally {
      setProfile(null)
    }
  }, [])

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const updated = await neginApi.changePassword(currentPassword, newPassword)
    setProfile(updated)
    return updated
  }, [])

  const authenticated = profile !== null && profile.active !== false

  const value = useMemo<VisitorAuthValue>(() => ({
    authenticated,
    authenticating,
    profile,
    signIn,
    signOut,
    changePassword,
  }), [authenticated, authenticating, changePassword, profile, signIn, signOut])

  return <VisitorAuthContext.Provider value={value}>{children}</VisitorAuthContext.Provider>
}

export function useVisitorAuth() {
  const value = useContext(VisitorAuthContext)
  if (!value) throw new Error('useVisitorAuth must be used inside VisitorAuthProvider')
  return value
}
